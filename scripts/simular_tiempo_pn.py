"""
SIMULACION - Ajuste temporal PN con 3 estrategias.
NO modifica nada productivo. Solo genera reporte en pantalla.

Uso: python scripts/simular_tiempo_pn.py
"""
import json, os, sys, warnings
import numpy as np
import pandas as pd
from datetime import datetime
from collections import defaultdict
from statistics import median
from sklearn.ensemble import RandomForestRegressor
warnings.filterwarnings("ignore")

BASE = r"C:\Users\Gustavo\ingresos_familiares_st"
os.chdir(BASE)

# ============================================================
# PASO 1: Cargar datos
# ============================================================
print("=" * 90)
print("SIMULACION: Ajuste temporal PN con date_created")
print("=" * 90)

with open("cache_scraping.json", encoding="utf-8") as f:
    cache = json.load(f)
props = cache["propiedades"]

# Sujeto de prueba
SUJETO = {
    "nombre": "Francia 250b",
    "zona": "Puerto Norte",
    "m2": 160.0,
    "dormitorios": 3,
    "operacion": "venta",
    "lat": -32.9304,
    "lon": -60.6621,
    "anio_construccion": 2025,
}
FECHA_REF = "2026-06-06"
fecha_ref_dt = datetime.strptime(FECHA_REF, "%Y-%m-%d")

print(f"\nSujeto: {SUJETO['nombre']} | {SUJETO['m2']}m2 | {SUJETO['dormitorios']} dorm | {SUJETO['zona']}")
print(f"Fecha ref: {FECHA_REF}")

# ============================================================
# PASO 2: Preparar datos para entrenamiento
# ============================================================
print("\n--- Preparando datos de entrenamiento ---")

def get_month_since_2021(date_str):
    """Convierte YYYY-MM-DD a meses desde 2021-01."""
    if not date_str:
        return None
    try:
        dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        return (dt.year - 2021) * 12 + (dt.month - 1)
    except:
        return None

def get_valor_m2(p):
    vm2 = p.get("valor_m2", 0)
    if isinstance(vm2, (int, float)) and 0 < vm2 < 10000:
        return vm2
    return None

rows = []
for p in props:
    if p.get("operacion") != "venta":
        continue
    lat, lon = p.get("lat"), p.get("lon")
    m2 = p.get("m2")
    vm2 = get_valor_m2(p)
    dorms = p.get("dormitorios")
    meses = get_month_since_2021(p.get("date_created"))
    if not all([lat, lon, m2, vm2, dorms is not None, meses is not None]):
        continue
    if m2 < 15 or m2 > 500 or dorms < 0 or dorms > 10:
        continue
    tipo = (p.get("tipo") or "").lower().strip()
    casa = 1 if "casa" in tipo else 0
    rows.append({
        "lat": float(lat), "lon": float(lon),
        "m2": float(m2), "dorms": int(dorms),
        "casa": casa,
        "meses": meses,
        "vm2": float(vm2),
        "zona": p.get("zona", ""),
        "date_created": str(p.get("date_created", ""))[:10],
    })

df = pd.DataFrame(rows)
print(f"Total ventas con datos completos: {len(df)}")

# Quick stat
df["log_vm2"] = np.log(df["vm2"])
print(f"  Rango vm2: ${df['vm2'].min():.0f} - ${df['vm2'].max():.0f}")
print(f"  Rango meses: {df['meses'].min()} - {df['meses'].max()}")

# PN subset
df_pn = df[df["zona"].str.lower().str.contains("puerto norte", na=False)]
print(f"  PN ventas: {len(df_pn)}")
print(f"  PN ventas 3 dorm: {len(df_pn[df_pn['dorms'] == 3])}")

FEATURES = ["lat", "lon", "m2", "dorms", "casa", "meses"]
X = df[FEATURES].values
y = df["log_vm2"].values

# ============================================================
# PASO 3: Entrenar Random Forest
# ============================================================
print("\n--- Entrenando Random Forest ---")
rf = RandomForestRegressor(n_estimators=200, max_depth=12, n_jobs=-1, random_state=42, verbose=0)
rf.fit(X, y)
r2 = rf.score(X, y)
print(f"R² en entrenamiento: {r2:.3f}")

# Feature importance
importances = rf.feature_importances_
for name, imp in zip(FEATURES, importances):
    print(f"  {name}: {imp:.3f} ({imp/sum(importances)*100:.1f}%)")

# ============================================================
# PASO 4: Buscar comparables PN con lógica de tiers
# ============================================================
print("\n--- Buscando comparables PN ---")

def get_year(date_str):
    try:
        return int(str(date_str)[:4])
    except:
        return None

# Todos los PN venta, sin filtrar por dorms inicialmente
pn_comps = df[df["zona"].str.lower().str.contains("puerto norte", na=False)].copy()

# Simular tiers de fecha como en obtener_mediana_cluster
TIERS_DIAS = [365, 545, 730, 9999]
MIN_PN = [10, 8, 5, 5]  # propuesto

comps_tier = None
tier_usado = None
for dias, min_comp in zip(TIERS_DIAS, MIN_PN):
    filtro = pn_comps[pn_comps["dorms"] == SUJETO["dormitorios"]].copy()
    # Filtrar por fecha
    fecha_limite = fecha_ref_dt - pd.Timedelta(days=dias)
    filtro["dt"] = pd.to_datetime(filtro["date_created"], errors="coerce")
    filtro = filtro[filtro["dt"] >= fecha_limite].copy()
    
    if len(filtro) >= min_comp:
        # Marcar que encontramos suficientes
        # Pero seguimos hasta 9999 si hay mas
        if dias == TIERS_DIAS[-1] or len(filtro) >= min_comp:
            comps_tier = filtro
            tier_usado = dias
            print(f"  Tier {dias:5d}d: {len(filtro)} comps (min {min_comp}) -> OK")
            break
    print(f"  Tier {dias:5d}d: {len(filtro)} comps (min {min_comp}) -> insuficiente")

