"""
Geocodificador V2 para propiedades en Rosario, Argentina.
Usa ArcGIS con validación inteligente y corrección por zona.
"""

import math
import json
import os
import requests
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCLAS_FILE = os.path.join(BASE_DIR, "anclas_rosario.json")
PROPIEDADES_FILE = os.path.join(BASE_DIR, "propiedades.json")
CACHE_FILE = os.path.join(BASE_DIR, "geocoding_cache.json")


def haversine_distance(lat1, lon1, lat2, lon2):
    """Calcula distancia en km entre dos puntos."""
    R = 6371
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))


def snap_a_anclas(lat, lon, anclas, k=5):
    """
    Ajusta coordenadas hacia las k anclas más cercanas usando IDW.
    Solo aplica snap si la ancla más cercana está a más de 300m.
    Args:
        lat, lon: Coordenadas originales
        anclas: Lista de anclas con lat/lon/usd_m2
        k: Número de anclas a usar para el snap
    Returns:
        (lat_corr, lon_corr, status)
    """
    # Calcular distancias a todas las anclas
    distancias = [(a, haversine_distance(lat, lon, a['lat'], a['lon'])) for a in anclas]
    # Tomar las k más cercanas
    cercanas = sorted(distancias, key=lambda x: x[1])[:k]
    
    # Si la más cercana está a menos de 300m, no hacer snap (coords ya son buenas)
    if cercanas[0][1] < 0.3:
        return lat, lon, "exact"
    
    # IDW: ponderar por 1/d²
    num_lat = num_lon = den = 0
    for a, d in cercanas:
        if d == 0:
            return a['lat'], a['lon'], "exact"
        w = 1 / (d ** 2)
        num_lat += w * a['lat']
        num_lon += w * a['lon']
        den += w
    
    return num_lat / den, num_lon / den, "snap_global"


def normalizar_direccion(direccion):
    return direccion.strip().lower()


def cargar_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def guardar_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2)


def geocodificar_arcgis(direccion):
    """Geocodifica usando ArcGIS API directamente."""
    url = "https://geocode.arcgis.com/arcgis/rest/services/World/GeocodeServer/findAddressCandidates"
    params = {
        "f": "json",
        "SingleLine": direccion,
        "outFields": "*",
        "maxLocations": 1
    }
    
    try:
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        
        if not data.get("candidates"):
            return None
        
        c = data["candidates"][0]
        return {
            "lat": c["location"]["y"],
            "lon": c["location"]["x"],
            "score": c.get("score", 0),
            "type": c.get("attributes", {}).get("Addr_type", "")
        }
    except Exception as e:
        print(f"Error geocodificación: {e}")
        return None


def detectar_zona_por_texto(direccion, anclas):
    """Detecta anclas relacionadas por palabras en la dirección."""
    d = direccion.lower()
    keywords = ["pellegrini", "oroño", "pichincha", "abasto", "lourdes", "bv", "cordoba", "paraguay", "necochea"]
    
    candidatos = []
    for kw in keywords:
        if kw in d:
            for a in anclas:
                if kw in a["id"]:
                    candidatos.append(a)
    
    return candidatos


def validar_y_corregir(direccion, geo, anclas):
    """
    Valida el resultado de ArcGIS y aplica snap a anclas.
    Retorna: (lat, lon, status, ancla_id, ancla_usd)
    """
    lat = geo["lat"]
    lon = geo["lon"]
    score = geo["score"]
    tipo = geo["type"]
    
    # Aplicar snap a anclas (mejora coords hacia zonas de precio correctas)
    lat_snap, lon_snap, snap_status = snap_a_anclas(lat, lon, anclas)
    
    # Buscar ancla más cercana a las coordenadas (snap o originales)
    min_dist = float('inf')
    ancla_cerca = None
    for a in anclas:
        d = haversine_distance(lat_snap, lon_snap, a['lat'], a['lon'])
        if d < min_dist:
            min_dist = d
            ancla_cerca = a
    
    # Estado combina calidad ArcGIS + snap
    baja_confianza = score < 90 or tipo not in ["PointAddress", "StreetAddress", "StreetAddressExt"]
    
    if snap_status == "exact" and not baja_confianza:
        status = "ok"
    elif snap_status == "snap_global":
        status = "snap_global"
    else:
        status = "low_confidence" if baja_confianza else "ok"
    
    return lat_snap, lon_snap, status, ancla_cerca["id"], ancla_cerca["usd_m2"], min_dist


