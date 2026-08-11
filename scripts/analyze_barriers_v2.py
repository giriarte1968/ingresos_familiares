"""
Comprehensive Barrier Analysis v3 — WITH CT, size norm, dorm norm, DEPRECIATION
Compares RAW vs ADJUSTED (with antiquity normalization) results.
"""
import json
import math
import sys
import os
from collections import Counter, defaultdict
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- Configuration ---
RADIUS_M = 500
MIN_PROPS_PER_SIDE = 5
PCTL = 33
ANIO_ACTUAL = datetime.now().year

# --- Helper functions ---
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def compute_percentil(pctl, values):
    if not values:
        return None
    s = sorted(values)
    idx = int(len(s) * pctl / 100)
    idx = min(idx, len(s) - 1)
    idx = max(idx, 0)
    return float(s[idx])

def classify_barrier(gap_pct, p_value):
    if gap_pct > 20 and p_value < 0.01:
        return "STRONG"
    elif gap_pct >= 10 and gap_pct <= 20 and p_value < 0.05:
        return "MODERATE"
    elif gap_pct >= 5 and gap_pct < 10 and p_value < 0.05:
        return "WEAK"
    else:
        return "NONE"

def mannwhitney_u_test(group1, group2):
    n1, n2 = len(group1), len(group2)
    if n1 < 3 or n2 < 3:
        return 1.0
    combined = [(v, 0, i) for i, v in enumerate(group1)] + [(v, 1, i) for i, v in enumerate(group2)]
    combined.sort(key=lambda x: x[0])
    ranks = [0] * len(combined)
    i = 0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + j + 1) / 2.0
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j
    R1 = sum(ranks[k] for k in range(len(combined)) if combined[k][1] == 0)
    U1 = R1 - n1 * (n1 + 1) / 2.0
    U2 = n1 * n2 - U1
    U = min(U1, U2)
    mu = n1 * n2 / 2.0
    sigma = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12.0)
    if sigma == 0:
        return 1.0
    z = (U - mu) / sigma
    p = 2.0 * (1.0 - 0.5 * (1.0 + math.erf(abs(z) / math.sqrt(2.0))))
    return p

def get_barrier_midpoint(geometry):
    coords = geometry.get("coordinates", [])
    if not coords:
        return None, None
    mid = len(coords) // 2
    lon, lat = coords[mid]
    return lat, lon

def get_barrier_orientation(geometry):
    coords = geometry.get("coordinates", [])
    if len(coords) < 2:
        return "unknown", 0, 0
    lats = [c[1] for c in coords]
    lons = [c[0] for c in coords]
    dlat = max(lats) - min(lats)
    dlon = max(lons) - min(lons)
    if dlon > dlat * 1.5:
        return "east-west", dlat, dlon
    elif dlat > dlon * 1.5:
        return "north-south", dlat, dlon
    else:
        return "diagonal", dlat, dlon

def get_barrier_direction_vector(geometry):
    coords = geometry.get("coordinates", [])
    if len(coords) < 2:
        return None
    start = coords[0]
    end = coords[-1]
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.sqrt(dx*dx + dy*dy)
    if length == 0:
        return None
    return (dx/length, dy/length)

def assign_side(lat, lon, barrier_lat, barrier_lon, direction_vec):
    if direction_vec is None:
        return "unknown"
    vprop = (lon - barrier_lon, lat - barrier_lat)
    cross = direction_vec[0] * vprop[1] - direction_vec[1] * vprop[0]
    if cross > 0:
        return "side_A"
    elif cross < 0:
        return "side_B"
    else:
        return "on_line"

# --- Adjustment functions ---
def calcular_ct(meses, macrozona_id=None):
    """CT calculation using macrozona rate."""
    if meses is None:
        return 1.0
    if macrozona_id:
        tasa = get_ct_rate(macrozona_id)
        ct = (1.0 + tasa) ** (meses / 12.0)
        return ct
    return 1.0

def get_ct_rate(macrozona_id):
    """Get CT rate from zonas_depreciacion.json."""
    try:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'zonas_depreciacion.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for mz in data.get('macrozonas', []):
            if mz['id'] == macrozona_id:
                return mz.get('ct_annual_rate', -0.02)
    except:
        pass
    return -0.02

