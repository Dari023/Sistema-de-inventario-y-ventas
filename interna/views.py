from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
from django.contrib.auth.decorators import login_required, permission_required
from .models import Producto, ProductoMateriaPrima, MateriaPrima, CategoriaProducto, MovimientoMateriaPrima
from django.db.models import F
from .forms import (
    ProductoForm, 
    MateriaPrimaForm, 
    ProductoMateriaPrimaForm, 
    CategoriaProductoForm, 
    ProductoMateriaPrimaFormSet, 
    FabricacionForm,
    MovimientoObservacionForm)


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
    return render(
        request, "interna/producto/producto_crear.html",
        {
            "form": form,
            "producto": producto if editando else None,
            "materiales": materiales,
        },
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