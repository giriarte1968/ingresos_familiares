import json
import hashlib
import os
from datetime import datetime

CACHE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
CACHE_PATH = os.path.join(CACHE_DIR, 'valuaciones_cache.json')
SCRAPING_CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache_scraping.json')
def get_cache_version():
    try:
        from parsers.motor_vpp_core import load_anclas_config
        cfg = load_anclas_config()
        return cfg.get('runtime', {}).get('cache_version', 'v6_pn_comparables')
    except Exception:
        return "v6_pn_comparables"

CACHE_VERSION = get_cache_version()
PROPIEDADES_PATH = os.path.join(os.path.dirname(CACHE_DIR), 'propiedades.json')


# ───────── Escritura atómica ─────────

def atomic_write_json(path, data):
    """Escribe JSON atómicamente: tmp -> os.replace.
    Garantiza que el archivo destino nunca quede truncado."""
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)
    os.replace(tmp, path)


# ───────── Hashing ─────────

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

def _calcular_hash_scraping() -> str | None:
    """Hash del cache_scraping.json para detectar si cambió."""
    try:
        if os.path.exists(SCRAPING_CACHE_PATH):
            stat = os.stat(SCRAPING_CACHE_PATH)
            return hashlib.md5(
                f"{stat.st_mtime}{stat.st_size}".encode()
            ).hexdigest()[:12]
    except:
        pass
    return None


# ───────── Cache I/O ─────────

def cargar_cache_valuaciones() -> dict:
    """Carga el cache de valuaciones desde disco."""
    from parsers.profiler import profile_block
    with profile_block("disk_cargar_cache_valuaciones", None):
        try:
            if os.path.exists(CACHE_PATH):
                with open(CACHE_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
    return {}

def guardar_cache_valuaciones(cache: dict) -> bool:
    """Persiste el cache de valuaciones en disco. Versión atómica."""
    from parsers.profiler import profile_block
    with profile_block("disk_guardar_cache_valuaciones", None):
        try:
            atomic_write_json(CACHE_PATH, cache)
            return True
        except Exception as e:
            print(f"[CACHE] Error guardando: {e}")
            return False

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
    current_cv = get_cache_version()
    if entrada.get('cache_version', '') != current_cv:
        return True, f"version_cambio ({entrada.get('cache_version', '')} -> {current_cv})"

    hash_actual = _calcular_hash_propiedad(prop)
    if hash_actual != entrada.get('hash_prop'):
        return True, "propiedad_modificada"

    hash_scraping = _calcular_hash_scraping()
    if hash_scraping is not None and hash_scraping != entrada.get('hash_scraping'):
        return True, "scraping_actualizado"

    return False, "cache_valido"


# ───────── Persistencia ─────────

def guardar_resultado(nombre: str, prop: dict, resultado: dict, cache: dict):
    """Wrapper de compatibilidad. Delega en persistir_valuacion().
    No hace git sync."""
    persistir_valuacion(nombre, prop, resultado, cache)


def persistir_valuacion(nombre: str, prop: dict, resultado: dict, cache: dict, commit: bool = True, manual_data: dict = None) -> bool:
    """
    Persiste una valuación completa.

    commit=True:  actualiza cache + _ultima_valuacion (valuación oficial)
    commit=False: solo actualiza cache (preview, no marca como valuada en portfolio)

    Orden obligatorio:
    1. Actualizar cache en memoria.
    2. Escribir data/valuaciones_cache.json a disco.
    3. Actualizar propiedades.json con _ultima_valuacion (solo si commit=True).
    4. Escribir propiedades.json a disco (solo si commit=True).
    5. Retornar True/False.

    NO hace git sync.
    """
    from parsers.profiler import profile_block
    print(f"[DEBUG-CACHE] persistir_valuacion({nombre}): commit={commit}, valor_usd={resultado.get('valor_propiedad_usd')}, n_comps={resultado.get('resolution_metadata',{}).get('n_propiedades',0)}")
    with profile_block("persistir_valuacion", None):
        try:
            if commit:
                # 1. Actualizar cache en memoria
                cache[nombre] = {
                    "timestamp": datetime.now().isoformat(),
                    "hash_prop": _calcular_hash_propiedad(prop),
                    "hash_scraping": _calcular_hash_scraping(),
                    "cache_version": get_cache_version(),
                    "resultado_completo": resultado,
                    "fecha_legible": datetime.now().strftime("%d/%m/%Y %H:%M"),
                }

                # 2. Escribir valuaciones_cache.json a disco
                atomic_write_json(CACHE_PATH, cache)

                # 3-4: Actualizar propiedades.json con _ultima_valuacion
                if os.path.exists(PROPIEDADES_PATH):
                    with open(PROPIEDADES_PATH, 'r', encoding='utf-8') as f:
                        props_data = json.load(f)
                    for p in props_data.get('propiedades', []):
                        if p.get('nombre') == nombre:
                            if manual_data:
                                p.update(manual_data)
                            
                            old_uv = p.get('_ultima_valuacion', {})
                            new_excluded = resultado.get('_comp_excluded')
                            if new_excluded is None and old_uv.get('_comp_exclusion_applied'):
                                new_excluded = old_uv.get('_comp_excluded')
                            p['_ultima_valuacion'] = {
                                'valor_usd': resultado.get('valor_propiedad_usd'),
                                'alquiler_ars': resultado.get('alquiler_estimado_ars'),
                                'cap_rate': resultado.get('cap_rate'),
                                'm2_equivalentes': resultado.get('m2_equivalentes'),
                                'comps': resultado.get('resolution_metadata', {}).get('n_propiedades', 0),
                                'fecha': datetime.now().strftime("%d/%m/%Y %H:%M"),
                                'cache_version': get_cache_version(),
                                'timestamp': datetime.now().isoformat(),
                                'fuente': resultado.get('fuente', 'auto'),
                                'manual_params': resultado.get('manual_params'),
                                '_comp_excluded': new_excluded,
                                '_comp_exclusion_applied': old_uv.get('_comp_exclusion_applied', False) if new_excluded else resultado.get('_comp_exclusion_applied', False),
                            }
                            break

                    atomic_write_json(PROPIEDADES_PATH, props_data)

            return True

        except Exception as e:
            print(f"[CACHE] Error persistiendo valuacion {nombre}: {e}")
            return False

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