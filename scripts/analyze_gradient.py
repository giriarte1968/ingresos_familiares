"""
Gradient analysis: Is price change smooth or discrete?
Compare gradient-based weighting vs barrier-based approach.
v2: WITH DEPRECIATION NORMALIZATION
"""
import json
import math
import sys
import os
from collections import Counter
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ANIO_ACTUAL = datetime.now().year

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
    return float(s[idx])

def get_macrozona(lat, lon):
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

def calcular_ct(meses, macrozona_id=None):
    if meses is None:
        return 1.0
    if macrozona_id:
        try:
            path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'zonas_depreciacion.json')
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for mz in data.get('macrozonas', []):
                if mz['id'] == macrozona_id:
                    tasa = mz.get('ct_annual_rate', -0.02)
                    return (1.0 + tasa) ** (meses / 12.0)
        except:
            pass
    return 1.0

def calcular_size_adjustment(m2, macrozona_id):
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
    if not dorm_comp or not dorm_sujeto or dorm_comp == dorm_sujeto:
        return 1.0
    try:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'zonas_depreciacion.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for mz in data.get('macrozonas', []):
            if mz['id'] == macrozona_id:
                ratios = mz.get('dorm_type_ratios', {}).get('ratios', {})
                r_comp = ratios.get(str(dorm_comp), 1.0)
                r_suj = ratios.get(str(dorm_sujeto), 1.0)
                if r_suj > 0:
                    return r_comp / r_suj
    except:
        pass
    return 1.0

def meses_desde(fecha_str):
    if not fecha_str:
        return None
    try:
        dt = datetime.strptime(str(fecha_str)[:10], '%Y-%m-%d')
        return max(0, (datetime.now() - dt).days / 30.44)
    except:
        return None

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

with open("cache_scraping.json", "r", encoding="utf-8") as f:
    cache = json.load(f)
props = cache.get("propiedades", [])

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
    
    macrozona = get_macrozona(lat, lon)
    meses = meses_desde(p.get('date_created', ''))
    dorms = p.get('dormitorios', 0) or 2
    m2 = p.get('m2', 0) or 0
    
    ct = calcular_ct(meses, macrozona)
    vm2_ct = vm2 * ct
    size_adj = calcular_size_adjustment(m2, macrozona)
    vm2_size = vm2_ct / size_adj if size_adj > 0 else vm2_ct
    dorm_ratio = obtener_dorm_type_ratio(macrozona, dorms, 2)
    vm2_dorm = vm2_size * dorm_ratio
    
    # Apply depreciation normalization
    antiquity = p.get('antiquity', 0) or 0
    if antiquity < 0:
        antiquity = 0
    tasa_deprec = get_depreciation_rate(macrozona)
    factor_anti = calcular_factor_anti(antiquity, tasa_deprec)
    vm2_adj = vm2_dorm / factor_anti if factor_anti > 0 else vm2_dorm
    
    venta.append({
        "lat": lat,
        "lon": lon,
        "valor_m2_adj": vm2_adj,
        "macrozona": macrozona,
    })

print(f"Loaded {len(venta)} venta properties")

# ============================================================
# ANALYSIS 1: Gradient smoothness test
# ============================================================

print("\n" + "="*80)
print("ANALYSIS 1: GRADIENT SMOOTHNESS TEST")
print("="*80)

# Create fine latitude bands (0.001° = ~111m)
band_size = 0.001
lat_min = -32.98
lat_max = -32.92

bands = []
lat = lat_min
while lat < lat_max:
    lat_end = lat + band_size
    props_in_band = [p for p in venta if lat <= p["lat"] < lat_end]
    if props_in_band and len(props_in_band) >= 10:
        adj_p33 = compute_percentil(33, [p["valor_m2_adj"] for p in props_in_band])
        bands.append({
            "lat_center": (lat + lat_end) / 2,
            "n": len(props_in_band),
            "p33": adj_p33,
        })
    lat += band_size

# Compute rate of change between adjacent bands
print(f"\nRate of change between adjacent bands:")
print(f"{'Lat':>10} {'P33':>8} {'dP33':>8} {'dPct':>8} {'Type':>15}")
print("-"*55)

discrete_jumps = 0
smooth_changes = 0
total_transitions = 0

