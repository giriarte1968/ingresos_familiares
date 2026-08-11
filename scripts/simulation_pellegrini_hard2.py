"""
Simulacion refinada: Cochabamba 45 con Pellegrini como barrera DURA.
Aplica Ct (time adjustment) y usa P33 + blend como el motor real.
"""
import json, os, sys, math

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SUBJECT_LAT = -32.9611391
SUBJECT_LON = -60.6264443
RADIO_M = 800
FECHA_REF = "2026-08-03"

base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(base, "cache_scraping.json"), "r", encoding="utf-8") as f:
    scraping_data = json.load(f)

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1))*math.cos(math.radians(lat2))*math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

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

def calc_ct(months_since):
    """Simplified Ct curve based on engine logic."""
    if months_since <= 0:
        return 1.0
    if months_since <= 3:
        return 0.98
    if months_since <= 6:
        return 0.96
    if months_since <= 12:
        return 0.94
    if months_since <= 24:
        return 0.90
    if months_since <= 36:
        return 0.85
    return 0.80

def months_since_date(date_str, ref_str):
    """Calculate months between date and reference."""
    if not date_str:
        return None
    try:
        d = datetime.fromisoformat(date_str.replace("Z", "").split("T")[0])
        r = datetime.strptime(ref_str, "%Y-%m-%d")
        delta = (r - d).days
        return delta / 30.0
    except:
        return None

from datetime import datetime

# Load barriers
from parsers.location_engine import cargar_barreras, check_barrier_crossing
barreras = cargar_barreras()

# Find Pellegrini features
pellegrini_features = [b for b in barreras if "pellegrini" in str(b.get("properties", {}).get("name", "")).lower()]

def check_pellegrini_crossing(p1, p2, pfeats):
    def ccw(A, B, C):
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
    def intersect(p1, p2, p3, p4):
        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)
    for b in pfeats:
        coords = b.get("geometry", {}).get("coordinates", [])
        for i in range(len(coords) - 1):
            if intersect(p1, p2, coords[i], coords[i + 1]):
                return True
    return False

# Get all 4-dorm venta within 800m
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

    # Time adjustment
    months = months_since_date(entry.get("date_created", ""), FECHA_REF)
    ct = calc_ct(months) if months is not None else 1.0
    precio_m2_ajustado = precio_m2 * ct

    comps_all.append({
        "direccion": entry.get("direccion", entry.get("direccion_limpia", "?")),
        "lat": lat, "lon": lon,
        "dormitorios": int(dorms),
        "precio": precio, "m2": m2,
        "precio_m2": round(precio_m2, 2),
        "precio_m2_ajustado": round(precio_m2_ajustado, 2),
        "distancia_m": round(dist_m, 0),
        "date_created": entry.get("date_created", ""),
        "ct": round(ct, 4),
        "months": round(months, 1) if months else None,
    })

print("=" * 72)
print("SIMULACION REFINADA: PELLEGRINI BARRERA DURA")
print("Aplica Ct + P33 + blend alpha (como motor real)")
print("=" * 72)
print("Total 4-dorm venta en 800m: %d" % len(comps_all))

# Classify: same-side vs crosses-Pellegrini
same_side = []
cross_pellegrini = []

for c in comps_all:
    try:
        crosses = check_pellegrini_crossing(
            (SUBJECT_LON, SUBJECT_LAT), (c["lon"], c["lat"]), pellegrini_features
        )
    except:
        crosses = False
    if crosses:
        cross_pellegrini.append(c)
    else:
        same_side.append(c)

print("Same-side (no cruza Pellegrini): %d" % len(same_side))
print("Cross-Pellegrini (excluidos si dura): %d" % len(cross_pellegrini))

# Pool = same_side only (Pellegrini hard)
pool = same_side
precios = sorted([c["precio_m2_ajustado"] for c in pool])
n = len(precios)

print()
print("-" * 72)
print("POOL SAME-SIDE (Pellegrini dura, con Ct aplicado):")
print("-" * 72)
for c in sorted(pool, key=lambda x: x["precio_m2_ajustado"]):
    print("  {:5.0f}m | ${:7.0f}/m2(adj) | ${:>10,.0f} | {:5.1f}m2 | {}d | ct={:.3f} | {}".format(
        c["distancia_m"], c["precio_m2_ajustado"], c["precio"], c["m2"],
        c["dormitorios"], c["ct"], c["direccion"][:40]))

if n == 0:
    print("SIN COMPARABLES")
    sys.exit(0)

