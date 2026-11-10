from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse
from decimal import Decimal, ROUND_HALF_UP
from django.views.decorators.http import require_POST, require_http_methods
from django.contrib.auth.decorators import login_required, permission_required
from .models import (Producto, 
    ProductoMateriaPrima, 
    MateriaPrima, 
    CategoriaProducto, 
    MovimientoMateriaPrima, 
    ConfiguracionPrecio)
from .forms import (
    ProductoForm, 
    MateriaPrimaForm, 
    ProductoMateriaPrimaForm, 
    CategoriaProductoForm, 
    ProductoMateriaPrimaFormSet, 
    FabricacionForm,
    MovimientoObservacionForm,
    ConfiguracionPrecioForm,
    PrecioMaterialesFormSet,
    TiempoPrecioForm)

@login_required
def home(request):
    return redirect('inventario')

@login_required
def inventario(request):
    return render(request, 'interna/inventario/inventario.html')

@login_required
def producto_listar(request):
    productos = Producto.objects.all()
    return render(request, 'interna/producto/producto_listar.html', {'productos': productos})

def _formulario_producto(request, producto):
    editando = producto.pk is not None
    if request.method == "POST":
        form = ProductoForm(
            request.POST,
            request.FILES,
            instance=producto,
        )
        materiales = ProductoMateriaPrimaFormSet(
            request.POST,
            instance=producto,
            prefix="materiales",
        )

        producto_valido = form.is_valid()
        materiales_validos = materiales.is_valid()

        if producto_valido and materiales_validos:
            with transaction.atomic():
                producto = form.save()
                materiales.instance = producto
                materiales.save()
            return redirect("producto_listar")
    else:
        form = ProductoForm(instance=producto)
        materiales = ProductoMateriaPrimaFormSet(
            instance=producto,
            prefix="materiales",
        )

    configuracion, creada = ConfiguracionPrecio.objects.get_or_create(pk=1)

    parametros_precio = {
    'costo_hora': str(configuracion.costo_hora),
    'costo_bolsa': str(configuracion.costo_bolsa),
    'costo_stickers': str(configuracion.costo_stickers),
    'margen_ganancia': str(configuracion.margen_ganancia),
    'porcentaje_iva': str(configuracion.porcentaje_iva),
    'porcentaje_comision': str(configuracion.porcentaje_comision),
    'comision_afecta_iva': configuracion.comision_afecta_iva,
    }

    return render(
        request, "interna/producto/producto_crear.html",
        {
            "form": form,
            "producto": producto if editando else None,
            "materiales": materiales,
            'parametros_precio': parametros_precio
        }
    )

@login_required
@permission_required("interna.add_producto", raise_exception=True)
def producto_crear(request):
    return _formulario_producto(request, Producto())

@login_required
@permission_required("interna.change_producto", raise_exception=True)
def producto_editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    return _formulario_producto(request, producto)

@login_required
@permission_required(
    ["interna.change_producto", "interna.change_materiaprima"],
    raise_exception=True,
)

@login_required
def producto_fabricar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    datos = request.POST if request.method == "POST" else None
    form = FabricacionForm(datos)

    if request.method == "POST" and form.is_valid():
        cantidad = form.cleaned_data["cantidad"]
        with transaction.atomic():
            producto = Producto.objects.select_for_update().get(pk=pk)
            materiales = list(
                ProductoMateriaPrima.objects
                .select_for_update()
                .filter(producto=producto)
                .select_related("materia_prima")
                .order_by("materia_prima_id")
            )
            if not materiales:
                form.add_error(None, "El Producto no Tiene Materiales Asociados.")
            elif any(
                not material.materia_prima.estado
                or material.cantidad_requerida <= 0
                for material in materiales
            ):
                form.add_error(None, "Revisa los Materiales de la Receta.")

            elif any(
                material.materia_prima.cantidad_actual
                < material.cantidad_requerida * cantidad
                for material in materiales
            ):
                form.add_error(None, "No hay Suficientes Materias Primas.")

            else:
                for material in materiales:
                    materia_prima = material.materia_prima
                    consumo = material.cantidad_requerida * cantidad
                    materia_prima.cantidad_actual -= consumo
                    materia_prima.save(update_fields=["cantidad_actual"])

                    MovimientoMateriaPrima.objects.create(
                        materia_prima=materia_prima,
                        tipo="SALIDA",
                        motivo="FABRICACION",
                        cantidad=consumo,
                        saldo_resultante=materia_prima.cantidad_actual,
                        responsable=request.user,
                        observacion=(
                            f"Fabricación de {cantidad} Unidad(es) "
                            f"de {producto.nombre} (ID {producto.pk})."
                        ),
                    )
                producto.stock_actual += cantidad
                producto.save(update_fields=["stock_actual"])

                return redirect("producto_detalles", producto.pk)

    return render(
        request,
        "interna/producto/producto_fabricar.html",
        {"form": form, "producto": producto},
    )

