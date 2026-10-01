from django.urls import path, include
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'productos', views.ProductoViewSet, 'producto')

urlpatterns = [
    path('', include(router.urls)),
    path('carrito/', views.CarritoAPIView.as_view(), name='api_carrito'),
    path('carrito/pagar/', views.PagarCarritoAPIView.as_view(), name='api_pagar_carrito'),
]