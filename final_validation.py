import requests
import re
import urllib.parse
import json

# Simulatión de las funciones del app.py
CATEGORIAS_WEB = {
    'comercios': {
        'restaurant': ['restaurant', 'pizzer', 'pizza', 'gastron', 'parrilla', 'bodegon'],
        'limpieza': ['limpieza', 'quimica', 'insumos', 'quimico', 'higiene', 'limp'],
        'estacionamiento': ['estacionamiento', 'parking', 'cochera', 'garage', 'gge', 'park'],
    }
}

CATEGORIAS_EGRESOS = {
    'comercios': {
        'restaurant': ['restaurant', 'resto', 'pizzer', 'pizza', 'parrilla', 'bodegon'],
        'limpieza': ['limpieza', 'quimica', 'articulos de', 'alberto rey', 'higiene'],
        'estacionamiento': ['estacionamiento', 'parking', 'cochera', 'garage', 'gge', 'park'],
    }
}

def mock_buscar_web(nombre_comercio):
    headers = {'User-Agent': 'Mozilla/5.0'}
    busqueda = f"{nombre_comercio} rubro gastronomia o comercio Argentina"
    url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(busqueda)}"
    try:
        r = requests.get(url, headers=headers, timeout=10)
        links = re.findall(r'<a[^>]+class="result-link"[^>]*>([^<]+)</a>', r.text, re.IGNORECASE)
        snippets = re.findall(r'<td[^>]+class="result-snippet"[^>]*>([^<]+)</td>', r.text, re.IGNORECASE)
        info = ""
        for i in range(min(3, len(links))):
            info += links[i] + " "
            if i < len(snippets): info += snippets[i] + " "
        return info.strip()
    except: return ""

def mock_categorizar(descripcion):
    desc_lower = descripcion.lower()
    # Check local
    for subcat, words in CATEGORIAS_EGRESOS['comercios'].items():
        for w in words:
            if w in desc_lower: return 'comercios', subcat
    
    # Check web
    info_web = mock_buscar_web(descripcion).lower()
    for subcat, words in CATEGORIAS_WEB['comercios'].items():
        for w in words:
            if w in info_web: return 'comercios', subcat
            
    return 'otros', 'otros'

print("--- VALIDACIÓN FINAL ---")
test_cases = ["La Gran Argentina", "Alberto Rey", "Estacionamiento Ocampo", "Pluss Servicios"]
for tc in test_cases:
    cat, subcat = mock_categorizar(tc)
    print(f"Comercio: {tc:25} -> {cat}/{subcat}")
