from django.db import models
from django.contrib.auth.models import User
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from api.models import Cliente
from decimal import Decimal, ROUND_HALF_UP
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
    cantidad_actual = models.DecimalField(max_digits=10, decimal_places=3, default=0, editable=False)
    cantidad_critica = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    unidad_de_medida = models.CharField(max_length=20, choices=UNIDADES_MEDIDA, default='UN')
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    estado = models.BooleanField(default=True)

    class Meta:
        permissions = [
            ('registrar_baja_materiaprima', 'Puede Registrar Bajas de Materias Primas'),
            ('ajustar_stock_materiaprima', 'Puede Registrar Stock Inicial y Ajustes de Materias Primas')
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad_actual__gte=0), name='mp_stock_no_negativo')
        ]

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
        ("PERDIDA", "Baja por Pérdida o Daño"),
        ("DANO", "Daño"),
        ("AJUSTE", "Ajuste de Inventario")
    ]

    materia_prima = models.ForeignKey(MateriaPrima, on_delete=models.PROTECT, related_name="movimientos")
    fecha = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=10, choices=TIPOS)
    motivo = models.CharField(max_length=20, choices=MOTIVOS)
    orden_compra = models.ForeignKey('OrdenCompra', on_delete=models.PROTECT, null=True, blank=True, related_name='movimientos')
    cantidad = models.DecimalField(max_digits=10, decimal_places=3)
    saldo_resultante = models.DecimalField(max_digits=10, decimal_places=3 )
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    observacion = models.CharField(max_length=300, blank=True)
    fabricacion_personalizada = models.ForeignKey('FabricacionPedidoPersonalizado', on_delete=models.PROTECT, null=True, blank=True, related_name='movimientos')

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
    descuento_porcentaje = models.IntegerField(default=0, validators=[MinValueValidator(0), MaxValueValidator(99)])
    tiempo_fabricacion_minutos = models.PositiveIntegerField(null=True, blank=True, verbose_name='Tiempo de Trabajo por Unidad (Minutos)')
    admite_personalizacion = models.BooleanField('Admite personalización', default=False)

    def aplicar_descuento(self, precio):
        monto = precio * (100 - self.descuento_porcentaje) / Decimal("100")
        return monto.quantize(Decimal("1"), rounding=ROUND_HALF_UP)

    @property
    def precio_final(self):
        return self.aplicar_descuento(self.precio)

    @property
    def stock_para_mostrar(self):
        variantes = list(self.variantes.all())
        if variantes:
            return sum(variante.stock_actual for variante in variantes)
        return self.stock_actual

    class Meta:
        permissions = [('fabricar_producto', 'Puede registrar fabricación')]

    def __str__(self):
        return self.nombre

class ProductoVariante(models.Model):
    TALLAS = [('S', 'S'), ('M', 'M'), ('L', 'L')]

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name='variantes')
    talla = models.CharField(max_length=1, choices=TALLAS)
    precio = models.DecimalField('Precio de venta', max_digits=10, decimal_places=0, validators=[MinValueValidator(1)])
    stock_actual = models.PositiveIntegerField(default=0)
    a_pedido = models.BooleanField('A pedido', default=False)
    tiempo_minutos = models.PositiveIntegerField('Minutos de confección', null=True, blank=True, validators=[MinValueValidator(1)])

    class Meta:
        constraints = [models.UniqueConstraint(fields=['producto', 'talla'], name='producto_talla_unica')]

    @property
    def precio_final(self):
        return self.producto.aplicar_descuento(self.precio)

    def __str__(self):
        return f"{self.producto.nombre} · Talla {self.talla}"

