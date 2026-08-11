"""
Script para analizar tendencias temporales (CT / apreciación anual)
en cache_scraping.json para Puerto Norte, Centro y Fisherton.
Calcula el cambio anual en precio por m2 para ver si los datos de la cache
respaldan un crecimiento menor en Puerto Norte vs otras zonas.
"""

import json
import os
import math
from datetime import datetime
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

def parse_date(date_str):
    if not date_str:
        return None
    try:
        # Intentar formato completo YYYY-MM-DD
        return datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
    except:
        try:
            # Intentar YYYY-MM
            return datetime.strptime(str(date_str)[:7], "%Y-%m")
        except:
            return None

def analizar_tendencias_temporales():
    base_dir = r"C:\Users\Gustavo\ingresos_familiares_st"
    cache_path = os.path.join(base_dir, "cache_scraping.json")
    
    if not os.path.exists(cache_path):
        print(f"No se encontró cache_scraping.json en: {cache_path}")
        return
        
    with open(cache_path, "r", encoding="utf-8") as f:
        cache = json.load(f)
        
    props = cache.get("propiedades", [])
    
    PN_LAT, PN_LON = -32.9244, -60.6662
    CENTRO_LAT, CENTRO_LON = -32.9468, -60.6393
    FISHERTON_LAT, FISHERTON_LON = -32.9250, -60.7400
    
    zonas_data = {
        "Puerto Norte": {"lat": PN_LAT, "lon": PN_LON, "r": 1.0, "keywords": ["puerto norte", "puertonorte"], "records": []},
        "Centro": {"lat": CENTRO_LAT, "lon": CENTRO_LON, "r": 1.0, "keywords": ["centro"], "records": []},
        "Fisherton (Oeste)": {"lat": FISHERTON_LAT, "lon": FISHERTON_LON, "r": 2.0, "keywords": ["fisherton"], "records": []}
    }
    
    # 1. Agrupar y limpiar por zona
    seen = set()
    for p in props:
        if p.get("operacion") != "venta":
            continue
        m2 = p.get("m2") or p.get("m2_cubiertos") or 0
        precio = p.get("precio") or 0
        if m2 <= 15 or precio <= 5000:
            continue
            
        # Deduplicar
        key = (int(precio), int(m2), p.get("zona", ""))
        if key in seen:
            continue
        seen.add(key)
        
        lat = p.get("lat") or p.get("latitud")
        lon = p.get("lon") or p.get("longitud")
        zona_text = str(p.get("zona", "")).lower()
        date_obj = parse_date(p.get("date_created"))
        
        if not date_obj:
            continue
            
        pm2 = precio / m2
        
        for name, config in zonas_data.items():
            match = False
            # Check keyword
            if any(kw in zona_text for kw in config["keywords"]):
                match = True
            # Check geo
            elif lat and lon:
                dist = haversine(config["lat"], config["lon"], lat, lon)
                if dist <= config["r"]:
                    match = True
                    
            if match:
                config["records"].append({
                    "date": date_obj,
                    "pm2": pm2,
                    "precio": precio,
                    "m2": m2
                })
                
    print("==================================================")
    print("ANALISIS DE TENDENCIA TEMPORAL EN CACHE_SCRAPING")
    print("==================================================")
    
    for name, config in zonas_data.items():
        records = config["records"]
        n_total = len(records)
        print(f"\n>>> Zona: {name} (Total muestras válidas: {n_total})")
        if n_total < 10:
            print("  Muestras insuficientes para análisis temporal.")
            continue
            
        # Dividir por semestres o años
        # Agrupar por año y mes
        grouped_by_quarter = defaultdict(list)
        for r in records:
            # Cuatrimestre o Trimestre (Q1, Q2, Q3, Q4)
            q = (r["date"].month - 1) // 3 + 1
            key = f"{r['date'].year}-Q{q}"
            grouped_by_quarter[key].append(r["pm2"])
            
        # Mostrar medianas por trimestre para ver la evolución
        sorted_keys = sorted(grouped_by_quarter.keys())
        quarter_medians = {}
        
        print("  Evolución Trimestral (Mediana $/m2 limpia por IQR):")
        for qkey in sorted_keys:
            prices = grouped_by_quarter[qkey]
            clean_prices = aplicar_iqr(prices)
            if len(clean_prices) >= 2:
                med = calcular_mediana(clean_prices)
                quarter_medians[qkey] = med
                print(f"    - {qkey}: USD {med:,.0f}/m2 (n={len(clean_prices)})")
                
        # Calcular tasa de variación anual aproximada si hay datos suficientes
        if len(quarter_medians) >= 3:
            first_q = sorted_keys[0]
            last_q = sorted_keys[-1]
            val_first = quarter_medians[first_q]
            val_last = quarter_medians[last_q]
            
            # Calcular meses transcurridos aproximados entre trimestres
            y1, q1 = map(int, first_q.replace("Q", "").split("-"))
            y2, q2 = map(int, last_q.replace("Q", "").split("-"))
            meses = (y2 - y1) * 12 + (q2 - q1) * 3
            
            if meses > 0:
                variacion_anual = (val_last / val_first) ** (12 / meses) - 1
                print(f"  --> Tasa Anual Promedio Estimada (CAGR {first_q} a {last_q}): {variacion_anual*100:+.2f}%")
            else:
                print("  Rango temporal insuficiente para estimación de tasa anual.")
        else:
            print("  Muestras trimestrales insuficientes para calcular la tasa.")

if __name__ == "__main__":
    analizar_tendencias_temporales()
