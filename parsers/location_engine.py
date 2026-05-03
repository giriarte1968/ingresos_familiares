import math
import json
import os
import numpy as np
from sklearn.cluster import DBSCAN

def cargar_anclas(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'anclas_rosario_v3_grid.json')
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

def generar_nodos_dinamicos(props, eps_meters=200, min_samples=8, target_year=None):
    """
    Genera nodos de valoración basados en clustering DBSCAN.
    Prioriza propiedades con datos de edad si target_year es provisto.
    """
    coords_all = np.array([[p['lat'], p['lon']] for p in props if p.get('lat') and p.get('lon')])
    if len(coords_all) == 0:
        return []
    
    # Separar propiedades con y sin edad (solo las que tienen coordenadas válidas)
    props_with_year = [p for p in props if p.get('anio_construccion') is not None and p.get('lat') and p.get('lon')]
    
    def run_dbscan(subset_props):
        coords = np.array([[p['lat'], p['lon']] for p in subset_props if p.get('lat') and p.get('lon')])
        if len(coords) < min_samples:
            return None, None
        eps_deg = eps_meters / 111000.0
        db = DBSCAN(eps=eps_deg, min_samples=min_samples).fit(coords)
        return db.labels_, coords

    labels_year, _ = run_dbscan(props_with_year)
    nodos = []
    
    if labels_year is not None:
        unique_labels = set(labels_year)
        for label in unique_labels:
            if label == -1: continue
            cluster_indices = np.where(labels_year == label)[0]
            cluster_props = [props_with_year[i] for i in cluster_indices]
            lats = [p['lat'] for p in cluster_props]
            lons = [p['lon'] for p in cluster_props]
            valores = [v for v in [p.get('valor_m2') for p in cluster_props] if isinstance(v, (int, float)) and v > 0]
            if not valores: continue
            
            # MAD Outlier Filtering (replaces IQR for asymmetric distributions)
            if len(valores) >= 3:
                mediana_val = np.median(valores)
                # Manual MAD calculation (more portable than scipy)
                mad = np.median(np.abs(np.array(valores) - mediana_val))
                lower = mediana_val - 3 * mad
                upper = mediana_val + 3 * mad
                valores_filtrados = [v for v in valores if lower <= v <= upper]
                # If too many removed, use adaptive IQR
                if len(valores_filtrados) >= 3:
                    valores = valores_filtrados
                else:
                    # Fallback: adaptive IQR (less aggressive than before)
                    lower_robust = mediana_val * 0.55
                    upper_robust = mediana_val * 1.85
                    valores_filtrados2 = [v for v in valores if lower_robust <= v <= upper_robust]
                    if len(valores_filtrados2) >= 3:
                        valores = valores_filtrados2
            
            nodos.append({
                'id': f'node_year_{label}',
                'lat': np.mean(lats),
                'lon': np.mean(lons),
                'usd_m2': float(np.median(valores)),
                'muestras': len(valores),
                'qualified': True
            })
    
    if len(nodos) < 3:
        # Filter props to only include those with valid coordinates
        props_filtered = [p for p in props if p.get('lat') and p.get('lon')]
        labels_all, _ = run_dbscan(props_filtered)
        if labels_all is not None:
            unique_labels = set(labels_all)
            for label in unique_labels:
                if label == -1: continue
                cluster_indices = np.where(labels_all == label)[0]
                cluster_props = [props_filtered[i] for i in cluster_indices]
                lats = [p['lat'] for p in cluster_props]
                lons = [p['lon'] for p in cluster_props]
                valores = [v for v in [p.get('valor_m2') for p in cluster_props] if isinstance(v, (int, float)) and v > 0]
                if not valores: continue
                
                # MAD Outlier Filtering
                if len(valores) >= 3:
                    mediana_val = np.median(valores)
                    mad = np.median(np.abs(np.array(valores) - mediana_val))
                    lower = mediana_val - 3 * mad
                    upper = mediana_val + 3 * mad
                    valores_filtrados = [v for v in valores if lower <= v <= upper]
                    # If too many removed, use adaptive IQR
                    if len(valores_filtrados) >= 3:
                        valores = valores_filtrados
                    else:
                        # Fallback: adaptive IQR (less aggressive)
                        lower_robust = mediana_val * 0.55
                        upper_robust = mediana_val * 1.85
                        valores_filtrados2 = [v for v in valores if lower_robust <= v <= upper_robust]
                        if len(valores_filtrados2) >= 3:
                            valores = valores_filtrados2
                
                nodos.append({
                    'id': f'node_gen_{label}',
                    'lat': np.mean(lats),
                    'lon': np.mean(lons),
                    'usd_m2': float(np.median(valores)),
                    'muestras': len(valores),
                    'qualified': False
                })
    return nodos

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
        if b.get('properties', {}).get('barrier_type') != 'hard':
            continue
        coords = b.get('geometry', {}).get('coordinates', [])
        for i in range(len(coords) - 1):
            if _intersect(p1, p2, coords[i], coords[i+1]):
                return True
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
            if check_barrier_crossing((lon, lat), (n['lon'], n['lat']), barriers):
                weight *= 0.2
                barrier_penalty = 0.2
        
        # Cap de peso máximo por nodo individual para evitar secuestro de la valuación
        # El peso se normaliza al final, pero limitamos la contribución relativa inicial
        # Nota: el peso real es weight / total_weight. Para limitar esto, 
        # aplicamos una función de saturación o limitamos el weight.
        weight = min(weight, MAX_PESO_NODO)
        
        weighted_vals.append(n['usd_m2'] * weight)
        total_weight += weight
        influencing_nodes.append({
            'id': n['id'],
            'lat': n['lat'],
            'lon': n['lon'],
            'dist_m': d_m,
            'weight': weight,
            'value': n['usd_m2'],
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