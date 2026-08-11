"""
Hybrid IDW+P33 Simulation — best of both worlds.
"""
import json
import math
import sys
import os
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

def crosses_barrier(lat1, lon1, lat2, lon2, barrier_lat):
    return (lat1 >= barrier_lat) != (lat2 >= barrier_lat)


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
    })

print(f"Loaded {len(venta)} venta properties")

# ============================================================
# LOAD PROPERTIES
# ============================================================

with open("propiedades.json", "r", encoding="utf-8") as f:
    prop_data = json.load(f)
propiedades = prop_data.get("propiedades", prop_data) if isinstance(prop_data, dict) else prop_data

print(f"Properties to valuate: {len(propiedades)}")

# ============================================================
# METHODS
# ============================================================

def current_method(comps, lat, lon):
    """Current system: blend P33 + barrier penalty"""
    same = [c for c in comps if not crosses_barrier(lat, lon, c["lat"], c["lon"], -32.965)]
    cross = [c for c in comps if crosses_barrier(lat, lon, c["lat"], c["lon"], -32.965)]
    
    if not same:
        return None, len(same), len(cross)
    
    same_p33 = compute_percentil(33, [c["valor_m2_adj"] for c in same])
    if not cross:
        return same_p33, len(same), len(cross)
    
    cross_p33 = compute_percentil(33, [c["valor_m2_adj"] for c in cross])
    alpha = min(0.70, max(0.50, 0.50 + 0.02 * len(same)))
    blend = alpha * same_p33 + (1-alpha) * cross_p33
    penalty = (len(cross) / len(comps)) * 0.03
    return blend * (1 - penalty), len(same), len(cross)

def idw_p33(comps, subj_dorms, subj_m2):
    """IDW-weighted P33 (no dorm filtering)"""
    if not comps:
        return None, 0
    
    # Weight by inverse distance
    weights = [1.0 / (c["dist_m"] ** 2) for c in comps]
    
    # Sort by weighted value
    weighted_vals = [(c["valor_m2_adj"], w) for c, w in zip(comps, weights)]
    weighted_vals.sort(key=lambda x: x[0])
    
    # Compute weighted P33
    total_w = sum(w for _, w in weighted_vals)
    target = total_w * 0.33
    cum_w = 0
    for val, w in weighted_vals:
        cum_w += w
        if cum_w >= target:
            return val, len(comps)
    
    return weighted_vals[-1][0], len(comps)

def idw_p33_dorm_filter(comps, subj_dorms, subj_m2):
    """IDW-weighted P33 with dorm filtering"""
    if not comps:
        return None, 0
    
    # Filter by dorm: same dorm or ±1
    filtered = [c for c in comps if abs((c["dormitorios"] or 2) - subj_dorms) <= 1]
    if len(filtered) < 3:
        filtered = comps  # fallback to all
    
    # Weight by inverse distance
    weights = [1.0 / (c["dist_m"] ** 2) for c in filtered]
    
    # Sort by weighted value
    weighted_vals = [(c["valor_m2_adj"], w) for c, w in zip(filtered, weights)]
    weighted_vals.sort(key=lambda x: x[0])
    
    # Compute weighted P33
    total_w = sum(w for _, w in weighted_vals)
    target = total_w * 0.33
    cum_w = 0
    for val, w in weighted_vals:
        cum_w += w
        if cum_w >= target:
            return val, len(filtered)
    
    return weighted_vals[-1][0], len(filtered)

def idw_p33_dorm_exact(comps, subj_dorms, subj_m2):
    """IDW-weighted P33 with exact dorm filtering"""
    if not comps:
        return None, 0
    
    # Filter by exact dorm
    filtered = [c for c in comps if (c["dormitorios"] or 2) == subj_dorms]
    if len(filtered) < 3:
        filtered = [c for c in comps if abs((c["dormitorios"] or 2) - subj_dorms) <= 1]
    if len(filtered) < 3:
        filtered = comps
    
    # Weight by inverse distance
    weights = [1.0 / (c["dist_m"] ** 2) for c in filtered]
    
    # Sort by weighted value
    weighted_vals = [(c["valor_m2_adj"], w) for c, w in zip(filtered, weights)]
    weighted_vals.sort(key=lambda x: x[0])
    
    # Compute weighted P33
    total_w = sum(w for _, w in weighted_vals)
    target = total_w * 0.33
    cum_w = 0
    for val, w in weighted_vals:
        cum_w += w
        if cum_w >= target:
            return val, len(filtered)
    
    return weighted_vals[-1][0], len(filtered)

