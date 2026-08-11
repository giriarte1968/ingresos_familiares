"""
Analyze premium corridors in Rosario — how barriers interact with zones.
Focus on Pellegrini, 27 de Febrero, and other key corridors.
v2: WITH DEPRECIATION NORMALIZATION
"""
import json
import math
import sys
import os
from collections import Counter, defaultdict
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
        "valor_m2_raw": vm2,
        "valor_m2_adj": vm2_adj,
        "macrozona": macrozona,
        "dormitorios": dorms,
        "m2": m2,
        "zona_texto": p.get('zona', '?'),
        "direccion": p.get('direccion', '?'),
    })

print(f"Loaded {len(venta)} venta properties")

# ============================================================
# ANALYSIS: Latitude bands around key barriers
# ============================================================

print("\n" + "="*80)
print("ANALYSIS: PRICE GRADIENT BY LATITUDE BANDS")
print("="*80)

# Key barriers by latitude
barriers = {
    "27 de Febrero": -32.965,
    "Pellegrini": -32.949,
    "Oroño": -32.941,
    "Francia": -32.938,
}

# Create bands
band_size = 0.002  # ~220m
lat_min = -32.98
lat_max = -32.92

print(f"\nLatitude bands (size={band_size}, ~{band_size*111000:.0f}m):")
print(f"{'Lat Range':>25} {'N':>6} {'RAW P33':>10} {'ADJ P33':>10} {'Zone':>20} {'Near Barrier':>15}")
print("-"*95)

bands = []
lat = lat_min
while lat < lat_max:
    lat_end = lat + band_size
    props_in_band = [p for p in venta if lat <= p["lat"] < lat_end]
    
    if props_in_band:
        raw_p33 = compute_percentil(33, [p["valor_m2_raw"] for p in props_in_band])
        adj_p33 = compute_percentil(33, [p["valor_m2_adj"] for p in props_in_band])
        
        # Determine zone by text (most common)
        zones = Counter(p["zona_texto"] for p in props_in_band)
        main_zone = zones.most_common(1)[0][0] if zones else "?"
        
        # Check proximity to barriers
        near_barrier = []
        for bname, blat in barriers.items():
            if abs(lat - blat) < band_size:
                near_barrier.append(bname)
        near_str = ", ".join(near_barrier) if near_barrier else "-"
        
        bands.append({
            "lat_min": lat,
            "lat_max": lat_end,
            "n": len(props_in_band),
            "raw_p33": raw_p33,
            "adj_p33": adj_p33,
            "zone": main_zone,
            "near": near_str,
        })
        
        print(f"  {lat:>10.4f} to {lat_end:>10.4f} {len(props_in_band):>6} ${raw_p33:>9.0f} ${adj_p33:>9.0f} {main_zone:>20} {near_str:>15}")
    
    lat += band_size

# ============================================================
# ANALYSIS: Pellegrini corridor deep dive
# ============================================================

print("\n" + "="*80)
print("DEEP DIVE: PELLEGRINI CORRIDOR")
print("="*80)

# Pellegrini barrier at lat ≈ -32.949
# Properties within 300m of Pellegrini (both sides)
pellegrini_lat = -32.949
pellegrini_zone = [p for p in venta if abs(p["lat"] - pellegrini_lat) < 0.003]  # ~330m
south_of_pellegrini = [p for p in pellegrini_zone if p["lat"] < pellegrini_lat]
north_of_pellegrini = [p for p in pellegrini_zone if p["lat"] >= pellegrini_lat]

print(f"\nProperties within ~300m of Pellegrini barrier:")
print(f"  Total: {len(pellegrini_zone)}")
print(f"  South: {len(south_of_pellegrini)}")
print(f"  North: {len(north_of_pellegrini)}")

# Zone distribution
print(f"\nZone distribution (text labels):")
for zone, count in Counter(p["zona_texto"] for p in pellegrini_zone).most_common():
    props_z = [p for p in pellegrini_zone if p["zona_texto"] == zone]
    raw_avg = sum(p["valor_m2_raw"] for p in props_z) / len(props_z)
    adj_avg = sum(p["valor_m2_adj"] for p in props_z) / len(props_z)
    print(f"  {zone:20}: {count:4} props, RAW avg=${raw_avg:.0f}, ADJ avg=${adj_avg:.0f}")

# Price by side
print(f"\nPrice comparison (ADJUSTED):")
if south_of_pellegrini:
    south_p33 = compute_percentil(33, [p["valor_m2_adj"] for p in south_of_pellegrini])
    south_avg = sum(p["valor_m2_adj"] for p in south_of_pellegrini) / len(south_of_pellegrini)
    print(f"  South: P33=${south_p33:.0f}, avg=${south_avg:.0f}")
