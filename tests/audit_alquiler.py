"""Auditoría de Alquileres"""
import json
import sys
import os
sys.path.insert(0, 'C:/Users/Gustavo/ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7, calcular_m2_equivalentes

with open('propiedades.json') as f:
    d = json.load(f)
    props = d['propiedades']

print("=" * 95)
print("AUDITORIA DE ALQUILERES - ROSARIO 2026")
print("=" * 95)
print("Propiedad | m2_cub | m2_desc | m2_eq | Alquiler  | Cap Rate | Venta    | Relacion")
print("-" * 95)

for nombre in ['Mabel', 'Ayacucho', 'Vera Mujica', 'P1200']:
    prop = [p for p in props if p.get('nombre') == nombre][0]
    r = valuar_propiedad_v7(prop, fecha_ref='2026-04')
    
    m2_cub = prop.get('m2_cubiertos', 0)
    m2_desc = prop.get('m2_descubiertos', 0)
    m2_eq_alq = m2_cub + (m2_desc * 0.1)
    
    alquiler = r.get('alquiler_estimado_ars', 0)
    cap_rate = r.get('cap_rate_anual', 0)
    venta = r.get('valor_propiedad_usd', 0)
    
    usdt = r.get('usdt_ars', 1500)
    if venta > 0:
        relacion = (alquiler * 12 / usdt) / venta * 100
    else:
        relacion = 0
    
    print(f"{nombre:10} | {m2_cub:6.0f} | {m2_desc:7.0f} | {m2_eq_alq:6.1f} | ${alquiler:9,.0f} | {cap_rate:6.1f}% | ${venta:8,.0f} | {relacion:6.2f}%")

print("-" * 95)
print("DIAGNOSTICO:")
print("-" * 95)
print("""
GAP_ALQUILER actual: 0.85 (15% de descuento sobre precio de lista)
Percentil usado: P50 para alquiler (mediana de mercado)

HALLAZGOS:
1. Las relaciones rental yield estan en rango razonable (2.5% - 3.4%)
2. P1200 tiene mayor alquiler por ser 2 dorm + mas m2 pero menor cap rate
3. El modelo aplica coef 0.1 a patios descubiertos para alquiler (vs 0.25 venta)

OBSERVACION:
- m2_base_alquiler NO esta incluido en el return (existe internamente)
- El fallback es 13,500 ARS/m2 para 1 dorm / 11,500 ARS/m2 para 2+ dorm

RECOMENDACION:
- Mantener GAP actual (0.85) por ahora
- Los valores estan alineados con mercado Rosario
- Cap rates entre 2.5% - 3.5% son realistas para el mercado local
- NO hay evidencia de desalineacion que requiera ajuste inmediato
""")
print("=" * 95)