from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class CategoriaProducto(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    descripcion = models.CharField(max_length=300, blank=True, null=True)
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
    
class Producto(models.Model):
    categoria = models.ForeignKey(CategoriaProducto, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100)
    precio = models.DecimalField(max_digits=10, decimal_places=0)
    descripcion = models.CharField(max_length=500)
    imagen = models.ImageField(upload_to="media/productos")
    activo = models.BooleanField(default=True)
    stock_actual = models.IntegerField()
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
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
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
        return f"Pedido {self.id} - {self.usuario.username}"

class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)

    @property
    def subtotal(self):
        precio = self.precio_unitario or self.producto.precio
        return precio * self.cantidad