if comps_tier is None and len(pn_comps[pn_comps["dorms"] == SUJETO["dormitorios"]]) >= 2:
    comps_tier = pn_comps[pn_comps["dorms"] == SUJETO["dormitorios"]].copy()
    tier_usado = "fallback"
    print(f"  Fallback (sin fecha): {len(comps_tier)} comps")

if comps_tier is None:
    print("  SIN COMPARABLES. Usando ancla.")
    exit()

print(f"\n  Tier usado: {tier_usado} | Comparables: {len(comps_tier)}")
for _, c in comps_tier.iterrows():
    anios = max(0, (fecha_ref_dt - c["dt"]).days / 365.25) if hasattr(c, 'dt') and ('dt' in comps_tier.columns and pd.notna(c['dt'])) else 0
    print(f"    {c['date_created'][:10]} | ${c['vm2']:>7.0f}/m2 | {c['m2']:>5.0f}m2 | {c['dorms']}dorm | {anios:.2f} anos")

# ============================================================
# PASO 5: Calcular 3 estrategias
# ============================================================
print("\n" + "=" * 90)
print("RESULTADOS POR ESTRATEGIA")
print("=" * 90)

# Para cada comparable, calcular factores
mes_actual = get_month_since_2021(FECHA_REF)

resultados = []
for _, c in comps_tier.iterrows():
    raw_vm2 = c["vm2"]
    anios = max(0, (fecha_ref_dt - c["dt"]).days / 365.25) if ('dt' in comps_tier.columns and pd.notna(c['dt'])) else 0
    
    # Estrategia A: sin ajuste
    fac_a = 1.0
    ajus_a = raw_vm2 * fac_a
    
    # Estrategia B: depreciacion actual (-4.5%/anual)
    fac_b = 1 + (-0.045) * anios
    ajus_b = raw_vm2 * fac_b
    
    # Estrategia C: ML con date_created
    meses_c = get_month_since_2021(c["date_created"])
    if meses_c is not None and mes_actual is not None:
        x_pred_meses = np.array([[c["lat"], c["lon"], c["m2"], c["dorms"], c["casa"], meses_c]])
        x_pred_actual = np.array([[c["lat"], c["lon"], c["m2"], c["dorms"], c["casa"], mes_actual]])
        pred_orig = np.exp(rf.predict(x_pred_meses)[0])
        pred_act = np.exp(rf.predict(x_pred_actual)[0])
        fac_c = pred_act / pred_orig if pred_orig > 0 else 1.0
    else:
        fac_c = 1.0
    ajus_c = raw_vm2 * fac_c
    
    resultados.append({
        "direccion": str(c.get("zona", "")),
        "fecha": c["date_created"],
        "anos": round(anios, 2),
        "raw_vm2": round(raw_vm2, 0),
        "fac_a": round(fac_a, 4),
        "fac_b": round(fac_b, 4),
        "fac_c": round(fac_c, 4),
        "ajus_a": round(ajus_a, 0),
        "ajus_b": round(ajus_b, 0),
        "ajus_c": round(ajus_c, 0),
    })

# Tabla
print(f"\n{'#':>2} | {'Comparable':<40} | {'Año':<10} | {'RAW':>6} | {'FAC A':>6} | {'FAC B':>6} | {'FAC C':>6} | {'AJ A':>7} | {'AJ B':>7} | {'AJ C':>7}")
print("-" * 110)
for i, r in enumerate(resultados, 1):
    print(f"{i:>2} | {r['direccion']:<40} | {r['fecha'][:10]:<10} | ${r['raw_vm2']:>5,.0f} | {r['fac_a']:>6.3f} | {r['fac_b']:>6.3f} | {r['fac_c']:>6.3f} | ${r['ajus_a']:>6,.0f} | ${r['ajus_b']:>6,.0f} | ${r['ajus_c']:>6,.0f}")

# P33 por estrategia (simplificado: percentil de los precios ordenados)
def calc_p33(vals):
    if not vals:
        return 0
    s = sorted(vals)
    idx = max(0, int(len(s) * 0.33))
    return s[idx]

p33_a = calc_p33([r["ajus_a"] for r in resultados])
p33_b = calc_p33([r["ajus_b"] for r in resultados])
p33_c = calc_p33([r["ajus_c"] for r in resultados])
ancla = 2800

print("\n" + "-" * 50)
print("P33 FINAL POR ESTRATEGIA:")
print(f"  A (sin ajuste):         ${p33_a:>7,.0f}/m2")
print(f"  B (deprec -4.5%/anual): ${p33_b:>7,.0f}/m2")
print(f"  C (ML trend):           ${p33_c:>7,.0f}/m2")
print(f"  Ancla actual:           ${ancla:>7,.0f}/m2")
print(f"\n  Tier usado: {tier_usado} | Comparables: {len(resultados)}")

# Para C, calcular la tasa implicita promedio
tasas_c = []
for r in resultados:
    if r["anos"] > 0.5:
        tasa = (r["ajus_c"] / r["raw_vm2"]) ** (1 / r["anos"]) - 1
        tasas_c.append(tasa)
if tasas_c:
    tasa_prom_c = np.median(tasas_c) * 100  # en %
    print(f"\n  Tasa implicita promedio (estrategia C): {tasa_prom_c:+.2f}%/anual")
    print(f"  Rango tasas: {min(tasas_c)*100:+.2f}% a {max(tasas_c)*100:+.2f}%")

print("\n" + "=" * 90)
print("FIN SIMULACION")
print("=" * 90)