def meses_desde(fecha_str):
    """Months since date_created."""
    if not fecha_str:
        return None
    try:
        dt = datetime.strptime(str(fecha_str)[:10], '%Y-%m-%d')
        return max(0, (datetime.now() - dt).days / 30.44)
    except:
        return None

def get_macrozona_for_prop(lat, lon):
    """Assign macrozona by bbox."""
    mz_order = [
        ('puerto_norte', -32.93, -32.918, -60.674, -60.658),
        ('centro_premium', -32.96, -32.92, -60.67, -60.62),
        ('macrocentro', -32.975, -32.92, -60.69, -60.625),
        ('fisherton', -32.945, -32.9, -60.78, -60.72),
        ('norte', -32.93, -32.85, -60.78, -60.6),
        ('oeste', -32.975, -32.9, -60.78, -60.67),
        ('sur', -33.05, -32.975, -60.76, -60.6),
    ]
    for name, lat_min, lat_max, lon_min, lon_max in mz_order:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return name
    return 'resto_rosario'

def calcular_size_adjustment(m2, macrozona_id):
    """Size adjustment from zonas_depreciacion.json curves."""
    if not m2 or m2 <= 0:
        return 1.0
    try:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'zonas_depreciacion.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for mz in data.get('macrozonas', []):
            if mz['id'] == macrozona_id:
                points = mz.get('size_adjustment', {}).get('points', [])
                if not points:
                    return 1.0
                # Piecewise linear interpolation
                if m2 <= points[0]['m2']:
                    return points[0]['factor']
                if m2 >= points[-1]['m2']:
                    return points[-1]['factor']
                for i in range(len(points) - 1):
                    x1, y1 = points[i]['m2'], points[i]['factor']
                    x2, y2 = points[i+1]['m2'], points[i+1]['factor']
                    if x1 <= m2 <= x2:
                        t = (m2 - x1) / (x2 - x1) if x2 != x1 else 0
                        return y1 + t * (y2 - y1)
    except:
        pass
    return 1.0

def obtener_dorm_type_ratio(macrozona_id, dorm_comp, dorm_sujeto=2):
    """Dorm type ratio from zonas_depreciacion.json."""
    if not dorm_comp or not dorm_sujeto or dorm_comp == dorm_sujeto:
        return 1.0
    try:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'zonas_depreciacion.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for mz in data.get('macrozonas', []):
            if mz['id'] == macrozona_id:
                ratios = mz.get('dorm_type_ratios', {}).get('ratios', {})
                baseline = mz.get('dorm_type_ratios', {}).get('baseline', 2)
                r_comp = ratios.get(str(dorm_comp), 1.0)
                r_suj = ratios.get(str(dorm_sujeto), 1.0)
                if r_suj > 0:
                    return r_comp / r_suj
    except:
        pass
    return 1.0

def get_depreciation_rate(macrozona_id):
    """Get tasa_depreciacion_anual from zonas_depreciacion.json."""
    try:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'zonas_depreciacion.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for mz in data.get('macrozonas', []):
            if mz['id'] == macrozona_id:
                return mz.get('tasa_depreciacion_anual', 0.006)
    except:
        pass
    return 0.006

def calcular_factor_anti(antiguedad, tasa_depreciacion):
    """
    Calculate factor_anti exactly as the valuation system does.
    Formula: max(0.40, 1.0 + delta_anti_effective)
    """
    delta_anti_raw = max(-0.60, -(antiguedad * tasa_depreciacion))
    
    UMBRAL_PENALIZACION_SEVERA = -0.18
    FACTOR_ATENUACION = 0.35
    
    if delta_anti_raw < UMBRAL_PENALIZACION_SEVERA:
        exceso = delta_anti_raw - UMBRAL_PENALIZACION_SEVERA
        delta_anti = UMBRAL_PENALIZACION_SEVERA + (exceso * FACTOR_ATENUACION)
    else:
        delta_anti = delta_anti_raw
    
    return max(0.40, 1.0 + delta_anti)

# --- Main ---
print("Loading data...")

with open("barreras_rosario.json", "r", encoding="utf-8") as f:
    barriers_data = json.load(f)
barriers = barriers_data.get("features", [])
print(f"Loaded {len(barriers)} barriers")

with open("cache_scraping.json", "r", encoding="utf-8") as f:
    cache = json.load(f)
