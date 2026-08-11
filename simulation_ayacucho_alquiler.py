#!/usr/bin/env python3
import json, math, statistics

print("=" * 70)
print("SIMULACION ALQUILER AYACUCHO 1805 -- 85m2, 3 DORM")
print("=" * 70)

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

props = cache.get('propiedades', []) if isinstance(cache, dict) and 'propiedades' in cache else cache
print(f"\nTotal propiedades en cache: {len(props)}")

LAT_AYACUCHO = -32.960649375
LON_AYACUCHO = -60.629792125
USDT_ARS = 1576

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    p = math.pi / 180
    a = 0.5 - math.cos((lat2 - lat1) * p) / 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * (1 - math.cos((lon2 - lon1) * p)) / 2
    return 2 * R * math.asin(math.sqrt(a))

# Filtrar alquileres en radio 1km
alq_usd_3d = []
alq_ars_3d = []
for p in props:
    if p.get('operacion') != 'alquiler':
        continue
    if p.get('lat') is None or p.get('lon') is None:
        continue
    dist = haversine(LAT_AYACUCHO, LON_AYACUCHO, p['lat'], p['lon'])
    if dist <= 1000 and p.get('dormitorios') == 3:
        p['_dist_m'] = round(dist, 1)
        moneda = p.get('moneda', '').upper()
        if moneda == 'USD':
            alq_usd_3d.append(p)
        elif moneda == 'ARS':
            alq_ars_3d.append(p)

print(f"\nAlquileres en radio 1km, 3 dorm: USD={len(alq_usd_3d)}, ARS={len(alq_ars_3d)}")

# ============ SECCION 1: USD ============
print(f"\n{'='*70}")
print("SECCION 1: CLUSTER USD -- Alquileres en USD, 3 dorm, 1km")
print(f"{'='*70}")

usd_m2_vals = []
for p in alq_usd_3d:
    precio = p.get('precio') or p.get('valor') or 0
    m2 = p.get('m2') or p.get('m2_cubiertos') or 0
    valor_m2 = p.get('valor_m2', 0)
    fecha = p.get('date_created', '')[:10]
    if valor_m2 > 0 and m2 > 0:
        vm2 = valor_m2
    elif precio > 0 and m2 > 0:
        vm2 = precio / m2
    else:
        vm2 = 0
    if vm2 > 0:
        usd_m2_vals.append(vm2)
    print(f"  {p.get('direccion','?')[:42]:<44} {p['_dist_m']:>5.0f}m  {precio:>8,.0f}  {m2:>4.0f}m2  {vm2:>6.2f}  {fecha}")

if usd_m2_vals:
    usd_m2_vals.sort()
    n = len(usd_m2_vals)
    median_usd = statistics.median(usd_m2_vals)
    mean_usd = statistics.mean(usd_m2_vals)
    p25 = usd_m2_vals[int(n * 0.25)] if n > 1 else usd_m2_vals[0]
    p75 = usd_m2_vals[int(n * 0.75)] if n > 1 else usd_m2_vals[-1]
    
    print(f"\n  RESUMEN USD (n={n}):")
    print(f"    Mediana:  {median_usd:.2f} USD/m2")
    print(f"    Promedio: {mean_usd:.2f} USD/m2")
    print(f"    P25:      {p25:.2f} USD/m2")
    print(f"    P75:      {p75:.2f} USD/m2")
    print(f"    IQR:      {p75 - p25:.2f} USD/m2")
    
    median_ars_from_usd = median_usd * USDT_ARS
    print(f"\n    Conversion a ARS (x{USDT_ARS}):")
    print(f"      Mediana: {median_usd:.2f} USD/m2 x {USDT_ARS} = {median_ars_from_usd:,.0f} ARS/m2")
else:
    print("  No se pudieron calcular valores/m2")
    median_usd = 0

# ============ SECCION 2: ARS ============
print(f"\n{'='*70}")
print("SECCION 2: CLUSTER ARS -- Alquileres en ARS, 3 dorm, 1km")
print(f"{'='*70}")

