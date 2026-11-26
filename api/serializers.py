from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from interna.models import Producto, DetallePedido, Pedido, CategoriaProducto, Resena, PreguntaFrecuente, ProductoVariante
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from decimal import Decimal
from .models import Cliente
from uuid import uuid4
from interna.models import Consulta, DetallePedidoPersonalizado
import re

def validar_telefono_chileno(value):
    if not value.strip():
        return ""

    telefono = re.sub(r"[\s()-]", "", value)

    if telefono.startswith("+56"):
        telefono = telefono[3:]
    elif re.fullmatch(r"56[0-9]{9}", telefono):
        telefono = telefono[2:]

    if not re.fullmatch(r"[0-9]{9}", telefono):
        raise serializers.ValidationError(
            "Ingresa un Teléfono de 9 dígitos")

    return f"+56{telefono}"

def validar_rut_chileno(value):
    rut = (value.strip()
        .upper()
        .replace('.', '')
        .replace(' ', '')
    )
    formato = re.fullmatch(r'([0-9]{1,8})-?([0-9K])', rut)

    if not formato:
        raise serializers.ValidationError('Ingresa un RUT Válido, Por Ejemplo: 12345678-5')

    cuerpo, verificador = formato.groups()
    cuerpo = str(int(cuerpo))

    if cuerpo == '0':
        raise serializers.ValidationError('El RUT no Puede ser Cero')

    suma = 0
    multiplicador = 2

    for numero in reversed(cuerpo):
        suma += int(numero) * multiplicador
        multiplicador += 1

        if multiplicador > 7:
            multiplicador = 2

    resultado = 11 - (suma % 11)

    if resultado == 11:
        esperado = '0'
    elif resultado == 10:
        esperado = 'K'
    else:
        esperado = str(resultado)

    if verificador != esperado:
        raise serializers.ValidationError('Ingresa un RUT Válido')

    return f'{cuerpo}-{verificador}'

class ProductoVarianteSerializer(serializers.ModelSerializer):
    precio_final = serializers.ReadOnlyField()

    class Meta:
        model = ProductoVariante
        fields = ['id', 'talla', 'precio', 'precio_final', 'stock_actual', 'a_pedido']

class ProductoSerializer(serializers.ModelSerializer):

    descuento_porcentaje = serializers.IntegerField(read_only = True)
    precio_final = serializers.DecimalField(max_digits=10, decimal_places=0, read_only=True)
    variantes = ProductoVarianteSerializer(many=True, read_only=True)

    class Meta:
        model = Producto
        fields = '__all__'

class CategoriaProductoSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoriaProducto
        fields = ['id', 'nombre', 'imagen']        

class DetallePedidoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.ReadOnlyField(source="producto.nombre")
    producto_imagen = serializers.ImageField(source="producto.imagen", read_only=True)
    subtotal = serializers.ReadOnlyField()
    producto_id = serializers.IntegerField(read_only=True)
    variante_id = serializers.IntegerField(read_only=True, allow_null=True)
    talla = serializers.SerializerMethodField()

    def get_talla(self, detalle):
        return detalle.variante.talla if detalle.variante_id is not None else None

    class Meta:
        model = DetallePedido
        fields = ["id", "producto", 'producto_id', 'variante_id', 'talla', "producto_nombre", "producto_imagen", "cantidad", 
                    "precio_unitario", "subtotal"]

    def to_representation(self, detalle):
        datos = super().to_representation(detalle)

        if self.context.get('es_carrito'):
            precio = detalle.precio_vigente
            datos['precio_unitario'] = format(precio, "f")
            datos['subtotal'] = format(precio * detalle.cantidad, "f")

        return datos

class DetallePedidoPersonalizadoSerializer(serializers.ModelSerializer):
    subtotal = serializers.ReadOnlyField()

    class Meta:
        model = DetallePedidoPersonalizado
        fields = [
            'id',
            'descripcion',
            'imagen_referencia',
            'cantidad',
            'precio_unitario',
            'subtotal',
            'unidades_fabricadas'
        ]
        read_only_fields = fields

class PedidoSerializer(serializers.ModelSerializer):
    detalles = DetallePedidoSerializer(source="detallepedido_set", many=True, read_only=True)
    detalles_personalizados = DetallePedidoPersonalizadoSerializer(many=True, read_only=True)
    total = serializers.ReadOnlyField()
    enlace_cliente = serializers.SerializerMethodField()

    class Meta:
        model = Pedido
        fields = ["id", "id_compra", "cliente", "fecha_pedido", "estado", "etapa", "tipo_pedido", "cancelado",
            "detalles", "total", "nombre_invitado", "rut_invitado", "email_invitado", "telefono_invitado",
            "direccion_invitado", "tipo_entrega", "detalles_personalizados", "enlace_cliente"]
        read_only_fields = ["id_compra", "fecha_pedido", "estado", "cliente", "tipo_pedido", "cancelado"]

    def to_representation(self, instancia):
        datos = super().to_representation(instancia)

        if self.context.get('es_carrito'):
            total = sum((Decimal(str(linea['subtotal'])) for linea in datos['detalles']), Decimal('0'))
            datos['total'] = format(total, "f")

        return datos

    def get_enlace_cliente(self, pedido):
        if pedido.tipo_pedido != 'personalizado':
            return None

        request = self.context.get('request')

        if request is None or not request.user.is_authenticated:
            return None

        if (pedido.cliente_id is None or pedido.cliente.usuario_id != request.user.pk):
            return None

        from interna.views import crear_enlace_pedido_personalizado

        return crear_enlace_pedido_personalizado(request, pedido)
    
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
        rut = validar_rut_chileno(value)

        if Cliente.objects.filter(rut=rut).exists():
            raise serializers.ValidationError('Ya Existe un Cliente con Este RUT')

        return rut

    def validate_email(self, value):
        correo = value.strip().lower()

        if User.objects.filter(email__iexact=correo).exists():
            raise serializers.ValidationError(
                "Ya Existe un Usuario con este Correo."
            )
        return correo

    def validate_telefono(self, value):
        return validar_telefono_chileno(value)

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