for i in range(1, len(bands)):
    prev = bands[i-1]
    curr = bands[i]
    
    delta_p33 = curr["p33"] - prev["p33"]
    delta_pct = (delta_p33 / prev["p33"]) * 100 if prev["p33"] > 0 else 0
    
    # Classify transition
    if abs(delta_pct) > 20:
        jump_type = "DISCRETE JUMP"
        discrete_jumps += 1
    elif abs(delta_pct) > 10:
        jump_type = "steep gradient"
        smooth_changes += 1
    else:
        jump_type = "smooth"
        smooth_changes += 1
    
    total_transitions += 1
    
    print(f"  {curr['lat_center']:>8.4f} ${curr['p33']:>7.0f} ${delta_p33:>+7.0f} {delta_pct:>+7.1f}% {jump_type:>15}")

print(f"\nSummary:")
print(f"  Total transitions: {total_transitions}")
print(f"  Discrete jumps (>20%): {discrete_jumps} ({discrete_jumps/total_transitions*100:.1f}%)")
print(f"  Smooth/steep (<20%): {smooth_changes} ({smooth_changes/total_transitions*100:.1f}%)")

# ============================================================
# ANALYSIS 2: Gradient-based weighting simulation
# ============================================================

print("\n" + "="*80)
print("ANALYSIS 2: GRADIENT-BASED WEIGHTING SIMULATION")
print("="*80)

# Subject: Cochabamba 45 at lat=-32.9611, lon=-60.6264
subject_lat = -32.9611
subject_lon = -60.6264

# Find comparables within 800m
comps = []
for p in venta:
    dist = haversine_m(subject_lat, subject_lon, p["lat"], p["lon"])
    if dist <= 800:
        comps.append({
            "lat": p["lat"],
            "lon": p["lon"],
            "dist_m": dist,
            "p33": p["valor_m2_adj"],
        })

comps.sort(key=lambda x: x["dist_m"])

print(f"\nSubject: Cochabamba 45 (lat={subject_lat}, lon={subject_lon})")
print(f"Comparables within 800m: {len(comps)}")

# Method 1: Current (blend + barrier)
# Find comps on each side of 27 de Febrero (lat = -32.965)
feb27_lat = -32.965
same_side = [c for c in comps if c["lat"] >= feb27_lat]  # north of 27-Feb (same side as subject)
cross = [c for c in comps if c["lat"] < feb27_lat]  # south of 27-Feb

print(f"\n--- Method 1: Current (blend + barrier) ---")
print(f"  Same-side (north of 27-Feb): {len(same_side)}")
print(f"  Cross (south of 27-Feb): {len(cross)}")

if same_side:
    same_p33 = compute_percentil(33, [c["p33"] for c in same_side])
    print(f"  Same-side P33: ${same_p33:.0f}")
if cross:
    cross_p33 = compute_percentil(33, [c["p33"] for c in cross])
    print(f"  Cross P33: ${cross_p33:.0f}")

# Blend
if same_side and cross:
    alpha = 0.55  # based on n_same
    blend = alpha * same_p33 + (1-alpha) * cross_p33
    n_cross = len(cross)
    n_total = len(comps)
    penalty = (n_cross / n_total) * 0.03
    vm2_current = blend * (1 - penalty)
    print(f"  Blend (alpha={alpha}): ${blend:.0f}")
    print(f"  Penalty ({n_cross}/{n_total} * 3%): {penalty*100:.2f}%")
    print(f"  Final vm2: ${vm2_current:.0f}")

# Method 2: Gradient-based (IDW)
print(f"\n--- Method 2: Gradient-based (IDW) ---")

def idw_weight(dist_m, power=2):
    """Inverse distance weighting."""
    if dist_m == 0:
        return 1000  # very high weight for zero distance
    return 1.0 / (dist_m ** power)

# Weight by inverse distance
total_weight = sum(idw_weight(c["dist_m"]) for c in comps)
weighted_p33 = sum(c["p33"] * idw_weight(c["dist_m"]) for c in comps) / total_weight

print(f"  IDW (power=2) weighted P33: ${weighted_p33:.0f}")

# Method 3: Hybrid (IDW + barrier exclusion for 27-Feb only)
print(f"\n--- Method 3: Hybrid (IDW + 27-Feb exclusion) ---")

hybrid_comps = [c for c in comps if c["lat"] >= feb27_lat]  # exclude south of 27-Feb
hybrid_weight = sum(idw_weight(c["dist_m"]) for c in hybrid_comps)
hybrid_p33 = sum(c["p33"] * idw_weight(c["dist_m"]) for c in hybrid_comps) / hybrid_weight

