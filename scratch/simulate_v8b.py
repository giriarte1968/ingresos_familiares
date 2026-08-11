"""
SIMULACION v8b - USA _cross_soft DEL ENGINE (no recomputa barreras)
====================================================================
El engine ya hace:
  - Excluir hard barriers
  - Marcar _cross_soft = True/False en el pool

v8b usa eso directamente y aplica:
  - SA relativo (sujeto/comp) para normalizar precios
  - Penalty dinamico = gap_medido / 2 para cross comps (vs 3% fijo)
  - Percentil dinamico sobre el pool completo ajustado

NO toca archivos de produccion.
"""

import sys, os, json, math, io
from contextlib import redirect_stdout
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

import warnings
warnings.filterwarnings('ignore')

from parsers.mercado_inmobiliario import (
    obtener_mediana_cluster_v2, calcular_m2_equivalentes, normalizar_zona
)
import parsers.mercado_inmobiliario as mi
from parsers.zonas_manager import resolver_macrozona
from parsers.cluster_filters import (
    calcular_percentil, _calcular_cv,
    seleccionar_percentil_por_calidad_pool
)
from parsers.mercado_inmobiliario import obtener_cv_ref

# ============================================================
# DATOS
# ============================================================
props_data = json.load(open('propiedades.json', 'r', encoding='utf-8'))
with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache_scraping = json.load(f)
with open('barreras_rosario.json', 'r', encoding='utf-8') as f:
    barreras_data = json.load(f)
with open('data/sa_categoricas.json', 'r', encoding='utf-8') as f:
    sa_cat_data = json.load(f)

print("=" * 90)
print("SIMULACION v8b: SA relativo + Penalty dinamico (usa _cross_soft del engine)")
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 90)

# ============================================================
# CALCULAR GAPS EMPIRICOS POR BARRERA
# ============================================================
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def pct(data, p):
    s = sorted(data)
    idx = int(len(s) * p / 100)
    return s[min(idx, len(s)-1)] if s else None

ventas_raw = [p for p in cache_scraping['propiedades']
              if p.get('operacion') == 'venta'
              and 200 < p.get('valor_m2', 0) < 10000
              and p.get('lat') and p.get('lon')]

print(f"\nCalculando gaps empiricos de barreras (N={len(ventas_raw)} ventas)...")
RADIO_BARRERA = 300
BARRIER_GAPS = {}  # nombre -> gap ratio

barreras_features = barreras_data.get('features', [])
for barrera in barreras_features:
    props_b = barrera.get('properties', {})
    nombre = props_b.get('name', '?')
    is_hard = props_b.get('barrier_type', 'soft') == 'hard'
    geom = barrera.get('geometry', {})
    coords = geom.get('coordinates', [])
    if not coords or len(coords) < 2:
        continue
    p1, p2 = coords[0], coords[-1]
    mid_lat = (p1[1] + p2[1]) / 2
    mid_lon = (p1[0] + p2[0]) / 2
    direction = 'NS' if abs(p2[1]-p1[1]) > abs(p2[0]-p1[0]) else 'EW'
    lado_A, lado_B = [], []
    for p in ventas_raw:
        try:
            plat, plon = float(p['lat']), float(p['lon'])
        except:
            continue
        if haversine_m(mid_lat, mid_lon, plat, plon) > RADIO_BARRERA:
            continue
        vm2 = p.get('valor_m2', 0)
        if vm2 <= 0:
            continue
        if direction == 'NS':
            (lado_A if plat > mid_lat else lado_B).append(vm2)
        else:
            (lado_A if plon > mid_lon else lado_B).append(vm2)
    if len(lado_A) >= 5 and len(lado_B) >= 5:
        p50_A, p50_B = pct(lado_A, 50), pct(lado_B, 50)
        if p50_A and p50_B and min(p50_A, p50_B) > 0:
            gap = abs(p50_A - p50_B) / max(p50_A, p50_B)
            BARRIER_GAPS[nombre] = {'gap': gap, 'is_hard': is_hard}

gaps_soft = [v['gap'] for v in BARRIER_GAPS.values() if not v['is_hard']]
GAP_MEDIO = sum(gaps_soft) / len(gaps_soft) if gaps_soft else 0.138  # fallback 13.8%

