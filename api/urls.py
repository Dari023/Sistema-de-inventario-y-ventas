from django.urls import path, include
from rest_framework import routers
from . import views
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

router = routers.DefaultRouter()
router.register(r'productos', views.ProductoViewSet, 'producto')
router.register(r'categorias', views.CategoriaProductoViewSet, basename='categoria',)

urlpatterns = [
    path('', include(router.urls)),
    path('carrito/', views.CarritoAPIView.as_view(), name='api_carrito'),
    path('carrito/pagar/', views.PagarCarritoAPIView.as_view(), name='api_pagar_carrito'),
    path('registro/', views.RegistroClienteView.as_view(), name='api_registro'),
    path('login/', views.LoginView.as_view(), name='api_login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),
]