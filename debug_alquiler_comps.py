import json

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

props = data.get('propiedades', [])

lat_ref = -32.9606
lon_ref = -60.6298

alquiler_comps = []
for p in props:
    if not isinstance(p, dict):
        continue
    if p.get('operacion') != 'alquiler':
        continue
    
    lat = p.get('lat')
    lon = p.get('lon')
    if lat is None or lon is None:
        continue
    
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except:
        continue
    
    dlat = abs(lat_f - lat_ref) * 111000
    dlon = abs(lon_f - lon_ref) * 85000
    dist = (dlat**2 + dlon**2) ** 0.5
    
    if dist > 1000:
        continue
    
    precio = p.get('precio', 0)
    moneda = p.get('moneda', 'ARS')
    m2 = p.get('m2', 0)
    dorms = p.get('dormitorios', 0)
    
    if precio and m2 and m2 > 0:
        vm2_ars = (precio / m2) if moneda == 'ARS' else (precio * 1604 / m2)
        
        alquiler_comps.append({
            'direccion': (p.get('direccion', '') or '')[:40],
            'precio': precio,
            'moneda': moneda,
            'm2': m2,
            'dormitorios': dorms,
            'vm2_ars': vm2_ars,
            'dist': round(dist),
        })

alquiler_comps.sort(key=lambda x: x['vm2_ars'])

print(f"=== ALQUILER COMPARABLES NEAR AYACUCHO (radio 1000m) ===")
print(f"Total: {len(alquiler_comps)}")
print()

for i, c in enumerate(alquiler_comps):
    marker = " ← P50" if i == len(alquiler_comps) // 2 else ""
    print(f"{i+1:2d}. {c['direccion']:40s} | {c['moneda']} {c['precio']:>10,.0f} | {c['m2']:.0f}m² | {c['dormitorios']}d | {c['dist']:4d}m | VM2 {c['vm2_ars']:>10,.0f}{marker}")

if alquiler_comps:
    n = len(alquiler_comps)
    p50_idx = n // 2
    p50_vm2 = alquiler_comps[p50_idx]['vm2_ars']
    print(f"\n{'='*80}")
    print(f"P50 (índice {p50_idx}): {p50_vm2:,.0f} ARS/m²")
    print(f"Cache dice: 13,363.84 ARS/m²")
    print(f"Diferencia: {p50_vm2 - 13363.84:,.0f}")
