from django.urls import path
from . import views

urlpatterns = [
    path('usuarios/', views.UsuarioListView, name='usuario-list'),
    path('usuarios/nuevo/', views.UsuarioCreateView, name='usuario-create'),
    path('usuarios/editar/<int:id>/', views.UsuarioUpdateView, name='usuario-update'),
    path('usuarios/eliminar/<int:id>/', views.UsuarioDeleteView, name='usuario-delete'),
    path('login/', views.login_view, name="login"),
    path('logout/', views.logout_view, name="logout"),
]