from rest_framework import viewsets, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.views import TokenObtainPairView
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.models import User
from django.core.mail import EmailMultiAlternatives
from django.db import transaction, IntegrityError
from django.db.models import F, Q
from django.conf import settings
from decimal import Decimal
from django.core import signing
from django.http import Http404
from django.template.loader import render_to_string
from transbank.webpay.webpay_plus.transaction import Transaction as WpTx
from transbank.common.integration_commerce_codes import IntegrationCommerceCodes
from transbank.common.integration_api_keys import IntegrationApiKeys
from rest_framework.exceptions import PermissionDenied as PermisoResenaDenegado
from uuid import UUID
from urllib.parse import quote
from interna.models import Producto, DetallePedido, Pedido, CategoriaProducto, Resena, PreguntaFrecuente, ProductoVariante
from .models import Cliente
from interna.views import generar_comprobante_pdf
from .serializers import ConsultaCrearSerializer
from .serializers import (
    ProductoSerializer,
    PedidoSerializer,
    CategoriaProductoSerializer,
    RegistroClienteSerializer,
    LoginCorreoSerializer,
    MiCuentaSerializer,
    ResenaCrearSerializer,
    ResenaPublicaSerializer,
    PreguntaFrecuenteSerializer,
    DatosCompradorSerializer
)

class ProductoViewSet(viewsets.ModelViewSet):
    serializer_class = ProductoSerializer
    queryset = Producto.objects.filter(activo=True)

def obtener_carrito(request, crear=False):
    filtros = {"estado": "pendiente", 'tipo_pedido':'normal'}

    if request.user.is_authenticated:
        filtros["cliente"] = get_object_or_404(
            Cliente,
            usuario=request.user,
        )
    else:
        if not request.session.session_key:
            if not crear:
                return None
            request.session.create()

        filtros["cliente"] = None
        filtros["session_key"] = request.session.session_key

    if crear:
        pedido, _ = Pedido.objects.get_or_create(**filtros)
        return pedido

    return Pedido.objects.filter(**filtros).first()

def _webpay_tx():
    cc = getattr(settings, 'WEBPAY_COMMERCE_CODE', '')
    key = getattr(settings, 'WEBPAY_API_KEY', '')
    if getattr(settings, 'WEBPAY_ENV', 'integration') == 'production' and cc and key:
        return WpTx.build_for_production(cc, key)
    return WpTx.build_for_integration(IntegrationCommerceCodes.WEBPAY_PLUS, IntegrationApiKeys.WEBPAY)

