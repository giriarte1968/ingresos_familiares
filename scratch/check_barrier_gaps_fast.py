import json, sys, os, math

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.zonas_manager import resolver_macrozona

with open('barreras_rosario.json', 'r', encoding='utf-8') as f:
    barreras_data = json.load(f)

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def dist_punto_segmento_m(px, py, x1, y1, x2, y2):
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    return haversine_m(py, px, my, mx)

def get_closest_segment_side(px, py, coords):
    min_d = 1e9
    best_cp = 0
    for i in range(len(coords) - 1):
        x1, y1 = coords[i]
        x2, y2 = coords[i+1]
        d = dist_punto_segmento_m(px, py, x1, y1, x2, y2)
        if d < min_d:
            min_d = d
            best_cp = (x2 - x1) * (py - y1) - (y2 - y1) * (px - x1)
    return ('LEFT' if best_cp >= 0 else 'RIGHT'), min_d

def pct(l, p):
    if not l: return 0
    s = sorted(l)
    return s[int(len(s)*p/100)]

ventas_raw = [p for p in cache['propiedades']
              if p.get('operacion') == 'venta'
              and 200 < p.get('valor_m2', 0) < 10000
              and p.get('lat') and p.get('lon')]

barreras_features = barreras_data.get('features', [])
measured_gaps = []
mz_gaps = {}

for barrera in barreras_features:
    props_b = barrera.get('properties', {})
    nombre = props_b.get('name', '?')
    geom = barrera.get('geometry', {})
    coords = geom.get('coordinates', [])
    if not coords or len(coords) < 2: continue
    
    lado_left, lado_right = [], []
    for p in ventas_raw:
        try:
            plat, plon = float(p['lat']), float(p['lon'])
        except: continue
        vm2 = p.get('valor_m2', 0)
        if vm2 <= 0: continue
        side, dist_m = get_closest_segment_side(plon, plat, coords)
        if dist_m <= 300:
            (lado_left if side == 'LEFT' else lado_right).append(vm2)
            
    if len(lado_left) >= 5 and len(lado_right) >= 5:
        p50_L = pct(lado_left, 50)
        p50_R = pct(lado_right, 50)
        if p50_L > 0 and p50_R > 0:
            gap = abs(p50_L - p50_R) / max(p50_L, p50_R)
            # Resolve macrozone at midpoint
            mid_lon, mid_lat = coords[len(coords)//2]
            mz_res = resolver_macrozona({'lat': mid_lat, 'lon': mid_lon})
            mz_id = mz_res.get('macrozona_id') if isinstance(mz_res, dict) else 'macrocentro'
            
            measured_gaps.append(gap)
            if mz_id not in mz_gaps: mz_gaps[mz_id] = []
            mz_gaps[mz_id].append(gap)
            print(f"Barrera: {nombre:<30} | Macrozona: {mz_id:<16} | Measured Gap: {gap*100:.2f}%")

print("=" * 80)
print(f"Mediana empirica GLOBAL del gap de barreras: {pct(measured_gaps, 50)*100:.2f}%")
for mz, g_list in mz_gaps.items():
    print(f"Macrozona: {mz:<18} | Mediana Empirica: {pct(g_list, 50)*100:.2f}% ({len(g_list)} barreras)")