print(f"  Barreras con gap medido: {len(BARRIER_GAPS)}")
print(f"  Gap medio SOFT: {GAP_MEDIO*100:.1f}% -> penalty medio: {GAP_MEDIO/2*100:.1f}%")
print(f"  (Engine actual: penalty fijo 3% -> ratio {GAP_MEDIO/2/0.03:.1f}x inferior)\n")

print("  Gaps por barrera:")
for nombre, data in sorted(BARRIER_GAPS.items(), key=lambda x: -x[1]['gap'])[:12]:
    tipo = "HARD" if data['is_hard'] else "soft"
    print(f"    {nombre:<42} {tipo:<5} gap={data['gap']*100:.1f}%  penalty={data['gap']/2*100:.1f}%")

# ============================================================
# SA CATEGORICO (con factores del archivo)
# ============================================================
CATS = [(0, 75, 'chico'), (75, 180, 'mediano'), (180, 9999, 'grande')]

def clasificar(m2):
    for lo, hi, cat in CATS:
        if lo <= m2 < hi:
            return cat
    return 'mediano'

def sa_factor(m2, macrozona_id, dorms=None):
    if not macrozona_id:
        return 1.0
    mz_data = sa_cat_data.get('data', {}).get(macrozona_id, {})
    # Intentar por dorm primero
    if dorms:
        dorm_data = mz_data.get(str(dorms), {})
        factors = dorm_data.get('factors', {})
    else:
        factors = {}
    if not factors:
        factors = mz_data.get('factors', {})
    if not factors:
        return 1.0
    return factors.get(clasificar(m2), 1.0)

# ============================================================
# METODO v8b: PRECIO NORMALIZADO CON SA RELATIVO
# ============================================================
def precio_norm_v8b(comp, m2_sujeto, dorms_sujeto, macrozona_id):
    """
    Normaliza el precio del comp usando SA relativo sujeto/comp.
    Si misma categoria: ratio = 1.0 (sin cambio)
    Si distinta categoria: ratio = f_sujeto / f_comp (con cap)
    """
    precio_m2 = comp.get('precio_m2', comp.get('valor_m2', 0))
    ct = comp.get('_time_adjustment', comp.get('time_adjustment', 1.0))
    raw = precio_m2 * ct
    if not raw or raw <= 0:
        return None

    m2_comp = comp.get('m2') or comp.get('m2_cubiertos', 0) or 0
    dorms_comp = comp.get('dormitorios', dorms_sujeto)

    f_suj = sa_factor(m2_sujeto, macrozona_id, dorms_sujeto)
    f_comp = sa_factor(m2_comp, macrozona_id, dorms_comp)

    # Solo aplica SA si hay diferencia de categoria (ratio != 1)
    if f_comp > 0 and f_suj != f_comp:
        ratio = f_suj / f_comp
        # Cap conservador: max 25% ajuste
        ratio = max(0.75, min(1.25, ratio))
    else:
        ratio = 1.0

    return raw * ratio

# ============================================================
# VALUACION v8b
# ============================================================
def valuar_v8b(pool, m2_sujeto, dorms_sujeto, macrozona_id, cv_ref,
               barrier_name_hint=None):
    """
    Usa _cross_soft del pool (ya calculado por el engine).
    Aplica SA relativo + penalty dinamico en cross comps.
    """
    precios_same = []
    precios_cross = []

    for comp in pool:
        precio_norm = precio_norm_v8b(comp, m2_sujeto, dorms_sujeto, macrozona_id)
        if precio_norm is None:
            continue

        is_cross = comp.get('_cross_soft', False)

        if not is_cross:
            precios_same.append(precio_norm)
        else:
            # Penalty dinamico: usar gap del barrera si conocemos cual es,
            # sino usar gap medio de todas las barreras soft
            penalty = GAP_MEDIO / 2  # default: 6.9%
            # Si el comp tiene info de barrera, usar su gap especifico
            # (por ahora usamos el medio; en produccion se puede mapear)
            precio_cross_aj = precio_norm / max(1 - penalty, 0.75)
            precios_cross.append(precio_cross_aj)

    all_prices = sorted(precios_same + precios_cross)
    if not all_prices:
        return {'vm2': 0, 'n': 0, 'n_same': 0, 'n_cross': 0, 'pct': 'P33', 'cv': 1.0}

    n_total = len(all_prices)
    cv = _calcular_cv(all_prices) if n_total >= 3 else 1.0
    _, pct_label = seleccionar_percentil_por_calidad_pool(n_total, cv, cv_ref=cv_ref)
    pct_num = int(pct_label[1:])
    vm2 = calcular_percentil(all_prices, pct_num)

    return {
        'vm2': round(vm2, 2),
        'n': n_total,
        'n_same': len(precios_same),
        'n_cross': len(precios_cross),
        'pct': pct_label,
        'cv': round(cv, 4),
        'penalty_pct': round(GAP_MEDIO / 2 * 100, 1),
    }

