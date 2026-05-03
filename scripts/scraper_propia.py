import re
import time
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def scrapear_propia(max_pages=5):
    print("="*60)
    print(f"SCRAPING PROPIA (PAGINADO - MAX {max_pages} PAGINAS)")
    print("="*60)
    
    props = []
    procesados = set()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for pagina_actual in range(1, max_pages + 1):
            print(f"\n--- Procesando Página {pagina_actual} ---")
            
            # URL de búsqueda con paginación
            url = f"https://propia.com.ar/propiedades?operation=1&type=2&location_city_id=1&page={pagina_actual}"
            
            try:
                page.goto(url, timeout=30000)
                # Esperar a que las tarjetas carguen
                page.wait_for_timeout(4000)
                
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                
                cards = soup.find_all('div', class_='bg-card')
                print(f"Tarjetas encontradas en pag {pagina_actual}: {len(cards)}")
                
                if not cards:
                    print("No se encontraron más tarjetas, terminando paginación.")
                    break
                
                for card in cards:
                    try:
                        text = card.text
                        
                        if text in procesados:
                            continue
                        procesados.add(text)
                        
                        # Buscar precio
                        precio_match = re.search(r'(U\$S|USD)\s*([\d.,]+)', text)
                        if not precio_match:
                            continue
                        
                        precio_str = precio_match.group(2).replace('.', '').replace(',', '.')
                        precio = float(precio_str)
                        
                        # Buscar m2
                        metros = None
                        for patron in [r'(\d{2,3})\s*m[2²]?', r'(\d{2,3})\s*mt[s]?']:
                            m_match = re.search(patron, text)
                            if m_match:
                                metros = float(m_match.group(1))
                                if 20 <= metros <= 300:
                                    break
                        
                        if not metros:
                            continue
                            
                        # Extraer titulo
                        h3 = card.find('h3')
                        h2 = card.find('h2')
                        if h3:
                            titulo = h3.text.strip()
                        elif h2:
                            titulo = h2.text.strip()
                        else:
                            titulo_match = re.search(r'Siguiente(.*?)Departamento', text)
                            if titulo_match:
                                titulo = titulo_match.group(1).strip()
                            else:
                                titulo = text[:50].strip()
                        
                        titulo = re.sub(r'^(Siguiente|Anterior)', '', titulo).strip()
                        
                        valor_m2 = precio / metros
                        if 400 <= valor_m2 <= 4000:
                            props.append({
                                "precio": precio,
                                "m2": metros,
                                "valor_m2": valor_m2,
                                "fuente": "propia",
                                "titulo": titulo[:50]
                            })
                            print(f"[{pagina_actual}] {len(props):3}. {titulo[:30]:30} | {metros:5.0f}m2 | USD {precio:10,.0f} | ${valor_m2:.0f}/m2")
                            
                    except Exception as e:
                        continue
                        
            except Exception as e:
                print(f"Error en página {pagina_actual}: {e}")
                
        browser.close()
            
    print(f"\nTotal propiedades únicas extraídas: {len(props)}")
    if props:
        prom = sum(p['valor_m2'] for p in props) / len(props)
        print(f"PROMEDIO USD/m2 de la muestra: ${prom:.0f}")
    
    return props

if __name__ == "__main__":
    scrapear_propia(max_pages=5)
