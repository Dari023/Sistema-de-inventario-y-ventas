from django.contrib import admin
from .models import *
from usuarios.models import Usuario, Rol

# Register your models here.


admin.site.register(Producto)
admin.site.register(MateriaPrima)
admin.site.register(CategoriaProducto)
admin.site.register(Usuario)
admin.site.register(Rol)