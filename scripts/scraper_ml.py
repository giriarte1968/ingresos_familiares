from playwright.sync_api import sync_playwright

def debug_ml():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Ir directo con parámetros de búsqueda
        url = "https://listado.mercadolibre.com.ar/inmuebles/departamentos/rosario-santa-fe_CEO"
        page.goto(url, timeout=30000)
        page.wait_for_timeout(5000)
        
        print(f"URL: {page.url}")
        print(f"HTML length: {len(page.content())}")
        
        # Buscar estructura
        items = page.query_selector_all(".ui-search-result, li")
        print(f"Items: {len(items)}")
        
        browser.close()

debug_ml()