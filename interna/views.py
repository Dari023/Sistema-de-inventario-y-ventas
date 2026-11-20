from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.db.models import F
from django import forms
from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from decimal import Decimal, ROUND_HALF_UP
from django.views.decorators.http import require_POST, require_http_methods, require_GET
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.views.decorators.cache import never_cache
from .pedidos_personalizados import crear_enlace_pedido_personalizado, obtener_pedido_personalizado_por_token, resumen_pagos_personalizado
from .models import (Producto, 
    ProductoMateriaPrima, 
    MateriaPrima, 
    CategoriaProducto, 
    MovimientoMateriaPrima, 
    ConfiguracionPrecio,
    Resena,
    PreguntaFrecuente,
    HistorialEtapaPedido,
    ProductoVariante,
    Pedido,
    DetallePedidoPersonalizado)
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
    TiempoPrecioForm,
    PreguntaFrecuenteForm,
    ProductoVarianteForm,
    PedidoPersonalizadoForm,
    DetallePedidoPersonalizadoForm,
    MaterialPedidoPersonalizadoFormSet,
    ArticulosPedidoPersonalizadoFormSet)

@login_required
def home(request):
    materias_criticas = list(
        MateriaPrima.objects.filter(
            estado=True,
            cantidad_actual__lte=F("cantidad_critica")
        ).order_by("nombre")
    )

    productos_criticos = list(
        Producto.objects.filter(
            activo=True,
            stock_actual__lte=F("stock_critico")
        ).order_by("nombre")
    )

    return render(request, "interna/dashboard.html", {
        "materias_criticas": materias_criticas,
        "productos_criticos": productos_criticos,
        "total_alertas": len(materias_criticas) + len(productos_criticos),
    })

@login_required
def inventario(request):
    return render(request, 'interna/inventario/inventario.html')

@login_required
@permission_required('interna.view_producto', raise_exception=True)
def producto_listar(request):
    productos = Producto.objects.prefetch_related('variantes')
    return render(request, 'interna/producto/producto_listar.html', {'productos': productos})

def _categoria_admite_tallas(categoria):
    return categoria.nombre.strip().casefold() == 'chaleco'

