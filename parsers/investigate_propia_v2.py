from playwright.sync_api import sync_playwright
import json
import re
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def get_random_ua():
    return random.choice(USER_AGENTS)

def investigacion_propia_v2():
    print("[PROPIA] Investigando estructura v2...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=get_random_ua())
        page = context.new_page()
        
        # Probar diferentes URLs
        urls_to_test = [
            "https://propia.com.ar/departamentos/rosario/venta",
            "https://propia.com.ar/propiedades/venta/departamento/rosario",
            "https://propia.com.ar/buscar?operacion=venta&tipo=departamento&ciudad=rosario",
            "https://propia.com.ar",
        ]
        
        for url in urls_to_test:
            print(f"\n[PROPIA] Probando: {url}")
            page.goto(url, timeout=30000)
            page.wait_for_timeout(5000)
            
            # Esperar que cargue contenido dinámico
            page.wait_for_selector("body", timeout=10000)
            
            # Obtener contenido
            content = page.content()
            print(f"  HTML length: {len(content)} chars")
            
            # Buscar si hay contenido relevante
            if "departamento" in content.lower() or "propiedad" in content.lower():
                print(f"  ✓ Contiene referencias a propiedades")
            
            # Buscar artículos/cards
            cards = page.query_selector_all("article, .card, .property, .listing-item")
            print(f"  Cards найдены: {len(cards)}")
            
            # Buscar enlaces específicos de Propia
            links = page.query_selector_all("a")
            propria_links = []
            for link in links[:50]:
                href = link.get_attribute("href")
                if href and "propiedades" in href:
                    propia_links.append(href)
            
            print(f"  Links con 'propiedades': {len(propia_links)}")
            if propria_links[:5]:
                for u in propria_links[:5]:
                    print(f"    {u}")
            
            # Si encontramos algo, salir
            if propria_links:
                print(f"  ✓ Encontramos {len(propia_links)} enlaces!")
                break
            
            # Si no hay nada, esperar más tiempo
            print(f"  Esperando carga dinámica...")
            page.wait_for_timeout(5000)
            
            links2 = page.query_selector_all("a")
            propria_links2 = [l.get_attribute("href") for l in links2[:100] if "propiedades" in (l.get_attribute("href") or "")]
            print(f"  Links después de esperar: {len(propia_links2)}")
            if propria_links2[:5]:
                for u in propria_links2[:5]:
                    print(f"    {u}")
                break
        
        browser.close()

if __name__ == "__main__":
    investigacion_propia_v2()