def idw_p33_dorm_exact_hb(comps, subj_dorms, subj_m2, lat, lon):
    """IDW-weighted P33 + exact dorm + hard barriers"""
    if not comps:
        return None, 0
    
    # Hard barrier exclusion
    filtered = [c for c in comps if not crosses_barrier(lat, lon, c["lat"], c["lon"], -32.965)]
    filtered = [c for c in filtered if not crosses_barrier(lat, lon, c["lat"], c["lon"], -32.933)]
    
    # Filter by exact dorm
    dorm_filtered = [c for c in filtered if (c["dormitorios"] or 2) == subj_dorms]
    if len(dorm_filtered) < 3:
        dorm_filtered = [c for c in filtered if abs((c["dormitorios"] or 2) - subj_dorms) <= 1]
    if len(dorm_filtered) < 3:
        dorm_filtered = filtered
    
    # Weight by inverse distance
    weights = [1.0 / (c["dist_m"] ** 2) for c in dorm_filtered]
    
    # Sort by weighted value
    weighted_vals = [(c["valor_m2_adj"], w) for c, w in zip(dorm_filtered, weights)]
    weighted_vals.sort(key=lambda x: x[0])
    
    # Compute weighted P33
    total_w = sum(w for _, w in weighted_vals)
    target = total_w * 0.33
    cum_w = 0
    for val, w in weighted_vals:
        cum_w += w
        if cum_w >= target:
            return val, len(dorm_filtered)
    
    return weighted_vals[-1][0], len(dorm_filtered)

def idw_p33_dorm_exact_hb_f50(comps, subj_dorms, subj_m2, lat, lon):
    """IDW-weighted P33 + exact dorm + hard barriers + floor 50m"""
    if not comps:
        return None, 0
    
    # Hard barrier exclusion
    filtered = [c for c in comps if not crosses_barrier(lat, lon, c["lat"], c["lon"], -32.965)]
    filtered = [c for c in filtered if not crosses_barrier(lat, lon, c["lat"], c["lon"], -32.933)]
    
    # Filter by exact dorm
    dorm_filtered = [c for c in filtered if (c["dormitorios"] or 2) == subj_dorms]
    if len(dorm_filtered) < 3:
        dorm_filtered = [c for c in filtered if abs((c["dormitorios"] or 2) - subj_dorms) <= 1]
    if len(dorm_filtered) < 3:
        dorm_filtered = filtered
    
    # Weight by inverse distance with floor 50m
    weights = [1.0 / (max(c["dist_m"], 50) ** 2) for c in dorm_filtered]
    
    # Sort by weighted value
    weighted_vals = [(c["valor_m2_adj"], w) for c, w in zip(dorm_filtered, weights)]
    weighted_vals.sort(key=lambda x: x[0])
    
    # Compute weighted P33
    total_w = sum(w for _, w in weighted_vals)
    target = total_w * 0.33
    cum_w = 0
    for val, w in weighted_vals:
        cum_w += w
        if cum_w >= target:
            return val, len(dorm_filtered)
    
    return weighted_vals[-1][0], len(dorm_filtered)


# ============================================================
# SIMULATION
# ============================================================

print("\n" + "="*100)
print("HYBRID IDW+P33 SIMULATION — ALL PROPERTIES")
print("="*100)

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
            })
    
    # Compute all methods
    m1, m1_same, m1_cross = current_method(comps, lat, lon)
    m2, m2_n = idw_p33(comps, dorms, m2)
    m3, m3_n = idw_p33_dorm_filter(comps, dorms, m2)
    m4, m4_n = idw_p33_dorm_exact(comps, dorms, m2)
    m5, m5_n = idw_p33_dorm_exact_hb(comps, dorms, m2, lat, lon)
    m6, m6_n = idw_p33_dorm_exact_hb_f50(comps, dorms, m2, lat, lon)
    
    results.append({
        "name": name, "lat": lat, "lon": lon, "m2": m2, "dorms": dorms, "year": year,
        "n_total": len(comps),
        "m1": m1, "m1_same": m1_same, "m1_cross": m1_cross,
        "m2": m2, "m2_n": m2_n,
        "m3": m3, "m3_n": m3_n,
        "m4": m4, "m4_n": m4_n,
        "m5": m5, "m5_n": m5_n,
        "m6": m6, "m6_n": m6_n,
    })

# ============================================================
# PRINT RESULTS
# ============================================================

print(f"\n{'Property':<22} {'m2':>5} {'D':>2} | {'Current':>9} {'IDW-P33':>9} {'IDW-D':>9} {'IDW-DE':>9} {'IDW-DE-HB':>9} {'IDW-DE-HB-F':>9}")
print("-"*100)

