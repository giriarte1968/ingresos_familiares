"""
Geocodificador para propiedades en Rosario, Argentina.
Usa ArcGIS como proveedor gratuito (no requiere API key).
"""

import math
import json
import os
from geopy.geocoders import ArcGIS
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCLAS_FILE = os.path.join(BASE_DIR, "anclas_rosario.json")
PROPIEDADES_FILE = os.path.join(BASE_DIR, "propiedades.json")

arcgis_geocoder = ArcGIS(timeout=10)


def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia en kilómetros entre dos puntos usando la fórmula de Haversine.
    """
    R = 6371  # Radio de la Tierra en km
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def geocode_address(direccion, zona="Rosario"):
    """
    Geocodifica una dirección y retorna lat/lon.
    Args:
        direccion: Dirección de la propiedad (ej: "Pellegrini 1200")
        zona: Zona default para mejor resultados (ej: "Rosario")
    Returns:
        tuple: (lat, lon) o (None, None) si falla
    """
    try:
        # Armar query optimizado para Rosario
        full_address = f"{direccion}, {zona}, Santa Fe, Argentina"
        
        location = arcgis_geocoder.geocode(full_address)
        
        if location:
            return location.latitude, location.longitude
        else:
            # Retry con menos contexto
            location = arcgis_geocoder.geocode(f"{direccion}, Rosario")
            if location:
                return location.latitude, location.longitude
    except (GeocoderTimedOut, GeocoderServiceError) as e:
        print(f"Error de geocodificación: {e}")
    
    return None, None


def find_nearest_anchor(lat, lon, anclas_file=ANCLAS_FILE):
    """
    Encuentra el ancla más cercana a las coordenadas dadas.
    Args:
        lat: Latitud de la propiedad
        lon: Longitud de la propiedad
        anclas_file: Ruta al archivo de anclas
    Returns:
        dict: El ancla más cercana con sus datos
    """
    if not os.path.exists(anclas_file):
        return None
    
    with open(anclas_file, 'r', encoding='utf-8') as f:
        anclas_data = json.load(f)
    
    anclas = anclas_data.get('anclas', [])
    if not anclas:
        return None
    
    min_dist = float('inf')
    nearest = None
    
    for ancla in anclas:
        ancla_lat = ancla.get('lat')
        ancla_lon = ancla.get('lon')
        
        if ancla_lat is None or ancla_lon is None:
            continue
        
        dist = haversine_distance(lat, lon, ancla_lat, ancla_lon)
        
        if dist < min_dist:
            min_dist = dist
            nearest = ancla
    
    return nearest


def update_property_coords(prop_id, lat, lon):
    """
    Actualiza las coordenadas de una propiedad en el archivo JSON.
    """
    if not os.path.exists(PROPIEDADES_FILE):
        return False
    
    with open(PROPIEDADES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    propiedades = data.get('propiedades', [])
    
    for prop in propiedades:
        if prop.get('id') == prop_id:
            prop['lat'] = lat
            prop['lon'] = lon
            break
    
    with open(PROPIEDADES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return True


def geocode_property(prop):
    """
    Geocodifica una propiedad y actualiza sus coordenadas.
    Args:
        prop: Diccionario con datos de la propiedad (debe tener 'direccion' y 'zona')
    Returns:
        dict: Propiedad con lat/lon actualizados
    """
    direccion = prop.get('direccion', '')
    zona = prop.get('zona', 'Rosario')
    prop_id = prop.get('id')
    
    if not direccion:
        return prop
    
    lat, lon = geocode_address(direccion, zona)
    
    if lat and lon:
        prop['lat'] = lat
        prop['lon'] = lon
        
        # Encontrar ancla más cercana
        nearest_anchor = find_nearest_anchor(lat, lon)
        if nearest_anchor:
            prop['ancla_mas_cercana'] = nearest_anchor.get('id')
            prop['ancla_usd_m2'] = nearest_anchor.get('usd_m2')
            prop['distancia_ancla_km'] = round(
                haversine_distance(lat, lon, nearest_anchor.get('lat'), nearest_anchor.get('lon')), 2
            )
        
        # Guardar en archivo
        if prop_id:
            update_property_coords(prop_id, lat, lon)
    
    return prop


def geocode_all_properties():
    """
    Geocodifica todas las propiedades que no tengan lat/lon.
    """
    if not os.path.exists(PROPIEDADES_FILE):
        return {"exito": False, "error": "Archivo no encontrado"}
    
    with open(PROPIEDADES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    propiedades = data.get('propiedades', [])
    actualizadas = 0
    errores = 0
    
    for prop in propiedades:
        # Skip si ya tiene coordenadas
        if prop.get('lat') and prop.get('lon'):
            continue
        
        direccion = prop.get('direccion', '')
        zona = prop.get('zona', 'Rosario')
        prop_id = prop.get('id')
        
        if not direccion:
            errores += 1
            continue
        
        lat, lon = geocode_address(direccion, zona)
        
        if lat and lon:
            prop['lat'] = lat
            prop['lon'] = lon
            
            # Encontrar ancla más cercana
            nearest_anchor = find_nearest_anchor(lat, lon)
            if nearest_anchor:
                prop['ancla_mas_cercana'] = nearest_anchor.get('id')
                prop['ancla_usd_m2'] = nearest_anchor.get('usd_m2')
                prop['distancia_ancla_km'] = round(
                    haversine_distance(lat, lon, nearest_anchor.get('lat'), nearest_anchor.get('lon')), 2
                )
            
            actualizadas += 1
        else:
            errores += 1
    
    # Guardar cambios
    with open(PROPIEDADES_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return {
        "exito": True,
        "actualizadas": actualizadas,
        "errores": errores,
        "total": len(propiedades)
    }


if __name__ == "__main__":
    # Test rápido
    result = geocode_all_properties()
    print(f"Geocodificación completada: {result}")