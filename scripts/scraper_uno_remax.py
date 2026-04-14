from playwright.sync_api import sync_playwright
import re

def scrapear_remax():
    print("="*60)
    print("SCRAPING REMAX ARGENTINA")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # URL correcta - filtrando por Rosario y tipo departamento
        url = "https://www.remax.com.ar/listings/buy?locations=in%3A%3A%3A460%3Cb%3ERosario%3C%2Fb%3E&in%3AtypeId=1"
        page.goto(url, timeout=30000)
        
        # Esperar a que cargue el contenido
        page.wait_for_load_state("networkidle", timeout=20000)
        page.wait_for_timeout(5000)
        
        print(f"URL: {page.url[:70]}")
        
        # Buscar resultados
        items = page.query_selector_all("[class*='listing'], [class*='property'], article")
        print(f"Items encontrados: {len(items)}")
        
        # También buscar por estructura
        if not items:
            # Tomar HTML y buscar precios
            html = page.content()
            
            # Contar patrones
            usd_count = html.count("USD")
            print(f"USD en página: {usd_count}")
        
        # Intentar con clase más genérica
        listings = page.query_selector_all(".listing-cards, .listings-container, .results")
        print(f"Listings containers: {len(listings)}")
        
        browser.close()
    
    return []

if __name__ == "__main__":
    scrapear_remax()