class ProductoMateriaPrima(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    materia_prima = models.ForeignKey(MateriaPrima, on_delete=models.CASCADE)
    cantidad_requerida = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    cantidad_s = models.DecimalField('Cantidad S', max_digits=10, decimal_places=2, null=True, blank=True, 
    validators=[MinValueValidator(Decimal('0.01'))])
    cantidad_m = models.DecimalField('Cantidad M', max_digits=10, decimal_places=2, null=True, blank=True, 
    validators=[MinValueValidator(Decimal('0.01'))])
    cantidad_l = models.DecimalField('Cantidad L', max_digits=10, decimal_places=2,null=True, blank=True, 
    validators=[MinValueValidator(Decimal('0.01'))])

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
    estado = models.CharField(max_length=20,  choices=[('pendiente', 'Pendiente'), ('pagado', 'Pagado')], default='pendiente')
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    nombre_invitado = models.CharField(max_length=150, null=True, blank=True)
    rut_invitado = models.CharField(max_length=12, null=True, blank=True)
    email_invitado = models.EmailField(null=True, blank=True)
    telefono_invitado = models.CharField(max_length=20, null=True, blank=True)
    direccion_invitado = models.CharField(max_length=200, null=True, blank=True)
    consulta_origen = models.OneToOneField('interna.Consulta', on_delete=models.SET_NULL, null=True, blank=True, editable=False, related_name='pedido_personalizado')

    TIPOS_ENTREGA = [
        ('envio',  'Envío a domicilio'),
        ('retiro', 'Retiro en tienda'),
    ]
    tipo_entrega = models.CharField(max_length=10, choices=TIPOS_ENTREGA, default='retiro')
    ETAPAS = [
        ('en_confeccion', 'En confección'),
        ('listo', 'Listo'),
        ('enviado', 'Enviado'),
        ('disponible_retiro', 'Disponible para retiro'),
        ('entregado', 'Entregado'),
    ]
    etapa = models.CharField(max_length=20, choices=ETAPAS, null=True, blank=True, verbose_name='Etapa de preparación')

    TIPOS_PEDIDO = [
        ('normal', 'Compra de Catálogo'),
        ('personalizado', 'Pedido Personalizado'),
    ]

    tipo_pedido = models.CharField(max_length=20, choices=TIPOS_PEDIDO, default='normal')
    adelanto_requerido = models.DecimalField(max_digits=10, decimal_places=0, default=0, validators=[MinValueValidator(Decimal('0'))])
    fecha_compromiso = models.DateField('Fecha acordada de entrega', null=True, blank=True)
    cancelado = models.BooleanField(default=False, editable=False)
    fecha_cancelacion = models.DateTimeField(null=True, blank=True, editable=False)
    cancelado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, editable=False, related_name='pedidos_cancelados')
    motivo_cancelacion = models.TextField(default='', blank=True, editable=False)

    class Meta:
        permissions = [('cancelar_pedido', 'Puede cancelar pedidos personalizados')]

    @property
    def total(self):
        if self.tipo_pedido == 'personalizado':
            return sum((detalle.subtotal for detalle in self.detalles_personalizados.all()), Decimal('0'))
                
        return sum((detalle.subtotal for detalle in self.detallepedido_set.all()), Decimal('0'))

    def __str__(self):
        return f"Pedido {self.id} - {self.cliente or self.nombre_invitado or 'Invitado'}"

class PagoPedido(models.Model):
    METODOS = [('transferencia', 'Transferencia Bancaria'), ('webpay', 'Webpay')]
    ESTADOS = [('pendiente', 'Pendiente'), ('en_revision', 'Comprobante en Revisión'), ('aprobado', 'Aprobado'), ('rechazado', 'Rechazado')]

    pedido = models.ForeignKey(Pedido, on_delete=models.PROTECT, related_name='pagos')
    metodo = models.CharField(max_length=20, choices=METODOS)
    monto = models.DecimalField(max_digits=10, decimal_places=0, validators=[MinValueValidator(Decimal('1'))])
    estado = models.CharField(max_length=20, choices=ESTADOS, default='pendiente')
    comprobante = models.FileField(upload_to="comprobantes_pedidos/", max_length=255, blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])]
    )

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    revisado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='pagos_pedidos_revisados')
    fecha_revision = models.DateTimeField(null=True, blank=True)
    observacion = models.TextField(blank=True)
    orden_webpay = models.CharField(max_length=26, unique=True, null=True, blank=True, editable=False)
    token_webpay = models.CharField(max_length=64, unique=True, null=True, blank=True, editable=False)

    class Meta:
        ordering = ['-fecha_creacion', '-pk']
        permissions = [('validar_transferencia','Puede Aprobar o Rechazar Transferencias de Pedidos')]
        constraints = [models.CheckConstraint(condition=models.Q(monto__gt=0), name='pago_pedido_monto_positivo')]

    def __str__(self):
        return (f"Pago {self.pk} - Pedido {self.pedido_id} " f"- {self.get_estado_display()}")

