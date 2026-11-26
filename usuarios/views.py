from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash, login, logout
from django.contrib.auth.models import Group, User
from django.contrib.auth.forms import PasswordChangeForm, SetPasswordForm, AuthenticationForm
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.views.decorators.http import require_http_methods
from .acceso import es_personal
from .models import Usuario, Rol
from .forms import UsuarioForm, LoginPersonalForm
from django.views.decorators.http import require_POST
from api.models import Cliente
from django.db.models import Q
from django.contrib.auth.decorators import login_required, permission_required

@login_required
@permission_required('usuarios.view_usuario', raise_exception=True)
def UsuarioListView(request):
    query = request.GET.get('q', '').strip()
    usuarios = Usuario.objects.select_related(
        'user',
        'rol'
    ).all()

    
    if query:
        usuarios = usuarios.filter(
            Q(user__username__icontains=query) | 
            Q(user__email__icontains = query) |
            Q(nombre_completo__icontains=query) |
            Q(rut__icontains=query)
        )

            
    contexto = {
        'usuarios': usuarios,
        'query': query
    }
    return render(request, 'usuarios/usuario_list.html', contexto)

@sensitive_post_parameters('password')
@login_required
@permission_required('usuarios.add_usuario', raise_exception=True)
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def UsuarioCreateView(request):
    form = UsuarioForm(request.POST if request.method == 'POST' else None,initial={'activo': True})
    if request.method == "POST" and form.is_valid():
        user = User.objects.create_user(
            username=form.cleaned_data['username'],
            email=form.cleaned_data['email'],
            password=form.cleaned_data['password'],
            is_active=form.cleaned_data['activo']
        )
        usuario = form.save(commit=False)
        usuario.user = user
        usuario.rol = Rol.objects.get(nombre='Colaborador')
        usuario.cambio_password_pendiente = True
        usuario.save()

        user.groups.add(Group.objects.get(name='Colaboradores'))

        messages.success(request, 'Colaborador Creado, Deberá Cambiar su Contraseña al Ingresar')
        return redirect('usuario-list')

    return render(request, 'usuarios/usuario_form.html', {
        'form': form,
        'action': 'Crear',
    })

@sensitive_post_parameters('password')
@login_required
@permission_required('usuarios.change_usuario', raise_exception=True)
@require_http_methods(['GET', 'POST'])
@transaction.atomic
def UsuarioUpdateView(request, id):
    usuario = get_object_or_404(Usuario.objects.select_related('user', 'rol'), pk=id, rol__nombre='Colaborador')
    
    form = UsuarioForm(
        request.POST if request.method == 'POST' else None,
        instance=usuario,
        initial={
            'username': usuario.user.username,
            'email': usuario.user.email,
            'activo': usuario.user.is_active
        }
    )

    form.fields.pop('password', None)

    if request.method == 'POST' and form.is_valid():
        user = usuario.user
        user.username = form.cleaned_data['username']
        user.email = form.cleaned_data['email']
        user.is_active = form.cleaned_data['activo']
        user.save(update_fields=['username', 'email', 'is_active'])

        form.save()

        messages.success(request, 'Cuenta Actualizada')
        return redirect('usuario-list')

    return render(request, 'usuarios/usuario_form.html', {'form': form, 'action': 'Modificar'})

@sensitive_post_parameters()
@never_cache
@require_http_methods(['GET', 'POST'])
def login_view(request):
    if request.user.is_authenticated:

        if not es_personal(request.user):
            raise PermissionDenied

        return redirect('home')

    form = LoginPersonalForm(request, data=request.POST if request.method == 'POST' else None)
        
    if request.method == "POST" and form.is_valid():
        user = form.get_user()

        if es_personal(user):
            login(request, user)

            pendiente = Usuario.objects.filter(user=user, cambio_password_pendiente=True).exists()

            return redirect('password_cambiar' if pendiente else 'home')

        form.add_error(None,'Esta Cuenta no Tiene Acceso al Panel del Personal')

    return render(request, 'usuarios/login.html', {'form': form})

@sensitive_post_parameters()
@never_cache
@login_required
@require_http_methods(['GET', 'POST'])
def password_cambiar(request):
    if not es_personal(request.user):
        raise PermissionDenied

    pendiente = Usuario.objects.filter(user=request.user, cambio_password_pendiente=True).exists()
    tipo_formulario = (SetPasswordForm if pendiente else PasswordChangeForm)

    form = tipo_formulario(request.user, data=request.POST if request.method == 'POST' else None)

    if request.method == 'POST' and form.is_valid():
        password = form.cleaned_data['new_password1']

        if request.user.check_password(password):
            form.add_error('new_password2', 'La Nueva Contraseña Debe ser Diferente de la Actual')
        else:
            with transaction.atomic():
                user = form.save()

                Usuario.objects.filter(user=user).update(cambio_password_pendiente=False)

            update_session_auth_hash(request, user)
            messages.success(request, 'Contraseña Actualizada Correctamente')
            return redirect('home')

    texto = ('Define una Nueva Contraseña Para Comenzar'
        if pendiente
        else 'Ingresa tu Contraseña Actual y Define una Nueva'
    )

    return render(request, 'usuarios/password_form.html', {
        'form': form,
        'titulo': 'Cambiar contraseña',
        'texto': texto
    })

def logout_view(request):
    if request.method == "POST":
        logout(request)
        return redirect('login')

    return render(request, 'usuarios/logout_confirmar.html')

@login_required
@permission_required('api.change_cliente', raise_exception=True)
@require_POST
def cliente_cambiar_estado(request, id):
    cliente = get_object_or_404(Cliente, pk=id, usuario__usuarios__isnull=True)
    activo = request.POST.get('activo')

    if activo not in ('0', '1'):
        messages.error(request, 'Selecciona un Estado Válido')
        return redirect('usuario-list')

    nuevo_estado = activo == '1'

    actualizado = (User.objects
        .filter(pk=cliente.usuario_id)
        .exclude(is_active=nuevo_estado)
        .update(is_active=nuevo_estado)
    )

    if actualizado:
        mensaje = ('Cuenta del Cliente Reactivada'
            if nuevo_estado
            else 'Cuenta del Cliente Deshabilitada'
        )
        messages.success(request, mensaje)
    else:
        messages.info(request, 'La Cuenta ya Tenía ese Estado')

    return redirect('usuario-list')