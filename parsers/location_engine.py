import math
import json
import os

def cargar_anclas(path=None):
    if path is None:
        try:
            from parsers.motor_vpp_core import load_anclas_config
            cfg = load_anclas_config()
            rel = cfg.get('runtime', {}).get('active_anchor_file', 'data/anclas_rosario_v5_1_limpio.json')
            path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), rel)
        except Exception:
            path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'anclas_rosario_v5_1_limpio.json')
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("anclas", data)  # support both formats

def cargar_barreras(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'barreras_rosario.json')
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("features", [])

_precios_oficiales_cache = None

def cargar_precios_oficiales(path=None):
    global _precios_oficiales_cache
    if _precios_oficiales_cache is not None and path is None:
        return _precios_oficiales_cache
    if path is None:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'precios_oficiales_rosario.json')
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    _precios_oficiales_cache = data
    return data

def obtener_precio_oficial(zona_texto, dormitorios=None):
    data = cargar_precios_oficiales()
    if not data or "zonas" not in data:
        return None
    zona_lower = zona_texto.lower().strip() if zona_texto else ""
    zonas = data["zonas"]
    zona_match = None
    for key, zdata in zonas.items():
        if key.lower() == zona_lower or zdata.get("nombre", "").lower() == zona_lower:
            zona_match = zdata
            break
    if not zona_match:
        for key, zdata in zonas.items():
            if zona_lower in key.lower() or key.lower() in zona_lower:
                zona_match = zdata
                break
    if not zona_match:
        return None
    if dormitorios is not None and "por_dormitorio" in zona_match:
        dorm_key = f"{dormitorios}d" if dormitorios <= 4 else "4d"
        if dorm_key in zona_match["por_dormitorio"]:
            return {
                "usd_m2": zona_match["por_dormitorio"][dorm_key],
                "fuente": zona_match.get("fuentes", ["desconocida"]),
                "fecha": data.get("fecha_generacion", ""),
                "zona": zona_match.get("nombre", zona_texto),
                "confianza": zona_match.get("confianza", "estimada"),
            }
    return {
        "usd_m2": zona_match.get("general", 0),
        "fuente": zona_match.get("fuentes", ["desconocida"]),
        "fecha": data.get("fecha_generacion", ""),
        "zona": zona_match.get("nombre", zona_texto),
        "confianza": zona_match.get("confianza", "estimada"),
    }

def distancia(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def _intersect(p1, p2, p3, p4):
    def ccw(A, B, C):
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
    return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)

def check_barrier_crossing(p1, p2, barriers):
    for b in barriers:
        props = b.get('properties', {})
        bt = props.get('barrier_type')
        if not bt:
            continue
        coords = b.get('geometry', {}).get('coordinates', [])
        for i in range(len(coords) - 1):
            if _intersect(p1, p2, coords[i], coords[i+1]):
                return bt  # 'hard' o 'soft'
    return False

def calcular_precio_m2(lat, lon, nodos, barriers=None, radio_km=1.0, lambda_val=0.012):
    if not nodos: return None, None
    weighted_vals = []
    total_weight = 0
    influencing_nodes = []
    MAX_PESO_NODO = 0.60
    for n in nodos:
        if n.get('usd_m2') is None:
            continue
        d_km = distancia(lat, lon, n['lat'], n['lon'])
        if d_km > radio_km: continue
        d_m = d_km * 1000
        weight = math.exp(-lambda_val * d_m)
        
        barrier_penalty = 1.0
        if barriers:
            cruza = check_barrier_crossing((lon, lat), (n['lon'], n['lat']), barriers)
            if cruza == 'hard':
                weight *= 0.20  # 80% penalty for railways
                barrier_penalty = 0.20
            elif cruza == 'soft':
                weight *= 0.90  # 10% penalty for avenues
                barrier_penalty = 0.90
        
        # Cap de peso máximo por nodo individual para evitar secuestro de la valuación
        # El peso se normaliza al final, pero limitamos la contribución relativa inicial
        # Nota: el peso real es weight / total_weight. Para limitar esto, 
        # aplicamos una función de saturación o limitamos el weight.
        weight = min(weight, MAX_PESO_NODO)
        
        anchor_val = n['usd_m2']
        weighted_vals.append(anchor_val * weight)
        total_weight += weight
        influencing_nodes.append({
            'id': n['id'],
            'lat': n['lat'],
            'lon': n['lon'],
            'dist_m': d_m,
            'weight': weight,
            'value': anchor_val,
            'barrier': barrier_penalty < 1.0,
            'qualified': n.get('qualified', False),
            'muestras': n.get('muestras', 1)
        })
    if total_weight == 0:
        return None, None
    
    # Mínimo de nodos para resultado confiable
    if len(influencing_nodes) < 5:
        return None, None

    final_val = sum(weighted_vals) / total_weight
    n_propiedades = sum(n.get('muestras', 1) for n in influencing_nodes)
    metadata = {
        'resolution': 'GEO',
        'nodes': influencing_nodes,
        'total_weight': total_weight,
        'n_propiedades': n_propiedades
    }
    return final_val, metadata

def estimar_confianza(lat, lon, anclas, radio_km=1.0):
    if not anclas: return "BAJA"
    distancias = []
    for a in anclas:
        d = distancia(lat, lon, a["lat"], a["lon"])
        if d <= radio_km:
            distancias.append(d)
    if not distancias: return "BAJA"
    dist_min = min(distancias)
    if dist_min < 0.2: return "ALTA"
    elif dist_min < 0.6: return "MEDIA"
    else: return "BAJA"

def get_ancla_mas_cercana(lat, lon, anclas):
    if not anclas: return None
    min_dist = float('inf')
    ancla_cercana = None
    for a in anclas:
        d = distancia(lat, lon, a["lat"], a["lon"])
        if d < min_dist:
            min_dist = d
            ancla_cercana = a
    return ancla_cercana