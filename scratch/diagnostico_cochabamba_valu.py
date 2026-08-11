import sys, os, json
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7, obtener_mediana_cluster_v2

props_data = json.load(open('propiedades.json', 'r', encoding='utf-8'))
cochabamba = None
for p in props_data.get('propiedades', []):
    if 'cochabamba' in p.get('nombre', '').lower() or 'cochabamba' in p.get('direccion', '').lower():
        cochabamba = p
        break

print("Propiedad Cochabamba 45:", cochabamba)
if cochabamba:
    res = valuar_propiedad_v7(cochabamba, retro_dias=0, flex_dormitorios=None)
    print("=" * 80)
    print("RESULTADO DE valuar_propiedad_v7:")
    print("  m2_microzona:", res.get('m2_microzona'))
    print("  valor_propiedad_usd:", res.get('valor_propiedad_usd'))
    print("  m2_base_venta:", res.get('m2_base_venta'))
    print("  metodo_origen:", res.get('metodo_origen'))
    print("  resolution_metadata:", res.get('resolution_metadata', {}))
