from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
import uuid
from api.models import Cliente
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

    @property
    def total(self):
        return sum(item.subtotal for item in self.detallepedido_set.all())

    def __str__(self):
        return f"Pedido {self.id} - {self.cliente}"

class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)

    @property
    def subtotal(self):
        precio = self.precio_unitario or self.producto.precio
        return precio * self.cantidad