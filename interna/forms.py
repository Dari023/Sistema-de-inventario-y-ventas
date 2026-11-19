from django import forms
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import BaseInlineFormSet, BaseFormSet, inlineformset_factory, formset_factory
from .models import (Producto, 
    MateriaPrima, 
    ProductoMateriaPrima, 
    CategoriaProducto, 
    MovimientoMateriaPrima, 
    ConfiguracionPrecio,
    PreguntaFrecuente,
    ProductoVariante,
    DetallePedidoPersonalizado,
    MaterialPedidoPersonalizado,
    Pedido)

class ProductoForm(forms.ModelForm):
    tiempo_fabricacion_minutos = forms.IntegerField(
        label='Tiempo de Trabajo por Unidad (Minutos)',
        required= False,
        min_value=1,
        help_text='Por Ejemplo: 90 Minutos Equivalen a una Hora y Media',
        widget=forms.NumberInput(attrs={'class':'form-control', 'min':'1','step':'1'})
    )

    class Meta:
        model = Producto
        exclude = ["stock_actual"]
        labels = {'descuento_porcentaje': 'Descuento'}
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control'}),
            'descuento_porcentaje': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 99}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-select'})
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["categoria"].queryset = (
        CategoriaProducto.objects.filter(activo=True).order_by("nombre"))
        self.fields["categoria"].empty_label = "Selecciona una Opción"
        self.fields["categoria"].error_messages["invalid_choice"] = (
        "Selecciona una Categoría que se Encuentre Activa."
        )
        if not self.instance.pk:
            self.fields["activo"].initial = False

class ProductoVarianteForm(forms.Form):
    ofrecer = forms.BooleanField(required=False)
    precio = forms.DecimalField(required=False, min_value=1, max_digits=10, decimal_places=0)
    tiempo_minutos = forms.IntegerField(required=False, min_value=1, max_value=2147483647,label='Minutos de confección')
    a_pedido = forms.BooleanField(required=False)

    def clean(self):
        datos = super().clean()

        if datos.get('ofrecer'):
            if 'tiempo_minutos' in datos and datos['tiempo_minutos'] is None:
                self.add_error('tiempo_minutos', 'Ingresa los Minutos de esta Talla')
            if 'precio' in datos and datos['precio'] is None:
                self.add_error('precio', 'Ingresa el Precio de esta Talla')
        elif datos.get('precio') is not None or datos.get('a_pedido') or datos.get('tiempo_minutos') is not None:
            self.add_error('ofrecer', 'Marca esta Talla para Guardarla')

        return datos

class MateriaPrimaForm(forms.ModelForm):
    observacion = forms.CharField(
        label = 'Observación',
        required = False,
        max_length = 300,
        help_text = 'Obligatorio cuando Modificas la Cantidad Actual',
        widget = forms.Textarea(attrs={"rows":3})
    )

    class Meta:
        model = MateriaPrima
        fields = [
            "nombre",
            "cantidad_actual",
            "cantidad_critica",
            "unidad_de_medida",
            "costo_unitario",
            "estado",
            "observacion"
        ]
        labels = {
            "nombre": "Nombre",
            "cantidad_actual": "Cantidad Actual",
            "cantidad_critica": "Cantidad Crítica",
            "unidad_de_medida": "Unidad de Medida",
            "costo_unitario": "Costo por Unidad de Medida",
            "estado": "Activa"
        }

    def clean(self):
        datos = super().clean()

        campos_numericos = [
            "cantidad_actual",
            "cantidad_critica",
            "costo_unitario",
        ]

        for campo in campos_numericos:
            valor = datos.get(campo)

            if valor is not None and valor < 0:
                self.add_error(campo, 'El Valor no Puede ser Negativo')

        cantidad_nueva = datos.get('cantidad_actual')
        if (
            self.instance.pk
            and cantidad_nueva is not None
            and cantidad_nueva != self.instance.cantidad_actual
            and not datos.get('observacion')
        ):
            self.add_error('observacion', 'Explica Por Qué Estas Modificando el Stock')

        return datos

class CategoriaProductoForm(forms.ModelForm):
    class Meta:
        model = CategoriaProducto
        fields = ['nombre', 'imagen', 'activo']
        labels = {
            'nombre': 'Nombre',
            'imagen':'Imagen de la Categoría',
            'activo': 'Activa',
        }
        widgets = {
            'nombre': forms.TextInput(),
            'imagen': forms.ClearableFileInput(attrs={'accept':'image/*'})
        }    

