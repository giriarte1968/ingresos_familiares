import json
import os

cache_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache_scraping.json')
with open(cache_path, encoding='utf-8') as f:
    cache = json.load(f)

props = cache.get('propiedades', [])

# Check specific properties
targets = ['Guemes 2036', 'Entre Rios 190', 'Salta 1400', 'Wheelwright 1400', 'Catamarca y Paraguay']

print("=== DETALLE DE ALQUILERES EN CLUSTER ===")
for prop in props:
    if isinstance(prop, dict):
        addr = prop.get('direccion', '')
        if any(t.lower() in addr.lower() for t in targets):
            print(f"\nDireccion: {addr}")
            print(f"  operacion: {prop.get('operacion')}")
            print(f"  moneda: {prop.get('moneda')}")
            print(f"  precio: {prop.get('precio')}")
            print(f"  m2: {prop.get('m2')}")
            print(f"  valor_m2: {prop.get('valor_m2')}")
            print(f"  dormitorios: {prop.get('dormitorios')}")
            print(f"  zona: {prop.get('zona')}")
            print(f"  fuente: {prop.get('fuente')}")
            print(f"  date_created: {prop.get('date_created')}")
            print(f"  lat: {prop.get('lat')}")
            print(f"  lon: {prop.get('lon')}")

# Check if there are VENTA versions of these addresses
print()
print("=== VERIFICAR SI SON VENTAS O ALQUILERES ===")
for prop in props:
    if isinstance(prop, dict):
        addr = prop.get('direccion', '')
        if any(t.lower() in addr.lower() for t in targets):
            op = prop.get('operacion', 'N/A')
            moneda = prop.get('moneda', 'N/A')
            precio = prop.get('precio', 0)
            m2 = prop.get('m2', 0)
            if op == 'venta':
                print(f"  VENTA: {addr[:50]} precio=${precio:,.0f} {moneda} m2={m2}")
