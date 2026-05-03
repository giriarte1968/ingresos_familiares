import json
data = json.load(open('cache_scraping.json', encoding='utf-8'))
props = data.get('propiedades', [])
with_year = [p for p in props if p.get('anio_construccion')]
print(f'Total props: {len(props)}')
print(f'With year: {len(with_year)}')
print(f'With lat/lon: {len([p for p in props if p.get("lat")])}')
print(f'Unique URLs: {len(set([p.get("url") for p in props if p.get("url")]))}')
print('--- Sample with year ---')
for p in with_year[:10]:
    print(f"  {p.get('anio_construccion')} | {p.get('direccion', '')[:40]}")