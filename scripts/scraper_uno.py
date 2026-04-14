from playwright.sync_api import sync_playwright
import re

def scrapear_uno():
    print("="*60)
    print("SCRAPING UNO PROPIEDADES")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Ir a buscar departamentos en venta Rosario
        url = "https://www.unopropiedades.com.ar/departamento/venta/rosario"
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=20000)
        page.wait_for_timeout(5000)
        
        print(f"URL: {page.url[:60]}")
        print(f"HTML length: {len(page.content())}")
        
        # Buscar items
        items = page.query_selector_all("[class*='property'], [class*='card'], article")
        print(f"Items: {len(items)}")
        
        # Si no hay, buscar por estructura
        if not items:
            items = page.query_selector_all("div[class]")
            print(f"Todos los divs: {len(items)}")
        
        # Guardar HTML para debug
        if items:
            html_file = open("uno_debug.html", "w", encoding="utf-8")
            html_file.write(page.content())
            html_file.close()
            print("HTML guardado en uno_debug.html")
        
        browser.close()
    
    return []

if __name__ == "__main__":
    scrapear_uno()