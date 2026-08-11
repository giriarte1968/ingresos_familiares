import sys, os, json
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7

props_data = json.load(open('propiedades.json', 'r', encoding='utf-8'))
cochabamba = None
for p in props_data.get('propiedades', []):
    if 'cochabamba' in p.get('nombre', '').lower():
        cochabamba = p
        break

print("=" * 80)
print("TESTING COCHABAMBA 45 WITH NATURAL SELECTION (retro_dias=0, flex_dormitorios=1):")
print("=" * 80)
res = valuar_propiedad_v7(cochabamba, retro_dias=0, flex_dormitorios=1)

print("  valor_propiedad_usd:", res.get('valor_propiedad_usd'))
print("  m2_microzona:", res.get('m2_microzona'))
print("  m2_base_venta:", res.get('m2_base_venta'))
print("  n_comps:", res.get('n_comps'))
