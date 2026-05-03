import json
with open('cache_scraping.json', encoding='utf-8') as f:
    data = json.load(f)
props = data['propiedades']

# Find properties WITH anio_construccion
with_year = [p for p in props if p.get('anio_construccion')]
print(f'Total with anio_construccion: {len(with_year)}')

# Show first 10 with year
for p in with_year[:10]:
    url = p.get('url', '')
    year = p.get('anio_construccion')
    print(f"Year: {year} | URL: {url[:60]}...")
    print(f"  Full data: {p}")
    print("---")
    break