props = cache.get("propiedades", [])

# Filter and enrich properties
venta = []
for p in props:
    if p.get("operacion") != "venta":
        continue
    vm2 = p.get("valor_m2", 0)
    if not vm2 or vm2 <= 0:
        continue
    lat = p.get("lat")
    lon = p.get("lon")
    if lat is None or lon is None:
        continue
    try:
        lat, lon = float(lat), float(lon)
    except:
        continue
    
    # Get macrozona
    macrozona = get_macrozona_for_prop(lat, lon)
    
    # Get months since listing
    meses = meses_desde(p.get('date_created', ''))
    
    # Get dormitorios
    dorms = p.get('dormitorios', 0) or 2  # default to 2 if missing
    
    # Get m2
    m2 = p.get('m2', 0) or 0
    
    # Apply CT
    ct = calcular_ct(meses, macrozona)
    vm2_ct = vm2 * ct
    
    # Apply size normalization
    size_adj = calcular_size_adjustment(m2, macrozona)
    vm2_size = vm2_ct / size_adj if size_adj > 0 else vm2_ct
    
    # Apply dorm normalization (baseline = 2 dorm)
    dorm_ratio = obtener_dorm_type_ratio(macrozona, dorms, 2)
    vm2_dorm = vm2_size * dorm_ratio
    
    # Get antiquity and apply depreciation normalization
    antiquity = p.get('antiquity', 0) or 0
    if antiquity < 0:
        antiquity = 0
    anio_calc = ANIO_ACTUAL - antiquity if antiquity >= 0 else None
    tasa_deprec = get_depreciation_rate(macrozona)
    factor_anti = calcular_factor_anti(antiquity, tasa_deprec)
    vm2_final = vm2_dorm / factor_anti if factor_anti > 0 else vm2_dorm
    
    venta.append({
        "lat": lat,
        "lon": lon,
        "valor_m2_raw": vm2,
        "valor_m2_ct": vm2_ct,
        "valor_m2_ct_size": vm2_size,
        "valor_m2_ct_size_dorm": vm2_dorm,
        "valor_m2_final": vm2_final,
        "factor_anti": factor_anti,
        "macrozona": macrozona,
        "dormitorios": dorms,
        "m2": m2,
        "antiquity": antiquity,
        "anio_calc": anio_calc,
        "date_created": p.get('date_created', ''),
        "zona": p.get('zona', '?'),
    })

print(f"Loaded {len(venta)} venta properties")

# Show adjustment statistics
print(f"\n--- Adjustment Statistics ---")
raw_prices = [p["valor_m2_raw"] for p in venta]
ct_prices = [p["valor_m2_ct"] for p in venta]
size_prices = [p["valor_m2_ct_size"] for p in venta]
dorm_prices = [p["valor_m2_ct_size_dorm"] for p in venta]
final_prices = [p["valor_m2_final"] for p in venta]

