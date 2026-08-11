import json
import os

cache_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache_scraping.json')
with open(cache_path, encoding='utf-8') as f:
    cache = json.load(f)

props = cache.get('propiedades', [])

# Check Centro alquileres in detail
print("=== DETALLE DE ALQUILERES EN CENTRO ===")
centro_alquileres = []
for prop in props:
    if isinstance(prop, dict) and prop.get('operacion') == 'alquiler':
        zona = prop.get('zona', '')
        if 'centro' in zona.lower():
            centro_alquileres.append(prop)

for prop in centro_alquileres:
    print(f"\nDireccion: {prop.get('direccion', 'N/A')}")
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
print("=== VERIFICAR SI HAY VENTAS DE LAS MISMAS DIRECCIONES ===")
centro_direcciones = [p.get('direccion', '') for p in centro_alquileres]
for prop in props:
    if isinstance(prop, dict) and prop.get('operacion') == 'venta':
        addr = prop.get('direccion', '')
        if any(addr in cd or cd in addr for cd in centro_direcciones if cd):
            print(f"  VENTA: {addr[:50]} precio=${prop.get('precio', 0):,.0f} {prop.get('moneda', 'N/A')} m2={prop.get('m2', 0)}")
