"""
Simulacion: Cochabamba 45 con Pellegrini como barrera DURA (excluyente).
Compara con el resultado actual del motor (Pellegrini = blanda, 10% penalty).
Uses real barrier geometry via check_barrier_crossing, then reclassifies
Pellegrini from soft -> hard to simulate the exclusion.
"""
import json, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Constants
SUBJECT_LAT = -32.9611391
SUBJECT_LON = -60.6264443
RADIO_M = 800

# Load data
base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(base, "cache_scraping.json"), "r", encoding="utf-8") as f:
    scraping_data = json.load(f)

with open(os.path.join(base, "propiedades.json"), "r", encoding="utf-8") as f:
    prop_data = json.load(f)

# Find subject property
subject = None
for p in prop_data.get("propiedades", []):
    if p.get("nombre") == "Cochabamba 45":
        subject = p
        break

if not subject:
    print("ERROR: Cochabamba 45 not found in propiedades.json")
    sys.exit(1)

print("=" * 72)
print("SIMULACION: PELLEGRINI COMO BARRERA DURA (EXCLUYENTE)")
print("=" * 72)
print()
print("Propiedad: %s" % subject["nombre"])
print("  Lat: %s, Lon: %s" % (subject["lat"], subject["lon"]))
print("  Tipo: %s, Dorms: %s, m2: %s" % (subject["tipo_inmueble"], subject["dormitorios"], subject["m2_cubiertos"]))
print("  Anio construccion: %s" % subject.get("anio_construccion", "N/A"))
print("  Zona: %s" % subject.get("zona", "N/A"))

# Distance function
def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# Get all 4-dorm venta comparables within 800m
comps_all = []
for entry in scraping_data.get("propiedades", []):
    if entry.get("operacion", "").lower() != "venta":
        continue
    dorms = entry.get("dormitorios")
    if dorms is None or int(dorms) != 4:
        continue
    lat = entry.get("lat") or entry.get("latitud")
    lon = entry.get("lon") or entry.get("longitud")
    if not lat or not lon:
        continue
    lat, lon = float(lat), float(lon)
    dist_m = haversine_km(SUBJECT_LAT, SUBJECT_LON, lat, lon) * 1000
    if dist_m > RADIO_M:
        continue
    precio = entry.get("precio", 0) or 0
    m2 = entry.get("m2") or entry.get("m2_cubiertos", 0) or 0
    if precio <= 0 or m2 <= 0:
        continue
    precio_m2 = precio / m2

    comps_all.append({
        "direccion": entry.get("direccion", entry.get("direccion_limpia", "?")),
        "lat": lat,
        "lon": lon,
        "dormitorios": int(dorms),
        "precio": precio,
        "m2": m2,
        "precio_m2": round(precio_m2, 2),
        "distancia_m": round(dist_m, 0),
        "date_created": entry.get("date_created", ""),
        "tipo": entry.get("tipo", entry.get("tipo_inmueble", "?")),
    })

print()
print("-" * 72)
print("COMPARABLES 4-DORM VENTA EN RADIO %dm:" % RADIO_M)
print("-" * 72)
print("Total encontrados: %d" % len(comps_all))

if not comps_all:
    print("No se encontraron comparables. Abortando.")
    sys.exit(0)

# ============================================================
# PART A: Current engine behavior (Pellegrini = soft)
# ============================================================
from parsers.location_engine import cargar_barreras, check_barrier_crossing

barreras = cargar_barreras()
print("Barreras cargadas: %d features" % len(barreras))

# Check barrier crossing for each comp using real geometry
# Current engine: hard -> excluded, soft -> cross_soft (penalized), False -> same_side
same_side_soft = []
cross_soft = []
excluded_hard = []

for c in comps_all:
    try:
        result = check_barrier_crossing(
            (SUBJECT_LON, SUBJECT_LAT),
            (c["lon"], c["lat"]),
            barreras
        )
        if result == 'hard':
            excluded_hard.append(c)
        elif result == 'soft':
            cross_soft.append(c)
        else:
            same_side_soft.append(c)
    except Exception:
        same_side_soft.append(c)

print()
print("-" * 72)
print("PART A: COMPORTAMIENTO ACTUAL (Pellegrini = blanda)")
print("-" * 72)
print("  Same-side (sin cruce): %d" % len(same_side_soft))
print("  Cross-soft (Pellegrini): %d" % len(cross_soft))
print("  Excluded-hard (ferrocarril/otras): %d" % len(excluded_hard))

# ============================================================
# PART B: Simulation - Pellegrini as HARD barrier
# ============================================================
# Strategy: identify which soft barriers are Pellegrini,
# then reclassify those as hard -> excluded

# Find Pellegrini barrier features
pellegrini_features = []
for b in barreras:
    props = b.get("properties", {})
    name = str(props.get("name", "")).lower()
    bt = props.get("barrier_type")
    if "pellegrini" in name:
        pellegrini_features.append(b)

