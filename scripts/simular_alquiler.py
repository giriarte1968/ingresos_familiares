#!/usr/bin/env python3
"""Simula el cálculo de alquiler con CT alquiler para propiedades específicas."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.time_adjustment import calcular_ct_alquiler, get_ct_alquiler_rate


def simular_alquiler(nombre, prop, res, es_manual=False):
    """Simula el cálculo de alquiler para una propiedad."""
    print(f"\n{'='*60}")
    print(f"  {nombre} {'(Solo Manual)' if es_manual else ''}")
    print(f"{'='*60}")
    
    # Datos de la propiedad
    m2_cub = prop.get('m2_cubiertos', 0)
    m2_desc = prop.get('m2_descubiertos', 0)
    dorms = prop.get('dormitorios', 0)
    lat = prop.get('lat', 0)
    lon = prop.get('lon', 0)
    
    print(f"\n  Datos propiedad:")
    print(f"    m2 cubiertos: {m2_cub}")
    print(f"    m2 descubiertos: {m2_desc}")
    print(f"    dormitorios: {dorms}")
    
    # 1. Cluster alquiler
    m2_base_alq = res.get('m2_base_alquiler', 0)
    n_alq = res.get('n_alquileres', 0)
    print(f"\n  1. Cluster Alquiler:")
    print(f"     m2_base_alquiler: ${m2_base_alq:,.0f} ARS/m²")
    print(f"     n_alquileres: {n_alq}")
    
    # 2. m2 equivalentes alquiler
    m2_equiv = m2_cub + (m2_desc * 0.1)
    print(f"\n  2. m2 equivalentes alquiler:")
    print(f"     {m2_cub} + ({m2_desc} × 0.1) = {m2_equiv:.1f} m²")
    
    # 3. Factores alquiler
    f_estado = res.get('factor_estado_alq', 1.0)
    f_calidad = res.get('factor_calidad_alq', 1.0)
    f_anti = res.get('factor_anti_alq', 1.0)
    f_nlp = res.get('nlp_ajuste_alq', 0.0)
    factores = f_estado * f_calidad * f_anti * (1 + f_nlp)
    
    print(f"\n  3. Factores alquiler:")
    print(f"     estado: {f_estado:.4f}")
    print(f"     calidad: {f_calidad:.4f}")
    print(f"     anti: {f_anti:.4f}")
    print(f"     nlp: {f_nlp:+.4f}")
    print(f"     factores combinados: {factores:.4f}")
    
    # 4. GAP
    gap = 0.92
    print(f"\n  4. GAP alquiler: {gap}")
    
    # 5. Alquiler base (CT alquiler viejo)
    alq_base = m2_equiv * m2_base_alq * factores * gap
    print(f"\n  5. Alquiler base (sin CT):")
    print(f"     {m2_equiv:.1f} × ${m2_base_alq:,.0f} × {factores:.4f} × {gap}")
    print(f"     = ${alq_base:,.0f} ARS/mes")
    
    # 6. Simular CT alquiler para diferentes antigüedades
    macrozona_id = 'resto_rosario'  # Default
    
    print(f"\n  6. CT Alquiler por antigüedad:")
    print(f"     {'Meses':>8} {'CT':>8} {'Alq Ajustado':>15} {'Diferencia':>12}")
    print(f"     {'─'*8} {'─'*8} {'─'*15} {'─'*12}")
    
    for meses in [0, 3, 6, 9, 12, 18, 24]:
        ct = calcular_ct_alquiler(meses, macrozona_id=macrozona_id, dormitorios=dorms)
        alq_ajustado = alq_base * ct
        diff = alq_ajustado - alq_base
        print(f"     {meses:>8} {ct:>8.4f} ${alq_ajustado:>14,.0f} {diff:>+11,.0f}")
    
    # 7. CT por dormitorio
    print(f"\n  7. CT por dormitorio (12 meses):")
    for d in [1, 2, 3]:
        ct_d = calcular_ct_alquiler(12, macrozona_id=macrozona_id, dormitorios=d)
        alq_d = alq_base * ct_d
        print(f"     {d}d: CT={ct_d:.4f} → ${alq_d:,.0f} ARS/mes")
    
    # 8. Cap rate (si hay valor de venta)
    valor_venta = res.get('valor_venta', 0)
    if valor_venta > 0:
        alq_anual_usd = alq_base * 12 / 1480  # Asumiendo USD/ARS = 1480
        cap_rate = alq_anual_usd / valor_venta
        print(f"\n  8. Cap Rate:")
        print(f"     Valor venta: USD {valor_venta:,.0f}")
        print(f"     Alquiler anual: USD {alq_anual_usd:,.0f}")
        print(f"     Cap rate: {cap_rate*100:.1f}%")
    
    # 9. Resultado final
    print(f"\n  9. RESULTADO FINAL:")
    print(f"     Alquiler mensual: ${alq_base:,.0f} ARS")
    alq_con_ct = alq_base * calcular_ct_alquiler(6, macrozona_id=macrozona_id, dormitorios=dorms)
    print(f"     Con CT 6 meses: ${alq_con_ct:,.0f} ARS")
    
    return alq_base


def main():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    
    # Cargar propiedades
    with open(os.path.join(base_dir, 'propiedades.json'), 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Cargar resultados de valuación
    with open(os.path.join(base_dir, 'data', 'valuaciones_cache.json'), 'r', encoding='utf-8') as f:
        cache = json.load(f)
    
    # Buscar propiedades objetivo
    objetivos = {
        'AYACUCHO': {'nombre': 'Ayacucho'},
        'MABEL': {'nombre': 'Mabel'},
        'VERA MUJICA': {'nombre': 'Vera Mujica'},
    }
    
    for prop in data.get('propiedades', []):
        nombre = (prop.get('nombre', '') or '').upper()
        for key, info in objetivos.items():
            if key in nombre:
                info['prop'] = prop
                info['res'] = cache.get(nombre, {})
    
    # Simular cada propiedad
    for key, info in objetivos.items():
        if 'prop' in info:
            simular_alquiler(info['nombre'], info['prop'], info['res'])
        else:
            print(f"\n  {key}: No encontrada en propiedades.json")
    
    # Simular escenario solo manual (sin cluster alquiler)
    print(f"\n{'='*60}")
    print(f"  ESCENARIO: Solo Valuación Manual (sin cluster alquiler)")
    print(f"{'='*60}")
    
    for key, info in objetivos.items():
        if 'prop' in info:
            nombre = info['nombre']
            prop = info['prop']
            
            print(f"\n  --- {nombre} ---")
            
            # Simular que no hay cluster alquiler
            res_sim = {
                'm2_base_alquiler': 0,  # Sin cluster
                'n_alquileres': 0,
                'factor_estado_alq': 1.0,
                'factor_calidad_alq': 1.0,
                'factor_anti_alq': 1.0,
                'nlp_ajuste_alq': 0.0,
                'valor_venta': 39514 if 'AYACUCHO' in nombre.upper() else 0,
            }
            
            # Calcular alquiler desde manual
            m2_cub = prop.get('m2_cubiertos', 0)
            m2_desc = prop.get('m2_descubiertos', 0)
            m2_equiv = m2_cub + (m2_desc * 0.1)
            
            # Sin cluster: usar cap rate
            valor_venta = res_sim.get('valor_venta', 0)
            if valor_venta > 0:
                cap_rate = 0.05  # Hardcoded como en generar_resultado_manual()
                alq_usd = valor_venta * cap_rate / 12
                alq_ars = alq_usd * 1480
                
                print(f"    Método: valor_venta × cap_rate / 12")
                print(f"    Valor venta: USD {valor_venta:,.0f}")
                print(f"    Cap rate (hardcoded): {cap_rate*100:.1f}%")
                print(f"    Alquiler: USD {alq_usd:,.0f} × 1480 = ${alq_ars:,.0f} ARS/mes")
                
                # Con CT
                dorms = prop.get('dormitorios', 0)
                ct = calcular_ct_alquiler(6, macrozona_id='resto_rosario', dormitorios=dorms)
                alq_con_ct = alq_ars * ct
                print(f"    Con CT 6 meses: ${alq_con_ct:,.0f} ARS/mes")
            else:
                print(f"    Sin valor de venta ni cluster alquiler → No se puede calcular")


if __name__ == '__main__':
    main()
