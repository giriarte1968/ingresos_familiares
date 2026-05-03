from playwright.sync_api import sync_playwright
import json
import re

# Intentar encontrar la API de Propia capturando requests de red

def investigacion_propia_api():
    print("[PROPIA] Investigando API...")
    
    captured_requests = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = context.new_page()
        
        # Capturar requests de red
        def handle_request(request):
            url = request.url
            # Solo capturar requests relevantes (API o propiedades)
            if "api" in url.lower() or "prop" in url.lower() or "json" in url.lower():
                captured_requests.append({
                    "url": url,
                    "method": request.method
                })
        
        page.on("request", handle_request)
        
        url = "https://propia.com.ar"
        print("[PROPIA] Navegando con captura de red...")
        page.goto(url, timeout=60000, wait_until="networkidle")
        page.wait_for_timeout(5000)
        
        # Filtrar requests capturados
        api_requests = [r for r in captured_requests if "api" in r["url"].lower() or "items" in r["url"].lower()]
        
        print(f"[PROPIA] Requests capturados: {len(captured_requests)}")
        print(f"[PROPIA] Requests API/items: {len(api_requests)}")
        
        for r in api_requests[:20]:
            print(f"  [{r['method']}] {r['url']}")
        
        # También probar la búsqueda y capturar los requests que hace
        print("\n[PROPIA] Probando con búsqueda específica...")
        page.goto("https://propia.com.ar/departamentos/rosario/venta", timeout=60000, wait_until="networkidle")
        page.wait_for_timeout(5000)
        
        api_requests2 = [r for r in captured_requests if "api" in r["url"].lower() or "items" in r["url"].lower()]
        
        print(f"[PROPIA] Requests con búsqueda: {len(api_requests2)}")
        for r in api_requests2[:20]:
            print(f"  [{r['method']}] {r['url']}")
        
        # Intentar hacer click en el buscador para ver si hace más requests
        print("\n[PROPIA] Buscando city=1 (Rosario)...")
        try:
            # Cargar URL con parámetros
            page.goto("https://propia.com.ar/items?city=1", timeout=60000, wait_until="networkidle")
            page.wait_for_timeout(5000)
        except:
            pass
        
        api_requests3 = [r for r in captured_requests if "api" in r["url"].lower() or "items" in r["url"].lower()]
        
        print(f"[PROPIA] Requests después: {len(api_requests3)}")
        for r in api_requests3[:20]:
            print(f"  [{r['method']}] {r['url']}")
        
        # Guardar resultados
        with open("propia_api_investigacion.json", "w", encoding="utf-8") as f:
            json.dump({
                "all_requests": captured_requests,
                "api_requests": api_requests,
            }, f, indent=2, ensure_ascii=False, default=str)
        
        print("[PROPIA] Guardado en propria_api_investigacion.json")
        
        browser.close()

if __name__ == "__main__":
    investigacion_propia_api()