print()
print("Pellegrini barrier features found: %d" % len(pellegrini_features))

# Now simulate: for comps that currently cross Pellegrini as soft,
# check if treating Pellegrini as hard would exclude them
# We need to check if the crossing barrier is Pellegrini specifically

# Since check_barrier_crossing returns the type but not WHICH barrier,
# we need to manually check Pellegrini barriers only

def check_pellegrini_crossing(p1, p2, pellegrini_barriers):
    """Check if line p1->p2 crosses any Pellegrini barrier segment."""
    def ccw(A, B, C):
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])

    def intersect(p1, p2, p3, p4):
        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)

    for b in pellegrini_barriers:
        coords = b.get("geometry", {}).get("coordinates", [])
        for i in range(len(coords) - 1):
            if intersect(p1, p2, coords[i], coords[i + 1]):
                return True
    return False

# Reclassify: soft comps that cross Pellegrini become HARD (excluded)
same_side_hard = []
cross_soft_hard = []  # crosses OTHER soft barriers (not Pellegrini)
excluded_pellegrini = []  # crosses Pellegrini (now treated as hard)

for c in comps_all:
    crosses_pellegrini = check_pellegrini_crossing(
        (SUBJECT_LON, SUBJECT_LAT),
        (c["lon"], c["lat"]),
        pellegrini_features
    )
    # Also check if it crosses any OTHER barrier
    try:
        result = check_barrier_crossing(
            (SUBJECT_LON, SUBJECT_LAT),
            (c["lon"], c["lat"]),
            barreras
        )
    except Exception:
        result = False

    if crosses_pellegrini:
        excluded_pellegrini.append(c)
    elif result == 'hard':
        excluded_hard_item = c
        same_side_hard.append(c)  # hard barrier fallback: keep same as engine
    elif result == 'soft':
        cross_soft_hard.append(c)
    else:
        same_side_hard.append(c)

# The pool for "Pellegrini hard" simulation: same_side + cross_soft (other soft barriers)
# But exclude Pellegrini-crossing comps
pool_hard = same_side_hard + cross_soft_hard

print()
print("=" * 72)
print("PART B: SIMULACION (Pellegrini = dura, excluyente)")
print("=" * 72)
print("  Same-side (sin cruce): %d" % len(same_side_hard))
print("  Cross-soft (otras avs, no Pellegrini): %d" % len(cross_soft_hard))
print("  Excluded (Pellegrini, ahora dura): %d" % len(excluded_pellegrini))
print("  Pool final (same + cross-soft otras): %d" % len(pool_hard))

print()
print("-" * 72)
print("COMPARABLES EN POOL HARD (incluidos):")
print("-" * 72)
for c in sorted(pool_hard, key=lambda x: x["precio_m2"]):
    print("  {:5.0f}m | ${:8.0f}/m2 | ${:>10,.0f} | {:5.1f}m2 | {}d | {}".format(
        c["distancia_m"], c["precio_m2"], c["precio"], c["m2"],
        c["dormitorios"], c["direccion"][:45]))

print()
print("-" * 72)
print("COMPARABLES EXCLUIDOS por Pellegrini (ahora barrera dura):")
print("-" * 72)
for c in sorted(excluded_pellegrini, key=lambda x: x["precio_m2"]):
    print("  {:5.0f}m | ${:8.0f}/m2 | ${:>10,.0f} | {:5.1f}m2 | {}d | lat={:.5f} | {}".format(
        c["distancia_m"], c["precio_m2"], c["precio"], c["m2"],
        c["dormitorios"], c["lat"], c["direccion"][:40]))

# ============================================================
# Calculate valuations
# ============================================================
m2_equiv = subject["m2_cubiertos"]  # 98

