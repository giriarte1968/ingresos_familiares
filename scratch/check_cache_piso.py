import json, sys, os

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

props = cache.get('propiedades', [])
print(f"Total propiedades en cache: {len(props)}")

# Sample first 20 properties
has_piso = sum(1 for p in props if 'piso' in p and p['piso'] is not None)
has_disposicion = sum(1 for p in props if 'disposicion' in p and p['disposicion'])
has_titulo = sum(1 for p in props if 'titulo' in p and p['titulo'])
has_desc = sum(1 for p in props if 'descripcion' in p and p['descripcion'])

print(f"Propiedades con campo 'piso': {has_piso}")
print(f"Propiedades con campo 'disposicion': {has_disposicion}")
print(f"Propiedades con campo 'titulo': {has_titulo}")
print(f"Propiedades con campo 'descripcion': {has_desc}")

print("\n--- EJEMPLO DE CAMPOS EN 3 PROPIEDADES DEL CACHE ---")
for p in props[:3]:
    print("Keys disponibles:", list(p.keys()))
    print("  piso:", p.get('piso'))
    print("  disposicion:", p.get('disposicion'))
    print("  titulo:", p.get('titulo', '')[:50])
    print("-" * 50)
