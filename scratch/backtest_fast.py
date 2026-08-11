import sys, os, json, random, time
import numpy as np

sys_path = r'c:\Users\Gustavo\ingresos_familiares_st'
os.chdir(sys_path)
sys.path.insert(0, sys_path)

import warnings
warnings.filterwarnings('ignore')

from parsers.mercado_inmobiliario import valuar_propiedad_v7, obtener_mediana_cluster_v2, calcular_m2_equivalentes, normalizar_zona
from parsers.zonas_manager import resolver_macrozona
from parsers.cluster_filters import _calcular_cv, seleccionar_percentil_por_calidad_pool
from parsers.mercado_inmobiliario import obtener_cv_ref

props_data = json.load(open('propiedades.json', 'r', encoding='utf-8'))
cache_scraping = json.load(open('cache_scraping.json', 'r', encoding='utf-8'))
barreras_data = json.load(open('barreras_rosario.json', 'r', encoding='utf-8'))
flex_dorm_data = json.load(open('data/flex_dorm_factors.json', 'r', encoding='utf-8'))['data']

all_props = [p for p in cache_scraping.get('propiedades', []) if p.get('operacion') == 'venta' and p.get('precio_usd', 0) > 15000 and 20 < p.get('m2', 0) < 350 and p.get('lat') and p.get('lon') and p.get('dormitorios')]

random.seed(42)
sample = random.sample(all_props, min(300, len(all_props)))

FECHA = "2026-08-11"

def clasificar_por_dorm(m2, dorms):
    if dorms == 1: return "chico" if m2 < 45 else ("mediano" if m2 <= 75 else "grande")
    elif dorms == 2: return "chico" if m2 < 75 else ("mediano" if m2 <= 130 else "grande")
    elif dorms == 3: return "chico" if m2 < 115 else ("mediano" if m2 <= 220 else "grande")
    else: return "chico" if m2 < 140 else ("mediano" if m2 <= 250 else "grande")

results = []
for i, prop in enumerate(sample):
    lat = prop.get('lat')
    lon = prop.get('lon')
    dorms = prop.get('dormitorios')
    m2 = prop.get('m2', 0)
    precio_pub = prop.get('precio_usd', 0)
    vm2_pub = precio_pub / m2 if m2 > 0 else 0
    zona = prop.get('zona', '')
    
    if not lat or not lon or not dorms or not m2 or not precio_pub: continue
    
    macrozona_id = None
    try:
        _mz = resolver_macrozona({'zona': normalizar_zona(zona) or '', 'lat': lat, 'lon': lon})
        macrozona_id = _mz.get('macrozona_id')
    except: pass
    
    cv_ref = obtener_cv_ref(macrozona_id)
    
    # Engine actual (S1)
    vm2_s1, _, meta_s1 = obtener_mediana_cluster_v2(
        zona=normalizar_zona(zona), dormitorios=dorms, operacion='venta',
        lat_ref=lat, lon_ref=lon, fecha_ref=FECHA,
        anio_sujeto=2020, tipo_inmueble='departamento',
        cache_scraping=cache_scraping, retro_dias=0,
        flex_dormitorios=1, m2_equiv=m2,
    )
    price_s1 = round(vm2_s1 * m2) if vm2_s1 else 0
    
    # Engine v8f
    vm2_v8f, _, meta_v8f = obtener_mediana_cluster_v2(
        zona=normalizar_zona(zona), dormitorios=dorms, operacion='venta',
        lat_ref=lat, lon_ref=lon, fecha_ref=FECHA,
        anio_sujeto=2020, tipo_inmueble='departamento',
        cache_scraping=cache_scraping, retro_dias=60,
        flex_dormitorios=[1, 2, 3, 4, 5], m2_equiv=m2,
    )
    price_v8f = round(vm2_v8f * m2) if vm2_v8f else 0
    
    if price_s1 > 0 and price_v8f > 0:
        ape_s1 = abs(price_s1 - precio_pub) / precio_pub * 100
        ape_v8f = abs(price_v8f - precio_pub) / precio_pub * 100
        results.append({
            'precio_pub': precio_pub, 'vm2_pub': vm2_pub,
            'price_s1': price_s1, 'vm2_s1': vm2_s1, 'ape_s1': ape_s1,
            'price_v8f': price_v8f, 'vm2_v8f': vm2_v8f, 'ape_v8f': ape_v8f,
            'dorms': dorms
        })

apes_s1 = np.array([r['ape_s1'] for r in results])
apes_v8f = np.array([r['ape_v8f'] for r in results])
mae_usd_s1 = np.mean([abs(r['price_s1'] - r['precio_pub']) for r in results])
mae_usd_v8f = np.mean([abs(r['price_v8f'] - r['precio_pub']) for r in results])
mae_vm2_s1 = np.mean([abs(r['vm2_s1'] - r['vm2_pub']) for r in results])
mae_vm2_v8f = np.mean([abs(r['vm2_v8f'] - r['vm2_pub']) for r in results])

y_true = np.array([r['precio_pub'] for r in results])
y_s1 = np.array([r['price_s1'] for r in results])
y_v8f = np.array([r['price_v8f'] for r in results])

r2_s1 = 1 - np.sum((y_true - y_s1)**2) / np.sum((y_true - y_true.mean())**2)
r2_v8f = 1 - np.sum((y_true - y_v8f)**2) / np.sum((y_true - y_true.mean())**2)

within_10_s1 = np.sum(apes_s1 <= 10) / len(results) * 100
within_10_v8f = np.sum(apes_v8f <= 10) / len(results) * 100
within_15_s1 = np.sum(apes_s1 <= 15) / len(results) * 100
within_15_v8f = np.sum(apes_v8f <= 15) / len(results) * 100

print(json.dumps({
    'n_evaluated': len(results),
    'mape_s1': round(float(np.mean(apes_s1)), 2),
    'mape_v8f': round(float(np.mean(apes_v8f)), 2),
    'medape_s1': round(float(np.median(apes_s1)), 2),
    'medape_v8f': round(float(np.median(apes_v8f)), 2),
    'mae_usd_s1': round(float(mae_usd_s1), 0),
    'mae_usd_v8f': round(float(mae_usd_v8f), 0),
    'mae_vm2_s1': round(float(mae_vm2_s1), 1),
    'mae_vm2_v8f': round(float(mae_vm2_v8f), 1),
    'r2_s1': round(float(r2_s1), 4),
    'r2_v8f': round(float(r2_v8f), 4),
    'within_10_s1': round(float(within_10_s1), 1),
    'within_10_v8f': round(float(within_10_v8f), 1),
    'within_15_s1': round(float(within_15_s1), 1),
    'within_15_v8f': round(float(within_15_v8f), 1)
}, indent=2))
