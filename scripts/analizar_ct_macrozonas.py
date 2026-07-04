"""
Analisis ML de Coeficiente de Tiempo (CT) por macrozona en Rosario.
Entrena RandomForest con feature 'meses' (tiempo desde 2021) para
detectar la tendencia temporal de precios por macrozona.

NO modifica archivos productivos. Solo genera reports/ml_ct_macrozonas.csv.

Uso: python scripts/analizar_ct_macrozonas.py
"""
import json, sys, os, csv
import numpy as np
import pandas as pd
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sklearn.ensemble import RandomForestRegressor
import warnings; warnings.filterwarnings("ignore")

print("=" * 90)
print("ANALISIS: CT (Coeficiente de Tiempo) por macrozona")
print("=" * 90)

# ─── CARGAR DATOS ───
with open("cache_scraping.json", encoding="utf-8") as f:
    cache = json.load(f)
props = cache["propiedades"]
print(f"\nTotal propiedades en cache: {len(props)}")

# ─── CARGAR MACROZONAS (desde zonas_depreciacion.json) ───
with open("data/zonas_depreciacion.json", encoding="utf-8") as f:
    zonas_cfg = json.load(f)
macrozonas = [m for m in zonas_cfg["macrozonas"] if m.get("bbox")]
print(f"Macrozonas con bbox: {[m['id'] for m in macrozonas]}")

# ─── PREPARAR DATASET ───
def get_month_since_2021(date_str):
    if not date_str:
        return None
    try:
        dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        return (dt.year - 2021) * 12 + (dt.month - 1)
    except:
        return None

AHORA = datetime.now()
rows = []
for p in props:
    if p.get("operacion") != "venta":
        continue
    try:
        lat, lon = p.get("lat"), p.get("lon")
        m2, vm2 = p.get("m2"), p.get("valor_m2")
        dorms = p.get("dormitorios")
        meses = get_month_since_2021(p.get("date_created"))
        if not all([lat, lon, m2, vm2, dorms is not None, meses is not None]):
            continue
        if vm2 < 200 or vm2 > 5000 or m2 < 15 or m2 > 500 or dorms < 0 or dorms > 10:
            continue
        tipo = (p.get("tipo") or "").lower().strip()
        casa = 1 if "casa" in tipo else 0

        # Asignar macrozona por bbox (orden: centro_premium tiene prioridad)
        macro = "resto_rosario"
        for m in macrozonas:
            b = m["bbox"]
            if b["lat_min"] <= lat <= b["lat_max"] and b["lon_min"] <= lon <= b["lon_max"]:
                macro = m["id"]
                break

        rows.append({
            "lat": float(lat), "lon": float(lon),
            "m2": float(m2), "dorms": int(dorms),
            "casa": casa,
            "meses": meses,
            "vm2": float(vm2),
            "date_created": str(p.get("date_created", ""))[:10],
            "macro": macro,
        })
    except:
        pass

df = pd.DataFrame(rows)
print(f"\nTotal ventas con date_created: {len(df)}")

# ─── ANALISIS POR MACROZONA ───
print("\n" + "=" * 90)
print("RESULTADOS POR MACROZONA")
print("=" * 90)

MES_ACTUAL = get_month_since_2021(AHORA.strftime("%Y-%m-%d"))
FEATURES = ["lat", "lon", "m2", "dorms", "casa", "meses"]
PROP_REF = {"m2": 50, "dorms": 1, "casa": 0}

resultados = []