ars_m2_all = []
ars_m2_clean = []
for p in alq_ars_3d:
    precio = p.get('precio') or p.get('valor') or 0
    m2 = p.get('m2') or p.get('m2_cubiertos') or 0
    valor_m2 = p.get('valor_m2', 0)
    fecha = p.get('date_created', '')[:10]
    if valor_m2 > 0 and m2 > 0:
        vm2 = valor_m2
    elif precio > 0 and m2 > 0:
        vm2 = precio / m2
    else:
        vm2 = 0
    
    filtro = ""
    if vm2 > 0:
        ars_m2_all.append(vm2)
        if 2000 <= vm2 <= 8000:
            ars_m2_clean.append(vm2)
            filtro = "[CLEAN]"
        else:
            filtro = "[EXCL]"
    
    print(f"  {p.get('direccion','?')[:42]:<44} {p['_dist_m']:>5.0f}m  {precio:>10,.0f}  {m2:>4.0f}m2  {vm2:>8.0f}  {fecha}  {filtro}")

if ars_m2_clean:
    ars_m2_clean.sort()
    n_c = len(ars_m2_clean)
    med_c = statistics.median(ars_m2_clean)
    mean_c = statistics.mean(ars_m2_clean)
    p25_c = ars_m2_clean[int(n_c * 0.25)] if n_c > 1 else ars_m2_clean[0]
    p75_c = ars_m2_clean[int(n_c * 0.75)] if n_c > 1 else ars_m2_clean[-1]
    
    print(f"\n  RESUMEN ARS CLEAN (n={n_c} de {len(ars_m2_all)} total):")
    print(f"    Mediana:  {med_c:,.0f} ARS/m2")
    print(f"    Promedio: {mean_c:,.0f} ARS/m2")
    print(f"    P25:      {p25_c:,.0f} ARS/m2")
    print(f"    P75:      {p75_c:,.0f} ARS/m2")
else:
    print("\n  No hay entradas ARS limpias (rango 2000-8000 ARS/m2)")
    med_c = 0

if ars_m2_all:
    all_sorted = sorted(ars_m2_all)
    print(f"\n  Stats TODOS ARS (n={len(all_sorted)}):")
    print(f"    Mediana:  {statistics.median(all_sorted):,.0f} ARS/m2")
    print(f"    Min:      {min(all_sorted):,.0f} ARS/m2")
    print(f"    Max:      {max(all_sorted):,.0f} ARS/m2")

# ============ SECCION 3: COMPARACION ============
print(f"\n{'='*70}")
print("SECCION 3: COMPARACION -- Cual fuente es mas confiable?")
print(f"{'='*70}")

print(f"\n  Contexto del usuario:")
print(f"    Alquiler real esperado: $353,000 ARS/mes")
print(f"    Superficie: 85 m2")
print(f"    Valor implicito: {353000/85:,.0f} ARS/m2")
print(f"    Moneda real: 274 de 285 alquileres en USD (96%)")

if median_usd > 0:
    print(f"\n  Fuente USD (cache, n={len(usd_m2_vals)}):")
    print(f"    Mediana: {median_usd:.2f} USD/m2 -> {median_usd*USDT_ARS:,.0f} ARS/m2")

if med_c > 0:
    print(f"\n  Fuente ARS (cache limpio, n={n_c}):")
    print(f"    Mediana: {med_c:,.0f} ARS/m2")

if median_usd > 0 and med_c > 0:
    diff_pct = abs(median_usd * USDT_ARS - med_c) / med_c * 100
    print(f"\n  Diferencia: {diff_pct:.1f}%")
    print(f"\n  Veredicto: USD es MAS confiable porque:")
    print(f"    1. 96% de alquileres en USD")
    print(f"    2. Mayor muestra = mayor estabilidad")
    print(f"    3. ARS incluye outliers extremos")

# ============ SECCION 4: SIMULACION FINAL ============
print(f"\n{'='*70}")
print("SECCION 4: SIMULACION FINAL -- FORMULA DE ALQUILER")
print(f"{'='*70}")

