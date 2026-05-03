import json
data = json.load(open('cache_scraping.json', encoding='utf-8'))
props = data['propiedades']

# Buscar propiedades de argenprop con URLs
argen = [p for p in props if p.get('fuente') == 'argenprop' and p.get('url')]
print('Argenprop URLs:', len(argen))
if argen:
    print('Sample:', argen[0].get('url'))

# TTL
ttl = [p for p in props if p.get('fuente') == 'ttl' and p.get('url')]
print('TTL URLs:', len(ttl))
if ttl:
    print('Sample:', ttl[0].get('url'))

# La Capital
lc = [p for p in props if p.get('fuente') == 'lacapital' and p.get('url')]
print('La Capital URLs:', len(lc))
if lc:
    print('Sample:', lc[0].get('url'))

# Bienes Rosario
br = [p for p in props if p.get('fuente') == 'bienesrosario' and p.get('url')]
print('Bienes Rosario URLs:', len(br))
if br:
    print('Sample:', br[0].get('url'))