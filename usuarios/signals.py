from django.contrib.auth.models import Group
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Usuario

@receiver(post_save, sender=Usuario)
def sincronizar_grupo_colaboradores(sender, instance, raw=False, **datos):
    if raw or not instance.user_id:
        return

    grupo = Group.objects.filter(name='Colaboradores').first()
    if grupo is None:
        return

    nombre_rol = instance.rol.nombre if instance.rol_id else ''

    if nombre_rol.strip().casefold() == 'colaborador':
        instance.user.groups.add(grupo)
    else:
        instance.user.groups.remove(grupo)