class ProductoMateriaPrimaForm(forms.ModelForm):
    cantidad_requerida = forms.DecimalField(
        label="Cantidad por Producto",
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )

    class Meta:
        model = ProductoMateriaPrima
        fields = ["materia_prima", "cantidad_requerida", "cantidad_s", "cantidad_m", "cantidad_l"]
        labels = {
            "materia_prima": "Materia prima",
        }
        widgets = {
            "materia_prima": forms.Select(
                attrs={"class": "selector-materia"},
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        disponibles = Q(estado=True)

        if self.instance.pk:
            disponibles |= Q(pk=self.instance.materia_prima_id)
            self.fields["materia_prima"].disabled = True

        self.fields["materia_prima"].queryset = (
            MateriaPrima.objects.filter(disponibles).order_by("nombre")
        )
        self.fields["materia_prima"].empty_label = "Selecciona un material"

class BaseMaterialesFormSet(BaseInlineFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)
        form.fields["DELETE"].label = "Quitar esta Asociación"

    def clean(self):
        super().clean()

        if any(self.errors):
            return

        materiales = [
            formulario.cleaned_data["materia_prima"]
            for formulario in self.forms
            if formulario.cleaned_data.get("materia_prima")
            and not formulario.cleaned_data.get("DELETE")
        ]

        if self.instance.activo and not materiales:
            raise ValidationError(
                "Asocia Materiales o Guarda el Producto Deshabilitado."
            )

ProductoMateriaPrimaFormSet = inlineformset_factory(
    Producto,
    ProductoMateriaPrima,
    form=ProductoMateriaPrimaForm,
    formset=BaseMaterialesFormSet,
    extra=1,
    can_delete=True,
)

class FabricacionForm(forms.Form):
    cantidad = forms.IntegerField(
        label="Unidades Fabricadas",
        min_value=1
    )
    variante = forms.ModelChoiceField(
    queryset=ProductoVariante.objects.none(),
    required=False,
    label='Talla a Fabricar',
    empty_label='Selecciona una Talla'
    )

class MovimientoObservacionForm(forms.ModelForm):
    class Meta:
        model = MovimientoMateriaPrima
        fields = ["observacion"]
        labels = {"observacion": "Observación",}
        widgets = {
            "observacion": forms.Textarea(
                attrs={"rows": 4}
            ),
        }

    def clean_observacion(self):
        observacion = self.cleaned_data["observacion"]

        if self.instance.motivo == "AJUSTE" and not observacion:
            raise forms.ValidationError(
                "Los Ajustes deben Conservar una Explicación."
            )
        return observacion

class TiempoPrecioForm(forms.Form):
    tiempo_fabricacion_minutos = forms.IntegerField(
        min_value=1,
        label='Tiempo de Trabajo por Unidad'
    )

class MaterialPrecioForm(forms.Form):
    materia_prima = forms.ModelChoiceField(
        queryset=MateriaPrima.objects.filter(estado=True),
        label='Materia prima',
        error_messages={
            'invalid_choice': 'Selecciona una Materia Prima que se Encuentre Activa'
        }
    )
    cantidad_requerida = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal('0.01'),
        label='Cantidad Requerida'
    )

class BasePrecioMaterialesFormSet(BaseFormSet):
    default_error_messages = {
        'too_few_forms': (
            'Agrega al menos una materia prima para calcular el precio sugerido'
        ),
    }

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        identificadores = set()
        for formulario in self.forms:
            datos = formulario.cleaned_data
            if not datos or datos.get("DELETE"):
                continue
            materia = datos.get("materia_prima")
            if materia is None:
                continue
            if materia.pk in identificadores:
                raise forms.ValidationError('No Repitas una Materia Prima en la Receta')
            identificadores.add(materia.pk)

PrecioMaterialesFormSet = formset_factory(
    MaterialPrecioForm,
    formset=BasePrecioMaterialesFormSet,
    extra=0,
    can_delete=True,
    min_num=1,
    validate_min=True,
)

class ConfiguracionPrecioForm(forms.ModelForm):
    class Meta:
        model = ConfiguracionPrecio
        fields = [
            'costo_hora', 'costo_bolsa', 'costo_stickers', 'margen_ganancia',
            'porcentaje_iva', 'porcentaje_comision', 'comision_afecta_iva'
        ]
        labels = {
            'costo_hora': 'Costo por hora de trabajo',
            'costo_bolsa': 'Bolsa por producto',
            'costo_stickers': 'Stickers por producto',
            'margen_ganancia': 'Margen sobre el precio sin IVA',
            'porcentaje_iva': 'IVA',
            'porcentaje_comision': 'Comisión del medio de pago',
            'comision_afecta_iva': 'La comisión está afecta a IVA'
        }
        help_texts = {
            'costo_bolsa': 'Usa 0 si este costo ya está incluido en la receta',
            'costo_stickers': 'Usa 0 si este costo ya está incluido en la receta',
            'porcentaje_comision': 'Ingresa la comisión real de tu medio de pago'
        }

class PreguntaFrecuenteForm(forms.ModelForm):
    class Meta:
        model = PreguntaFrecuente

        fields = [
            'pregunta',
            'respuesta',
            'orden',
            'activo',
        ]

        labels = {
            'pregunta': 'Pregunta',
            'respuesta': 'Respuesta',
            'orden': 'Orden de aparición',
            'activo': 'Activa'
        }

        help_texts = {
            'orden': 'Los números menores aparecen primero'
        }

        widgets = {
            'respuesta': forms.Textarea(attrs={'rows': 6})
        }

class PedidoPersonalizadoForm(forms.ModelForm):
    nombre_invitado = forms.CharField(label='Nombre de Contacto', max_length=150)
    email_invitado = forms.EmailField(label='Correo de Contacto')
    telefono_invitado = forms.CharField(label='Teléfono de contacto', max_length=20)
    adelanto_requerido = forms.DecimalField(label='Adelanto requerido (CLP)', max_digits=10, decimal_places=0, min_value=1)
    fecha_compromiso = forms.DateField(label='Fecha Acordada de Entrega', widget=forms.DateInput(
            format="%Y-%m-%d",
            attrs={"type": "date"}
        )
    )

    class Meta:
        model = Pedido
        fields = [
            'nombre_invitado',
            'rut_invitado',
            'email_invitado',
            'telefono_invitado',
            'tipo_entrega',
            'direccion_invitado',
            'fecha_compromiso',
            'adelanto_requerido'
        ]
        labels = {
            'rut_invitado': 'RUT',
            'tipo_entrega': 'Tipo de Entrega',
            'direccion_invitado': 'Dirección de Entrega'
        }

    def clean(self):
        datos = super().clean()
        direccion = (datos.get('direccion_invitado') or '').strip()

        if datos.get('tipo_entrega') == 'envio':
            if not direccion:
                self.add_error('direccion_invitado', 'Indica la Dirección de Envío')
        else:
            direccion = None

        datos['direccion_invitado'] = direccion
        return datos

class DetallePedidoPersonalizadoForm(forms.ModelForm):
    class Meta:
        model = DetallePedidoPersonalizado
        fields = [
            'descripcion',
            'imagen_referencia',
            'cantidad',
            'precio_unitario'
        ]
        labels = {
            'descripcion': 'Descripción y Características Acordadas',
            'imagen_referencia': 'Imagen de Referencia',
            'cantidad': 'Unidades Encargadas',
            'precio_unitario': 'Precio Acordado por Unidad (CLP)'
        }
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4})
        }

