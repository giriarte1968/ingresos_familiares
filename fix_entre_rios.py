from parsers.mercado_inmobiliario import valuar_propiedad_v7
import json

with open('propiedades.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

er = next(p for p in data['propiedades'] if 'Entre' in p.get('nombre', ''))

# Test different retro values
for retro in [0, 36, 60]:
    res = valuar_propiedad_v7(er, retro_dias=retro, flex_dormitorios=None)
    rm = res.get('resolution_metadata', {})
    print(f"retro={retro:>2} | USD {res['valor_propiedad_usd']:>9,.0f} | m2_base={res.get('m2_base_venta'):>8.2f} | m2_eq={res.get('m2_equivalentes'):>6.2f} | comps={rm.get('n_propiedades'):>3} | alq={res.get('alquiler_estimado_ars'):>9,.0f}")
