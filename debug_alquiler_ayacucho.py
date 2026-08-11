#!/usr/bin/env python3
import json, math

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

props = cache.get('propiedades', []) if isinstance(cache, dict) and 'propiedades' in cache else cache

LAT_AY = -32.960649375
LON_AY = -60.629792125

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    p = math.pi / 180
    a = 0.5 - math.cos((lat2 - lat1) * p) / 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lon2 - lon1) * p)) / 2
    return 2 * R * math.asin(math.sqrt(a))

# Check ALL alquileres USD in 1km, with full details
print("=" * 90)
print("DEBUG: ALL USD ALQUILERES IN 1km OF AYACUCHO (any dorm)")
print("=" * 90)

count = 0
for p in props:
    if p.get('operacion') != 'alquiler':
        continue
    if p.get('lat') is None or p.get('lon') is None:
        continue
    dist = haversine(LAT_AY, LON_AY, p['lat'], p['lon'])
    if dist <= 1000 and p.get('moneda', '').upper() == 'USD':
        count += 1
        precio = p.get('precio') or p.get('valor') or 0
        m2 = p.get('m2') or p.get('m2_cubiertos') or 0
        vm2 = p.get('valor_m2', 0)
        dorms = p.get('dormitorios', '?')
        tipo = p.get('tipo_inmueble', '?')
        amoblado = any(k in str(p.get('descripcion_libre', '')).lower() for k in ['amoblado', 'amueblado', 'equipado'])
        print(f"  {p.get('direccion','?')[:40]:<42} {dist:>5.0f}m {dorms:>2}d {tipo:<5} ${precio:>8,.0f} {m2:>4.0f}m2 ${vm2:>7,.0f}/m2 {'AMOBLADO' if amoblado else ''}")

print(f"\nTotal USD alquileres in 1km: {count}")

# Now check ARS too
print("\n" + "=" * 90)
print("DEBUG: ALL ARS ALQUILERES IN 1km OF AYACUCHO (any dorm)")
print("=" * 90)

count_ars = 0
for p in props:
    if p.get('operacion') != 'alquiler':
        continue
    if p.get('lat') is None or p.get('lon') is None:
        continue
    dist = haversine(LAT_AY, LON_AY, p['lat'], p['lon'])
    if dist <= 1000 and p.get('moneda', '').upper() == 'ARS':
        count_ars += 1
        precio = p.get('precio') or p.get('valor') or 0
        m2 = p.get('m2') or p.get('m2_cubiertos') or 0
        vm2 = p.get('valor_m2', 0)
        dorms = p.get('dormitorios', '?')
        tipo = p.get('tipo_inmueble', '?')
        amoblado = any(k in str(p.get('descripcion_libre', '')).lower() for k in ['amoblado', 'amueblado', 'equipado'])
        print(f"  {p.get('direccion','?')[:40]:<42} {dist:>5.0f}m {dorms:>2}d {tipo:<5} ${precio:>12,.0f} {m2:>4.0f}m2 ${vm2:>10,.0f}/m2 {'AMOBLADO' if amoblado else ''}")

print(f"\nTotal ARS alquileres in 1km: {count_ars}")

# Also check: what does the user's 353,000 ARS translate to in USD?
print(f"\n{'='*90}")
print("CROSS-CHECK: User's 353,000 ARS/month")
print(f"{'='*90}")
print(f"  353,000 ARS = {353000/1576:.2f} USD")
print(f"  353,000 ARS / 85m2 = {353000/85:,.0f} ARS/m2")
print(f"  {353000/1576/85:.2f} USD/m2")
print(f"  User says real USD median is ~9.17 USD/m2")
print(f"  This would mean: 85m2 * 9.17 * 1576 = {85*9.17*1576:,.0f} ARS/month")
print(f"  vs real 353,000 ARS/month")
print(f"  Ratio: {(85*9.17*1576)/353000:.1f}x")
