from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from api.models import Cliente
from decimal import Decimal
import uuid
# Create your models here.

class CategoriaProducto(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(max_length=300, blank=True, null=True)
    imagen = models.ImageField(upload_to="media/productos", blank=True)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return self.nombre

class MateriaPrima(models.Model):
    UNIDADES_MEDIDA = [
        ('KG', 'Kilogramos'),
        ('G', 'Gramos'),
        ('M', 'Metros'),
        ('CM', 'Centímetros'),
        ('UN', 'Unidad'),
    ]

    nombre = models.CharField(max_length=100)
    cantidad_actual = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    cantidad_critica = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    unidad_de_medida = models.CharField(max_length=20, choices=UNIDADES_MEDIDA, default='UN')
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.nombre} ({self.cantidad_actual} {self.unidad_de_medida})"

class MovimientoMateriaPrima(models.Model):
    TIPOS = [
        ("ENTRADA", "Entrada"),
        ("SALIDA", "Salida")
    ]

    MOTIVOS = [
        ("INICIAL", "Stock Inicial"),
        ("COMPRA", "Compra"),
        ("FABRICACION", "Fabricación"),
        ("PERDIDA", "Pérdida"),
        ("AJUSTE", "Ajuste de Inventario")
    ]

    materia_prima = models.ForeignKey(MateriaPrima, on_delete=models.PROTECT, related_name="movimientos")
    fecha = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=10, choices=TIPOS)
    motivo = models.CharField(max_length=20, choices=MOTIVOS)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    saldo_resultante = models.DecimalField(max_digits=10, decimal_places=3 )
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    observacion = models.CharField(max_length=300, blank=True)

    class Meta:
        ordering = ["-fecha", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0),
                name="mov_mp_cantidad_positiva"
            ),
            models.CheckConstraint(
                condition=models.Q(saldo_resultante__gte=0),
                name="mov_mp_saldo_no_negativo"
            )
        ]

    def __str__(self):
        return(
            f"{self.get_tipo_display()} - "
            f"{self.materia_prima.nombre}: {self.cantidad}"
        )
    
class Producto(models.Model):
    categoria = models.ForeignKey(CategoriaProducto, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=0)
    descripcion = models.CharField(max_length=500)
    imagen = models.ImageField(upload_to="media/productos")
    activo = models.BooleanField(default=True)
    stock_actual = models.IntegerField(default=0)
    stock_critico = models.IntegerField()
    modalidad_de_venta = models.CharField(max_length=20)

    tiempo_fabricacion_minutos = models.PositiveIntegerField(null=True, blank=True, verbose_name='Tiempo de Trabajo por Unidad' \
    '(Minutos)')

    def __str__(self):
        return self.nombre

class ProductoMateriaPrima(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    materia_prima = models.ForeignKey(MateriaPrima, on_delete=models.CASCADE)
    cantidad_requerida = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.producto.nombre} - {self.materia_prima.nombre}"

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["producto", "materia_prima"],
                name = "producto_materia_prima_unica"
            )
        ]

class Pedido(models.Model):
    id_compra = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='pedidos', null=True)
    fecha_pedido = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(
        max_length=20, 
        choices=[('pendiente', 'Pendiente'), ('pagado', 'Pagado')], 
        default='pendiente'
    )

    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    nombre_invitado = models.CharField(max_length=150, null=True, blank=True)
    rut_invitado = models.CharField(max_length=12, null=True, blank=True)
    email_invitado = models.EmailField(null=True, blank=True)
    telefono_invitado = models.CharField(max_length=20, null=True, blank=True)
    direccion_invitado = models.CharField(max_length=200, null=True, blank=True)
    TIPOS_ENTREGA = [
        ('envio',  'Envío a domicilio'),
        ('retiro', 'Retiro en tienda'),
    ]
    tipo_entrega = models.CharField(max_length=10, choices=TIPOS_ENTREGA, default='retiro')

    @property
    def total(self):
        return sum(item.subtotal for item in self.detallepedido_set.all())

    def __str__(self):
        return f"Pedido {self.id} - {self.cliente or self.nombre_invitado or 'Invitado'}"

class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)

    @property
    def subtotal(self):
        precio = self.precio_unitario or self.producto.precio
        return precio * self.cantidad

class ConfiguracionPrecio(models.Model):
    id = models.PositiveSmallIntegerField(primary_key=True, default=1, editable=False)
    costo_hora = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('3500.00'), 
                                    validators=[MinValueValidator(Decimal('0'))])
    costo_bolsa = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('50.00'), 
                                    validators=[MinValueValidator(Decimal('0'))])
    costo_stickers = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('50.00'), 
                                    validators=[MinValueValidator(Decimal('0'))])
    margen_ganancia = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('30.00'), 
                                        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('99.99'))])
    porcentaje_iva = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('19.00'), 
                                        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))])
    porcentaje_comision = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'), 
                                        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('99.99'))])
    comision_afecta_iva = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(id=1), name='configuracion_precio_unica')
        ]

    def __str__(self):
        return 'Configuración General de Precios'

class Resena(models.Model):
    pedido = models.ForeignKey('Pedido', on_delete=models.PROTECT, related_name='resenas')
    producto = models.ForeignKey('Producto', on_delete=models.PROTECT, related_name='resenas')
    calificacion = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comentario = models.CharField(max_length=500)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['-fecha_creacion', '-pk']
        constraints = [
            models.UniqueConstraint(fields=['pedido', 'producto'], name='resena_unica_producto_pedido'),
            models.CheckConstraint(
                condition=models.Q(
                    calificacion__gte=1,
                    calificacion__lte=5,
                ),
                name='resena_calificacion_1_a_5'
            )
        ]

    def __str__(self):
        return (
            f"{self.producto.nombre} — "
            f"{self.calificacion}/5 — Pedido {self.pedido_id}"
        )

class PreguntaFrecuente(models.Model):
    pregunta = models.CharField(max_length=250)
    respuesta = models.TextField(max_length=3000)
    orden = models.PositiveIntegerField(default=1)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['orden', 'pk']

    def __str__(self):
        return self.pregunta