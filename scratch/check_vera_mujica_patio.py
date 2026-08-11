import json, sys, os
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import calcular_m2_equivalentes, valuar_propiedad_v7

props = json.load(open('propiedades.json', 'r', encoding='utf-8')).get('propiedades', [])
vera = None
for p in props:
    if 'vera' in p.get('nombre', '').lower() or 'vera' in p.get('direccion', '').lower():
        vera = p
        break

if vera:
    print("PROPIEDAD VERA MUJICA:")
    print("  nombre:", vera.get('nombre'))
    print("  piso:", vera.get('piso'))
    print("  m2_cubiertos:", vera.get('m2_cubiertos'))
    print("  m2_descubiertos:", vera.get('m2_descubiertos'))
    print("  m2_descubiertos_propios:", vera.get('m2_descubiertos_propios'))
    print("  m2_descubiertos_comun_exclusivo:", vera.get('m2_descubiertos_comun_exclusivo'))
    
    m2_eq = calcular_m2_equivalentes(vera)
    print("  m2_equivalentes calculados:", m2_eq)
    
    res = valuar_propiedad_v7(vera)
    print("  valor_propiedad_usd:", res.get('valor_propiedad_usd'))
    print("  m2_base_venta:", res.get('m2_base_venta'))
    print("  m2_microzona:", res.get('m2_microzona'))
    print("  formula usada en resultado:", f"${res.get('m2_base_venta',0):,.0f}/m² × {res.get('m2_equivalentes',0):.1f} m² = ${res.get('valor_propiedad_usd',0):,.0f}")