class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    variante = models.ForeignKey('ProductoVariante', on_delete=models.PROTECT, null=True, blank=True)
    cantidad = models.PositiveIntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=0, null=True, blank=True)

    @property
    def precio_vigente(self):
        if self.variante_id is not None:
            return self.variante.precio_final
        return self.producto.precio_final

    @property
    def subtotal(self):
        precio = self.precio_unitario

        if precio is None:
            precio = self.producto.precio

        return precio * self.cantidad

class HistorialEtapaPedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='historial_etapas')
    etapa = models.CharField(max_length=20, choices=Pedido.ETAPAS)
    fecha = models.DateTimeField(auto_now_add=True)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-fecha']

    def __str__(self):
        return f"Pedido {self.pedido.id} - {self.etapa}"
    
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
        constraints = [models.CheckConstraint(condition=models.Q(id=1), name='configuracion_precio_unica')]

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
    
class Consulta(models.Model):
    ESTADOS = [("pendiente", "Pendiente"), ("respondida", "Respondida")]

    cliente = models.ForeignKey(Cliente, on_delete=models.SET_NULL, null=True, blank=True, related_name="consultas")
    nombre = models.CharField(max_length=150)
    correo = models.EmailField()
    asunto = models.CharField(max_length=150)
    mensaje = models.TextField()
    es_personalizado = models.BooleanField(default=False)
    imagen_referencia = models.ImageField(upload_to="consultas/", blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    tipo_entrega = models.CharField(max_length=10, choices=[('retiro', 'Retiro en tienda'), ('envio', 'Envío a domicilio')], blank=True, default='')
    direccion_entrega = models.CharField(max_length=200, blank=True, default='')
    rut = models.CharField(max_length=12, blank=True, default='')
    telefono = models.CharField(max_length=20, blank=True, default='')

    class Meta:
        ordering = ["-fecha", "-pk"]
        verbose_name = "Consulta"
        verbose_name_plural = "Consultas"

    def __str__(self):
        return f"{self.nombre} - {self.asunto}"

class RespuestaConsulta(models.Model):
    consulta = models.ForeignKey(Consulta, on_delete=models.PROTECT, related_name='respuestas')
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='respuestas_consultas')
    correo_destino = models.EmailField()
    asunto = models.CharField(max_length=200)
    mensaje = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    fecha_envio = models.DateTimeField(null=True, blank=True)

    estado = models.CharField(
        max_length=10,
        choices=[('pendiente', 'Pendiente de Envío'), ('enviada', 'Enviada'), ('error', 'Envío no Confirmado')],
        default='pendiente'
    )
    clave_envio = models.UUIDField(default=uuid.uuid4, unique=True, editable=False,)

    class Meta:
        ordering = ['-fecha', '-pk']

class DetallePedidoPersonalizado(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles_personalizados')
    descripcion = models.TextField('Descripción del Encargo')
    imagen_referencia = models.ImageField(upload_to='pedidos_personalizados/', blank=True)
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.DecimalField('Precio acordado por unidad', max_digits=10, decimal_places=0, validators=[MinValueValidator((1))])
    unidades_fabricadas = models.PositiveIntegerField(default=0, editable=False)

    @property
    def subtotal(self):
        return self.precio_unitario * self.cantidad

    @property
    def unidades_pendientes(self):
        return self.cantidad - self.unidades_fabricadas

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name='detalle_personalizado_cantidad_positiva'),
            models.CheckConstraint(condition=models.Q(precio_unitario__gt=0), name='detalle_personalizado_precio_positivo'),
            models.CheckConstraint(
                condition=(
                    models.Q(unidades_fabricadas__gte=0)
                    & models.Q(
                        unidades_fabricadas__lte=models.F('cantidad'),
                    )
                ),
                name='detalle_personalizado_fabricadas_validas',
            )
        ]

    def __str__(self):
        return f"Encargo {self.pk} - Pedido {self.pedido_id}"

