"""
Replicate actual valuation logic and compare with IDW.
Uses the REAL functions from the codebase.
"""
import json
import math
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.cluster_filters import (
    filtrar_por_fecha,
    separar_por_barreras,
    calcular_percentil,
    calcular_blend_p33,
    _calcular_cv,
)
from parsers.mercado_inmobiliario import (
    _precio_ajustado,
    _computar_vm2_core,
    normalizar_zona,
)
from parsers.time_adjustment import calcular_ct, meses_desde, es_nuevo, get_natural_window_dias
from parsers.zonas_manager import resolver_macrozona

ANIO_ACTUAL = datetime.now().year


def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def calcular_distancia_km(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))


# ============================================================
# LOAD DATA
# ============================================================

print("Loading data...")

with open("cache_scraping.json", "r", encoding="utf-8") as f:
    cache = json.load(f)

with open("propiedades.json", "r", encoding="utf-8") as f:
    prop_data = json.load(f)
propiedades = prop_data.get("propiedades", prop_data) if isinstance(prop_data, dict) else prop_data

ventas = [p for p in cache.get("propiedades", []) if p.get("operacion") == "venta"]

print(f"Loaded {len(ventas)} venta properties")

# ============================================================
# REAL VALUATION (replicating actual logic)
# ============================================================

print("\n" + "="*120)
print("REAL VALUATION vs IDW COMPARISON")
print("="*120)

results = []

