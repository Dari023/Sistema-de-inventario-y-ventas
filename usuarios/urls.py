from django.urls import path
from . import views
from django.urls import reverse_lazy
from django.contrib.auth import views as auth_views
from .forms import (RecuperarPasswordPersonalForm, RestablecerPasswordPersonalForm)

urlpatterns = [
    path('usuarios/', views.UsuarioListView, name='usuario-list'),
    path('usuarios/nuevo/', views.UsuarioCreateView, name='usuario-create'),
    path('usuarios/editar/<int:id>/', views.UsuarioUpdateView, name='usuario-update'),
    path('login/', views.login_view, name="login"),
    path('logout/', views.logout_view, name="logout"),
    path('clientes/<int:id>/estado/', views.cliente_cambiar_estado, name='cliente-cambiar-estado')
]

urlpatterns += [
    path('password/cambiar/', views.password_cambiar, name='password_cambiar'),
    path('password/recuperar/',
        auth_views.PasswordResetView.as_view(
            form_class=RecuperarPasswordPersonalForm,
            template_name='usuarios/password_form.html',
            email_template_name='usuarios/password_email.txt',
            subject_template_name='usuarios/password_asunto.txt',
            success_url=reverse_lazy('password_recuperar_enviado'),
            extra_context={
                'titulo': 'Recuperar contraseña',
                'texto': 'Ingresa el correo asociado a tu cuenta del personal.',
            }
        ),
        name='password_recuperar'
    ),
    path(
        'password/enviado/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='usuarios/password_form.html',
            extra_context={
                'titulo': 'Revisa tu correo',
                'texto': (
                    'Si el correo corresponde a una cuenta activa del personal, recibirás un enlace para definir una contraseña nueva'
                )
            }
        ),
        name='password_recuperar_enviado'
    ),
    path(
        'password/restablecer/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            form_class=RestablecerPasswordPersonalForm,
            template_name='usuarios/password_form.html',
            success_url=reverse_lazy('password_restablecer_completo'),
            extra_context={'titulo': 'Definir nueva contraseña'}
        ),
        name='password_restablecer'
    ),
    path(
        'password/completado/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='usuarios/password_form.html',
            extra_context={
                'titulo': 'Contraseña restablecida',
                'texto': 'Ya puedes ingresar con tu nueva contraseña.'
            }
        ),
        name='password_restablecer_completo'
    )
]