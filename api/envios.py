import json
from functools import lru_cache
from pathlib import Path
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from interna.models import TarifaEnvio

@lru_cache(maxsize=1)
def regiones_chile():
    ruta = Path(__file__).resolve().parent / 'data' / 'regiones_comunas.json'
    return json.loads(ruta.read_text(encoding='utf-8'))['regiones']

def resolver_envio(codigo_region, codigo_comuna):
    region = next((r for r in regiones_chile() if r['codigo'] == codigo_region), None)

    if region is None:
        raise serializers.ValidationError('Selecciona una Región Válida')

    comuna = next((c for c in region['comunas'] if c['codigo'] == codigo_comuna), None)

    if comuna is None:
        raise serializers.ValidationError('Selecciona una Comuna de esa Región')

    tarifa = TarifaEnvio.objects.filter(codigo_region=codigo_region, activo=True).first()

    if tarifa is None:
        raise serializers.ValidationError('No hay Envío Disponible Para esa Región')

    return {'region_entrega': region['nombre'], 'comuna_entrega': comuna['nombre'], 'costo_envio': tarifa.costo}

class OpcionesEnvioView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        tarifas = dict(TarifaEnvio.objects.filter(activo=True).values_list('codigo_region', 'costo'))

        datos = [
            dict(
                region,
                costo_envio=(
                    format(tarifas[region['codigo']], 'f')
                    if region['codigo'] in tarifas else None
                ),
            )
            for region in regiones_chile()
        ]

        respuesta = Response(datos)
        respuesta['Cache-Control'] = 'no-store'
        return respuesta