from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from pathlib import Path
from django.contrib.auth.models import User
from django.core.files import File
from django.db.models import F
from django.utils import timezone
from django import forms
from django.contrib import messages
from django.template.defaultfilters import floatformat
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from decimal import Decimal, ROUND_HALF_UP
from django.views.decorators.http import require_POST, require_http_methods, require_GET
from django.contrib.auth.decorators import login_required, permission_required
from django.db.models import Q
from django.views.decorators.cache import never_cache
from .pedidos_personalizados import (
    crear_enlace_pedido_personalizado,
    obtener_pedido_personalizado_por_token,
    resumen_pagos_personalizado)
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
    Consulta,
    DetallePedidoPersonalizado,
    MaterialPedidoPersonalizado,
    FabricacionPedidoPersonalizado)
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
    ArticulosPedidoPersonalizadoFormSet,
    FabricacionPedidoPersonalizadoForm,
    PedidoPersonalizadoDatosForm,
    CancelacionPedidoPersonalizadoForm,
    PedidoPersonalizadoCrearForm)

@login_required
def home(request):
    materias_criticas = list(MateriaPrima.objects.filter(estado=True, cantidad_actual__lte=F("cantidad_critica")).order_by("nombre"))
    productos_criticos = list(Producto.objects.filter(activo=True, variantes__isnull=True, stock_actual__lte=F("stock_critico")).order_by("nombre"))
    variantes_criticas = list(ProductoVariante.objects
        .select_related('producto')
        .filter(producto__activo=True, stock_actual__lte=F('producto__stock_critico'))
        .order_by('producto__nombre', 'talla')
    )

    return render(request, "interna/dashboard.html", {
        "materias_criticas": materias_criticas,
        "productos_criticos": productos_criticos,
        'variantes_criticas': variantes_criticas,
        'total_alertas': (len(materias_criticas) + len(productos_criticos) + len(variantes_criticas))
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
                        stock_anterior = materia_prima.cantidad_actual
                        materia_prima.cantidad_actual -= consumo
                        materia_prima.save(update_fields=['cantidad_actual'])

                        MovimientoMateriaPrima.objects.create(
                            materia_prima=materia_prima,
                            tipo='SALIDA',
                            motivo='FABRICACION',
                            cantidad=consumo,
                            saldo_resultante=materia_prima.cantidad_actual,
                            responsable=request.user,
                            observacion=(f'Fabricación de {cantidad} Unidad(es) de {nombre} (ID {producto.pk})')
                        )

                        _avisar_stock_materia(request, materia_prima, stock_anterior, materia_prima.cantidad_actual)

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
@require_http_methods(['GET', 'POST'])
def materia_prima_crear(request):
    form = MateriaPrimaForm(request.POST if request.method == 'POST' else None)

    if request.method == 'POST' and form.is_valid():
        materia = form.save(commit=False)
        materia.cantidad_actual = 0
        materia.save()

        messages.success(request, 'Materia Prima Creada con Existencias en Cero')
        return redirect('materia_prima_listar')

    return render(request, 'interna/inventario/materia_prima_crear.html', {'form': form})

@login_required
@permission_required('interna.change_materiaprima', raise_exception=True)
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def materia_prima_editar(request, pk):
    consulta = (MateriaPrima.objects.select_for_update()
        if request.method == 'POST'
        else MateriaPrima.objects.all()
    )
    materia = get_object_or_404(consulta, pk=pk)

    form = MateriaPrimaForm(request.POST if request.method == 'POST' else None, instance=materia)
    form.fields['unidad_de_medida'].disabled = True

    if request.method == 'POST' and form.is_valid():
        materia = form.save(commit=False)
        materia.save(update_fields=['nombre', 'cantidad_critica', 'unidad_de_medida', 'costo_unitario', 'estado'])

        messages.success(request, 'Materia Prima Actualizada')
        return redirect('materia_prima_listar')

    return render(request, 'interna/inventario/materia_prima_crear.html', {'form': form, 'materia_prima': materia})

@login_required
@permission_required('interna.view_movimientomateriaprima', raise_exception=True)
def movimientos_listar(request):
    movimientos = (
        MovimientoMateriaPrima.objects
        .select_related("materia_prima", "responsable")
        .all()
    )

    return render(request,"interna/inventario/movimientos_listar.html", {"movimientos": movimientos})

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
    desde_producto = request.GET.get('origen') == 'producto'
    datos = request.POST if request.method == 'POST' else None
    form = ConfiguracionPrecioForm(datos, instance=configuracion)

    for campo in form.fields.values():
        campo.widget.attrs['class'] = ('form-check-input'
            if campo.widget.input_type == 'checkbox'
            else 'form-control'
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Configuración de Precios Actualizada')
        return redirect(request.get_full_path())
    return render(request, 'interna/producto/configuracion_precio.html', {'form': form, 'desde_producto': desde_producto})

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
            'detalles_personalizados__fabricaciones__responsable', 'pagos', 'historial_etapas__responsable',
        ), pk=pk)

    contexto = {'pedido': pedido}
    contexto.update(_contexto_etapas_pedido(pedido))

    if pedido.tipo_pedido == 'personalizado':
        resumen = resumen_pagos_personalizado(pedido)
        contexto.update({
            'total_abonado': resumen['abonado'],
            'saldo_pendiente': resumen['saldo'],
            'puede_editar_encargo': (_puede_editar_encargo(pedido)),
            'puede_fabricar_encargo': (
                pedido.estado in ('pendiente', 'pagado')
                and pedido.etapa in (
                    None, '', 'en_confeccion'
                )
                and (
                    0 < pedido.adelanto_requerido
                    <= resumen['total']
                )
                and resumen['adelanto_pendiente'] == 0
            ),
            'enlace_cliente': (crear_enlace_pedido_personalizado(request, pedido)
            )
        })

        return render(request, 'interna/inventario/pedido_personalizado_detalles.html', contexto)

    return render(request, 'interna/inventario/pedido_detalles.html', contexto)

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

@login_required
@permission_required('interna.change_pedido', raise_exception=True)
@require_POST
def pedido_cambiar_estado(request, pk):
    try:
        actualizado = _registrar_etapa_pedido(pk, request.POST.get('etapa', ''), request.POST.get('etapa_anterior'), request.user)

    except ValidationError as error:
        messages.error(request, ' '.join(error.messages))

    else:
        if actualizado:
            messages.success(request, 'Etapa del Pedido Actualizada')
        else:
            messages.info(request, 'La Etapa ya Estaba Registrada')

    return redirect('pedido_detalles', pk=pk)

@login_required
@permission_required("interna.view_consulta", raise_exception=True)
@require_http_methods(["GET"])
def consultas_listar(request):
    q = request.GET.get("q", "").strip()
    estado = request.GET.get("estado", "")

    consultas = Consulta.objects.all().order_by("-fecha", "-pk")

    if q:
        consultas = consultas.filter(
            Q(nombre__icontains=q)
            | Q(correo__icontains=q)
            | Q(asunto__icontains=q)
            | Q(mensaje__icontains=q)
        )

    if estado in ("pendiente", "respondida"):
        consultas = consultas.filter(estado=estado)
    else:
        estado = ""

    return render(
        request,
        "interna/inventario/consulta_listar.html",
        {
            "consultas": consultas,
            "q": q,
            "estado": estado,
        },
    )

@login_required
@permission_required("interna.view_consulta", raise_exception=True)
@require_http_methods(["GET"])
def consulta_detalle(request, pk):
    consulta = get_object_or_404(Consulta, pk=pk)
    pedido_generado = Pedido.objects.filter(consulta_origen=consulta).first()

    return render(request, "interna/inventario/consulta_detalle.html", {"consulta": consulta, 'pedido_generado': pedido_generado})

def _datos_contacto_cliente(cliente):
    return {
        'nombre_invitado': f'{cliente.nombre} {cliente.apellido}'.strip(),
        'rut_invitado': cliente.rut,
        'email_invitado': cliente.correo,
        'telefono_invitado': cliente.telefono,
        'direccion_invitado': cliente.direccion
    }

@login_required
@permission_required('interna.add_pedido', raise_exception=True)
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def pedido_personalizado_crear(request, consulta_pk=None):
    es_post = request.method == 'POST'
    datos = request.POST if es_post else None
    archivos = request.FILES if es_post else None
    consulta = None
    incial = {}

    if consulta_pk is not None:
        if not request.user.has_perm('interna.view_consulta'):
            raise PermissionDenied

        consultas = Consulta.objects.all()

        if es_post:
            consultas = consultas.select_for_update()

        consulta = get_object_or_404(consultas, pk=consulta_pk, es_personalizado=True)
        existente = Pedido.objects.filter(consulta_origen=consulta).first()

        if existente:
            messages.info(request, 'Esta Consulta ya Tiene un Pedido Asociado')
            return redirect('pedido_detalles', pk=existente.pk)

        if consulta.cliente_id:
            inicial = _datos_contacto_cliente(consulta.cliente)
            inicial['cliente'] = consulta.cliente_id
        else:
            inicial = {
                'nombre_invitado': consulta.nombre,
                'email_invitado': consulta.correo
            }

    pedido = Pedido(tipo_pedido='personalizado')
    form_pedido = PedidoPersonalizadoCrearForm(datos, instance=pedido, initial=inicial, prefix='pedido')

    campo_cliente = form_pedido.fields['cliente']

    if consulta and consulta.cliente_id:
        if not campo_cliente.queryset.filter(pk=consulta.cliente_id).exists():
            messages.error(request,'La cuenta vinculada no está disponible, revisa su estado antes de preparar el pedido')
            return redirect('consulta_detalle', pk=consulta.pk)

        campo_cliente.disabled = True

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
            cliente = form_pedido.cleaned_data['cliente']

            if cliente:
                cuenta = get_object_or_404(User.objects.select_for_update(), pk=cliente.usuario_id)

                if not cuenta.is_active:
                    form_pedido.add_error('cliente', 'La Cuenta fue Deshabilitada, Revisa el Cliente')
                    pedido_valido = False

            if pedido_valido:
                pedido = form_pedido.save(commit=False)
                pedido.consulta_origen = consulta
                pedido.tipo_pedido = 'personalizado'
                pedido.estado = 'pendiente'
                pedido.etapa = None
                pedido.save()

                for indice, fila in enumerate(filas_a_guardar):
                    detalle = fila.save(commit=False)
                    detalle.pedido = pedido

                    if (
                        indice == 0
                        and consulta
                        and consulta.imagen_referencia
                        and not detalle.imagen_referencia
                    ):
                        nombre = Path(consulta.imagen_referencia.name).name

                        with consulta.imagen_referencia.open('rb') as archivo:
                            detalle.imagen_referencia.save(nombre, File(archivo), save=False)

                    detalle.save()
                    fila.materiales.instance = detalle
                    fila.materiales.save()

                messages.success(request, 'Pedido Personalizado Creado')
                return redirect('pedido_detalles', pk=pedido.pk)

    clientes_datos = {str(cliente.pk): _datos_contacto_cliente(cliente) for cliente in campo_cliente.queryset}

    return render(request, 'interna/inventario/pedido_personalizado_crear.html',
        {
            'form_pedido': form_pedido,
            'articulos': articulos,
            'consulta': consulta,
            'clientes_datos': clientes_datos
        }
    )

def _puede_editar_encargo(pedido):
    return (
        not pedido.cancelado
        and pedido.estado == 'pendiente'
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

    avisos = {
        'actualizado': 'Revisa el Resultado en el Registro de Pagos',
        'rechazado': 'El Intento no se Completó, Puedes Revisar el Registro y Volver a Intentar',
        'sin_confirmar': 'No Pudimos Confirmar el Resultado del Pago',
        'pago_en_tramite': 'Ya Existe un Pago Pendiente o un Comprobante en Revisión',
        'sin_saldo': 'Este Pedido no tiene Saldo Pendiente',
        'sin_monto': 'El Importe Seleccionado ya está Cubierto',
        'total_cambiado': 'El Total Cambió, Revisa los Importes antes de Continuar',
        'opcion_invalida': 'Selecciona una Opción de Pago Válida',
        'error_inicio': 'No Pudimos Iniciar Webpay, Inténtalo Nuevamente',
        'condiciones_invalidas': 'Contacta a la Tienda para Revisar las Condiciones de Pago',
        'monto_fuera_de_rango': 'Contacta a la Tienda para Revisar el Importe del Pago',
        'pedido_cancelado': 'Este Pedido Está Cancelado y no Admite Nuevos Pagos'
    }

    respuesta = render(request, 'interna/inventario/pedido_personalizado_publico.html',
        {
            'pedido': pedido,
            'resumen': resumen,
            'token': token,
            'aviso': avisos.get(request.GET.get('aviso')),
            'pago_webpay_pendiente': pedido.pagos.filter(metodo='webpay', estado='pendiente').first(),
            'hay_pago_en_tramite': pedido.pagos.filter(estado__in=["pendiente", "en_revision"]).exists()
        }
    )

    respuesta['Referrer-Policy'] = 'same-origin'
    respuesta['X-Robots-Tag'] = 'noindex, nofollow'

    return respuesta

@transaction.atomic
def _registrar_fabricacion_personalizada(pedido_pk, detalle_pk, cantidad, fabricadas_iniciales, responsable):
    pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=pedido_pk, tipo_pedido='personalizado')

    if pedido.cancelado:
        raise ValidationError('No se Puede Fabricar para un Pedido Cancelado')

    detalle = get_object_or_404(DetallePedidoPersonalizado.objects.select_for_update(), pk=detalle_pk, pedido=pedido)
    resumen = resumen_pagos_personalizado(pedido)

    if pedido.estado not in ('pendiente', 'pagado') or pedido.etapa not in (None, '', 'en_confeccion'):
        raise ValidationError('Este Pedido ya no Admite Fabricación')

    if not (0 < pedido.adelanto_requerido <= resumen['total']):
        raise ValidationError('Revisa el Total y el Adelanto Requerido del Pedido')

    if resumen['adelanto_pendiente'] > 0:
        raise ValidationError('El Adelanto debe estar Cubierto por Pagos Aprobados')

    if detalle.unidades_fabricadas != fabricadas_iniciales:
        raise ValidationError('La Fabricación de este Artículo Cambió, Vuelve a abrir el Formulario')

    if cantidad <= 0 or cantidad > detalle.unidades_pendientes:
        raise ValidationError(f'Puedes Fabricar entre 1 y ' f'{detalle.unidades_pendientes} Unidades Pendientes')

    receta = list(MaterialPedidoPersonalizado.objects
        .select_for_update()
        .filter(detalle=detalle)
        .order_by('materia_prima_id')
    )

    if not receta:
        raise ValidationError('El Artículo no Tiene una Receta Registrada')

    materias = {materia.pk: materia
        for materia in (MateriaPrima.objects
            .select_for_update()
            .filter(pk__in=[fila.materia_prima_id for fila in receta])
            .order_by('pk')
        )
    }

    consumos = []

    for fila in receta:
        materia = materias[fila.materia_prima_id]

        if not materia.estado or fila.cantidad_por_unidad <= 0:
            raise ValidationError(f'Revisa la Cantidad o el Estado de {materia.nombre}')

        consumo = fila.cantidad_por_unidad * cantidad

        if materia.cantidad_actual < consumo:
            raise ValidationError(f'No hay Stock Suficiente de {materia.nombre}')

        consumos.append((materia, consumo))

    actualizado = DetallePedidoPersonalizado.objects.filter(
        pk=detalle.pk,
        unidades_fabricadas=fabricadas_iniciales,
        cantidad__gte=F('unidades_fabricadas') + cantidad,
    ).update(
        unidades_fabricadas=F('unidades_fabricadas') + cantidad,
    )

    if not actualizado:
        raise ValidationError('El Artículo Cambió, Vuelve a Abrir el Formulario')

    fabricacion = FabricacionPedidoPersonalizado.objects.create(detalle=detalle, cantidad=cantidad, responsable=responsable)

    for materia, consumo in consumos:
        actualizado = MateriaPrima.objects.filter(pk=materia.pk, estado=True, cantidad_actual__gte=consumo).update(
            cantidad_actual=F('cantidad_actual') - consumo)

        if not actualizado:
            raise ValidationError(f'Cambió el Stock o el Estado de {materia.nombre}')

        materia.refresh_from_db(fields=['cantidad_actual'])

        MovimientoMateriaPrima.objects.create(
            materia_prima=materia,
            tipo='SALIDA',
            motivo='FABRICACION',
            cantidad=consumo,
            saldo_resultante=materia.cantidad_actual,
            responsable=responsable,
            fabricacion_personalizada=fabricacion,
            observacion=(f'Pedido Personalizado #{pedido.pk}, ' f'Artículo #{detalle.pk}: ' f'Fabricación de {cantidad} Unidad(es)')
        )

    if not pedido.etapa:
        pedido.etapa = 'en_confeccion'
        pedido.save(update_fields=['etapa'])

        HistorialEtapaPedido.objects.create(pedido=pedido, etapa='en_confeccion', responsable=responsable)

    return fabricacion

@login_required
@permission_required('interna.fabricar_producto', raise_exception=True)
@require_http_methods(['GET', 'POST'])
def pedido_personalizado_fabricar(request, pk, detalle_pk):
    pedido = get_object_or_404(Pedido, pk=pk, tipo_pedido='personalizado')
    detalle = get_object_or_404(DetallePedidoPersonalizado, pk=detalle_pk, pedido=pedido)
    form = FabricacionPedidoPersonalizadoForm(request.POST if request.method == 'POST' else None,
        initial={
            'cantidad': 1,
            'fabricadas_iniciales': detalle.unidades_fabricadas
        })

    if request.method == 'POST' and form.is_valid():
        try:
            fabricacion = _registrar_fabricacion_personalizada(
                pedido.pk,
                detalle.pk,
                form.cleaned_data['cantidad'],
                form.cleaned_data['fabricadas_iniciales'],
                request.user
            )

        except ValidationError as error:
            form.add_error(None, error)

        else:
            _avisar_materiales_fabricacion(request, fabricacion)

            messages.success(request, 'Fabricación Registrada y Materiales Descontados')
            return redirect('pedido_detalles', pk=pedido.pk)

    return render(request, 'interna/inventario/pedido_personalizado_fabricar.html',
        {
            'pedido': pedido,
            'detalle': detalle,
            'form': form,
            'materiales': (detalle.materiales.select_related('materia_prima')
            )
        })

def _contexto_etapas_pedido(pedido):
    contexto = {
        'etapas_disponibles': [],
        'aviso_etapas': ''
    }

    if pedido.cancelado:
        contexto['aviso_etapas'] = ('El Pedido Está Cancelado y no Admite Cambios de Etapa')
        return contexto

    flujos = {
        ('normal', 'envio'): ['enviado', 'entregado'],
        ('normal', 'retiro'): ['disponible_retiro', 'entregado'],
        ('personalizado', 'envio'): ['en_confeccion', 'listo','enviado', 'entregado'],
        ('personalizado', 'retiro'): ['en_confeccion', 'disponible_retiro', 'entregado']
    }

    flujo = flujos.get((pedido.tipo_pedido, pedido.tipo_entrega))

    if flujo is None:
        contexto['aviso_etapas'] = ('Revisa el Tipo de Pedido y de Entrega')
        return contexto

    actual = pedido.etapa or ''

    if actual == 'entregado':
        contexto['aviso_etapas'] = ('El Pedido ya fue Entregado')
        return contexto

    if not actual:
        indice = -1
    elif actual in flujo:
        indice = flujo.index(actual)

    elif (pedido.tipo_pedido == 'normal' and actual in ('en_confeccion', 'listo')):
        indice = -1
    elif (pedido.tipo_pedido == 'personalizado' and pedido.tipo_entrega == 'retiro' and actual == 'listo'):
        indice = 0
    else:
        contexto['aviso_etapas'] = ('La Etapa Actual no Corresponde a este Flujo de Entrega')
        return contexto

    siguiente = flujo[indice + 1]

    if pedido.tipo_pedido == 'normal':
        if pedido.estado != 'pagado':
            contexto['aviso_etapas'] = ('El Pedido debe estar Pagado para Gestionar su Entrega')
            return contexto

    else:
        if pedido.estado not in ('pendiente', 'pagado'):
            contexto['aviso_etapas'] = ('El Estado del Pedido no Permite Continuar')
            return contexto

        resumen = resumen_pagos_personalizado(pedido)

        if not (
            0 < pedido.adelanto_requerido <= resumen['total']
        ):
            contexto['aviso_etapas'] = ('Revisa el Total y el Adelanto Requerido')
            return contexto

        if resumen['adelanto_pendiente'] > 0:
            contexto['aviso_etapas'] = ('Falta Cubrir el Adelanto con Pagos Aprobados')
            return contexto

        articulos = list(pedido.detalles_personalizados.all())

        if siguiente != 'en_confeccion' and (
            not articulos
            or any(articulo.unidades_fabricadas != articulo.cantidad for articulo in articulos)
        ):
            contexto['aviso_etapas'] = ('Falta Completar la Fabricación de Todos los Artículos')
            return contexto

        if (siguiente == 'entregado' and resumen['saldo'] > 0):
            contexto['aviso_etapas'] = ('Debes Confirmar el Pago del Saldo antes de Entregar')
            return contexto

    contexto['etapas_disponibles'] = [(siguiente, dict(Pedido.ETAPAS)[siguiente])]

    return contexto

@transaction.atomic
def _registrar_etapa_pedido(pedido_pk, nueva_etapa, etapa_anterior, responsable):
    pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=pedido_pk)

    if pedido.cancelado:
        raise ValidationError('El Pedido Está Cancelado y no Admite Cambios de Etapa')

    actual = pedido.etapa or ''

    if nueva_etapa and nueva_etapa == actual:
        return False

    if etapa_anterior != actual:
        raise ValidationError('El Pedido Cambió, Revisa su Etapa Actual e Inténtalo Nuevamente')

    contexto = _contexto_etapas_pedido(pedido)
    permitidas = [valor for valor, etiqueta in contexto['etapas_disponibles']]

    if nueva_etapa not in permitidas:
        raise ValidationError(contexto['aviso_etapas'] or 'La Etapa Seleccionada no está Permitida')

    actualizado = Pedido.objects.filter(pk=pedido.pk, etapa=pedido.etapa, estado=pedido.estado, cancelado=False).update(etapa=nueva_etapa)

    if not actualizado:
        raise ValidationError('El Pedido Cambió, Vuelve a Consultar sus Detalles')

    HistorialEtapaPedido.objects.create(pedido=pedido, etapa=nueva_etapa, responsable=responsable)

    return True

