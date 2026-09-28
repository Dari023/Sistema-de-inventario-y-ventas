from django.shortcuts import render, get_object_or_404, redirect
from .models import Usuario
from .forms import UsuarioForm
from django.db.models import Q
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, logout

def UsuarioListView(request):
    query = request.GET.get('q', '').strip()
    usuarios = Usuario.objects.all()
    
    if query:
        usuarios = usuarios.filter(
            Q(user__username__icontains=query) | 
            Q(nombre_completo__icontains=query)
        )
            
    contexto = {
        'usuarios': usuarios,
        'query': query
    }
    return render(request, 'usuarios/usuario_list.html', contexto)

def UsuarioCreateView(request):
    if request.method == "POST":
        form = UsuarioForm(request.POST)
        if form.is_valid():
            user = User.objects.create_user(
                username=form.cleaned_data['username'],
                password=form.cleaned_data['password']
            )
            user.is_active = form.cleaned_data['activo']
            user.save()
            usuario = form.save(commit=False)
            usuario.user = user
            usuario.save()
            return redirect('usuario-list')
    else:
        form = UsuarioForm(initial={'activo': True})
    return render(request, 'usuarios/usuario_form.html', {'form': form, 'action': 'Crear'})

def UsuarioUpdateView(request, id):
    usuario = get_object_or_404(Usuario, pk=id)
    if request.method == "POST":
        form = UsuarioForm(request.POST, instance=usuario)
        if form.is_valid():
            user = usuario.user
            user.username = form.cleaned_data['username']
            user.is_active = form.cleaned_data['activo']
            if form.cleaned_data['password']:
                user.set_password(form.cleaned_data['password'])
            user.save()
            form.save()
            return redirect('usuario-list')
    else:
        form = UsuarioForm(
            instance=usuario, 
            initial={
                'username': usuario.user.username,
                'activo': usuario.user.is_active
            }
        )
    return render(request, 'usuarios/usuario_form.html', {'form': form, 'action': 'Modificar'})

def UsuarioDeleteView(request, id):
    usuario = get_object_or_404(Usuario, pk=id)
    if request.method == "POST":
        usuario.user.delete()
        return redirect('usuario-list')
    return render(request, 'usuarios/usuario_delete.html', {'usuario': usuario})

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
        
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')
    else:
        form = AuthenticationForm()
        
    return render(request, 'usuarios/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('login')