def geocoding_manager(direccion):
    """
    Manager principal de geocodificación con cache.
    """
    cache = cargar_cache()
    key = normalizar_direccion(direccion)
    
    # 1. Revisar cache
    if key in cache:
        return cache[key]
    
    # Cargar anclas
    with open(ANCLAS_FILE, 'r', encoding='utf-8') as f:
        anclas_data = json.load(f)
    anclas = anclas_data.get('anclas', [])
    
    # 2. Geocodificar
    direccion_full = f"{direccion}, Rosario, Santa Fe, Argentina"
    geo = geocodificar_arcgis(direccion_full)
    
    time.sleep(0.5)  # Rate limiting
    
    if not geo:
        result = {"lat": None, "lon": None, "status": "error", "ancla_id": None, "ancla_usd": None}
        cache[key] = result
        guardar_cache(cache)
        return result
    
    # 3. Validar y corregir
    lat, lon, status, ancla_id, ancla_usd, dist = validar_y_corregir(direccion, geo, anclas)
    
    result = {
        "lat": lat,
        "lon": lon,
        "status": status,
        "score": geo["score"],
        "type": geo["type"],
        "ancla_id": ancla_id,
        "ancla_usd": ancla_usd,
        "distancia_km": round(dist, 2)
    }
    
    # 4. Guardar en cache
    cache[key] = result
    guardar_cache(cache)
    
    return result


def geocode_property(prop):
    """
    Geocodifica una propiedad y retorna con coordenadas actualizadas.
    """
    direccion = prop.get('direccion', '')
    prop_id = prop.get('id')
    
    if not direccion:
        return prop
    
    result = geocoding_manager(direccion)
    
    if result.get("lat"):
        prop['lat'] = result["lat"]
        prop['lon'] = result["lon"]
        prop['ancla_mas_cercana'] = result.get("ancla_id")
        prop['ancla_usd_m2'] = result.get("ancla_usd")
        prop['distancia_ancla_km'] = result.get("distancia_km")
        prop['geocode_status'] = result.get("status")
        
        # Guardar en archivo
        if prop_id:
            update_property_coords(prop_id, result["lat"], result["lon"], 
                                   result.get("ancla_id"), result.get("ancla_usd"), 
                                   result.get("distancia_km"))
    
    return prop


def update_property_coords(prop_id, lat, lon, ancla_id=None, ancla_usd=None, distancia_km=None):
    """Actualiza coordenadas y ancla de una propiedad."""
    if not os.path.exists(PROPIEDADES_FILE):
        return False
    
    with open(PROPIEDADES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    propiedades = data.get('propiedades', [])
    
    for prop in propiedades:
        if prop.get('id') == prop_id:
            prop['lat'] = lat
            prop['lon'] = lon
            if ancla_id:
                prop['ancla_mas_cercana'] = ancla_id
            if ancla_usd:
                prop['ancla_usd_m2'] = ancla_usd
            if distancia_km:
                prop['distancia_ancla_km'] = distancia_km
            break
    
    with open(PROPIEDADES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return True


def geocode_all_properties():
    """Geocodifica todas las propiedades que no tengan coordenadas."""
    if not os.path.exists(PROPIEDADES_FILE):
        return {"exito": False, "error": "Archivo no encontrado"}
    
    with open(PROPIEDADES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    propiedades = data.get('propiedades', [])
    actualizadas = 0
    errores = 0
    
    for prop in propiedades:
        direccion = prop.get('direccion', '')
        
        if not direccion:
            errores += 1
            continue
        
        # Cargar anclas una vez
        with open(ANCLAS_FILE, 'r', encoding='utf-8') as f:
            anclas_data = json.load(f)
        anclas = anclas_data.get('anclas', [])
        
        # Si ya tiene coordenadas, aplicar snap + buscar ancla
        if prop.get('lat') and prop.get('lon'):
            lat = prop.get('lat')
            lon = prop.get('lon')
            
            # Aplicar snap (incluso a coords existentes para mejorar)
            lat_snap, lon_snap, snap_status = snap_a_anclas(lat, lon, anclas)
            
            # Buscar ancla mas cercana a coords snap
            min_dist = float('inf')
            ancla_cerca = None
            for a in anclas:
                d = haversine_distance(lat_snap, lon_snap, a['lat'], a['lon'])
                if d < min_dist:
                    min_dist = d
                    ancla_cerca = a
            
            prop['lat'] = lat_snap
            prop['lon'] = lon_snap
            prop['ancla_mas_cercana'] = ancla_cerca['id']
            prop['ancla_usd_m2'] = ancla_cerca['usd_m2']
            prop['distancia_ancla_km'] = round(min_dist, 2)
            prop['geocode_status'] = snap_status
            
            update_property_coords(prop.get('id'), lat_snap, lon_snap,
                                  ancla_cerca['id'], ancla_cerca['usd_m2'],
                                  round(min_dist, 2))
            actualizadas += 1
            continue
        
        # Geocodificar desde cero
        result = geocoding_manager(direccion)
        
        if result.get("lat"):
            prop['lat'] = result["lat"]
            prop['lon'] = result["lon"]
            prop['ancla_mas_cercana'] = result.get("ancla_id")
            prop['ancla_usd_m2'] = result.get("ancla_usd")
            prop['distancia_ancla_km'] = result.get("distancia_km")
            prop['geocode_status'] = result.get("status")
            actualizadas += 1
        else:
            errores += 1
    
    with open(PROPIEDADES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return {
        "exito": True,
        "actualizadas": actualizadas,
        "errores": errores,
        "total": len(propiedades)
    }


if __name__ == "__main__":
    result = geocode_all_properties()
    print(f"Geocodificación: {result}")