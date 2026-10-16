from django.db import models
from django.contrib.auth.models import User

class Cliente(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='cliente')
    rut = models.CharField(max_length=12, unique=True)
    telefono = models.CharField(max_length=20, blank=True, default='')
    direccion = models.CharField(max_length=200, blank=True, default='')
    
    @property
    def nombre(self):
        return self.usuario.first_name

    @property
    def apellido(self):
        return self.usuario.last_name

    @property
    def correo(self):
        return self.usuario.email

    def __str__(self):
        return f"{self.rut} - {self.nombre} {self.apellido}"