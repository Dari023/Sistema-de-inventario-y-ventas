from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.db import transaction

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

class PagarCarritoAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        pedido = obtener_carrito(request)

        if pedido is None:
            return Response(
                {"error": "El Carrito Está Vacío."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        datos_invitado = {}

        if not request.user.is_authenticated:
            campos = {
                "nombre_invitado": "nombre",
                "rut_invitado": "RUT",
                "email_invitado": "correo",
                "telefono_invitado": "teléfono",
                "direccion_invitado": "dirección",
            }

            faltantes = []

            for campo, etiqueta in campos.items():
                valor = request.data.get(campo)

                if not isinstance(valor, str) or not valor.strip():
                    faltantes.append(etiqueta)
                else:
                    datos_invitado[campo] = valor.strip()

            if faltantes:
                return Response(
                    {"error": f"Faltan campos: {', '.join(faltantes)}."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        with transaction.atomic():
            pedido = get_object_or_404(
                Pedido.objects.select_for_update(),
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
                if detalle.cantidad <= 0:
                    return Response(
                        {"error": "El carrito contiene una cantidad inválida."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if detalle.producto.stock_actual < detalle.cantidad:
                    return Response(
                        {
                            "error": (
                                f"No hay Suficiente Stock para "
                                f"{detalle.producto.nombre}."
                            )
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            for detalle in detalles:
                producto = detalle.producto
                producto.stock_actual -= detalle.cantidad
                producto.save(update_fields=["stock_actual"])

            pedido.estado = "pagado"

            for campo, valor in datos_invitado.items():
                setattr(pedido, campo, valor)

            pedido.save(
                update_fields=["estado"] + list(datos_invitado)
            )

        return Response({
            "mensaje": "Pago Realizado con Éxito.",
            "id_compra": str(pedido.id_compra),
            "id_pedido": pedido.pk,
            "estado": pedido.estado,
        })

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