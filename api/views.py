from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from interna.models import Producto, DetallePedido, Pedido
from .serializers import ProductoSerializer, PedidoSerializer, DetallePedidoSerializer

class ProductoViewSet(viewsets.ModelViewSet):
    serializer_class = ProductoSerializer
    queryset = Producto.objects.all()

class CarritoAPIView(APIView):
    def get(self, request):
        user = request.user if request.user.is_authenticated else User.objects.first()
        pedido, _ = Pedido.objects.get_or_create(usuario=user, estado='pendiente')
        serializer = PedidoSerializer(pedido)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        user = request.user if request.user.is_authenticated else User.objects.first()
        producto_id = request.data.get('producto_id')
        cantidad = int(request.data.get('cantidad', 1))
        producto = get_object_or_404(Producto, id=producto_id)
        if producto.stock_actual < cantidad:
            return Response({"error": "poco stock disponible"}, status=status.HTTP_400_BAD_REQUEST)
        pedido, _ = Pedido.objects.get_or_create(usuario=user, estado='pendiente')
        
        detalle, creado = DetallePedido.objects.get_or_create(
            pedido=pedido,
            producto=producto,
            defaults={'precio_unitario': producto.precio, 'cantidad': cantidad}
        )

        if not creado:
            if detalle.cantidad + cantidad > producto.stock_actual:
                return Response({"error": "poco stock disponible"}, status=status.HTTP_400_BAD_REQUEST)
            detalle.cantidad += cantidad
            detalle.save()

        serializer = PedidoSerializer(pedido)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request):
        user = request.user if request.user.is_authenticated else User.objects.first()
        pedido = Pedido.objects.filter(usuario=user, estado='pendiente').first()
        if pedido:
            producto_id = request.data.get('producto_id')
            if producto_id:
                detalle = pedido.detallepedido_set.filter(producto=producto_id).first()
                if detalle:
                    detalle.delete()
                return Response({"mensaje": "producto eliminado"}, status=status.HTTP_200_OK)
            else:
                pedido.delete()
        return Response({"mensaje": "se vacio el carrito"}, status=status.HTTP_200_OK)

class PagarCarritoAPIView(APIView):
    def post(self, request):
        user = request.user if request.user.is_authenticated else User.objects.first()
        pedido = get_object_or_404(Pedido, usuario=user, estado='pendiente')
        detalles = pedido.detallepedido_set.all()
        if not detalles.exists():
            return Response({"error": "el carrito está vacio"}, status=status.HTTP_400_BAD_REQUEST)
        for detalle in detalles:
            producto = detalle.producto
            if producto.stock_actual < detalle.cantidad:
                return Response({"error": f"poco stock disponible para {producto.nombre}."}, status=status.HTTP_400_BAD_REQUEST)
            producto.stock_actual -= detalle.cantidad
            producto.save()

        pedido.estado = 'pagado'
        pedido.save()

        return Response({"mensaje": "pago realizado con éxito"}, status=status.HTTP_200_OK)

