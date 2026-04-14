from playwright.sync_api import sync_playwright
import re

def scrapear_ttl():
    print("="*60)
    print("SCRAPING TTL PROPIEDADES")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        page.goto("https://www.ttlpropiedades.com/Venta", timeout=30000)
        page.wait_for_timeout(3000)
        
        propiedades = page.query_selector_all("ul#propiedades > li")
        print(f"Propiedades: {len(propiedades)}")
        
        props = []
        
        for prop in propiedades:
            try:
                precio_el = prop.query_selector("[class*='valor']")
                if not precio_el:
                    continue
                
                precio_text = precio_el.inner_text()
                precio_match = re.search(r'USD([\d.,]+)', precio_text)
                if not precio_match:
                    continue
                
                # ARREGLAR: el formato es USD79.000 = USD 79.000 (79 mil pesos/dolares)
                precio_str = precio_match.group(1)
                # Los precios en TTL están en miles (ej: 79.000 = 79,000)
                precio = float(precio_str.replace(",", ""))
                
                # Si el precio es menor a 1000, probablemente es miles
                if precio < 1000:
                    precio = precio * 1000
                
                m2_el = prop.query_selector(".prop-data")
                if not m2_el:
                    continue
                
                m2_text = m2_el.inner_text()
                m2_match = re.search(r'([\d.,]+)\s*m', m2_text)
                if not m2_match:
                    continue
                
                metros = float(m2_match.group(1).replace(",", "."))
                
                if not (20 < metros < 250):
                    continue
                
                link = prop.query_selector("a[href]")
                titulo = ""
                if link:
                    href = link.get_attribute("href")
                    titulo = href.split("/")[-1] if href else ""
                    titulo = titulo.replace("-", " ")[:50]
                
                valor_m2 = precio / metros
                if 400 <= valor_m2 <= 4000:
                    props.append({
                        "precio": precio,
                        "m2": metros,
                        "valor_m2": valor_m2,
                        "fuente": "ttl",
                        "titulo": titulo
                    })
                    print(f"  {titulo[:40]:40} | {metros:6.1f}m2 | USD {precio:8,.0f} | ${valor_m2:.0f}/m2")
            except Exception as e:
                continue
        
        browser.close()
    
    print(f"\nTotal propiedades: {len(props)}")
    if props:
        prom = sum(p['valor_m2'] for p in props) / len(props)
        print(f"PROMEDIO USD/m2: ${prom:.0f}")
    
    return props

if __name__ == "__main__":
    scrapear_ttl()