import re

def parse_address_from_ocr(ocr_text):
    """
    Extrae direcciones de textos OCR de Planos de Mensura.
    Soporta rangos (ej: 2137/2141, 1845 y 1851) y múltiples calles.
    """
    # 1. Limpieza básica
    text = ocr_text.upper().replace('\n', ' ')
    
    # 2. Patrón robusto para capturar calles y números (incluyendo rangos)
    # Ejemplo: CALLE JUJUY Nos 1845 y 1851
    # Ejemplo: B. RIVADAVIA N° 2137 / 2141
    # Ejemplo: CALLE BALCARCE N° 121Bis/123Bis
    pattern = re.compile(
        r"(?:CALLE|AVENIDA|AV\.?|BVAR\.?|BV\.?|PJE\.?|CORTADA)\s+"
        r"([A-ZÁÉÍÓÚÜÑ\.\s]+?)\s+"
        r"(?:N(?:O|OS|RO|ROS|°|º)\s*)?"
        r"(\d{1,5}(?:\s*BIS)?(?:\s*(?:/|Y|-)\s*\d{1,5}(?:\s*BIS)?)*)",
        re.IGNORECASE
    )
    
    matches = pattern.findall(text)
    resultados = []
    
    for match in matches:
        calle = match[0].strip()
        numeros_raw = match[1].strip()
        
        # Limpiar la calle (quitar basuras del OCR)
        calle = re.sub(r'\s+', ' ', calle)
        
        # Parsear los números (separar por /, Y, -)
        nums = re.split(r'\s*(?:/|Y|-)\s*', numeros_raw.upper())
        nums = [n.strip() for n in nums if n.strip()]
        
        resultados.append({
            "calle": calle,
            "numeros": nums,
            "raw": f"{calle} {numeros_raw}"
        })
        
    return resultados

# Tests basados en lo que vimos en los PDFs
test_cases = [
    "CALLE JUJUY Nos 1845 y 1851",
    "CALLE     B. RIVADAVIA N° 2137 / 2141",
    "CALLE BALCARCE N° 121Bis/123Bis/125Bis",
    "calle Rivadavia l.c. 106.03", # Falso positivo potencial de ancho de calle
    "Calle: GUEMES Nos 2102 - 2106 - 2110 - 2114 - 2116",
    "Fachada Calle Balcarce N 13 Bis"
]

print("Resultados de las pruebas del Regex Avanzado:\n")
for t in test_cases:
    res = parse_address_from_ocr(t)
    print(f"Texto: '{t}'")
    print(f"Extraído: {res}\n")
