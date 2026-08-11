"""
SIMULACION v8d - PENALTY DIRECCIONAL VECTORIAL (Cross-product Side Detection)
==============================================================================
Detecta el lado de la barrera (LEFT vs RIGHT) usando el producto cruz vectorial
con respecto al segmento mas cercano de la barrera.

Para cada barrera:
  1. Calcula median(LEFT) vs median(RIGHT) con ventas a < 300m.
  2. Determina cheaper_side ('LEFT' o 'RIGHT') y gap = |L-R| / max(L,R).
  3. Para comps cross:
     - Si sujeto en cheaper_side y comp en expensive_side:
       precio_comp_ajustado = precio_norm * (1 - gap / 2)  <- baja comp caro
     - Si sujeto en expensive_side y comp en cheaper_side:
       precio_comp_ajustado = precio_norm / (1 - gap / 2)  <- sube comp barato

Totalmente automatico y geometricamente exacto.
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
print("SIMULACION v8d: Penalty Direccional Vectorial (Cross-Product Exacto)")
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 90)

# ============================================================
# GEOMETRIA: DISTANCIA Y PRODUCTO CRUZ
# ============================================================
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def dist_punto_segmento_m(px, py, x1, y1, x2, y2):
    """Retorna distancia aproximada en metros de (px, py) al segmento (x1,y1)-(x2,y2)."""
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    return haversine_m(py, px, my, mx)

def get_closest_segment_side(px, py, coords):
    """
    Dada la lista de coordenadas de una barrera (lon, lat),
    retorna ('LEFT' o 'RIGHT', min_dist_m) para el punto (px=lon, py=lat).
    """
    min_d = 1e9
    best_cp = 0
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i+1]
        d = dist_punto_segmento_m(px, py, x1, y1, x2, y2)
        if d < min_d:
            min_d = d
            best_cp = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
    
    side = 'LEFT' if best_cp >= 0 else 'RIGHT'
    return side, min_d

def pct(l, p):
    if not l: return 0
    s = sorted(l)
    return s[int(len(s)*p/100)]

# ============================================================
# MEDIR LADO CARO / CHEAP Y GAP PARA CADA BARRERA EN EL CACHE
# ============================================================
ventas_raw = [p for p in cache_scraping['propiedades']
              if p.get('operacion') == 'venta'
              and 200 < p.get('valor_m2', 0) < 10000
              and p.get('lat') and p.get('lon')]

print(f"\nCalculando lados caro/barato para barreras desde {len(ventas_raw)} ventas...")

BARRIER_VECTOR_INFO = {} # nombre -> {gap, is_hard, cheaper_side, p50_left, p50_right, coords}
RADIO_BARRERA = 300

barreras_features = barreras_data.get('features', [])
for barrera in barreras_features:
    props_b = barrera.get('properties', {})
    nombre = props_b.get('name', '?')
    is_hard = props_b.get('barrier_type', 'soft') == 'hard'
    geom = barrera.get('geometry', {})
    coords = geom.get('coordinates', [])
    if not coords or len(coords) < 2:
        continue
    
    lado_left, lado_right = [], []
    for p in ventas_raw:
        try:
            plat, plon = float(p['lat']), float(p['lon'])
        except:
            continue
        vm2 = p.get('valor_m2', 0)
        if vm2 <= 0:
            continue
        
        side, dist_m = get_closest_segment_side(plon, plat, coords)
        if dist_m <= RADIO_BARRERA:
            (lado_left if side == 'LEFT' else lado_right).append(vm2)
            
    if len(lado_left) >= 5 and len(lado_right) >= 5:
        p50_L = pct(lado_left, 50)
        p50_R = pct(lado_right, 50)
        if p50_L > 0 and p50_R > 0:
            gap = abs(p50_L - p50_R) / max(p50_L, p50_R)
            cheaper_side = 'LEFT' if p50_L < p50_R else 'RIGHT'
            BARRIER_VECTOR_INFO[nombre] = {
                'gap': gap,
                'is_hard': is_hard,
                'cheaper_side': cheaper_side,
                'p50_L': p50_L, 'p50_R': p50_R,
                'n_L': len(lado_left), 'n_R': len(lado_right),
                'coords': coords
            }

GAP_FALLBACK = 0.143

print(f"\nBarreras vectoriales medidas: {len(BARRIER_VECTOR_INFO)}")
print(f"{'Barrera':<40} {'Tipo':<5} {'gap':>6} {'LEFT (p50)':>13} {'RIGHT (p50)':>13} {'lado mas barato':>15}")
print("-" * 100)
for nombre, info in sorted(BARRIER_VECTOR_INFO.items(), key=lambda x: -x[1]['gap']):
    tipo = "HARD" if info['is_hard'] else "soft"
    print(f"{nombre:<40} {tipo:<5} {info['gap']*100:>5.1f}%  "
          f"${info['p50_L']:>5,.0f} (n={info['n_L']:>3})  "
          f"${info['p50_R']:>5,.0f} (n={info['n_R']:>3})  lado {info['cheaper_side']}")

# ============================================================
# DETECCION DE BARRERA INTERSECTADA
# ============================================================
def detectar_barrera_vector(lon_suj, lat_suj, lon_comp, lat_comp):
    for barrera in barreras_features:
        props_b = barrera.get('properties', {})
        nombre = props_b.get('name', '?')
        geom = barrera.get('geometry', {})
        coords = geom.get('coordinates', [])
        if not coords or len(coords) < 2:
            continue
        
        for i in range(len(coords) - 1):
            bx1, by1 = coords[i]
            bx2, by2 = coords[i+1]
            denom = (lat_comp - lat_suj) * (bx2 - bx1) - (lon_comp - lon_suj) * (by2 - by1)
            if abs(denom) < 1e-12:
                continue
            t = ((lon_suj - bx1) * (by2 - by1) - (lat_suj - by1) * (bx2 - bx1)) / denom
            u = -((lon_comp - lon_suj) * (lat_suj - by1) - (lat_comp - lat_suj) * (lon_suj - bx1)) / denom
            if 0 <= t <= 1 and 0 <= u <= 1:
                return nombre, BARRIER_VECTOR_INFO.get(nombre, {}), coords
                
    return None, {}, []

# ============================================================
# SA CATEGORICO
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
    factors = {}
    if dorms:
        dorm_data = mz_data.get(str(dorms), {})
        factors = dorm_data.get('factors', {})
    if not factors:
        factors = mz_data.get('factors', {})
    if not factors:
        return 1.0
    return factors.get(clasificar(m2), 1.0)

def precio_norm_sa(comp, m2_sujeto, dorms_sujeto, macrozona_id):
    precio_m2 = comp.get('precio_m2', comp.get('valor_m2', 0))
    ct = comp.get('_time_adjustment', comp.get('time_adjustment', 1.0))
    raw = precio_m2 * ct
    if not raw or raw <= 0:
        return None
    m2_comp = comp.get('m2') or comp.get('m2_cubiertos', 0) or 0
    dorms_comp = comp.get('dormitorios', dorms_sujeto)
    f_suj = sa_factor(m2_sujeto, macrozona_id, dorms_sujeto)
    f_comp = sa_factor(m2_comp, macrozona_id, dorms_comp)
    if f_comp > 0 and f_suj != f_comp:
        ratio = max(0.75, min(1.33, f_suj / f_comp))
    else:
        ratio = 1.0
    return raw * ratio

# ============================================================
# PENALTY DIRECCIONAL VECTORIAL
# ============================================================
def calcular_factor_penalty_vector(lat_suj, lon_suj, lat_comp, lon_comp, b_info, coords):
    if not b_info or not coords:
        return 1 - GAP_FALLBACK / 2
        
    side_suj, _ = get_closest_segment_side(lon_suj, lat_suj, coords)
    side_comp, _ = get_closest_segment_side(lon_comp, lat_comp, coords)
    
    if side_suj == side_comp:
        return 1.0
        
    cheaper_side = b_info['cheaper_side']
    gap = b_info['gap']
    penalty = gap / 2
    
    if side_suj == cheaper_side and side_comp != cheaper_side:
        # Sujeto en lado BARATO, comp en lado CARO -> BAJAR comp
        factor = 1 - penalty
    elif side_suj != cheaper_side and side_comp == cheaper_side:
        # Sujeto en lado CARO, comp en lado BARATO -> SUBIR comp
        factor = 1 / max(1 - penalty, 0.70)
    else:
        factor = 1.0
        
    return max(0.70, min(1.43, factor))

# ============================================================
# VALUACION v8d
# ============================================================
def valuar_v8d(pool, m2_sujeto, dorms_sujeto, macrozona_id, lat_suj, lon_suj, cv_ref):
    precios_same = []
    precios_cross = []
    detalle_barreras = []

    for comp in pool:
        precio_norm = precio_norm_sa(comp, m2_sujeto, dorms_sujeto, macrozona_id)
        if precio_norm is None:
            continue

        is_cross = comp.get('_cross_soft', False)

        if not is_cross:
            precios_same.append(precio_norm)
            continue

        lat_comp = comp.get('lat')
        lon_comp = comp.get('lon')
        factor = 1 - GAP_FALLBACK / 2

        if lat_comp and lon_comp and lat_suj and lon_suj:
            try:
                b_nombre, b_info, coords = detectar_barrera_vector(
                    float(lon_suj), float(lat_suj),
                    float(lon_comp), float(lat_comp)
                )
                factor = calcular_factor_penalty_vector(
                    float(lat_suj), float(lon_suj),
                    float(lat_comp), float(lon_comp),
                    b_info, coords
                )
                if b_nombre:
                    adj_pct = (factor - 1) * 100
                    detalle_barreras.append(f"{b_nombre[:20]}({adj_pct:+.1f}%)")
            except Exception as e:
                pass

        precios_cross.append(precio_norm * factor)

    all_prices = sorted(precios_same + precios_cross)
    if not all_prices:
        return {'vm2': 0, 'n': 0, 'n_same': 0, 'n_cross': 0, 'pct': 'P33', 'cv': 1.0, 'barreras': []}

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
        'barreras': list(set(detalle_barreras)),
    }

# ============================================================
# LOOP PRINCIPAL: 9 PROPIEDADES
# ============================================================
print("\n" + "=" * 90)
print("CORRIENDO 9 PROPIEDADES EN SIMULACION v8d...")
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

    # ENGINE ACTUAL
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

    # METODO v8d
    v8d = valuar_v8d(pool, m2, dorms, macrozona_id, lat, lon, cv_ref)
    value_v8d = round(v8d['vm2'] * m2_equiv) if v8d['vm2'] else 0

    sa_suj = sa_factor(m2, macrozona_id, dorms)
    cat_suj = clasificar(m2)

    results.append({
        'nombre': nombre, 'dorms': dorms, 'm2': m2, 'm2eq': m2_equiv,
        'macrozona': macrozona_id or '?', 'cat': cat_suj, 'sa_suj': sa_suj,
        'value_s1': value_s1, 'value_v8d': value_v8d, 'stored': stored,
        'n_pool': len(pool), 'n_same': v8d['n_same'], 'n_cross': v8d['n_cross'],
        'pct': v8d['pct'], 'cv': v8d['cv'],
        'barreras': v8d['barreras'],
    })

# ============================================================
# TABLA PRINCIPAL
# ============================================================
print("\n" + "=" * 110)
print(f"{'Prop':<16} {'d':>2} {'m2':>4} {'cat':>7} {'sa_suj':>7} {'zona':<16} | {'ENGINE':>10} {'v8d':>10} {'delta%':>7} | {'N':>3} {'s':>3} {'x':>3} {'pct':>4} | barreras ajustadas")
print("-" * 110)

for r in results:
    delta = (r['value_v8d'] / r['value_s1'] - 1) * 100 if r['value_s1'] else 0
    barr_str = ', '.join(r['barreras'][:2]) if r['barreras'] else '-'
    print(f"{r['nombre']:<16} {r['dorms']:>2} {r['m2']:>4.0f} {r['cat']:>7} {r['sa_suj']:>7.3f} {r['macrozona']:<16} | "
          f"${r['value_s1']:>9,} ${r['value_v8d']:>9,} {delta:>+7.1f}% | "
          f"{r['n_pool']:>3} {r['n_same']:>3} {r['n_cross']:>3} {r['pct']:>4} | {barr_str}")

print("-" * 110)
t_s1 = sum(r['value_s1'] for r in results)
t_v8d = sum(r['value_v8d'] for r in results)
delta_t = (t_v8d / t_s1 - 1) * 100 if t_s1 else 0
print(f"{'TOTAL':<16} {'':>2} {'':>4} {'':>7} {'':>7} {'':>16} | ${t_s1:>9,} ${t_v8d:>9,} {delta_t:>+7.1f}%")

print("\n\nDETALLE DE COCHABAMBA 45 (Prueba de Fuego de Penalty Direccional):")
for r in results:
    if 'Cochabamba' in r['nombre']:
        vm2_e = r['value_s1'] / r['m2eq']
        vm2_v = r['value_v8d'] / r['m2eq']
        print(f"  ENGINE: ${r['value_s1']:,} (${vm2_e:,.0f}/m2)")
        print(f"  v8d:    ${r['value_v8d']:,} (${vm2_v:,.0f}/m2)")
        print(f"  Pool cross_soft comps: {r['n_cross']} comps")
        print(f"  Ajustes de barreras aplicados: {r['barreras']}")
