from django.shortcuts import redirect
from django.urls import resolve, Resolver404
from .models import Usuario

def cambio_password_obligatorio(get_response):
    def middleware(request):
        pendiente = (
            request.user.is_authenticated
            and Usuario.objects.filter(user_id=request.user.pk,cambio_password_pendiente=True).exists()
        )

        if pendiente:
            try:
                ruta = resolve(request.path_info).url_name
            except Resolver404:
                return get_response(request)

            permitidas = {
                'login',
                'logout',
                'password_cambiar',
                'password_recuperar',
                'password_recuperar_enviado',
                'password_restablecer',
                'password_restablecer_completo'
            }

            if ruta not in permitidas:
                return redirect('password_cambiar')

        return get_response(request)

    return middleware