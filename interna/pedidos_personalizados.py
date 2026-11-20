from decimal import Decimal
from uuid import UUID
from django.core import signing
from django.http import Http404
from django.shortcuts import get_object_or_404
from django.urls import reverse
from .models import Pedido

FIRMA_PEDIDO_PERSONALIZADO = 'interna.pedido-personalizado.v1'
VIGENCIA_ENLACE = 60 * 60 * 24 * 30

def crear_enlace_pedido_personalizado(request, pedido):
    token = signing.dumps(str(pedido.id_compra), salt=FIRMA_PEDIDO_PERSONALIZADO)
    ruta = reverse('pedido_personalizado_publico', kwargs={'token': token})

    return request.build_absolute_uri(ruta)


def obtener_pedido_personalizado_por_token(token):
    try:
        codigo = signing.loads(token, salt=FIRMA_PEDIDO_PERSONALIZADO, max_age=VIGENCIA_ENLACE)
        codigo = UUID(codigo)
    except (signing.BadSignature, ValueError, TypeError, AttributeError):
        raise Http404('El Enlace no es Válido o ha Vencido')

    return get_object_or_404(
        Pedido.objects.prefetch_related('detalles_personalizados', 'pagos'), id_compra=codigo, tipo_pedido='personalizado')


def resumen_pagos_personalizado(pedido):
    total = pedido.total
    abonado = sum(
        (
            pago.monto
            for pago in pedido.pagos.all()
            if pago.estado == 'aprobado'
        ),
        Decimal('0')
    )

    return {
        'total': total,
        'abonado': abonado,
        'saldo': max(Decimal('0'), total - abonado),
        'adelanto_pendiente': max(Decimal('0'), pedido.adelanto_requerido - abonado
        )
    }