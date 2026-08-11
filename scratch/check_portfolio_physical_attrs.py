import json, sys, os

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

with open('propiedades.json', 'r', encoding='utf-8') as f:
    props = json.load(f)

print(f"{'Nombre':<16} {'Piso':>4} {'Vista':<12} {'m2 Cub':>7} {'Patio m2':>9}")
print("-" * 55)
for p in props['propiedades']:
    nombre = p['nombre']
    piso = p.get('piso')
    vista = p.get('vista', '')
    m2_cub = p.get('m2_cubiertos', 0) or p.get('m2', 0)
    patio = p.get('m2_descubiertos_comun_exclusivo', 0) + p.get('m2_descubiertos_propios', 0)
    print(f"{nombre:<16} {str(piso):>4} {vista:<12} {m2_cub:>7.1f} {patio:>9.1f}")
