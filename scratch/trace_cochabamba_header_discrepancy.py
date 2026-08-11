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

print("=" * 80)
print("TRACE COCHABAMBA 45 WITH flex_dormitorios = 1:")
print("=" * 80)
res = valuar_propiedad_v7(cochabamba, retro_dias=0, flex_dormitorios=1)

print("  valor_propiedad_usd:", res.get('valor_propiedad_usd'))
print("  m2_microzona:", res.get('m2_microzona'))
print("  n_comps:", res.get('n_comps'))

meta = res.get('resolution_metadata', {})
print("  percentil_usado:", meta.get('percentil_usado'))
print("  radio_usado:", meta.get('radio_usado'))
comps = meta.get('comparables_reales', [])
print(f"  N Comparables devueltos: {len(comps)}")
for i, c in enumerate(comps, 1):
    print(f"   #{i:<2} | {c.get('direccion','?'):<35} | {c.get('dormitorios')}d | {c.get('m2')}m2 | ${c.get('precio',0):>8,.0f} USD | ${c.get('precio_m2',0):>6.1f}/m2 | cross={c.get('_cross_soft')}")
