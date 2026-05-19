"""
Geocodificador V3 para propiedades en Rosario, Argentina.
Usa Nominatim (OpenStreetMap) + archivo de anclas v2.
"""

import math
import json
import os
import time

try:
    from geopy.geocoders import Nominatim
    GEOPY_AVAILABLE = True
except ImportError:
    GEOPY_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCLAS_FILE = os.path.join(BASE_DIR, "anclas_rosario_v3_grid.json")  # V3
PROPIEDADES_FILE = os.path.join(BASE_DIR, "propiedades.json")
CACHE_FILE = os.path.join(BASE_DIR, "geocoding_cache.json")

# Geocodificador Nominatim
geolocator = Nominatim(user_agent="rosario_avm_geocoder") if GEOPY_AVAILABLE else None


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
    Deshabilitado: Nominatim ya es preciso (~32m).
    Retorna coordenadas originales.
    """
    return lat, lon, "no_snap"


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


def geocodificar_nominatim(direccion):
    """
    Geocodifica usando Nominatim (OpenStreetMap).
    """
    if not geolocator:
        return None
    
    try:
        full_address = f"{direccion}, Rosario, Santa Fe, Argentina"
        location = geolocator.geocode(full_address)
        
        if location:
            raw = location.raw if hasattr(location, 'raw') and location.raw else {}
            osm_type = raw.get('type', 'unknown') if isinstance(raw, dict) else 'unknown'
            return {
                "lat": location.latitude,
                "lon": location.longitude,
                "address": location.address or '',
                "score": raw.get('importance', 0.5) if isinstance(raw, dict) else 0.5,
                "type": osm_type,
            }
    except Exception as e:
        print(f"Error geocodificación Nominatim: {e}")
    
    return None


# Alias para compatibilidad
geocodificar_arcgis = geocodificar_nominatim


# Bounding box para Rosario centro (~radio 5km desde punto central)
CENTRO_LAT, CENTRO_LON = -32.945, -60.632
RADIO_MAX_KM = 8.0


def _validar_dentro_de_rosario(lat, lon):
    """Retorna True si las coordenadas estan dentro del area de Rosario."""
    d = haversine_distance(lat, lon, CENTRO_LAT, CENTRO_LON)
    return d <= RADIO_MAX_KM


def validar_y_corregir(direccion, geo, anclas):
    """
    Valida el resultado de Nominatim y aplica snap a anclas.
    Retorna: (lat, lon, status, ancla_id, ancla_usd)
    """
    lat = geo["lat"]
    lon = geo["lon"]
    score = geo["score"]
    tipo = geo["type"]
    
    # Validar que este dentro del area de Rosario
    dentro = _validar_dentro_de_rosario(lat, lon)
    
    # Aplicar snap a anclas (deshabilitado, devuelve original)
    lat_snap, lon_snap, snap_status = snap_a_anclas(lat, lon, anclas)
    
    # Buscar ancla más cercana a las coordenadas (snap o originales)
    min_dist = float('inf')
    ancla_cerca = None
    for a in anclas:
        d = haversine_distance(lat_snap, lon_snap, a['lat'], a['lon'])
        if d < min_dist:
            min_dist = d
            ancla_cerca = a
    
    # Calidad del resultado
    tipos_validos = ["house", "building", "yes", "residential", "apartments", "detached", "terrace", "house_number"]
    score_alto = score >= 0.4  # importance de Nominatim > 0.4 = resultado bueno
    tipo_valido = tipo in tipos_validos
    
    if not dentro:
        status = "fuera_de_rosario"
    elif not tipo_valido or not score_alto:
        status = "low_confidence"
    else:
        status = "ok"
    
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
    
    # 2. Geocodificar (primer intento)
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
    
    # Si quedo fuera de Rosario, reintentar con query mas especifica
    if status == "fuera_de_rosario":
        time.sleep(0.5)
        direccion_full2 = f"{direccion}, Rosario Centro, Santa Fe, Argentina"
        geo2 = geocodificar_arcgis(direccion_full2)
        if geo2:
            geo = geo2
            lat, lon, status, ancla_id, ancla_usd, dist = validar_y_corregir(direccion, geo2, anclas)
    
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
    """Geocodifica todas las propiedades."""
    if not os.path.exists(PROPIEDADES_FILE):
        return {"exito": False, "error": "Archivo no encontrado"}
    
    with open(PROPIEDADES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    propiedades = data.get('propiedades', [])
    actualizadas = 0
    errores = 0
    
    # Cargar anclas una vez
    with open(ANCLAS_FILE, 'r', encoding='utf-8') as f:
        anclas_data = json.load(f)
    anclas = anclas_data.get('anclas', [])
    
    for prop in propiedades:
        direccion = prop.get('direccion', '')
        
        # Solo geocodificar si no tiene coordenadas
        if prop.get('lat') and prop.get('lon'):
            continue
        
        if not direccion:
            errores += 1
            continue
        
        # SIEMPRE geocodificar con Nominatim (ignorar coords existentes)
        result = geocodificar_nominatim(direccion)
        
        if result and result.get("lat"):
            lat = result["lat"]
            lon = result["lon"]
            
            # Aplicar snap
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