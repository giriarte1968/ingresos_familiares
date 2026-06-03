import re

# RANGOS DE SEGURIDAD
MAX_AJUSTE = 0.35   # +35% máximo
MIN_AJUSTE = -0.30  # -30% mínimo

# Mapa de exclusión NLP: si un amenity está presente en detalles_categoria,
# las keywords equivalentes en NLP no deben sumar.
AMENITY_NLP_EXCLUSION_MAP = {
    "parrilla_propia": [
        "parrilla", "parrillero", "parrillero propio", "asador"
    ],
    "parrilla_compartida": [
        "parrilla", "parrillero", "parrillero comun", "parrillero común",
        "quincho con parrilla"
    ],
    "terraza_compartida": [
        "terraza compartida", "terraza comun", "terraza común"
    ],
    "pileta": ["pileta", "piscina"],
    "sum": ["sum", "salon de usos multiples", "salón de usos múltiples"],
    "gym": ["gym", "gimnasio"],
    "seguridad_24hs": [
        "seguridad 24 horas", "seguridad 24hs", "vigilancia"
    ],
    "seguridad_tag": ["tag de seguridad", "tag seguridad"],
    "seguridad_camaras": ["camaras de seguridad", "cámaras de seguridad"],
    "seguridad_totem": ["totem de seguridad", "tótem de seguridad"],
    "aberturas_premium": [
        "aberturas premium", "dvh", "doble vidrio", "doble vitreo"
    ],
    "caldera_central": ["caldera central"],
    "radiadores": [
        "radiadores", "calefaccion por radiadores",
        "calefacción por radiadores"
    ],
    "balcon_terraza": ["balcon terraza", "balcón terraza"],
    "terraza_comun": ["terraza comun", "terraza común"],
    "baulera": ["baulera", "bauleras"],
    "cocheras": ["cochera", "cocheras", "garage"],
}


def _keywords_a_excluir(amenities_present):
    """Retorna set de keywords NLP a excluir según amenities presentes."""
    excluir = set()
    if not amenities_present:
        return excluir
    for amenity in amenities_present:
        key = amenity.lower().replace(" ", "_")
        if key == "parrilla":
            key = "parrilla_compartida"
        if key in AMENITY_NLP_EXCLUSION_MAP:
            excluir.update(AMENITY_NLP_EXCLUSION_MAP[key])
    return excluir


# DICCIONARIO OPTIMIZADO (ROSARIO) v2 — pesos reducidos para amenities comunes
FEATURES = {
    # --- PREMIUM ---
    "vista al río": 0.15,
    "vista franca al río": 0.18,
    "frente al río": 0.18,
    "primera línea río": 0.20,

    # --- ESTADO ---
    "a estrenar": 0.20,
    "reciclado": 0.10,
    "reciclado a nuevo": 0.15,
    "refaccionado": 0.08,

    # --- LUZ / ORIENTACIÓN ---
    "muy luminoso": 0.07,
    "luminoso": 0.05,
    "orientación norte": 0.06,

    # --- CALIDAD ---
    "premium": 0.10,
    "alta gama": 0.12,
    "excelentes terminaciones": 0.08,

    # --- EXTERIORES ---
    "balcón terraza": 0.10,
    "terraza exclusiva": 0.15,
    "patio": 0.05,
    "quincho": 0.08,
    "parrillero": 0.06,

    # --- AMENITIES (pesos reducidos vs v1) ---
    "pileta": 0.02,
    "piscina": 0.02,
    "parrilla": 0.01,
    "parrillero": 0.01,
    "terraza compartida": 0.01,
    "terraza comun": 0.01,
    "terraza común": 0.01,
    "sum": 0.01,
    "gimnasio": 0.01,
    "gym": 0.01,
    "seguridad 24 horas": 0.02,
    "vigilancia": 0.02,

    # --- UBICACIÓN (micro señales) ---
    "cerca del río": 0.07,
    "zona río": 0.06,
    "zona facultades": 0.05,

    # --- NEGATIVOS ---
    "a refaccionar": -0.20,
    "para reciclar": -0.18,
    "estado original": -0.10,

    "interno": -0.10,
    "muy interno": -0.12,
    "oscuro": -0.08,

    "planta baja": -0.07,
    "sin ascensor": -0.08,

    "zona insegura": -0.12,
    "ruidoso": -0.06
}


def normalizar_texto(texto):
    if not texto: return ""
    texto = texto.lower()
    texto = texto.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    texto = re.sub(r"[^\w\s]", "", texto)
    return texto


def calcular_ajuste_nlp_detallado(descripcion, amenities_present=None):
    """
    Calcula el ajuste total y devuelve la lista de coincidencias para la UI.
    Si amenities_present contiene keys estructurados, las keywords NLP
    equivalentes se excluyen para evitar doble conteo.
    Backward compatible: amenities_present=None funciona como antes.
    """
    if not descripcion:
        return 0, []

    texto = normalizar_texto(descripcion)
    palabras_excluir = _keywords_a_excluir(amenities_present)

    ajuste = 0
    detecciones = []

    features_ordenadas = sorted(FEATURES.items(), key=lambda x: len(x[0]), reverse=True)

    for keyword, valor in features_ordenadas:
        keyword_norm = normalizar_texto(keyword)

        # Excluir si el amenity estructurado ya cubre esta señal
        if keyword_norm in palabras_excluir:
            continue

        if keyword_norm in texto:
            ajuste += valor
            detecciones.append((keyword, valor))
            texto = texto.replace(keyword_norm, " ")

    ajuste_final = max(min(ajuste, MAX_AJUSTE), MIN_AJUSTE)

    return ajuste_final, detecciones
