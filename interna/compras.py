from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .models import MateriaPrima, Proveedor, OrdenCompra
from .forms import (
    ProveedorForm,
    OrdenCompraForm,
    DetallesCompraFormSet,
    BajaMateriaPrimaForm,
    AjusteMateriaPrimaForm
)
from .stock_compras import (
    crear_orden_compra,
    recibir_orden_compra,
    cancelar_orden_compra,
    registrar_cambio_materia
)
from .views import _avisar_stock_materia

def _estilizar(form):
    for campo in form.fields.values():
        if isinstance(campo.widget, forms.CheckboxInput):
            clase = 'form-check-input'
        elif isinstance(campo.widget, forms.Select):
            clase = 'form-select'
        else:
            clase = 'form-control'

        campo.widget.attrs['class'] = clase

    return form

@login_required
@permission_required('interna.view_proveedor', raise_exception=True)
@require_GET
def proveedores_listar(request):
    return render(request, 'interna/inventario/proveedores_listar.html', {'proveedores': Proveedor.objects.all()})

@transaction.atomic
@require_http_methods(['GET', 'POST'])
def _formulario_proveedor(request, pk=None):
    proveedor = (get_object_or_404(Proveedor.objects.select_for_update(), pk=pk)
        if pk is not None
        else None
    )

    form = _estilizar(ProveedorForm(request.POST if request.method == 'POST' else None, instance=proveedor))

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Proveedor Guardado')
        return redirect('proveedores_listar')

    return render(request, 'interna/inventario/gestion_form.html',
        {
            'form': form,
            'titulo': 'Editar proveedor' if proveedor else 'Crear proveedor',
            'volver': 'proveedores_listar'
        }
    )

@login_required
@permission_required('interna.add_proveedor', raise_exception=True)
def proveedor_crear(request):
    return _formulario_proveedor(request)

@login_required
@permission_required('interna.change_proveedor', raise_exception=True)
def proveedor_editar(request, pk):
    return _formulario_proveedor(request, pk)

@login_required
@permission_required('interna.view_ordencompra', raise_exception=True)
@require_GET
def ordenes_compra_listar(request):
    ordenes = (OrdenCompra.objects.select_related('proveedor').prefetch_related('detalles'))
    return render(request, 'interna/inventario/ordenes_compra_listar.html', {'ordenes': ordenes})

@login_required
@permission_required('interna.add_ordencompra', raise_exception=True)
@require_http_methods(['GET', 'POST'])
def orden_compra_crear(request):
    datos = request.POST if request.method == 'POST' else None
    orden = OrdenCompra()
    form = _estilizar(OrdenCompraForm(datos, instance=orden))
    detalles = DetallesCompraFormSet(datos, instance=orden, prefix='detalles')

    if request.method == 'POST':
        valido = form.is_valid()
        detalles_validos = detalles.is_valid()

        if valido and detalles_validos:
            filas = [
                fila.cleaned_data
                for fila in detalles.forms
                if fila.cleaned_data
                and not fila.cleaned_data.get('DELETE')
            ]

            try:
                orden = crear_orden_compra(form.cleaned_data, filas, request.user)
            except ValidationError as error:
                form.add_error(None, error)
            except IntegrityError:
                form.add_error(None,'El Documento ya Está Registrado Para ese Proveedor o los Datos Cambiaron')
            else:
                messages.success(request,'Orden Creada, las Existencias Aumentarán al Confirmar su Recepción')
                return redirect('orden_compra_detalles', pk=orden.pk)

    for fila in detalles.forms:
        _estilizar(fila)

    return render(request, 'interna/inventario/orden_compra_form.html',
        {
            'form': form,
            'detalles': detalles,
            'fila_vacia': _estilizar(detalles.empty_form)
        }
    )

@login_required
@permission_required('interna.view_ordencompra', raise_exception=True)
@require_GET
def orden_compra_detalles(request, pk):
    consulta = (OrdenCompra.objects
        .select_related('proveedor', 'responsable', 'gestionado_por')
        .prefetch_related('detalles__materia_prima')
    )
    orden = get_object_or_404(consulta, pk=pk)

    return render(request, 'interna/inventario/orden_compra_detalles.html', {'orden': orden})

@login_required
@permission_required('interna.recibir_ordencompra', raise_exception=True)
@require_POST
def orden_compra_recibir(request, pk):
    try:
        actualizado = recibir_orden_compra(pk, request.user)
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
    else:
        if actualizado:
            messages.success(request, 'Recepción Registrada, Stock, Costos y Movimientos Actualizados')
        else:
            messages.info(request,'La Orden ya Estaba Recibida, no se Duplicaron las Entradas')

    return redirect('orden_compra_detalles', pk=pk)

@login_required
@permission_required('interna.cancelar_ordencompra', raise_exception=True)
@require_POST
def orden_compra_cancelar(request, pk):
    try:
        actualizado = cancelar_orden_compra(pk, request.POST.get('motivo', ''), request.user)
    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))
    else:
        messages.info(request, 'Orden Cancelada'
            if actualizado
            else 'La Orden ya Estaba Cancelada'
        )

    return redirect('orden_compra_detalles', pk=pk)

@require_http_methods(['GET', 'POST'])
def _formulario_stock(request, pk, es_ajuste):
    materia = get_object_or_404(MateriaPrima, pk=pk)
    tipo_form = (AjusteMateriaPrimaForm if es_ajuste else BajaMateriaPrimaForm)
    form = _estilizar(tipo_form(
        request.POST if request.method == 'POST' else None,
        initial={'stock_esperado': materia.cantidad_actual}
    ))

    if request.method == 'POST' and form.is_valid():
        try:
            movimiento, anterior = registrar_cambio_materia(pk, form.cleaned_data, request.user, es_ajuste)
        except ValidationError as error:
            form.add_error(None, error)
        else:
            _avisar_stock_materia(
                request,
                movimiento.materia_prima,
                anterior,
                movimiento.saldo_resultante
            )
            messages.success(request, 'Stock y Movimiento Registrados')
            return redirect('materia_prima_detalles', pk=pk)

    return render(request, 'interna/inventario/gestion_form.html',
        {
            'form': form,
            'titulo': ('Ajuste de Inventario'
                if es_ajuste
                else 'Registrar Baja'
            ),
            'materia_prima': materia,
            'volver': 'materia_prima_listar'
        }
    )

@login_required
@permission_required('interna.registrar_baja_materiaprima', raise_exception=True)
def materia_prima_baja(request, pk):
    return _formulario_stock(request, pk, False)

@login_required
@permission_required('interna.ajustar_stock_materiaprima', raise_exception=True)
def materia_prima_ajustar(request, pk):
    return _formulario_stock(request, pk, True)