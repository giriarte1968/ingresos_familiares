"""
IDW Improved Simulation — with dormitorio + size similarity weighting.
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

def dorm_similarity(d1, d2):
    diff = abs((d1 or 2) - (d2 or 2))
    if diff == 0: return 1.0
    if diff == 1: return 0.7
    return 0.4

def size_similarity(m2a, m2b):
    if not m2a or not m2b or m2a <= 0 or m2b <= 0:
        return 0.5
    ratio = max(m2a, m2b) / min(m2a, m2b)
    if ratio < 1.3: return 1.0
    if ratio < 1.6: return 0.8
    if ratio < 2.0: return 0.6
    return 0.4


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
# SIMULATION
# ============================================================

print("\n" + "="*110)
print("IDW IMPROVED SIMULATION — ALL PROPERTIES")
print("="*110)
print("Parameters: all dormitorios, 60 months retro, 800m radius")
print("Weighting: 1/dist^2 * dorm_similarity * size_similarity")
print("Hard barriers: 27-Feb (lat -32.965) + ferrocarril (lat -32.933)")

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
    
    # --- Method 1: Current (blend + barrier) ---
    same_side = [c for c in comps if not crosses_barrier(lat, lon, c["lat"], c["lon"], -32.965)]
    cross = [c for c in comps if crosses_barrier(lat, lon, c["lat"], c["lon"], -32.965)]
    
    def compute_blend_p33(same, cross_list):
        if not same:
            return None, 0, 0
        same_p33 = compute_percentil(33, [c["valor_m2_adj"] for c in same])
        if not cross_list:
            return same_p33, len(same), 0
        cross_p33 = compute_percentil(33, [c["valor_m2_adj"] for c in cross_list])
        alpha = min(0.70, max(0.50, 0.50 + 0.02 * len(same)))
        blend = alpha * same_p33 + (1-alpha) * cross_p33
        n_cross = len(cross_list)
        n_total = len(same) + len(cross_list)
        penalty = (n_cross / n_total) * 0.03 if n_total > 0 else 0
        return blend * (1 - penalty), len(same), len(cross_list)
    
    m1_vm2, m1_n_same, m1_n_cross = compute_blend_p33(same_side, cross)
    
    # --- Method 2: IDW pure (power=2) ---
    def idw_pure(comps_list):
        if not comps_list:
            return None
        tw = sum(1.0 / (c["dist_m"] ** 2) for c in comps_list)
        return sum(c["valor_m2_adj"] / (c["dist_m"] ** 2) for c in comps_list) / tw
    
    m2_vm2 = idw_pure(comps)
    
    # --- Method 3: IDW + hard barriers ---
    hard_excluded = [c for c in comps if not crosses_barrier(lat, lon, c["lat"], c["lon"], -32.965)]
    hard_excluded = [c for c in hard_excluded if not crosses_barrier(lat, lon, c["lat"], c["lon"], -32.933)]
    m3_vm2 = idw_pure(hard_excluded)
    
    # --- Method 4: IDW improved (dorm + size similarity) ---
    def idw_improved(comps_list, subj_dorms, subj_m2):
        if not comps_list:
            return None
        weights = []
        for c in comps_list:
            d_sim = dorm_similarity(c["dormitorios"], subj_dorms)
            s_sim = size_similarity(c["m2"], subj_m2)
            w = (1.0 / (c["dist_m"] ** 2)) * d_sim * s_sim
            weights.append(w)
        tw = sum(weights)
        return sum(c["valor_m2_adj"] * w for c, w in zip(comps_list, weights)) / tw
    
    m4_vm2 = idw_improved(comps, dorms, m2)
    
    # --- Method 5: IDW improved + hard barriers ---
    m5_vm2 = idw_improved(hard_excluded, dorms, m2)
    
    # --- Method 6: IDW improved + barriers + floor 50m ---
    def idw_improved_floor(comps_list, subj_dorms, subj_m2, floor_m=50):
        if not comps_list:
            return None
        weights = []
        for c in comps_list:
            d_eff = max(c["dist_m"], floor_m)
            d_sim = dorm_similarity(c["dormitorios"], subj_dorms)
            s_sim = size_similarity(c["m2"], subj_m2)
            w = (1.0 / (d_eff ** 2)) * d_sim * s_sim
            weights.append(w)
        tw = sum(weights)
        return sum(c["valor_m2_adj"] * w for c, w in zip(comps_list, weights)) / tw
    
    m6_vm2 = idw_improved_floor(hard_excluded, dorms, m2)
    
    # --- Method 7: IDW improved + barriers + power=1.5 ---
    def idw_improved_p15(comps_list, subj_dorms, subj_m2):
        if not comps_list:
            return None
        weights = []
        for c in comps_list:
            d_sim = dorm_similarity(c["dormitorios"], subj_dorms)
            s_sim = size_similarity(c["m2"], subj_m2)
            w = (1.0 / (c["dist_m"] ** 1.5)) * d_sim * s_sim
            weights.append(w)
        tw = sum(weights)
        return sum(c["valor_m2_adj"] * w for c, w in zip(comps_list, weights)) / tw
    
    m7_vm2 = idw_improved_p15(hard_excluded, dorms, m2)
    
    # --- Method 8: IDW improved + barriers + floor + p1.5 ---
    m8_vm2 = idw_improved_floor(hard_excluded, dorms, m2, floor_m=50)
    # recalc with p1.5
    def idw_improved_p15_floor(comps_list, subj_dorms, subj_m2, floor_m=50):
        if not comps_list:
            return None
        weights = []
        for c in comps_list:
            d_eff = max(c["dist_m"], floor_m)
            d_sim = dorm_similarity(c["dormitorios"], subj_dorms)
            s_sim = size_similarity(c["m2"], subj_m2)
            w = (1.0 / (d_eff ** 1.5)) * d_sim * s_sim
            weights.append(w)
        tw = sum(weights)
        return sum(c["valor_m2_adj"] * w for c, w in zip(comps_list, weights)) / tw
    
    m8_vm2 = idw_improved_p15_floor(hard_excluded, dorms, m2)
    
    # Store
    results.append({
        "name": name, "lat": lat, "lon": lon, "m2": m2, "dorms": dorms, "year": year,
        "n_total": len(comps),
        "m1": m1_vm2, "m1_same": m1_n_same, "m1_cross": m1_n_cross,
        "m2": m2_vm2,
        "m3": m3_vm2,
        "m4": m4_vm2,
        "m5": m5_vm2,
        "m6": m6_vm2,
        "m7": m7_vm2,
        "m8": m8_vm2,
    })


# ============================================================
# PRINT RESULTS
# ============================================================

print(f"\n{'Property':<22} {'m2':>5} {'D':>2} {'N':>4} | {'Current':>9} {'IDW':>9} {'IDW+HB':>9} {'IDW-Sim':>9} {'IDW-Sim+HB':>9} {'IDW-Sim+HB+F':>9} {'IDW-Sim+HB+P15':>9} {'IDW-Sim+HB+P15+F':>9}")
print("-"*160)

for r in results:
    def fmt(v):
        return f"${v:.0f}" if v else "N/A"
    
    print(f"{r['name']:<22} {r['m2']:>5} {r['dorms']:>2} {r['n_total']:>4} | {fmt(r['m1']):>9} {fmt(r['m2']):>9} {fmt(r['m3']):>9} {fmt(r['m4']):>9} {fmt(r['m5']):>9} {fmt(r['m6']):>9} {fmt(r['m7']):>9} {fmt(r['m8']):>9}")


# ============================================================
# DETAILED EXAMPLES
# ============================================================

print("\n" + "="*110)
print("DETAILED EXAMPLES")
print("="*110)

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
    
    print(f"\n--- {name} (m2={r['m2']}, dorm={r['dorms']}, year={r['year']}) ---")
    print(f"  Comparables within 800m: {len(comps)}")
    
    # Top 15 with weights
    print(f"  Top 15 closest with weights (dorm_sim * size_sim):")
    print(f"  {'#':>3} {'Dist':>6} {'P33':>8} {'D':>2} {'m2':>5} {'dSim':>5} {'sSim':>5} {'w':>10}")
    print(f"  {'-'*55}")
    
    for i, c in enumerate(comps[:15]):
        d_sim = dorm_similarity(c["dormitorios"], r["dorms"])
        s_sim = size_similarity(c["m2"], r["m2"])
        w_raw = 1.0 / (c["dist_m"] ** 2)
        w_imp = w_raw * d_sim * s_sim
        print(f"  {i+1:>3} {c['dist_m']:>5.0f}m ${c['valor_m2_adj']:>7.0f} {c['dormitorios']:>2} {c['m2']:>5.0f} {d_sim:>5.2f} {s_sim:>5.2f} {w_imp:>10.8f}")
    
    # Results comparison
    print(f"\n  Results:")
    print(f"    Current (blend+barrier):  ${r['m1']:.0f}/m2")
    print(f"    IDW pure:                 ${r['m2']:.0f}/m2")
    print(f"    IDW + HB:                 ${r['m3']:.0f}/m2")
    print(f"    IDW improved:             ${r['m4']:.0f}/m2  (+dorm+size sim)")
    print(f"    IDW improved + HB:        ${r['m5']:.0f}/m2  (+dorm+size sim + barriers)")
    print(f"    IDW improved + HB + F50:  ${r['m6']:.0f}/m2  (+floor 50m)")
    print(f"    IDW improved + HB + P15:  ${r['m7']:.0f}/m2  (power=1.5)")
    print(f"    IDW improved + HB + F50+P15: ${r['m8']:.0f}/m2")


# ============================================================
# SUMMARY: Which method is most realistic?
# ============================================================

print("\n" + "="*110)
print("SUMMARY: DIFFERENCES vs CURRENT")
print("="*110)

methods = ["m2", "m3", "m4", "m5", "m6", "m7", "m8"]
labels = ["IDW pure", "IDW+HB", "IDW-Sim", "IDW-Sim+HB", "IDW-Sim+HB+F50", "IDW-Sim+HB+P15", "IDW-Sim+HB+F50+P15"]

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
