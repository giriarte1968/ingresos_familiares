import json
data = json.load(open('cache_scraping.json', encoding='utf-8'))
props = data['propiedades']

fuentes = {}
for p in props:
    f = p.get('fuente', 'unknown')
    fuentes[f] = fuentes.get(f, 0) + 1

print('Fuentes:', fuentes)

urls = [p.get('url') for p in props if p.get('url')]
print('URLs total:', len(urls))
print('Sample URLs:', urls[:10])