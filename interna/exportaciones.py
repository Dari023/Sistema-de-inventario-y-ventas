from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from openpyxl import Workbook
from .models import Producto, MateriaPrima, Pedido


def _excel(nombre, encabezados, filas):
    wb = Workbook()
    ws = wb.active
    ws.append(encabezados)
    for fila in filas:
        ws.append(fila)
    respuesta = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    respuesta['Content-Disposition'] = f'attachment; filename="{nombre}.xlsx"'
    wb.save(respuesta)
    return respuesta


def producto_exportar(request):
    productos = Producto.objects.select_related('categoria').prefetch_related('variantes')
    filas = [[p.nombre, p.categoria.nombre, int(p.precio_final), p.stock_para_mostrar,
              'Activo' if p.activo else 'Deshabilitado'] for p in productos]
    return _excel('productos', ['Nombre', 'Categoría', 'Precio', 'Stock total', 'Estado'], filas)


def materia_prima_exportar(request):
    filas = [[m.nombre, m.cantidad_actual, m.cantidad_critica, m.unidad_de_medida,
              m.costo_unitario, 'Activo' if m.estado else 'Deshabilitado']
             for m in MateriaPrima.objects.all()]
    return _excel('materias_primas',
                  ['Nombre', 'Stock actual', 'Stock crítico', 'Unidad', 'Costo unitario', 'Estado'], filas)

def pedido_exportar(request):
    pedidos = (Pedido.objects
               .filter(Q(tipo_pedido='normal', estado='pagado') | Q(tipo_pedido='personalizado'))
               .select_related('cliente')
               .prefetch_related('detallepedido_set', 'detalles_personalizados')
               .order_by('-fecha_pedido'))
    filas = [[str(p.id_compra),
              timezone.localtime(p.fecha_pedido).strftime('%d/%m/%Y %H:%M'),
              f'{p.cliente.nombre} {p.cliente.apellido}' if p.cliente else (p.nombre_invitado or 'Invitado'),
              int(p.total),
              p.get_estado_display(),
              p.get_etapa_display() or '—'] for p in pedidos]
    return _excel('pedidos', ['Código', 'Fecha', 'Comprador', 'Total', 'Estado', 'Etapa'], filas)