class CarritoAPIView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        pedido = obtener_carrito(request)

        if pedido is None:
            return Response({
                "detalles": [],
                "total": "0",
            })

        serializer = PedidoSerializer(pedido, context={'es_carrito': True, 'request': request})
        return Response(serializer.data)

    def post(self, request):
        try:
            producto_id = int(str(request.data.get('producto_id')))
            cambio = int(str(request.data.get('cantidad', 1)))
            variante_id = request.data.get('variante_id')
            if variante_id is not None:
                variante_id = int(str(variante_id))
        except (TypeError, ValueError):
            return Response({'error': 'Revisa el Producto, Talla y Cantidad'}, status=status.HTTP_400_BAD_REQUEST)

        producto = get_object_or_404(Producto, pk=producto_id, activo=True)
        variante = None

        if variante_id is not None:
            variante = producto.variantes.filter(pk=variante_id).first()
            if variante is None:
                return Response({'error': 'La Talla Seleccionada no Existe'}, status=status.HTTP_400_BAD_REQUEST)
        elif producto.variantes.exists():
            return Response({'error': 'Selecciona una Talla antes de Agregar el Producto'}, status=status.HTTP_400_BAD_REQUEST)

        stock = variante.stock_actual if variante else producto.stock_actual
        precio = variante.precio_final if variante else producto.precio_final

        pedido = obtener_carrito(request, crear=True)
        detalle = pedido.detallepedido_set.filter(producto=producto, variante=variante).first()
        cantidad_actual = detalle.cantidad if detalle else 0
        nueva_cantidad = cantidad_actual + cambio

        if nueva_cantidad <= 0:
            return Response({'error': 'La Cantidad debe ser Mayor que Cero'}, status=status.HTTP_400_BAD_REQUEST)

        if nueva_cantidad > stock:
            return Response({'error': 'No hay Stock Suficiente para esta Selección'}, status=status.HTTP_400_BAD_REQUEST)

        if detalle:
            detalle.cantidad = nueva_cantidad
            detalle.precio_unitario = precio
            detalle.save(update_fields=['cantidad', 'precio_unitario'])
        else:
            DetallePedido.objects.create(
                pedido=pedido,
                producto=producto,
                variante=variante,
                cantidad=nueva_cantidad,
                precio_unitario=precio
            )

        serializer = PedidoSerializer(pedido, context={'es_carrito': True, 'request': request})

        return Response(serializer.data)

    def delete(self, request):
        pedido = obtener_carrito(request)

        if pedido is None:
            return Response({"mensaje": "El Carrito Está Vacío."})

        if 'detalle_id' in request.data:
            try:
                detalle_id = int(str(request.data['detalle_id']))
            except (TypeError, ValueError):
                return Response({'error': 'Este Objeto del Carrito no es Válido'}, status=status.HTTP_400_BAD_REQUEST)

            detalle = get_object_or_404(pedido.detallepedido_set.all(), pk=detalle_id)
            detalle.delete()
            return Response({'mensaje': 'Producto eliminado del carrito'})

        producto_id = request.data.get("producto_id")

        if 'producto_id' in request.data:
            try:
                producto_id = int(str(request.data['producto_id']))
            except (TypeError, ValueError):
                return Response({'error': 'El Producto no es Válido'}, status=status.HTTP_400_BAD_REQUEST)

            pedido.detallepedido_set.filter(producto_id=producto_id, variante__isnull=True).delete()

            return Response({'mensaje': 'Producto Eliminado del Carrito'})

        if request.data:
            return Response({'error': 'Envía el Detalle del Producto que Quieres Quitar'}, status=status.HTTP_400_BAD_REQUEST)

        pedido.detallepedido_set.all().delete()
        return Response({'mensaje': 'Se Vació el Carrito'})

class WebpayIniciarView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        pedido = obtener_carrito(request)
        if pedido is None or not pedido.detallepedido_set.exists():
            return Response({"error": "el carrito está vacío"}, status=status.HTTP_400_BAD_REQUEST)
    
        datos = request.data.copy()

        if request.user.is_authenticated:
            cliente = Cliente.objects.filter(usuario=request.user).first()

            if cliente is None or pedido.cliente_id != cliente.pk:
                return Response({'error': 'El Carrito no Corresponde a tu Cuenta de Cliente'}, status=status.HTTP_403_FORBIDDEN)

            datos['rut_invitado'] = cliente.rut

        serializer = DatosCompradorSerializer(data=datos)

        if not serializer.is_valid():
            mensaje = ' '.join(str(error)
                for errores in serializer.errors.values()
                for error in errores
            )

            return Response({'error': mensaje}, status=status.HTTP_400_BAD_REQUEST)

        for campo, valor in serializer.validated_data.items():
            setattr(pedido, campo, valor)

        pedido.save(update_fields=list(serializer.validated_data))

        with transaction.atomic():
            detalles = list(
                pedido.detallepedido_set
                .select_related('producto', 'variante__producto')
                .prefetch_related('producto__variantes')
            )

            for detalle in detalles:
                producto = detalle.producto
                variante = detalle.variante

                if not producto.activo or (
                    variante is not None and variante.producto_id != producto.pk
                ):
                    return Response({'error': 'Hay un Producto que ya no Está Disponible'}, status=status.HTTP_409_CONFLICT)

                if variante is None and producto.variantes.exists():
                    return Response({'error': f"Selecciona una Talla para {producto.nombre}."}, status=status.HTTP_409_CONFLICT)

                stock = variante.stock_actual if variante else producto.stock_actual
                if detalle.cantidad > stock:
                    talla = f" (talla {variante.talla})" if variante else ""
                    return Response({"error": f"No hay Stock Suficiente de {producto.nombre}{talla}."}, status=status.HTTP_409_CONFLICT)

                detalle.precio_unitario = detalle.precio_vigente

            subtotal = sum((detalle.subtotal for detalle in detalles), Decimal('0'))
            total = subtotal + pedido.costo_envio

            if total <= 0:
                return Response({'error': 'El Total del Pedido debe ser Mayor que 0'}, status=status.HTTP_400_BAD_REQUEST)

            if request.data.get('total_esperado') != int(total):
                return Response({'error': 'El Total Cambió, Vuelve al Carrito y Revisa los Precios Antes de Pagar'}, status=status.HTTP_409_CONFLICT)

            DetallePedido.objects.bulk_update(detalles, ['precio_unitario'])

        return_url = getattr(settings, 'WEBPAY_RETURN_URL', 'http://localhost:8000/api/webpay/retorno/')
        try:
            resp = _webpay_tx().create(
                buy_order=f"pedido-{pedido.id}",
                session_id=str(pedido.id_compra),
                amount=int(total),
                return_url=return_url
            )
            return Response({"url": resp['url'], "token": resp['token']})
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

