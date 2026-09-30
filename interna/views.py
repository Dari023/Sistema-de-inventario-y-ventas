from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import (login_required, permission_required)
from .models import Producto, ProductoMateriaPrima, MateriaPrima
from .forms import ProductoForm, MateriaPrimaForm, ProductoMateriaPrimaForm

# Create your views here.

@login_required
def home(request):
    return render(request, 'interna/base.html')

@login_required
def producto_listar(request):
    productos = Producto.objects.all()
    return render(request, 'interna/producto/producto_listar.html', {'productos': productos})

def producto_crear(request):
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('producto_listar')
    else:
        form = ProductoForm()
    return render(request, 'interna/producto/producto_crear.html', {'form': form})

def producto_editar(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            return redirect('producto_listar')
    else:
        form = ProductoForm(instance=producto)
    return render(request, 'interna/producto/producto_crear.html', {'form': form, 'producto': producto})

def producto_detalles(request, pk):
    producto = get_object_or_404(Producto, pk=pk)
    return render(request, 'interna/producto/producto_detalles.html', {'producto': producto})

def materia_prima_listar(request):
    materia_prima = MateriaPrima.objects.all()
    return render(request, 'interna/inventario/materia_prima_listar.html', {'materia_prima': materia_prima})

def materia_prima_crear(request):
    if request.method == "POST":
        form = MateriaPrimaForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(
                request,
                "Materia Prima Registrada Correctamente.",
            )
            return redirect('materia_prima_listar')
    else:
        form = MateriaPrimaForm()
    return render(
        request,
        'interna/inventario/materia_prima_crear.html',
        {"form": form},
    )

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