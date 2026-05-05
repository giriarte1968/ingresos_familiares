import json
import sys
sys.path.insert(0, 'C:/Users/Gustavo/ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7

with open('propiedades.json') as f:
    d = json.load(f)
    props = d['propiedades']

print('=== ALQUILERES - GAP 0.92 ===')
for nombre in ['Mabel', 'Ayacucho', 'Vera Mujica', 'P1200']:
    prop = [p for p in props if p.get('nombre') == nombre][0]
    r = valuar_propiedad_v7(prop, fecha_ref='2026-04')
    alquiler = r.get('alquiler_estimado_ars', 0)
    cap = r.get('cap_rate_anual', 0)
    venta = r.get('valor_propiedad_usd', 0)
    print(f'{nombre}: ${alquiler:,.0f} | Cap: {cap:.1f}% | Venta: ${venta:,.0f}')