from django.urls import path, include
from rest_framework import routers
from . import views
from rest_framework_simplejwt.views import TokenRefreshView

router = routers.DefaultRouter()
router.register(r'productos', views.ProductoViewSet, 'producto')
router.register(r'categorias', views.CategoriaProductoViewSet, basename='categoria',)

urlpatterns = [
    path('', include(router.urls)),
    path('carrito/', views.CarritoAPIView.as_view(), name='api_carrito'),
    path('registro/', views.RegistroClienteView.as_view(), name='api_registro'),
    path('mi-cuenta/', views.MiCuentaView.as_view(), name='api_mi_cuenta'),
    path('login/', views.LoginCorreoView.as_view(), name='api_login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='api_token_refresh'),
    path('compras/<uuid:id_compra>/', views.CompraDetailView.as_view(), name='compra-detail'),
    path('webpay/iniciar/', views.WebpayIniciarView.as_view(), name='api_webpay_iniciar'),
    path('webpay/retorno/', views.WebpayRetornoView.as_view(), name='api_webpay_retorno'),
    path('mi-cuenta/pedidos/', views.HistorialPedidosView.as_view(), name='api_historial_pedidos'),
    path('resenas/<str:token>/', views.ResenaCompraView.as_view(), name='api_resena_compra'),
    path('productos/<int:pk>/resenas/', views.ResenasProductoView.as_view(), name='api_resenas_producto'),
    path('preguntas-frecuentes/', views.PreguntasFrecuentesView.as_view(), name='api_preguntas_frecuentes')
]