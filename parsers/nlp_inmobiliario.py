import re

# RANGOS DE SEGURIDAD
MAX_AJUSTE = 0.35   # +35% máximo
MIN_AJUSTE = -0.30  # -30% mínimo

# DICCIONARIO OPTIMIZADO (ROSARIO)
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

    # --- AMENITIES ---
    "pileta": 0.08,
    "piscina": 0.08,
    "sum": 0.05,
    "gimnasio": 0.05,
    "seguridad 24 horas": 0.07,
    "vigilancia": 0.05,

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
    # Eliminar acentos
    texto = texto.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
    texto = re.sub(r"[^\w\s]", "", texto)
    return texto

def calcular_ajuste_nlp_detallado(descripcion):
    """
    Calcula el ajuste total y devuelve la lista de coincidencias para la UI.
    Aplica lógica de frases largas primero para evitar doble conteo.
    """
    if not descripcion:
        return 0, []

    texto = normalizar_texto(descripcion)
    ajuste = 0
    detecciones = []
    
    # Normalizar también las keys para el match
    # Ordenar por longitud de keyword (frases largas primero)
    features_ordenadas = sorted(FEATURES.items(), key=lambda x: len(x[0]), reverse=True)

    for keyword, valor in features_ordenadas:
        keyword_norm = normalizar_texto(keyword)
        if keyword_norm in texto:
            ajuste += valor
            detecciones.append((keyword, valor))
            # Remover para evitar que sub-frases hagan match
            texto = texto.replace(keyword_norm, " ")

    # Cap de seguridad
    ajuste_final = max(min(ajuste, MAX_AJUSTE), MIN_AJUSTE)
    
    return ajuste_final, detecciones