for mz in macrozonas:
    mz_id = mz["id"]
    sub = df[df["macro"] == mz_id]
    n = len(sub)

    if n < 20:
        print(f"\n  {mz_id:<25} n={n:>5} -> SKIP (min 20)")
        resultados.append({"macrozona": mz_id, "n": n, "skip": True})
        continue

    X = sub[FEATURES].values
    y = np.log(sub["vm2"].values)

    rf = RandomForestRegressor(n_estimators=200, max_depth=12, n_jobs=-1, random_state=42)
    rf.fit(X, y)
    r2 = rf.score(X, y)

    importances = rf.feature_importances_
    imp_meses = importances[FEATURES.index("meses")]
    imp_meses_pct = imp_meses / sum(importances) * 100

    # Tasa anual implicita: simular propiedad de referencia en el centro del bbox
    b = mz["bbox"]
    lat_c = (b["lat_min"] + b["lat_max"]) / 2
    lon_c = (b["lon_min"] + b["lon_max"]) / 2

    # Predecir vm2 para propiedad de referencia en distintos momentos
    tasas = []
    for meses_offset in [6, 12, 18, 24, 30, 36]:
        meses_pasado = MES_ACTUAL - meses_offset
        if meses_pasado < 0:
            continue
        x_pred_pasado = np.array([[lat_c, lon_c, PROP_REF["m2"], PROP_REF["dorms"], PROP_REF["casa"], meses_pasado]])
        x_pred_hoy = np.array([[lat_c, lon_c, PROP_REF["m2"], PROP_REF["dorms"], PROP_REF["casa"], MES_ACTUAL]])
        pred_pasado = np.exp(rf.predict(x_pred_pasado)[0])
        pred_hoy = np.exp(rf.predict(x_pred_hoy)[0])
        if pred_pasado > 0:
            anos = meses_offset / 12
            tasa = (pred_hoy / pred_pasado) ** (1 / anos) - 1
            tasas.append(tasa)

    tasa_ct_anual = np.median(tasas) * 100 if tasas else 0.0
    tasa_min = min(tasas) * 100 if tasas else 0.0
    tasa_max = max(tasas) * 100 if tasas else 0.0

    # Estadisticas del pool
    vm2_med = sub["vm2"].median()
    cv_pool = sub["vm2"].std() / sub["vm2"].mean() if sub["vm2"].mean() > 0 else 0

    print(f"\n  {mz_id:<25} n={n:>5}  R2={r2:.3f}  imp_meses={imp_meses_pct:.1f}%")
    print(f"    Centro: ({lat_c:.4f}, {lon_c:.4f})")
    print(f"    vm2_med: ${vm2_med:>6,.0f}  CV_pool: {cv_pool:.3f}")
    print(f"    Tasa CT anual: {tasa_ct_anual:+.2f}%  (rango: {tasa_min:+.2f}% a {tasa_max:+.2f}%)")

    resultados.append({
        "macrozona": mz_id,
        "n": n,
        "r2": round(r2, 3),
        "imp_meses_pct": round(imp_meses_pct, 1),
        "vm2_med": round(vm2_med, 0),
        "cv_pool": round(cv_pool, 3),
        "tasa_ct_anual": round(tasa_ct_anual, 2),
        "tasa_min": round(tasa_min, 2),
        "tasa_max": round(tasa_max, 2),
        "skip": False,
    })

# ─── GUARDAR REPORTE ───
csv_path = "reports/ml_ct_macrozonas.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["macrozona", "n", "r2", "imp_meses_pct", "vm2_med", "cv_pool",
                "tasa_ct_anual", "tasa_min", "tasa_max"])
    for r in resultados:
        if r.get("skip"):
            continue
        w.writerow([r["macrozona"], r["n"], r["r2"], r["imp_meses_pct"],
                    r["vm2_med"], r["cv_pool"],
                    r["tasa_ct_anual"], r["tasa_min"], r["tasa_max"]])
print(f"\nReporte guardado: {csv_path}")

# ─── RESUMEN FINAL ───
print("\n" + "=" * 90)
print("RESUMEN CT POR MACROZONA")
print("=" * 90)
print(f"{'Macrozona':<22} {'n':>6} {'R2':>6} {'imp_meses':>10} {'vm2_med':>9} {'CV':>6} {'Tasa CT':>9}")
print("-" * 75)
for r in resultados:
    if r.get("skip"):
        print(f"{r['macrozona']:<22} {r['n']:>6} {'SKIP':>6}")
        continue
    print(f"{r['macrozona']:<22} {r['n']:>6} {r['r2']:>6.3f} {r['imp_meses_pct']:>9.1f}% ${r['vm2_med']:>6,.0f} {r['cv_pool']:>6.3f} {r['tasa_ct_anual']:>+7.2f}%")

# Tasa promedio ponderada por n
validos = [r for r in resultados if not r.get("skip")]
if validos:
    total_n = sum(r["n"] for r in validos)
    tasa_prom = sum(r["tasa_ct_anual"] * r["n"] for r in validos) / total_n if total_n > 0 else 0
    print("-" * 75)
    print(f"{'PONDERADO':<22} {total_n:>6} {'':>6} {'':>9} {'':>9} {'':>6} {tasa_prom:>+7.2f}%")

print("\n" + "=" * 90)
print("FIN ANALISIS CT")
print("=" * 90)
