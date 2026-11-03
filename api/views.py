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

class ProductoViewSet(viewsets.ModelViewSet):
    serializer_class = ProductoSerializer
    queryset = Producto.objects.all()

def obtener_carrito(request, crear=False):
    if request.user.is_authenticated:
        cliente = get_object_or_404(
            Cliente,
            usuario=request.user,
        )

        pedido = Pedido.objects.filter(
            cliente=cliente,
            estado="pendiente",
        ).first()

        if pedido is None and crear:
            pedido = Pedido.objects.create(
                cliente=cliente,
                estado="pendiente",
            )

        return pedido

    pedido_id = request.session.get("carrito_pedido_id")

    pedido = Pedido.objects.filter(
        pk=pedido_id,
        cliente__isnull=True,
        estado="pendiente",
    ).first()

    if pedido is None and crear:
        pedido = Pedido.objects.create(
            cliente=None,
            estado="pendiente",
        )
        request.session["carrito_pedido_id"] = pedido.pk

    return pedido

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

        producto = get_object_or_404(Producto, pk=producto_id,)
        pedido = obtener_carrito(request, crear=True)
        detalle = pedido.detallepedido_set.filter(producto=producto,).first()
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

class PagarCarritoAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        pedido = obtener_carrito(request)
        if pedido is None:
            return Response(
                {"error": "El Carrito Está Vacío."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        with transaction.atomic():
            pedido = Pedido.objects.select_for_update().get(
                pk=pedido.pk,
            )

            if pedido.estado != "pendiente":
                return Response(
                    {"error": "Este Pedido ya fue Procesado."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            detalles = list(
                pedido.detallepedido_set
                .select_related("producto")
                .select_for_update()
                .order_by("producto_id")
            )

            if not detalles:
                return Response(
                    {"error": "El Carrito Está Vacío."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            for detalle in detalles:
                if detalle.producto.stock_actual < detalle.cantidad:
                    return Response(
                        {
                            "error": f"No hay Suficiente Stock para {detalle.producto.nombre}."
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            for detalle in detalles:
                producto = detalle.producto
                producto.stock_actual -= detalle.cantidad
                producto.save(update_fields=["stock_actual"])

            pedido.estado = "pagado"
            pedido.save(update_fields=["estado"])
            if not request.user.is_authenticated:
                request.session.pop("carrito_pedido_id", None)

        return Response({
            "mensaje": "Pago Realizado con Éxito.",
            "id_compra": str(pedido.id_compra),
            "estado": pedido.estado,
        })
    
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