def _formulario_producto(request, producto):
    editando = producto.pk is not None
    es_post = request.method == "POST"
    datos = request.POST if es_post else None
    archivos = request.FILES if es_post else None

    form = ProductoForm(datos, archivos, instance=producto)
    materiales = ProductoMateriaPrimaFormSet(datos, instance=producto, prefix='materiales')
    variantes_guardadas = {}
    if editando:
        variantes_guardadas = {
            variante.talla: variante for variante in producto.variantes.all()
        }

    filas_tallas = []
    for talla, etiqueta in ProductoVariante.TALLAS:
        variante = variantes_guardadas.get(talla)
        fila = ProductoVarianteForm(
            datos,
            prefix=f"talla-{talla}",
            initial={
                'ofrecer': variante is not None,
                'precio': variante.precio if variante else None,
                'a_pedido': variante.a_pedido if variante else False,
                'tiempo_minutos': variante.tiempo_minutos if variante else None
            }
        )

        if variante is not None:
            fila.fields['ofrecer'].disabled = True

        filas_tallas.append((talla, etiqueta, fila))

    tallas_ofrecidas = [
        talla for talla, _, fila in filas_tallas
        if fila['ofrecer'].value()
    ]
    tiene_tallas = bool(tallas_ofrecidas)

    campo_precio = form.fields['precio']
    campo_precio.required = not tiene_tallas
    campo_precio.disabled = tiene_tallas

    for fila_material in materiales.forms:
        campo_cantidad = fila_material.fields['cantidad_requerida']
        campo_cantidad.required = not tiene_tallas
        campo_cantidad.disabled = tiene_tallas

    campo_tiempo = form.fields['tiempo_fabricacion_minutos']
    campo_tiempo.required = not tiene_tallas
    campo_tiempo.disabled = tiene_tallas

    if es_post:
        producto_valido = form.is_valid()
        materiales_validos = materiales.is_valid()
        tallas_validas = all([fila.is_valid() for _, _, fila in filas_tallas])

        if tiene_tallas and materiales_validos:
            campos_tallas = [
                f"cantidad_{talla.lower()}" for talla in tallas_ofrecidas
            ]

            for fila_material in materiales.forms:
                receta = fila_material.cleaned_data

                if receta.get('DELETE') or not receta.get('materia_prima'):
                    continue

                if not any(receta.get(campo) is not None for campo in campos_tallas):
                    fila_material.add_error(
                        campos_tallas[0],
                        'Indica Cuánto se usa de este Material en al Menos una Talla'
                    )
                    materiales_validos = False

        if producto_valido:
            categoria = form.cleaned_data['categoria']

            if not _categoria_admite_tallas(categoria) and (variantes_guardadas or tiene_tallas):
                mensaje = (
                    'Este producto ya tiene Tallas Registradas, debe Mantenerse en la Categoría Chaleco'
                    if variantes_guardadas
                    else 'Solo la Categoría Chaleco Admite Tallas'
                )
                form.add_error('categoria', mensaje)
                producto_valido = False

        if producto_valido and materiales_validos and tallas_validas:
            with transaction.atomic():

                producto = form.save(commit=False)
                if tiene_tallas:
                    producto.precio = min(
                        fila.cleaned_data['precio']
                        for _, _, fila in filas_tallas
                        if fila.cleaned_data['ofrecer']
                    )

                producto.save()
                form.save_m2m()

                materiales.instance = producto
                materiales.save()

                for talla, _, fila in filas_tallas:
                    if fila.cleaned_data['ofrecer']:
                        ProductoVariante.objects.update_or_create(
                            producto=producto,
                            talla=talla,
                            defaults={
                                'precio': fila.cleaned_data['precio'],
                                'a_pedido': fila.cleaned_data['a_pedido'],
                                'tiempo_minutos': fila.cleaned_data['tiempo_minutos']
                            }
                        )

            return redirect("producto_listar")

    configuracion, _ = ConfiguracionPrecio.objects.get_or_create(pk=1)

    parametros_precio = {
        "costo_hora": str(configuracion.costo_hora),
        "costo_bolsa": str(configuracion.costo_bolsa),
        "costo_stickers": str(configuracion.costo_stickers),
        "margen_ganancia": str(configuracion.margen_ganancia),
        "porcentaje_iva": str(configuracion.porcentaje_iva),
        "porcentaje_comision": str(configuracion.porcentaje_comision),
        "comision_afecta_iva": configuracion.comision_afecta_iva
    }

    mostrar_tallas = bool(variantes_guardadas)
    if es_post:
        mostrar_tallas = mostrar_tallas or any(
            fila["ofrecer"].value() or fila.errors for _, _, fila in filas_tallas
        )

    return render(
        request,
        "interna/producto/producto_crear.html",
        {
            "form": form,
            "producto": producto if editando else None,
            "materiales": materiales,
            "filas_tallas": filas_tallas,
            "mostrar_tallas": mostrar_tallas,
            "parametros_precio": parametros_precio,
            "tiene_tallas": tiene_tallas,
            'categorias_con_tallas': [
                categoria.pk
                for categoria in form.fields['categoria'].queryset
                if _categoria_admite_tallas(categoria)
            ],
            'hay_variantes_guardadas': bool(variantes_guardadas),
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
@permission_required('interna.fabricar_producto', raise_exception=True)
def producto_fabricar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    es_post = request.method == "POST"
    form = FabricacionForm(request.POST if es_post else None)
    variantes = producto.variantes.order_by("talla")
    tiene_tallas = variantes.exists()
    campo_variante = form.fields["variante"]
    campo_variante.queryset = variantes
    campo_variante.required = tiene_tallas

    if not tiene_tallas:
        campo_variante.widget = forms.HiddenInput()

    if es_post and form.is_valid():
        cantidad = form.cleaned_data['cantidad']
        variante_elegida = form.cleaned_data['variante']

        with transaction.atomic():
            producto = get_object_or_404(Producto.objects.select_for_update(), pk=pk)
            variantes_actuales = producto.variantes.select_for_update()
            variante = None

            if variante_elegida is not None:
                variante = variantes_actuales.filter(pk=variante_elegida.pk,).first()

                if variante is None:
                    form.add_error("variante", "Esta talla ya no está disponible.")
            elif variantes_actuales.exists():
                form.add_error("variante", "Selecciona la talla que vas a fabricar.")

            if not form.errors:
                campo_cantidad = (
                    f"cantidad_{variante.talla.lower()}"
                    if variante is not None
                    else "cantidad_requerida"
                )

                materiales = (
                    ProductoMateriaPrima.objects
                    .select_for_update()
                    .filter(producto=producto)
                    .select_related("materia_prima")
                    .order_by("materia_prima_id")
                )

                consumos = []

                for material in materiales:
                    cantidad_por_unidad = getattr(material, campo_cantidad)

                    if variante is not None and cantidad_por_unidad is None:
                        continue

                    materia_prima = material.materia_prima

                    if (
                        not materia_prima.estado
                        or cantidad_por_unidad is None
                        or cantidad_por_unidad <= 0
                    ):
                        form.add_error(
                            None,
                            f"Revisa la cantidad o el estado de {materia_prima.nombre}.",
                        )
                        break

                    consumo = cantidad_por_unidad * cantidad

                    if materia_prima.cantidad_actual < consumo:
                        form.add_error(None, f"No hay stock suficiente de {materia_prima.nombre}")
                        break

                    consumos.append((materia_prima, consumo))

                if not form.errors and not consumos:
                    mensaje = (
                        f"La talla {variante.talla} no tiene materiales en su receta."
                        if variante is not None
                        else "El producto no tiene materiales en su receta."
                    )
                    form.add_error(None, mensaje)

                if not form.errors:
                    nombre = (
                        f"{producto.nombre}, talla {variante.talla}"
                        if variante is not None
                        else producto.nombre
                    )

                    for materia_prima, consumo in consumos:
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
                                f"Fabricación de {cantidad} unidad(es) de "
                                f"{nombre} (ID {producto.pk})."
                            ),
                        )

                    destino_stock = variante if variante is not None else producto
                    destino_stock.stock_actual += cantidad
                    destino_stock.save(update_fields=["stock_actual"])

                    return redirect("producto_detalles", producto.pk)

    return render(
        request,
        "interna/producto/producto_fabricar.html",
        {"form": form, "producto": producto, "tiene_tallas": tiene_tallas},
    )

