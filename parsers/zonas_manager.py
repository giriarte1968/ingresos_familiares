"""
Sistema de macrozonas inmobiliarias para depreciacion diferenciada.
Provee resolucion de macrozona para cualquier propiedad del sistema.

Jerarquia de resolucion:
  1. Texto especifico (keywords de alta precision) -> confianza ALTA
  2. Bounding box geografico (lat/lon) -> confianza MEDIA
  3. Default (resto_rosario) -> confianza BAJA

Uso:
    from parsers.zonas_manager import resolver_macrozona
    resultado = resolver_macrozona(prop)
"""
import json
import os
import re

_ZONAS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "data", "zonas_depreciacion.json")
_CACHE = {"data": None, "version": 0}


def _cargar_macrozonas():
    """Carga el JSON de macrozonas con cache en memoria."""
    if _CACHE["data"] is not None:
        return _CACHE["data"]
    try:
        with open(_ZONAS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        _CACHE["data"] = data
        return data
    except Exception as e:
        raise RuntimeError(f"Error cargando macrozonas: {e}")


def normalizar_texto_zona(texto):
    """Normaliza texto de zona: lower, sin tildes, sin puntuacion, espacios compactos."""
    if not texto:
        return ""
    t = texto.lower().strip()
    reemplazos = {
        'a': ['á', 'à', 'ä', 'â'],
        'e': ['é', 'è', 'ë', 'ê'],
        'i': ['í', 'ì', 'ï', 'î'],
        'o': ['ó', 'ò', 'ö', 'ô'],
        'u': ['ú', 'ù', 'ü', 'û'],
        'n': ['ñ'],
        'c': ['ç'],
    }
    for target, chars in reemplazos.items():
        for ch in chars:
            t = t.replace(ch, target)
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def _nombre_por_id(mid):
    """Obtiene nombre legible de una macrozona por su id."""
    data = _cargar_macrozonas()
    for m in data["macrozonas"]:
        if m["id"] == mid:
            return m["nombre"]
    return mid


def resolver_macrozona(prop):
    """
    Resuelve la macrozona de una propiedad siguiendo la jerarquia:
    1) texto especifico (confianza ALTA)
    2) bbox geografico (confianza MEDIA)
    3) default (confianza BAJA)

    Args:
        prop: dict con datos de la propiedad (zona, barrio, lat, lon)

    Returns:
        dict con macrozona_id, macrozona_nombre, metodo_match, confianza_macrozona, bbox_conflict
    """
    data = _cargar_macrozonas()
    default_id = data.get("default_macrozona", "resto_rosario")

    # --- 1. MATCH TEXTUAL ---
    texto_zona = (prop.get("zona") or prop.get("barrio") or prop.get("direccion") or "")
    match_textual = None
    if texto_zona:
        zona_norm = normalizar_texto_zona(texto_zona)
        for mz in data["macrozonas"]:
            for keyword in mz.get("zonas_match_textual", []):
                kw_norm = normalizar_texto_zona(keyword)
                if kw_norm and kw_norm in zona_norm:
                    match_textual = mz
                    break
            if match_textual:
                break

    # --- 2. MATCH POR BBOX ---
    match_bbox = None
    lat = prop.get("lat")
    lon = prop.get("lon")
    if lat is not None and lon is not None:
        try:
            lat_f, lon_f = float(lat), float(lon)
            for mz in data["macrozonas"]:
                bbox = mz.get("bbox")
                if bbox is None:
                    continue
                if (bbox["lat_min"] <= lat_f <= bbox["lat_max"]
                        and bbox["lon_min"] <= lon_f <= bbox["lon_max"]):
                    match_bbox = mz
                    break
        except (ValueError, TypeError):
            pass

    # --- 3. RESOLVER ---
    if match_textual and match_bbox:
        # Conflicto: texto dice una zona, bbox dice otra
        if match_textual["id"] != match_bbox["id"]:
            return {
                "macrozona_id": match_textual["id"],
                "macrozona_nombre": match_textual["nombre"],
                "metodo_match": "textual",
                "confianza_macrozona": "ALTA",
                "bbox_conflict": True,
                "bbox_sugerido": match_bbox["id"],
            }
        else:
            # Coinciden: solo metadata textual
            return {
                "macrozona_id": match_textual["id"],
                "macrozona_nombre": match_textual["nombre"],
                "metodo_match": "textual",
                "confianza_macrozona": "ALTA",
                "bbox_conflict": False,
            }

    if match_textual:
        return {
            "macrozona_id": match_textual["id"],
            "macrozona_nombre": match_textual["nombre"],
            "metodo_match": "textual",
            "confianza_macrozona": "ALTA",
            "bbox_conflict": False,
        }

    if match_bbox:
        return {
            "macrozona_id": match_bbox["id"],
            "macrozona_nombre": match_bbox["nombre"],
            "metodo_match": "bbox",
            "confianza_macrozona": "MEDIA",
            "bbox_conflict": False,
        }

    # Default
    return {
        "macrozona_id": default_id,
        "macrozona_nombre": _nombre_por_id(default_id),
        "metodo_match": "default",
        "confianza_macrozona": "BAJA",
        "bbox_conflict": False,
    }


def obtener_tasa_depreciacion_macrozona(prop):
    """
    Retorna la tasa anual de depreciacion segun la macrozona resuelta.
    
    Args:
        prop: dict con datos de la propiedad
    
    Returns:
        (tasa_anual, metadata_macrozona)
        tasa_anual: float (0.004, 0.005, 0.006)
        metadata_macrozona: dict del resolver_macrozona
    """
    mz = resolver_macrozona(prop)
    macro_id = mz.get("macrozona_id", "resto_rosario")
    data = _cargar_macrozonas()
    for m in data.get("macrozonas", []):
        if m.get("id") == macro_id:
            tasa = m.get("tasa_depreciacion_anual", 0.006)
            return tasa, mz
    return 0.006, mz


def limpiar_cache():
    """Fuerza recarga del JSON en la proxima llamada."""
    _CACHE["data"] = None
