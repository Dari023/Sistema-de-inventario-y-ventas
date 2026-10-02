from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('producto/', views.producto_listar, name='producto_listar'),
    path('producto/crear/', views.producto_crear, name='producto_crear'),
    path('producto/editar/<int:pk>/', views.producto_editar, name='producto_editar'),
    path('producto/detalles/<int:pk>/', views.producto_detalles, name='producto_detalles'),
    path('categoria/', views.categoria_listar, name='categoria_listar'),
    path('categoria/crear/', views.categoria_crear, name='categoria_crear'),
    path('categoria/editar/<int:pk>/', views.categoria_editar, name='categoria_editar'),
    path('materia_prima/', views.materia_prima_listar, name='materia_prima_listar'),
    path('materia_prima/detalles/<int:pk>/', views.materia_prima_detalles, name='materia_prima_detalles'),
    path('materia_prima_crear/', views.materia_prima_crear, name='materia_prima_crear'),
    path('materia_prima/editar/<int:pk>/', views.materia_prima_editar, name='materia_prima_editar'),
    path('productos/<int:producto_id>/materias-primas/', views.gestionar_materias_producto, name="gestionar_materias_producto")
]