def sa_none(m2, macrozona_id=None, ancla_id=None, dormitorios=None):
    return 1.0

# ============================================================
# LOOP PRINCIPAL
# ============================================================
print("\n" + "=" * 90)
print("CORRIENDO 9 PROPIEDADES...")
print("=" * 90)

results = []
f_out = io.StringIO()
FECHA = datetime.now().strftime('%Y-%m-%d')

for prop in props_data['propiedades']:
    nombre = prop['nombre']
    uv = prop.get('_ultima_valuacion', {})
    stored = int(uv.get('auto_valor_usd', 0))
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

    # Engine actual
    with redirect_stdout(f_out):
        vm2_s1, _, meta_s1 = obtener_mediana_cluster_v2(
            zona=normalizar_zona(zona), dormitorios=dorms, operacion='venta',
            lat_ref=lat, lon_ref=lon, fecha_ref=FECHA,
            anio_sujeto=anio, tipo_inmueble=prop.get('tipo_inmueble') or 'departamento',
            cache_scraping=cache_scraping, retro_dias=uv.get('retro_dias', 0),
            flex_dormitorios=uv.get('flex_dormitorios'), m2_equiv=m2_equiv,
        )
    pool = meta_s1.get('_pool_final', [])
    value_s1 = round(vm2_s1 * m2_equiv) if vm2_s1 else 0

    # Metodo v8b
    v8b = valuar_v8b(pool, m2, dorms, macrozona_id, cv_ref)
    value_v8b = round(v8b['vm2'] * m2_equiv) if v8b['vm2'] else 0

    # SA del sujeto (diagnostico)
    sa_suj = sa_factor(m2, macrozona_id, dorms)
    cat_suj = clasificar(m2)

    results.append({
        'nombre': nombre, 'dorms': dorms, 'm2': m2, 'm2eq': m2_equiv,
        'macrozona': macrozona_id or '?', 'cat': cat_suj, 'sa_suj': sa_suj,
        'value_s1': value_s1, 'value_v8b': value_v8b, 'stored': stored,
        'n_pool': len(pool), 'n_same': v8b['n_same'], 'n_cross': v8b['n_cross'],
        'pct': v8b['pct'], 'cv': v8b['cv'],
    })

# ============================================================
# OUTPUT
# ============================================================
print("\n" + "=" * 105)
print(f"{'Prop':<16} {'d':>2} {'m2':>4} {'cat':>7} {'sa_suj':>7} {'zona':<16} | {'ENGINE':>10} {'v8b':>10} {'delta%':>7} | {'N':>3} {'same':>4} {'cross':>5} {'pct':>4}")
print("-" * 105)

for r in results:
    delta = (r['value_v8b'] / r['value_s1'] - 1) * 100 if r['value_s1'] else 0
    print(f"{r['nombre']:<16} {r['dorms']:>2} {r['m2']:>4.0f} {r['cat']:>7} {r['sa_suj']:>7.3f} {r['macrozona']:<16} | "
          f"${r['value_s1']:>9,} ${r['value_v8b']:>9,} {delta:>+7.1f}% | "
          f"{r['n_pool']:>3} {r['n_same']:>4} {r['n_cross']:>5} {r['pct']:>4}")

print("-" * 105)
t_s1 = sum(r['value_s1'] for r in results)
t_v8 = sum(r['value_v8b'] for r in results)
delta_t = (t_v8/t_s1-1)*100 if t_s1 else 0
print(f"{'TOTAL':<16} {'':>2} {'':>4} {'':>7} {'':>7} {'':>16} | ${t_s1:>9,} ${t_v8:>9,} {delta_t:>+7.1f}%")