def enviar_correo_compra(pedido_id, frontend):
    pedido = Pedido.objects.select_related('cliente__usuario').get(pk=pedido_id, estado='pagado')

    if pedido.cliente_id:
        correo = pedido.cliente.usuario.email
    else:
        correo = pedido.email_invitado

    if not correo:
        return

    firmador = signing.Signer(salt='resenas-pedido')
    token = firmador.sign(str(pedido.id_compra))
    enlace_resena = f"{frontend.rstrip('/')}/resenas/{quote(token, safe='')}"
    detalles = []
    lineas = []

    for detalle in pedido.detallepedido_set.select_related('producto'):
        nombre = detalle.producto.nombre
        subtotal = f"${int(detalle.subtotal):,}".replace(",", ".")
        detalles.append({
            'nombre': nombre,
            'cantidad': detalle.cantidad,
            'subtotal': subtotal
        })

        lineas.append(f"{detalle.cantidad} × {nombre}: {subtotal}")

    total = f"${int(pedido.total):,}".replace(",", ".")
    productos = "\n".join(lineas)
    cuerpo = (
        "Gracias por comprar en Amigos del Vuelo\n\n"
        f"Número de compra: {pedido.id_compra}\n\n"
        f"{productos}\n\n"
        f"Total pagado: {total}\n\n"
        f"Valora tus productos: {enlace_resena}"
    )

    html = render_to_string('interna/inventario/compra_confirmada.html',
        {
            'pedido': pedido,
            'detalles': detalles,
            'total': total,
            'enlace_resena': enlace_resena
        }
    )

    mensaje = EmailMultiAlternatives(subject='Compra confirmada | Amigos del Vuelo', body=cuerpo, to=[correo])
    mensaje.attach_alternative(html, 'text/html')
    try:
        buffer_pdf = generar_comprobante_pdf(pedido)
        nombre_archivo = f"Comprobante_Pedido_{pedido.pk}.pdf" 
        mensaje.attach(nombre_archivo, buffer_pdf.getvalue(), 'application/pdf')
    except Exception as e:
        print(f"Error al generar o adjuntar el PDF para el pedido {pedido.pk}: {e}")
    mensaje.send()

