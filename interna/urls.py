from django.contrib import admin
from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('producto/', views.producto_listar, name='producto_listar'),
    path('producto/crear/', views.producto_crear, name='producto_crear'),
    path('producto/editar/<int:pk>/', views.producto_editar, name='producto_editar'),
    path('producto/detalles/<int:pk>/', views.producto_detalles, name='producto_detalles'),
]
