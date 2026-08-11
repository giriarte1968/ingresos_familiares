import sys, os, json
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7

props_data = json.load(open('propiedades.json', 'r', encoding='utf-8'))
cochabamba = None
for p in props_data.get('propiedades', []):
    if 'cochabamba' in p.get('nombre', '').lower() or 'cochabamba' in p.get('direccion', '').lower():
        cochabamba = p
        break

if cochabamba:
    print("=" * 90)
    print("EJECUTANDO valuar_propiedad_v7 PARA COCHABAMBA 45 (retro=60, flex=[1..5])")
    print("=" * 90)
    res = valuar_propiedad_v7(cochabamba, retro_dias=60, flex_dormitorios=[1, 2, 3, 4, 5])
    print("  valor_propiedad_usd:", res.get('valor_propiedad_usd'))
    print("  m2_microzona:", res.get('m2_microzona'))
    print("  m2_base_venta:", res.get('m2_base_venta'))
    print("  valor_venta_conservador:", res.get('valor_venta_conservador'))
    print("  valor_venta_optimista:", res.get('valor_venta_optimista'))
    print("  n_comps:", res.get('n_comps'))
    
    meta = res.get('resolution_metadata', {})
    print("  percentil_usado:", meta.get('percentil_usado'))
    print("  radio_usado:", meta.get('radio_usado'))
    print("  zona_resolucion:", meta.get('zona_resolucion'))
