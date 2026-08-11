import sys, os, json, math, io
from contextlib import redirect_stdout
from datetime import datetime

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

import warnings
warnings.filterwarnings('ignore')

from parsers.mercado_inmobiliario import (
    obtener_mediana_cluster_v2, normalizar_zona, obtener_cv_ref
)
from parsers.zonas_manager import resolver_macrozona
from scratch.simulate_v8f import valuar_v8f

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
    'Vera Mujica':    (50000, 55000),
}

def calcular_m2_equivalentes_ajustado(prop):
    m2_cub = prop.get('m2_cubiertos', 0) or prop.get('m2', 0) or 0
    m2_semi = prop.get('m2_semicubiertos', 0) or 0
    m2_desc = prop.get('m2_descubiertos_propios', 0) or 0
    m2_patio = prop.get('m2_descubiertos_comun_exclusivo', 0) or 0
    
    # Patios internos de planta baja: 0.15 - 0.20
    # Patios al frente / terrazas propias: 0.25 - 0.30
    # Semicubierto / balcones: 0.50
    factor_patio = 0.18 if prop.get('vista') == 'interna' else 0.25
    
    return m2_cub + (0.50 * m2_semi) + (0.25 * m2_desc) + (factor_patio * m2_patio)

results = []

for prop in props_data['propiedades']:
    nombre = prop['nombre']
    uv = prop.get('_ultima_valuacion', {})
    lat = prop.get('lat')
    lon = prop.get('lon')
    dorms = prop.get('dormitorios')
    m2 = prop.get('m2_cubiertos', 0) or prop.get('m2', 0) or 0
    anio = prop.get('anio_construccion', 2020)
    m2_equiv = calcular_m2_equivalentes_ajustado(prop)
    zona = prop.get('zona', '')
    piso = prop.get('piso')
    vista = prop.get('vista', '')
    
    if not lat or not lon or not dorms: continue

    macrozona_id = None
    try:
        _mz = resolver_macrozona({'zona': normalizar_zona(zona) or '', 'lat': lat, 'lon': lon})
        macrozona_id = _mz.get('macrozona_id')
    except: pass

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

    # 2. METODO v8f CONTINUO CON AJUSTE FISICO DE PISO / DISPOSICION
    # Para Planta Baja Interna (piso 0, vista interna) se aplica factor_disposicion = 0.83 (-17%)
    # respecto a la mediana del mercado promedio (pisos medios frente)
    factor_disposicion = 0.83 if (piso == 0 and vista == 'interna') else 1.0
    
    v8f = valuar_v8f(pool, m2_equiv, dorms, macrozona_id, lat, lon, cv_ref)
    vm2_v8f = v8f['vm2'] * factor_disposicion
    val_usd_v8f = round(vm2_v8f * m2_equiv) if vm2_v8f else 0
    
    activos_usd = prop.get('activos_usd', 0)
    if 'Francia' in nombre and val_usd_v8f > 0:
        val_usd_v8f_activos = val_usd_v8f + 60000
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

print("\n" + "=" * 125, flush=True)
print("VALUACION FINAL DE PROPIEDADES (SA CONTINUO + AJUSTE PATIO/DISPOSICION PB INTERNO)", flush=True)
print(f"Fecha: {FECHA}", flush=True)
print("=" * 125, flush=True)

print(f"\n{'Propiedad':<16} {'d':>2} {'m2':>4} {'m2eq':>5} {'Macrozona':<16} | {'ENGINE $/m2':>11} {'ENGINE USD':>12} | {'v8f $/m2':>11} {'v8f USD':>12} | {'Delta USD':>10} | {'Target Mercado':>20}", flush=True)
print("-" * 125, flush=True)

for r in results:
    delta_usd = r['val_usd_v8f_activos'] - r['val_usd_s1']
    t_lo, t_hi = r['target'] if r['target'] else (0, 0)
    t_str = f"${t_lo:,}-${t_hi:,}" if t_lo else "—"
    
    val_v8f_str = f"${r['val_usd_v8f']:,}"
    if 'Francia' in r['nombre']:
        val_v8f_str = f"${r['val_usd_v8f_activos']:,}*"
        
    print(f"{r['nombre']:<16} {r['dorms']:>2} {r['m2']:>4.0f} {r['m2_equiv']:>5.1f} {r['macrozona']:<16} | "
          f"${r['vm2_s1']:>9,.0f} ${r['val_usd_s1']:>10,} | "
          f"${r['vm2_v8f']:>9,.0f} {val_v8f_str:>12} | "
          f"${delta_usd:>+9,} | {t_str:>20}", flush=True)

print("-" * 125, flush=True)
tot_s1 = sum(r['val_usd_s1'] for r in results)
tot_v8f = sum(r['val_usd_v8f_activos'] for r in results)
delta_tot = tot_v8f - tot_s1
print(f"{'TOTAL PORTAFOLIO':<16} {'':>2} {'':>4} {'':>5} {'':>16} | {'':>10} ${tot_s1:>10,} | {'':>10} ${tot_v8f:>12,} | ${delta_tot:>+9,} |", flush=True)
print("\n* Francia 250b en v8f incluye valor de cocheras/activos anexos de Puerto Norte ($60,000 USD).", flush=True)
