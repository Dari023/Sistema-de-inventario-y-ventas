from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('inventario/', views.inventario, name='inventario'),
    path('producto/', views.producto_listar, name='producto_listar'),
    path('producto/crear/', views.producto_crear, name='producto_crear'),
    path('producto/editar/<int:pk>/', views.producto_editar, name='producto_editar'),
    path('producto/detalles/<int:pk>/', views.producto_detalles, name='producto_detalles'),
    path('producto/fabricar/<int:pk>/', views.producto_fabricar,name="producto_fabricar"),
    path('categoria/', views.categoria_listar, name='categoria_listar'),
    path('categoria/crear/', views.categoria_crear, name='categoria_crear'),
    path('categoria/editar/<int:pk>/', views.categoria_editar, name='categoria_editar'),
    path('materia_prima/', views.materia_prima_listar, name='materia_prima_listar'),
    path('materia_prima/detalles/<int:pk>/', views.materia_prima_detalles, name='materia_prima_detalles'),
    path('materia_prima_crear/', views.materia_prima_crear, name='materia_prima_crear'),
    path('materia_prima/editar/<int:pk>/', views.materia_prima_editar, name='materia_prima_editar'),
    path('productos/<int:producto_id>/materias-primas/', views.gestionar_materias_producto, name='gestionar_materias_producto'),
    path('movimientos/', views.movimientos_listar, name='movimientos_listar'),
    path('movimientos/<int:pk>/observacion/', views.movimiento_observacion_editar, name='movimiento_observacion_editar'),
    path('productos/precio-sugerido/', views.producto_precio_sugerido, name='producto_precio_sugerido'),
    path('configuracion/precios/', views.configuracion_precio_editar, name='configuracion_precio_editar'),
    path('pedidos/', views.pedido_listar, name='pedido_listar'),
    path('pedidos/<int:pk>/', views.pedido_detalles, name='pedido_detalles'),
]
