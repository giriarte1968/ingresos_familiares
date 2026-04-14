from playwright.sync_api import sync_playwright

def debug_buscadorprop():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        url = "https://www.buscadorprop.com.ar/rosario/departamento/venta"
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(3000)
        
        # Buscar cualquier clase con "item" o "card"
        items = page.query_selector_all("[class*='item'], [class*='card'], [class*='listing']")
        print(f"Items with class patterns: {len(items)}")
        
        # Ver todos los articles
        articles = page.query_selector_all("article")
        print(f"Articles: {len(articles)}")
        
        # Buscar por estructura más simple
        all_divs = page.query_selector_all("div")
        print(f"All divs: {len(all_divs)}")
        
        # Tomar el primer div y ver su clase
        for div in all_divs[:20]:
            cls = div.get_attribute("class")
            if cls:
                print(f"Div class: {cls}")
        
        # HTML sample
        html = page.content()
        
        # Save para análisis
        with open("buscadorprop.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        print(f"\nHTML saved: {len(html)} chars")
        
        browser.close()

debug_buscadorprop()