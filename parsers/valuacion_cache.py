import json
import hashlib
import os
from datetime import datetime

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
CACHE_PATH = os.path.join(CACHE_DIR, 'valuaciones_cache.json')
SCRAPING_CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache_scraping.json')
CACHE_VERSION = "v4_real_comparables"  # Incrementar cuando cambie la lógica de valuación

def _calcular_hash_propiedad(prop: dict) -> str:
    """Hash de los campos que afectan la valuación."""
    campos_relevantes = [
        'm2_cubiertos', 'm2_semicubiertos', 'm2_descubiertos_propios',
        'm2_descubiertos_comun_exclusivo', 'm2_comunes', 'anio_construccion',
        'estado_detalle', 'calidad_edificio', 'piso', 'total_pisos',
        'ventilacion', 'tipo_balcon', 'ubicacion_tipo', 'vista',
        'lat', 'lon', 'zona', 'dormitorios', 'descripcion_libre',
        'tipo_inmueble', 'reciclado', 'ascensores_edificio'
    ]
    prop_subset = {k: prop.get(k) for k in campos_relevantes if prop.get(k) is not None}
    prop_str = json.dumps(prop_subset, sort_keys=True, default=str)
    return hashlib.md5(prop_str.encode()).hexdigest()[:12]

def _calcular_hash_scraping() -> str:
    """Hash del cache_scraping.json para detectar si cambió."""
    try:
        if os.path.exists(SCRAPING_CACHE_PATH):
            stat = os.stat(SCRAPING_CACHE_PATH)
            return hashlib.md5(
                f"{stat.st_mtime}{stat.st_size}".encode()
            ).hexdigest()[:12]
    except:
        pass
    return "unknown"

def cargar_cache_valuaciones() -> dict:
    """Carga el cache de valuaciones desde disco."""
    try:
        if os.path.exists(CACHE_PATH):
            with open(CACHE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception:
        pass
    return {}

def guardar_cache_valuaciones(cache: dict):
    """Persiste el cache de valuaciones en disco."""
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        with open(CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=2, ensure_ascii=False, default=str)
    except Exception as e:
        print(f"[CACHE] Error guardando: {e}")

def necesita_recalcular(nombre: str, prop: dict, cache: dict) -> tuple[bool, str]:
    """
    Determina si una propiedad necesita recalcularse.
    
    Returns:
        (bool, str): (necesita_recalcular, razón)
    """
    if nombre not in cache:
        return True, "primera_vez"

    entrada = cache[nombre]

    # Invalidar por versión del código
    if entrada.get('cache_version', '') != CACHE_VERSION:
        return True, f"version_cambio ({entrada.get('cache_version', '')} -> {CACHE_VERSION})"

    hash_actual = _calcular_hash_propiedad(prop)
    if hash_actual != entrada.get('hash_prop'):
        return True, "propiedad_modificada"

    hash_scraping = _calcular_hash_scraping()
    if hash_scraping != entrada.get('hash_scraping'):
        return True, "scraping_actualizado"

    return False, "cache_valido"

def guardar_resultado(nombre: str, prop: dict, resultado: dict, cache: dict):
    """Guarda el resultado de una valuación en el cache."""
    cache[nombre] = {
        "timestamp": datetime.now().isoformat(),
        "hash_prop": _calcular_hash_propiedad(prop),
        "hash_scraping": _calcular_hash_scraping(),
        "cache_version": CACHE_VERSION,
        "resultado_completo": resultado,
        "fecha_legible": datetime.now().strftime("%d/%m/%Y %H:%M")
    }

def obtener_resultado_cacheado(nombre: str, cache: dict) -> dict:
    """Retorna el resultado cacheado para una propiedad."""
    if nombre in cache:
        return cache[nombre].get('resultado_completo', {})
    return {}

def obtener_metadata_cache(nombre: str, cache: dict) -> dict:
    """Retorna metadata del cache (fecha, razón, etc.)."""
    if nombre in cache:
        entrada = cache[nombre]
        return {
            'fecha': entrada.get('fecha_legible', '?'),
            'timestamp': entrada.get('timestamp', ''),
            'hash_prop': entrada.get('hash_prop', '?'),
        }
    return {}