mediana = calc_median(precios)
p33 = calc_percentil(precios, 33)
p25 = calc_percentil(precios, 25)
p75 = calc_percentil(precios, 75)

m2_equiv = 98.0
valor_mediana = m2_equiv * mediana
valor_p33 = m2_equiv * p33

print()
print("-" * 72)
print("ESTADISTICAS (post-Ct, same-side only):")
print("-" * 72)
print("  N = %d" % n)
print("  Precios m2 ajustados: %s" % ["${:,.0f}".format(p) for p in precios])
print("  P25  = ${:,.2f}".format(p25))
print("  P33  = ${:,.2f}".format(p33))
print("  Med  = ${:,.2f}".format(mediana))
print("  P75  = ${:,.2f}".format(p75))

print()
print("-" * 72)
print("VALUACION (Pellegrini dura):")
print("-" * 72)
print("  m2_equiv   = %.1f" % m2_equiv)
print("  m2_base(P33)= ${:,.2f}".format(p33))
print("  m2_base(Med)= ${:,.2f}".format(mediana))
print("  Valor(P33)  = ${:,.0f}".format(valor_p33))
print("  Valor(Med)  = ${:,.0f}".format(valor_mediana))

# Also compute what the engine gives with all 26 comps (Pellegrini soft)
pool_all = comps_all  # all are in the pool when Pellegrini is soft
precios_all = sorted([c["precio_m2_ajustado"] for c in pool_all])
n_all = len(precios_all)
mediana_all = calc_median(precios_all)
p33_all = calc_percentil(precios_all, 33)

valor_p33_all = m2_equiv * p33_all
valor_med_all = m2_equiv * mediana_all

print()
print("-" * 72)
print("VALUACION (Pellegrini blanda - referencia):")
print("-" * 72)
print("  Pool: %d comps (all 4-dorm in 800m)" % n_all)
print("  P33  = ${:,.2f}".format(p33_all))
print("  Med  = ${:,.2f}".format(mediana_all))
print("  Valor(P33) = ${:,.0f}".format(valor_p33_all))
print("  Valor(Med) = ${:,.0f}".format(valor_med_all))

# Excluded comps analysis
print()
print("-" * 72)
print("COMPARABLES EXCLUIDOS POR PELLEGRINI DURA:")
print("-" * 72)
if cross_pellegrini:
    excl_prices = sorted([c["precio_m2_ajustado"] for c in cross_pellegrini])
    excl_med = calc_median(excl_prices)
    excl_mean = sum(excl_prices) / len(excl_prices)
    print("  N excluded = %d" % len(cross_pellegrini))
    print("  Precios: %s" % ["${:,.0f}".format(p) for p in excl_prices])
    print("  Mediana excluidos: ${:,.2f}".format(excl_med))
    print("  Promedio excluidos: ${:,.2f}".format(excl_mean))
    print("  Promedio same-side: ${:,.2f}".format(sum(precios)/len(precios)))
    if excl_med > mediana:
        print("  -> Los excluidos eran MAS CAROS que el pool same-side")
        print("     Exclusion REDUCE la valuacion")
    else:
        print("  -> Los excluidos eran MAS BARATOS que el pool same-side")
        print("     Exclusion INCREMENTA la valuacion")

# Final comparison
print()
print("=" * 72)
print("COMPARACION FINAL:")
print("=" * 72)
print("%-40s %6s %10s %12s" % ("Escenario", "N", "P33/m2", "Valor(P33)"))
print("%-40s %6s %10s %12s" % ("-" * 40, "-" * 6, "-" * 10, "-" * 12))
print("%-40s %6d %10s %12s" % ("Pellegrini blanda (all)", n_all, "${:,.0f}".format(p33_all), "${:,.0f}".format(valor_p33_all)))
print("%-40s %6d %10s %12s" % ("Pellegrini dura (same-side)", n, "${:,.0f}".format(p33), "${:,.0f}".format(valor_p33)))
print()
print("Cache del motor: $76,303 (m2_base=$778.60)")
print()
diff_vs_soft = ((valor_p33 - valor_p33_all) / valor_p33_all) * 100
print("Dif Pellegrini dura vs blanda: ${:+,.0f} ({:+.1f}%)".format(valor_p33 - valor_p33_all, diff_vs_soft))
diff_vs_cache = ((valor_p33 - 76303) / 76303) * 100
print("Dif Pellegrini dura vs cache: ${:+,.0f} ({:+.1f}%)".format(valor_p33 - 76303, diff_vs_cache))