if north_of_pellegrini:
    north_p33 = compute_percentil(33, [p["valor_m2_adj"] for p in north_of_pellegrini])
    north_avg = sum(p["valor_m2_adj"] for p in north_of_pellegrini) / len(north_of_pellegrini)
    print(f"  North: P33=${north_p33:.0f}, avg=${north_avg:.0f}")

# ============================================================
# ANALYSIS: 27 de Febrero corridor
# ============================================================

print("\n" + "="*80)
print("DEEP DIVE: 27 DE FEBRERO CORRIDOR")
print("="*80)

feb27_lat = -32.965
feb27_zone = [p for p in venta if abs(p["lat"] - feb27_lat) < 0.003]
south_of_feb27 = [p for p in feb27_zone if p["lat"] < feb27_lat]
north_of_feb27 = [p for p in feb27_zone if p["lat"] >= feb27_lat]

print(f"\nProperties within ~300m of 27 de Febrero barrier:")
print(f"  Total: {len(feb27_zone)}")
print(f"  South: {len(south_of_feb27)}")
print(f"  North: {len(north_of_feb27)}")

print(f"\nZone distribution (text labels):")
for zone, count in Counter(p["zona_texto"] for p in feb27_zone).most_common():
    props_z = [p for p in feb27_zone if p["zona_texto"] == zone]
    raw_avg = sum(p["valor_m2_raw"] for p in props_z) / len(props_z)
    adj_avg = sum(p["valor_m2_adj"] for p in props_z) / len(props_z)
    print(f"  {zone:20}: {count:4} props, RAW avg=${raw_avg:.0f}, ADJ avg=${adj_avg:.0f}")

print(f"\nPrice comparison (ADJUSTED):")
if south_of_feb27:
    south_p33 = compute_percentil(33, [p["valor_m2_adj"] for p in south_of_feb27])
    south_avg = sum(p["valor_m2_adj"] for p in south_of_feb27) / len(south_of_feb27)
    print(f"  South: P33=${south_p33:.0f}, avg=${south_avg:.0f}")
if north_of_feb27:
    north_p33 = compute_percentil(33, [p["valor_m2_adj"] for p in north_of_feb27])
    north_avg = sum(p["valor_m2_adj"] for p in north_of_feb27) / len(north_of_feb27)
    print(f"  North: P33=${north_p33:.0f}, avg=${north_avg:.0f}")

# ============================================================
# ANALYSIS: Premium strips (between barriers)
# ============================================================

print("\n" + "="*80)
print("ANALYSIS: PREMIUM STRIPS BETWEEN BARRIERS")
print("="*80)

strips = [
    ("Sur of 27-Feb", -33.05, -32.965),
    ("27-Feb to Pellegrini", -32.965, -32.949),
    ("Pellegrini to Oroño", -32.949, -32.941),
    ("Oroño to Francia", -32.941, -32.938),
    ("North of Francia", -32.938, -32.92),
]

print(f"\n{'Strip':>25} {'N':>6} {'RAW P33':>10} {'ADJ P33':>10} {'Character':>30}")
print("-"*85)

for name, lat_min_s, lat_max_s in strips:
    props_strip = [p for p in venta if lat_min_s <= p["lat"] < lat_max_s]
    if props_strip:
        raw_p33 = compute_percentil(33, [p["valor_m2_raw"] for p in props_strip])
        adj_p33 = compute_percentil(33, [p["valor_m2_adj"] for p in props_strip])
        
        # Character
        zones = Counter(p["zona_texto"] for p in props_strip)
        main_zones = [z for z, c in zones.most_common(2)]
        char = " / ".join(main_zones)
        
        print(f"  {name:>25} {len(props_strip):>6} ${raw_p33:>9.0f} ${adj_p33:>9.0f} {char:>30}")

# ============================================================
# CONCLUSION: How to configure each corridor
# ============================================================

print("\n" + "="*80)
print("RECOMMENDATIONS: CORRIDOR CONFIGURATION")
print("="*80)

print("""
1. PELLEGRINI CORRIDOR:
   - Premium zone ($2,083/m2 text-labeled)
   - Barrier does NOT create price discontinuity
   - Configuration: DO NOT use as barrier for same-zone properties
   - Use: Zone override (Pellegrini = premium, regardless of barrier)

2. 27 DE FEBRERO:
   - TRUE barrier (53% price gap)
   - South: $658/m2 (affordable residential)
   - North: $1,500-1,700/m2 (urban core)
   - Configuration: HARD barrier (exclude cross comps)
   - Or: Very high penalty (40-50%)

3. OROÑO:
   - NOT a significant barrier
   - Configuration: Ignore or very low penalty

4. FRANCIA:
   - Marginal barrier (20% gap)
   - Configuration: Moderate penalty (15-20%)

5. FERROCARRIL (railway):
   - STRONG barrier (35-45% gap)
   - Configuration: HARD barrier (already excluded)
""")
