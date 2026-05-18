"""
Sistema de macrozonas inmobiliarias para depreciacion diferenciada.
Provee resolucion de macrozona para cualquier propiedad del sistema.

Uso:
    from parsers.zonas_manager import resolver_macrozona
    resultado = resolver_macrozona(prop)
    # -> {"macrozona_id": "...", "macrozona_nombre": "...", "metodo": "...", "confianza": "..."}
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
    """
    Normaliza texto de zona para busqueda textual.
    - lower
    - elimina tildes y dieresis
    - elimina puntuacion
    - strip
    - colapsa espacios multiples
    """
    if not texto:
        return ""
    t = texto.lower().strip()
    # Reemplazar caracteres acentuados y especiales
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

    # Eliminar caracteres no alfanumericos (excepto espacios)
    t = re.sub(r'[^a-z0-9\s]', ' ', t)
    # Colapsar espacios multiples
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def resolver_macrozona(prop):
    """
    Resuelve la macrozona de una propiedad.

    Args:
        prop: dict con datos de la propiedad.
              Debe contener al menos 'zona' (string) o 'lat'/'lon' (float).

    Returns:
        dict con:
            macrozona_id: str
            macrozona_nombre: str
            metodo: "textual" | "bbox" | "default"
            confianza: "ALTA" | "MEDIA" | "BAJA"
    """
    data = _cargar_macrozonas()
    default_id = data.get("default_macrozona", "resto_rosario")

    # Encontrar la macrozona default para nombre
    def _nombre_por_id(mid):
        for m in data["macrozonas"]:
            if m["id"] == mid:
                return m["nombre"]
        return mid

    # 1. MATCH TEXTUAL
    zona = prop.get("zona", "") or prop.get("barrio", "") or ""
    if zona:
        zona_norm = normalizar_texto_zona(zona)
        for mz in data["macrozonas"]:
            for keyword in mz.get("zonas_match_textual", []):
                kw_norm = normalizar_texto_zona(keyword)
                if kw_norm and kw_norm in zona_norm:
                    return {
                        "macrozona_id": mz["id"],
                        "macrozona_nombre": mz["nombre"],
                        "metodo": "textual",
                        "confianza": "ALTA",
                    }

    # 2. MATCH POR BBOX
    lat = prop.get("lat")
    lon = prop.get("lon")
    if lat is not None and lon is not None:
        try:
            lat_f = float(lat)
            lon_f = float(lon)
            # Iterar macrozonas con bbox definido
            for mz in data["macrozonas"]:
                bbox = mz.get("bbox")
                if bbox is None:
                    continue
                if (bbox["lat_min"] <= lat_f <= bbox["lat_max"]
                        and bbox["lon_min"] <= lon_f <= bbox["lon_max"]):
                    return {
                        "macrozona_id": mz["id"],
                        "macrozona_nombre": mz["nombre"],
                        "metodo": "bbox",
                        "confianza": "MEDIA",
                    }
        except (ValueError, TypeError):
            pass

    # 3. DEFAULT
    return {
        "macrozona_id": default_id,
        "macrozona_nombre": _nombre_por_id(default_id),
        "metodo": "default",
        "confianza": "BAJA",
    }


def limpiar_cache():
    """Fuerza recarga del JSON en la proxima llamada."""
    _CACHE["data"] = None