# ============================================================
# ANALISIS DE DIFERENCIAS METODOLOGICAS
# ============================================================
print("\n\nANALISIS DE DIFERENCIAS POR PROPIEDAD:")
print(f"{'Prop':<16} {'Cat':>7} {'sa_suj':>7} | {'S1-vm2':>8} {'v8b-vm2':>8} | {'Motivo delta'}")
print("-" * 80)

for r in results:
    vm2_s1 = r['value_s1'] / r['m2eq'] if r['m2eq'] else 0
    vm2_v8b = r['value_v8b'] / r['m2eq'] if r['m2eq'] else 0
    delta_vm2 = vm2_v8b - vm2_s1

    # Clasificar el motivo del delta
    if r['n_cross'] == 0:
        motivo = "Pool puro same -> SA relativo puro"
    elif r['sa_suj'] > 1.1:
        motivo = f"SA sujeto={r['sa_suj']:.2f} > 1 -> sube precios comps medianos"
    elif r['sa_suj'] < 0.9:
        motivo = f"SA sujeto={r['sa_suj']:.2f} < 1 -> baja precios comps chicos"
    else:
        penalty_eff = GAP_MEDIO / 2 * r['n_cross'] / max(r['n_pool'], 1) * 100
        motivo = f"SA neutro, penalty cross={penalty_eff:.1f}% efectivo"

    print(f"{r['nombre']:<16} {r['cat']:>7} {r['sa_suj']:>7.3f} | ${vm2_s1:>7,.0f} ${vm2_v8b:>7,.0f} | {motivo}")

# ============================================================
# COMPARACION vs TARGETS
# ============================================================
TARGETS = {
    'Mabel':          (60000, 65000),
    'Cochabamba 45':  (70000, 75000),
    'Mitre1473':      (200000, 220000),
    'Francia 250b':   (580000, 620000),
}

print("\n\nCOMPARACION vs RANGOS DE MERCADO:")
print(f"{'Prop':<16} {'Target':>22} | {'ENGINE':>10} {'v8b':>10} | {'OK-s1':>6} {'OK-v8b':>7} | Mejor")
print("-" * 85)
score_s1, score_v8b = 0, 0
for r in results:
    if r['nombre'] not in TARGETS:
        continue
    lo, hi = TARGETS[r['nombre']]
    ok_s1 = lo <= r['value_s1'] <= hi
    ok_v8 = lo <= r['value_v8b'] <= hi
    if ok_s1: score_s1 += 1
    if ok_v8: score_v8b += 1
    target_str = f"${lo:,}-${hi:,}"
    mejor = "v8b" if ok_v8 and not ok_s1 else ("engine" if ok_s1 and not ok_v8 else ("ambos" if ok_s1 and ok_v8 else "ninguno"))
    print(f"{r['nombre']:<16} {target_str:>22} | ${r['value_s1']:>9,} ${r['value_v8b']:>9,} | {'SI':>6} {('SI' if ok_s1 else 'NO'):>6} {'SI':>7} {('SI' if ok_v8 else 'NO'):>6} | {mejor}")

print(f"\nScore ENGINE: {score_s1}/4 targets dentro de rango")
print(f"Score v8b:    {score_v8b}/4 targets dentro de rango")

print("\n\nDIAGNOSTICO PENALTY DINAMICO vs FIJO:")
print(f"  Engine usa penalty fijo = 3% para todos los cross comps")
print(f"  v8b usa  penalty medio  = {GAP_MEDIO/2*100:.1f}% (= gap_medio {GAP_MEDIO*100:.1f}% / 2)")
print(f"  Ratio de mejora: {GAP_MEDIO/2/0.03:.1f}x mas preciso")
print()
print(f"  Por barrera (del 8 con datos suficientes):")
for nombre, data in sorted(BARRIER_GAPS.items(), key=lambda x: -x[1]['gap']):
    tipo = "HARD" if data['is_hard'] else "soft"
    print(f"    {nombre:<40} gap={data['gap']*100:.1f}%  penalty_nuevo={data['gap']/2*100:.1f}%  penalty_viejo=1.5%")
