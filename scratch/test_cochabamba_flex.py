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
    print("=" * 80)
    print("TEST 1: flex_dormitorios = 1 (PRODUCCION NUEVO v8f)")
    res_flex = valuar_propiedad_v7(cochabamba, retro_dias=0, flex_dormitorios=1)
    print("  valor_propiedad_usd:", res_flex.get('valor_propiedad_usd'))
    print("  m2_microzona:", res_flex.get('m2_microzona'))
    print("  n_comps:", res_flex.get('n_comps'))
    
    print("=" * 80)
    print("TEST 2: flex_dormitorios = 0 (SIN FLEX)")
    res_noflex = valuar_propiedad_v7(cochabamba, retro_dias=0, flex_dormitorios=0)
    print("  valor_propiedad_usd:", res_noflex.get('valor_propiedad_usd'))
    print("  m2_microzona:", res_noflex.get('m2_microzona'))
    print("  n_comps:", res_noflex.get('n_comps'))
