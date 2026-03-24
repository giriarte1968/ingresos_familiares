import requests
import re
import urllib.parse

def test_search(query):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
    print(f"Buscando: {url}")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {r.status_code}")
        # Buscar títulos de resultados
        titulos = re.findall(r'<a class="result__a"[^>]*>([^<]+)</a>', r.text, re.IGNORECASE)
        print(f"Títulos encontrados ({len(titulos)}):")
        for t in titulos[:5]:
            print(f"- {t}")
        # Buscar snippets (descripciones)
        snippets = re.findall(r'<a class="result__snippet"[^>]*>([^<]+)</a>', r.text, re.IGNORECASE)
        print(f"Snippets encontrados ({len(snippets)}):")
        for s in snippets[:5]:
            print(f"- {s}")
    except Exception as e:
        print(f"Error: {e}")

test_search("La Gran Argentina Rosario rubro")
test_search("Pizzería Rosati Rosario")
test_search("Estacionamiento Ocampo Rosario")
