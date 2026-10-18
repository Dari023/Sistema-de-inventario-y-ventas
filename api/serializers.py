from rest_framework import serializers
from interna.models import Producto, DetallePedido, Pedido, CategoriaProducto
from django.contrib.auth.models import User
from django.db import transaction
from .models import Cliente

class ProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = '__all__'

class CategoriaProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaProducto
        fields = ['id', 'nombre', 'imagen']        

class DetallePedidoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.ReadOnlyField(source='producto.nombre')
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = DetallePedido
        fields = ['id', 'producto', 'producto_nombre', 'cantidad', 'precio_unitario', 'subtotal']

class PedidoSerializer(serializers.ModelSerializer):
    detalles = DetallePedidoSerializer(source='detallepedido_set', many=True, read_only=True)
    total = serializers.ReadOnlyField()

    class Meta:
        model = Pedido
        fields = ['id', 'usuario', 'fecha_pedido', 'estado', 'detalles', 'total']

class RegistroClienteSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    rut = serializers.CharField(write_only=True)
    nombre = serializers.CharField(write_only=True)
    apellido = serializers.CharField(write_only=True)
    telefono = serializers.CharField(write_only=True, required=False, default='')
    direccion = serializers.CharField(write_only=True, required=False, default='')

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'rut', 'nombre',
                  'apellido', 'telefono', 'direccion']

    def validate_rut(self, value):
        if Cliente.objects.filter(rut=value).exists():
            raise serializers.ValidationError("Ya existe un cliente con este RUT")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Ya existe un usuario con este correo")
        return value

    @transaction.atomic
    def create(self, validated_data):
        datos_cliente = {
            campo: validated_data.pop(campo)
            for campo in ('rut', 'telefono', 'direccion')
        }
        user = User.objects.create_user(
            first_name=validated_data.pop('nombre'),
            last_name=validated_data.pop('apellido'),
            **validated_data,
        )
        Cliente.objects.create(usuario=user, **datos_cliente)
        return user