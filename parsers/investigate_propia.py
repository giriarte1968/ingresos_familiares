from playwright.sync_api import sync_playwright
import json
import re
import random
import os

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def get_random_ua():
    return random.choice(USER_AGENTS)

def investigacion_propia():
    print("[PROPIA] Investigando estructura actual...")
    
    props = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent=get_random_ua())
        page = context.new_page()
        
        # Ir a la página principal de Propia Rosario Venta
        url = "https://propia.com.ar/departamentos/rosario/venta"
        print(f"[PROPIA] Cargando: {url}")
        
        page.goto(url, timeout=30000)
        page.wait_for_load_state("domcontentloaded", timeout=20000)
        page.wait_for_timeout(3000)
        
        # Scroll para cargar propiedades
        for _ in range(3):
            page.evaluate("window.scrollBy(0, 500)")
            page.wait_for_timeout(1000)
        
        # Obtener HTML para analizar estructura
        html = page.content()
        
        # Buscar enlaces a propiedades
        # Propia usa enlaces tipo /propiedades/[slug]
        links = page.query_selector_all("a[href^='/propiedades/']")
        print(f"[PROPIA] Encontrados {len(links)} enlaces a propiedades")
        
        # Tomar muestra de las primeras 10 URLs
        sample_urls = []
        for link in links[:20]:
            href = link.get_attribute("href")
            if href and "/propiedades/" in href:
                sample_urls.append(href)
        
        print(f"[PROPIA] Muestra de URLs:")
        for u in sample_urls[:10]:
            print(f"  {u}")
        
        #visitar una propiedad para ver estructura de detalle
        if sample_urls:
            first_url = sample_urls[0]
            print(f"[PROPIA] Visitando detalle: {first_url}")
            page.goto(first_url, timeout=30000)
            page.wait_for_timeout(3000)
            
            detail_html = page.content()
            
            # Buscar año de construcción en el detalle
            # Patrones comunes: "Año", "Construido", "Antigüedad", "Edificio"
            year_patterns = [
                r'(?:año|anio|construido|construccion|edificio|del año)\s*:?\s*(\d{4})',
                r'(\d{4})\s*(?:año|anio)',
                r'Antigüedad[:\s]*(\d+)\s*años',
                r'estrenar',
            ]
            
            import re
            for pattern in year_patterns:
                matches = re.findall(pattern, detail_html, re.I)
                print(f"[PROPIA] Pattern '{pattern}': {matches}")
            
            # Buscar la dirección para obtener coordenadas
            print(f"[PROPIA] Título de propiedad:")
            title_el = page.query_selector("h1")
            if title_el:
                print(f"  {title_el.inner_text()}")
            
            # Buscar precio
            price_el = page.query_selector("[class*='precio']")
            if price_el:
                print(f"  Precio: {price_el.inner_text()}")
        
        browser.close()
        
        # Guardar muestra en archivo
        with open("propia_sample.json", "w", encoding="utf-8") as f:
            json.dump({
                "sample_urls": sample_urls,
                "total_links": len(links)
            }, f, indent=2, ensure_ascii=False)
        
        print(f"[PROPIA] Investigación completada. Muestra guardada en propria_sample.json")

if __name__ == "__main__":
    investigacion_propia()