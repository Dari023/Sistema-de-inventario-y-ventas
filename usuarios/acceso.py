def es_personal(user):
    return user.is_active and (user.is_superuser or user.groups.filter(name__in=['Administradores', 'Colaboradores']).exists())