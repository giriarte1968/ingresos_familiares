"""
BACKTEST 1000 DEPARTAMENTOS AL AZAR - CACHE SCRAPING (VERSION CORREGIDA)
========================================================================
Valua 1.000 departamentos seleccionados al azar del cache de scraping.
Para cada departamento (sujeto):
  - Excluye el sujeto del pool de comparables (match por URL y coords).
  - Valua con ENGINE ACTUAL (S1).
  - Valua con NUEVO METODO v8f.
  - Compara contra el precio publicado real (valor_m2 / valor_usd).
"""

import sys, os, json, math, random, io, time
from contextlib import redirect_stdout
from datetime import datetime

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

import warnings
warnings.filterwarnings('ignore')

import numpy as np

from parsers.mercado_inmobiliario import (
    obtener_mediana_cluster_v2, calcular_m2_equivalentes, normalizar_zona, obtener_cv_ref
)
from parsers.zonas_manager import resolver_macrozona
from parsers.cluster_filters import (
    calcular_percentil, _calcular_cv, seleccionar_percentil_por_calidad_pool
)

# Cargar funciones de v8f
from scratch.simulate_v8f import (
    valuar_v8f, sa_factor_v8f, clasificar_por_dorm, BARRIER_VECTOR_INFO
)

print("=" * 90)
print("BACKTEST: 1.000 DEPARTAMENTOS AL AZAR CONTRA PRECIO PUBLICADO")
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 90)

# 1. Cargar cache
with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache_scraping = json.load(f)

props_all = cache_scraping.get('propiedades', [])
validas = [p for p in props_all
           if p.get('operacion') == 'venta'
           and 300 < p.get('valor_m2', 0) < 6000
           and 20 < p.get('m2', 0) < 400
           and p.get('lat') and p.get('lon')
           and p.get('dormitorios') in [1, 2, 3, 4]
           and p.get('precio', 0) > 10000]

print(f"Departamentos validos en cache: {len(validas)}")

# 2. Seleccionar 1.000 al azar (seed fijo)
random.seed(42)
SAMPLE_SIZE = min(1000, len(validas))
sample = random.sample(validas, SAMPLE_SIZE)
print(f"Muestra seleccionada para backtest: {len(sample)} propiedades")

# 3. Loop de valuacion
f_out = io.StringIO()
FECHA = datetime.now().strftime('%Y-%m-%d')

results = []
t0 = time.time()

for idx, prop in enumerate(sample):
    if (idx + 1) % 100 == 0 or idx == 0:
        print(f"  Procesando {idx + 1}/{len(sample)} ({time.time()-t0:.1f}s)...")
        
    prop_url = prop.get('url', '')
    lat = float(prop['lat'])
    lon = float(prop['lon'])
    dorms = int(prop['dormitorios'])
    m2 = float(prop['m2'])
    precio_pub = float(prop['precio'])
    vm2_pub = float(prop['valor_m2'])
    zona = prop.get('zona', '') or ''
    anio = prop.get('antiquity') or 2020
    if isinstance(anio, (int, float)):
        anio = int(datetime.now().year - anio) if 0 < anio < 120 else 2020
    else:
        anio = 2020
        
    m2_equiv = m2
    
    macrozona_id = None
    try:
        _mz = resolver_macrozona({'zona': normalizar_zona(zona) or '', 'lat': lat, 'lon': lon})
        macrozona_id = _mz.get('macrozona_id')
    except:
        pass

    cv_ref = obtener_cv_ref(macrozona_id)

    # --- ENGINE ACTUAL (S1) ---
    flex_d = [max(1, dorms-1), dorms, min(4, dorms+1)]
    with redirect_stdout(f_out):
        vm2_s1, n_s1, meta_s1 = obtener_mediana_cluster_v2(
            zona=normalizar_zona(zona), dormitorios=dorms, operacion='venta',
            lat_ref=lat, lon_ref=lon, fecha_ref=FECHA,
            anio_sujeto=anio, tipo_inmueble='departamento',
            cache_scraping=cache_scraping, retro_dias=0,
            flex_dormitorios=flex_d, m2_equiv=m2_equiv,
        )
    
    # Excluir la propiedad misma del pool para evitar data leakage
    def _f(v):
        try: return float(v) if v is not None else 0.0
        except: return 0.0
    raw_pool = meta_s1.get('_pool_final', [])
    pool = [c for c in raw_pool if c.get('url') != prop_url and (_f(c.get('lat')) != lat or _f(c.get('lon')) != lon)]
    
    if not pool or not vm2_s1 or vm2_s1 <= 0:
        continue
        
    price_s1 = vm2_s1 * m2
    
    # --- METODO v8f ---
    v8f = valuar_v8f(pool, m2, dorms, macrozona_id, lat, lon, cv_ref)
    vm2_v8f = v8f['vm2']
    if not vm2_v8f or vm2_v8f <= 0:
        continue
    price_v8f = vm2_v8f * m2

    # Errores
    ape_s1 = abs(price_s1 - precio_pub) / precio_pub * 100
    ape_v8f = abs(price_v8f - precio_pub) / precio_pub * 100
    
    results.append({
        'url': prop_url,
        'dorm': dorms,
        'm2': m2,
        'precio_pub': precio_pub,
        'vm2_pub': vm2_pub,
        'price_s1': price_s1,
        'vm2_s1': vm2_s1,
        'ape_s1': ape_s1,
        'price_v8f': price_v8f,
        'vm2_v8f': vm2_v8f,
        'ape_v8f': ape_v8f,
        'n_pool': len(pool),
        'n_same': v8f['n_same'],
        'n_cross': v8f['n_cross'],
    })

