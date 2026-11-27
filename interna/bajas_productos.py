from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core import signing
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import OperationalError, transaction
from django.db.models import F
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from .models import BajaProducto, Producto, ProductoVariante

class BajaProductoForm(forms.Form):
    variante = forms.ModelChoiceField(queryset=ProductoVariante.objects.none(), required=False, label='Talla')
    cantidad = forms.IntegerField(min_value=1, label='Cantidad a Dar de Baja')
    motivo = forms.CharField(max_length=300, widget=forms.Textarea(attrs={'rows': 3}))
    stock_esperado = forms.CharField(widget=forms.HiddenInput)

    def __init__(self, *args, producto, **kwargs):
        super().__init__(*args, **kwargs)
        self.producto = producto

        variantes = producto.variantes.order_by('talla')
        self.fields['variante'].queryset = variantes
        self.fields['variante'].required = variantes.exists()

        if not self.fields['variante'].required:
            self.fields['variante'].widget = forms.HiddenInput()

        stocks = {'general': producto.stock_actual}
        stocks.update({
            str(variante.pk): variante.stock_actual
            for variante in variantes
        })

        self.fields['stock_esperado'].initial = signing.dumps({'producto': producto.pk, 'stocks': stocks}, salt='baja-producto-stock')

        for campo in self.fields.values():
            if not campo.widget.is_hidden:
                campo.widget.attrs['class'] = (
                    'form-select'
                    if isinstance(campo.widget, forms.Select)
                    else 'form-control'
                )

    def clean(self):
        datos = super().clean()

        if self.errors:
            return datos

        try:
            original = signing.loads(datos['stock_esperado'], salt='baja-producto-stock', max_age=3600)

            if original['producto'] != self.producto.pk:
                raise ValueError

            variante = datos.get('variante')
            clave = str(variante.pk) if variante is not None else 'general'
            datos['stock_esperado'] = original['stocks'][clave]

        except (signing.BadSignature, KeyError, TypeError, ValueError):
            raise forms.ValidationError('Abre Nuevamente el Formulario Para Revisar el Stock')

        return datos

@transaction.atomic
def registrar_baja_producto(pk, datos, responsable):
    if not responsable.has_perm('interna.registrar_baja_producto'):
        raise PermissionDenied

    cantidad = datos['cantidad']
    motivo = datos['motivo'].strip()

    if type(cantidad) is not int or cantidad <= 0:
        raise ValidationError('La Cantidad Debe ser un Entero Mayor que Cero')

    if not 1 <= len(motivo) <= 300:
        raise ValidationError('Indica un Motivo de Hasta 300 Caracteres')

    producto = get_object_or_404(Producto.objects.select_for_update(), pk=pk)

    variante = datos.get('variante')

    if variante is not None:
        variante = (producto.variantes.select_for_update()
            .filter(pk=variante.pk)
            .first()
        )

        if variante is None:
            raise ValidationError('La Talla Seleccionada no Pertenece a Este Producto')

        inventario = ProductoVariante.objects.filter(pk=variante.pk, producto=producto)
        anterior = variante.stock_actual

    else:
        if producto.variantes.exists():
            raise ValidationError('Selecciona la Talla que Darás de Baja')

        inventario = Producto.objects.filter(pk=producto.pk)
        anterior = producto.stock_actual

    if anterior != datos['stock_esperado']:
        raise ValidationError('El Stock Cambió, Abre Nuevamente el Formulario Antes de Continuar')

    if cantidad > anterior:
        raise ValidationError('La Cantidad Supera el Stock Disponible')

    actualizado = inventario.filter(stock_actual=anterior, stock_actual__gte=cantidad).update(stock_actual=F('stock_actual') - cantidad)

    if not actualizado:
        raise ValidationError('El Stock Cambió, Abre Nuevamente el Formulario Antes de Continuar')

    return BajaProducto.objects.create(
        producto=producto,
        variante=variante,
        cantidad=cantidad,
        motivo=motivo,
        stock_anterior=anterior,
        saldo_resultante=anterior - cantidad,
        responsable=responsable,
    )

@login_required
@permission_required('interna.view_producto', raise_exception=True)
@require_http_methods(['GET', 'POST'])
def producto_baja(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    puede_registrar = request.user.has_perm('interna.registrar_baja_producto')

    if request.method == 'POST' and not puede_registrar:
        raise PermissionDenied

    form = (BajaProductoForm(request.POST if request.method == 'POST' else None, producto=producto)
        if puede_registrar
        else None
    )

    if request.method == 'POST' and form.is_valid():
        try:
            registrar_baja_producto(producto.pk, form.cleaned_data, request.user)

        except ValidationError as error:
            form.add_error(None, error)

        except OperationalError as error:
            if 'locked' not in str(error).lower():
                raise

            form.add_error(None,'El Stock Está Siendo Actualizado, Abre Nuevamente el Formulario')

        else:
            messages.success(request, 'Baja Registrada y Stock Actualizado')
            return redirect('producto_baja', pk=producto.pk)

    return render(request, 'interna/producto/producto_baja.html',
        {
            'producto': producto,
            'form': form,
            'variantes': producto.variantes.order_by('talla'),
            'bajas': producto.bajas.select_related(
                'variante',
                'responsable'
            )
        }
    )