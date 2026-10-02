from django import forms
from .models import Producto, MateriaPrima, ProductoMateriaPrima, CategoriaProducto

class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = '__all__'
        
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
    class Meta:
        model = ProductoMateriaPrima
        fields = ["materia_prima", "cantidad_requerida"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["materia_prima"].queryset = (
            MateriaPrima.objects.filter(estado=True)
        )

    def clean_cantidad_requerida(self):
        cantidad = self.cleaned_data["cantidad_requerida"]

        if cantidad <= 0:
            raise forms.ValidationError(
                "La Cantidad Requerida debe ser Mayor que Cero."
            )
        return cantidad