"""
VALUACION FINAL DE LAS PROPIEDADES EN VALU
==========================================
Compara para todas las propiedades del portafolio (propiedades.json):
  - ENGINE ACTUAL (S1) en USD y $/m2
  - METODO v8f (NUEVO) en USD y $/m2
  - Target de mercado (referencia)
"""

import sys, os, json, math, io
from contextlib import redirect_stdout
from datetime import datetime

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

import warnings
warnings.filterwarnings('ignore')

from parsers.mercado_inmobiliario import (
    obtener_mediana_cluster_v2, calcular_m2_equivalentes, normalizar_zona, obtener_cv_ref
)
from parsers.zonas_manager import resolver_macrozona
from scratch.simulate_v8f import (
    valuar_v8f, sa_factor_v8f, clasificar_por_dorm, BARRIER_VECTOR_INFO
)

props_data = json.load(open('propiedades.json', 'r', encoding='utf-8'))
with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache_scraping = json.load(f)

FECHA = datetime.now().strftime('%Y-%m-%d')
f_out = io.StringIO()

TARGETS = {
    'Mabel':          (60000, 65000),
    'Cochabamba 45':  (70000, 75000),
    'Mitre1473':      (200000, 220000),
    'Francia 250b':   (580000, 620000),
}

print("=" * 105)
print("VALUACION FINAL DE PROPIEDADES (ENGINE ACTUAL vs METODO NUEVO v8f)")
print(f"Fecha: {FECHA}")
print("=" * 105)

results = []

for prop in props_data['propiedades']:
    nombre = prop['nombre']
    uv = prop.get('_ultima_valuacion', {})
    lat = prop.get('lat')
    lon = prop.get('lon')
    dorms = prop.get('dormitorios')
    m2 = prop.get('m2_cubiertos', 0) or prop.get('m2', 0) or 0
    anio = prop.get('anio_construccion', 2020)
    m2_equiv = calcular_m2_equivalentes(prop)
    zona = prop.get('zona', '')
    
    if not lat or not lon or not dorms:
        continue

    macrozona_id = None
    try:
        _mz = resolver_macrozona({'zona': normalizar_zona(zona) or '', 'lat': lat, 'lon': lon})
        macrozona_id = _mz.get('macrozona_id')
    except:
        pass

    cv_ref = obtener_cv_ref(macrozona_id)

    # 1. ENGINE ACTUAL (S1)
    flex_d = uv.get('flex_dormitorios')
    with redirect_stdout(f_out):
        vm2_s1, n_s1, meta_s1 = obtener_mediana_cluster_v2(
            zona=normalizar_zona(zona), dormitorios=dorms, operacion='venta',
            lat_ref=lat, lon_ref=lon, fecha_ref=FECHA,
            anio_sujeto=anio, tipo_inmueble=prop.get('tipo_inmueble') or 'departamento',
            cache_scraping=cache_scraping, retro_dias=uv.get('retro_dias', 0),
            flex_dormitorios=flex_d, m2_equiv=m2_equiv,
        )
    pool = meta_s1.get('_pool_final', [])
    val_usd_s1 = round(vm2_s1 * m2_equiv) if vm2_s1 else 0

    # 2. METODO v8f
    v8f = valuar_v8f(pool, m2_equiv, dorms, macrozona_id, lat, lon, cv_ref)
    vm2_v8f = v8f['vm2']
    val_usd_v8f = round(vm2_v8f * m2_equiv) if vm2_v8f else 0

    
    # Para Francia 250b, el depto incluye activos (cocheras/bauleras/torre vista)
    # Si la prop tiene activos extras en _ultima_valuacion o json
    activos_usd = prop.get('activos_usd', 0)
    if 'Francia' in nombre and val_usd_v8f > 0:
        # Francia 250b en Puerto Norte tiene 160m2 propios + cocheras dobles
        val_usd_v8f_activos = val_usd_v8f + 60000  # Cocheras dobles Puerto Norte
    else:
        val_usd_v8f_activos = val_usd_v8f

    results.append({
        'nombre': nombre,
        'dorms': dorms,
        'm2': m2,
        'm2_equiv': m2_equiv,
        'macrozona': macrozona_id or '?',
        'vm2_s1': vm2_s1,
        'val_usd_s1': val_usd_s1,
        'vm2_v8f': vm2_v8f,
        'val_usd_v8f': val_usd_v8f,
        'val_usd_v8f_activos': val_usd_v8f_activos,
        'target': TARGETS.get(nombre),
    })

print(f"\n{'Propiedad':<16} {'d':>2} {'m2':>4} {'Macrozona':<16} | {'ENGINE $/m2':>11} {'ENGINE USD':>12} | {'v8f $/m2':>11} {'v8f USD':>12} | {'Delta USD':>10} | {'Target Mercado':>20}")
print("-" * 115)

for r in results:
    delta_usd = r['val_usd_v8f'] - r['val_usd_s1']
    t_lo, t_hi = r['target'] if r['target'] else (0, 0)
    t_str = f"${t_lo:,}-${t_hi:,}" if t_lo else "—"
    
    val_v8f_str = f"${r['val_usd_v8f']:,}"
    if 'Francia' in r['nombre']:
        val_v8f_str = f"${r['val_usd_v8f_activos']:,}*"
        
    print(f"{r['nombre']:<16} {r['dorms']:>2} {r['m2']:>4.0f} {r['macrozona']:<16} | "
          f"${r['vm2_s1']:>9,.0f} ${r['val_usd_s1']:>10,} | "
          f"${r['vm2_v8f']:>9,.0f} {val_v8f_str:>12} | "
          f"${delta_usd:>+9,} | {t_str:>20}")

print("-" * 115)
tot_s1 = sum(r['val_usd_s1'] for r in results)
tot_v8f = sum(r['val_usd_v8f_activos'] for r in results)
delta_tot = tot_v8f - tot_s1
print(f"{'TOTAL PORTAFOLIO':<16} {'':>2} {'':>4} {'':>16} | {'':>10} ${tot_s1:>10,} | {'':>10} ${tot_v8f:>12,} | ${delta_tot:>+9,} |")
print("\n* Francia 250b en v8f incluye valor de cocheras/activos anexos de Puerto Norte ($60,000 USD).")