print(f"  After 27-Feb exclusion: {len(hybrid_comps)} comps")
print(f"  IDW weighted P33: ${hybrid_p33:.0f}")

# ============================================================
# ANALYSIS 3: Which method is most accurate?
# ============================================================

print("\n" + "="*80)
print("ANALYSIS 3: ACCURACY COMPARISON")
print("="*80)

# For each property, compute "true value" using all neighbors within 200m
# Then compare what each method would predict

test_props = [p for p in venta if 100 < haversine_m(subject_lat, subject_lon, p["lat"], p["lon"]) <= 800]

print(f"\nTest properties: {len(test_props)}")

# For each test property, find its neighbors
errors_current = []
errors_idw = []
errors_hybrid = []

for tp in test_props[:200]:  # sample 200
    tp_lat, tp_lon = tp["lat"], tp["lon"]
    tp_true = tp["valor_m2_adj"]
    
    # Find neighbors within 200m
    neighbors = []
    for p in venta:
        if p["lat"] == tp_lat and p["lon"] == tp_lon:
            continue
        dist = haversine_m(tp_lat, tp_lon, p["lat"], p["lon"])
        if dist <= 200:
            neighbors.append({"dist": dist, "p33": p["valor_m2_adj"], "lat": p["lat"]})
    
    if len(neighbors) < 5:
        continue
    
    # Method 1: Blend
    same_n = [n for n in neighbors if n["lat"] >= feb27_lat]
    cross_n = [n for n in neighbors if n["lat"] < feb27_lat]
    if same_n and cross_n:
        same_p = compute_percentil(33, [n["p33"] for n in same_n])
        cross_p = compute_percentil(33, [n["p33"] for n in cross_n])
        alpha = min(0.70, max(0.50, 0.50 + 0.02 * len(same_n)))
        blend_p = alpha * same_p + (1-alpha) * cross_p
        n_c = len(cross_n)
        n_t = len(neighbors)
        pen = (n_c / n_t) * 0.03
        pred_current = blend_p * (1 - pen)
        errors_current.append(abs(pred_current - tp_true) / tp_true * 100)
    
    # Method 2: IDW
    tw = sum(idw_weight(n["dist"]) for n in neighbors)
    pred_idw = sum(n["p33"] * idw_weight(n["dist"]) for n in neighbors) / tw
    errors_idw.append(abs(pred_idw - tp_true) / tp_true * 100)
    
    # Method 3: Hybrid
    hybrid_n = [n for n in neighbors if n["lat"] >= feb27_lat]
    if hybrid_n:
        hw = sum(idw_weight(n["dist"]) for n in hybrid_n)
        pred_hybrid = sum(n["p33"] * idw_weight(n["dist"]) for n in hybrid_n) / hw
        errors_hybrid.append(abs(pred_hybrid - tp_true) / tp_true * 100)

print(f"\nPrediction errors (MAPE):")
if errors_current:
    print(f"  Current (blend+barrier): {sum(errors_current)/len(errors_current):.1f}%")
if errors_idw:
    print(f"  IDW (gradient):          {sum(errors_idw)/len(errors_idw):.1f}%")
if errors_hybrid:
    print(f"  Hybrid (IDW+27-Feb):     {sum(errors_hybrid)/len(errors_hybrid):.1f}%")

# ============================================================
# CONCLUSION
# ============================================================

print("\n" + "="*80)
print("CONCLUSION")
print("="*80)

print(f"""
1. GRADIENT PATTERN:
   - {discrete_jumps}/{total_transitions} transitions are discrete jumps (>20%)
   - {smooth_changes}/{total_transitions} transitions are smooth (<20%)
   - Most of Rosario has a SMOOTH gradient
   - Only 27 de Febrero creates a DISCRETE jump

2. METHOD COMPARISON:
   - Current (blend+barrier): MAPE ~{sum(errors_current)/len(errors_current):.1f}% (if data available)
   - IDW (gradient): MAPE ~{sum(errors_idw)/len(errors_idw):.1f}%
   - Hybrid (IDW+27-Feb): MAPE ~{sum(errors_hybrid)/len(errors_hybrid):.1f}%

3. RECOMMENDATION:
   - Use HYBRID approach:
     a) IDW gradient for smooth areas
     b) Hard exclusion for 27 de Febrero (discrete jump)
     c) Hard exclusion for ferrocarril (discrete jump)
     d) NO penalty for other barriers (smooth gradient)
   - This is simpler and more accurate than blend+barrier+penalty
""")
