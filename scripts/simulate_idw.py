"""
IDW Gradient Simulation — Full comparison across all properties.
No dormitorio filter, 60 months retro, 800m radius.
"""
import json
import math
import sys
import os
from datetime import datetime
from collections import defaultdict

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

def crosses_27feb(lat1, lon1, lat2, lon2):
    """Check if line between two points crosses 27 de Febrero (lat ~-32.965)."""
    feb27_lat = -32.965
    return (lat1 >= feb27_lat) != (lat2 >= feb27_lat)

def crosses_ferrocarril(lat1, lon1, lat2, lon2):
    """Check if line crosses ferrocarril (lat ~-32.933)."""
    fc_lat = -32.933
    return (lat1 >= fc_lat) != (lat2 >= fc_lat)


# ============================================================
# LOAD DATA
# ============================================================

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
    vm2_adj = vm2_size * dorm_ratio
    
    venta.append({
        "lat": lat,
        "lon": lon,
        "valor_m2_adj": vm2_adj,
        "macrozona": macrozona,
        "dormitorios": dorms,
        "m2": m2,
        "date_created": p.get("date_created"),
        "title": p.get("title", "")[:40],
    })

print(f"Loaded {len(venta)} venta properties")

# ============================================================
# LOAD PROPERTIES TO VALUATE
# ============================================================

with open("propiedades.json", "r", encoding="utf-8") as f:
    prop_data = json.load(f)
propiedades = prop_data.get("propiedades", prop_data) if isinstance(prop_data, dict) else prop_data

print(f"\nProperties to valuate: {len(propiedades)}")

# ============================================================
# SIMULATION
# ============================================================

print("\n" + "="*100)
print("IDW GRADIENT SIMULATION — ALL PROPERTIES")
print("="*100)
print("Parameters: all dormitorios, 60 months retro, 800m radius, hard barriers (27-Feb + ferrocarril)")

results = []

for prop in propiedades:
    name = prop.get("nombre", prop.get("direccion", "Unknown"))
    lat = prop.get("lat")
    lon = prop.get("lon")
    m2 = prop.get("m2_cubiertos", 0) or prop.get("m2", 0) or 0
    dorms = prop.get("dormitorios", 2) or 2
    year = prop.get("antiquity") or prop.get("year")
    
    if lat is None or lon is None:
        continue
    try:
        lat, lon = float(lat), float(lon)
    except:
        continue
    
    # Find comparables within 800m
    comps = []
    for p in venta:
        dist = haversine_m(lat, lon, p["lat"], p["lon"])
        if dist <= 800:
            comps.append({
                "lat": p["lat"],
                "lon": p["lon"],
                "dist_m": dist,
                "valor_m2_adj": p["valor_m2_adj"],
                "dormitorios": p["dormitorios"],
                "m2": p["m2"],
                "title": p["title"],
            })
    
    comps.sort(key=lambda x: x["dist_m"])
    
    # --- Method 1: Current (blend + barrier) ---
    same_side = []
    cross = []
    for c in comps:
        if crosses_27feb(lat, lon, c["lat"], c["lon"]):
            cross.append(c)
        else:
            same_side.append(c)
    
    # --- Method 2: IDW (no barrier exclusion) ---
    # --- Method 3: IDW + hard barrier exclusion (27-Feb only) ---
    hard_excluded = [c for c in comps if not crosses_27feb(lat, lon, c["lat"], c["lon"])]
    # Also exclude ferrocarril cross
    hard_excluded = [c for c in hard_excluded if not crosses_ferrocarril(lat, lon, c["lat"], c["lon"])]
    
    # Compute valuations
    def compute_idw(comps_list):
        if not comps_list:
            return None, 0, []
        total_weight = sum(1.0 / (c["dist_m"] ** 2) for c in comps_list)
        weighted = sum(c["valor_m2_adj"] / (c["dist_m"] ** 2) for c in comps_list) / total_weight
        return weighted, len(comps_list), comps_list
    
    def compute_blend_p33(comps_same, comps_cross):
        if not comps_same:
            return None, 0, 0, 0
        same_p33 = compute_percentil(33, [c["valor_m2_adj"] for c in comps_same])
        if not comps_cross:
            return same_p33, len(comps_same), len(comps_cross), same_p33
        cross_p33 = compute_percentil(33, [c["valor_m2_adj"] for c in comps_cross])
        alpha = min(0.70, max(0.50, 0.50 + 0.02 * len(comps_same)))
        blend = alpha * same_p33 + (1-alpha) * cross_p33
        n_cross = len(comps_cross)
        n_total = len(comps_same) + len(comps_cross)
        penalty = (n_cross / n_total) * 0.03 if n_total > 0 else 0
        vm2 = blend * (1 - penalty)
        return vm2, len(comps_same), len(comps_cross), blend
    
    # Method 1: Current
    m1_vm2, m1_n_same, m1_n_cross, m1_blend = compute_blend_p33(same_side, cross)
    
    # Method 2: IDW (no exclusion)
    m2_vm2, m2_n, _ = compute_idw(comps)
    
    # Method 3: IDW + hard barriers
    m3_vm2, m3_n, _ = compute_idw(hard_excluded)
    
    # Store results
    results.append({
        "name": name,
        "lat": lat,
        "lon": lon,
        "m2": m2,
        "dorms": dorms,
        "year": year,
        "n_total": len(comps),
        "m1_vm2": m1_vm2,
        "m1_n_same": m1_n_same,
        "m1_n_cross": m1_n_cross,
        "m1_blend": m1_blend,
        "m2_vm2": m2_vm2,
        "m2_n": m2_n,
        "m3_vm2": m3_vm2,
        "m3_n": m3_n,
        "diff_m2_m1": ((m2_vm2 - m1_vm2) / m1_vm2 * 100) if m1_vm2 and m1_vm2 > 0 else None,
        "diff_m3_m1": ((m3_vm2 - m1_vm2) / m1_vm2 * 100) if m1_vm2 and m1_vm2 > 0 else None,
    })

