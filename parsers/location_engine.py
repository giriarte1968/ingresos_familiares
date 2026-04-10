import math
import json
import os


def cargar_anclas(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'anclas_rosario.json')
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        return data.get("anclas", data)  # support both formats


def distancia(lat1, lon1, lat2, lon2):
    """Haversine formula for distance in km."""
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def calcular_precio_m2(lat, lon, anclas, radio_km=2.0):
    """
    IDW cuadrático - calcula precio m2 desde múltiples anclas.
    Solo considera anclas dentro del radio.
    """
    valores = []
    pesos = []
    
    for a in anclas:
        d = distancia(lat, lon, a["lat"], a["lon"])
        
        if d > radio_km:
            continue
        
        # IDW cuadrático: peso = 1 / (d^2 + 0.1)
        peso = 1 / (d**2 + 0.1)
        
        valores.append(a["usd_m2"] * peso)
        pesos.append(peso)
    
    if not valores:
        return None  # No hay anclas en rango
    
    return sum(valores) / sum(pesos)


def estimar_confianza(lat, lon, anclas, radio_km=2.0):
    """Calcula confianza basada en distancia a la анcla más cercana."""
    if not anclas:
        return "BAJA"
    
    distancias = []
    for a in anclas:
        d = distancia(lat, lon, a["lat"], a["lon"])
        if d <= radio_km:
            distancias.append(d)
    
    if not distancias:
        return "BAJA"
    
    dist_min = min(distancias)
    
    if dist_min < 0.2:
        return "ALTA"
    elif dist_min < 0.6:
        return "MEDIA"
    else:
        return "BAJA"


def get_ancla_mas_cercana(lat, lon, anclas):
    """Retorna la анcla más cercana."""
    if not anclas:
        return None
    
    min_dist = float('inf')
    anclas_cercana = None
    
    for a in anclas:
        d = distancia(lat, lon, a["lat"], a["lon"])
        if d < min_dist:
            min_dist = d
            anclas_cercana = a
    
    return anclas_cercana