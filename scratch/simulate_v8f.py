"""
SIMULACION v8f - AJUSTE DE CATEGORIAS POR DORMITORIO + FLEX DORM FACTOR EMPIRICO
==================================================================================
Calibracion basada 100% en datos del cache (16.427 ventas reales de Rosario):

1. Umbrales de tamano por dormitorio:
   - 1-dorm: chico <45m2, mediano 45-75m2, grande >=75m2
   - 2-dorm: chico <75m2, mediano 75-130m2, grande >=130m2
   - 3-dorm: chico <115m2, mediano 115-220m2, grande >=220m2
   - 4-dorm: chico <140m2, mediano 140-250m2, grande >=250m2

2. Factor de ajuste dorm-flex EMPIRICO:
   - Cargado desde data/flex_dorm_factors.json (generado por analisis ML)
   - Especifico por macrozona: ej. macrocentro 4d/2d = 0.986, centro_premium 4d/2d = 0.718
   - Fallback global si la macrozona no tiene datos suficientes
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

props_data = json.load(open('propiedades.json', 'r', encoding='utf-8'))
with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache_scraping = json.load(f)
with open('barreras_rosario.json', 'r', encoding='utf-8') as f:
    barreras_data = json.load(f)
with open('data/sa_categoricas.json', 'r', encoding='utf-8') as f:
    sa_cat_data = json.load(f)
with open('data/flex_dorm_factors.json', 'r', encoding='utf-8') as f:
    flex_dorm_data = json.load(f)['data']

# ============================================================
# PERCENTILES DE m2 POR DORMITORIO (para filtro flex pool)
# Derivado del cache: solo se calcula una vez al inicio
# ============================================================
_m2_by_dorm = {d: [] for d in [1, 2, 3, 4]}
for _p in cache_scraping.get('propiedades', []):
    _d = _p.get('dormitorios')
    _m2 = _p.get('m2', 0)
    if _d in [1, 2, 3, 4] and 20 < _m2 < 400 and _p.get('operacion') == 'venta':
        _m2_by_dorm[_d].append(_m2)
for _d in _m2_by_dorm:
    _m2_by_dorm[_d].sort()

def m2_percentile(m2, dorms):
    """Retorna el percentil (0-100) de un m2 dentro de la distribucion de su tipologia."""
    d = min(max(int(dorms or 1), 1), 4)
    dist = _m2_by_dorm.get(d, [])
    if not dist or not m2: return 50.0
    # Biseccion para encontrar posicion
    lo, hi = 0, len(dist)
    while lo < hi:
        mid = (lo + hi) // 2
        if dist[mid] < m2: lo = mid + 1
        else: hi = mid
    return lo / len(dist) * 100

print("=" * 90)
print("SIMULACION v8f: Calibracion Umbrales por Dorm + Flex-Dorm Ratio")
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 90)
with open('data/sa_categoricas.json', 'r', encoding='utf-8') as f:
    sa_cat_data = json.load(f)
with open('data/flex_dorm_factors.json', 'r', encoding='utf-8') as f:
    flex_dorm_data = json.load(f)['data']
with open('data/sa_continuous.json', 'r', encoding='utf-8') as f:
    sa_cont_data = json.load(f)

USE_CONTINUOUS_SA = True

def get_beta_continuous(macrozona_id, dorms=1):
    mz = sa_cont_data.get('macrozonas', {}).get(macrozona_id or '_global', {})
    d_str = str(min(max(dorms or 1, 1), 4))
    beta = mz.get(d_str, mz.get('all', -0.18))
    if beta is None or beta >= 0:
        beta = mz.get('all', -0.18)
    if beta is None or beta >= 0:
        beta = sa_cont_data.get('beta_global_all', -0.18)
    return max(-0.35, min(-0.05, beta))

SA_CONTINUOUS_BOUNDS_2SIGMA = {
    "centro_premium": (0.780, 1.250),
    "macrocentro": (0.727, 1.375),
    "puerto_norte": (0.807, 1.238),
    "norte": (0.781, 1.281),
    "oeste": (0.746, 1.340),
    "fisherton": (0.793, 1.261),
    "sur_default": (0.848, 1.179),
    "_global": (0.775, 1.290),
}

def sa_factor_continuous(m2_sujeto, m2_comp, macrozona_id, dorms=1):
    if not m2_sujeto or not m2_comp or m2_comp <= 0 or m2_sujeto <= 0:
        return 1.0
    beta = get_beta_continuous(macrozona_id, dorms)
    ratio = (m2_sujeto / m2_comp) ** beta
    bounds = SA_CONTINUOUS_BOUNDS_2SIGMA.get(macrozona_id, SA_CONTINUOUS_BOUNDS_2SIGMA['_global'])
    return max(bounds[0], min(bounds[1], ratio))


# ============================================================
# UMBRALES ESPECIFICOS POR DORMITORIO
# ============================================================
CATEGORIAS_POR_DORM = {
    1: [(0, 45, 'chico'), (45, 75, 'mediano'), (75, 9999, 'grande')],
    2: [(0, 75, 'chico'), (75, 130, 'mediano'), (130, 9999, 'grande')],
    3: [(0, 115, 'chico'), (115, 220, 'mediano'), (220, 9999, 'grande')],
    4: [(0, 140, 'chico'), (140, 250, 'mediano'), (250, 9999, 'grande')],
}

def clasificar_por_dorm(m2, dorms=1):
    d = min(max(dorms or 1, 1), 4)
    cats = CATEGORIAS_POR_DORM.get(d, CATEGORIAS_POR_DORM[1])
    for lo, hi, cat in cats:
        if lo <= m2 < hi: return cat
    return 'mediano'

def sa_factor_v8f(m2, macrozona_id, dorms=1):
    if not macrozona_id: return 1.0
    mz_data = sa_cat_data.get('data', {}).get(macrozona_id, {})
    factors = mz_data.get(str(dorms), {}).get('factors', {}) if dorms else {}
    if not factors:
        factors = mz_data.get('factors', {})
    if not factors: return 1.0
    cat = clasificar_por_dorm(m2, dorms)
    return factors.get(cat, 1.0)

# Factor de ajuste por diferencia de dormitorios (dorms sujeto vs comp)
# EMPIRICO: usa ratios medidos en el cache por macrozona desde flex_dorm_factors.json
def _obtener_flex_fallback_dinamico():
    mz_dict = flex_dorm_data.get('data', flex_dorm_data)
    tot = 0
    w = {'1': 0.0, '2': 0.0, '3': 0.0, '4': 0.0}
    for mz, data in mz_dict.items():
        if mz == '_global' or not isinstance(data, dict): continue
        n = data.get('n', data.get('n_props', 100))
        ratios = data.get('ratios_vs_2d', {})
        if not ratios: continue
        tot += n
        for d in ['1', '2', '3', '4']:
            w[d] += ratios.get(d, 1.0) * n
    if tot > 0:
        return {d: round(w[d] / tot, 4) for d in ['1', '2', '3', '4']}
    return {'1': 1.0845, '2': 1.0, '3': 0.9831, '4': 0.8178}

def factor_dorm_flex(dorms_sujeto, dorms_comp, macrozona_id=None):
    if not dorms_sujeto or not dorms_comp or dorms_sujeto == dorms_comp:
        return 1.0
    mz_dict = flex_dorm_data.get('data', flex_dorm_data)
    mz_data = mz_dict.get(macrozona_id or '', {})
    if not mz_data:
        mz_data = mz_dict.get('_global', {})
    ratios = mz_data.get('ratios_vs_2d', {})
    if not ratios:
        # Fallback global empirico dinamico (promedio ponderado por muestras)
        ratios = _obtener_flex_fallback_dinamico()

    r_suj = ratios.get(str(dorms_sujeto), 1.0)
    r_comp = ratios.get(str(dorms_comp), 1.0)
    if not r_suj or not r_comp or r_comp == 0:
        return 1.0
    # factor = ratio_sujeto / ratio_comp
    # Si sujeto=4d(ratio=0.986) y comp=1d(ratio=1.451): factor = 0.986/1.451 = 0.679
    # -> comp 1d sobreestima el valor -> bajar al nivel del 4d del mercado local
    factor = r_suj / r_comp
    return max(0.50, min(2.00, factor))

# ============================================================
# BARRERAS Y GEOMETRIA
# ============================================================
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def dist_punto_segmento_m(px, py, x1, y1, x2, y2):
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    return haversine_m(py, px, my, mx)

def get_closest_segment_side(px, py, coords):
    min_d = 1e9
    best_cp = 0
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i+1]
        d = dist_punto_segmento_m(px, py, x1, y1, x2, y2)
        if d < min_d:
            min_d = d
            best_cp = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
    return ('LEFT' if best_cp >= 0 else 'RIGHT'), min_d

def pct(l, p):
    if not l: return 0
    s = sorted(l)
    return s[int(len(s)*p/100)]

ventas_raw = [p for p in cache_scraping['propiedades']
              if p.get('operacion') == 'venta'
              and 200 < p.get('valor_m2', 0) < 10000
              and p.get('lat') and p.get('lon')]

BARRIER_VECTOR_INFO = {}
RADIO_BARRERA = 300

barreras_features = barreras_data.get('features', [])
for barrera in barreras_features:
    props_b = barrera.get('properties', {})
    nombre = props_b.get('name', '?')
    is_hard = props_b.get('barrier_type', 'soft') == 'hard'
    geom = barrera.get('geometry', {})
    coords = geom.get('coordinates', [])
    if not coords or len(coords) < 2: continue
    
    lado_left, lado_right = [], []
    for p in ventas_raw:
        try:
            plat, plon = float(p['lat']), float(p['lon'])
        except: continue
        vm2 = p.get('valor_m2', 0)
        if vm2 <= 0: continue
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
                'gap': gap, 'is_hard': is_hard,
                'cheaper_side': cheaper_side,
                'coords': coords
            }

MACROZONE_BARRIER_GAP_FALLBACKS = {
    'centro_premium': 0.1588,
    'macrocentro': 0.2014,
    'puerto_norte': 0.0567,
    'norte': 0.3741,
    'oeste': 0.1469,
    'sur_default': 0.0725,
    '_global': 0.1692,
}


def detectar_barrera_vector(lon_suj, lat_suj, lon_comp, lat_comp):
    for barrera in barreras_features:
        props_b = barrera.get('properties', {})
        nombre = props_b.get('name', '?')
        geom = barrera.get('geometry', {})
        coords = geom.get('coordinates', [])
        if not coords or len(coords) < 2: continue
        
        for i in range(len(coords) - 1):
            bx1, by1 = coords[i]
            bx2, by2 = coords[i+1]
            denom = (lat_comp - lat_suj) * (bx2 - bx1) - (lon_comp - lon_suj) * (by2 - by1)
            if abs(denom) < 1e-12: continue
            t = ((lon_suj - bx1) * (by2 - by1) - (lat_suj - by1) * (bx2 - bx1)) / denom
            u = -((lon_comp - lon_suj) * (lat_suj - by1) - (lat_comp - lat_suj) * (lon_suj - bx1)) / denom
            if 0 <= t <= 1 and 0 <= u <= 1:
                return nombre, BARRIER_VECTOR_INFO.get(nombre, {}), coords
    return None, {}, []

def precio_norm_sa_v8f(comp, m2_sujeto, dorms_sujeto, macrozona_id):
    precio_m2 = comp.get('precio_m2', comp.get('valor_m2', 0))
    ct = comp.get('_time_adjustment', comp.get('time_adjustment', 1.0))
    raw = precio_m2 * ct
    if not raw or raw <= 0: return None
    m2_comp = comp.get('m2') or comp.get('m2_cubiertos', 0) or 0
    dorms_comp = comp.get('dormitorios', dorms_sujeto)

    if USE_CONTINUOUS_SA:
        ratio_sa = sa_factor_continuous(m2_sujeto, m2_comp, macrozona_id, dorms_sujeto)
    else:
        f_suj = sa_factor_v8f(m2_sujeto, macrozona_id, dorms_sujeto)
        f_comp = sa_factor_v8f(m2_comp, macrozona_id, dorms_comp)
        ratio_sa = (f_suj / f_comp) if f_comp > 0 and f_suj != f_comp else 1.0
        ratio_sa = max(0.75, min(1.33, ratio_sa))

    # Flex dorm ratio EMPIRICO (por macrozona)
    # Aplica a TODOS los comps de distinto tipo (factor_dorm_flex retorna 1.0 si mismo tipo)
    f_dorm = factor_dorm_flex(dorms_sujeto, dorms_comp, macrozona_id)

    return raw * ratio_sa * f_dorm

def calcular_factor_penalty_vector(lat_suj, lon_suj, lat_comp, lon_comp, b_info, coords, macrozona_id=None):

    gap_fallback = MACROZONE_BARRIER_GAP_FALLBACKS.get(macrozona_id, MACROZONE_BARRIER_GAP_FALLBACKS['_global'])
    if not b_info or not coords: return 1 - gap_fallback / 2
    side_suj, _ = get_closest_segment_side(lon_suj, lat_suj, coords)
    side_comp, _ = get_closest_segment_side(lon_comp, lat_comp, coords)
    if side_suj == side_comp: return 1.0
    cheaper_side = b_info.get('cheaper_side')
    gap = b_info.get('gap', gap_fallback)
    penalty = gap / 2
    if side_suj == cheaper_side and side_comp != cheaper_side:
        factor = 1 - penalty
    elif side_suj != cheaper_side and side_comp == cheaper_side:
        factor = 1 / max(1 - penalty, 0.70)
    else:
        factor = 1.0
    return max(0.70, min(1.43, factor))


def valuar_v8f(pool, m2_sujeto, dorms_sujeto, macrozona_id, lat_suj, lon_suj, cv_ref):
    precios_same = []
    precios_cross = []

    # ---- PASO 1: Filtro de percentil m2 para comps flex (cross-dorm) ----
    # Tolerancia empirica de percentil m2 basada en la densidad de comparables flex disponibles:
    # Si hay muchos comps (pool denso), estrecha el margen (ej 20-25 percentiles).
    # Si hay pocos comps (pool disperso), abre el margen (ej 35-40 percentiles).
    n_cross_total = sum(1 for c in pool if c.get('_cross_soft', False))
    m2_pct_tol_dynamic = max(18, min(40, int(30 * (25 / max(1, n_cross_total))**0.25)))

    pct_sujeto = m2_percentile(m2_sujeto, dorms_sujeto)
    pool_m2 = []
    for comp in pool:
        if comp.get('_cross_soft', False):
            comp_m2 = comp.get('m2', 0) or 0
            comp_dorms = comp.get('dormitorios', dorms_sujeto)
            pct_comp = m2_percentile(comp_m2, comp_dorms)
            if abs(pct_comp - pct_sujeto) <= m2_pct_tol_dynamic:
                pool_m2.append(comp)
        else:
            pool_m2.append(comp)  # comps same-dorm: siempre pasan


    # ---- PASO 2: Filtro de banda de precio (submercado lujo vs estándar) ----
    # Solo activo cuando hay >= 10 comps flex (pool suficiente para anclar)
    # Usa la mediana $/m2 del pool filtrado como ancla del submercado local
    # Luego descarta comps flex que se alejen más del 60% de esa ancla
    PRICE_BAND_MIN_FLEX = 10   # activar solo con pool flex suficiente

    flex_comps  = [c for c in pool_m2 if c.get('_cross_soft', False)]
    same_comps  = [c for c in pool_m2 if not c.get('_cross_soft', False)]

    if len(flex_comps) >= PRICE_BAND_MIN_FLEX:
        # Ancla: mediana del vm2 del pool flex (aplicando factor dorm para normalizarlo)
        vm2_flex = []
        for c in flex_comps:
            raw = c.get('precio_m2', c.get('valor_m2', 0))
            ct  = c.get('_time_adjustment', c.get('time_adjustment', 1.0))
            d_c = c.get('dormitorios', dorms_sujeto)
            f   = factor_dorm_flex(dorms_sujeto, d_c, macrozona_id)
            if raw and ct and f:
                vm2_flex.append(raw * ct * f)
        if vm2_flex:
            vm2_flex.sort()
            ancla = vm2_flex[len(vm2_flex) // 2]
            # Banda de submercado dinamica basada en el Coeficiente de Variacion (CV) local:
            # dynamic_ratio = 2.0 * CV (acota submercados homogeneos y abre submercados dispares)
            cv_flex = _calcular_cv(vm2_flex) if len(vm2_flex) >= 3 else 0.30
            dynamic_price_band_ratio = max(0.35, min(0.75, 2.0 * cv_flex))
            
            lo_band = ancla * (1 - dynamic_price_band_ratio)
            hi_band = ancla * (1 + dynamic_price_band_ratio)
            flex_filtrado = [c for c in flex_comps
                             if lo_band <= (c.get('precio_m2', c.get('valor_m2', 0)) *
                                            c.get('_time_adjustment', c.get('time_adjustment', 1.0))) <= hi_band]
            # Fallback: si el filtro deja muy pocos, usar el pool sin filtrar precio
            pool = same_comps + (flex_filtrado if len(flex_filtrado) >= 5 else flex_comps)
        else:
            pool = pool_m2
    else:
        pool = pool_m2

    for comp in pool:
        precio_norm = precio_norm_sa_v8f(comp, m2_sujeto, dorms_sujeto, macrozona_id)
        if precio_norm is None: continue

        dorms_comp_real = comp.get('dormitorios', dorms_sujeto)
        is_cross_soft   = comp.get('_cross_soft', False)

        # Clasificacion por TIPO REAL de dormitorio (no por _cross_soft)
        # - Mismo tipo → precios_same (peso pleno en el blend)
        # - Distinto tipo → precios_cross (menor peso), independientemente del _cross_soft
        # El flag _cross_soft solo controla si se aplica penalidad de barrera
        if dorms_comp_real == dorms_sujeto:
            precios_same.append(precio_norm)
            continue

        # Comp de distinto tipo: aplicar penalidad de barrera si es _cross_soft
        lat_comp, lon_comp = comp.get('lat'), comp.get('lon')
        factor = 1.0  # sin penalidad por defecto para comps regulares
        if is_cross_soft and lat_comp and lon_comp and lat_suj and lon_suj:
            try:
                b_nombre, b_info, coords = detectar_barrera_vector(
                    float(lon_suj), float(lat_suj),
                    float(lon_comp), float(lat_comp)
                )
                factor = calcular_factor_penalty_vector(
                    float(lat_suj), float(lon_suj),
                    float(lat_comp), float(lon_comp),
                    b_info, coords, macrozona_id=macrozona_id
                )
            except: pass

        precios_cross.append(precio_norm * factor)

    n_same = len(precios_same)
    n_cross = len(precios_cross)
    n_total = n_same + n_cross

    if n_total == 0:
        return {'vm2': 0, 'n_same': 0, 'n_cross': 0, 'pct': 'P33', 'cv': 1.0}

    all_prices = sorted(precios_same + precios_cross)
    cv = _calcular_cv(all_prices) if n_total >= 3 else 1.0
    _, pct_label = seleccionar_percentil_por_calidad_pool(n_total, cv, cv_ref=cv_ref)
    pct_num = int(pct_label[1:])

    if n_same >= 3 and n_cross > 0:
        mean_s = sum(precios_same) / len(precios_same)
        mean_c = sum(precios_cross) / len(precios_cross)
        var_s = sum((x - mean_s) ** 2 for x in precios_same) / max(1, len(precios_same) - 1)
        var_c = sum((x - mean_c) ** 2 for x in precios_cross) / max(1, len(precios_cross) - 1)
        
        # Ponderacion por Varianza Inversa Empirica:
        # w_same = n_same / (var_same + eps), w_cross = n_cross / (var_cross + eps)
        # Si un pool tiene menor dispersion de precios, recibe mayor peso estadistico.
        eps = (mean_s ** 2) * 1e-4  # escala relativa a la magnitud de los precios
        w_same = n_same / (var_s + eps)
        w_cross = n_cross / (var_c + eps)
        
        alpha = w_same / (w_same + w_cross)
        
        vm2_same = calcular_percentil(sorted(precios_same), pct_num)
        vm2_cross = calcular_percentil(sorted(precios_cross), pct_num)
        vm2 = alpha * vm2_same + (1 - alpha) * vm2_cross
    else:
        vm2 = calcular_percentil(all_prices, pct_num)


    return {
        'vm2': round(vm2, 2),
        'n_same': n_same,
        'n_cross': n_cross,
        'pct': pct_label,
        'cv': round(cv, 4),
    }

TARGETS = {
    'Mabel':          (60000, 65000),
    'Cochabamba 45':  (70000, 75000),
    'Mitre1473':      (200000, 220000),
    'Francia 250b':   (580000, 620000),
}

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
    if not lat or not lon or not dorms: continue


    macrozona_id = None
    try:
        _mz = resolver_macrozona({'zona': normalizar_zona(zona) or '', 'lat': lat, 'lon': lon})
        macrozona_id = _mz.get('macrozona_id')
    except: pass

    cv_ref = obtener_cv_ref(macrozona_id)

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

    v8f = valuar_v8f(pool, m2_equiv, dorms, macrozona_id, lat, lon, cv_ref)
    value_v8f = round(v8f['vm2'] * m2_equiv) if v8f['vm2'] else 0


    results.append({
        'nombre': nombre, 'dorms': dorms, 'm2': m2, 'm2eq': m2_equiv,
        'macrozona': macrozona_id or '?', 'cat': clasificar_por_dorm(m2, dorms),
        'value_s1': value_s1, 'value_v8f': value_v8f, 'stored': stored,
        'n_same': v8f['n_same'], 'n_cross': v8f['n_cross'],
        'pct': v8f['pct'], 'cv': v8f['cv'],
    })

print("\n" + "=" * 105)
print(f"{'Propiedad':<16} {'d':>2} {'m2':>4} {'cat':>8} {'macrozona':<16} | {'ENGINE':>10} {'v8f (CALIB)':>11} {'delta%':>7} | {'Target':>20} {'OK?':>6}")
print("-" * 105)

for r in results:
    delta = (r['value_v8f'] / r['value_s1'] - 1) * 100 if r['value_s1'] else 0
    t_lo, t_hi = TARGETS.get(r['nombre'], (0, 0))
    t_str = f"${t_lo:,}-${t_hi:,}" if t_lo else "-"
    
    ok_str = ""
    if t_lo:
        ok_v8f = t_lo <= r['value_v8f'] <= t_hi
        ok_s1 = t_lo <= r['value_s1'] <= t_hi
        ok_str = "OK-v8f" if ok_v8f else ("OK-s1" if ok_s1 else "XX")
    
    print(f"{r['nombre']:<16} {r['dorms']:>2} {r['m2']:>4.0f} {r['cat']:>8} {r['macrozona']:<16} | "
          f"${r['value_s1']:>9,} ${r['value_v8f']:>10,} {delta:>+7.1f}% | "
          f"{t_str:>20} {ok_str:>6}")

print("-" * 105)
t_s1 = sum(r['value_s1'] for r in results)
t_v8f = sum(r['value_v8f'] for r in results)
delta_t = (t_v8f / t_s1 - 1) * 100 if t_s1 else 0
print(f"{'TOTAL':<16} {'':>2} {'':>4} {'':>8} {'':>16} | ${t_s1:>9,} ${t_v8f:>10,} {delta_t:>+7.1f}%")