class MaterialPedidoPersonalizado(models.Model):
    detalle = models.ForeignKey(DetallePedidoPersonalizado, on_delete=models.CASCADE, related_name='materiales')
    materia_prima = models.ForeignKey(MateriaPrima, on_delete=models.PROTECT)
    cantidad_por_unidad = models.DecimalField(max_digits=10, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['detalle', 'materia_prima'], name='material_unico_por_encargo'),
            models.CheckConstraint(condition=models.Q(cantidad_por_unidad__gt=0), name='material_encargo_cantidad_positiva')
        ]

    def __str__(self):
        return f"{self.materia_prima.nombre} - Encargo {self.detalle_id}"

class FabricacionPedidoPersonalizado(models.Model):
    detalle = models.ForeignKey(DetallePedidoPersonalizado, on_delete=models.PROTECT, related_name='fabricaciones')
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    fecha = models.DateTimeField(auto_now_add=True)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ['-fecha', '-pk']
        constraints = [models.CheckConstraint(condition=models.Q(cantidad__gt=0), name='fabricacion_encargo_cantidad_positiva')]

    def __str__(self):
        return f"Fabricación {self.pk} - Encargo {self.detalle_id}"

class Proveedor(models.Model):
    nombre = models.CharField(max_length=150)
    rut = models.CharField(max_length=12, unique=True)
    contacto = models.CharField(max_length=100, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ['nombre', 'pk']

    def __str__(self):
        return self.nombre

class OrdenCompra(models.Model):
    ESTADOS = [('pendiente', 'Pendiente de Recepción'), ('recibida', 'Recibida'), ('cancelada', 'Cancelada')]
    DOCUMENTOS = [('FACTURA', 'Factura'), ('BOLETA', 'Boleta'), ('OTRO', 'Otro')]

    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='ordenes')
    tipo_documento = models.CharField(max_length=10, choices=DOCUMENTOS, default='FACTURA')
    numero_documento = models.CharField(max_length=40, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)
    responsable = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='ordenes_compra')
    estado = models.CharField( max_length=10, choices=ESTADOS, default='pendiente', editable=False)
    observacion = models.CharField(max_length=300, blank=True)
    fecha_gestion = models.DateTimeField(null=True, blank=True, editable=False)
    gestionado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='+', editable=False)
    motivo_cancelacion = models.CharField( max_length=300, blank=True, editable=False)

    class Meta:
        ordering = ['-fecha', '-pk']
        permissions = [
            ('recibir_ordencompra', 'Puede Confirmar Recepción de Órdenes de Compra'),
            ('cancelar_ordencompra', 'Puede Cancelar Órdenes de Compra Pendientes')
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['proveedor', 'tipo_documento', 'numero_documento'],
                condition=(~models.Q(numero_documento='') & ~models.Q(estado='cancelada')),
                name='oc_documento_proveedor_unico'
            )
        ]

    @property
    def total(self):
        return sum((fila.subtotal for fila in self.detalles.all()), Decimal('0'))

    def __str__(self):
        return f'OC-{self.pk}'

class DetalleOrdenCompra(models.Model):
    orden = models.ForeignKey(OrdenCompra, on_delete=models.CASCADE, related_name='detalles')
    materia_prima = models.ForeignKey(MateriaPrima, on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=10, decimal_places=3, validators=[MinValueValidator(Decimal('0.001'))])
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    unidad = models.CharField(max_length=20, editable=False)

    @property
    def subtotal(self):
        return (self.cantidad * self.costo_unitario).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['orden', 'materia_prima'], name='oc_material_unico'),
            models.CheckConstraint(condition=models.Q(cantidad__gt=0), name='oc_cantidad_positiva'),
            models.CheckConstraint(condition=models.Q(costo_unitario__gt=0), name='oc_costo_positivo')
        ]