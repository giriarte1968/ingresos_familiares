"""
Geocodificador V3 para propiedades en Rosario, Argentina.
Usa Nominatim (OpenStreetMap) + archivo de anclas v2.
"""

import math
import json
import os
import re
import time
import requests

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ANCLAS_FILE = os.path.join(BASE_DIR, "anclas_rosario_v3_grid.json")  # V3
PROPIEDADES_FILE = os.path.join(BASE_DIR, "propiedades.json")
CACHE_FILE = os.path.join(BASE_DIR, "geocoding_cache.json")

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
NOMINATIM_HEADERS = {"User-Agent": "rosario_avm_geocoder"}

CATSTRO_CSV = os.path.join(BASE_DIR, "data", "rosario_avm_full.csv")
_catastro_cache = None  # carga lazy


def normalizar_direccion(direccion):
    return direccion.strip().lower()


def cargar_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


def guardar_cache(cache):
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def _deunicodificar(s):
    """NFKD normalize + strip, para comparar direcciones."""
    import unicodedata
    s = unicodedata.normalize("NFKD", str(s))
    s = s.encode("ascii", "ignore").decode("ascii")
    return s.strip().lower()


def _cargar_catastro():
    global _catastro_cache
    if _catastro_cache is None:
        import pandas as pd
        df = pd.read_csv(CATSTRO_CSV, encoding="utf-8")
        df["_addr_norm"] = df["direccion_nominatim"].astype(str).apply(_deunicodificar)
        _catastro_cache = df
    return _catastro_cache


def buscar_en_catastro(direccion):
    """
    Busca 'direccion' en rosario_avm_full.csv.
    Retorna dict con lat, lon, address o None si no encuentra.
    """
    df = _cargar_catastro()
    addr_norm = _deunicodificar(direccion)
    match = df[df["_addr_norm"] == addr_norm]
    if len(match) == 0:
        # intentar matching parcial: solamente calle + numero
        addr_clean = re.sub(r"\bbis\b", "", addr_norm)
        match = df[df["_addr_norm"].str.contains(re.escape(addr_clean), na=False)]
    if len(match) > 0:
        row = match.iloc[0]
        lat, lon = row["latitud"], row["longitud"]
        if pd.notna(lat) and pd.notna(lon):
            return {
                "lat": float(lat),
                "lon": float(lon),
                "address": row["direccion_nominatim"],
                "score": 0.9,
                "type": "catastro",
                "source": "catastro",
            }
    return None


# Viewbox para restringir a Rosario centro (formato string: lon_min,lat_min,lon_max,lat_max)
VIEWBOX = "-60.75,-33.00,-60.50,-32.87"


def _parse_nominatim_response(data):
    """Parsea el primer resultado de Nominatim JSON. Retorna dict o None."""
    if not data or not isinstance(data, list) or len(data) == 0:
        return None
    r = data[0]
    osm_type = r.get("type") or r.get("addresstype") or "unknown"
    return {
        "lat": float(r["lat"]),
        "lon": float(r["lon"]),
        "address": r.get("display_name", ""),
        "score": r.get("importance", 0.5),
        "type": osm_type,
    }


def geocodificar_nominatim(direccion):
    """
    Geocodifica usando Nominatim (OpenStreetMap) con query estructurada HTTP directo.
    direccion debe ser solo la calle y numero (ej: 'Entre Rios 400').
    """
    try:
        calle = direccion.split(",")[0].strip()
        # Limpiar sufijos como "bis" que confunden a Nominatim (no puede matchear numero con bis)
        calle = re.sub(r"\bbis\b", "", calle, flags=re.IGNORECASE)
        calle = re.sub(r"\s+", " ", calle).strip()
        params = {
            "street": calle,
            "city": "Rosario",
            "state": "Santa Fe",
            "country": "Argentina",
            "format": "jsonv2",
            "limit": 1,
        }
        r = requests.get(NOMINATIM_URL, params=params, headers=NOMINATIM_HEADERS, timeout=10)
        r.raise_for_status()
        return _parse_nominatim_response(r.json())
    except Exception as e:
        print(f"Error geocodificacion Nominatim: {e}")
    return None


