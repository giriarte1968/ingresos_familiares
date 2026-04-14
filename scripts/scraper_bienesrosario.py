from playwright.sync_api import sync_playwright
import re

def scrapear_bienesrosario():
    print("="*60)
    print("SCRAPING BIENESROSARIO (SIN LOGIN - SOLO LISTA)")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        # Ir directo a lista de propiedades
        url = "https://www.bienesrosario.com/venta-departamentos.html"
        page.goto(url, timeout=30000)
        page.wait_for_timeout(3000)
        
        print(f"URL: {page.url}")
        
        # Los items tienen clase .item
        items = page.query_selector_all("div.item")
        print(f"Items en lista: {len(items)}")
        
        props = []
        
        # Analizar los primeros items
        for i, item in enumerate(items[:20]):
            texto = item.inner_text()
            
            # Buscar precio - buscar "U$S" seguido de números
            precio_match = re.search(r'U?\$S?\s*([\d.,]+)', texto)
            
            # Buscar m2 - buscar números seguidos de "m2"
            m2_match = re.search(r'(\d+)\s*m[2²]?', texto)
            
            if precio_match and m2_match:
                try:
                    precio = float(precio_match.group(1).replace(".", ""))
                    metros = float(m2_match.group(1))
                    
                    if 20 < metros < 250 and precio > 0:
                        valor_m2 = precio / metros
                        
                        if 400 <= valor_m2 <= 4000:
                            # Título
                            titulo = texto.split("\n")[0][:40] if texto else ""
                            
                            props.append({
                                "precio": precio,
                                "m2": metros,
                                "valor_m2": valor_m2,
                                "fuente": "bienesrosario",
                                "titulo": titulo
                            })
                            print(f"{i+1:2}. {titulo[:35]:35} | {metros:5.0f}m2 | ${precio:8,.0f} | ${valor_m2:.0f}/m2")
                except:
                    continue
        
        browser.close()
    
    print(f"\nTotal propiedades: {len(props)}")
    if props:
        prom = sum(p['valor_m2'] for p in props) / len(props)
        print(f"PROMEDIO USD/m2: ${prom:.0f}")
    
    return props

scrapear_bienesrosario()