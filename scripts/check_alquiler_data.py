import json
import os

cache_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cache_scraping.json')
with open(cache_path, encoding='utf-8') as f:
    cache = json.load(f)

props = cache.get('propiedades', [])

# Count alquileres by zona
alquileres_by_zona = {}
for prop in props:
    if isinstance(prop, dict) and prop.get('operacion') == 'alquiler':
        zona = prop.get('zona', 'Unknown')
        if zona not in alquileres_by_zona:
            alquileres_by_zona[zona] = []
        alquileres_by_zona[zona].append(prop)

print("=== ALQUILERES BY ZONA ===")
for zona, alquileres in sorted(alquileres_by_zona.items()):
    print(f"\n{zona}: {len(alquileres)} alquileres")
    
    # Get m2 values
    m2_values = [a.get('valor_m2', 0) for a in alquileres if a.get('valor_m2', 0) > 0]
    if m2_values:
        print(f"  Min m2: ${min(m2_values):,.0f}")
        print(f"  Max m2: ${max(m2_values):,.0f}")
        print(f"  Median m2: ${sorted(m2_values)[len(m2_values)//2]:,.0f}")
        print(f"  Avg m2: ${sum(m2_values)/len(m2_values):,.0f}")
    
    # Show some examples
    for a in alquileres[:3]:
        m2 = a.get('valor_m2', 0)
        precio = a.get('precio', 0)
        dorm = a.get('dormitorios', 0)
        addr = a.get('direccion', 'N/A')[:40]
        print(f"    {addr:40} m2=${m2:>10,.0f}  precio=${precio:>12,.0f}  dorm={dorm}")

# Check for suspicious patterns
print()
print("=== ALQUILERES CON M2 > 20,000 (POSIBLES VENTAS ETIQUETADAS COMO ALQUILER) ===")
suspicious = []
for prop in props:
    if isinstance(prop, dict) and prop.get('operacion') == 'alquiler':
        m2 = prop.get('valor_m2', 0)
        precio = prop.get('precio', 0)
        if m2 > 20000:
            suspicious.append({
                'direccion': prop.get('direccion', 'N/A')[:40],
                'm2': m2,
                'precio': precio,
                'dormitorios': prop.get('dormitorios', 0),
                'zona': prop.get('zona', 'N/A'),
                'fuente': prop.get('fuente', 'N/A')
            })

for s in suspicious:
    print(f"  {s['direccion']:40} m2=${s['m2']:>10,.0f}  precio=${s['precio']:>12,.0f}  dorm={s['dormitorios']}  zona={s['zona']}")

# Check distribution of m2 values
print()
print("=== DISTRIBUCIÓN DE M2 EN ALQUILERES ===")
all_m2 = []
for prop in props:
    if isinstance(prop, dict) and prop.get('operacion') == 'alquiler':
        m2 = prop.get('valor_m2', 0)
        if m2 > 0:
            all_m2.append(m2)

if all_m2:
    all_m2.sort()
    print(f"Total alquileres with m2: {len(all_m2)}")
    print(f"Min: ${min(all_m2):,.0f}")
    print(f"Max: ${max(all_m2):,.0f}")
    print(f"Median: ${all_m2[len(all_m2)//2]:,.0f}")
    print(f"Avg: ${sum(all_m2)/len(all_m2):,.0f}")
    
    # Distribution
    ranges = [(0, 5000), (5000, 10000), (10000, 15000), (15000, 20000), (20000, 50000), (50000, 100000), (100000, float('inf'))]
    for low, high in ranges:
        count = len([m for m in all_m2 if low <= m < high])
        print(f"  ${low:>6,} - ${high:>6,}: {count} alquileres")