class WebpayRetornoView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = [] 

    def post(self, request):
        return self._procesar_retorno(request)

    def get(self, request):
        return self._procesar_retorno(request)

    def _procesar_retorno(self, request):
        frontend = getattr(settings, 'WEBPAY_FRONTEND_URL', 'http://localhost:5173')
        params = request.POST if request.method == 'POST' else request.GET
        token = params.get('token_ws')
        if not token:
            return redirect(f"{frontend}/carrito?pago=cancelado")
        try:
            resp = _webpay_tx().commit(token)
        except Exception:
            return redirect(f"{frontend}/carrito?pago=error")
        if resp.get('response_code') != 0:
            return redirect(f"{frontend}/carrito?pago=rechazado")
        buy_order = str(resp.get('buy_order') or '')
        try:
            pedido = Pedido.objects.get(
                pk=int(buy_order.replace('pedido-', '')),
            )
        except (TypeError, ValueError, Pedido.DoesNotExist):
            return redirect(f"{frontend}/carrito?pago=error")
        with transaction.atomic():
            actualizado = Pedido.objects.filter(pk=pedido.pk, estado="pendiente").update(estado="pagado")

            if not actualizado:
                ya_pagado = Pedido.objects.filter(pk=pedido.pk, estado="pagado").exists()

                if ya_pagado:
                    return redirect(f"{frontend}/compra/{pedido.id_compra}")

                return redirect(f"{frontend}/carrito?pago=error")

            if resp.get('amount') != pedido.total:
                transaction.set_rollback(True)
                return redirect(f"{frontend}/carrito?pago=error")

            for detalle in pedido.detallepedido_set.order_by('producto_id', 'variante_id'):
                if detalle.variante_id is not None:
                    inventario = ProductoVariante.objects.filter(pk = detalle.variante_id, producto_id = detalle.producto_id)
                else:
                    inventario = Producto.objects.filter(pk = detalle.producto_id, variantes__isnull = True)

                stock_actualizado = inventario.filter(
                    stock_actual__gte = detalle.cantidad,
                ).update(
                    stock_actual = F("stock_actual") - detalle.cantidad,
                )

                if not stock_actualizado:
                    transaction.set_rollback(True)
                    return redirect(f"{frontend}/carrito?pago=sin-stock")

            transaction.on_commit(
                lambda: enviar_correo_compra(pedido.pk, frontend),
                robust=True,
            )

        return redirect(f"{frontend}/compra/{pedido.id_compra}")    

class CompraDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, id_compra):
        pedidos = (Pedido.objects.filter(Q(tipo_pedido='normal', estado='pagado') | Q(tipo_pedido='personalizado'))
            .prefetch_related('detallepedido_set__producto','detallepedido_set__variante', 'detalles_personalizados'))

        if request.user.is_authenticated:
            pedidos = pedidos.filter(cliente__usuario=request.user)
        else:
            clave_sesion = request.session.session_key

            if clave_sesion:
                pedidos = pedidos.filter(cliente__isnull=True, session_key=clave_sesion)
            else:
                pedidos = pedidos.none()

        pedido = get_object_or_404(pedidos, id_compra=id_compra)
        datos = PedidoSerializer(pedido, context={'request': request}).data

        datos['puede_resenar'] = (pedido.tipo_pedido == 'normal' and pedido.estado == 'pagado' and pedido.etapa == 'entregado'
            and not pedido.cancelado
        )
        datos['token_resenas'] = None

        if datos['puede_resenar']:
            firmador = signing.Signer(salt='resenas-pedido')
            datos['token_resenas'] = firmador.sign(str(pedido.id_compra))

        respuesta = Response(datos)
        respuesta["Cache-Control"] = "no-store"
        return respuesta

class RegistroClienteView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegistroClienteSerializer

class MiCuentaView(generics.RetrieveUpdateAPIView):
    serializer_class = MiCuentaSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(
            Cliente,
            usuario=self.request.user,
        )

class CategoriaProductoViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CategoriaProductoSerializer
    queryset = CategoriaProducto.objects.filter(
        activo=True,
    ).order_by("nombre")
    permission_classes = [AllowAny]
    pagination_class = None

class LoginCorreoView(TokenObtainPairView):
    serializer_class = LoginCorreoSerializer

class HistorialPedidosView(generics.ListAPIView):
    serializer_class = PedidoSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (Pedido.objects
            .filter(cliente__usuario=self.request.user)
            .filter(Q(tipo_pedido='normal', estado='pagado') | Q(tipo_pedido='personalizado'))
            .prefetch_related('detallepedido_set__producto', 'detallepedido_set__variante', 'detalles_personalizados')
            .order_by('-fecha_pedido', '-pk')
        )

def obtener_pedido_resena(token, bloquear=False):
    firmador = signing.Signer(salt='resenas-pedido')

    try:
        codigo_compra = UUID(firmador.unsign(token))
    except (signing.BadSignature, ValueError):
        raise Http404('El Enlace de Reseñas no es Válido')

    consulta = Pedido.objects.all()

    if bloquear:
        consulta = consulta.select_for_update()

    pedido = get_object_or_404(consulta, id_compra=codigo_compra, tipo_pedido='normal', estado='pagado', cancelado=False)

    if pedido.etapa != 'entregado':
        raise PermisoResenaDenegado('Podrás Dejar tu Reseña Después de Retirar o Recibir el Pedido')

    return pedido