for prop in propiedades:
    name = prop.get("nombre", "?")
    lat = prop.get("lat")
    lon = prop.get("lon")
    prop_m2 = prop.get("m2_cubiertos", 0) or prop.get("m2", 0) or 0
    dorms = prop.get("dormitorios", 2) or 2
    anio_const = prop.get("anio_construccion") or (ANIO_ACTUAL - prop.get("antiguedad", 0))
    zona_txt = prop.get("zona", "centro")
    
    # Actual JSON valuation
    uv = prop.get("_ultima_valuacion", {})
    val_json = uv.get("valor_usd") or uv.get("manual_valor_usd") or uv.get("auto_valor_usd") or 0
    m2_base_json = uv.get("m2_base_venta") or 0
    comps_json = uv.get("comps") or 0
    fuente = uv.get("fuente", "?")
    vm2_json = val_json / prop_m2 if prop_m2 and val_json else m2_base_json
    
    if lat is None or lon is None:
        continue
    
    # Resolve macrozona
    macrozona_id = None
    try:
        pseudo_prop = {'zona': zona_txt or '', 'lat': lat, 'lon': lon}
        mz_info = resolver_macrozona(pseudo_prop)
        macrozona_id = mz_info.get('macrozona_id')
    except:
        pass
    
    # Find comparables within 800m (same as actual system)
    props_geo = []
    for p in ventas:
        p_lat = p.get("lat")
        p_lon = p.get("lon")
        if not p_lat or not p_lon:
            continue
        try:
            dist = calcular_distancia_km(lat, lon, p_lat, p_lon)
            if dist <= 0.8:  # 800m
                props_geo.append(p)
        except:
            continue
    
    # Filter by dorms (with flex tolerance)
    props_filtered = [p for p in props_geo if p.get("dormitorios") == dorms]
    if len(props_filtered) < 3:
        props_filtered = props_geo
    
    # Filter by valor_m2 > 0
    props_filtered = [p for p in props_filtered if p.get("valor_m2", 0) > 0]
    
    # Apply time adjustment (CT)
    natural_dias = get_natural_window_dias()
    for p in props_filtered:
        dc = p.get("date_created", "")
        if dc:
            try:
                m = meses_desde(dc)
                if m is not None and m > natural_dias / 30:
                    p["_time_adjustment"] = calcular_ct(m, es_nuevo(p), macrozona_id=macrozona_id)
            except:
                pass
    
    # Apply barrier separation
    same_side = []
    cross_soft = []
    try:
        from parsers.location_engine import check_barrier_crossing, cargar_barreras
        barreras = cargar_barreras()
        
        barreras_result = separar_por_barreras(
            props=props_filtered,
            lat_ref=lat,
            lon_ref=lon,
            check_barrier_fn=lambda p1, p2: check_barrier_crossing(p1, p2, barreras),
            zona_ref=normalizar_zona(zona_txt)
        )
        
        same_side = barreras_result["same_side"]
        cross_soft = barreras_result["cross_soft"]
        
        for p in same_side:
            p["_cross_soft"] = False
        for p in cross_soft:
            p["_cross_soft"] = True
    except Exception as e:
        same_side = props_filtered
        cross_soft = []
    
    # Compute REAL vm2 using _computar_vm2_core
    all_comps = same_side + cross_soft
    vm2_real, n_same, n_cross, pct_same, pct_cross = _computar_vm2_core(
        all_comps, 33, apply_barrier=True, alpha=None,
        macrozona_id=macrozona_id, ancla_id=None, dormitorios_sujeto=dorms
    )
    
    val_real = vm2_real * prop_m2 if vm2_real else None
    
    # Compute IDW vm2 (same comps, IDW weighting)
    def idw_p33(comps_list, power=2):
        if not comps_list:
            return None
        precio_m2_list = []
        weights = []
        for c in comps_list:
            precio = c.get("valor_m2", 0)
            ta = c.get("_time_adjustment", 1.0)
            precio_aj = precio * ta
            p_lat = c.get("lat")
            p_lon = c.get("lon")
            if p_lat and p_lon:
                dist = haversine_m(lat, lon, p_lat, p_lon)
                w = 1.0 / (max(dist, 1) ** power)
            else:
                w = 1.0
            precio_m2_list.append(precio_aj)
            weights.append(w)
        
        # Sort by price
        paired = sorted(zip(precio_m2_list, weights))
        precio_m2_sorted = [p for p, w in paired]
        weights_sorted = [w for p, w in paired]
        
        total_w = sum(weights_sorted)
        target = total_w * 0.33
        cum_w = 0
        for val, w in zip(precio_m2_sorted, weights_sorted):
            cum_w += w
            if cum_w >= target:
                return val
        return precio_m2_sorted[-1] if precio_m2_sorted else None
    
    vm2_idw_p2 = idw_p33(all_comps, power=2)
    vm2_idw_p15 = idw_p33(all_comps, power=1.5)
    
    val_idw_p2 = vm2_idw_p2 * prop_m2 if vm2_idw_p2 else None
    val_idw_p15 = vm2_idw_p15 * prop_m2 if vm2_idw_p15 else None
    
    results.append({
        "name": name, "m2": prop_m2, "dorms": dorms, "year": anio_const,
        "n_same": n_same, "n_cross": n_cross,
        "val_json": val_json, "vm2_json": vm2_json,
        "vm2_real": vm2_real, "val_real": val_real,
        "vm2_idw_p2": vm2_idw_p2, "val_idw_p2": val_idw_p2,
        "vm2_idw_p15": vm2_idw_p15, "val_idw_p15": val_idw_p15,
        "fuente": fuente,
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

print("\n  VALOR USD TOTAL")
print("")

header = "{:<20} {:>5} {:>2} {:>4} | {:>12} {:>12} {:>12} {:>12} | {:>8} {:>8} {:>8}".format(
    "Propiedad", "m2", "D", "Year", "JSON", "Real", "IDW-p2", "IDW-p1.5", "dIDWp2", "dIDWp15", "dReal")
print(header)
print("-"*120)

for i, r in enumerate(results):
    yr = str(r['year']) if r['year'] else "?"
    
    d_idw2 = ((r['val_idw_p2'] - r['val_json']) / r['val_json'] * 100) if r['val_json'] and r['val_idw_p2'] else None
    d_idw15 = ((r['val_idw_p15'] - r['val_json']) / r['val_json'] * 100) if r['val_json'] and r['val_idw_p15'] else None
    d_real = ((r['val_real'] - r['val_json']) / r['val_json'] * 100) if r['val_json'] and r['val_real'] else None
    
    d2s = "{:+.1f}%".format(d_idw2) if d_idw2 is not None else "N/A"
    d15s = "{:+.1f}%".format(d_idw15) if d_idw15 is not None else "N/A"
    drs = "{:+.1f}%".format(d_real) if d_real is not None else "N/A"
    
    print("{:<20} {:>5} {:>2} {:>4} | {:>12} {:>12} {:>12} {:>12} | {:>8} {:>8} {:>8}".format(
        r['name'], "{:.0f}".format(r['m2']), r['dorms'], yr,
        fmt_usd(r['val_json']), fmt_usd(r['val_real']), fmt_usd(r['val_idw_p2']), fmt_usd(r['val_idw_p15']),
        d2s, d15s, drs))


print("\n  VALOR por m2")
print("")

header2 = "{:<20} {:>5} {:>2} {:>4} | {:>9} {:>9} {:>9} {:>9} | {:>8} {:>8} {:>8}".format(
    "Propiedad", "m2", "D", "Year", "JSON", "Real", "IDW-p2", "IDW-p1.5", "dIDWp2", "dIDWp15", "dReal")
print(header2)
print("-"*110)

for i, r in enumerate(results):
    yr = str(r['year']) if r['year'] else "?"
    
    d_idw2 = ((r['vm2_idw_p2'] - r['vm2_json']) / r['vm2_json'] * 100) if r['vm2_json'] and r['vm2_idw_p2'] else None
    d_idw15 = ((r['vm2_idw_p15'] - r['vm2_json']) / r['vm2_json'] * 100) if r['vm2_json'] and r['vm2_idw_p15'] else None
    d_real = ((r['vm2_real'] - r['vm2_json']) / r['vm2_json'] * 100) if r['vm2_json'] and r['vm2_real'] else None
    
    d2s = "{:+.1f}%".format(d_idw2) if d_idw2 is not None else "N/A"
    d15s = "{:+.1f}%".format(d_idw15) if d_idw15 is not None else "N/A"
    drs = "{:+.1f}%".format(d_real) if d_real is not None else "N/A"
    
    print("{:<20} {:>5} {:>2} {:>4} | {:>9} {:>9} {:>9} {:>9} | {:>8} {:>8} {:>8}".format(
        r['name'], "{:.0f}".format(r['m2']), r['dorms'], yr,
        fmt_m2(r['vm2_json']), fmt_m2(r['vm2_real']), fmt_m2(r['vm2_idw_p2']), fmt_m2(r['vm2_idw_p15']),
        d2s, d15s, drs))
