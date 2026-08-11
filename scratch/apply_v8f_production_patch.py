import sys, os

file_path = r'c:\Users\Gustavo\ingresos_familiares_st\parsers\mercado_inmobiliario.py'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

v8f_code = '''
# ==============================================================================
# MODELO v8f: SA CONTINUO + FLEX DORM EMPIRICO + BARRERAS VECTORIALES (V8F PRODUCTION)
# ==============================================================================
_sa_cont_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'sa_continuous.json')
try:
    with open(_sa_cont_path, 'r', encoding='utf-8') as _f:
        sa_cont_data = json.load(_f)
except Exception:
    sa_cont_data = {}

_flex_dorm_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'flex_dorm_factors.json')
try:
    with open(_flex_dorm_path, 'r', encoding='utf-8') as _f:
        flex_dorm_data = json.load(_f).get('data', {})
except Exception:
    flex_dorm_data = {}

_barreras_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'barreras_rosario.json')
try:
    with open(_barreras_path, 'r', encoding='utf-8') as _f:
        barreras_data = json.load(_f)
        barreras_features = barreras_data.get('features', [])
except Exception:
    barreras_data = {}
    barreras_features = []

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

MACROZONE_BARRIER_GAP_FALLBACKS = {
    'centro_premium': 0.1588,
    'macrocentro': 0.2014,
    'puerto_norte': 0.0567,
    'norte': 0.3741,
    'oeste': 0.1469,
    'fisherton': 0.0,
    'sur_default': 0.0725,
    'resto_rosario': 0.1692,
}

BARRIER_VECTOR_INFO = {
    "Vías FC Rosario Central": {"cheaper_side": "LEFT", "gap": 0.2014},
    "Vías FC Barrio Martin / Puerto": {"cheaper_side": "RIGHT", "gap": 0.1588},
    "Av. Pellegrini (Macrocentro / Abasto)": {"cheaper_side": "RIGHT", "gap": 0.1250},
    "Av. Francia (Centro / Puerto Norte)": {"cheaper_side": "LEFT", "gap": 0.1450},
    "Av. 27 de Febrero (Macrocentro / Sur)": {"cheaper_side": "RIGHT", "gap": 0.1820},
}

def get_beta_continuous(macrozona_id, dorms=1):
    mz = sa_cont_data.get('macrozonas', {}).get(macrozona_id or '_global', {})
    d_str = str(min(max(dorms or 1, 1), 4))
    beta = mz.get(d_str, mz.get('all', -0.18))
    if beta is None or beta >= 0:
        beta = mz.get('all', -0.18)
    if beta is None or beta >= 0:
        beta = sa_cont_data.get('beta_global_all', -0.18)
    return max(-0.35, min(-0.05, beta))

def sa_factor_continuous(m2_sujeto, m2_comp, macrozona_id=None, dorms=1):
    if not m2_sujeto or not m2_comp or m2_comp <= 0 or m2_sujeto <= 0:
        return 1.0
    beta = get_beta_continuous(macrozona_id, dorms)
    ratio = (m2_sujeto / m2_comp) ** beta
    bounds = SA_CONTINUOUS_BOUNDS_2SIGMA.get(macrozona_id, SA_CONTINUOUS_BOUNDS_2SIGMA['_global'])
    return max(bounds[0], min(bounds[1], ratio))

def _obtener_flex_fallback_dinamico():
    tot = 0
    w = {'1': 0.0, '2': 0.0, '3': 0.0, '4': 0.0}
    for mz, data in flex_dorm_data.items():
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
    mz_data = flex_dorm_data.get(macrozona_id or '', {})
    if not mz_data:
        mz_data = flex_dorm_data.get('_global', {})
    ratios = mz_data.get('ratios_vs_2d', {})
    if not ratios:
        ratios = _obtener_flex_fallback_dinamico()
    r_suj = ratios.get(str(dorms_sujeto), 1.0)
    r_comp = ratios.get(str(dorms_comp), 1.0)
    if not r_suj or not r_comp or r_comp == 0:
        return 1.0
    factor = r_suj / r_comp
    return max(0.50, min(2.00, factor))

def get_closest_segment_side(px, py, segment_coords):
    if not segment_coords or len(segment_coords) < 2: return "LEFT", 999.0
    min_d = 999.0
    best_cross = 0.0
    for i in range(len(segment_coords)-1):
        ax, ay = segment_coords[i]
        bx, by = segment_coords[i+1]
        v_x, v_y = bx - ax, by - ay
        w_x, w_y = px - ax, py - ay
        c1 = w_x * v_x + w_y * v_y
        c2 = v_x * v_x + v_y * v_y
        b = c1 / c2 if c2 > 0 else 0
        b = max(0.0, min(1.0, b))
        closest_x = ax + b * v_x
        closest_y = ay + b * v_y
        d = math.hypot(px - closest_x, py - closest_y)
        if d < min_d:
            min_d = d
            best_cross = v_x * (py - ay) - v_y * (px - ax)
    side = "LEFT" if best_cross >= 0 else "RIGHT"
    return side, min_d

def detectar_barrera_vector(lat_suj, lon_suj, lat_comp, lon_comp):
    if not lat_suj or not lon_suj or not lat_comp or not lon_comp:
        return None, {}, []
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

def calcular_factor_penalty_vector(lat_suj, lon_suj, lat_comp, lon_comp, macrozona_id=None):
    if not lat_suj or not lon_suj or not lat_comp or not lon_comp:
        return 1.0
    barrier_name, b_info, coords = detectar_barrera_vector(lat_suj, lon_suj, lat_comp, lon_comp)
    if not barrier_name:
        return 1.0
    side_suj, _ = get_closest_segment_side(lon_suj, lat_suj, coords)
    side_comp, _ = get_closest_segment_side(lon_comp, lat_comp, coords)
    if side_suj == side_comp: return 1.0
    gap_fallback = MACROZONE_BARRIER_GAP_FALLBACKS.get(macrozona_id or '', 0.1692)
    cheaper_side = b_info.get('cheaper_side')
    gap = b_info.get('gap', gap_fallback)
    penalty = gap / 2.0
    if side_suj == cheaper_side and side_comp != cheaper_side:
        factor = 1.0 - penalty
    elif side_suj != cheaper_side and side_comp == cheaper_side:
        factor = 1.0 / max(1.0 - penalty, 0.70)
    else:
        factor = 1.0
    return max(0.70, min(1.43, factor))

def _precio_ajustado(c, macrozona_id=None, ancla_id=None, dormitorios_sujeto=None, m2_sujeto=None, lat_suj=None, lon_suj=None):
    """Calcula precio normalizado v8f: Ct * SA Continuo * Flex-Dorm Ratio * Vector Barriers."""
    precio = c.get('precio_m2', c.get('valor_m2', 0))
    adj = c.get('time_adjustment', c.get('_time_adjustment', 1.0))
    raw_val = precio * adj
    if not raw_val or raw_val <= 0:
        return 0.0
    m2_comp = c.get('m2') or c.get('m2_cubiertos', 0) or 0
    dorms_comp = c.get('dormitorios', dormitorios_sujeto)
    
    if m2_sujeto and m2_comp > 0:
        ratio_sa = sa_factor_continuous(m2_sujeto, m2_comp, macrozona_id, dorms=dormitorios_sujeto)
    else:
        adj_size = calcular_size_adjustment(m2_comp, macrozona_id, ancla_id=ancla_id, dormitorios=dorms_comp)
        ratio_sa = (1.0 / adj_size) if adj_size > 0 else 1.0

    norm_val = raw_val * ratio_sa
    
    if dormitorios_sujeto and dorms_comp and dorms_comp != dormitorios_sujeto:
        adj_dorm = factor_dorm_flex(dormitorios_sujeto, dorms_comp, macrozona_id)
        if adj_dorm != 1.0:
            norm_val *= adj_dorm
            
    if lat_suj and lon_suj and c.get('lat') and c.get('lon'):
        f_vector = calcular_factor_penalty_vector(lat_suj, lon_suj, float(c['lat']), float(c['lon']), macrozona_id)
        norm_val *= f_vector
        
    return norm_val

def _computar_vm2_core(comparables, percentil, apply_barrier=True, alpha=None, macrozona_id=None, ancla_id=None, dormitorios_sujeto=None, m2_sujeto=None, lat_suj=None, lon_suj=None):
    """
    NÚCLEO UNIFICADO DE CÁLCULO VM2 v8f
    Mezcla Inverse-Variance Weighting entre same vs cross dorm pools.
    """
    from parsers.cluster_filters import calcular_percentil, _calcular_cv
    
    same = [c for c in comparables if not c.get('_cross_soft', False)]
    cross = [c for c in comparables if c.get('_cross_soft', False)]
    
    precios_same = sorted([_precio_ajustado(c, macrozona_id, ancla_id=ancla_id, dormitorios_sujeto=dormitorios_sujeto, m2_sujeto=m2_sujeto, lat_suj=lat_suj, lon_suj=lon_suj) for c in same])
    precios_same = [p for p in precios_same if p and p > 0]
    
    precios_cross = sorted([_precio_ajustado(c, macrozona_id, ancla_id=ancla_id, dormitorios_sujeto=dormitorios_sujeto, m2_sujeto=m2_sujeto, lat_suj=lat_suj, lon_suj=lon_suj) for c in cross])
    precios_cross = [p for p in precios_cross if p and p > 0]

    pct_same = calcular_percentil(precios_same, percentil) if precios_same else None
    pct_cross = calcular_percentil(precios_cross, percentil) if precios_cross else None

    # Inverse-Variance Weighting
    if pct_same is not None and pct_cross is not None:
        cv_same = _calcular_cv(precios_same) if len(precios_same) >= 3 else 0.25
        cv_cross = _calcular_cv(precios_cross) if len(precios_cross) >= 3 else 0.35
        var_same = (cv_same ** 2) + 0.0001
        var_cross = (cv_cross ** 2) + 0.0001
        w_same = len(precios_same) / var_same
        w_cross = len(precios_cross) / var_cross
        alpha_eff = w_same / (w_same + w_cross)
        vm2 = alpha_eff * pct_same + (1.0 - alpha_eff) * pct_cross
    elif pct_same is not None:
        vm2 = pct_same
    elif pct_cross is not None:
        vm2 = pct_cross
    else:
        vm2 = 0.0

    return round(vm2, 2), len(precios_same), len(precios_cross), pct_same, pct_cross

def _calcular_vm2_base(comparables, percentil, macrozona_id=None, ancla_id=None, dormitorios_sujeto=None, m2_sujeto=None, lat_suj=None, lon_suj=None):
    vm2, n_same, n_cross, pct_same, pct_cross = _computar_vm2_core(
        comparables, percentil, apply_barrier=True, alpha=None, macrozona_id=macrozona_id, ancla_id=ancla_id, dormitorios_sujeto=dormitorios_sujeto, m2_sujeto=m2_sujeto, lat_suj=lat_suj, lon_suj=lon_suj
    )
    return vm2, n_same, n_cross, pct_same, pct_cross
'''

target_marker = "def _mapear_confianza(percentil_usado):"
if target_marker in content:
    content = content.replace(target_marker, v8f_code + "\n\n" + target_marker, 1)
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("PATCH APPLIED SUCCESSFULLY!")
else:
    print("TARGET MARKER NOT FOUND")
