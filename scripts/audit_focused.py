#!/usr/bin/env python3
"""scripts/audit_focused.py - Auditoría focalizada Vera/P1200

Separa comparables por cruce de barreras blandas.
"""
import json
import math
from pathlib import Path
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from parsers.mercado_inmobiliario import obtener_mediana_cluster_v2, normalizar_zona
from parsers.location_engine import cargar_barreras, check_barrier_crossing

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def get_comparables(prop, cache, barreras, radio_km=0.3):
    lat, lon = prop.get('lat'), prop.get('lon')
    dorm = prop.get('dormitorios', 1)
    
    props_all = [p for p in cache.get('propiedades', [])
               if p.get('operacion') == 'venta' and p.get('dormitorios') == dorm
               and p.get('lat') and p.get('lon')]
    
    same_side = []
    cross_soft = []
    
    for p in props_all:
        d = haversine(lat, lon, p['lat'], p['lon'])
        if d <= radio_km:
            cruza = check_barrier_crossing((lon, lat), (p['lon'], p['lat']), barreras)
            if cruza == 'soft':
                cross_soft.append(p)
            else:
                same_side.append(p)
    
    return same_side, cross_soft

def calc_stats(props):
    if not props:
        return {}
    vals = [p.get('valor_m2', 0) for p in props if p.get('valor_m2')]
    if not vals:
        return {}
    
    import numpy as np
    return {
        'n': len(vals),
        'min': min(vals),
        'max': max(vals),
        'p33': np.percentile(vals, 33),
        'p50': np.median(vals),
        'sorted': sorted(vals)
    }

def print_comparables(props, title, top_n=5):
    print(f"\n{title}")
    print("-" * 60)
    if not props:
        print("  [NINGUNO]")
        return
    
    sorted_props = sorted(props, key=lambda x: x.get('valor_m2', 0))
    
    print(f"  TOP {top_n} BARATOS:")
    for i, p in enumerate(sorted_props[:top_n]):
        print(f"    {i+1}. ${p.get('valor_m2'):.2f} | {p.get('direccion', '')[:25]} | m2:{p.get('m2')}")
    
    print(f"\n  TOP {top_n} CAROS:")
    for i, p in enumerate(reversed(sorted_props[-top_n:])):
        print(f"    {i+1}. ${p.get('valor_m2'):.2f} | {p.get('direccion', '')[:25]} | m2:{p.get('m2')}")

def main():
    with open('cache_scraping.json', encoding='utf-8') as f:
        cache = json.load(f)
    with open('propiedades.json', encoding='utf-8') as f:
        props_data = json.load(f)
    barreras = cargar_barreras()
    
    print("\n" + "=" * 80)
    print("AUDITORIA FOCALIZADA: VERA & P1200".center(80))
    print("=" * 80)
    
    for nome in ['Vera Mujica', 'P1200']:
        prop = [p for p in props_data['propiedades'] if nome.lower() in p['nombre'].lower()][0]
        
        lat, lon = prop.get('lat'), prop.get('lon')
        zona = prop.get('zona')
        dorm = prop.get('dormitorios', 1)
        
        print(f"\n{'=' * 70}")
        print(f"PROPIEDAD: {nome}")
        print(f"  Zona: {zona} | Dorm: {dorm} | Coord: ({lat}, {lon})")
        
        m2_base, n_total, meta = obtener_mediana_cluster_v2(
            zona=normalizar_zona(zona),
            dormitorios=dorm,
            operacion='venta',
            lat_ref=lat,
            lon_ref=lon,
            fecha_ref='2026-04'
        )
        radio = meta.get('radio_usado', 300) / 1000
        
        print(f"\n  CLUSTER ACTUAL:")
        print(f"    m2_base: ${m2_base:.2f}")
        print(f"    n_total: {n_total}")
        print(f"    radio: {radio*1000}m")
        
        same_side, cross_soft = get_comparables(prop, cache, barreras, radio)
        
        print(f"\n  SEPARACION POR BARRERA:")
        print(f"    same_side (no cruza): {len(same_side)} props")
        print(f"    cross_soft (cruza): {len(cross_soft)} props")
        
        stats_same = calc_stats(same_side)
        stats_cross = calc_stats(cross_soft)
        
        print(f"\n  ESTADISTICOS:")
        if stats_same:
            print(f"    SAME-SIDE: n={stats_same['n']}, Min={stats_same['min']:.2f}, P33={stats_same['p33']:.2f}, P50={stats_same['p50']:.2f}, Max={stats_same['max']:.2f}")
        
        if stats_cross:
            print(f"    CROSS_SOFT: n={stats_cross['n']}, Min={stats_cross['min']:.2f}, P33={stats_cross['p33']:.2f}, P50={stats_cross['p50']:.2f}, Max={stats_cross['max']:.2f}")
        
        print_comparables(same_side, "SAME-SIDE - Comparables", top_n=5)
        print_comparables(cross_soft, "CROSS_SOFT - Comparables", top_n=5)
        
        print(f"\n{'=' * 70}")
        print(f"RESUMEN: {nome}")
        print(f"| Grupo       | n   | P33       | P50       |")
        print(f"|------------|-----|-----------|-----------|")
        same_p33 = stats_same.get('p33', 0)
        same_p50 = stats_same.get('p50', 0)
        cross_p33 = stats_cross.get('p33', 0)
        cross_p50 = stats_cross.get('p50', 0)
        print(f"| same_side   | {stats_same['n']:3} | ${same_p33:7.2f} | ${same_p50:7.2f} |")
        print(f"| cross_soft | {stats_cross['n']:3} | ${cross_p33:7.2f} | ${cross_p50:7.2f} |")
        print(f"| m2_base UI | -   | ${m2_base:7.2f} | -        |")
        
        print()

if __name__ == '__main__':
    main()