@login_required
@permission_required('interna.view_producto', raise_exception=True)
def producto_detalles(request, pk):
    producto = get_object_or_404(Producto.objects.select_related('categoria').prefetch_related('variantes'), pk=pk)

    variantes = list(producto.variantes.all())
    materiales = ProductoMateriaPrima.objects.filter(producto=producto).select_related('materia_prima').order_by('materia_prima__nombre')
    receta = [
        {
            'materia_prima': material.materia_prima,
            'cantidad_general': material.cantidad_requerida,
            'cantidades_por_talla': [getattr(material, f"cantidad_{variante.talla.lower()}")
                for variante in variantes
            ]
        }
        for material in materiales
    ]

    return render(request, 'interna/producto/producto_detalles.html', {'producto': producto, 'variantes':variantes, 'receta':receta})

@login_required
@permission_required('interna.view_materiaprima', raise_exception=True)
def materia_prima_listar(request):
    materia_prima = MateriaPrima.objects.all()
    return render(request, 'interna/inventario/materia_prima_listar.html', {'materia_prima': materia_prima})

@login_required
@permission_required('interna.view_materiaprima', raise_exception=True)
def materia_prima_detalles(request, pk):
    materia_prima = get_object_or_404(MateriaPrima, pk=pk)
    return render(request, 'interna/inventario/materia_prima_detalles.html', {'materia_prima': materia_prima})

@login_required
@permission_required('interna.add_materiaprima', raise_exception=True)
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
    materia_prima = get_object_or_404(consulta, pk=pk)
    cantidad_anterior = materia_prima.cantidad_actual
    datos = request.POST if request.method == 'POST' else None
    form = MateriaPrimaForm(datos, instance=materia_prima)

    form.fields['cantidad_actual'].widget.attrs.update({'data-cantidad-inicial': str(cantidad_anterior)})
    form.fields['unidad_de_medida'].disabled = True

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
                observacion=form.cleaned_data['observacion']
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
@permission_required('interna.view_categoriaproducto', raise_exception=True)
def categoria_listar(request):
    categorias = CategoriaProducto.objects.all()
    return render(request, 'interna/inventario/categoria_listar.html', {'categorias': categorias})

