#!/usr/bin/env python3
"""Simula el cálculo de alquiler con el motor real para propiedades específicas."""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.mercado_inmobiliario import valuar_propiedad_v7
from parsers.time_adjustment import calcular_ct_alquiler, get_ct_alquiler_rate


def cargar_cache():
    """Carga cache_scraping.json directamente."""
    import json
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache_scraping.json')
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('propiedades', data) if isinstance(data, dict) else data


def simular(nombre_buscado):
    """Simula la valuación de una propiedad específica."""
    # Cargar datos
    cache = cargar_cache()
    propiedades = json.load(open('propiedades.json', 'r', encoding='utf-8')).get('propiedades', [])
    
    # Buscar propiedad
    prop = None
    for p in propiedades:
        if nombre_buscado.upper() in (p.get('nombre', '') or '').upper():
            prop = p
            break
    
    if not prop:
        print(f"Propiedad '{nombre_buscado}' no encontrada")
        return None
    
    nombre = prop.get('nombre', '')
    print(f"\n{'='*60}")
    print(f"  {nombre}")
    print(f"{'='*60}")
    print(f"  Dirección: {prop.get('direccion', '')}")
    print(f"  m2 cubiertos: {prop.get('m2_cubiertos', 0)}")
    print(f"  dormitorios: {prop.get('dormitorios', 0)}")
    
    # Correr valuación real
    try:
        resultado = valuar_propiedad_v7(
            propiedad=prop,
            fecha_ref=datetime.now().strftime('%Y-%m-%d'),
            flex_dormitorios=None,
            retro_dias=0,
        )
    except Exception as e:
        print(f"  ERROR en valuación: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    if not resultado:
        print("  Sin resultado")
        return None
    
    # Extraer datos relevantes
    print(f"\n  --- RESULTADOS ---")
    print(f"  Valor venta: ${resultado.get('valor_venta', 0):,.0f} USD")
    print(f"  m2 base venta: ${resultado.get('m2_base_venta', 0):,.0f} USD/m²")
    
    # Alquiler
    alq_base = resultado.get('m2_base_alquiler', 0)
    n_alq = resultado.get('n_alquileres', 0)
    alq_est = resultado.get('alquiler_estimado_ars', 0)
    cap_rate = resultado.get('cap_rate', 0)
    metodo_alq = resultado.get('metodo_alquiler', 'N/A')
    
    print(f"\n  --- ALQUILER ---")
    print(f"  Cluster alquiler m2: ${alq_base:,.0f} ARS/m²")
    print(f"  N alquileres: {n_alq}")
    print(f"  Método: {metodo_alq}")
    print(f"  Cap rate: {cap_rate*100:.1f}%")
    print(f"  Alquiler estimado: ${alq_est:,.0f} ARS/mes")
    
    # Simular CT alquiler
    m2_cub = prop.get('m2_cubiertos', 0)
    m2_desc = prop.get('m2_descubiertos', 0)
    m2_equiv = m2_cub + (m2_desc * 0.1)
    dorms = prop.get('dormitorios', 0)
    
    if alq_base > 0:
        # Alquiler sin CT
        factores = resultado.get('factor_estado', 1.0) * resultado.get('factor_calidad', 1.0)
        gap = 0.92
        alq_sin_ct = m2_equiv * alq_base * factores * gap
        
        print(f"\n  --- SIMULACIÓN CT ALQUILER ---")
        print(f"  m2 equivalentes: {m2_equiv:.1f}")
        print(f"  Alquiler sin CT: ${alq_sin_ct:,.0f} ARS/mes")
        
        # Con CT por antigüedad
        print(f"\n  Alquiler con CT (por antigüedad):")
        print(f"  {'Meses':>8} {'CT':>8} {'Alq Ajustado':>15} {'vs Sin CT':>12}")
        print(f"  {'─'*8} {'─'*8} {'─'*15} {'─'*12}")
        
        for meses in [0, 6, 12, 18, 24]:
            ct = calcular_ct_alquiler(meses, macrozona_id='resto_rosario', dormitorios=dorms)
            alq_ct = alq_sin_ct * ct
            diff_pct = (ct - 1) * 100
            print(f"  {meses:>8} {ct:>8.4f} ${alq_ct:>14,.0f} {diff_pct:>+10.1f}%")
        
        # CT por dormitorio
        print(f"\n  CT por dormitorio (12 meses):")
        for d in [1, 2, 3]:
            ct_d = calcular_ct_alquiler(12, macrozona_id='resto_rosario', dormitorios=d)
            alq_d = alq_sin_ct * ct_d
            print(f"    {d}d: CT={ct_d:.4f} → ${alq_d:,.0f} ARS/mes")
    
    return resultado


def main():
    propiedades = ['Ayacucho', 'Mabel', 'Vera Mujica', 'P1200', 'Entre Rios']
    
    for nombre in propiedades:
        simular(nombre)


if __name__ == '__main__':
    main()
