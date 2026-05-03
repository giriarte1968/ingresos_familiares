import re
import time
import json
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

def scrapear_propia_enriquecido(max_pages=1):
    """
    Scraper enriquecido para propia.com.ar
    Extrae: precio, m2, dormitorios, direccion, tipo, operacion, url
    Output: propria.json
    """
    print("="*60)
    print("SCRAPING PROPIA ENRIQUECIDO")
    print("="*60)
    
    props = []
    procesados = set()
    
    # Tipos de operación
    # operation=1: Venta, operation=2: Alquiler
    # type=1: Casa, type=2: Departamento, type=3: PH
    operaciones = [
        {"operation": "1", "op_nombre": "venta"},
        {"operation": "2", "op_nombre": "alquiler"},
    ]
    tipos = [
        {"type": "2", "tipo_nombre": "departamento"},
        {"type": "1", "tipo_nombre": "casa"},
        {"type": "3", "tipo_nombre": "ph"},
    ]
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        for op in operaciones:
            for tipo in tipos:
                for pagina in range(1, max_pages + 1):
                    url = (
                        f"https://propia.com.ar/propiedades"
                        f"?operation={op['operation']}"
                        f"&type={tipo['type']}"
                        f"&location_city_id=1"
                        f"&page={pagina}"
                    )
                    
                    try:
                        page.goto(url, timeout=30000)
                        page.wait_for_timeout(4000)
                        
                        html = page.content()
                        soup = BeautifulSoup(html, 'html.parser')
                        
                        # Buscar cards - probar múltiples métodos
                        cards = soup.find_all('div', class_=lambda x: x and 'card' in x.lower())
                        if not cards:
                            cards = soup.find_all('article')
                        if not cards:
                            cards = soup.find_all('div', class_='bg-white')
                        if not cards:
                            # Fallback: buscar cualquier bloque con precio
                            cards = soup.find_all(text=re.compile(r'U\$S|USD'))
                            cards = [c.parent for c in cards[:20] if c.parent]
                        
                        page_count = len(cards)
                        if page_count == 0:
                            print(f"  [{op_nombre}/{tipo_nombre}] Pág {pagina}: sin resultados")
                            continue
                        
                        print(f"  [{op['op_nombre']}/{tipo['tipo_nombre']}] Pág {pagina}: {page_count} cards")
                        
                        for card in cards:
                            try:
                                text = card.text if hasattr(card, 'text') else str(card)
                                
                                if text in procesados:
                                    continue
                                procesados.add(text)
                                
                                precio = 0
                                es_venta = True
                                
                                # Buscar precio USD primero
                                precio_match = re.search(r'(U\$S|USD)\s*([\d.,]+)', text)
                                if precio_match:
                                    precio_str = precio_match.group(2).replace('.', '').replace(',', '.')
                                    precio = float(precio_str)
                                    es_venta = True
                                else:
                                    # Buscar precio ARS (alquiler) - formato $ X.XXX.XXX
                                    precio_ars_match = re.search(r'\$\s*([\d.]+)', text)
                                    if precio_ars_match:
                                        precio_str = precio_ars_match.group(1).replace('.', '')
                                        precio = float(precio_str)
                                        es_venta = False
                                
                                if precio == 0:
                                    continue
                                
                                # m2
                                metros = None
                                for patron in [r'(\d{2,3})\s*m[²2]?', r'(\d{2,3})\s*mt[s]?']:
                                    m_match = re.search(patron, text)
                                    if m_match:
                                        metros = float(m_match.group(1))
                                        if 20 <= metros <= 300:
                                            break
                                
                                if not metros:
                                    continue
                                
                                # Dormitorios
                                dorm_match = re.search(r'(\d+)\s*(?:amb|ambiente|dorm|hab)', text, re.IGNORECASE)
                                dormitorios = int(dorm_match.group(1)) if dorm_match else 1
                                
                                # Título/Dirección
                                titulo = ""
                                link = ""
                                if hasattr(card, 'find_all'):
                                    h_tag = card.find_all(['h2', 'h3', 'h4', 'a'])
                                    for h in h_tag:
                                        t = h.get_text(strip=True)
                                        if t and len(t) > 5:
                                            titulo = t
                                            # Buscar link
                                            if h.name == 'a' and h.get('href'):
                                                link = h.get('href')
                                            elif h.find('a') and h.find('a').get('href'):
                                                link = h.find('a').get('href')
                                            break
                                
                                # Limpiar link
                                if link and not link.startswith('http'):
                                    link = 'https://propia.com.ar' + link
                                
                                valor_m2 = precio / metros
                                
                                # Solo valores razonables
                                if es_venta:
                                    if not (400 <= valor_m2 <= 4000):
                                        continue
                                else:
                                    # Alquiler: precio mensual en ARS por m2
                                    # 480.000 / 45m2 = ~10.667
                                    if not (1000 <= valor_m2 <= 100000):
                                        continue
                                
                                props.append({
                                    "precio": precio,
                                    "m2": metros,
                                    "dormitorios": dormitorios,
                                    "tipo": tipo['tipo_nombre'],
                                    "operacion": "venta" if es_venta else "alquiler",
                                    "direccion": titulo[:80] if titulo else "",
                                    "url": link,
                                    "valor_m2": round(valor_m2, 2),
                                    "fuente": "propia"
                                })
                                
                            except Exception as e:
                                continue
                        
                        # Respetar rate limit
                        time.sleep(2)
                        
                    except Exception as e:
                        print(f"  Error [{op['op_nombre']}/{tipo['tipo_nombre']}] Pág {pagina}: {e}")
        
        browser.close()
    
    # Deduplicar
    seen = set()
    unique = []
    for p in props:
        key = (int(p['precio']), int(p['m2']), p.get('direccion', ''))
        if key not in seen and p['precio'] and p['m2']:
            seen.add(key)
            unique.append(p)
    
    # Guardar JSON
    output = {
        "fecha": datetime.now().isoformat(),
        "fuente": "propia",
        "total": len(unique),
        "venta": len([p for p in unique if p['operacion'] == 'venta']),
        "alquiler": len([p for p in unique if p['operacion'] == 'alquiler']),
        "propiedades": unique
    }
    
    output_file = r"C:\Users\Gustavo\ingresos_familiares_st\propia.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    print(f"\n{'='*60}")
    print(f"RESULTADO: {len(unique)} propiedades únicas")
    print(f"  Venta: {output['venta']}")
    print(f"  Alquiler: {output['alquiler']}")
    print(f"Output: {output_file}")
    print("="*60)
    
    return unique

if __name__ == "__main__":
    scrapear_propia_enriquecido(max_pages=3)