# Elegir mejor fuente
if median_usd > 0:
    m2_alq_usd = median_usd
    m2_alq_ars = m2_alq_usd * USDT_ARS
    fuente = "USD cache"
else:
    m2_alq_usd = 9.17
    m2_alq_ars = m2_alq_usd * USDT_ARS
    fuente = "usuario (9.17 USD/m2)"

print(f"\n  m2_alquiler (fuente: {fuente}):")
print(f"    USD: {m2_alq_usd:.2f} USD/m2")
print(f"    ARS: {m2_alq_ars:,.0f} ARS/m2")

# GAP 0.92
alq_92 = 85 * m2_alq_ars * 0.92
print(f"\n  --- ESCENARIO A: GAP = 0.92 ---")
print(f"    85 x {m2_alq_ars:,.0f} x 0.92 = {alq_92:,.0f} ARS/mes")
print(f"    vs $353,000: {(alq_92/353000-1)*100:+.1f}%")

# Sin GAP
alq_no = 85 * m2_alq_ars
print(f"\n  --- ESCENARIO B: SIN GAP ---")
print(f"    85 x {m2_alq_ars:,.0f} = {alq_no:,.0f} ARS/mes")
print(f"    vs $353,000: {(alq_no/353000-1)*100:+.1f}%")

# GAP 0.96 (MEMORIA)
alq_96 = 85 * m2_alq_ars * 0.96
print(f"\n  --- ESCENARIO C: GAP = 0.96 (MEMORIA) ---")
print(f"    85 x {m2_alq_ars:,.0f} x 0.96 = {alq_96:,.0f} ARS/mes")
print(f"    vs $353,000: {(alq_96/353000-1)*100:+.1f}%")

# ============ SECCION 5: SENSIBILIDAD ============
print(f"\n{'='*70}")
print("SECCION 5: QUE m2_ALQUILER NECESITO PARA LLEGAR A $353,000?")
print(f"{'='*70}")

m2_92 = 353000 / (85 * 0.92)
m2_96 = 353000 / (85 * 0.96)
m2_no = 353000 / 85

print(f"\n  Con GAP 0.92: m2 = {m2_92:,.0f} ARS/m2 ({m2_92/USDT_ARS:.2f} USD/m2)")
print(f"  Con GAP 0.96: m2 = {m2_96:,.0f} ARS/m2 ({m2_96/USDT_ARS:.2f} USD/m2)")
print(f"  Sin GAP:      m2 = {m2_no:,.0f} ARS/m2 ({m2_no/USDT_ARS:.2f} USD/m2)")

print(f"\n  Tu m2 real: 9.17 USD/m2 = {9.17*USDT_ARS:,.0f} ARS/m2")
if median_usd > 0:
    print(f"  Cache m2:   {median_usd:.2f} USD/m2 = {median_usd*USDT_ARS:,.0f} ARS/m2")

# ============ CONCLUSION ============
print(f"\n{'='*70}")
print("CONCLUSION")
print(f"{'='*70}")
print(f"""
  1. El cache tiene {len(usd_m2_vals)} alquileres USD y {len(ars_m2_clean)} ARS limpios en 1km, 3 dorm.
  2. Mediana USD: {median_usd:.2f} USD/m2 = {median_usd*USDT_ARS:,.0f} ARS/m2
  3. Formula actual (GAP 0.92): 85 x {median_usd*USDT_ARS:,.0f} x 0.92 = {alq_92:,.0f} ARS/mes
     vs esperado $353,000: {(alq_92/353000-1)*100:+.1f}%
  4. Sin GAP: 85 x {median_usd*USDT_ARS:,.0f} = {alq_no:,.0f} ARS/mes
     vs esperado $353,000: {(alq_no/353000-1)*100:+.1f}%
  5. Para llegar a $353,000 con GAP 0.92, necesitarias m2 = {m2_92/USDT_ARS:.2f} USD/m2
""")
