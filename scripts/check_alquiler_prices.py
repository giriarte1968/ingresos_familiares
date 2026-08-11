import json
import os

cache_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache_scraping.json')
with open(cache_path, encoding='utf-8') as f:
    cache = json.load(f)

props = cache.get('propiedades', [])

# Count alquileres by zona and check prices
print("=== ALQUILERES POR ZONA (VERIFICACIÓN DE PRECIOS) ===")
alquileres_by_zona = {}
for prop in props:
    if isinstance(prop, dict) and prop.get('operacion') == 'alquiler':
        zona = prop.get('zona', 'Unknown')
        m2 = prop.get('valor_m2', 0)
        precio = prop.get('precio', 0)
        moneda = prop.get('moneda', 'N/A')
        dorm = prop.get('dormitorios', 0)
        
        if zona not in alquileres_by_zona:
            alquileres_by_zona[zona] = []
        
        if m2 > 0 and precio > 0:
            alquileres_by_zona[zona].append({
                'm2': m2,
                'precio': precio,
                'moneda': moneda,
                'dormitorios': dorm,
                'direccion': prop.get('direccion', 'N/A')[:40]
            })

for zona, alquileres in sorted(alquileres_by_zona.items()):
    if not alquileres:
        continue
    
    print(f"\n{zona}: {len(alquileres)} alquileres")
    
    # Separate by currency
    ars_alquileres = [a for a in alquileres if a['moneda'] == 'ARS']
    usd_alquileres = [a for a in alquileres if a['moneda'] == 'USD']
    
    print(f"  ARS: {len(ars_alquileres)} alquileres")
    if ars_alquileres:
        ars_m2 = [a['m2'] for a in ars_alquileres]
        print(f"    Min m2: ${min(ars_m2):,.0f}")
        print(f"    Max m2: ${max(ars_m2):,.0f}")
        print(f"    Median m2: ${sorted(ars_m2)[len(ars_m2)//2]:,.0f}")
        
        # Show some examples
        for a in ars_alquileres[:3]:
            print(f"    {a['direccion']:40} m2=${a['m2']:>10,.0f}  precio=${a['precio']:>12,.0f}  dorm={a['dormitorios']}")
    
    print(f"  USD: {len(usd_alquileres)} alquileres")
    if usd_alquileres:
        usd_m2 = [a['m2'] for a in usd_alquileres]
        print(f"    Min m2: ${min(usd_m2):,.0f}")
        print(f"    Max m2: ${max(usd_m2):,.0f}")
        print(f"    Median m2: ${sorted(usd_m2)[len(usd_m2)//2]:,.0f}")
        
        # Show some examples
        for a in usd_alquileres[:3]:
            print(f"    {a['direccion']:40} m2=${a['m2']:>10,.0f}  precio=${a['precio']:>12,.0f}  dorm={a['dormitorios']}")

# Check for suspicious patterns
print()
print("=== ALQUILERES CON PRECIOS SOSPECHOSOS ===")
suspicious_ars = []
for prop in props:
    if isinstance(prop, dict) and prop.get('operacion') == 'alquiler':
        m2 = prop.get('valor_m2', 0)
        precio = prop.get('precio', 0)
        moneda = prop.get('moneda', 'N/A')
        
        if moneda == 'ARS' and m2 > 20000:
            suspicious_ars.append({
                'direccion': prop.get('direccion', 'N/A')[:40],
                'm2': m2,
                'precio': precio,
                'dormitorios': prop.get('dormitorios', 0),
                'zona': prop.get('zona', 'N/A')
            })

print(f"Total alquileres ARS con m2 > 20,000: {len(suspicious_ars)}")
for s in suspicious_ars[:10]:
    print(f"  {s['direccion']:40} m2=${s['m2']:>10,.0f}  precio=${s['precio']:>12,.0f}  dorm={s['dormitorios']}  zona={s['zona']}")