for r in results:
    def fmt(v):
        return f"${v:.0f}" if v else "N/A"
    
    print(f"{r['name']:<22} {r['m2']:>5} {r['dorms']:>2} | {fmt(r['m1']):>9} {fmt(r['m2']):>9} {fmt(r['m3']):>9} {fmt(r['m4']):>9} {fmt(r['m5']):>9} {fmt(r['m6']):>9}")


# ============================================================
# DIFFERENCES
# ============================================================

print("\n" + "="*100)
print("DIFFERENCES vs CURRENT")
print("="*100)

methods = ["m2", "m3", "m4", "m5", "m6"]
labels = ["IDW-P33", "IDW-D (±1dorm)", "IDW-DE (exact dorm)", "IDW-DE-HB (exact+barriers)", "IDW-DE-HB-F50 (+floor)"]

for method, label in zip(methods, labels):
    diffs = []
    for r in results:
        if r[method] and r["m1"]:
            diff = (r[method] - r["m1"]) / r["m1"] * 100
            diffs.append(diff)
    if diffs:
        avg = sum(diffs) / len(diffs)
        med = sorted(diffs)[len(diffs)//2]
        mn = min(diffs)
        mx = max(diffs)
        print(f"\n{label}:")
        print(f"  Mean: {avg:+.1f}%  Median: {med:+.1f}%  Min: {mn:+.1f}%  Max: {mx:+.1f}%")


# ============================================================
# DETAILED EXAMPLES
# ============================================================

print("\n" + "="*100)
print("DETAILED EXAMPLES")
print("="*100)

for idx, r in enumerate(results):
    lat, lon = r["lat"], r["lon"]
    name = r["name"]
    
    comps = []
    for p in venta:
        dist = haversine_m(lat, lon, p["lat"], p["lon"])
        if dist <= 800:
            comps.append({
                "lat": p["lat"], "lon": p["lon"], "dist_m": dist,
                "valor_m2_adj": p["valor_m2_adj"], "dormitorios": p["dormitorios"],
                "m2": p["m2"],
            })
    comps.sort(key=lambda x: x["dist_m"])
    
    # Filter by exact dorm
    same_dorm = [c for c in comps if (c["dormitorios"] or 2) == r["dorms"]]
    same_dorm_hb = [c for c in same_dorm if not crosses_barrier(lat, lon, c["lat"], c["lon"], -32.965)]
    same_dorm_hb = [c for c in same_dorm_hb if not crosses_barrier(lat, lon, c["lat"], c["lon"], -32.933)]
    
    print(f"\n--- {name} (m2={r['m2']}, dorm={r['dorms']}) ---")
    print(f"  Total comps: {len(comps)}, Same dorm ({r['dorms']}d): {len(same_dorm)}, Same dorm + HB: {len(same_dorm_hb)}")
    
    # Show same-dorm comps
    print(f"\n  Same-dorm ({r['dorms']}d) comparables:")
    print(f"  {'#':>3} {'Dist':>6} {'P33':>8} {'D':>2} {'m2':>5} {'Barrier':>8}")
    print(f"  {'-'*40}")
    
    for i, c in enumerate(same_dorm[:10]):
        barrier = "27-Feb" if crosses_barrier(lat, lon, c["lat"], c["lon"], -32.965) else ""
        barrier = "FC" if crosses_barrier(lat, lon, c["lat"], c["lon"], -32.933) else barrier
        print(f"  {i+1:>3} {c['dist_m']:>5.0f}m ${c['valor_m2_adj']:>7.0f} {c['dormitorios']:>2} {c['m2']:>5.0f} {barrier:>8}")
    
    # Results
    print(f"\n  Results:")
    print(f"    Current (blend+barrier):      ${r['m1']:.0f}/m2")
    print(f"    IDW-P33 (all comps):          ${r['m2']:.0f}/m2 ({r['m2_n']} comps)")
    print(f"    IDW-D (dorm±1):               ${r['m3']:.0f}/m2 ({r['m3_n']} comps)")
    print(f"    IDW-DE (exact dorm):          ${r['m4']:.0f}/m2 ({r['m4_n']} comps)")
    print(f"    IDW-DE-HB (exact+barriers):   ${r['m5']:.0f}/m2 ({r['m5_n']} comps)")
    print(f"    IDW-DE-HB-F50 (+floor 50m):   ${r['m6']:.0f}/m2 ({r['m6_n']} comps)")