class LoginCorreoSerializer(TokenObtainPairSerializer):
    default_error_messages = {
        "no_active_account": "Correo o Contraseña Incorrectos."
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields.pop(self.username_field)
        self.fields["email"] = serializers.EmailField(write_only=True)

    def validate(self, attrs):
        try:
            usuario = User.objects.get(
                email__iexact=attrs["email"].strip()
            )
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            raise AuthenticationFailed(
                "Correo o Contraseña Incorrectos."
            )

        return super().validate({
            self.username_field: usuario.get_username(),
            "password": attrs["password"],
        })    
    
class MiCuentaSerializer(serializers.ModelSerializer):
    nombre = serializers.CharField(
        source="usuario.first_name",
        max_length=150,
    )
    apellido = serializers.CharField(
        source="usuario.last_name",
        max_length=150,
    )
    email = serializers.EmailField(
        source="usuario.email",
        max_length = 254,
    )

    class Meta:
        model = Cliente
        fields = [
            "nombre",
            "apellido",
            "email",
            "rut",
            "telefono",
            "direccion",
        ]
        read_only_fields = ["rut"]

    def validate_telefono(self, value):
        return validar_telefono_chileno(value)

    def validate_email(self, value):
        correo = value.strip().lower()

        if User.objects.filter(
            email__iexact=correo
        ).exclude(
            pk=self.instance.usuario_id
        ).exists():
            raise serializers.ValidationError(
                "Ya Existe un Usuario con este Correo."
            )
        return correo

    @transaction.atomic
    def update(self, instance, validated_data):
        datos_usuario = validated_data.pop("usuario", {})
        usuario = instance.usuario

        usuario.first_name = datos_usuario.get(
            "first_name", usuario.first_name
        )
        usuario.last_name = datos_usuario.get(
            "last_name", usuario.last_name
        )
        usuario.email = datos_usuario.get(
            "email", usuario.email
        )
        usuario.save(update_fields=["first_name", "last_name", "email"])

        return super().update(instance, validated_data)

class ResenaCrearSerializer(serializers.ModelSerializer):
    calificacion = serializers.IntegerField(min_value=1, max_value=5)
    comentario = serializers.CharField(max_length=500)

    class Meta:
        model = Resena
        fields = ['producto', 'calificacion', 'comentario']

    def validate(self, datos):
        pedido = self.context['pedido']

        if (pedido.tipo_pedido != 'normal' or pedido.estado != 'pagado' or pedido.etapa != 'entregado' or pedido.cancelado):
            raise serializers.ValidationError('Solo Puedes Reseñar una Compra Pagada Retirada o Entregada y no Cancelada')

        producto = datos['producto']
        pertenece_al_pedido = DetallePedido.objects.filter(pedido=pedido, producto=producto, cantidad__gt=0,).exists()

        if not pertenece_al_pedido:
            raise serializers.ValidationError('Este Producto no Pertenece a Esta Compra')
        
        if Resena.objects.filter(pedido=pedido, producto=producto).exists():
            raise serializers.ValidationError('Ya Dejaste una Reseña Para Este Producto en Esta Compra')

        return datos

class ResenaPublicaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resena
        fields = [
            'id',
            'calificacion',
            'comentario',
            'fecha_creacion',
        ]

class PreguntaFrecuenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PreguntaFrecuente
        fields = ['id', 'pregunta', 'respuesta']
        
class ConsultaCrearSerializer(serializers.ModelSerializer):
    mensaje = serializers.CharField(allow_blank=False, trim_whitespace=True)

    class Meta:
        model = Consulta
        fields = ["nombre", "correo", "asunto", "mensaje", "es_personalizado", "imagen_referencia", 'tipo_entrega', 
                    'direccion_entrega', 'rut', 'telefono']

        def validate(self, datos):
            if not datos.get('es_personalizado', False):
                datos['rut'] = ''
                datos['telefono'] = ''
                datos['tipo_entrega'] = ''
                datos['direccion_entrega'] = ''
                return datos

            tipo = datos.get('tipo_entrega', '')
            direccion = (datos.get('direccion_entrega') or '').strip()
            errores = {}

            if tipo not in ('retiro', 'envio'):
                errores['tipo_entrega'] = ('Selecciona Retiro en Tienda o Envío a Domicilio')

            if tipo == 'envio' and not direccion:
                errores['direccion_entrega'] = ('Indica la Dirección de Entrega')

            for campo, validador in (('rut', validar_rut_chileno), ('telefono', validar_telefono_chileno)):
                valor = (datos.get(campo) or '').strip()

                if not valor:
                    errores[campo] = ('Este Campo es Obligatorio Para un Pedido Personalizado')
                    continue

                try:
                    datos[campo] = validador(valor)
                except serializers.ValidationError as error:
                    errores[campo] = error.detail

            if errores:
                raise serializers.ValidationError(errores)

            datos['direccion_entrega'] = direccion if tipo == 'envio' else ''
            return datos