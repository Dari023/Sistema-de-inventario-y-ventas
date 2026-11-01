from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from interna.models import Producto, DetallePedido, Pedido, CategoriaProducto
from .models import Cliente
from django.db import transaction

from .serializers import (
    ProductoSerializer,
    PedidoSerializer,
    DetallePedidoSerializer,
    CategoriaProductoSerializer,
    RegistroClienteSerializer,
    LoginCorreoSerializer,
    MiCuentaSerializer,
)

def _get_pedido(request):
    if request.user.is_authenticated:
        cliente = get_object_or_404(Cliente, usuario=request.user)
        pedido, _ = Pedido.objects.get_or_create(cliente=cliente, estado='pendiente')
        return pedido

    if not request.session.session_key:
        request.session.create()
    pedido, _ = Pedido.objects.get_or_create(
        session_key=request.session.session_key,
        estado='pendiente',
        defaults={'cliente': None},
    )
    return pedido

class ProductoViewSet(viewsets.ModelViewSet):
    serializer_class = ProductoSerializer
    queryset = Producto.objects.all()

class CarritoAPIView(APIView):
    def get(self, request):
        pedido = _get_pedido(request)
        serializer = PedidoSerializer(pedido)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        pedido = _get_pedido(request)
        producto_id = request.data.get('producto_id')
        cantidad = int(request.data.get('cantidad', 1))
        producto = get_object_or_404(Producto, id=producto_id)
        if producto.stock_actual < cantidad:
            return Response({"error": "poco stock disponible"}, status=status.HTTP_400_BAD_REQUEST)

        detalle, creado = DetallePedido.objects.get_or_create(
            pedido=pedido,
            producto=producto,
            defaults={'precio_unitario': producto.precio, 'cantidad': cantidad},
        )

        if not creado:
            if detalle.cantidad + cantidad > producto.stock_actual:
                return Response({"error": "poco stock disponible"}, status=status.HTTP_400_BAD_REQUEST)
            detalle.cantidad += cantidad
            detalle.save()

        serializer = PedidoSerializer(pedido)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        pedido = _get_pedido(request)
        producto_id = request.data.get('producto_id')
        if producto_id:
            pedido.detallepedido_set.filter(producto_id=producto_id).delete()
            return Response({"mensaje": "producto eliminado"}, status=status.HTTP_200_OK)
        pedido.delete()
        return Response({"mensaje": "se vacio el carrito"}, status=status.HTTP_200_OK)

class PagarCarritoAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        pedido = _get_pedido(request)
        detalles = list(pedido.detallepedido_set.select_related('producto'))
        if not detalles:
            return Response({"error": "el carrito está vacio"}, status=status.HTTP_400_BAD_REQUEST)

        datos_invitado = {}
        if not request.user.is_authenticated:
            campos = {
                'nombre_invitado': 'nombre',
                'rut_invitado': 'RUT',
                'email_invitado': 'email',
                'telefono_invitado': 'teléfono',
                'direccion_invitado': 'dirección',
            }
            faltantes = [
                label for campo, label in campos.items()
                if not str(request.data.get(campo) or '').strip()
            ]
            if faltantes:
                return Response(
                    {"error": f"Faltan campos: {', '.join(faltantes)}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            datos_invitado = {campo: str(request.data[campo]).strip() for campo in campos}

        with transaction.atomic():
            for detalle in detalles:
                producto = detalle.producto
                if producto.stock_actual < detalle.cantidad:
                    transaction.set_rollback(True)
                    return Response(
                        {"error": f"poco stock disponible para {producto.nombre}."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                producto.stock_actual -= detalle.cantidad
                producto.save(update_fields=['stock_actual'])

            pedido.estado = 'pagado'
            for k, v in datos_invitado.items():
                setattr(pedido, k, v)
            pedido.save()
        return Response({
            "mensaje": "pago realizado con éxito",
            "id_compra": str(pedido.id_compra),
            "id_pedido": pedido.id,
            "estado": pedido.estado,
        }, status=status.HTTP_200_OK)

class CompraDetailView(APIView):
    permission_classes = [AllowAny]
    def get(self, request, id_compra):
        pedido = get_object_or_404(Pedido, id_compra=id_compra, estado='pagado')
        return Response(PedidoSerializer(pedido).data, status=status.HTTP_200_OK)
    
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
    queryset = CategoriaProducto.objects.filter(activo=True).order_by("nombre")
    permission_classes = [AllowAny]
    pagination_class = None

class LoginCorreoView(TokenObtainPairView):
    serializer_class = LoginCorreoSerializer