# ============================================================
# PRINT RESULTS
# ============================================================

print(f"\n{'Property':<25} {'m2':>5} {'D':>2} {'Year':>5} | {'Current':>10} {'IDW':>10} {'IDW+HB':>10} | {'dIDW':>8} {'dIDW+HB':>8}")
print("-"*120)

for r in results:
    m1 = f"${r['m1_vm2']:.0f}" if r['m1_vm2'] else "N/A"
    m2 = f"${r['m2_vm2']:.0f}" if r['m2_vm2'] else "N/A"
    m3 = f"${r['m3_vm2']:.0f}" if r['m3_vm2'] else "N/A"
    d2 = f"{r['diff_m2_m1']:+.1f}%" if r['diff_m2_m1'] is not None else ""
    d3 = f"{r['diff_m3_m1']:+.1f}%" if r['diff_m3_m1'] is not None else ""
    
    print(f"{r['name']:<25} {r['m2']:>5} {r['dorms']:>2} {r['year'] or 'N/A':>5} | {m1:>10} {m2:>10} {m3:>10} | {d2:>8} {d3:>8}")

# ============================================================
# DETAILED EXAMPLES (top 3)
# ============================================================

print("\n" + "="*100)
print("DETAILED EXAMPLES — TOP 3 PROPERTIES")
print("="*100)

for idx, r in enumerate(results[:3]):
    lat, lon = r["lat"], r["lon"]
    name = r["name"]
    
    # Find comparables
    comps = []
    for p in venta:
        dist = haversine_m(lat, lon, p["lat"], p["lon"])
        if dist <= 800:
            comps.append({
                "lat": p["lat"],
                "lon": p["lon"],
                "dist_m": dist,
                "valor_m2_adj": p["valor_m2_adj"],
                "dormitorios": p["dormitorios"],
                "m2": p["m2"],
                "title": p["title"],
            })
    
    comps.sort(key=lambda x: x["dist_m"])
    
    print(f"\n--- Property {idx+1}: {name} ---")
    print(f"  Location: lat={lat:.6f}, lon={lon:.6f}")
    print(f"  m2={r['m2']}, dorm={r['dorms']}, year={r['year']}")
    print(f"  Total comparables within 800m: {len(comps)}")
    
    # Show top 10 closest
    print(f"\n  Top 10 closest comparables:")
    print(f"  {'#':>3} {'Dist':>6} {'P33':>8} {'Dorm':>4} {'m2':>5} {'Title':<40}")
    print(f"  {'-'*70}")
    
    for i, c in enumerate(comps[:10]):
        marker = " <-- HARD BARRIER" if crosses_27feb(lat, lon, c["lat"], c["lon"]) else ""
        print(f"  {i+1:>3} {c['dist_m']:>5.0f}m ${c['valor_m2_adj']:>7.0f} {c['dormitorios']:>4} {c['m2']:>5} {c['title']:<40}{marker}")
    
    # Summary
    print(f"\n  Results:")
    print(f"    Current (blend+barrier): ${r['m1_vm2']:.0f}/m2 ({r['m1_n_same']} same + {r['m1_n_cross']} cross)")
    print(f"    IDW (no exclusion):      ${r['m2_vm2']:.0f}/m2 ({r['m2_n']} comps)")
    print(f"    IDW + hard barriers:     ${r['m3_vm2']:.0f}/m2 ({r['m3_n']} comps after exclusion)")

# ============================================================
# SUMMARY STATISTICS
# ============================================================

print("\n" + "="*100)
print("SUMMARY STATISTICS")
print("="*100)

diffs_m2 = [r["diff_m2_m1"] for r in results if r["diff_m2_m1"] is not None]
diffs_m3 = [r["diff_m3_m1"] for r in results if r["diff_m3_m1"] is not None]

if diffs_m2:
    print(f"\nIDW vs Current:")
    print(f"  Mean difference: {sum(diffs_m2)/len(diffs_m2):+.1f}%")
    print(f"  Median: {sorted(diffs_m2)[len(diffs_m2)//2]:+.1f}%")
    print(f"  Min: {min(diffs_m2):+.1f}%")
    print(f"  Max: {max(diffs_m2):+.1f}%")

if diffs_m3:
    print(f"\nIDW+HB vs Current:")
    print(f"  Mean difference: {sum(diffs_m3)/len(diffs_m3):+.1f}%")
    print(f"  Median: {sorted(diffs_m3)[len(diffs_m3)//2]:+.1f}%")
    print(f"  Min: {min(diffs_m3):+.1f}%")
    print(f"  Max: {max(diffs_m3):+.1f}%")

# Count properties where IDW is higher/lower
higher = sum(1 for r in results if r['diff_m2_m1'] and r['diff_m2_m1'] > 0)
lower = sum(1 for r in results if r['diff_m2_m1'] and r['diff_m2_m1'] < 0)
same = sum(1 for r in results if r['diff_m2_m1'] is not None and abs(r['diff_m2_m1']) < 1)
print(f"\nIDW vs Current:")
print(f"  Higher: {higher}/{len(results)} ({higher/len(results)*100:.1f}%)")
print(f"  Lower: {lower}/{len(results)} ({lower/len(results)*100:.1f}%)")
print(f"  Similar (within 1%): {same}/{len(results)} ({same/len(results)*100:.1f}%)")

print("\nDone!")
