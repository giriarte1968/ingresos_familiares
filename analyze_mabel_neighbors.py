
import json
import math

def distance(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

# Mabel's Data
mabel = {
    'lat': -32.9541101,
    'lon': -60.6316406,
    'm2': 44.4,
    'dorms': 1,
    'age': 26,
    'tipo': 'departamento',
    'op': 'venta'
}

cache_path = r'C:\Users\Gustavo\ingresos_familiares_st\cache_scraping.json'
with open(cache_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

props = data.get('propiedades', [])
candidates = []

for p in props:
    lat, lon = p.get('lat'), p.get('lon')
    if not lat or not lon: continue
    
    # We only care about properties that actually passed the filters for Mabel
    # (Distance <= 1km, Operation = venta, Type = departamento)
    d = distance(mabel['lat'], mabel['lon'], lat, lon)
    if d <= 1.0:
        if p.get('operacion') == mabel['op']:
            # Flexible type check
            p_tipo = p.get('tipo')
            tipo_ok = (not p_tipo) or ('depto' in str(p_tipo).lower() or 'departamento' in str(p_tipo).lower() or 'ph' in str(p_tipo).lower())
            
            if tipo_ok and p.get('valor_m2', 0) > 0:
                candidates.append({
                    'dist_m': d * 1000,
                    'm2': p.get('m2', 0),
                    'dorms': p.get('dormitorios', 1),
                    'val_m2': p.get('valor_m2', 0),
                    'addr': p.get('direccion', 'S/N'),
                    'fuente': p.get('fuente', 'unknown'),
                    'lat': lat,
                    'lon': lon
                })

# Sort by distance and take top 8 (matching the UI)
candidates.sort(key=lambda x: x['dist_m'])
top_8 = candidates[:8]

print(f"{'ID':<5} | {'Dist(m)':<10} | {'m2':<8} | {'Dorms':<8} | {'USD/m2':<10} | {'Direccion'}")
print("-" * 80)
for i, p in enumerate(top_8):
    print(f"{i+1:<5} | {p['dist_m']:<10.1f} | {p['m2']:<8.1f} | {p['dorms']:<8} | {p['val_m2']:<10.1f} | {p['addr']}")
