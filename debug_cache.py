import json

# Load cache
with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

# Check Martin zone, venta properties
martin_venta = []
for p in cache.get('propiedades', []):
    z = p.get('zona', '')
    if z and 'martin' in z.lower():
        if p.get('operacion') == 'venta':
            martin_venta.append(p)

print('=== MARTIN ZONA - VENTA PROPERTIES ===')
print('Total:', len(martin_venta))

# Check zona field values
zonas = set()
for p in martin_venta:
    zonas.add(p.get('zona', 'N/A'))
print('Zonas:', zonas)

# Check dorms values
dorms = set()
for p in martin_venta:
    dorms.add(p.get('dormitorios'))
print('Dormitorios:', dorms)

# Check moneda values
monedas = set()
for p in martin_venta:
    monedas.add(p.get('moneda'))
print('Moneda:', monedas)

# Sample first 3
print('')
print('Sample:')
for i, p in enumerate(martin_venta[:3], 1):
    print(i, 'zona=', p.get('zona'), ',dorms=', p.get('dormitorios'), ',moneda=', p.get('moneda'), ',m2=', p.get('m2'), ',valor_m2=', p.get('valor_m2'))