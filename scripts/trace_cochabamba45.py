#!/usr/bin/env python3
"""Trace Cochabamba 45 valuation step by step with both barrier sets."""
import json, sys, math
sys.path.insert(0, '.')

from parsers.cluster_filters import calcular_percentil, calcular_blend_p33
from parsers.mercado_inmobiliario import _precio_ajustado

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def load_barriers(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)['features']

def check_crossing(lat1, lon1, lat2, lon2, barriers):
    """Check if line between two points crosses any barrier."""
    def _ccw(A, B, C):
        return (C[1]-A[1]) * (B[0]-A[0]) > (B[1]-A[1]) * (C[0]-A[0])
    def _intersect(p1, p2, p3, p4):
        if (_ccw(p1,p3,p4) == _ccw(p2,p3,p4)) or (_ccw(p1,p2,p3) == _ccw(p1,p2,p4)):
            return False
        return True
    for b in barriers:
        bt = b.get('properties',{}).get('barrier_type')
        if not bt:
            continue
        coords = b.get('geometry',{}).get('coordinates',[])
        for i in range(len(coords)-1):
            if _intersect((lon1,lat1), (lon2,lat2), coords[i], coords[i+1]):
                return bt
    return False

# Load data
with open('propiedades.json','r',encoding='utf-8') as f:
    props = json.load(f)['propiedades']
c45 = [p for p in props if p['id']==10][0]
lat_ref = float(c45['lat'])
lon_ref = float(c45['lon'])
macrozona = 'centro_premium'
ancla_id = None
dorm_suj = c45.get('dormitorios', 2)

# Load cache comps
with open('cache_scraping.json','r',encoding='utf-8') as f:
    cache = json.load(f)
all_props = cache['propiedades']

# Load both barrier sets
barreras_orig = load_barriers('barreras_rosario.json')
barreras_corr = load_barriers('barreras_rosario_corrected.json')

# Find comps within 500m with valid data
comps_raw = []
for p in all_props:
    if p.get('operacion') != 'venta': continue
    if p.get('valor_m2', 0) <= 0: continue
    if not p.get('lat') or not p.get('lon'): continue
    try:
        plat = float(p['lat'])
        plon = float(p['lon'])
    except:
        continue
    dist = haversine_m(lat_ref, lon_ref, plat, plon)
    if dist > 500: continue
    comps_raw.append({
        'direccion': p.get('direccion', '?'),
        'lat': plat,
        'lon': plon,
        'precio_m2': float(p['valor_m2']),
        'dormitorios': int(float(p.get('dormitorios', 2))),
        'm2_cubiertos': float(p.get('m2_cubiertos', 50)),
        'dist_m': dist,
    })

print(f"Total comps within 500m: {len(comps_raw)}")
print()

# For each barrier set, classify and compute
for label, barreras in [("ORIGINAL", barreras_orig), ("CORRECTED", barreras_corr)]:
    print(f"{'='*70}")
    print(f"BARRIER SET: {label}")
    print(f"{'='*70}")
    
    same_comps = []
    cross_comps = []
    
    for c in comps_raw:
        cross_type = check_crossing(lat_ref, lon_ref, c['lat'], c['lon'], barreras)
        adj_price = _precio_ajustado(c, macrozona, ancla_id=ancla_id, dormitorios_sujeto=dorm_suj)
        
        entry = {**c, '_cross_soft': bool(cross_type), '_adj_price': adj_price, '_cross_type': cross_type}
        if cross_type:
            cross_comps.append(entry)
        else:
            same_comps.append(entry)
    
    same_prices = sorted([c['_adj_price'] for c in same_comps])
    cross_prices = sorted([c['_adj_price'] for c in cross_comps])
    
    n_same = len(same_prices)
    n_cross = len(cross_prices)
    n_total = n_same + n_cross
    
    pct_same = calcular_percentil(same_prices, 33) if same_prices else None
    pct_cross = calcular_percentil(cross_prices, 33) if cross_prices else None
    
    # Alpha
    if n_same >= 15: alpha = 0.70
    elif n_same >= 8: alpha = 0.60
    elif n_same >= 5: alpha = 0.55
    else: alpha = 0.50
    
    # Blend
    vm2 = calcular_blend_p33(pct_same, pct_cross, alpha=alpha)
    if vm2 is None:
        vm2 = 0.0
    
    # Barrier penalty
    barrier_pct = 0.0
    if n_cross > 0:
        barrier_pct = (n_cross / n_total) * 0.03
        vm2_final = round(vm2 * (1 - barrier_pct), 2)
    else:
        vm2_final = round(vm2, 2)
    
    m2eq = c45.get('m2_cubiertos', 50) + c45.get('m2_descubiertos', 0) * 0.5
    if m2eq <= 0: m2eq = 50
    
    print(f"  n_same={n_same}, n_cross={n_cross}, n_total={n_total}")
    print(f"  P33_same={pct_same:.2f}, P33_cross={pct_cross:.2f}")
    print(f"  Gap = (cross-same)/same = {(pct_cross-pct_same)/pct_same*100:.1f}%")
    print(f"  Alpha={alpha} (n_same={n_same})")
    print(f"  Blend: {alpha}×{pct_same:.2f} + {1-alpha}×{pct_cross:.2f} = {vm2:.2f}")
    print(f"  Barrier penalty: ({n_cross}/{n_total})×0.03 = {barrier_pct:.6f}")
    print(f"  vm2_final = {vm2:.2f} × (1-{barrier_pct:.6f}) = {vm2_final:.2f}")
    print(f"  Valor = {vm2_final:.2f} × {m2eq:.1f} = ${vm2_final * m2eq:,.0f}")
    print()
    
    # Show cross comps
    if cross_comps:
        print(f"  Cross comps ({len(cross_comps)}):")
        for c in sorted(cross_comps, key=lambda x: x['_adj_price']):
            print(f"    {c['direccion']:40} dist={c['dist_m']:.0f}m adj=${c['_adj_price']:.0f}")
    print()

print("COMPARISON:")
print(f"  Original barriers: $81,803")
print(f"  Corrected barriers: $90,120")
print(f"  Difference: +$8,317 (+10.2%)")
