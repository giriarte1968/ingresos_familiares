import requests
import json
import urllib.parse
import time
import random
import os

API_BASE = "https://admin.propia.com.ar/items/properties"

# Absolute filter for Rosario market
VALOR_MINIMO_ABSOLUTO = 400   # USD/m² - no property worth less
VALOR_MAXIMO_ABSOLUTO = 5000  # USD/m² - no property worth more under normal conditions

def obtener_propiedades_propia(max_pages=20, limit_per_page=50):
    print("[PROPIA] Obteniendo propiedades via API exhaustivamente...")
    props = []
    seen_urls = set()
    
    for page in range(1, max_pages + 1):
        # SIMPLIFICANDO FILTROS para evitar el Error 400
        # Probamos solo con limit, page y fields primero
        params = {
            "limit": limit_per_page,
            "page": page,
            "fields": "id,title,slug,price,area,bedrooms,bathrooms,address,latitude,longitude,operation_id,antiquity,property_construction_status_id,delivery_year,date_created",
        }
        
        # Agregar filtros uno por uno para debuguear
        # Intentamos solo Rosario (city_id=1)
        params["filter"] = json.dumps({"location_city_id": {"_eq": 1}})
        
        try:
            r = requests.get(API_BASE, params=params, timeout=30)
            if r.status_code != 200:
                print(f"[PROPIA] Error status {r.status_code} page {page}")
                # Si falla con filtro, intentar sin filtro para ver si es el problema
                params.pop("filter")
                r = requests.get(API_BASE, params=params, timeout=30)
                if r.status_code != 200:
                    break
                print(f"[PROPIA] Recuperado sin filtro en página {page}")
            
            data = r.json()
            items = data.get('data', [])
            if not items:
                print(f"[PROPIA] Fin en página {page}")
                break
            
            print(f"[PROPIA] Página {page}: {len(items)} propiedades")
            
            for item in items:
                price = item.get('price', 0)
                area = item.get('area', 0)
                if not price or not area or float(area) <= 0: continue
                if float(area) < 15 or float(area) > 500: continue
                
                slug = item.get('slug', '')
                url = f"https://propia.com.ar/propiedad/{slug}" if slug else ""
                if url in seen_urls: continue
                seen_urls.add(url)
                
                op_id = item.get('operation_id', {})
                operacion = "venta" if op_id == 1 else "alquiler"
                
                antiguedad = item.get('antiquity')
                anio = None
                if antiguedad and isinstance(antiguedad, (int, float)):
                    anio = 2026 - int(antiguedad)
                
                props.append({
                    "precio": float(price),
                    "m2": float(area),
                    "dormitorios": item.get('bedrooms') or 1,
                    "valor_m2": round(float(price) / float(area), 2),
                    "direccion": item.get('address') or item.get('title') or "",
                    "fuente": "propia",
                    "operacion": operacion,
                    "zona": "Rosario",
                    "url": url,
                    "lat": item.get('latitude'),
                    "lon": item.get('longitude'),
                    "anio_construccion": anio,
                    "fecha_publicacion": item.get('date_created'),
                    "estado_construccion": item.get('property_construction_status_id'),
                    "delivery_year": item.get('delivery_year'),
                })
            time.sleep(0.2)
        except Exception as e:
            print(f"[PROPIA] Error en página {page}: {e}")
            break
    
    print(f"[PROPIA] Total propiedades obtenidas: {len(props)}")
    
    # Absolute filter: remove properties with valor_m2 outside [400, 5000]
    props_filtradas = [p for p in props if VALOR_MINIMO_ABSOLUTO <= p.get('valor_m2', 0) <= VALOR_MAXIMO_ABSOLUTO]
    print(f"[PROPIA] Filtro absoluto: {len(props)} -> {len(props_filtradas)} propiedades (eliminadas {len(props) - len(props_filtradas)} outliers)")
    return props_filtradas

def save_to_cache(props):
    import os
    all_props = []
    if os.path.exists("cache_scraping.json"):
        try:
            with open("cache_scraping.json", 'r', encoding="utf-8") as f:
                data = json.load(f)
                all_props = data.get("propiedades", [])
        except:
            pass
    
    # Absolute filter: remove properties with valor_m2 outside [400, 5000]
    all_props_filtradas = [p for p in all_props if VALOR_MINIMO_ABSOLUTO <= p.get('valor_m2', 0) <= VALOR_MAXIMO_ABSOLUTO]
    if len(all_props_filtradas) < len(all_props):
        print(f"[CACHE] Filtro absoluto: {len(all_props)} -> {len(all_props_filtradas)} propiedades (eliminadas {len(all_props) - len(all_props_filtradas)} outliers)")
    all_props = all_props_filtradas
    
    props_by_url = {p.get('url'): p for p in all_props if p.get('url')}
    for prop in props:
        url = prop.get('url', '')
        if url:
            if url in props_by_url:
                props_by_url[url].update(prop)
            else:
                all_props.append(prop)
                props_by_url[url] = prop
    
    seen = set()
    unique = []
    for p in all_props:
        url = p.get('url', '')
        if url and url not in seen:
            seen.add(url)
            unique.append(p)
    
    data = {
        "fecha": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "status": "propia_api_fresh_v3",
        "propiedades": unique
    }
    with open("cache_scraping.json", 'w', encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"[CACHE] Guardado: {len(unique)} propiedades únicas")

def main():
    import time
    print("=" * 50)
    print("PROPIA SCRAPER v3.1 - API ONLY")
    print("=" * 50)
    props = obtener_propiedades_propia(max_pages=30, limit_per_page=50)
    if props:
        save_to_cache(props)
        print(f"Cosecha completada: {len(props)} propiedades.")
    else:
        print("No se obtuvieron datos.")

if __name__ == "__main__":
    main()