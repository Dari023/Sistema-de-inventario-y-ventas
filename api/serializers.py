from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from interna.models import Producto, DetallePedido, Pedido, CategoriaProducto
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from .models import Cliente
from uuid import uuid4
import re

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
    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True)
    password_confirmacion = serializers.CharField(write_only=True)
    rut = serializers.CharField(write_only=True)
    nombre = serializers.CharField(write_only=True)
    apellido = serializers.CharField(write_only=True)
    telefono = serializers.CharField(write_only=True, required=False, allow_blank=True, default='')
    direccion = serializers.CharField(write_only=True, required=False, allow_blank=True, max_length=200, default='')

    class Meta:
        model = User
        fields = ['email', 'password', 'password_confirmacion', 'rut', 'nombre',
                  'apellido', 'telefono', 'direccion']

    def validate_rut(self, value):
        rut = (
            value.strip()
            .upper()
            .replace(".", "")
            .replace(" ", "")
        )
        formato = re.fullmatch(
            r"([0-9]{1,8})-?([0-9K])",
            rut,
        )

        if not formato:
            raise serializers.ValidationError(
                "Ingresa un RUT Válido, por ejemplo: 12345678-5."
            )

        cuerpo, verificador = formato.groups()
        cuerpo = str(int(cuerpo))

        if cuerpo == "0":
            raise serializers.ValidationError(
                "El RUT no Puede ser Cero."
            )

        suma = 0
        multiplicador = 2

        for numero in reversed(cuerpo):
            suma += int(numero) * multiplicador
            multiplicador += 1

            if multiplicador > 7:
                multiplicador = 2

        resultado = 11 - (suma % 11)

        if resultado == 11:
            verificador_esperado = "0"
        elif resultado == 10:
            verificador_esperado = "K"
        else:
            verificador_esperado = str(resultado)

        if verificador != verificador_esperado:
            raise serializers.ValidationError(
                "Ingresa un RUT Válido"
            )

        rut_normalizado = f"{cuerpo}-{verificador}"

        if Cliente.objects.filter(rut=rut_normalizado).exists():
            raise serializers.ValidationError(
                "Ya Existe un Cliente con este RUT."
            )

        return rut_normalizado

    def validate_email(self, value):
        correo = value.strip().lower()

        if User.objects.filter(email__iexact=correo).exists():
            raise serializers.ValidationError(
                "Ya Existe un Usuario con este Correo."
            )
        return correo

    def validate_telefono(self, value):
        if not value.strip():
            return ""

        telefono = re.sub(r"[\s()-]", "", value)

        if telefono.startswith("+56"):
            telefono = telefono[3:]
        elif re.fullmatch(r"56[0-9]{9}", telefono):
            telefono = telefono[2:]

        if not re.fullmatch(r"[0-9]{9}", telefono):
            raise serializers.ValidationError(
                "Ingresa un Número de 9 dígitos, "
                "Por Ejemplo: 912345678."
            )

        return f"+56{telefono}"

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirmacion"]:
            raise serializers.ValidationError({
                "password_confirmacion": [
                    "Las Contraseñas no Coinciden."
                ],
            })

        password = attrs["password"]
        errores = []

        if not any(caracter.isupper() for caracter in password):
            errores.append(
                "La Contraseña debe Incluir al Menos una Mayúscula."
            )

        if not any(caracter.islower() for caracter in password):
            errores.append(
                "La Contraseña debe Incluir al Menos una Minúscula."
            )

        if not any(caracter.isdecimal() for caracter in password):
            errores.append(
                "La Contraseña debe Incluir al Menos un Número."
            )

        if not any(
            not caracter.isalnum() and not caracter.isspace()
            for caracter in password
        ):
            errores.append(
                "La Contraseña debe Incluir al Menos un Símbolo, "
            )

        usuario = User(
            email=attrs.get("email", ""),
            first_name=attrs.get("nombre", ""),
            last_name=attrs.get("apellido", ""),
        )

        try:
            validate_password(password, user=usuario)
        except DjangoValidationError as error:
            errores.extend(error.messages)

        if errores:
            raise serializers.ValidationError({
                "password": errores,
            })

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        validated_data.pop("password_confirmacion")
        datos_cliente = {
            campo: validated_data.pop(campo)
            for campo in ('rut', 'telefono', 'direccion')
        }

        user = User.objects.create_user(
            username=uuid4().hex,
            first_name=validated_data.pop('nombre'),
            last_name=validated_data.pop('apellido'),
            **validated_data,
        )

        Cliente.objects.create(usuario=user, **datos_cliente)
        return user