@login_required
@permission_required('interna.add_categoriaproducto', raise_exception=True)
def categoria_crear(request):
    if request.method == 'POST':
        form = CategoriaProductoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('categoria_listar')
    else:
        form = CategoriaProductoForm()
    return render(request, 'interna/inventario/categoria_crear.html', {'form': form})

@login_required
@permission_required('interna.change_categoriaproducto', raise_exception=True)
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

@login_required
@permission_required('interna.view_pedido', raise_exception=True)
def pedido_listar(request):
    q = request.GET.get('q', '').strip()
    pedidos = (
        Pedido.objects
        .filter(Q(tipo_pedido='normal', estado='pagado') | (Q(tipo_pedido='personalizado')))
        .select_related('cliente')
        .prefetch_related('detallepedido_set__producto', 'detalles_personalizados')
        .order_by('-fecha_pedido')
    )
    if q:
        if q.isdigit():
            pedidos = pedidos.filter(pk=int(q))
        else:
            pedidos = pedidos.filter(id_compra__icontains=q)
    return render(request, 'interna/inventario/pedido_listar.html', {'pedidos': pedidos, 'q': q})

@login_required
@permission_required('interna.view_pedido', raise_exception=True)
def pedido_detalles(request, pk):
    pedido = get_object_or_404(
        Pedido.objects
        .select_related('cliente')
        .prefetch_related('detallepedido_set__producto', 'detalles_personalizados__materiales__materia_prima', 
        'pagos', 'historial_etapas__responsable'), pk=pk)

    if pedido.tipo_pedido == 'personalizado':
        total_abonado = sum(
            (
                pago.monto
                for pago in pedido.pagos.all()
                if pago.estado == 'aprobado'
            ),
            Decimal('0')
        )

        return render(request, 'interna/inventario/pedido_personalizado_detalles.html',
                {'pedido': pedido, 
                'total_abonado': total_abonado, 
                'saldo_pendiente': pedido.total - total_abonado, 
                'puede_editar_encargo': _puede_editar_encargo(pedido),
                'enlace_cliente': crear_enlace_pedido_personalizado(request, pedido)})
    
    return render(request, 'interna/inventario/pedido_detalles.html', {'pedido': pedido})

@login_required
@permission_required('interna.view_resena', raise_exception=True)
def resenas_listar(request):
    resenas = (Resena.objects
        .select_related('producto', 'pedido')
        .order_by('-fecha_creacion', '-pk')
    )

    return render(request, 'interna/inventario/resenas_listar.html',{'resenas': resenas})

@login_required
@permission_required(('interna.view_resena', 'interna.change_resena'),raise_exception=True)

@require_POST
def resena_estado_cambiar(request, pk):
    resena = get_object_or_404(Resena, pk=pk)
    accion = request.POST.get('accion')

    if accion == 'deshabilitar':
        resena.activo = False
    elif accion == 'reactivar':
        resena.activo = True
    else:
        return HttpResponseBadRequest('La Acción no es Válida')

    resena.save(update_fields=['activo'])

    return redirect('resenas_listar')

@login_required
@permission_required('interna.view_preguntafrecuente', raise_exception=True)
def preguntas_frecuentes_listar(request):
    preguntas = PreguntaFrecuente.objects.all()
    estado = request.GET.get('estado', '')

    if estado == 'activas':
        preguntas = preguntas.filter(activo=True)
    elif estado == 'deshabilitadas':
        preguntas = preguntas.filter(activo=False)

    return render(
        request,
        'interna/inventario/preguntas_listar.html',
        {
            'preguntas': preguntas,
            'estado': estado,
        },
    )

@login_required
@permission_required('interna.add_preguntafrecuente', raise_exception=True)
def pregunta_frecuente_crear(request):
    if request.method == 'POST':
        form = PreguntaFrecuenteForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('preguntas_frecuentes_listar')
    else:
        form = PreguntaFrecuenteForm()

    return render(request, 'interna/inventario/pregunta_formulario.html', {"form": form})

