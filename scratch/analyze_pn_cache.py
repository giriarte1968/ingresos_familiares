"""
Script para re-analizar la base de datos cache_scraping.json
específicamente para Puerto Norte (1, 2 y 3 dormitorios).
Aplica los mismos filtros de deduplicación e IQR de Valu.
"""

import json
import os
import math
from collections import defaultdict

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def calcular_mediana(lista):
    if not lista:
        return 0.0
    s = sorted(lista)
    n = len(s)
    if n % 2 == 1:
        return float(s[n // 2])
    return (s[n // 2 - 1] + s[n // 2]) / 2.0

def calcular_percentil_linear(precios, q):
    if not precios:
        return 0.0
    s = sorted(precios)
    n = len(s)
    if n == 1:
        return float(s[0])
    idx = q / 100.0 * (n - 1)
    lo = int(idx)
    hi = lo + 1
    if hi >= n:
        return float(s[-1])
    frac = idx - lo
    return float(s[lo] * (1 - frac) + s[hi] * frac)

def aplicar_iqr(precios):
    if len(precios) < 3:
        return precios
    q1 = calcular_percentil_linear(precios, 25)
    q3 = calcular_percentil_linear(precios, 75)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    return [p for p in precios if lower <= p <= upper]

def analizar_cache_puerto_norte():
    base_dir = r"C:\Users\Gustavo\ingresos_familiares_st"
    cache_path = os.path.join(base_dir, "cache_scraping.json")
    
    if not os.path.exists(cache_path):
        print(f"No se encontró cache_scraping.json en: {cache_path}")
        return
        
    with open(cache_path, "r", encoding="utf-8") as f:
        cache = json.load(f)
        
    props = cache.get("propiedades", [])
    print(f"Total propiedades en cache: {len(props)}")
    
    # Coordenadas reales centro de Puerto Norte
    PN_LAT = -32.9244
    PN_LON = -60.6662
    
    # 1. Filtrar por geofencing (1 km) o concordancia textual de zona
    pn_props = []
    for p in props:
        # Solo venta y con precio/superficie válidos
        if p.get("operacion") != "venta":
            continue
        m2 = p.get("m2") or p.get("m2_cubiertos") or 0
        precio = p.get("precio") or 0
        if m2 <= 10 or precio <= 1000:
            continue
            
        lat = p.get("lat") or p.get("latitud")
        lon = p.get("lon") or p.get("longitud")
        zona_text = str(p.get("zona", "")).lower()
        
        es_pn = False
        if "puerto norte" in zona_text or "puertonorte" in zona_text:
            es_pn = True
        elif lat and lon:
            dist = haversine(PN_LAT, PN_LON, lat, lon)
            if dist <= 1.0: # radio de 1km
                es_pn = True
                
        if es_pn:
            pn_props.append(p)
            
    print(f"Propiedades en Puerto Norte (geo + texto): {len(pn_props)}")
    
    # 2. Deduplicar propiedades (misma clave que Valu)
    seen = set()
    unicas = []
    for p in pn_props:
        m2 = p.get("m2") or p.get("m2_cubiertos") or 0
        precio = p.get("precio") or 0
        key = (int(precio), int(m2), p.get("zona", ""))
        if key not in seen:
            seen.add(key)
            unicas.append(p)
            
    print(f"Propiedades deduplicadas: {len(unicas)}")
    
    # Clasificación por dormitorios
    dorms_dict = defaultdict(list)
    for p in unicas:
        d = p.get("dormitorios")
        if d in (1, 2, 3):
            m2 = p.get("m2") or p.get("m2_cubiertos") or 0
            precio = p.get("precio") or 0
            pm2 = precio / m2
            dorms_dict[d].append((m2, pm2))
            
    # Mostrar resultados por dormitorios
    bins_2_dorm = [
        ("50-70m2", 50, 70),
        ("70-90m2", 70, 90),
        ("90-110m2", 90, 110),
        ("110-130m2", 110, 130),
        ("130-150m2", 130, 150),
        ("150-180m2", 150, 180),
        ("180+m2", 180, 9999),
    ]
    
    bins_3_dorm = [
        ("90-110m2", 90, 110),
        ("110-130m2", 110, 130),
        ("130-150m2", 130, 150),
        ("150-180m2", 150, 180),
        ("180+m2", 180, 9999),
    ]
    
    bins_1_dorm = [
        ("30-50m2", 30, 50),
        ("50-70m2", 50, 70),
        ("70+m2", 70, 9999),
    ]
    
    config_bins = {
        1: bins_1_dorm,
        2: bins_2_dorm,
        3: bins_3_dorm
    }
    
    print("\n" + "="*50)
    print("ANÁLISIS DE PRECIOS POR $M2 EN PUERTO NORTE (LIMPIO)")
    print("="*50)
    
    for d in (1, 2, 3):
        print(f"\n>>> {d} DORMITORIOS (n_total = {len(dorms_dict[d])}):")
        bins = config_bins[d]
        
        for name, start, end in bins:
            submuestra = [pm2 for m2, pm2 in dorms_dict[d] if start <= m2 < end]
            n_raw = len(submuestra)
            
            # Limpiar por IQR para quitar ruido
            submuestra_limpia = aplicar_iqr(submuestra)
            n_clean = len(submuestra_limpia)
            
            if n_clean > 0:
                mediana_m2 = calcular_mediana(submuestra_limpia)
                promedio_m2 = sum(submuestra_limpia) / n_clean
                min_m2 = min(submuestra_limpia)
                max_m2 = max(submuestra_limpia)
                print(f"  {name:<10} | Muestras: {n_clean:<3} (descartadas {n_raw - n_clean}) | Mediana: USD {mediana_m2:,.0f}/m2 | Rango: [{min_m2:,.0f} - {max_m2:,.0f}]")
            else:
                print(f"  {name:<10} | Muestras: 0")

if __name__ == "__main__":
    analizar_cache_puerto_norte()