def calc_median(prices):
    s = sorted(prices)
    n = len(s)
    if n % 2 == 1:
        return s[n // 2]
    return (s[n // 2 - 1] + s[n // 2]) / 2

def calc_percentil(prices, q):
    s = sorted(prices)
    n = len(s)
    idx = int(n * q / 100)
    idx = min(idx, n - 1)
    idx = max(idx, 0)
    return float(s[idx])

# --- Scenario 1: Current engine (Pellegrini soft) ---
pool_current = same_side_soft + cross_soft
precios_current = sorted([c["precio_m2"] for c in pool_current])
mediana_current = calc_median(precios_current)
p33_current = calc_percentil(precios_current, 33)
valor_current = m2_equiv * mediana_current

print()
print("=" * 72)
print("VALUACION - ESCENARIO 1: PELLEGRINI BLANDA (actual)")
print("=" * 72)
print("  Pool: %d comps (same + cross-soft)" % len(pool_current))
print("  Precios m2: %s" % ["$%s" % "{:,.0f}".format(p) for p in sorted(precios_current)])
print("  Mediana m2: $%s" % "{:,.2f}".format(mediana_current))
print("  P33 m2: $%s" % "{:,.2f}".format(p33_current))
print("  Valor (mediana x m2_equiv): $%s" % "{:,.0f}".format(valor_current))

# --- Scenario 2: Pellegrini hard (excluded) ---
if len(pool_hard) > 0:
    precios_hard = sorted([c["precio_m2"] for c in pool_hard])
    mediana_hard = calc_median(precios_hard)
    p33_hard = calc_percentil(precios_hard, 33)
    valor_hard = m2_equiv * mediana_hard
else:
    precios_hard = []
    mediana_hard = 0
    p33_hard = 0
    valor_hard = 0

print()
print("=" * 72)
print("VALUACION - ESCENARIO 2: PELLEGRINI DURA (excluyente)")
print("=" * 72)
if len(pool_hard) > 0:
    print("  Pool: %d comps (same + cross-soft otras avs)" % len(pool_hard))
    print("  Precios m2: %s" % ["$%s" % "{:,.0f}".format(p) for p in sorted(precios_hard)])
    print("  Mediana m2: $%s" % "{:,.2f}".format(mediana_hard))
    print("  P33 m2: $%s" % "{:,.2f}".format(p33_hard))
    print("  Valor (mediana x m2_equiv): $%s" % "{:,.0f}".format(valor_hard))
else:
    print("  Pool vacio - no se puede calcular")

# --- Scenario 3: Only same-side (strict exclusion) ---
if len(same_side_hard) > 0:
    precios_same = sorted([c["precio_m2"] for c in same_side_hard])
    mediana_same = calc_median(precios_same)
    valor_same = m2_equiv * mediana_same
else:
    precios_same = []
    mediana_same = 0
    valor_same = 0

print()
print("=" * 72)
print("VALUACION - ESCENARIO 3: SOLO SAME-SIDE (excluye todo cruce)")
print("=" * 72)
if len(same_side_hard) > 0:
    print("  Pool: %d comps (solo same-side, sin cruce de ninguna barrera)" % len(same_side_hard))
    print("  Precios m2: %s" % ["$%s" % "{:,.0f}".format(p) for p in sorted(precios_same)])
    print("  Mediana m2: $%s" % "{:,.2f}".format(mediana_same))
    print("  Valor (mediana x m2_equiv): $%s" % "{:,.0f}".format(valor_same))
else:
    print("  Pool vacio - no se puede calcular")

# ============================================================
# COMPARISON
# ============================================================
print()
print("=" * 72)
print("COMPARACION DE ESCENARIOS:")
print("=" * 72)
print()
print("%-45s %6s %10s %12s" % ("Escenario", "N", "m2_base", "Valor"))
print("%-45s %6s %10s %12s" % ("-" * 45, "-" * 6, "-" * 10, "-" * 12))
print("%-45s %6d %10s %12s" % ("Actual (Pellegrini blanda)", len(pool_current), "$%s" % "{:,.0f}".format(mediana_current), "$%s" % "{:,.0f}".format(valor_current)))
print("%-45s %6d %10s %12s" % ("Simulacion (Pellegrini dura)", len(pool_hard), "$%s" % "{:,.0f}".format(mediana_hard), "$%s" % "{:,.0f}".format(valor_hard)))
print("%-45s %6d %10s %12s" % ("Solo same-side (todo barrera excluido)", len(same_side_hard), "$%s" % "{:,.0f}".format(mediana_same), "$%s" % "{:,.0f}".format(valor_same)))
print()
if len(excluded_pellegrini) > 0:
    pct_excl = len(excluded_pellegrini) / len(comps_all) * 100
    print("Comps excluidos por Pellegrini dura: %d de %d (%.1f%%)" % (len(excluded_pellegrini), len(comps_all), pct_excl))

if valor_hard > 0 and valor_current > 0:
    diff_hard = ((valor_hard - valor_current) / valor_current) * 100
    diff_hard_abs = valor_hard - valor_current
    print()
    print("Diferencia Pellegrini dura vs blanda: $%s (%s%%)" % ("{:+,.0f}".format(diff_hard_abs), "{:+.1f}".format(diff_hard)))

if valor_same > 0 and valor_current > 0:
    diff_same = ((valor_same - valor_current) / valor_current) * 100
    diff_same_abs = valor_same - valor_current
    print("Diferencia same-side estricto vs blanda: $%s (%s%%)" % ("{:+,.0f}".format(diff_same_abs), "{:+.1f}".format(diff_same)))

# Reference to cached value
print()
print("REFERENCIA: Motor actual cacheado = $76,303 (m2_base=$778.60, 29 comps flex)")
if valor_hard > 0:
    diff_vs_cache = ((valor_hard - 76303) / 76303) * 100
    print("Pellegrini dura vs cache: $%s (%s%%)" % ("{:+,.0f}".format(valor_hard - 76303), "{:+.1f}".format(diff_vs_cache)))