@login_required
@permission_required('interna.change_pedido', raise_exception=True)
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def pedido_personalizado_datos_editar(request, pk):
    consulta = Pedido.objects

    if request.method == 'POST':
        consulta = consulta.select_for_update()

    pedido = get_object_or_404(consulta, pk=pk, tipo_pedido='personalizado')

    if pedido.etapa == 'entregado':
        messages.error(request, 'No se Pueden Modificar los Datos de un Pedido Entregado')
        return redirect('pedido_detalles', pk=pedido.pk)

    datos = request.POST if request.method == 'POST' else None

    form = PedidoPersonalizadoDatosForm(data=datos, instance=pedido)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Datos del Pedido Actualizados')
        return redirect('pedido_detalles', pk=pedido.pk)

    return render(request, 'interna/inventario/pedido_personalizado_datos_editar.html',
        {
            'form': form,
            'pedido': pedido,
        }
    )

@login_required
@permission_required('interna.change_pedido', raise_exception=True)
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def pedido_personalizado_receta_editar(request, pk, detalle_pk):
    es_post = request.method == 'POST'
    pedidos = Pedido.objects.filter(tipo_pedido='personalizado')
    detalles = DetallePedidoPersonalizado.objects.all()

    if es_post:
        pedidos = pedidos.select_for_update()
        detalles = detalles.select_for_update()

    pedido = get_object_or_404(pedidos, pk=pk)
    detalle = get_object_or_404(detalles, pk=detalle_pk, pedido=pedido)

    receta_bloqueada = (
        pedido.cancelado
        or pedido.estado not in ('pendiente', 'pagado')
        or pedido.etapa not in (None, '', 'en_confeccion')
        or detalle.unidades_fabricadas > 0
        or detalle.fabricaciones.exists()
    )

    if receta_bloqueada:
        messages.error(request, 'La receta no se puede modificar, el artículo ya tiene fabricaciones o la etapa del pedido no permite cambios')
        return redirect('pedido_detalles', pk=pedido.pk)

    materiales = MaterialPedidoPersonalizadoFormSet(data=request.POST if es_post else None, instance=detalle, prefix='materiales')

    fila_vacia = materiales.empty_form
    filas = list(materiales.forms)
    filas.append(fila_vacia)

    for fila in filas:
        disponibles = Q(estado=True)

        if fila.instance.pk:
            disponibles |= Q(pk=fila.instance.materia_prima_id)

        fila.fields['materia_prima'].queryset = (
            MateriaPrima.objects
            .filter(disponibles)
            .order_by('nombre')
        )

        fila.fields['materia_prima'].widget.attrs['class'] = 'form-select'
        fila.fields['cantidad_por_unidad'].widget.attrs['class'] = 'form-control'
        fila.fields['DELETE'].widget.attrs['class'] = 'form-check-input'
        fila.fields['DELETE'].label = 'Quitar este material'

    if es_post and materiales.is_valid():
        materiales.save()
        messages.success(request, 'Receta del artículo actualizada.')
        return redirect('pedido_detalles', pk=pedido.pk)

    return render(request, 'interna/inventario/pedido_personalizado_receta_editar.html',
        {
            'pedido': pedido,
            'detalle': detalle,
            'materiales': materiales,
            'fila_vacia': fila_vacia,
        }
    )

