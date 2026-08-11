import json, os

sys_path = r'c:\Users\Gustavo\ingresos_familiares_st'
barreras_path = os.path.join(sys_path, 'barreras_rosario.json')
barreras_data = json.load(open(barreras_path, 'r', encoding='utf-8'))
barreras_features = barreras_data.get('features', [])

def intersecta_segmento(p1, p2, b1, b2):
    x1, y1 = p1 # lon, lat
    x2, y2 = p2
    bx1, by1 = b1
    bx2, by2 = b2
    
    dx_p = x2 - x1
    dy_p = y2 - y1
    dx_b = bx2 - bx1
    dy_b = by2 - by1
    
    denom = dy_p * dx_b - dx_p * dy_b
    if abs(denom) < 1e-12:
        return False
        
    dx1 = bx1 - x1
    dy1 = by1 - y1
    
    t = (dy1 * dx_b - dx1 * dy_b) / denom
    u = (dx_p * dy1 - dy_p * dx1) / denom
    
    return 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0

def detectar_barrera_cramer(lat_suj, lon_suj, lat_comp, lon_comp):
    p1 = (lon_suj, lat_suj)
    p2 = (lon_comp, lat_comp)
    for barrera in barreras_features:
        nombre = barrera.get('properties', {}).get('name', '?')
        coords = barrera.get('geometry', {}).get('coordinates', [])
        if not coords or len(coords) < 2: continue
        for i in range(len(coords) - 1):
            if intersecta_segmento(p1, p2, coords[i], coords[i+1]):
                return nombre
    return None

# Cochabamba 45: lat=-32.9611391, lon=-60.6264443
suj_lat, suj_lon = -32.9611391, -60.6264443

# Zeballos 300: lat=-32.95725, lon=-60.629467 (Mismo barrio, sin cruzar Pellegrini ni Avellaneda)
zeb_lat, zeb_lon = -32.95725, -60.629467

# Pellegrini 600: lat=-32.957, lon=-60.635 (Cruza Av. Pellegrini)
pel_lat, pel_lon = -32.957, -60.635

print("Zeballos 300 (mismo barrio):", detectar_barrera_cramer(suj_lat, suj_lon, zeb_lat, zeb_lon))
print("Pellegrini 600 (cruza Pellegrini):", detectar_barrera_cramer(suj_lat, suj_lon, pel_lat, pel_lon))
