from playwright.sync_api import sync_playwright
import json
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def get_random_ua():
    return random.choice(USER_AGENTS)

def investigacion_propia_v3():
    print("[PROPIA] Investigando estructura v3...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=get_random_ua(),
            java_script_enabled=True,
            ignore_https_errors=True
        )
        page = context.new_page()
        
        url = "https://propia.com.ar"
        print(f"[PROPIA] Navegando a home: {url}")
        
        try:
            page.goto(url, timeout=60000, wait_until="networkidle")
            print(f"[PROPIA] Page loaded. Title: {page.title()}")
            page.wait_for_timeout(5000)
            
            # Capturar lo que hay en la página
            content = page.content()
            print(f"[PROPIA] HTML length: {len(content)}")
            
            # Verificar si hay contenido
            if len(content) < 5000:
                print("[PROPIA] ⚠️ Página casi vacía - posible bloqueo o redirect")
                print(content[:1000])
            else:
                print("[PROPIA] ✓ Página con contenido")
                
                # Buscar cualquier enlace
                links = page.query_selector_all("a")
                print(f"[PROPIA] Total links encontrados: {len(links)}")
                
                # Filtrar enlaces relevantes
                relevant = []
                for link in links[:100]:
                    href = link.get_attribute("href")
                    if href and ("propia" in href or "departamento" in href or "rosario" in href or "venta" in href):
                        relevant.append(href)
                
                print(f"[PROPIA] Links relevantes: {len(relevant)}")
                for u in relevant[:15]:
                    print(f"  {u}")
                
                # También buscar si hay iframes (algunos portales usan iframes)
                iframes = page.query_selector_all("iframe")
                print(f"[PROPIA] Iframes: {len(iframes)}")
        
        except Exception as e:
            print(f"[PROPIA] Error: {e}")
        
        browser.close()

if __name__ == "__main__":
    investigacion_propia_v3()