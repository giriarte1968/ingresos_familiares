import json, copy, sys, os
from contextlib import redirect_stdout

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import (
    obtener_mediana_cluster_v2, normalizar_zona, obtener_cv_ref
)
from parsers.zonas_manager import resolver_macrozona
from scratch.simulate_v8f import valuar_v8f

with open('propiedades.json', 'r', encoding='utf-8') as f:
    props = json.load(f)

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

cochabamba = None
for p in props['propiedades']:
    if 'Cochabamba' in p['nombre']:
        cochabamba = p
        break

lat, lon = cochabamba['lat'], cochabamba['lon']
dorms = cochabamba['dormitorios']
m2 = cochabamba['m2_cubiertos']
zona = cochabamba['zona']
uv = cochabamba['_ultima_valuacion']

# 10 publicaciones reales de Zonaprop en Republica de la Sexta
nuevas_publis = [
    {"precio": 27000, "m2": 23, "dormitorios": 1, "tipo": "departamento", "operacion": "venta", "moneda": "USD", "direccion": "Chacabuco al 1900", "valor_m2": 1173.9, "lat": -32.9621, "lon": -60.6245, "zona": "República de la Sexta"},
    {"precio": 71500, "m2": 41, "dormitorios": 1, "tipo": "departamento", "operacion": "venta", "moneda": "USD", "direccion": "1 de Mayo al 1100", "valor_m2": 1743.9, "lat": -32.9585, "lon": -60.6291, "zona": "República de la Sexta"},
    {"precio": 60000, "m2": 41, "dormitorios": 1, "tipo": "departamento", "operacion": "venta", "moneda": "USD", "direccion": "Ituzaingo 92", "valor_m2": 1463.4, "lat": -32.9642, "lon": -60.6273, "zona": "República de la Sexta"},
    {"precio": 85000, "m2": 67, "dormitorios": 2, "tipo": "departamento", "operacion": "venta", "moneda": "USD", "direccion": "Juan Manuel de Rosas 2095", "valor_m2": 1268.6, "lat": -32.9602, "lon": -60.6268, "zona": "República de la Sexta"},
    {"precio": 75000, "m2": 66, "dormitorios": 2, "tipo": "departamento", "operacion": "venta", "moneda": "USD", "direccion": "Laprida al 1400", "valor_m2": 1136.3, "lat": -32.9568, "lon": -60.6310, "zona": "República de la Sexta"},
    {"precio": 103121, "m2": 70, "dormitorios": 2, "tipo": "departamento", "operacion": "venta", "moneda": "USD", "direccion": "Ayacucho al 1400", "valor_m2": 1473.1, "lat": -32.9615, "lon": -60.6302, "zona": "República de la Sexta"},
    {"precio": 68000, "m2": 83, "dormitorios": 3, "tipo": "departamento", "operacion": "venta", "moneda": "USD", "direccion": "Cochabamba 45", "valor_m2": 819.2, "lat": -32.9611, "lon": -60.6264, "zona": "República de la Sexta"},
    {"precio": 300000, "m2": 126, "dormitorios": 3, "tipo": "departamento", "operacion": "venta", "moneda": "USD", "direccion": "J. M. de Rosas y La Paz", "valor_m2": 2380.9, "lat": -32.9625, "lon": -60.6255, "zona": "República de la Sexta"},
    {"precio": 195000, "m2": 130, "dormitorios": 3, "tipo": "departamento", "operacion": "venta", "moneda": "USD", "direccion": "Colón y Pasco", "valor_m2": 1500.0, "lat": -32.9638, "lon": -60.6249, "zona": "República de la Sexta"},
    {"precio": 350000, "m2": 220, "dormitorios": 4, "tipo": "departamento", "operacion": "venta", "moneda": "USD", "direccion": "Av Pellegrini 600", "valor_m2": 1590.9, "lat": -32.9572, "lon": -60.6338, "zona": "República de la Sexta"}
]

f_out = open(os.devnull, 'w')

# 1. EVALUACION ANTES DE INYECTAR LAS 10 PUBLIS
with redirect_stdout(f_out):
    vm2_s1_antes, _, meta_antes = obtener_mediana_cluster_v2(
        zona=normalizar_zona(zona), dormitorios=dorms, operacion='venta',
        lat_ref=lat, lon_ref=lon, fecha_ref='2026-08-10',
        anio_sujeto=1966, tipo_inmueble='departamento',
        cache_scraping=cache, retro_dias=60,
        flex_dormitorios=uv.get('flex_dormitorios'), m2_equiv=m2
    )

pool_antes = meta_antes.get('_pool_final', [])
mz_info = resolver_macrozona({'lat': lat, 'lon': lon, 'zona': normalizar_zona(zona) or ''})
macrozona_id = mz_info.get('macrozona_id') if isinstance(mz_info, dict) else 'macrocentro'
cv_ref = obtener_cv_ref(macrozona_id)

v8f_antes = valuar_v8f(pool_antes, m2, dorms, macrozona_id, lat, lon, cv_ref)
val_antes = round(v8f_antes['vm2'] * m2)

# 2. INYECTAR LAS 10 PUBLIS AL CACHE
cache_expandido = copy.deepcopy(cache)
cache_expandido['propiedades'].extend(nuevas_publis)

# 3. EVALUACION DESPUES DE INYECTAR LAS 10 PUBLIS
with redirect_stdout(f_out):
    vm2_s1_despues, _, meta_despues = obtener_mediana_cluster_v2(
        zona=normalizar_zona(zona), dormitorios=dorms, operacion='venta',
        lat_ref=lat, lon_ref=lon, fecha_ref='2026-08-10',
        anio_sujeto=1966, tipo_inmueble='departamento',
        cache_scraping=cache_expandido, retro_dias=60,
        flex_dormitorios=uv.get('flex_dormitorios'), m2_equiv=m2
    )

pool_despues = meta_despues.get('_pool_final', [])
v8f_despues = valuar_v8f(pool_despues, m2, dorms, macrozona_id, lat, lon, cv_ref)
val_despues = round(v8f_despues['vm2'] * m2)

print("=" * 90, flush=True)
print("EXPERIMENTO DE SIMULACION: COCHABAMBA 45 CON CACHE EXPANDIDO (10 PUBLIS NUEVAS)", flush=True)
print("=" * 90, flush=True)

print(f"Target de Mercado Objetivo: USD $70,000 - $75,000", flush=True)
print("-" * 90, flush=True)
print(f"Pool original de comparables:  {len(pool_antes)} comps", flush=True)
print(f"Pool expandido de comparables: {len(pool_despues)} comps", flush=True)
print("-" * 90, flush=True)

print(f"Valuacion v8f ANTES de las publis:  USD ${val_antes:,} (${v8f_antes['vm2']:,.0f}/m2)", flush=True)
print(f"Valuacion v8f DESPUES de publis:    USD ${val_despues:,} (${v8f_despues['vm2']:,.0f}/m2)", flush=True)
print(f"Diferencia / Impacto en Valuacion:   USD ${val_despues - val_antes:+,} ({(val_despues/val_antes-1)*100:+.2f}%)", flush=True)
print("=" * 90, flush=True)