@login_required
@permission_required('interna.change_preguntafrecuente', raise_exception=True)
def pregunta_frecuente_editar(request, pk):
    pregunta = get_object_or_404(PreguntaFrecuente, pk=pk)

    if request.method == 'POST':
        form = PreguntaFrecuenteForm(request.POST, instance=pregunta)

        if form.is_valid():
            form.save()
            return redirect('preguntas_frecuentes_listar')
    else:
        form = PreguntaFrecuenteForm(instance=pregunta)

    return render(request, 'interna/inventario/pregunta_formulario.html',{'form': form, 'pregunta': pregunta,})

@login_required
@permission_required('interna.change_preguntafrecuente',raise_exception=True)
@require_POST
def pregunta_frecuente_estado(request, pk):
    pregunta = get_object_or_404(PreguntaFrecuente, pk=pk)
    accion = request.POST.get('accion')

    if accion == 'deshabilitar':
        pregunta.activo = False
    elif accion == 'reactivar':
        pregunta.activo = True
    else:
        return HttpResponseBadRequest('La Acción no es Válida')

    pregunta.save(update_fields=['activo'])

    return redirect('preguntas_frecuentes_listar')

def pedido_cambiar_estado(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    nueva_etapa = request.POST.get('etapa')    
    etapas_validas = [e[0] for e in Pedido.ETAPAS]

    if pedido.tipo_pedido == 'personalizado':
        return HttpResponseForbidden('La Gestión de Etapas de pedidos Personalizados aún no está Habilitada')

    if nueva_etapa in etapas_validas:
        pedido.etapa = nueva_etapa
        pedido.save(update_fields=['etapa'])
        HistorialEtapaPedido.objects.create(
            pedido=pedido,
            etapa=nueva_etapa,
            responsable=request.user
        )
    return redirect('pedido_detalles', pk=pedido.pk)

@login_required
@permission_required('interna.add_pedido', raise_exception=True)
def pedido_personalizado_crear(request):
    es_post = request.method == 'POST'
    datos = request.POST if es_post else None
    archivos = request.FILES if es_post else None
    pedido = Pedido(tipo_pedido='personalizado')
    form_pedido = PedidoPersonalizadoForm(datos, instance=pedido, prefix='pedido')
    articulos = ArticulosPedidoPersonalizadoFormSet(datos, archivos, instance=pedido, prefix='articulos', queryset=DetallePedidoPersonalizado.objects.none())

    if es_post:
        pedido_valido = form_pedido.is_valid()
        articulos_validos = articulos.is_valid()
        recetas_validas = True

        for fila in articulos.forms:
            if fila.cleaned_data.get('DELETE'):
                continue

            if fila.empty_permitted and not fila.has_changed():
                if fila.materiales.has_changed():
                    fila.add_error(None, 'Completa las Características del Artículo al que Pertenecen estos Materiales')
                    articulos_validos = False
                else:
                    continue

            if not fila.materiales.is_valid():
                recetas_validas = False

        filas_a_guardar= []

        if articulos_validos:
            filas_a_guardar = [
                fila
                for fila in articulos.forms
                if fila.cleaned_data
                and not fila.cleaned_data.get('DELETE')
            ]

        if pedido_valido and articulos_validos:
            total = sum(
                (fila.cleaned_data['cantidad']* fila.cleaned_data['precio_unitario'] for fila in filas_a_guardar), Decimal('0'))

            if form_pedido.cleaned_data['adelanto_requerido'] > total:
                form_pedido.add_error('adelanto_requerido', 'El Adelanto no puede Superar el Total de Todos los Artículos del Pedido')
                pedido_valido = False

        if pedido_valido and articulos_validos and recetas_validas:
            with transaction.atomic():
                pedido = form_pedido.save(commit=False)
                pedido.tipo_pedido = 'personalizado'
                pedido.estado = 'pendiente'
                pedido.etapa = None
                pedido.save()

                for fila in filas_a_guardar:
                    detalle = fila.save(commit=False)
                    detalle.pedido = pedido
                    detalle.save()

                    fila.materiales.instance = detalle
                    fila.materiales.save()

            return redirect('pedido_detalles', pk=pedido.pk)

    return render(request, 'interna/inventario/pedido_personalizado_crear.html',
        {
            'form_pedido': form_pedido,
            'articulos': articulos
        }
    )

def _puede_editar_encargo(pedido):
    return (
        pedido.estado == 'pendiente'
        and not pedido.etapa
        and not pedido.pagos.exclude(estado="rechazado").exists()
        and not pedido.detalles_personalizados.filter(unidades_fabricadas__gt=0).exists()
    )

@transaction.atomic
def _formulario_articulo_personalizado(request, pedido_pk, detalle_pk=None):
    es_post = request.method == 'POST'

    consulta = Pedido.objects.filter(tipo_pedido='personalizado')
    if es_post:
        consulta = consulta.select_for_update()

    pedido = get_object_or_404(consulta, pk=pedido_pk)

    if not _puede_editar_encargo(pedido):
        return HttpResponseForbidden(
            'No puedes modificar los artículos de un pedido'
            "con pagos en trámite, pagos aprobados o fabricación iniciada"
        )

    if detalle_pk is None:
        detalle = DetallePedidoPersonalizado(pedido=pedido)
        subtotal_anterior = 0
    else:
        detalle = get_object_or_404(DetallePedidoPersonalizado, pk=detalle_pk, pedido=pedido)
        subtotal_anterior = detalle.subtotal

    editando = detalle.pk is not None
    datos = request.POST if es_post else None
    archivos = request.FILES if es_post else None

    form_detalle = DetallePedidoPersonalizadoForm(datos, archivos, instance=detalle, prefix='encargo')
    materiales = MaterialPedidoPersonalizadoFormSet(datos, instance=detalle, prefix='materiales')

    for fila in materiales.forms:
        disponibles = Q(estado=True)

        if fila.instance.pk:
            disponibles |= Q(pk=fila.instance.materia_prima_id)

        fila.fields['materia_prima'].queryset = (
            MateriaPrima.objects
            .filter(disponibles)
            .order_by('nombre')
        )

    if es_post:
        detalle_valido = form_detalle.is_valid()
        materiales_validos = materiales.is_valid()

        if detalle_valido:
            nuevo_subtotal = (form_detalle.cleaned_data['cantidad'] * form_detalle.cleaned_data['precio_unitario'])
            nuevo_total = pedido.total - subtotal_anterior + nuevo_subtotal

            if nuevo_total < pedido.adelanto_requerido:
                form_detalle.add_error(None,
                    'El total resultante del pedido no puede ser '
                    'menor que el adelanto requerido'
                )
                detalle_valido = False

        if detalle_valido and materiales_validos:
            detalle = form_detalle.save(commit=False)
            detalle.pedido = pedido
            detalle.save()

            materiales.instance = detalle
            materiales.save()

            return redirect('pedido_detalles', pk=pedido.pk)

    return render(request, 'interna/inventario/pedido_personalizado_articulo_form.html',
        {'pedido': pedido, 'form_detalle': form_detalle, 'materiales': materiales, 'editando': editando})

@login_required
@permission_required('interna.change_pedido', raise_exception=True)
def pedido_personalizado_articulo_agregar(request, pk):
    return _formulario_articulo_personalizado(request, pedido_pk=pk)

@login_required
@permission_required('interna.change_pedido', raise_exception=True)
def pedido_personalizado_articulo_editar(request, pk, detalle_pk):
    return _formulario_articulo_personalizado(request, pedido_pk=pk, detalle_pk=detalle_pk)

@never_cache
@require_GET
def pedido_personalizado_publico(request, token):
    pedido = obtener_pedido_personalizado_por_token(token)
    resumen = resumen_pagos_personalizado(pedido)

    respuesta = render(request, 'interna/inventario/pedido_personalizado_publico.html',
        {
            'pedido': pedido,
            'resumen': resumen,
        }
    )

    respuesta['Referrer-Policy'] = 'no-referrer'
    respuesta['X-Robots-Tag'] = 'noindex, nofollow'

    return respuesta