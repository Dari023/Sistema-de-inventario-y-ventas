from django import forms
from .models import Usuario
from django.contrib.auth.models import User

class UsuarioForm(forms.ModelForm):
    username = forms.CharField(max_length=150, label='Nombre de usuario', 
         widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre de usuario', 'autocomplete': 'off'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '******', 'autocomplete': 'new-password'}),         
         label='Contraseña', required=False)
    activo = forms.BooleanField(required=False, label='Usuario Activo', 
         widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}))

    class Meta:
        model = Usuario
        fields = ['nombre_completo', 'rut', 'telefono', 'rol']
        widgets = {
            'nombre_completo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre y Apellido'}),
            'rut': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '12345678-9'}),
            'telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'rol': forms.Select(attrs={'class': 'form-select'}),
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