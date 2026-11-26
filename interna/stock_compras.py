from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import (
    MateriaPrima,
    Proveedor,
    OrdenCompra,
    DetalleOrdenCompra,
    MovimientoMateriaPrima
)

MAX_STOCK = Decimal('9999999.999')

def _mover_stock(materia, tipo, motivo, cantidad, responsable, observacion, orden=None):
    if not materia.estado:
        raise ValidationError(f'{materia.nombre} Está Deshabilitada')

    if tipo not in ('ENTRADA', 'SALIDA') or cantidad <= 0:
        raise ValidationError('La Cantidad y el Tipo de Movimiento no son Válidos')

    anterior = materia.cantidad_actual
    saldo = (anterior + cantidad
        if tipo == 'ENTRADA'
        else anterior - cantidad
    )

    if not 0 <= saldo <= MAX_STOCK:
        raise ValidationError(f'Revisa las Existencias de {materia.nombre}, el Saldo no es Válido')

    actualizado = MateriaPrima.objects.filter(pk=materia.pk, estado=True, cantidad_actual=anterior).update(cantidad_actual=saldo)

    if not actualizado:
        raise ValidationError('El Stock Cambió, Abre Nuevamente el Formulario')

    movimiento = MovimientoMateriaPrima.objects.create(
        materia_prima=materia,
        tipo=tipo,
        motivo=motivo,
        cantidad=cantidad,
        saldo_resultante=saldo,
        responsable=responsable,
        observacion=observacion,
        orden_compra=orden
    )

    materia.cantidad_actual = saldo
    return movimiento, anterior

@transaction.atomic
def crear_orden_compra(datos, filas, responsable):
    proveedor = get_object_or_404(Proveedor.objects.select_for_update(), pk=datos['proveedor'].pk)

    if not proveedor.activo:
        raise ValidationError('El Proveedor Está Deshabilitado')

    ids = [fila['materia_prima'].pk for fila in filas]

    if not ids or len(ids) != len(set(ids)):
        raise ValidationError('Registra al Menos una Materia Prima, sin Repetirla')

    materias = {materia.pk: materia
        for materia in MateriaPrima.objects.select_for_update()
        .filter(pk__in=ids).order_by('pk')
    }

    for fila in filas:
        materia = materias.get(fila['materia_prima'].pk)

        if (
            materia is None
            or not materia.estado
            or fila['cantidad'] <= 0
            or fila['costo_unitario'] <= 0
        ):
            raise ValidationError('Revisa los Materiales, sus Cantidades y sus Costos')

    orden = OrdenCompra.objects.create(
        proveedor=proveedor,
        tipo_documento=datos['tipo_documento'],
        numero_documento=datos['numero_documento'],
        observacion=datos['observacion'],
        responsable=responsable
    )

    for fila in filas:
        materia = materias[fila['materia_prima'].pk]

        DetalleOrdenCompra.objects.create(
            orden=orden,
            materia_prima=materia,
            cantidad=fila['cantidad'],
            costo_unitario=fila['costo_unitario'],
            unidad=materia.unidad_de_medida
        )

    return orden

@transaction.atomic
def recibir_orden_compra(pk, responsable):
    orden = get_object_or_404(OrdenCompra.objects.select_for_update(), pk=pk)

    if orden.estado == 'recibida':
        return False

    if orden.estado != 'pendiente':
        raise ValidationError('Esta Orden Está Cancelada')

    proveedor = Proveedor.objects.select_for_update().get(pk=orden.proveedor_id)

    if not proveedor.activo:
        raise ValidationError('El Proveedor Está Deshabilitado')

    filas = list(orden.detalles.select_for_update().order_by('materia_prima_id'))

    if not filas:
        raise ValidationError('La Orden no Tiene Materiales')

    materias = {materia.pk: materia
        for materia in MateriaPrima.objects.select_for_update()
        .filter(pk__in=[fila.materia_prima_id for fila in filas])
        .order_by('pk')
    }

    for fila in filas:
        materia = materias[fila.materia_prima_id]

        if not materia.estado or materia.unidad_de_medida != fila.unidad:
            raise ValidationError(f'Revisa el Estado y la Unidad de {materia.nombre}')

        if materia.cantidad_actual + fila.cantidad > MAX_STOCK:
            raise ValidationError(f'La Cantidad de {materia.nombre} Supera el Límite Permitido')

    actualizado = OrdenCompra.objects.filter(pk=pk, estado='pendiente').update(
        estado='recibida',
        fecha_gestion=timezone.now(),
        gestionado_por=responsable,
    )

    if not actualizado:
        raise ValidationError('La Orden Cambió, Consulta Nuevamente su Detalle')

    for fila in filas:
        materia = materias[fila.materia_prima_id]

        _mover_stock(materia, 'ENTRADA', 'COMPRA', fila.cantidad, responsable, f'Recepción de OC-{orden.pk}', orden)

        MateriaPrima.objects.filter(pk=materia.pk).update(costo_unitario=fila.costo_unitario)

    return True

@transaction.atomic
def cancelar_orden_compra(pk, motivo, responsable):
    orden = get_object_or_404(OrdenCompra.objects.select_for_update(), pk=pk)

    if orden.estado == 'cancelada':
        return False

    if orden.estado != 'pendiente':
        raise ValidationError('Solo Puedes Cancelar Órdenes Pendientes de Recepción')

    motivo = motivo.strip()

    if not 1 <= len(motivo) <= 300:
        raise ValidationError('Explica la Cancelación Usando Hasta 300 Caracteres')

    actualizado = OrdenCompra.objects.filter(pk=pk, estado='pendiente').update(
        estado='cancelada',
        motivo_cancelacion=motivo,
        fecha_gestion=timezone.now(),
        gestionado_por=responsable
    )

    if not actualizado:
        raise ValidationError('La Orden Cambió, Consulta Nuevamente su Detalle')

    return True

@transaction.atomic
def registrar_cambio_materia(pk, datos, responsable, es_ajuste=False):
    permiso = ('interna.ajustar_stock_materiaprima'
        if es_ajuste
        else 'interna.registrar_baja_materiaprima'
    )

    if not responsable.has_perm(permiso):
        raise ValidationError('No Tienes Permiso Para Registrar Esta Pperación')

    materia = get_object_or_404(MateriaPrima.objects.select_for_update(), pk=pk)

    if datos['stock_esperado'] != materia.cantidad_actual:
        raise ValidationError('El Stock Cambió, Abre Nuevamente el Formulario')

    observacion = datos['observacion'].strip()

    if not 1 <= len(observacion) <= 300:
        raise ValidationError('La Observación es Obligatoria y Admite Hasta 300 Caracteres')

    if es_ajuste:
        operacion = datos['operacion']

        if operacion not in ('INICIAL', 'ENTRADA', 'SALIDA'):
            raise ValidationError('Selecciona una Operación Válida')

        if operacion == 'INICIAL' and (
            materia.cantidad_actual != 0
            or materia.movimientos.exists()
        ):
            raise ValidationError('La Carga Inicial Solo se Permite sin Stock ni Movimientos Previos')

        tipo = 'SALIDA' if operacion == 'SALIDA' else 'ENTRADA'
        motivo = 'INICIAL' if operacion == 'INICIAL' else 'AJUSTE'

    else:
        tipo = 'SALIDA'
        motivo = 'PERDIDA'

    return _mover_stock(materia, tipo, motivo, datos['cantidad'], responsable, observacion)