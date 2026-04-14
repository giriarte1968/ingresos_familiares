from playwright.sync_api import sync_playwright
import re

def scrapear_lacapital():
    print("="*60)
    print("SCRAPING LA CAPITAL")
    print("="*60)
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        url = "https://inmuebles.lacapital.com.ar/buscar-propiedades/?inmueble_hidden=Departamento&localidad=487&operacion_hidden=Venta"
        page.goto(url, timeout=30000)
        page.wait_for_load_state("networkidle", timeout=15000)
        page.wait_for_timeout(3000)
        
        props_divs = page.query_selector_all(".avisodestacado")
        print(f"Propiedades: {len(props_divs)}")
        
        props = []
        
        for div in props_divs:
            try:
                texto = div.inner_text()
                
                # Buscar m2 - formato "39 M2" o "39 M"
                m2_match = re.search(r"(\d+)\s*M", texto)
                if not m2_match:
                    continue
                
                try:
                    metros = int(m2_match.group(1))
                except:
                    continue
                
                # Solo deptos pequeños
                if not (20 < metros < 250):
                    continue
                
                # Buscar precio - último número después de "--"
                # Formato: "X M  Y  Z  --  PRECIO"
                precio_match = re.search(r"--\s*(\d+)", texto)
                if not precio_match:
                    continue
                
                try:
                    precio = int(precio_match.group(1))
                    if precio < 10000:
                        precio = precio * 1000
                except:
                    continue
                
                # Título
                dir_el = div.query_selector(".dir")
                titulo = dir_el.inner_text() if dir_el else ""
                titulo = titulo.replace("Departamento en Venta", "").replace("-", " ").strip()[:50]
                
                valor_m2 = precio / metros
                if 400 <= valor_m2 <= 4000:
                    props.append({
                        "precio": precio,
                        "m2": metros,
                        "valor_m2": valor_m2,
                        "fuente": "lacapital",
                        "titulo": titulo
                    })
                    print(f"  {titulo[:40]:40} | {metros:5.0f}m2 | ${precio:8,.0f} | ${valor_m2:.0f}/m2")
            except Exception as e:
                continue
        
        browser.close()
    
    print(f"\nTotal propiedades: {len(props)}")
    if props:
        prom = sum(p['valor_m2'] for p in props) / len(props)
        print(f"PROMEDIO USD/m2: ${prom:.0f}")
    
    return props

if __name__ == "__main__":
    scrapear_lacapital()