@login_required
@permission_required('interna.cancelar_pedido', raise_exception=True)
@require_POST
@transaction.atomic
def pedido_personalizado_cancelar(request, pk):
    pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=pk, tipo_pedido='personalizado')

    if pedido.cancelado:
        messages.info(request, 'Este Pedido ya Está Cancelado')
        return redirect('pedido_detalles', pk=pedido.pk)

    if pedido.etapa == 'entregado':
        messages.error(request, 'No se Puede Cancelar un Pedido que ya fue Entregado')
        return redirect('pedido_detalles', pk=pedido.pk)

    if pedido.pagos.filter(estado__in=['pendiente', 'en_revision']).exists():
        messages.error(request, 'Primero Debes Resolver los Pagos Pendientes o en Revisión')
        return redirect('pedido_detalles', pk=pedido.pk)

    form = CancelacionPedidoPersonalizadoForm(data=request.POST)

    if not form.is_valid():
        messages.error(request,'Indica un Motivo Válido')
        return redirect('pedido_detalles', pk=pedido.pk)

    pedido.cancelado = True
    pedido.fecha_cancelacion = timezone.now()
    pedido.cancelado_por = request.user
    pedido.motivo_cancelacion = form.cleaned_data['motivo']

    pedido.save(update_fields=['cancelado', 'fecha_cancelacion', 'cancelado_por', 'motivo_cancelacion'])

    messages.success(request, 'Pedido cancelado correctamente.')
    return redirect('pedido_detalles', pk=pedido.pk)

def _avisar_stock_materia(request, materia, stock_anterior, stock_actual):
    unidad = materia.get_unidad_de_medida_display()

    if stock_actual <= 0 and stock_anterior > 0:
        nivel = messages.ERROR
        mensaje = (f'Stock Agotado Para: {materia.nombre}')

    elif (
        stock_anterior > materia.cantidad_critica
        and 0 < stock_actual <= materia.cantidad_critica
    ):
        nivel = messages.WARNING
        cantidad = floatformat(stock_actual, '-3')
        minimo = floatformat(materia.cantidad_critica, '-3')
        mensaje = (f'Stock Crítico Para: {materia.nombre}, Quedan {cantidad} {unidad} (Mínimo: {minimo} {unidad})')

    else:
        return

    transaction.on_commit(lambda: messages.add_message(request, nivel, mensaje), robust=True)

def _avisar_materiales_fabricacion(request, fabricacion):
    movimientos = fabricacion.movimientos.select_related('materia_prima')

    for movimiento in movimientos:
        _avisar_stock_materia(request, movimiento.materia_prima, movimiento.saldo_resultante + movimiento.cantidad, movimiento.saldo_resultante)