from playwright.sync_api import sync_playwright
import re

def scrapear_bienesrosario():
    print("="*60)
    print("SCRAPING BIENESROSARIO CON PLAYWRIGHT")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        
        # Obtener lista de propiedades
        page = browser.new_page()
        page.goto("https://www.bienesrosario.com/venta-departamentos.html", timeout=30000)
        page.wait_for_timeout(3000)
        
        items = page.query_selector_all("div.item")
        print(f"Items en lista: {len(items)}")
        
        # Recolectar links
        links = []
        for item in items[:30]:
            link_el = item.query_selector("a[href*='showProduct']")
            if link_el:
                links.append(link_el.get_attribute("href"))
        
        print(f"Links a propiedades: {len(links)}")
        
        # Visitar cada propiedad individualmente
        props = []
        
        for i, link in enumerate(links):
            try:
                # Abrir nueva pestana
                with browser.new_context().new_page() as prop_page:
                    prop_page.goto(link, timeout=15000)
                    prop_page.wait_for_timeout(2000)
                    
                    # Buscar precio
                    body = prop_page.content()
                    precio_match = re.search(r'U?\$S?\s*([\d.,]+)', body)
                    if not precio_match:
                        continue
                    try:
                        precio = float(precio_match.group(1).replace(".", ""))
                    except:
                        continue
                    
                    # Buscar metros
                    m2_match = re.search(r'(\d+)\s*m[2²]?|(\d+)\s*metros', body)
                    metros = None
                    if m2_match:
                        metros = float(m2_match.group(1) or m2_match.group(2))
                    
                    # Buscar título
                    titulo_match = re.search(r'<h1[^>]*>([^<]+)', body)
                    titulo = titulo_match.group(1).strip() if titulo_match else ""
                
                if not metros or metros < 20 or metros > 300:
                    print(f"{i+1}. Sin m2 válidos")
                    continue
                    
                valor_m2 = precio / metros
                if 400 <= valor_m2 <= 4000:
                    props.append({
                        "precio": precio,
                        "m2": metros,
                        "valor_m2": valor_m2,
                        "fuente": "bienesrosario",
                        "titulo": titulo[:50]
                    })
                    print(f"{i+1:2}. {titulo[:30]:30} | {metros:5.0f}m2 | USD {precio:8,.0f} | ${valor_m2:.0f}/m2")
            except Exception as e:
                print(f"Error {i+1}: {e}")
                continue
        
        browser.close()
    
    print(f"\nTotal propiedades extraídas: {len(props)}")
    if props:
        prom = sum(p['valor_m2'] for p in props) / len(props)
        print(f"PROMEDIO USD/m2: ${prom:.0f}")
    
    return props

if __name__ == "__main__":
    scrapear_bienesrosario()