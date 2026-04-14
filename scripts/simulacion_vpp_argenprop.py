import requests
from bs4 import BeautifulSoup
import re
import math

def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def scrapear_argenprop_multiples_paginas(paginas=5):
    propiedades = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    for pagina in range(1, paginas + 1):
        if pagina == 1:
            url = "https://www.argenprop.com/departamentos/venta/rosario"
        else:
            url = f"https://www.argenprop.com/departamentos/venta/rosario/pagina-{pagina}"
        
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code != 200:
                break
        except:
            break
            
        soup = BeautifulSoup(response.text, 'html.parser')
        tarjetas = soup.find_all('div', class_='listing__item')
        
        if not tarjetas:
            break
            
        for t in tarjetas:
            price_tag = t.find("p", class_="card__price")
            if not price_tag:
                continue
            
            price_str = price_tag.text
            precio = re.sub(r'[^\d]', '', price_str)
            if not precio:
                continue
            try:
                precio = float(precio)
            except:
                continue
            
            features = t.find("ul", class_="card__main-features")
            metros = None
            if features:
                for li in features.find_all("li"):
                    text = li.text
                    if "m²" in text:
                        m_str = re.sub(r'[^\d]', '', text)
                        if m_str:
                            try:
                                metros = float(m_str)
                            except:
                                pass
                            break
            
            direccion = t.find("h2") or t.find("h3")
            direccion = direccion.text if direccion else ""
            
            titulo = t.find("a", class_="card")
            if titulo:
                href = titulo.get("href", "")
            else:
                href = ""
            
            if precio and metros and metros > 0:
                valor_m2 = precio / metros
                if 500 <= valor_m2 <= 3500:
                    propiedades.append({
                        "precio": precio,
                        "m2": metros,
                        "valor_m2": valor_m2,
                        "direccion": direccion,
                        "url": href
                    })
        
        print(f"Página {pagina}: {len(tarjetas)} tarjetas,.total {len(propiedades)} propiedades")
    
    return propiedades

def main():
    print("="*70)
    print("SIMULACIÓN VPP - PROPIEDAD AYACUCHO")
    print("="*70)
    
    ayacucho = {
        "nombre": "Ayacucho",
        "lat": -32.9545,
        "lon": -60.6455,
        "m2": 27.0,
        "m2_cubiertos": 27.0,
        "zona": "Sexta Pellegrini",
        "piso": 1,
        "estado": "muy bueno"
    }
    
    print(f"\nPROPIEDAD OBJETIVO:")
    print(f"  Nombre: {ayacucho['nombre']}")
    print(f"  Dirección: Ayacucho 1518")
    print(f"  Coordenadas: {ayacucho['lat']}, {ayacucho['lon']}")
    print(f"  Superficie: {ayacucho['m2']} m2")
    print(f"  Zona: {ayacucho['zona']}")
    
    print("\n" + "-"*70)
    print("SCRAPING DE ARGENPROP...")
    print("-"*70)
    
    propiedades = scrapear_argenprop_multiples_paginas(paginas=5)
    print(f"\nTotal propiedades scrapeadas: {len(propiedades)}")
    
    print("\n" + "-"*70)
    print("LISTADO COMPLETO DE PROPIEDADES ENCONTRADAS")
    print("-"*70)
    
    for i, p in enumerate(propiedades):
        print(f"{i+1:2}. {p['direccion'][:45]:45} | {p['m2']:6.0f}m2 | USD {p['precio']:10,.0f} | USD/m2 {p['valor_m2']:.0f}")
    
    if not propiedades:
        print("NO SE OBTUVIERON PROPIEDADES")
        return
    
    promedio_m2 = sum(p['valor_m2'] for p in propiedades) / len(propiedades)
    print(f"\nPROMEDIO USD/m2 (todas): {promedio_m2:.0f}")
    
    precio_min = min(p['valor_m2'] for p in propiedades)
    precio_max = max(p['valor_m2'] for p in propiedades)
    print(f"RANGO USD/m2: {precio_min:.0f} - {precio_max:.0f}")
    
    print("\n" + "-"*70)
    print("CÁLCULO VPP PARA AYACUCHO")
    print("-"*70)
    
    promedio_cercanas = promedio_m2
    
    valor_base = ayacucho['m2'] * promedio_cercanas
    
    factor_estado = 1.10 if ayacucho['estado'] == "muy bueno" else 1.0
    factor_piso = 0.95 if ayacucho['piso'] == 0 else 1.0
    
    valor_ajustado = valor_base * factor_estado * factor_piso
    
    descuento_liquidez = 0.08
    valor_realizable = valor_ajustado * (1 - descuento_liquidez)
    
    print(f"\nCálculos:")
    print(f"  m2 propiedad objetivo: {ayacucho['m2']}")
    print(f"  Precio base/m2 promedio: USD {promedio_cercanas:.0f}")
    print(f"  Valor base (sin ajustes): USD {valor_base:,.0f}")
    print(f"  Ajuste estado (+10%): {factor_estado}")
    print(f"  Ajuste piso: {factor_piso}")
    print(f"  Valor ajustado: USD {valor_ajustado:,.0f}")
    print(f"  Descuento liquidez: -{descuento_liquidez*100:.0f}%")
    print(f"  VALOR REALIZABLE: USD {valor_realizable:,.0f}")
    
    print("\n" + "="*70)
    print("RESUMEN FINAL")
    print("="*70)
    print(f"  Valor estimado (VPP): USD {valor_ajustado:,.0f}")
    print(f"  Valor net (liquidez): USD {valor_realizable:,.0f}")
    print(f"  USD/m2 utilizado: {promedio_cercanas:.0f}")
    print(f"  Comparables encontrados: {len(propiedades)}")
    print("="*70)

if __name__ == "__main__":
    main()