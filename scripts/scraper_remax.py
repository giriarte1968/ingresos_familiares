from playwright.sync_api import sync_playwright
import re

def scrapear_remax():
    print("="*60)
    print("SCRAPING REMAX (PLAYWRIGHT)")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Ir a la pagina principal y buscar desde ahí
        page.goto("https://www.remax.com.ar/", timeout=30000)
        page.wait_for_timeout(3000)
        
        # Buscar input de búsqueda o navegar
        buscar_link = page.query_selector("a[href*='buscar']")
        if buscar_link:
            href = buscar_link.get_attribute("href")
            print(f"Link buscar: {href}")
        
        # Ir directo a resultados con filtros
        url = "https://www.remax.com.ar/inmuebles/venta/rosario/departamento"
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=20000)
        page.wait_for_timeout(5000)
        
        html = page.content()
        print(f"HTML length: {len(html)}")
        
        # Buscar contenido renderizado
        if len(html) > 5000:
            print("Contenido cargado correctamente")
            
            # Buscar estructura
            items = page.query_selector_all("[class*='property'], [class*='listing'], article")
            print(f"Items: {len(items)}")
            
        else:
            print("Contenido minimal - posible redirect o protección")
        
        browser.close()

if __name__ == "__main__":
    scrapear_remax()