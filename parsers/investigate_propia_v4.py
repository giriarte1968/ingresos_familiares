from playwright.sync_api import sync_playwright
import json
import random
import re

def investigacion_propia_v4():
    print("[PROPIA] Investigando estructura v4...")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")
        page = context.new_page()
        
        url = "https://propia.com.ar"
        print("[PROPIA] Navegando a home...")
        page.goto(url, timeout=60000, wait_until="networkidle")
        page.wait_for_timeout(4000)
        
        print(f"[PROPIA] Titulo: {page.title()}")
        
        # Buscar listings en la página principal
        # Propia usa un buscador, pero también tiene listados
        # Vamos a buscar directamente los enlaces que contengan /propiedad/ o /propiedades/
        all_links = page.query_selector_all("a")
        print(f"[PROPIA] Total enlaces: {len(all_links)}")
        
        # Recolectar enlaces relevantes
        relevante_urls = []
        for link in all_links:
            href = link.get_attribute("href")
            if href:
                # Buscar los que sean de propiedades en Rosario
                if ("/propiedad/" in href or "/propiedades/" in href) and "rosario" in href.lower():
                    relevante_urls.append(href)
        
        unique_urls = list(set(relevante_urls))
        print(f"[PROPIA] Links a propiedades de Rosario: {len(unique_urls)}")
        for u in unique_urls[:20]:
            print(f"  {u}")
        
        # También probar una URL directa de búsqueda
        search_url = "https://propia.com.ar/buscar?ciudad=rosario&operacion=venta"
        print(f"\n[PROPIA] Probando busqueda: {search_url}")
        page.goto(search_url, timeout=60000, wait_until="networkidle")
        page.wait_for_timeout(4000)
        
        links2 = page.query_selector_all("a")
        propiedad_links = []
        for link in links2:
            href = link.get_attribute("href")
            if href and "/propiedad/" in href:
                propiedad_links.append(href)
        
        print(f"[PROPIA] Links de resultados: {len(propiedad_links)}")
        if propiedad_links[:5]:
            for u in propiedad_links[:5]:
                print(f"  {u}")
        
        # VISITAR UNA PROPIEDAD PARA VER ESTRELUCTURA DE DETALLE
        if unique_urls:
            first_prop = unique_urls[0]
            print(f"\n[PROPIA] Visitando propiedad: {first_prop}")
            page.goto(first_prop, timeout=60000, wait_until="networkidle")
            page.wait_for_timeout(3000)
            
            # Extraer información del detalle
            detail_html = page.content()
            
            # Buscar año de construcción en el HTML
            # Patrones comunes
            year_matches = re.findall(r'(?:año|anio|construido|construccion|antigüedad)[:\s]*(\d{4})', detail_html, re.I)
            print(f"[PROPIA] Años encontrados en detalle: {year_matches[:10]}")
            
            # Buscar también precio
            precio_matches = re.findall(r'\$([\d,\.]+)|USD\s*([\d,\.]+)', detail_html, re.I)
            print(f"[PROPIA] Precios encontrados: {precio_matches[:5]}")
            
            # Buscar metros
            m2_matches = re.findall(r'(\d+)\s*m²|(\d+)\s*m2|superficie[:\s]*(\d+)', detail_html, re.I)
            print(f"[PROPIA] Metros encontrados: {m2_matches[:5]}")
        
        # Guardar muestra
        with open("propia_investigacion.json", "w", encoding="utf-8") as f:
            json.dump({
                "propiedad_urls": unique_urls[:30],
                "titulo": page.title(),
            }, f, indent=2, ensure_ascii=False)
        
        print("[PROPIA] Investigación guardada en propria_investigacion.json")
        
        browser.close()

if __name__ == "__main__":
    investigacion_propia_v4()