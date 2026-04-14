from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    page.goto("https://www.zonaprop.com.ar/departamentos-venta-rosario.html", timeout=30000)
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(3000)
    
    html = page.content()
    
    # Guardar HTML para análisis
    with open("zonaprop_debug.html", "w", encoding="utf-8") as f:
        f.write(html)
    
    print("HTML guardado en zonaprop_debug.html")
    
    # Buscar todos los elementos con data-qa
    elementos = page.query_selector_all("[data-qa]")
    print(f"Elementos con data-qa: {len(elementos)}")
    
    for el in elementos[:20]:
        data_qa = el.get_attribute("data-qa")
        texto = el.inner_text()[:50] if el.inner_text() else ""
        print(f"  data-qa: {data_qa} | texto: {texto}")
    
    browser.close()