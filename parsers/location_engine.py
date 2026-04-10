import math
import json
import os


def cargar_anclas(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'anclas_rosario.json')
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def distancia(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def calcular_m2_por_anclas(lat, lon, anclas):
    total_peso = 0
    total_valor = 0
    for a in anclas.values():
        d = distancia(lat, lon, a["lat"], a["lon"])
        peso = 1 / (d + 0.05)
        total_peso += peso
        total_valor += peso * a["usd_m2"]
    return total_valor / total_peso


def estimar_confianza(lat, lon, anclas):
    distancias = [distancia(lat, lon, a["lat"], a["lon"]) for a in anclas.values()]
    d_min = min(distancias)
    if d_min < 0.3:
        return "ALTA"
    elif d_min < 0.8:
        return "MEDIA"
    else:
        return "BAJA"