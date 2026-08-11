"""
Final valuation list: actual JSON values vs IDW methods.
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

with open("propiedades.json", "r", encoding="utf-8") as f:
    prop_data = json.load(f)
propiedades = prop_data.get("propiedades", prop_data) if isinstance(prop_data, dict) else prop_data


# ============================================================
# COMPUTE
# ============================================================

output = []

for prop in propiedades:
    name = prop.get("nombre", prop.get("direccion", "?"))
    lat = prop.get("lat")
    lon = prop.get("lon")
    prop_m2 = prop.get("m2_cubiertos", 0) or prop.get("m2", 0) or 0
    dorms = prop.get("dormitorios", 2) or 2
    year = prop.get("anio_construccion") or prop.get("antiquity")
    if year and year < 100:
        year = ANIO_ACTUAL - year
    addr = prop.get("direccion", "")
    
    # Actual valuation from JSON
    uv = prop.get("_ultima_valuacion", {})
    val_json = uv.get("valor_usd") or uv.get("manual_valor_usd") or uv.get("auto_valor_usd") or 0
    m2_base_json = uv.get("m2_base_venta") or 0
    comps_json = uv.get("comps") or 0
    fuente = uv.get("fuente", "?")
    vm2_json = val_json / prop_m2 if prop_m2 and val_json else m2_base_json
    
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
                "lat": p["lat"], "lon": p["lon"], "dist_m": dist,
                "valor_m2_adj": p["valor_m2_adj"], "dormitorios": p["dormitorios"],
                "m2": p["m2"], "year": p["year"],
            })
    
    # Filter: dorm ±1
    filtered = [c for c in comps if abs((c["dormitorios"] or 2) - dorms) <= 1]
    if len(filtered) < 3:
        filtered = comps
    
    # Filter: age ±10yr
    if year:
        year_min = year - 10
        year_max = year + 10
        age_filtered = [c for c in filtered if c['year'] and year_min <= c['year'] <= year_max]
        if len(age_filtered) >= 5:
            filtered = age_filtered
    
    # Split by 27-Feb
    same_side = [c for c in filtered if not crosses_barrier(lat, lon, c["lat"], c["lon"], -32.965)]
    cross = [c for c in filtered if crosses_barrier(lat, lon, c["lat"], c["lon"], -32.965)]
    
    # Method: Current (blend P33 + barrier + penalty)
    vm2_current = None
    if same_side:
        same_p33 = compute_percentil(33, [c["valor_m2_adj"] for c in same_side])
        if cross:
            cross_p33 = compute_percentil(33, [c["valor_m2_adj"] for c in cross])
            alpha = min(0.70, max(0.50, 0.50 + 0.02 * len(same_side)))
            blend = alpha * same_p33 + (1-alpha) * cross_p33
            penalty = (len(cross) / len(filtered)) * 0.03
            vm2_current = blend * (1 - penalty)
        else:
            vm2_current = same_p33
    
    # Method: IDW P33 (power=2)
    vm2_idw_p2 = idw_p33_weighted(filtered, dist_power=2)
    
    # Method: IDW P33 (power=1.5)
    vm2_idw_p15 = idw_p33_weighted(filtered, dist_power=1.5)
    
    # Value USD
    val_current = vm2_current * prop_m2 if vm2_current else None
    val_idw_p2 = vm2_idw_p2 * prop_m2 if vm2_idw_p2 else None
    val_idw_p15 = vm2_idw_p15 * prop_m2 if vm2_idw_p15 else None
    
    output.append({
        "name": name, "addr": addr, "m2": prop_m2, "dorms": dorms, "year": int(year) if year else None,
        "n_comps": len(filtered),
        "val_json": val_json, "vm2_json": vm2_json, "comps_json": comps_json, "fuente": fuente,
        "vm2_current": vm2_current, "val_current": val_current,
        "vm2_idw_p2": vm2_idw_p2, "val_idw_p2": val_idw_p2,
        "vm2_idw_p15": vm2_idw_p15, "val_idw_p15": val_idw_p15,
    })


# ============================================================
# PRINT
# ============================================================

def fmt_usd(v):
    if not v:
        return "N/A"
    if v >= 1000000:
        return "${:.2f}M".format(v)
    return "${:,.0f}".format(v)

def fmt_m2(v):
    if not v:
        return "N/A"
    return "${:.0f}".format(v)

print("="*130)
print("VALUACIONES REALES (JSON) vs SIMULACION (IDW)")
print("="*130)

print("")
print("  VALOR USD TOTAL")
print("")

header = "{:<20} {:<25} {:>5} {:>2} {:>5} | {:>12} {:>12} {:>12} {:>12} | {:>8} {:>8} {:>8}".format(
    "Propiedad", "Direccion", "m2", "D", "Year", "JSON (real)", "Current", "IDW-p2", "IDW-p1.5", "dIDWp2", "dIDWp15", "dCurr")
print(header)
print("-"*130)

for i, r in enumerate(output):
    yr = str(r['year']) if r['year'] else "?"
    
    d_idw2 = ((r['val_idw_p2'] - r['val_json']) / r['val_json'] * 100) if r['val_json'] and r['val_idw_p2'] else None
    d_idw15 = ((r['val_idw_p15'] - r['val_json']) / r['val_json'] * 100) if r['val_json'] and r['val_idw_p15'] else None
    d_curr = ((r['val_current'] - r['val_json']) / r['val_json'] * 100) if r['val_json'] and r['val_current'] else None
    
    d2s = "{:+.1f}%".format(d_idw2) if d_idw2 is not None else "N/A"
    d15s = "{:+.1f}%".format(d_idw15) if d_idw15 is not None else "N/A"
    dcs = "{:+.1f}%".format(d_curr) if d_curr is not None else "N/A"
    
    print("{:<20} {:<25} {:>5} {:>2} {:>5} | {:>12} {:>12} {:>12} {:>12} | {:>8} {:>8} {:>8}".format(
        r['name'], r['addr'][:25], "{:.0f}".format(r['m2']), r['dorms'], yr,
        fmt_usd(r['val_json']), fmt_usd(r['val_current']), fmt_usd(r['val_idw_p2']), fmt_usd(r['val_idw_p15']),
        d2s, d15s, dcs))


print("")
print("  VALOR por m2")
print("")

header2 = "{:<20} {:<25} {:>5} {:>2} {:>5} | {:>9} {:>9} {:>9} {:>9} | {:>8} {:>8} {:>8}".format(
    "Propiedad", "Direccion", "m2", "D", "Year", "JSON", "Current", "IDW-p2", "IDW-p1.5", "dIDWp2", "dIDWp15", "dCurr")
print(header2)
print("-"*120)

for i, r in enumerate(output):
    yr = str(r['year']) if r['year'] else "?"
    
    d_idw2 = ((r['vm2_idw_p2'] - r['vm2_json']) / r['vm2_json'] * 100) if r['vm2_json'] and r['vm2_idw_p2'] else None
    d_idw15 = ((r['vm2_idw_p15'] - r['vm2_json']) / r['vm2_json'] * 100) if r['vm2_json'] and r['vm2_idw_p15'] else None
    d_curr = ((r['vm2_current'] - r['vm2_json']) / r['vm2_json'] * 100) if r['vm2_json'] and r['vm2_current'] else None
    
    d2s = "{:+.1f}%".format(d_idw2) if d_idw2 is not None else "N/A"
    d15s = "{:+.1f}%".format(d_idw15) if d_idw15 is not None else "N/A"
    dcs = "{:+.1f}%".format(d_curr) if d_curr is not None else "N/A"
    
    print("{:<20} {:<25} {:>5} {:>2} {:>5} | {:>9} {:>9} {:>9} {:>9} | {:>8} {:>8} {:>8}".format(
        r['name'], r['addr'][:25], "{:.0f}".format(r['m2']), r['dorms'], yr,
        fmt_m2(r['vm2_json']), fmt_m2(r['vm2_current']), fmt_m2(r['vm2_idw_p2']), fmt_m2(r['vm2_idw_p15']),
        d2s, d15s, dcs))
