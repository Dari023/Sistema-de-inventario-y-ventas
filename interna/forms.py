from django import forms
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.forms import BaseInlineFormSet, inlineformset_factory
from .models import Producto, MateriaPrima, ProductoMateriaPrima, CategoriaProducto

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        exclude = ["stock_actual"]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'precio': forms.NumberInput(attrs={'class': 'form-control'}),
            'descripcion': forms.Textarea(attrs={'class': 'form-control'}),
            'imagen': forms.FileInput(attrs={'class': 'form-control'}),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["categoria"].queryset = (
        CategoriaProducto.objects
        .filter(activo=True)
        .order_by("nombre")
        )
        self.fields["categoria"].empty_label = "Selecciona una Opción"
        self.fields["categoria"].error_messages["invalid_choice"] = (
        "Selecciona una Categoría que se Encuentre Activa."
        )
        if not self.instance.pk:
            self.fields["activo"].initial = False

class MateriaPrimaForm(forms.ModelForm):
    class Meta:
        model = MateriaPrima
        fields = [
            "nombre",
            "cantidad_actual",
            "cantidad_critica",
            "unidad_de_medida",
            "costo_unitario",
            "estado"
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
                self.add_error(
                    campo,
                    "El Valor no Puede ser Negativo.",
                )

        return datos

class CategoriaProductoForm(forms.ModelForm):
    class Meta:
        model = CategoriaProducto
        fields = ['nombre', 'activo']
        labels = {
            'nombre': 'Nombre',
            'activo': 'Activa',
        }
        widgets = {
            'nombre': forms.TextInput(),
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
        fields = ["materia_prima", "cantidad_requerida"]
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

        if self.instance.activo:
            if not materiales:
                raise ValidationError(
                    "Asocia Materiales o Guarda el Producto Deshabilitado."
                )

            if any(not material.estado for material in materiales):
                raise ValidationError(
                    "Un Producto Activo Necesita Materias Primas Habilitadas."
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
        label="Unidades fabricadas",
        min_value=1,
    )