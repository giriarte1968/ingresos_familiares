"""
SIMULACION v8c - PENALTY DIRECCIONAL POR BARRERA
=================================================
Mejora sobre v8b: el penalty se aplica HACIA el mercado del sujeto.

  Si sujeto en lado BARATO y comp en lado CARO:
    precio_cross_aj = precio_norm * (1 - gap/2)   <- baja el comp caro

  Si sujeto en lado CARO y comp en lado BARATO:
    precio_cross_aj = precio_norm / (1 - gap/2)   <- sube el comp barato

Esto corrige el problema de Cochabamba (+107K en v8b) donde el penalty
subia los comps caros de Centro en vez de bajarlos al nivel de la Sexta.

Correcciones adicionales vs v8b:
  - Asignacion de lados corregida: barrera NS -> separa E/W por longitud
  - SA por dormitorio (si disponible en sa_categoricas.json)
  - Sin modificar produccion
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
print("SIMULACION v8c: SA relativo + Penalty DIRECCIONAL por barrera")
print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
print("=" * 90)

# ============================================================
# BARRERAS: CALCULAR GAPS + LADO CARO/BARATO
# ============================================================
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def pct(data, p):
    s = sorted(data)
    idx = int(len(s) * p / 100)
    return s[min(idx, len(s)-1)] if s else None

def get_side(lat, lon, mid_lat, mid_lon, direction):
    """
    Asigna lado A o B segun la geometria de la barrera.
    CORREGIDO: barrera NS (corre N-S) separa E/W por longitud.
               barrera EW (corre E-W) separa N/S por latitud.
    """
    if direction == 'NS':   # barrera vertical -> separa Este/Oeste
        return 'A' if lon > mid_lon else 'B'
    else:                   # barrera horizontal -> separa Norte/Sur
        return 'A' if lat > mid_lat else 'B'

ventas_raw = [p for p in cache_scraping['propiedades']
              if p.get('operacion') == 'venta'
              and 200 < p.get('valor_m2', 0) < 10000
              and p.get('lat') and p.get('lon')]

print(f"\nCalculando BARRIER_INFO desde {len(ventas_raw)} ventas...")
RADIO_BARRERA = 300
BARRIER_INFO = {}   # nombre -> {gap, is_hard, mid_lat, mid_lon, direction, p50_A, p50_B}

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
    dlat = p2[1] - p1[1]
    dlon = p2[0] - p1[0]
    direction = 'NS' if abs(dlat) > abs(dlon) else 'EW'

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
        side = get_side(plat, plon, mid_lat, mid_lon, direction)
        (lado_A if side == 'A' else lado_B).append(vm2)

    if len(lado_A) >= 5 and len(lado_B) >= 5:
        p50_A = pct(lado_A, 50)
        p50_B = pct(lado_B, 50)
        if p50_A and p50_B and min(p50_A, p50_B) > 0:
            gap = abs(p50_A - p50_B) / max(p50_A, p50_B)
            BARRIER_INFO[nombre] = {
                'gap': gap, 'is_hard': is_hard,
                'mid_lat': mid_lat, 'mid_lon': mid_lon,
                'direction': direction,
                'p50_A': p50_A, 'p50_B': p50_B,
                'n_A': len(lado_A), 'n_B': len(lado_B),
            }

GAP_FALLBACK = 0.143  # media empirica como fallback

print(f"\nBarreras con info: {len(BARRIER_INFO)}")
print(f"\n{'Barrera':<45} {'Dir':>4} {'gap':>7} {'lado A (p50)':>13} {'lado B (p50)':>13} {'caro':>5}")
print("-" * 90)
for nombre, info in sorted(BARRIER_INFO.items(), key=lambda x: -x[1]['gap']):
    caro = 'A' if info['p50_A'] > info['p50_B'] else 'B'
    tipo = "HARD" if info['is_hard'] else "soft"
    print(f"{nombre:<45} {info['direction']:>4} {info['gap']*100:>6.1f}%  "
          f"${info['p50_A']:>5,.0f} (n={info['n_A']:>3})  "
          f"${info['p50_B']:>5,.0f} (n={info['n_B']:>3})  lado {caro}")

# ============================================================
# CRUCE DE BARRERAS (para cross_soft comps)
# ============================================================
def detectar_barrera(lon_suj, lat_suj, lon_comp, lat_comp):
    """
    Retorna (nombre, info) de la PRIMERA barrera cruzada entre sujeto y comp.
    Trabaja sobre segmentos del GeoJSON (barreras con muchos puntos).
    """
    for barrera in barreras_features:
        props_b = barrera.get('properties', {})
        nombre = props_b.get('name', '?')
        geom = barrera.get('geometry', {})
        coords = geom.get('coordinates', [])
        if not coords or len(coords) < 2:
            continue
        # Chequear interseccion con cada segmento
        for i in range(len(coords) - 1):
            bx1, by1 = coords[i]
            bx2, by2 = coords[i+1]
            denom = (lat_comp - lat_suj) * (bx2 - bx1) - (lon_comp - lon_suj) * (by2 - by1)
            if abs(denom) < 1e-12:
                continue
            t = ((lon_suj - bx1) * (by2 - by1) - (lat_suj - by1) * (bx2 - bx1)) / denom
            u = -((lon_comp - lon_suj) * (lat_suj - by1) - (lat_comp - lat_suj) * (lon_suj - bx1)) / denom
            if 0 <= t <= 1 and 0 <= u <= 1:
                return nombre, BARRIER_INFO.get(nombre, {})
    return None, {}

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

# ============================================================
# PRECIO NORMALIZADO CON SA RELATIVO
# ============================================================
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
# PENALTY DIRECCIONAL
# ============================================================
def penalty_direccional(lat_suj, lon_suj, lat_comp, lon_comp, barrier_nombre, barrier_info):
    """
    Determina si comp esta en lado mas caro que sujeto y aplica factor correcto.
    Retorna factor multiplicativo:
      < 1: baja el comp (comp en zona cara, sujeto en barata)
      > 1: sube el comp (comp en zona barata, sujeto en cara)
      = 1: sin ajuste (sin info de barrera)
    """
    if not barrier_info:
        # Sin info: usar gap fallback, baja ligeramente (conservador)
        return 1 - GAP_FALLBACK / 2

    mid_lat = barrier_info['mid_lat']
    mid_lon = barrier_info['mid_lon']
    direction = barrier_info['direction']
    p50_A = barrier_info['p50_A']
    p50_B = barrier_info['p50_B']
    gap = barrier_info['gap']

    side_suj = get_side(lat_suj, lon_suj, mid_lat, mid_lon, direction)
    side_comp = get_side(lat_comp, lon_comp, mid_lat, mid_lon, direction)

    if side_suj == side_comp:
        # Mismo lado (cruce dudoso): sin penalty
        return 1.0

    p50_suj_side = p50_A if side_suj == 'A' else p50_B
    p50_comp_side = p50_A if side_comp == 'A' else p50_B

    if p50_comp_side > p50_suj_side:
        # Comp en zona MAS CARA -> bajar precio para reflejar mercado del sujeto
        factor = 1 - gap / 2
    else:
        # Comp en zona MAS BARATA -> subir precio
        factor = 1 / (1 - gap / 2)

    # Cap: max 30% de ajuste en un sentido
    return max(0.70, min(1.43, factor))

# ============================================================
# VALUACION v8c
# ============================================================
def valuar_v8c(pool, m2_sujeto, dorms_sujeto, macrozona_id,
               lat_suj, lon_suj, cv_ref):
    """
    SA relativo + penalty direccional sobre comps cross_soft.
    Usa _cross_soft del engine (ya excluyo hard barriers).
    Para cross: detecta barrera cruzada y aplica factor direccional.
    """
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

        # Para cross: detectar barrera y aplicar penalty direccional
        lat_comp = comp.get('lat')
        lon_comp = comp.get('lon')
        factor = 1 - GAP_FALLBACK / 2  # fallback conservador

        if lat_comp and lon_comp and lat_suj and lon_suj:
            try:
                barr_nombre, barr_info = detectar_barrera(
                    float(lon_suj), float(lat_suj),
                    float(lon_comp), float(lat_comp)
                )
                factor = penalty_direccional(
                    float(lat_suj), float(lon_suj),
                    float(lat_comp), float(lon_comp),
                    barr_nombre, barr_info
                )
                if barr_nombre:
                    gap_pct = barr_info.get('gap', GAP_FALLBACK) * 100
                    adj_pct = (factor - 1) * 100
                    detalle_barreras.append(f"{barr_nombre[:20]}({adj_pct:+.1f}%)")
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

def sa_none(m2, macrozona_id=None, ancla_id=None, dormitorios=None):
    return 1.0

# ============================================================
# LOOP PRINCIPAL: 9 PROPIEDADES
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

    # METODO v8c
    v8c = valuar_v8c(pool, m2, dorms, macrozona_id, lat, lon, cv_ref)
    value_v8c = round(v8c['vm2'] * m2_equiv) if v8c['vm2'] else 0

    sa_suj = sa_factor(m2, macrozona_id, dorms)
    cat_suj = clasificar(m2)

    results.append({
        'nombre': nombre, 'dorms': dorms, 'm2': m2, 'm2eq': m2_equiv,
        'macrozona': macrozona_id or '?', 'cat': cat_suj, 'sa_suj': sa_suj,
        'value_s1': value_s1, 'value_v8c': value_v8c, 'stored': stored,
        'n_pool': len(pool), 'n_same': v8c['n_same'], 'n_cross': v8c['n_cross'],
        'pct': v8c['pct'], 'cv': v8c['cv'],
        'barreras': v8c['barreras'],
    })

# ============================================================
# TABLA PRINCIPAL
# ============================================================
print("\n" + "=" * 110)
print(f"{'Prop':<16} {'d':>2} {'m2':>4} {'cat':>7} {'sa_suj':>7} {'zona':<16} | {'ENGINE':>10} {'v8c':>10} {'delta%':>7} | {'N':>3} {'s':>3} {'x':>3} {'pct':>4} | barreras")
print("-" * 110)

for r in results:
    delta = (r['value_v8c'] / r['value_s1'] - 1) * 100 if r['value_s1'] else 0
    barr_str = ', '.join(r['barreras'][:2]) if r['barreras'] else '-'
    print(f"{r['nombre']:<16} {r['dorms']:>2} {r['m2']:>4.0f} {r['cat']:>7} {r['sa_suj']:>7.3f} {r['macrozona']:<16} | "
          f"${r['value_s1']:>9,} ${r['value_v8c']:>9,} {delta:>+7.1f}% | "
          f"{r['n_pool']:>3} {r['n_same']:>3} {r['n_cross']:>3} {r['pct']:>4} | {barr_str}")

print("-" * 110)
t_s1 = sum(r['value_s1'] for r in results)
t_v8c = sum(r['value_v8c'] for r in results)
delta_t = (t_v8c / t_s1 - 1) * 100 if t_s1 else 0
print(f"{'TOTAL':<16} {'':>2} {'':>4} {'':>7} {'':>7} {'':>16} | ${t_s1:>9,} ${t_v8c:>9,} {delta_t:>+7.1f}%")

# ============================================================
# ANALISIS COMPONENTES
# ============================================================
print("\n\nANALISIS DE COMPONENTES:")
print(f"{'Prop':<16} {'same':>5} {'cross':>5} | {'vm2_engine':>11} {'vm2_v8c':>10} | {'SA efecto':>11} {'Penalty':>10}")
print("-" * 80)
for r in results:
    vm2_e = r['value_s1'] / r['m2eq'] if r['m2eq'] else 0
    vm2_v = r['value_v8c'] / r['m2eq'] if r['m2eq'] else 0
    sa_efecto = f"suj={r['sa_suj']:.3f}"
    penalty_str = f"gap_dir/{GAP_FALLBACK/2*100:.0f}%" if r['n_cross'] > 0 else "sin cross"
    print(f"{r['nombre']:<16} {r['n_same']:>5} {r['n_cross']:>5} | ${vm2_e:>9,.0f} ${vm2_v:>9,.0f} | {sa_efecto:>11} {penalty_str:>10}")

# ============================================================
# COMPARACION: DIRECCIONABILIDAD DEL PENALTY
# ============================================================
print("\n\nDIAGNOSTICO PENALTY DIRECCIONAL (casos con cross comps):")
print("-" * 70)
for r in results:
    if r['n_cross'] == 0:
        continue
    vm2_e = r['value_s1'] / r['m2eq'] if r['m2eq'] else 0
    vm2_v = r['value_v8c'] / r['m2eq'] if r['m2eq'] else 0
    delta_vm2 = vm2_v - vm2_e
    barr_str = ', '.join(r['barreras'][:3]) if r['barreras'] else 'sin deteccion'
    print(f"\n  {r['nombre']} (1d, {r['cat']}, {r['macrozona']}):")
    print(f"    Pool: {r['n_pool']} | same={r['n_same']} cross={r['n_cross']}")
    print(f"    ENGINE vm2: ${vm2_e:,.0f} -> v8c vm2: ${vm2_v:,.0f} ({delta_vm2:+,.0f})")
    print(f"    Barreras: {barr_str}")

# ============================================================
# COMPARACION METODOLOGICA ENGINE vs v8c
# ============================================================
print("\n\nRESUMEN METODOLOGICO:")
print("=" * 60)
print(f"{'Componente':<30} {'ENGINE':<20} {'v8c':<20}")
print("-" * 60)
comps = [
    ("SA normalizacion",   "raw / adj_comp",          "raw * (f_suj/f_comp)"),
    ("SA referencia",      "punto 150m2",              "sujeto especifico"),
    ("Penalty cross",      "3% fijo de n_cross/total", "gap_empirico/2 direc."),
    ("Blend alpha",        "0.50-0.70 (arbitrario)",   "eliminado"),
    ("Percentil",          "P33-P50 segun CV",         "P33-P50 segun CV"),
    ("Hard barriers",      "excluye",                  "excluye (via engine)"),
    ("Soft barriers",      "_cross_soft marca",        "_cross_soft + direc."),
]
for c, e, v in comps:
    print(f"  {c:<28} {e:<20} {v:<20}")

print("\n\nGAPS EMPIRICOS USADOS PARA PENALTY DIRECCIONAL:")
for nombre, info in sorted(BARRIER_INFO.items(), key=lambda x: -x[1]['gap']):
    caro = 'A ($' + f"{info['p50_A']:,.0f}" + ')' if info['p50_A'] > info['p50_B'] else 'B ($' + f"{info['p50_B']:,.0f}" + ')'
    tipo = "HARD" if info['is_hard'] else "soft"
    print(f"  {nombre:<42} {tipo:<5} gap={info['gap']*100:.1f}%  lado_caro={caro}")
