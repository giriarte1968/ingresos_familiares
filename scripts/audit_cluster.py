#!/usr/bin/env python3
"""scripts/audit_cluster.py - Auditoría de comparables para propiedades."""
import json
import math
from pathlib import Path
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.mercado_inmobiliario import obtener_mediana_cluster_v2, normalizar_zona
from parsers.location_engine import cargar_barreras, check_barrier_crossing

PROPIEDADES = ['Mabel', 'Ayacucho', 'Vera Mujica', 'P1200']

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def main():
    with open('cache_scraping.json', encoding='utf-8') as f:
        cache = json.load(f)
    with open('propiedades.json', encoding='utf-8') as f:
        props_data = json.load(f)
    barreras = cargar_barreras()
    
    print("\n" + "=" * 70)
    print("AUDITORIA DE COMPARABLES".center(70))
    print("=" * 70)
    
    for nome in PROPIEDADES:
        prop = [p for p in props_data['propiedades'] if nome.lower() in p['nombre'].lower()]
        if not prop:
            print(f"\n[SKIP] {nome} no encontrada")
            continue
        
        p = prop[0]
        lat, lon = p.get('lat'), p.get('lon')
        zona, dorm = p.get('zona'), p.get('dormitorios', 1)
        
        print(f"\n{'=' * 60}")
        print(f"PROPIEDAD: {nome}")
        print(f"  Zona: {zona} | Dorm: {dorm} | Coord: ({lat}, {lon})")
        
        # Obtener cluster
        m2_base, n, meta = obtener_mediana_cluster_v2(
            zona=normalizar_zona(zona),
            dormitorios=dorm,
            operacion='venta',
            lat_ref=lat,
            lon_ref=lon,
            fecha_ref='2026-04'
        )
        
        print(f"  m2_base: ${m2_base:.2f}")
        print(f"  n_muestras: {n}")
        print(f"  radio: {meta.get('radio_usado')}m")
        print(f"  percentil: {meta.get('percentil_usado')}")
        
        # Analisis de barreras
        props_all = [p for p in cache.get('propiedades', []) 
                   if p.get('operacion') == 'venta' and p.get('dormitorios') == dorm
                   and p.get('lat') and p.get('lon')]
        
        radio = meta.get('radio_usado', 300) / 1000
        nearby = [p for p in props_all if haversine(lat, lon, p['lat'], p['lon']) <= radio]
        
        cross_hard = 0
        cross_soft = 0
        for np in nearby:
            cruza = check_barrier_crossing((lon, lat), (np['lon'], np['lat']), barreras)
            if cruza == 'hard':
                cross_hard += 1
            elif cruza == 'soft':
                cross_soft += 1
        
        print(f"  En radio {radio*1000}m: {len(nearby)} props")
        print(f"  Cruza hard: {cross_hard} | Cruza soft: {cross_soft}")
        
        # Top 10 y bottom 10 por precio/m2
        precios = [(p['valor_m2'], p.get('direccion', ''), p.get('zona', ''), p.get('m2', 0)) for p in nearby if p.get('valor_m2')]
        precios.sort(key=lambda x: x[0])
        
        if precios:
            print(f"\n  TOP 5 BARATOS (USD/m2):")
            for i, (m2, dir, z, mtotal) in enumerate(precios[:5]):
                print(f"    {i+1}. ${m2:.2f} | {dir[:30]} | zona:{z} | m2:{mtotal}")
            
            print(f"\n  TOP 5 CAROS (USD/m2):")
            for i, (m2, dir, z, mtotal) in enumerate(reversed(precios[-5:])):
                print(f"    {i+1}. ${m2:.2f} | {dir[:30]} | zona:{z} | m2:{mtotal}")
            
            vals = [x[0] for x in precios]
            import numpy as np
            print(f"\n  ESTADISTICOS:")
            print(f"    Min: ${min(vals):.2f}")
            print(f"    P33: ${np.percentile(vals, 33):.2f}")
            print(f"    P50: ${np.median(vals):.2f}")
            print(f"    Max: ${max(vals):.2f}")
        
        print()

if __name__ == '__main__':
    main()