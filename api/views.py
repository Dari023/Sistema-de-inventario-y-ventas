from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.models import User
from django.db import transaction
from django.conf import settings
from transbank.webpay.webpay_plus.transaction import Transaction as WpTx
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys

from interna.models import Producto, DetallePedido, Pedido, CategoriaProducto

from .models import Cliente
from .serializers import (
    ProductoSerializer,
    PedidoSerializer,
    CategoriaProductoSerializer,
    RegistroClienteSerializer,
    LoginCorreoSerializer,
    MiCuentaSerializer,
)


class ProductoViewSet(viewsets.ModelViewSet):
    serializer_class = ProductoSerializer
    queryset = Producto.objects.all()


def obtener_carrito(request, crear=False):
    filtros = {"estado": "pendiente"}

    if request.user.is_authenticated:
        filtros["cliente"] = get_object_or_404(
            Cliente,
            usuario=request.user,
        )
    else:
        if not request.session.session_key:
            if not crear:
                return None
            request.session.create()

        filtros["cliente"] = None
        filtros["session_key"] = request.session.session_key

    if crear:
        pedido, _ = Pedido.objects.get_or_create(**filtros)
        return pedido

    return Pedido.objects.filter(**filtros).first()

def _webpay_tx():
    cc = getattr(settings, 'WEBPAY_COMMERCE_CODE', '')
    key = getattr(settings, 'WEBPAY_API_KEY', '')
    if getattr(settings, 'WEBPAY_ENV', 'integration') == 'production' and cc and key:
        return WpTx.build_for_production(cc, key)
    return WpTx.build_for_integration(
        IntegrationCommerceCodes.WEBPAY_PLUS,
        IntegrationApiKeys.WEBPAY,
    )

class CarritoAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        pedido = obtener_carrito(request)

        if pedido is None:
            return Response({
                "detalles": [],
                "total": "0",
            })

        serializer = PedidoSerializer(pedido)
        return Response(serializer.data)

    def post(self, request):
        producto_id = request.data.get("producto_id")

        try:
            cambio = int(request.data.get("cantidad", 1))
        except (TypeError, ValueError):
            return Response(
                {"error": "La Cantidad debe ser un Número Entero"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        producto = get_object_or_404(Producto, pk=producto_id)
        pedido = obtener_carrito(request, crear=True)

        detalle = pedido.detallepedido_set.filter(
            producto=producto,
        ).first()

        cantidad_actual = detalle.cantidad if detalle else 0
        nueva_cantidad = cantidad_actual + cambio

        if nueva_cantidad <= 0:
            return Response(
                {"error": "La Cantidad debe ser Mayor que Cero"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if nueva_cantidad > producto.stock_actual:
            return Response(
                {"error": "No hay Suficiente Stock Disponible"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if detalle:
            detalle.cantidad = nueva_cantidad
            detalle.save(update_fields=["cantidad"])
        else:
            DetallePedido.objects.create(
                pedido=pedido,
                producto=producto,
                cantidad=nueva_cantidad,
                precio_unitario=producto.precio,
            )

        serializer = PedidoSerializer(pedido)
        return Response(serializer.data)

    def delete(self, request):
        pedido = obtener_carrito(request)

        if pedido is None:
            return Response({"mensaje": "El Carrito Está Vacío."})

        producto_id = request.data.get("producto_id")

        if producto_id:
            pedido.detallepedido_set.filter(
                producto_id=producto_id,
            ).delete()

            return Response({
                "mensaje": "Producto Eliminado del Carrito"
            })

        pedido.detallepedido_set.all().delete()
        return Response({"mensaje": "Se Vació el Carrito."})

class WebpayIniciarView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        pedido = obtener_carrito(request)
        if not pedido.detallepedido_set.exists():
            return Response({"error": "el carrito está vacío"}, status=status.HTTP_400_BAD_REQUEST)
        if not request.user.is_authenticated:
            campos = {
                'nombre_invitado': 'nombre', 'rut_invitado': 'RUT',
                'email_invitado': 'email', 'telefono_invitado': 'teléfono',
                'direccion_invitado': 'dirección',
            }
            faltantes = [label for campo, label in campos.items() if not str(request.data.get(campo) or '').strip()]
            if faltantes:
                return Response({"error": f"Faltan campos: {', '.join(faltantes)}"}, status=status.HTTP_400_BAD_REQUEST)
            for campo in campos:
                setattr(pedido, campo, str(request.data[campo]).strip())
            pedido.save()

        return_url = getattr(settings, 'WEBPAY_RETURN_URL', 'http://localhost:8000/api/webpay/retorno/')
        try:
            resp = _webpay_tx().create(
                buy_order=f"pedido-{pedido.id}",
                session_id=str(pedido.id_compra),
                amount=int(pedido.total),
                return_url=return_url,
            )
            return Response({"url": resp['url'], "token": resp['token']})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class WebpayRetornoView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [] 

    def post(self, request):
        return self._procesar_retorno(request)

    def get(self, request):
        return self._procesar_retorno(request)

    def _procesar_retorno(self, request):
        frontend = getattr(settings, 'WEBPAY_FRONTEND_URL', 'http://localhost:5173')
        params = request.POST if request.method == 'POST' else request.GET
        token = params.get('token_ws')
        if not token:
            return redirect(f"{frontend}/carrito?pago=cancelado")
        try:
            resp = _webpay_tx().commit(token)
        except Exception:
            return redirect(f"{frontend}/carrito?pago=error")
        if resp.get('response_code') != 0:
            return redirect(f"{frontend}/carrito?pago=rechazado")
        buy_order = str(resp.get('buy_order') or '')
        try:
            pedido = Pedido.objects.get(
                pk=int(buy_order.replace('pedido-', '')),
            )
        except (TypeError, ValueError, Pedido.DoesNotExist):
            return redirect(f"{frontend}/carrito?pago=error")
        if pedido.estado == 'pagado':
            return redirect(f"{frontend}/compra/{pedido.id_compra}")
        if pedido.estado != 'pendiente':
            return redirect(f"{frontend}/carrito?pago=error")

        with transaction.atomic():
            for detalle in pedido.detallepedido_set.select_related('producto'):
                prod = detalle.producto
                if prod.stock_actual < detalle.cantidad:
                    return redirect(f"{frontend}/carrito?pago=sin-stock")
                prod.stock_actual -= detalle.cantidad
                prod.save(update_fields=['stock_actual'])
            pedido.estado = 'pagado'
            pedido.save()
        return redirect(f"{frontend}/compra/{pedido.id_compra}")    

class CompraDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id_compra):
        pedidos = Pedido.objects.filter(estado="pagado")

        if request.user.is_authenticated:
            pedidos = pedidos.filter(cliente__usuario=request.user)
        else:
            clave_sesion = request.session.session_key

            if clave_sesion:
                pedidos = pedidos.filter(
                    cliente__isnull=True,
                    session_key=clave_sesion,
                )
            else:
                pedidos = pedidos.none()

        pedido = get_object_or_404(pedidos, id_compra=id_compra)
        return Response(PedidoSerializer(pedido).data)

class RegistroClienteView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegistroClienteSerializer

class MiCuentaView(generics.RetrieveUpdateAPIView):
    serializer_class = MiCuentaSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(
            Cliente,
            usuario=self.request.user,
        )

class CategoriaProductoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategoriaProductoSerializer
    queryset = CategoriaProducto.objects.filter(
        activo=True,
    ).order_by("nombre")
    permission_classes = [AllowAny]
    pagination_class = None

class LoginCorreoView(TokenObtainPairView):
    serializer_class = LoginCorreoSerializer