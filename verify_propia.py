import json
data = json.load(open('cache_scraping.json', encoding='utf-8'))
props = data.get('propiedades', [])

# Check Propia properties
propia = [p for p in props if 'propia.com.ar' in p.get('url','')]
print(f'Total Propia: {len(propia)}')

# Check with year
with_year = [p for p in props if p.get('anio_construccion')]
print(f'With year: {len(with_year)}')

# Print some with year
for p in with_year[:10]:
    print(f"  {p.get('anio_construccion')} | {p.get('direccion', '')[:50]}")