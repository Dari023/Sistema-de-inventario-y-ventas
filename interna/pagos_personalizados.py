import logging
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST, require_http_methods
from .models import Pedido, PagoPedido
from .pedidos_personalizados import (
    obtener_pedido_personalizado_por_token,
    resumen_pagos_personalizado)

logger = logging.getLogger(__name__)

def _transaccion_webpay():
    from api.views import _webpay_tx

    return _webpay_tx()

def _volver_al_encargo(token, aviso):
    ruta = reverse('pedido_personalizado_publico', kwargs={'token': token})
    return redirect(f'{ruta}?{urlencode({'aviso': aviso})}')

def _registrar_respuesta_webpay(pago_id, respuesta):
    if not isinstance(respuesta, dict):
        return 'sin_confirmar'

    referencia = PagoPedido.objects.only('pedido_id').get(pk=pago_id)

    with transaction.atomic():
        pedido = Pedido.objects.select_for_update().get(pk=referencia.pedido_id, tipo_pedido='personalizado')
        pago = PagoPedido.objects.select_for_update().get(pk=pago_id, pedido=pedido, metodo='webpay')

        if pago.estado == 'aprobado':
            return 'actualizado'

        try:
            monto_recibido = Decimal(str(respuesta.get('amount')))
            corresponde = (
                monto_recibido.is_finite()
                and monto_recibido == pago.monto
                and str(respuesta.get('buy_order')) == pago.orden_webpay
                and str(respuesta.get('session_id')) == str(pedido.id_compra)
            )
        except (InvalidOperation, TypeError, ValueError):
            corresponde = False

        if not corresponde:
            logger.error('Respuesta de Webpay no corresponde al pago personalizado %s', pago.pk)
            return 'sin_confirmar'

        estado_webpay = respuesta.get('status')

        if (
            estado_webpay == 'AUTHORIZED'
            and respuesta.get('response_code') == 0
        ):
            pago.estado = 'aprobado'
            pago.fecha_revision = timezone.now()
            pago.observacion = 'Pago Confirmado Automáticamente por Webpay'
            pago.save(update_fields=['estado', 'fecha_revision', 'observacion'])
            abonado = sum(pedido.pagos.filter(estado='aprobado').values_list('monto', flat=True), Decimal('0'))
            pedido.estado = ('pagado'
                if pedido.total > 0 and abonado >= pedido.total
                else 'pendiente'
            )
            pedido.save(update_fields=['estado'])

            return 'actualizado'

        if estado_webpay in {'FAILED', 'REVERSED', 'NULLIFIED'}:
            pago.estado = 'rechazado'
            pago.fecha_revision = timezone.now()
            pago.observacion = f'Resultado de Webpay: {estado_webpay}'
            pago.save(update_fields=['estado', 'fecha_revision', 'observacion'])
            return 'rechazado'

        if (
            estado_webpay == 'INITIALIZED'
            and timezone.now() - pago.fecha_creacion >= timedelta(minutes=15)
        ):
            pago.estado = 'rechazado'
            pago.fecha_revision = timezone.now()
            pago.observacion = (
                'Intento Vencido'
            )
            pago.save(update_fields=['estado', 'fecha_revision', 'observacion'])
            return 'rechazado'

    return 'sin_confirmar'

def _consultar_webpay(pago):
    tx = _transaccion_webpay()
    respuesta = tx.status(pago.token_webpay)

    if (
        respuesta.get('status') == 'AUTHORIZED'
        and respuesta.get('response_code') == 0
    ):
        try:
            respuesta = tx.commit(pago.token_webpay)
        except Exception:
            respuesta = tx.status(pago.token_webpay)

    return _registrar_respuesta_webpay(pago.pk, respuesta)

