from django import forms
from .models import Usuario
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm, AuthenticationForm, UsernameField
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from .acceso import es_personal
from django.db.models import Q

class UsuarioForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150, 
        label='Nombre de usuario', 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario', 'autocomplete': 'off'}))
    email = forms.EmailField(
        label='Correo electrónico',
        max_length=254,
        widget=forms.EmailInput(attrs={'class': 'form-control'}))
    password = forms.CharField(
        label='Contraseña temporal',
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'autocomplete': 'new-password',
        }),
        help_text=(
            'Obligatoria al crear, al editar, deja vacío para conservar la actual, si asignas otra, deberá cambiarse al ingresar'
        ))       
    activo = forms.BooleanField(
        required=False, 
        label='Usuario Activo', 
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    class Meta:
        model = Usuario
        fields = ['nombre_completo', 'rut', 'telefono']
        widgets = {
            'nombre_completo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre y Apellido'}),
            'rut': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '12345678-9'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean_rut(self):
        rut = self.cleaned_data.get("rut")
        if rut:
            rut_limpio = rut.replace(".", "").replace("-", "")
            if "-" not in rut:
                self.add_error("rut", "El RUT debe llevar guion. Ejemplo: 12345678-9")
            if len(rut_limpio) > 9:
                self.add_error("rut", "El RUT es demasiado largo.")
            if len(rut_limpio) < 9:
                self.add_error("rut", "El RUT es demasiado corto.")
        return rut

    def clean_telefono(self):
        telefono = self.cleaned_data.get("telefono")
        if telefono:
            if len(telefono) > 9:
                self.add_error("telefono", "El teléfono no puede tener más de 9 dígitos.")
            if len(telefono) < 9:
                self.add_error("telefono", "El teléfono debe tener 9 dígitos.")
        return telefono

    def clean_username(self):
        username = self.cleaned_data['username']
        User.username_validator(username)

        if User.objects.filter(username=username).exclude(pk=self.instance.user_id).exists():
            raise forms.ValidationError('Este Nombre de Usuario ya Está Registrado')

        return username

    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()

        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.user_id).exists():
            raise forms.ValidationError('Este Correo ya Está Asociado a Otra Cuenta')

        return email

    def clean_password(self):
        password = self.cleaned_data.get('password', '')

        if not password and not self.instance.pk:
            raise forms.ValidationError('Asigna una Contraseña Temporal Para la Cuenta Nueva')

        if password:
            user = User(username=self.cleaned_data.get('username', ''), email=self.cleaned_data.get('email', ''))
            validate_password(password, user=user)

        return password

class RecuperarPasswordPersonalForm(PasswordResetForm):
    def get_users(self, email):
        return (user for user in super().get_users(email) if es_personal(user))

class RestablecerPasswordPersonalForm(SetPasswordForm):
    def clean(self):
        datos = super().clean()

        if not es_personal(self.user):
            raise forms.ValidationError('Esta Cuenta no Puede Restablecer su Contraseña del Personal')

        password = datos.get('new_password1')

        if password and self.user.check_password(password):
            self.add_error('new_password2', 'La Nueva Contraseña debe ser Diferente de la Actual')

        return datos

    @transaction.atomic
    def save(self, commit=True):
        user = super().save(commit=commit)

        if commit:
            Usuario.objects.filter(user=user).update(cambio_password_pendiente=False)

        return user

class LoginPersonalForm(AuthenticationForm):
    username = UsernameField(
        label='Nombre de Usuario o Correo Electrónico',
        max_length=254,
        widget=forms.TextInput(attrs={
            'autofocus': True,
            'autocomplete': 'username',
        })
    )

    error_messages = {'invalid_login': ('El Usuario, Correo o Contraseña no son Correctos'),
        'inactive': 'Esta Cuenta Está Desactivada'
    }

    def __init__(self, request=None, data=None):
        super().__init__(request=request, data=data)
        self.fields['username'].max_length = 254
        self.fields['username'].widget.attrs['maxlength'] = 254

    def clean(self):
        identificador = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if identificador and password:
            coincidencias = list(User.objects.filter(Q(username=identificador) | Q(email__iexact=identificador))[:2])

            if len(coincidencias) != 1:
                raise self.get_invalid_login_error()

            self.cleaned_data['username'] = coincidencias[0].username

        return super().clean()