class ResenaCompraView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, token):
        pedido = obtener_pedido_resena(token)
        productos = Producto.objects.filter(detallepedido__pedido=pedido, detallepedido__cantidad__gt=0,).distinct()
        lista_productos = []

        for producto in productos:
            resena = Resena.objects.filter(pedido=pedido, producto=producto).first()
            datos_resena = None

            if resena is not None:
                datos_resena = ResenaPublicaSerializer(resena).data

            lista_productos.append({
                'id': producto.id,
                'nombre': producto.nombre,
                'resena': datos_resena
            })

        respuesta = Response({'productos': lista_productos})
        respuesta['Cache-Control'] = 'no-store'
        return respuesta

    def post(self, request, token):
        try:
            with transaction.atomic():
                pedido = obtener_pedido_resena(token, bloquear=True)
                serializer = ResenaCrearSerializer(data=request.data, context={'pedido': pedido})
                serializer.is_valid(raise_exception=True)
                serializer.save(pedido=pedido)
        except IntegrityError:
            return Response(
                {
                    'error': ('Ya Existe una Reseña para este Producto en esta Compra')
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        respuesta = Response(serializer.data, status=status.HTTP_201_CREATED)
        respuesta['Cache-Control'] = 'no-store'
        return respuesta

class ResenasProductoView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request, pk):
        producto = get_object_or_404(Producto, pk=pk, activo=True)
        resenas = list(Resena.objects.filter(producto=producto, activo=True))
        suma = 0

        for resena in resenas:
            suma = suma + resena.calificacion

        cantidad = len(resenas)
        promedio = 0

        if cantidad > 0:
            promedio = round(suma / cantidad, 1)

        serializer = ResenaPublicaSerializer(resenas, many=True)

        return Response({
            'cantidad': cantidad,
            'promedio': promedio,
            'resenas': serializer.data,
        })

class PreguntasFrecuentesView(generics.ListAPIView):
    serializer_class = PreguntaFrecuenteSerializer
    permission_classes = [AllowAny]
    authentication_classes = []
    pagination_class = None

    queryset = (
        PreguntaFrecuente.objects
        .filter(activo=True)
        .order_by('orden', 'pk')
    )
    
class ConsultaCrearView(generics.CreateAPIView):
    serializer_class = ConsultaCrearSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        cliente = None

        if self.request.user.is_authenticated:
            cliente = Cliente.objects.filter(usuario=self.request.user).first()

        serializer.save(cliente=cliente, estado="pendiente")

def enviar_correo_reset(usuario, enlace):
    html = render_to_string(
        'interna/inventario/restablecerContraseña.html',
        {'nombre': usuario.first_name or 'cliente', 'enlace': enlace},
    )
    mensaje = EmailMultiAlternatives(
        subject='Restablece tu contraseña | Amigos del Vuelo',
        body=f"Abre este enlace para crear una nueva contraseña (válido 1 hora):\n{enlace}",
        to=[usuario.email],
    )
    mensaje.attach_alternative(html, 'text/html')
    mensaje.send()

class PedirResetPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        email = str(request.data.get("email") or "").strip()
        usuario = User.objects.filter(email__iexact=email, is_active=True).first()

        if usuario:
            token = signing.dumps(usuario.pk, salt="reset-password")
            frontend = getattr(settings, "WEBPAY_FRONTEND_URL", "http://localhost:5173")
            enviar_correo_reset(usuario, f"{frontend.rstrip('/')}/restablecer-password/{quote(token, safe='')}")

        return Response({"mensaje": "Si el correo existe, te enviamos un enlace."})

class ResetPasswordView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        try:
            usuario = User.objects.get(
                pk=signing.loads(request.data.get("token", ""), salt="reset-password", max_age=3600),
                is_active=True,
            )
        except Exception:
            return Response({"error": "El enlace es inválido o ha expirado"}, status=400)

        password = str(request.data.get("password") or "")

        if not password:
            return Response({"error": "Ingresa una contraseña"}, status=400)
        if password != request.data.get("password_confirmacion"):
            return Response({"error": "Las contraseñas no coinciden"}, status=400)

        usuario.set_password(password)
        usuario.save(update_fields=["password"])
        return Response({"mensaje": "Contraseña actualizada correctamente"})