@never_cache
@require_POST
def pedido_personalizado_webpay_iniciar(request, token):
    acceso = obtener_pedido_personalizado_por_token(token)

    with transaction.atomic():
        pedido = Pedido.objects.select_for_update().get(pk=acceso.pk, tipo_pedido='personalizado')
        resumen = resumen_pagos_personalizado(pedido)

        if resumen['saldo'] <= 0:
            return _volver_al_encargo(token, 'sin_saldo')

        if not (0 < pedido.adelanto_requerido <= resumen['total']):
            return _volver_al_encargo(token, 'condiciones_invalidas')

        if pedido.pagos.filter(estado__in=['pendiente', 'en_revision']).exists():
            return _volver_al_encargo(token, 'pago_en_tramite')

        try:
            esperado = Decimal(request.POST.get('total_esperado', ''))
            total_correcto = (esperado.is_finite() and esperado == resumen['total'])
        except (InvalidOperation, TypeError, ValueError):
            total_correcto = False

        if not total_correcto:
            return _volver_al_encargo(token, 'total_cambiado')

        opcion = request.POST.get('opcion')

        if opcion == 'adelanto':
            monto = resumen['adelanto_pendiente']
        elif opcion == 'saldo':
            monto = resumen['saldo']
        else:
            return _volver_al_encargo(token, 'opcion_invalida')

        if monto <= 0:
            return _volver_al_encargo(token, 'sin_monto')

        if monto > Decimal('9999999999'):
            return _volver_al_encargo(token, 'monto_fuera_de_rango')

        pago = PagoPedido.objects.create(pedido=pedido, metodo='webpay', monto=monto, estado='pendiente')
        pago.orden_webpay = f'pp-{pago.pk}'
        pago.save(update_fields=['orden_webpay'])

    ruta_retorno = reverse('pedido_personalizado_webpay_retorno', kwargs={'token': token})
    return_url = request.build_absolute_uri(ruta_retorno)

    try:
        respuesta = _transaccion_webpay().create(
            buy_order=pago.orden_webpay,
            session_id=str(pedido.id_compra),
            amount=int(monto),
            return_url=return_url
        )

        token_webpay = respuesta['token']
        url_webpay = respuesta['url']

        if not token_webpay or not url_webpay:
            raise ValueError('Webpay no Devolvió los Datos de Inicio')

    except Exception:
        logger.exception('No se pudo Iniciar el pago Personalizado %s', pago.pk)

        with transaction.atomic():
            Pedido.objects.select_for_update().get(pk=pedido.pk)
            PagoPedido.objects.filter(pk=pago.pk, estado='pendiente', token_webpay__isnull=True).update(
                estado='rechazado',
                observacion='No se pudo Iniciar la Transacción en Webpay'
            )

        return _volver_al_encargo(token, 'error_inicio')

    PagoPedido.objects.filter(pk=pago.pk).update(token_webpay=token_webpay)

    respuesta_html = render(request, 'interna/inventario/pedido_personalizado_webpay.html',
        {
            'url_webpay': url_webpay,
            'token_webpay': token_webpay,
            'monto': monto
        })

    respuesta_html['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    return respuesta_html

@csrf_exempt
@never_cache
@require_http_methods(['GET', 'POST'])
def pedido_personalizado_webpay_retorno(request, token):
    token_acceso = token
    pedido = obtener_pedido_personalizado_por_token(token_acceso)
    parametros = request.POST if request.method == 'POST' else request.GET
    token_webpay = (parametros.get('token_ws') or parametros.get('TBK_TOKEN'))
    consulta = PagoPedido.objects.filter(pedido=pedido, metodo='webpay')

    if token_webpay:
        pago = get_object_or_404(consulta, token_webpay=token_webpay)
    else:
        pago = get_object_or_404(consulta, orden_webpay=parametros.get('TBK_ORDEN_COMPRA'))

    if pago.estado == 'aprobado':
        return _volver_al_encargo(token_acceso, 'actualizado')

    if not pago.token_webpay:
        return _volver_al_encargo(token_acceso, 'sin_confirmar')

    try:
        if (
            parametros.get('token_ws')
            and not parametros.get('TBK_TOKEN')
        ):
            try:
                respuesta = _transaccion_webpay().commit(pago.token_webpay)
                resultado = _registrar_respuesta_webpay(pago.pk, respuesta)
            except Exception:
                resultado = _consultar_webpay(pago)
        else:
            resultado = _consultar_webpay(pago)

    except Exception:
        logger.exception('No se pudo resolver el pago personalizado %s', pago.pk)
        resultado = 'sin_confirmar'

    return _volver_al_encargo(token_acceso, resultado)

@never_cache
@require_POST
def pedido_personalizado_webpay_consultar(request, token, pago_pk):
    pedido = obtener_pedido_personalizado_por_token(token)
    pago = get_object_or_404(PagoPedido, pk=pago_pk, pedido=pedido, metodo='webpay')

    if pago.estado in {'aprobado', 'rechazado'}:
        return _volver_al_encargo(token, 'actualizado')

    if not pago.token_webpay:

        with transaction.atomic():
            Pedido.objects.select_for_update().get(pk=pedido.pk)
            actual = PagoPedido.objects.select_for_update().get(pk=pago.pk)

            if (
                actual.estado == 'pendiente'
                and not actual.token_webpay
                and timezone.now() - actual.fecha_creacion
                >= timedelta(minutes=15)
            ):
                actual.estado = 'rechazado'
                actual.observacion = 'Inicio de pago incompleto y vencido.'
                actual.save(update_fields=['estado', 'observacion'])

        return _volver_al_encargo(token, 'actualizado')

    try:
        resultado = _consultar_webpay(pago)
    except Exception:
        logger.exception('No se pudo consultar el pago personalizado %s', pago.pk)
        resultado = 'sin_confirmar'

    return _volver_al_encargo(token, resultado)