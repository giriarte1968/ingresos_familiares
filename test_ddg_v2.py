import requests
import re
import urllib.parse

def test_search(query):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    url = f"https://lite.duckduckgo.com/lite/?q={urllib.parse.quote(query)}"
    print(f"\nBuscando: {url}")
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"Status: {r.status_code}")
        
        # Buscar todos los enlaces y su texto
        links = re.findall(r'<a[^>]+class="result-link"[^>]*>([^<]+)</a>', r.text, re.IGNORECASE)
        snippets = re.findall(r'<td[^>]+class="result-snippet"[^>]*>([^<]+)</td>', r.text, re.IGNORECASE)
        
        print(f"Resultados encontrados: {len(links)}")
        for i in range(min(5, len(links))):
            link_text = links[i].strip()
            snippet_text = snippets[i].strip() if i < len(snippets) else "N/A"
            print(f"{i+1}. [{link_text}]")
            print(f"   Snippet: {snippet_text[:150]}...")
            
    except Exception as e:
        print(f"Error: {e}")

print("--- PRUEBA 1: La Gran Argentina ---")
test_search("La Gran Argentina Rosario restaurant")

print("\n--- PRUEBA 2: Alberto Rey ---")
test_search("Rey Diego Alberto CUIT rubro")

print("\n--- PRUEBA 3: Rosati Damian Pablo ---")
test_search("Rosati Damian Pablo pizeria")