for name, prices in [("RAW", raw_prices), ("+CT", ct_prices), ("+Size", size_prices), ("+Dorm", dorm_prices), ("+Anti", final_prices)]:
    avg = sum(prices) / len(prices)
    med = sorted(prices)[len(prices)//2]
    p33 = compute_percentil(33, prices)
    print(f"  {name:10}: avg=${avg:.0f}, P50=${med:.0f}, P33=${p33:.0f}")

# Depreciation stats
print(f"\n--- Depreciation Stats ---")
anti_factors = [p["factor_anti"] for p in venta]
print(f"  factor_anti avg: {sum(anti_factors)/len(anti_factors):.4f}")
print(f"  factor_anti min: {min(anti_factors):.4f}")
print(f"  factor_anti max: {max(anti_factors):.4f}")
print(f"  Props with factor < 0.90: {sum(1 for f in anti_factors if f < 0.90)} ({sum(1 for f in anti_factors if f < 0.90)/len(anti_factors)*100:.1f}%)")
print(f"  Props with factor < 0.80: {sum(1 for f in anti_factors if f < 0.80)} ({sum(1 for f in anti_factors if f < 0.80)/len(anti_factors)*100:.1f}%)")

# Macrozone distribution
mz_counts = Counter(p["macrozona"] for p in venta)
print(f"\n--- Macrozone Distribution ---")
for mz, count in mz_counts.most_common():
    prices = [p["valor_m2_final"] for p in venta if p["macrozona"] == mz]
    avg = sum(prices) / len(prices) if prices else 0
    print(f"  {mz:20}: {count:5} props, avg=${avg:.0f}/m2 (adjusted+anti)")

# --- Run analysis for both RAW and ADJUSTED ---
for mode in ["RAW", "ADJUSTED"]:
    print(f"\n{'='*80}")
    print(f"BARRIER ANALYSIS — {mode} PRICES")
    print(f"{'='*80}")
    
    if mode == "RAW":
        price_key = "valor_m2_raw"
    else:
        price_key = "valor_m2_final"
    
    results = []
    skipped = 0
    
    for i, barrier in enumerate(barriers):
        if (i + 1) % 200 == 0:
            print(f"  Processing barrier {i+1}/{len(barriers)}...")
        
        props_geom = barrier.get("properties", {})
        geometry = barrier.get("geometry", {})
        barrier_type = props_geom.get("barrier_type", "unknown")
        barrier_name = props_geom.get("name", "unknown")
        
        mid_lat, mid_lon = get_barrier_midpoint(geometry)
        if mid_lat is None:
            skipped += 1
            continue
        
        orientation, dlat, dlon = get_barrier_orientation(geometry)
        direction_vec = get_barrier_direction_vector(geometry)
        
        side_A = []
        side_B = []
        
        for p in venta:
            dist = haversine_m(mid_lat, mid_lon, p["lat"], p["lon"])
            if dist > RADIUS_M:
                continue
            side = assign_side(p["lat"], p["lon"], mid_lat, mid_lon, direction_vec)
            if side == "side_A":
                side_A.append(p)
            elif side == "side_B":
                side_B.append(p)
        
        if len(side_A) < MIN_PROPS_PER_SIDE or len(side_B) < MIN_PROPS_PER_SIDE:
            skipped += 1
            continue
        
        prices_A = [p[price_key] for p in side_A]
        prices_B = [p[price_key] for p in side_B]
        
        p33_A = compute_percentil(PCTL, prices_A)
        p33_B = compute_percentil(PCTL, prices_B)
        
        if p33_A is None or p33_B is None:
            skipped += 1
            continue
        
        max_p33 = max(p33_A, p33_B)
        min_p33 = min(p33_A, p33_B)
        gap_pct = ((max_p33 - min_p33) / max_p33) * 100 if max_p33 > 0 else 0
        
        p_value = mannwhitney_u_test(prices_A, prices_B)
        classification = classify_barrier(gap_pct, p_value)
        
        results.append({
            "name": barrier_name,
            "type": barrier_type,
            "orientation": orientation,
            "n_A": len(side_A),
            "n_B": len(side_B),
            "p33_A": round(p33_A, 2),
            "p33_B": round(p33_B, 2),
            "gap_pct": round(gap_pct, 2),
            "p_value": round(p_value, 6),
            "classification": classification,
        })
    
    print(f"\nAnalyzed: {len(results)} barriers (skipped: {skipped})")
    
    # Classification
    class_counts = Counter(r["classification"] for r in results)
    print(f"\nClassification:")
    for cls in ["STRONG", "MODERATE", "WEAK", "NONE"]:
        count = class_counts.get(cls, 0)
        pct = (count / len(results) * 100) if results else 0
        print(f"  {cls:10}: {count:4} ({pct:.1f}%)")
    
    # Gap stats
    print(f"\nGap statistics:")
    for cls in ["STRONG", "MODERATE", "WEAK", "NONE"]:
        gaps = [r["gap_pct"] for r in results if r["classification"] == cls]
        if gaps:
            avg_gap = sum(gaps) / len(gaps)
            print(f"  {cls:10}: avg={avg_gap:.1f}%")
    
    # Top 10
    print(f"\nTop 10 by gap:")
    top = sorted(results, key=lambda x: x["gap_pct"], reverse=True)[:10]
    for i, r in enumerate(top):
        print(f"  {i+1}. {r['name']:>30} {r['type']:>6} gap={r['gap_pct']:>5.1f}% P33_A=${r['p33_A']:.0f} P33_B=${r['p33_B']:.0f}")

print(f"\n{'='*80}")
print("COMPARISON: RAW vs ADJUSTED")
print(f"{'='*80}")
print("See analysis above for both modes.")
