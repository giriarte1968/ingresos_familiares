from playwright.sync_api import sync_playwright
import re

def scrapear_bienesrosario():
    print("="*60)
    print("SCRAPING BIENESROSARIO (SIMPLE)")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto("https://www.bienesrosario.com/venta-departamentos.html", timeout=30000)
        page.wait_for_timeout(3000)
        
        # Tomar solo los primeros items que tengan m2 en el listado
        items = page.query_selector_all("div.item")
        print(f"Items: {len(items)}")
        
        props = []
        
        for i, item in enumerate(items[:30]):
            try:
                # Precio
                precio_el = item.query_selector(".precio")
                if not precio_el:
                    continue
                precio_text = precio_el.inner_text()
                precio_match = re.search(r'([\d.,]+)', precio_text.replace(".", ""))
                if not precio_match:
                    continue
                precio = float(precio_match.group(1).replace(",", "."))
                
                # Buscar precio en el texto del item
                item_text = item.inner_text()
                
                # Patrones de m2 que aparecen en ROSARIOGARAGE
                # Buscar en el item el patrón como "45 m2" o "45m2"
                for patron in [r'(\d{2,3})\s*m[2²]?', r'(\d{2,3})\s*mt[s]?']:
                    m_match = re.search(patron, item_text)
                    if m_match:
                        metros = float(m_match.group(1))
                        if 20 < metros < 300:
                            # Algunos items tienen "X ambientes" que no son m2
                            # Filtrar solo los que tienen sentido
                            if 25 <= metros <= 200:
                                break
                else:
                    metros = None
                
                # Título
                titulo_el = item.query_selector(".list_type_propiedades")
                titulo = titulo_el.inner_text() if titulo_el else ""
                
                if not metros:
                    # No tiene m2 visible - skip
                    if i < 10:
                        print(f"{i+1}. Sin m2: {titulo[:40]}")
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
                    print(f"{i+1:2}. {titulo[:35]:35} | {metros:5.0f}m2 | USD {precio:10,.0f} | ${valor_m2:.0f}/m2")
            except Exception as e:
                continue
        
        browser.close()
    
    print(f"\nTotal propiedades: {len(props)}")
    if props:
        prom = sum(p['valor_m2'] for p in props) / len(props)
        print(f"PROMEDIO USD/m2: ${prom:.0f}")
    
    return props

if __name__ == "__main__":
    scrapear_bienesrosario()