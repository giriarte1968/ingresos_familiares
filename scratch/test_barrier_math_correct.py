import sys, os, json
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.location_engine import cargar_barreras

# Load vector barriers
geojson_path = os.path.join(r'c:\Users\Gustavo\ingresos_familiares_st', 'data', 'rosario_barriers_vectors.geojson')
geojson_data = json.load(open(geojson_path, 'r', encoding='utf-8'))
barreras_features = geojson_data.get('features', [])

def detectar_barrera_vector_correct(lat_suj, lon_suj, lat_comp, lon_comp):
    if not lat_suj or not lon_suj or not lat_comp or not lon_comp:
        return None
    for barrera in barreras_features:
        props_b = barrera.get('properties', {})
        nombre = props_b.get('name', '?')
        geom = barrera.get('geometry', {})
        coords = geom.get('coordinates', [])
        if not coords or len(coords) < 2: continue
        for i in range(len(coords) - 1):
            bx1, by1 = coords[i] # bx=lon, by=lat
            bx2, by2 = coords[i+1]
            dx_p = lon_comp - lon_suj
            dy_p = lat_comp - lat_suj
            dx_b = bx2 - bx1
            dy_b = by2 - by1
            denom = dy_p * dx_b - dx_p * dy_b
            if abs(denom) < 1e-12: continue
            t = ((bx1 - lon_suj) * dy_b - (by1 - lat_suj) * dx_b) / denom
            u = ((bx1 - lon_suj) * dy_p - (by1 - lat_suj) * dx_p) / denom
            if 0.0 <= t <= 1.0 and 0.0 <= u <= 1.0:
                return nombre
    return None

# Cochabamba 45: lat=-32.9611391, lon=-60.6264443
suj_lat, suj_lon = -32.9611391, -60.6264443

# Zeballos 300: lat=-32.95725, lon=-60.629467
zeb_lat, zeb_lon = -32.95725, -60.629467

# Pellegrini 600: lat=-32.957, lon=-60.635
pel_lat, pel_lon = -32.957, -60.635

print("Zeballos 300 (500m away in same neighborhood):", detectar_barrera_vector_correct(suj_lat, suj_lon, zeb_lat, zeb_lon))
print("Pellegrini 600 (across Pellegrini barrier):", detectar_barrera_vector_correct(suj_lat, suj_lon, pel_lat, pel_lon))