def producto_detalles(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    return render(request, 'interna/producto/producto_detalles.html', {'producto': producto})

def materia_prima_listar(request):
    materia_prima = MateriaPrima.objects.all()
    return render(request, 'interna/inventario/materia_prima_listar.html', {'materia_prima': materia_prima})

def materia_prima_detalles(request, pk):
    materia_prima = get_object_or_404(MateriaPrima, pk=pk)
    return render(request, 'interna/inventario/materia_prima_detalles.html', {'materia_prima': materia_prima})

@login_required
def materia_prima_crear(request):
    if request.method == "POST":
        form = MateriaPrimaForm(request.POST)
        form.fields.pop('observacion')
        if form.is_valid():
            with transaction.atomic():
                materia_prima = form.save()
                if materia_prima.cantidad_actual > 0:
                    MovimientoMateriaPrima.objects.create(
                        materia_prima=materia_prima,
                        tipo="ENTRADA",
                        motivo="INICIAL",
                        cantidad=materia_prima.cantidad_actual,
                        saldo_resultante=materia_prima.cantidad_actual,
                        responsable=request.user,
                    )

            return redirect("materia_prima_listar")
    else:
        form = MateriaPrimaForm()
        form.fields.pop("observacion")

    return render(
        request,
        "interna/inventario/materia_prima_crear.html",
        {"form": form},
    )

@login_required
@permission_required('interna.change_materiaprima', raise_exception=True,)
@transaction.atomic
def materia_prima_editar(request, pk):
    consulta = MateriaPrima.objects.all()
    if request.method == 'POST':
        consulta = consulta.select_for_update()
    materia_prima = get_object_or_404(MateriaPrima, pk=pk)
    cantidad_anterior = materia_prima.cantidad_actual
    datos = request.POST if request.method == 'POST' else None
    form = MateriaPrimaForm(datos, instance=materia_prima)

    form.fields['cantidad_actual'].widget.attrs.update({'data-cantidad-inicial': str(cantidad_anterior),})

    if materia_prima.movimientos.exists():
        form.fields['unidad_de_medida'].disabled = True

    if request.method == 'POST' and form.is_valid():
        materia_prima = form.save()
        diferencia = (materia_prima.cantidad_actual - cantidad_anterior)

        if diferencia !=0:
            MovimientoMateriaPrima.objects.create(
                materia_prima=materia_prima,
                tipo='ENTRADA' if diferencia > 0 else 'SALIDA',
                motivo='AJUSTE',
                cantidad=abs(diferencia),
                saldo_resultante=materia_prima.cantidad_actual,
                responsable=request.user,
                observacion=form.cleaned_data['observacion'],
            )
            return redirect ('materia_prima_listar')
    return render(request, 'interna/inventario/materia_prima_crear.html', {'form': form, 'materia_prima': materia_prima})

@login_required
def movimientos_listar(request):
    movimientos = (
        MovimientoMateriaPrima.objects
        .select_related("materia_prima", "responsable")
        .all()
    )

    return render(
        request,
        "interna/inventario/movimientos_listar.html",
        {"movimientos": movimientos},
    )

@login_required
@permission_required("interna.change_movimientomateriaprima", raise_exception=True,)
def movimiento_observacion_editar(request, pk):
    movimiento = get_object_or_404(MovimientoMateriaPrima, pk=pk,)
    datos = request.POST if request.method == "POST" else None
    form = MovimientoObservacionForm(datos, instance=movimiento,)

    if request.method == "POST" and form.is_valid():
        movimiento = form.save(commit=False)
        movimiento.save(update_fields=["observacion"])

        return redirect("movimientos_listar")

    return render(
        request,
        "interna/inventario/movimiento_observacion.html",
        {
            "form": form,
            "movimiento": movimiento,
        },
    )

@login_required
def categoria_listar(request):
    categorias = CategoriaProducto.objects.all()
    return render(request, 'interna/inventario/categoria_listar.html', {'categorias': categorias})

def categoria_crear(request):
    if request.method == 'POST':
        form = CategoriaProductoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('categoria_listar')
    else:
        form = CategoriaProductoForm()
    return render(request, 'interna/inventario/categoria_crear.html', {'form': form})

def categoria_editar(request, pk):
    categoria = get_object_or_404(CategoriaProducto, pk=pk)
    if request.method == 'POST':
        form = CategoriaProductoForm(request.POST, request.FILES, instance=categoria)
        if form.is_valid():
            form.save()
            return redirect('categoria_listar')
    else:
        form = CategoriaProductoForm(instance=categoria)
    return render(request, 'interna/inventario/categoria_crear.html', {'form': form, 'categoria': categoria})

@login_required
@permission_required("interna.change_producto", raise_exception=True)
def gestionar_materias_producto(request, producto_id):
    producto = get_object_or_404(Producto, pk=producto_id)

    if request.method == "POST":
        form = ProductoMateriaPrimaForm(request.POST)

        if form.is_valid():
            ProductoMateriaPrima.objects.update_or_create(
                producto=producto,
                materia_prima=form.cleaned_data["materia_prima"],
                defaults={
                    "cantidad_requerida": (
                        form.cleaned_data["cantidad_requerida"]
                    )
                },
            )

            return redirect(
                "gestionar_materias_producto",
                producto_id=producto.pk,
            )
    else:
        form = ProductoMateriaPrimaForm()

    materiales = (
        ProductoMateriaPrima.objects
        .filter(producto=producto)
        .select_related("materia_prima")
    )

    return render(
        request,
        "productos/materias_primas.html",
        {
            "producto": producto,
            "form": form,
            "materiales": materiales,
        },
    )

@login_required
@require_POST
def producto_precio_sugerido(request):
    puede_crear = request.user.has_perm('interna.add_producto')
    puede_editar = request.user.has_perm('interna.change_producto')
    if not (puede_crear or puede_editar):
        raise PermissionDenied

    tiempo = TiempoPrecioForm(request.POST)
    materiales = PrecioMaterialesFormSet(request.POST, prefix='materiales')
    tiempo_valido = tiempo.is_valid()
    materiales_validos = materiales.is_valid()

    if not tiempo_valido or not materiales_validos:
        errores = []
        for mensajes in tiempo.errors.values():
            errores.extend(str(mensaje) for mensaje in mensajes)
        errores.extend(str(mensaje) for mensaje in materiales.non_form_errors())
        for errores_fila in materiales.errors:
            for mensajes in errores_fila.values():
                errores.extend(str(mensaje) for mensaje in mensajes)
        return JsonResponse({'error': errores[0] if errores else 'Revisa la Receta'}, status=400)

    configuracion, creada = ConfiguracionPrecio.objects.get_or_create(pk=1)
    costos = []
    for formulario in materiales.forms:
        datos = formulario.cleaned_data
        if not datos or datos.get('DELETE'):
            continue
        materia = datos.get('materia_prima')
        if materia is not None:
            costos.append((datos['cantidad_requerida'], materia.costo_unitario))

    try:
        configuracion.full_clean()
        resultado = calcular_sugerencia(
            tiempo.cleaned_data['tiempo_fabricacion_minutos'], costos, configuracion,
        )
    except (ValueError, ValidationError):
        return JsonResponse({
            'error': 'Revisa los costos de la receta o la configuración de precios',
        }, status=400)

    respuesta = JsonResponse(resultado)
    respuesta['Cache-Control'] = 'no-store'
    return respuesta

@login_required
@permission_required('interna.change_configuracionprecio', raise_exception=True)
@require_http_methods(['GET', 'POST'])
def configuracion_precio_editar(request):
    configuracion, creada = ConfiguracionPrecio.objects.get_or_create(pk=1)
    datos = request.POST if request.method == 'POST' else None
    form = ConfiguracionPrecioForm(datos, instance=configuracion)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Configuración de Precios Actualizada')
        return redirect('configuracion_precio_editar')
    return render(request, 'interna/producto/configuracion_precio.html', {'form': form})

def decimal_valido(valor, nombre):
    numero = Decimal(str(valor))
    if not numero.is_finite() or numero < 0:
        raise ValueError(f"Revisa el valor de {nombre}.")
    return numero

def calcular_sugerencia(minutos, materiales, configuracion):
    tiempo = decimal_valido(minutos, 'tiempo de trabajo')
    if tiempo <= 0 or not materiales:
        raise ValueError('Indica el Tiempo de Trabajo y al menos un Material')

    costo_materiales = Decimal('0')
    for cantidad, costo_unitario in materiales:
        cantidad = decimal_valido(cantidad, 'cantidad requerida')
        if cantidad <= 0:
            raise ValueError('Las Cantidades de Materiales deben ser Mayores que 0')
        costo_materiales += cantidad * decimal_valido(costo_unitario, 'costo del material')

    costo_hora = decimal_valido(configuracion.costo_hora, 'costo por hora')
    bolsa = decimal_valido(configuracion.costo_bolsa, 'bolsa')
    stickers = decimal_valido(configuracion.costo_stickers, 'stickers')
    margen = decimal_valido(configuracion.margen_ganancia, 'margen')
    iva = decimal_valido(configuracion.porcentaje_iva, 'IVA')
    tasa_comision = decimal_valido(configuracion.porcentaje_comision, 'comisión')
    if margen >= 100 or tasa_comision >= 100 or iva > 100:
        raise ValueError('Revisa los Porcentajes de la Configuración de Precios')
    mano_obra = tiempo / Decimal('60') * costo_hora
    total = costo_materiales + mano_obra + bolsa + stickers
    if total <= 0:
        raise ValueError('El Costo Total debe ser Mayor que 0')
    sin_iva = total / (Decimal('1') - margen / Decimal('100'))
    con_iva = sin_iva * (Decimal('1') + iva / Decimal('100'))
    comision = con_iva * tasa_comision / Decimal('100')
    if configuracion.comision_afecta_iva:
        comision *= Decimal('1') + iva / Decimal('100')

    return {
        'materiales': costo_materiales,
        'mano_obra': mano_obra,
        'bolsa': bolsa,
        'stickers': stickers,
        'costo_total': total,
        'precio_sin_iva': sin_iva,
        'precio_sugerido': con_iva.quantize(Decimal('1'), rounding=ROUND_HALF_UP),
        'comision': comision,
        'margen': margen,
        'iva': iva,
    }