t_total = time.time() - t0
print(f"\nBacktest completado en {t_total:.1f}s. Valuaciones validas: {len(results)}/{len(sample)}")

# ============================================================
# METRICAS Y ESTADISTICAS COMPARATIVAS
# ============================================================
if results:
    apes_s1 = np.array([r['ape_s1'] for r in results])
    apes_v8f = np.array([r['ape_v8f'] for r in results])

    mae_usd_s1 = np.mean([abs(r['price_s1'] - r['precio_pub']) for r in results])
    mae_usd_v8f = np.mean([abs(r['price_v8f'] - r['precio_pub']) for r in results])

    mae_vm2_s1 = np.mean([abs(r['vm2_s1'] - r['vm2_pub']) for r in results])
    mae_vm2_v8f = np.mean([abs(r['vm2_v8f'] - r['vm2_pub']) for r in results])

    # R2 score
    y_true = np.array([r['precio_pub'] for r in results])
    y_s1 = np.array([r['price_s1'] for r in results])
    y_v8f = np.array([r['price_v8f'] for r in results])

    r2_s1 = 1 - np.sum((y_true - y_s1)**2) / np.sum((y_true - y_true.mean())**2)
    r2_v8f = 1 - np.sum((y_true - y_v8f)**2) / np.sum((y_true - y_true.mean())**2)

    within_10_s1 = np.sum(apes_s1 <= 10) / len(results) * 100
    within_10_v8f = np.sum(apes_v8f <= 10) / len(results) * 100

    within_15_s1 = np.sum(apes_s1 <= 15) / len(results) * 100
    within_15_v8f = np.sum(apes_v8f <= 15) / len(results) * 100

    within_20_s1 = np.sum(apes_s1 <= 20) / len(results) * 100
    within_20_v8f = np.sum(apes_v8f <= 20) / len(results) * 100

    print("\n" + "=" * 90)
    print("RESULTADOS DEL BACKTEST (1.000 DEPARTAMENTOS AL AZAR)")
    print("=" * 90)

    print(f"\n{'Metrica Evaluada':<35} {'ENGINE ACTUAL (S1)':>20} {'METODO NUEVO (v8f)':>20} {'Mejora':>12}")
    print("-" * 90)
    print(f"{'MAPE (Mean Error %)':<35} {np.mean(apes_s1):>19.2f}% {np.mean(apes_v8f):>19.2f}% {np.mean(apes_s1)-np.mean(apes_v8f):>+11.2f}%")
    print(f"{'MedAPE (Median Error %)':<35} {np.median(apes_s1):>19.2f}% {np.median(apes_v8f):>19.2f}% {np.median(apes_s1)-np.median(apes_v8f):>+11.2f}%")
    print(f"{'MAE USD (Error medio en USD)':<35} ${mae_usd_s1:>18,.0f} ${mae_usd_v8f:>18,.0f} ${mae_usd_s1-mae_usd_v8f:>+11,.0f}")
    print(f"{'MAE $/m2 (Error medio $/m2)':<35} ${mae_vm2_s1:>18,.1f} ${mae_vm2_v8f:>18,.1f} ${mae_vm2_s1-mae_vm2_v8f:>+11.1f}")
    print(f"{'Coeficiente R² (Explicacion)':<35} {r2_s1:>20.4f} {r2_v8f:>20.4f} {r2_v8f-r2_s1:>+12.4f}")
    print("-" * 90)
    print(f"{'% dentro del +-10% de tolerancia':<35} {within_10_s1:>19.1f}% {within_10_v8f:>19.1f}% {within_10_v8f-within_10_s1:>+11.1f}%")
    print(f"{'% dentro del +-15% de tolerancia':<35} {within_15_s1:>19.1f}% {within_15_v8f:>19.1f}% {within_15_v8f-within_15_s1:>+11.1f}%")
    print(f"{'% dentro del +-20% de tolerancia':<35} {within_20_s1:>19.1f}% {within_20_v8f:>19.1f}% {within_20_v8f-within_20_s1:>+11.1f}%")

    print("\n\nMAPE POR TIPO DE DORMITORIO:")
    print(f"{'Dormitorios':<15} {'N props':>10} {'ENGINE (S1)':>15} {'NUEVO (v8f)':>15} {'Ganador':>12}")
    print("-" * 70)
    for d in [1, 2, 3, 4]:
        sub = [r for r in results if r['dorm'] == d]
        if not sub: continue
        e_s1 = np.mean([r['ape_s1'] for r in sub])
        e_v8f = np.mean([r['ape_v8f'] for r in sub])
        win = "v8f" if e_v8f < e_s1 else "ENGINE"
        print(f"{d:<15} {len(sub):>10} {e_s1:>14.2f}% {e_v8f:>14.2f}% {win:>12}")