class MaterialPedidoPersonalizadoForm(forms.ModelForm):
    materia_prima = forms.ModelChoiceField(label='Materia Prima', queryset=MateriaPrima.objects.filter(estado=True,).order_by('nombre'))

    class Meta:
        model = MaterialPedidoPersonalizado
        fields = ['materia_prima', 'cantidad_por_unidad']
        labels = {
            'cantidad_por_unidad': 'Cantidad Necesaria por Unidad'
        }

MaterialPedidoPersonalizadoFormSet = inlineformset_factory(
    DetallePedidoPersonalizado,
    MaterialPedidoPersonalizado,
    form=MaterialPedidoPersonalizadoForm,
    extra=0,
    min_num=1,
    validate_min=True,
    can_delete=True
)

class BaseArticulosPedidoPersonalizadoFormSet(BaseInlineFormSet):
    def add_fields(self, form, index):
        super().add_fields(form, index)

        form.fields['DELETE'].label = 'Quitar este Artículo'

        datos = self.data if form.is_bound else None
        archivos = self.files if form.is_bound else None

        form.materiales = MaterialPedidoPersonalizadoFormSet(datos, archivos, instance=form.instance, prefix=f"{form.prefix}-materiales")

        for fila_material in form.materiales.forms:
            fila_material.fields['DELETE'].label = 'Quitar este Material'

ArticulosPedidoPersonalizadoFormSet = inlineformset_factory(
    Pedido,
    DetallePedidoPersonalizado,
    form=DetallePedidoPersonalizadoForm,
    formset=BaseArticulosPedidoPersonalizadoFormSet,
    extra=0,
    min_num=1,
    validate_min=True,
    can_delete=True,
)