def geocodificar_nominatim_freeform(direccion_full):
    """
    Fallback: geocodifica con free-form query HTTP directo
    (ej: 'Entre Rios 400, Rosario, Santa Fe, Argentina').
    """
    try:
        params = {
            "q": direccion_full,
            "format": "jsonv2",
            "limit": 1,
        }
        r = requests.get(NOMINATIM_URL, params=params, headers=NOMINATIM_HEADERS, timeout=10)
        r.raise_for_status()
        return _parse_nominatim_response(r.json())
    except Exception as e:
        print(f"Error geocodificacion Nominatim freeform: {e}")
    return None


# Alias para compatibilidad
geocodificar_arcgis = geocodificar_nominatim


def haversine_distance(lat1, lon1, lat2, lon2):
    """Distancia Haversine entre dos puntos (km)."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def snap_a_anclas(lat, lon, anclas, max_dist_km=3.0):
    """Snap coordenadas al ancla mas cercana. Deshabilitado: devuelve originales."""
    return lat, lon, 'no_snap'


MAX_DISCREPANCIA_M = 500  # max diferencia entre pin scraping y geocoding textual


def validar_coordenadas_contra_direccion(direccion, lat_pin, lon_pin, max_diff_m=MAX_DISCREPANCIA_M):
    """
    Compara coordenadas del pin scraping contra geocoding de la direccion textual.
    Si difieren > max_diff_m, retorna coordenadas de geocoding mas confiables.
    Retorna: (lat, lon, diff_m, accion) donde accion es 'ok', 'corregido', o 'error'.
    """
    if not direccion or not direccion.strip():
        return lat_pin, lon_pin, 0, "error"

    try:
        geo = geocodificar_nominatim(direccion)
        if not geo:
            geo = geocodificar_nominatim_freeform(f"{direccion}, Rosario, Santa Fe, Argentina")
        if not geo or geo.get("lat") is None:
            return lat_pin, lon_pin, 0, "error"

        lat_geo = geo["lat"]
        lon_geo = geo["lon"]
        diff_m = haversine_distance(lat_pin, lon_pin, lat_geo, lon_geo) * 1000

        if diff_m > max_diff_m:
            return lat_geo, lon_geo, round(diff_m, 1), "corregido"

        return lat_pin, lon_pin, round(diff_m, 1), "ok"
    except Exception:
        return lat_pin, lon_pin, 0, "error"


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
    
    # Buscar ancla mas cercana a las coordenadas (snap o originales)
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
    Manager principal de geocodificacion con cache.

    Orden de busqueda:
      1. Cache
      2. Catastro CSV (rosario_avm_full.csv) — prioridad para direcciones con "bis"
      3. Nominatim structured (geocodificar_nominatim) que quita "bis" de la calle
      4. Nominatim free-form como fallback

    Retorna dict con lat, lon, status, score, type, _debug (info de trazabilidad).
    """
    import time
    debug = {"pasos": [], "errores": []}
    debug["input"] = direccion

    cache = cargar_cache()
    key = normalizar_direccion(direccion)

    # 1. Revisar cache
    if key in cache:
        cached = cache[key]
        debug["pasos"].append("Cache HIT (resultado de ejecución previa)")
        debug["fuente_original"] = cached.get("_fuente", "desconocida (cache anterior a TAREA-027)")
        debug["status_cachead"] = cached.get("status", "?")
        if cached.get("lat") and not debug.get("errores"):
            debug["coordenadas_cacheadas"] = f"{cached['lat']:.5f}, {cached['lon']:.5f}"
        if debug["fuente_original"] == "catastro" and cached.get("status") == "catastro":
            pass  # no tenemos la dirección matchada, pero sabemos que vino de catastro
        r = dict(cached)
        r["_debug"] = debug
        return r
    debug["pasos"].append("Cache MISS")

    # 2. Buscar en catastro CSV
    tiene_bis = bool(re.search(r"\bbis\b", direccion, flags=re.IGNORECASE))
    debug["tiene_bis"] = tiene_bis
    catastro_geo = buscar_en_catastro(direccion)
    if catastro_geo:
        debug["pasos"].append("Catastro CSV HIT")
        debug["catastro_addr"] = catastro_geo["address"]
        debug["catastro_lat"] = catastro_geo["lat"]
        debug["catastro_lon"] = catastro_geo["lon"]
        with open(ANCLAS_FILE, 'r', encoding='utf-8') as f:
            anclas_data = json.load(f)
        anclas = anclas_data.get('anclas', [])
        lat, lon, status, ancla_id, ancla_usd, dist = validar_y_corregir(direccion, catastro_geo, anclas)
        result = {
            "lat": lat,
            "lon": lon,
            "status": "catastro",
            "score": catastro_geo["score"],
            "type": catastro_geo["type"],
            "ancla_id": ancla_id,
            "ancla_usd": ancla_usd,
            "distancia_km": round(dist, 2),
            "_fuente": "catastro",
            "_debug": debug,
        }
        cache[key] = result
        guardar_cache(cache)
        return result
    debug["pasos"].append("Catastro CSV MISS")

    # Cargar anclas
    with open(ANCLAS_FILE, 'r', encoding='utf-8') as f:
        anclas_data = json.load(f)
    anclas = anclas_data.get('anclas', [])

    # 3. Geocodificar con Nominatim
    if tiene_bis:
        debug["pasos"].append("Nominatim free-form (tiene bis)")
        full_addr = f"{direccion}, Rosario, Santa Fe, Argentina"
        geo = geocodificar_nominatim_freeform(full_addr)
    else:
        debug["pasos"].append("Nominatim structured")
        geo = geocodificar_arcgis(direccion)

    time.sleep(0.5)

    if not geo:
        debug["pasos"].append("Nominatim FAIL (sin resultado)")
        result = {"lat": None, "lon": None, "status": "error", "ancla_id": None, "ancla_usd": None, "_fuente": "nominatim", "_debug": debug}
        cache[key] = result
        guardar_cache(cache)
        return result
    debug["pasos"].append(f"Nominatim OK lat={geo['lat']:.5f} lon={geo['lon']:.5f} score={geo['score']} type={geo['type']}")

    # 4. Validar y corregir
    lat, lon, status, ancla_id, ancla_usd, dist = validar_y_corregir(direccion, geo, anclas)
    debug["pasos"].append(f"Validacion status={status}")

    # Si quedo fuera de Rosario o low_confidence, reintentar con free-form
    if not tiene_bis and status in ("fuera_de_rosario", "low_confidence"):
        debug["pasos"].append("Fallback: free-form query")
        time.sleep(0.5)
        full_addr = f"{direccion}, Rosario, Santa Fe, Argentina"
        geo2 = geocodificar_nominatim_freeform(full_addr)
        if geo2:
            debug["pasos"].append(f"Free-form OK lat={geo2['lat']:.5f} lon={geo2['lon']:.5f}")
            geo = geo2
            lat, lon, status, ancla_id, ancla_usd, dist = validar_y_corregir(direccion, geo2, anclas)
        else:
            debug["pasos"].append("Free-form FAIL")

    result = {
        "lat": lat,
        "lon": lon,
        "status": status,
        "score": geo["score"],
        "type": geo["type"],
        "ancla_id": ancla_id,
        "ancla_usd": ancla_usd,
        "distancia_km": round(dist, 2),
        "_fuente": "nominatim",
        "_debug": debug,
    }

    # 5. Guardar en cache
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
    print(f"Geocodificacion: {result}")
