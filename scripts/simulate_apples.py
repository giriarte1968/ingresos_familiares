"""
Apples-to-apples comparison: Same comps, different weighting.
Method 1: Current (blend P33 + barrier + penalty)
Method 2: IDW P33 (same comps, inverse-distance weighted P33)
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

def compute_year(antiquity):
    if antiquity and antiquity > 0:
        return ANIO_ACTUAL - antiquity
    return None

def idw_p33_weighted(comps, dist_power=2):
    """IDW-weighted P33 from a list of comps (already filtered)."""
    if not comps:
        return None
    weights = [1.0 / (c["dist_m"] ** dist_power) for c in comps]
    weighted_vals = [(c["valor_m2_adj"], w) for c, w in zip(comps, weights)]
    weighted_vals.sort(key=lambda x: x[0])
    total_w = sum(w for _, w in weighted_vals)
    target = total_w * 0.33
    cum_w = 0
    for val, w in weighted_vals:
        cum_w += w
        if cum_w >= target:
            return val
    return weighted_vals[-1][0]


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
    
    antiquity = p.get('antiquity')
    year = compute_year(antiquity) if antiquity and antiquity > 0 else None
    
    venta.append({
        "lat": lat, "lon": lon, "valor_m2_adj": vm2_adj,
        "dormitorios": dorms, "m2": m2, "year": year,
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
# SIMULATION — SAME COMPS, DIFFERENT WEIGHTING
# ============================================================

print("\n" + "="*110)
print("APPLES-TO-APPLES: Same comparable selection, different weighting")
print("="*110)

results = []

for prop in propiedades:
    name = prop.get("nombre", prop.get("direccion", "Unknown"))
    lat = prop.get("lat")
    lon = prop.get("lon")
    m2 = prop.get("m2_cubiertos", 0) or prop.get("m2", 0) or 0
    dorms = prop.get("dormitorios", 2) or 2
    year = prop.get("anio_construccion") or prop.get("antiquity")
    if year and year < 100:
        year = ANIO_ACTUAL - year
    
    if lat is None or lon is None:
        continue
    try:
        lat, lon = float(lat), float(lon)
    except:
        continue
    
    # --- STEP 1: Find all comparables within 800m ---
    comps = []
    for p in venta:
        dist = haversine_m(lat, lon, p["lat"], p["lon"])
        if dist <= 800:
            comps.append({
                "lat": p["lat"], "lon": p["lon"], "dist_m": dist,
                "valor_m2_adj": p["valor_m2_adj"], "dormitorios": p["dormitorios"],
                "m2": p["m2"], "year": p["year"],
            })
    
    # --- STEP 2: Same filtering logic (dorm ±1, age ±10yr) ---
    # Dorm filter
    filtered = [c for c in comps if abs((c["dormitorios"] or 2) - dorms) <= 1]
    if len(filtered) < 3:
        filtered = comps
    
    # Age filter
    if year:
        year_min = year - 10
        year_max = year + 10
        age_filtered = [c for c in filtered if c['year'] and year_min <= c['year'] <= year_max]
        if len(age_filtered) >= 5:
            filtered = age_filtered
    
    # --- STEP 3: Split by 27-Feb barrier (for current method) ---
    same_side = [c for c in filtered if not crosses_barrier(lat, lon, c["lat"], c["lon"], -32.965)]
    cross = [c for c in filtered if crosses_barrier(lat, lon, c["lat"], c["lon"], -32.965)]
    
    # --- METHOD 1: Current (blend P33 + barrier + penalty) ---
    m1_vm2 = None
    m1_blend = None
    m1_penalty = 0
    if same_side:
        same_p33 = compute_percentil(33, [c["valor_m2_adj"] for c in same_side])
        if cross:
            cross_p33 = compute_percentil(33, [c["valor_m2_adj"] for c in cross])
            alpha = min(0.70, max(0.50, 0.50 + 0.02 * len(same_side)))
            m1_blend = alpha * same_p33 + (1-alpha) * cross_p33
            m1_penalty = (len(cross) / len(filtered)) * 0.03
            m1_vm2 = m1_blend * (1 - m1_penalty)
        else:
            m1_vm2 = same_p33
            m1_blend = same_p33
    
    # --- METHOD 2: IDW P33 (same filtered comps, IDW weighting) ---
    m2_vm2 = idw_p33_weighted(filtered, dist_power=2)
    
    # --- METHOD 3: IDW P33 power=1.5 ---
    m3_vm2 = idw_p33_weighted(filtered, dist_power=1.5)
    
    results.append({
        "name": name, "lat": lat, "lon": lon, "m2": m2, "dorms": dorms, "year": year,
        "n_comps": len(filtered),
        "n_same": len(same_side), "n_cross": len(cross),
        "m1": m1_vm2, "m1_blend": m1_blend, "m1_penalty": m1_penalty,
        "m2": m2_vm2,
        "m3": m3_vm2,
    })

# ============================================================
# PRINT RESULTS
# ============================================================

print(f"\n{'Property':<22} {'m2':>5} {'D':>2} {'Year':>5} {'N':>4} | {'Current':>9} {'IDW-p2':>9} {'IDW-p1.5':>9} | {'dIDWp2':>8} {'dIDWp15':>8}")
print("-"*115)

for r in results:
    def fmt(v):
        return f"${v:.0f}" if v else "N/A"
    
    d2 = ((r['m2'] - r['m1']) / r['m1'] * 100) if r['m1'] and r['m2'] else None
    d3 = ((r['m3'] - r['m1']) / r['m1'] * 100) if r['m1'] and r['m3'] else None
    d2s = f"{d2:+.1f}%" if d2 is not None else ""
    d3s = f"{d3:+.1f}%" if d3 is not None else ""
    
    yr = str(int(r['year'])) if r['year'] else "N/A"
    print(f"{r['name']:<22} {r['m2']:>5} {r['dorms']:>2} {yr:>5} {r['n_comps']:>4} | {fmt(r['m1']):>9} {fmt(r['m2']):>9} {fmt(r['m3']):>9} | {d2s:>8} {d3s:>8}")


# ============================================================
# DIFFERENCES SUMMARY
# ============================================================

print("\n" + "="*110)
print("DIFFERENCES SUMMARY")
print("="*110)

for method_key, label in [("m2", "IDW P33 (power=2)"), ("m3", "IDW P33 (power=1.5)")]:
    diffs = []
    for r in results:
        if r[method_key] and r["m1"]:
            diff = (r[method_key] - r["m1"]) / r["m1"] * 100
            diffs.append(diff)
    if diffs:
        avg = sum(diffs) / len(diffs)
        med = sorted(diffs)[len(diffs)//2]
        print(f"\n{label}:")
        print(f"  Mean: {avg:+.1f}%  Median: {med:+.1f}%  Min: {min(diffs):+.1f}%  Max: {max(diffs):+.1f}%")


# ============================================================
# DETAILED EXAMPLES
# ============================================================

print("\n" + "="*110)
print("DETAILED EXAMPLES — How weighting changes the result")
print("="*110)

for idx, r in enumerate(results):
    lat, lon = r["lat"], r["lon"]
    name = r["name"]
    year = r["year"]
    dorms = r["dorms"]
    
    comps = []
    for p in venta:
        dist = haversine_m(lat, lon, p["lat"], p["lon"])
        if dist <= 800:
            comps.append({
                "lat": p["lat"], "lon": p["lon"], "dist_m": dist,
                "valor_m2_adj": p["valor_m2_adj"], "dormitorios": p["dormitorios"],
                "m2": p["m2"], "year": p["year"],
            })
    
    # Same filtering
    filtered = [c for c in comps if abs((c["dormitorios"] or 2) - dorms) <= 1]
    if len(filtered) < 3:
        filtered = comps
    if year:
        year_min = year - 10
        year_max = year + 10
        age_filtered = [c for c in filtered if c['year'] and year_min <= c['year'] <= year_max]
        if len(age_filtered) >= 5:
            filtered = age_filtered
    
    filtered.sort(key=lambda x: x["dist_m"])
    
    # Split
    same_side = [c for c in filtered if not crosses_barrier(lat, lon, c["lat"], c["lon"], -32.965)]
    cross = [c for c in filtered if crosses_barrier(lat, lon, c["lat"], c["lon"], -32.965)]
    
    print(f"\n--- {name} (m2={r['m2']}, dorm={dorms}, year={int(year) if year else '?'}) ---")
    print(f"  Filtered comps: {len(filtered)} ({len(same_side)} same + {len(cross)} cross 27-Feb)")
    
    # Show top 10
    print(f"\n  {'#':>3} {'Dist':>6} {'P33':>8} {'D':>2} {'m2':>5} {'Year':>5} {'Side':>6} {'IDW-w':>10}")
    print(f"  {'-'*55}")
    
    for i, c in enumerate(filtered[:10]):
        side = "SAME" if not crosses_barrier(lat, lon, c["lat"], c["lon"], -32.965) else "CROSS"
        w = 1.0 / (c["dist_m"] ** 2)
        yr = int(c['year']) if c['year'] else "?"
        print(f"  {i+1:>3} {c['dist_m']:>5.0f}m ${c['valor_m2_adj']:>7.0f} {c['dormitorios']:>2} {c['m2']:>5.0f} {yr:>5} {side:>6} {w:>10.8f}")
    
    # Show how blend vs IDW work
    print(f"\n  Method comparison:")
    print(f"    Current (blend+penalty):")
    print(f"      Same-side P33: ${compute_percentil(33, [c['valor_m2_adj'] for c in same_side]):.0f}" if same_side else "      Same-side P33: N/A")
    if cross:
        print(f"      Cross P33:    ${compute_percentil(33, [c['valor_m2_adj'] for c in cross]):.0f}")
        print(f"      Blend:        ${r['m1_blend']:.0f}")
        print(f"      Penalty:      {r['m1_penalty']*100:.2f}%")
    print(f"      Final:        ${r['m1']:.0f}/m2")
    
    print(f"\n    IDW P33 (power=2):")
    # Show top 3 most influential comps
    iw = [(c["valor_m2_adj"], c["dist_m"], 1.0/(c["dist_m"]**2)) for c in filtered[:5]]
    total_w = sum(w for _, _, w in iw)
    print(f"      Top 3 most influential:")
    for i, (val, dist, w) in enumerate(iw[:3]):
        pct = w / total_w * 100
        print(f"        #{i+1}: ${val:.0f} at {dist:.0f}m (weight={pct:.1f}%)")
    print(f"      Final:        ${r['m2']:.0f}/m2")
