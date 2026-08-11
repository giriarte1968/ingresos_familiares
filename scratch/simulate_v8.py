"""
SIMULACION v8 - METODO PROPUESTO: SA CATEGORICO POR DORM + PENALTY DINAMICO
=============================================================================
Reemplaza:  alpha_blend + penalty 3% fijo
Por:        SA relativo (sujeto/comp) + penalty = gap_barrera/2 (empirico)

Formula central:
  vm2_norm = precio_m2 * CT * (sa_sujeto / sa_comp)  [mismo dorm → ratio=1]
  si cross: vm2_norm /= (1 - penalty_barrera)         [penalty = gap_real/2]
  vm2 = percentil(sorted(vm2_norms), P_dinamico)

NO toca archivos de produccion. Solo simulacion.
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
print("SIMULACION v8: SA por-dorm + Penalty Dinamico (sin alpha/blend/3% fijo)")
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print(f"Cache: {len(cache_scraping['propiedades'])} props")
print("=" * 90)

# ============================================================
# SA CATEGORICO POR DORMITORIO
# ============================================================
# Categorias universales (no por dorm, simplificacion pragmatica)
# La diferencia clave vs actual es la formula de normalizacion (ratio)
CATS_UNIV = [(0, 75, 'chico'), (75, 180, 'mediano'), (180, 9999, 'grande')]

def clasificar(m2):
    for lo, hi, cat in CATS_UNIV:
        if lo <= m2 < hi:
            return cat
    return 'mediano'

# Cargar factores del sa_categoricas.json 
# Intentar primero formato por_dorm, fallback a universal
def sa_factor(m2, macrozona_id, dorms=None):
    """Factor SA para un inmueble de m2 en macrozona."""
    if not macrozona_id:
        return 1.0
    mz_data = sa_cat_data.get('data', {}).get(macrozona_id, {})
    
    # Intentar formato por dormitorio
    dorm_key = str(dorms) if dorms else None
    if dorm_key and dorm_key in mz_data:
        factors = mz_data[dorm_key].get('factors', {})
    else:
        # Formato universal
        factors = mz_data.get('factors', {})
    
    if not factors:
        return 1.0
    cat = clasificar(m2)
    return factors.get(cat, 1.0)

# ============================================================
# BARRERAS: CALCULAR GAPS EMPIRICOS
# ============================================================
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def pct(data, p):
    s = sorted(data)
    idx = int(len(s) * p / 100)
    return s[min(idx, len(s)-1)] if s else None

# Pre-calcular gaps empiricos por barrera desde el cache
print("\nCalculando gaps empiricos de barreras...")
ventas_raw = [p for p in cache_scraping['propiedades']
              if p.get('operacion') == 'venta'
              and p.get('valor_m2', 0) > 200
              and p.get('valor_m2', 0) < 10000
              and p.get('lat') and p.get('lon')]

barreras_features = barreras_data.get('features', [])
BARRIER_GAPS = {}  # {nombre: gap_ratio}
RADIO_BARRERA = 300

for barrera in barreras_features:
    props_b = barrera.get('properties', {})
    nombre = props_b.get('name', '?')
    is_hard = props_b.get('is_hard', False)
    geom = barrera.get('geometry', {})
    coords = geom.get('coordinates', [])
    if not coords or len(coords) < 2:
        continue
    
    p1, p2 = coords[0], coords[-1]
    mid_lat = (p1[1] + p2[1]) / 2
    mid_lon = (p1[0] + p2[0]) / 2
    dlat = p2[1] - p1[1]
    dlon = p2[0] - p1[0]
    direction = 'NS' if abs(dlat) > abs(dlon) else 'EW'
    
    lado_A, lado_B = [], []
    for p in ventas_raw:
        try:
            plat, plon = float(p['lat']), float(p['lon'])
        except:
            continue
        dist = haversine_m(mid_lat, mid_lon, plat, plon)
        if dist > RADIO_BARRERA:
            continue
        vm2 = p.get('valor_m2', 0)
        if vm2 <= 0:
            continue
        if direction == 'NS':
            side = 'A' if plat > mid_lat else 'B'
        else:
            side = 'A' if plon > mid_lon else 'B'
        if side == 'A':
            lado_A.append(vm2)
        else:
            lado_B.append(vm2)
    
    if len(lado_A) >= 5 and len(lado_B) >= 5:
        p50_A = pct(lado_A, 50)
        p50_B = pct(lado_B, 50)
        if p50_A and p50_B and p50_A > 0 and p50_B > 0:
            gap = abs(p50_A - p50_B) / max(p50_A, p50_B)
            BARRIER_GAPS[nombre] = {'gap': gap, 'is_hard': is_hard, 'n_a': len(lado_A), 'n_b': len(lado_B)}

n_hard = sum(1 for v in BARRIER_GAPS.values() if v['is_hard'])
n_soft = sum(1 for v in BARRIER_GAPS.values() if not v['is_hard'])
gaps_soft = [v['gap'] for v in BARRIER_GAPS.values() if not v['is_hard']]
gaps_hard = [v['gap'] for v in BARRIER_GAPS.values() if v['is_hard']]
print(f"  Barreras con gap calculado: {n_hard} hard, {n_soft} soft")
if gaps_soft:
    print(f"  Gap medio SOFT: {sum(gaps_soft)/len(gaps_soft)*100:.1f}%  (min={min(gaps_soft)*100:.1f}% max={max(gaps_soft)*100:.1f}%)")
if gaps_hard:
    print(f"  Gap medio HARD: {sum(gaps_hard)/len(gaps_hard)*100:.1f}%  (min={min(gaps_hard)*100:.1f}% max={max(gaps_hard)*100:.1f}%)")

# ============================================================
# CRUCE DE BARRERAS
# ============================================================
def check_crossing(lon1, lat1, lon2, lat2):
    """Retorna (tipo, nombre, gap) para el primer cruce detectado."""
    for barrera in barreras_features:
        props_b = barrera.get('properties', {})
        nombre = props_b.get('name', '?')
        is_hard = props_b.get('barrier_type', 'soft') == 'hard'
        geom = barrera.get('geometry', {})
        coords = geom.get('coordinates', [])
        if not coords or len(coords) < 2:
            continue
        
        # Chequear interseccion con cada segmento de la barrera
        for i in range(len(coords) - 1):
            bx1, by1 = coords[i]
            bx2, by2 = coords[i+1]
            
            denom = (lat2 - lat1) * (bx2 - bx1) - (lon2 - lon1) * (by2 - by1)
            if abs(denom) < 1e-12:
                continue
            t = ((lon1 - bx1) * (by2 - by1) - (lat1 - by1) * (bx2 - bx1)) / denom
            u = -((lon2 - lon1) * (lat1 - by1) - (lat2 - lat1) * (lon1 - bx1)) / denom
            if 0 <= t <= 1 and 0 <= u <= 1:
                gap_info = BARRIER_GAPS.get(nombre, {})
                gap = gap_info.get('gap', 0.03 if not is_hard else 0.5)
                return ('hard' if is_hard else 'soft', nombre, gap)
    
    return (None, None, 0)

# ============================================================
# FUNCION DE PRECIO NORMALIZADO (NUEVO METODO)
# ============================================================
def precio_norm_v8(comp, m2_sujeto, dorms_sujeto, macrozona_id, lat_ref, lon_ref):
    """
    Normaliza el precio del comp al sujeto usando SA relativo.
    Retorna (precio_normalizado, tipo_cruce, gap_barrera)
    """
    precio_m2 = comp.get('precio_m2', comp.get('valor_m2', 0))
    ct = comp.get('_time_adjustment', comp.get('time_adjustment', 1.0))
    precio_raw = precio_m2 * ct
    
    m2_comp = comp.get('m2') or comp.get('m2_cubiertos', 0)
    dorms_comp = comp.get('dormitorios', dorms_sujeto)
    
    # SA relativo: escala el comp al tamanio del sujeto
    f_sujeto = sa_factor(m2_sujeto, macrozona_id, dorms_sujeto)
    f_comp = sa_factor(m2_comp, macrozona_id, dorms_comp)
    
    if f_comp > 0:
        ratio = f_sujeto / f_comp
        ratio = max(0.75, min(1.33, ratio))  # cap ±33%
    else:
        ratio = 1.0
    
    precio_ajustado = precio_raw * ratio
    
    # Cruce de barrera
    comp_lat = comp.get('lat')
    comp_lon = comp.get('lon')
    tipo_cruce, nombre_barrera, gap = None, None, 0
    if comp_lat and comp_lon:
        try:
            tipo_cruce, nombre_barrera, gap = check_crossing(
                lon_ref, lat_ref, float(comp_lon), float(comp_lat)
            )
        except:
            pass
    
    return precio_ajustado, tipo_cruce, nombre_barrera, gap

# ============================================================
# FUNCION DE VALUACION v8
# ============================================================
def valuar_v8(pool, m2_sujeto, dorms_sujeto, macrozona_id, lat_ref, lon_ref, cv_ref, zona_ref=None):
    """
    Aplica el metodo v8 sobre un pool de comparables.
    Retorna dict con vm2 y metadata.
    """
    precios_same = []
    precios_cross = []
    n_excluidos = 0
    barreras_cruzadas = []
    
    for comp in pool:
        precio_norm, tipo_cruce, nombre_barrera, gap = precio_norm_v8(
            comp, m2_sujeto, dorms_sujeto, macrozona_id, lat_ref, lon_ref
        )
        
        if not precio_norm or precio_norm <= 0:
            continue
        
        if tipo_cruce == 'hard':
            n_excluidos += 1
            continue
        elif tipo_cruce == 'soft':
            # Penalty dinamico = gap_empirico / 2
            penalty = gap / 2
            precio_ajustado = precio_norm / max(1 - penalty, 0.70)  # max penalty 30%
            precios_cross.append(precio_ajustado)
            if nombre_barrera:
                barreras_cruzadas.append(f"{nombre_barrera}({gap*100:.0f}%->{penalty*100:.0f}%)")
        else:
            precios_same.append(precio_norm)
    
    all_prices = sorted(precios_same + precios_cross)
    
    if not all_prices:
        return {'vm2': 0, 'n': 0, 'n_same': 0, 'n_cross': 0, 'n_excluidos': n_excluidos, 'pct': 'P33', 'cv': 1.0, 'barreras': []}
    
    # Percentil dinamico basado en CV y N
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
        'n_excluidos': n_excluidos,
        'pct': pct_label,
        'cv': round(cv, 4),
        'barreras': barreras_cruzadas,
    }

# ============================================================
# REFERENCIA: VALORES REALES DE MERCADO (targets del enunciado)
# Mabel: $60-65K, Cochabamba: $70-75K, Mitre: $210K, Francia: $600K
# ============================================================
TARGETS = {
    'Mabel': (60000, 65000),
    'Cochabamba 45': (70000, 75000),
    'Mitre1473': (200000, 220000),
    'Francia 250b': (580000, 620000),
}

def sa_none(m2, macrozona_id=None, ancla_id=None, dormitorios=None):
    return 1.0

# ============================================================
# LOOP PRINCIPAL
# ============================================================
results = []
f_out = io.StringIO()

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
    
    # --- ENGINE ACTUAL (S1) ---
    with redirect_stdout(f_out):
        vm2_s1, n_s1, meta_s1 = obtener_mediana_cluster_v2(
            zona=normalizar_zona(zona), dormitorios=dorms, operacion='venta',
            lat_ref=lat, lon_ref=lon, fecha_ref=datetime.now().strftime('%Y-%m-%d'),
            anio_sujeto=anio, tipo_inmueble=prop.get('tipo_inmueble') or 'departamento',
            cache_scraping=cache_scraping, retro_dias=uv.get('retro_dias', 0),
            flex_dormitorios=uv.get('flex_dormitorios'), m2_equiv=m2_equiv,
        )
    pool = meta_s1.get('_pool_final', [])
    value_s1 = round(vm2_s1 * m2_equiv) if vm2_s1 else 0
    
    # --- METODO v8 ---
    v8 = valuar_v8(pool, m2, dorms, macrozona_id, lat, lon, cv_ref, zona)
    value_v8 = round(v8['vm2'] * m2_equiv) if v8['vm2'] else 0
    
    # --- TARGET ---
    target_lo, target_hi = TARGETS.get(nombre, (0, 0))
    ok_s1 = target_lo <= value_s1 <= target_hi if target_lo else None
    ok_v8 = target_lo <= value_v8 <= target_hi if target_lo else None
    
    results.append({
        'nombre': nombre,
        'dorms': dorms, 'm2': m2, 'm2eq': m2_equiv,
        'macrozona': macrozona_id or '?',
        'cat': clasificar(m2),
        'value_s1': value_s1, 'value_v8': value_v8, 'stored': stored,
        'target': f"${target_lo:,}-${target_hi:,}" if target_lo else "--",
        'ok_s1': ok_s1, 'ok_v8': ok_v8,
        'n_same': v8['n_same'], 'n_cross': v8['n_cross'],
        'n_excluidos': v8['n_excluidos'],
        'pct': v8['pct'], 'cv': v8['cv'],
        'barreras': v8['barreras'],
    })

# ============================================================
# OUTPUT
# ============================================================
print("\n" + "=" * 100)
print("RESULTADOS")
print("=" * 100)

HDR = f"{'Propiedad':<16} {'dorm':>4} {'m2':>5} {'cat':<8} {'macrozona':<16} | {'ENGINE':>10} {'v8':>10} {'delta%':>7} | {'Target':>20} {'OK?':>5}"
print(HDR)
print("-" * 100)

for r in results:
    delta = (r['value_v8'] / r['value_s1'] - 1) * 100 if r['value_s1'] else 0
    ok_str = ""
    if r['ok_v8'] is True: ok_str = "OK-v8"
    elif r['ok_v8'] is False: ok_str = "XX-v8"
    if r['ok_s1'] is True: ok_str += " OK-s1"
    elif r['ok_s1'] is False: ok_str += " XX-s1"
    
    print(f"{r['nombre']:<16} {r['dorms']:>4} {r['m2']:>5.0f} {r['cat']:<8} {r['macrozona']:<16} | "
          f"${r['value_s1']:>9,} ${r['value_v8']:>9,} {delta:>+7.1f}% | "
          f"{r['target']:>20} {ok_str:>6}")

print("-" * 100)

# Totales
total_s1 = sum(r['value_s1'] for r in results)
total_v8 = sum(r['value_v8'] for r in results)
delta_total = (total_v8 / total_s1 - 1) * 100 if total_s1 else 0
print(f"{'TOTAL':<16} {'':<4} {'':<5} {'':<8} {'':<16} | "
      f"${total_s1:>9,} ${total_v8:>9,} {delta_total:>+7.1f}%")

# Detalle de barreras
print("\n\nDETALLE BARRERAS CRUZADAS EN v8:")
for r in results:
    if r['barreras']:
        print(f"  {r['nombre']}: {', '.join(r['barreras'][:5])}")
        print(f"    -> same={r['n_same']}, cross={r['n_cross']}, excluidos={r['n_excluidos']}, {r['pct']}, CV={r['cv']:.3f}")

# Analisis de targets
print("\n\nCOMPARACION vs TARGETS DE MERCADO:")
print(f"{'Prop':<16} {'Target':>20} {'ENGINE':>10} {'v8':>10} {'Mejor':>8}")
print("-" * 70)
for r in results:
    if not r['target'] or r['target'] == '--':
        continue
    wins = ""
    if r['ok_v8'] and not r['ok_s1']: wins = "v8"
    elif r['ok_s1'] and not r['ok_v8']: wins = "engine"
    elif r['ok_v8'] and r['ok_s1']: wins = "ambos"
    else: wins = "ninguno"
    print(f"{r['nombre']:<16} {r['target']:>20} ${r['value_s1']:>9,} ${r['value_v8']:>9,} {wins:>8}")

print("\n")
print("LEYENDA:")
print("  ENGINE = Motor actual (SA old + alpha/blend/3% penalty)")
print("  v8     = SA relativo (sujeto/comp) + penalty dinamico (gap_empirico/2)")
print()
