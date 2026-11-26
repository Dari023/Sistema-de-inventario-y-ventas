from django.contrib import admin
from interna.models import TarifaEnvio

# Register your models here.
@admin.register(TarifaEnvio)
class TarifaEnvioAdmin(admin.ModelAdmin):
    list_display = ('nombre_region', 'costo', 'activo')
    list_editable = ('costo', 'activo')