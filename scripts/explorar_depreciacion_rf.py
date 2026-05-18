"""
Exploracion de senal RF de depreciacion por macrozona en Rosario.
NO modifica archivos productivos. Solo genera reportes en reports/ y data/experimental/.
"""
import json, sys, os, csv
import numpy as np
import pandas as pd
from datetime import datetime
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sklearn.ensemble import RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LinearRegression
import warnings; warnings.filterwarnings("ignore")

# ─── CARGAR DATOS ───
print("=" * 80)
print("EXPLORACION: Senal RF de depreciacion por macrozona")
print("=" * 80)

with open("cache_scraping.json", encoding="utf-8") as f:
    cache = json.load(f)
props = cache["propiedades"]

avm = pd.read_csv("data/rosario_avm_full.csv", encoding="utf-8")
avm_y = avm[avm["year"].notna()].copy()
tree = cKDTree(avm_y[["latitud", "longitud"]].values)

# ─── CARGAR MACROZONAS ───
with open("data/experimental/macrozonas_rf_exploracion.json") as f:
    macro_config = json.load(f)
macrozonas = macro_config["macrozonas"]
print(f"\nMacrozonas definidas: {[m['id'] for m in macrozonas]}")

# ─── PREPARAR DATASET ───
AHORA = datetime.now()
rows = []
for p in props:
    if p.get("operacion") != "venta": continue
    try:
        lat, lon = p.get("lat"), p.get("lon")
        m2, vm2 = p.get("m2"), p.get("valor_m2")
        dorms = p.get("dormitorios")
        if not all([lat, lon, m2, vm2, dorms is not None]): continue
        if vm2 < 200 or vm2 > 5000 or m2 < 15 or m2 > 500 or dorms < 0 or dorms > 10: continue
        fs = p.get("date_updated") or p.get("fecha_publicacion")
        dias = (AHORA - datetime.fromisoformat(fs.replace("Z",""))).days if fs else 180
        tipo = (p.get("tipo") or "").lower().strip()
        d, idx = tree.query([float(lat), float(lon)])
        anio = int(avm_y.iloc[idx]["year"]) if d * 111000 < 50 else None
        if anio is None: continue
        # Asignar macrozona
        macro = "resto"
        for m in macrozonas:
            b = m["bbox"]
            if b["lat_min"] <= lat <= b["lat_max"] and b["lon_min"] <= lon <= b["lon_max"]:
                macro = m["id"]
                break
        rows.append({
            "lat": float(lat), "lon": float(lon), "m2": float(m2),
            "vm2": float(vm2), "dorms": int(dorms), "dias": min(dias, 730),
            "casa": 1 if "casa" in tipo else 0,
            "anio": anio, "anti": 2026 - anio,
            "macro": macro,
        })
    except: pass

df = pd.DataFrame(rows)
print(f"\nTotal ventas con ano: {len(df)}")

# Contar por macrozona
for m in macrozonas:
    cnt = len(df[df["macro"] == m["id"]])
    m["n_props_estimado"] = cnt
    print(f"  {m['id']:<25} {cnt:>6} props")

resto = len(df[df["macro"] == "resto"])
print(f"  {'resto':<25} {resto:>6} props")

# ─── FASE B: RF POR MACROZONA ───
print("\n" + "=" * 80)
print("FASE B: RF por macrozona")
print("=" * 80)

resultados_mz = []
prop_ref = {"m2": 50, "dorms": 1, "casa": 0, "dias": 60}
ANIOS_SIMULACION = [1920, 1950, 1970, 1980, 1990, 2000, 2010, 2020, 2025]

for m in macrozonas:
    sub = df[df["macro"] == m["id"]]
    if len(sub) < 20:
        print(f"\n  {m['id']}: solo {len(sub)} props (min 20) -> SKIP")
        resultados_mz.append({"id": m["id"], "n": len(sub), "skip": True})
        continue

    # Coordenada representativa (centro del bbox)
    b = m["bbox"]
    lat_c = (b["lat_min"] + b["lat_max"]) / 2
    lon_c = (b["lon_min"] + b["lon_max"]) / 2

    X = sub[["lat", "lon", "m2", "dorms", "anti", "casa"]].values
    y = sub["vm2"].values

    rf = RandomForestRegressor(n_estimators=200, max_depth=12, n_jobs=-1, random_state=42)
    rf.fit(X, y)
    r2 = rf.score(X, y)

    # Feature importance
    imp = permutation_importance(rf, X, y, n_repeats=3, random_state=42)
    names = ["lat", "lon", "m2", "dorms", "anti", "casa"]
    imp_dict = {names[i]: imp.importances_mean[i] for i in range(len(names))}
    imp_anti = imp_dict["anti"] / sum(imp.importances_mean) * 100

    # Simulacion controlada: variar solo la edad
    vals_por_anio = []
    for anio_sim in ANIOS_SIMULACION:
        anti_sim = 2026 - anio_sim
        x_pred = np.array([[lat_c, lon_c, prop_ref["m2"], prop_ref["dorms"], anti_sim, prop_ref["casa"]]])
        vm2_pred = rf.predict(x_pred)[0]
        vals_por_anio.append(vm2_pred)

    vals = np.array(vals_por_anio)
    factor_base = vals[-1]  # 2025
    factores = vals / factor_base if factor_base > 0 else np.ones_like(vals)

    # Regresion lineal: log(vm2) ~ anti para estimar pendiente
    X_lr = sub[["anti", "m2", "dorms"]].values
    y_lr = np.log(sub["vm2"].clip(1))
    lr = LinearRegression(); lr.fit(X_lr, y_lr)
    pendiente_anual = (np.exp(lr.coef_[0]) - 1) * 100

    # Clasificar
    if abs(pendiente_anual) <= 0.25:
        clase = "baja"
    elif abs(pendiente_anual) <= 0.45:
        clase = "media"
    else:
        clase = "alta"

    # Factor anti actual del motor para la edad promedio de la macrozona
    edad_prom = sub["anti"].median()
    tasa_motor = 0.006
    delta_motor = max(-0.60, -(edad_prom * tasa_motor))
    U = -0.18; F = 0.35
    delta_motor_ef = U + (delta_motor - U) * F if delta_motor < U else delta_motor
    factor_motor = max(0.40, 1.0 + delta_motor_ef)

    print(f"\n  {m['id']:<25} n={len(sub):>5}  R2={r2:.3f}")
    print(f"    Centro: ({lat_c:.4f}, {lon_c:.4f})")
    print(f"    Feature anti: {imp_anti:.1f}%  (lat={imp_dict['lat']:.3f} lon={imp_dict['lon']:.3f})")
    print(f"    Pendiente RF: {pendiente_anual:+.2f}%/ano  -> clase: {clase}")
    print(f"    Edad media: {edad_prom:.0f} anos  |  factor motor actual: {factor_motor:.4f}")
    print(f"    Simulacion (depto {prop_ref['m2']}m2, {prop_ref['dorms']}dorm):")
    print(f"      {'Ano':>6}  {'USD/m2':>8}  {'Factor vs 2025':>16}")
    for anio_sim, v, fac in zip(ANIOS_SIMULACION, vals, factores):
        print(f"      {anio_sim:>6}  ${v:>6,.0f}  {fac:>10.3f}  ({'+' if fac>1 else ''}{fac-1:.1%})")

    resultados_mz.append({
        "id": m["id"],
        "n": len(sub),
        "r2": r2,
        "imp_anti_pct": imp_anti,
        "imp_lat": imp_dict["lat"],
        "imp_lon": imp_dict["lon"],
        "pendiente_anual": pendiente_anual,
        "clase": clase,
        "edad_prom": edad_prom,
        "factor_motor": factor_motor,
        "lat_c": lat_c,
        "lon_c": lon_c,
    })

# ─── FASE C: GRID EXPERIMENTAL ───
print("\n" + "=" * 80)
print("FASE C: Grid experimental 40x40")
print("=" * 80)

# Reentrenar RF global
df_all = df.copy()
X_all = df_all[["lat", "lon", "m2", "dorms", "anti", "casa"]].values
y_all = df_all["vm2"].values
rf_global = RandomForestRegressor(n_estimators=200, max_depth=12, n_jobs=-1, random_state=42)
rf_global.fit(X_all, y_all)

# Grid 40x40
lats = np.linspace(-33.03, -32.90, 40)
lons = np.linspace(-60.72, -60.59, 40)
grid_rows = []

print("  Generando grid 40x40...")
for i, lat in enumerate(lats):
    for j, lon in enumerate(lons):
        # Propiedad nueva (2025)
        x_new = np.array([[lat, lon, 50, 1, 1, 0]])
        vm2_new = rf_global.predict(x_new)[0]
        # Propiedad vieja (1970)
        x_old = np.array([[lat, lon, 50, 1, 56, 0]])
        vm2_old = rf_global.predict(x_old)[0]
        # Pendiente implicita
        if vm2_new > 0:
            pendiente = ((vm2_old / vm2_new) ** (1/55) - 1) * -100
        else:
            pendiente = 0
        # Asignar macrozona
        macro_punto = "resto"
        for m in macrozonas:
            b = m["bbox"]
            if b["lat_min"] <= lat <= b["lat_max"] and b["lon_min"] <= lon <= b["lon_max"]:
                macro_punto = m["id"]
                break
        grid_rows.append({
            "lat": round(lat, 4), "lon": round(lon, 4),
            "vm2_2025": round(vm2_new, 0),
            "vm2_1970": round(vm2_old, 0),
            "pendiente_pct": round(pendiente, 3),
            "macrozona": macro_punto,
        })
    if (i+1) % 10 == 0:
        print(f"    Fila {i+1}/40")

grid_df = pd.DataFrame(grid_rows)
grid_df.to_csv("reports/rf_depreciacion_grid.csv", index=False)
print(f"  Grid guardado: reports/rf_depreciacion_grid.csv ({len(grid_df)} puntos)")

# ─── FASE D: COMPARACION CON CURVA ACTUAL ───
print("\n" + "=" * 80)
print("FASE D: Comparacion con curva actual del motor")
print("=" * 80)

print(f"\n{'Macrozona':<25} {'n':>5} {'R2':>5} {'Imp_anti':>9} {'Pend.RF':>9} {'Clase':>8} {'Edad':>5} {'Fac.motor':>10} {'Fac.RF':>10}")
print("-" * 95)
for r in resultados_mz:
    if r.get("skip"): continue
    # Factor RF simulado para la edad promedio
    anti_prom = r["edad_prom"]
    tasa_rf_abs = abs(r["pendiente_anual"]) / 100
    delta_rf = max(-0.60, -(anti_prom * tasa_rf_abs))
    U = -0.18; F = 0.35
    delta_rf_ef = U + (delta_rf - U) * F if delta_rf < U else delta_rf
    factor_rf = max(0.40, 1.0 + delta_rf_ef)

    print(f"{r['id']:<25} {r['n']:>5} {r['r2']:>5.2f} {r['imp_anti_pct']:>8.1f}% {r['pendiente_anual']:>+8.2f}% {r['clase']:>8} {r['edad_prom']:>5.0f} {r['factor_motor']:>10.4f} {factor_rf:>10.4f}")

# Guardar reporte macrozonas
csv_path = "reports/rf_depreciacion_macrozonas.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["macrozona", "n_props", "r2", "imp_anti_pct", "imp_lat", "imp_lon",
                "pendiente_rf", "clase", "edad_prom", "factor_motor", "factor_rf"])
    for r in resultados_mz:
        if r.get("skip"): continue
        w.writerow([r["id"], r["n"], round(r["r2"],3), round(r["imp_anti_pct"],1),
                    round(r["imp_lat"],3), round(r["imp_lon"],3),
                    round(r["pendiente_anual"],3), r["clase"],
                    round(r["edad_prom"],0), round(r["factor_motor"],4),
                    round(factor_rf,4)])
print(f"\nReporte guardado: {csv_path}")
print()

# ─── FASE E: VALIDACION CONTRA ANCLAS ───
print("=" * 80)
print("FASE E: Validacion contra propiedades ancla")
print("=" * 80)
from parsers.mercado_inmobiliario import valuar_propiedad_v7, calcular_factores
from tests.test_regression import ejecutar_valuacion

ANCLAS = {"Mabel": ejecutar_valuacion("mabel"), "Ayacucho": ejecutar_valuacion("ayacucho")}
with open("propiedades.json", encoding="utf-8") as f:
    for p in json.load(f)["propiedades"]:
        n = p.get("nombre","")
        if "Vera" in n: ANCLAS["Vera Mujica"] = p
        if "P1200" in n: ANCLAS["P1200"] = p
        if "Amenabar" in n: ANCLAS["Amenabar"] = p

print(f"\n{'Ancla':<15} {'Macrozona':<20} {'Edad':>5} {'Anti_motor':>11} {'Anti_RFprop':>12} {'Val.actual':>10} {'Val.RF':>10} {'Dif%':>7}")
print("-" * 95)
for nombre, prop in ANCLAS.items():
    if nombre == "Amenabar": continue
    lat = prop.get("lat", -32.95); lon = prop.get("lon", -60.63)
    anio_prop = prop.get("anio_construccion", 2000) or 2000
    anti_prop = 2026 - int(anio_prop)
    res = valuar_propiedad_v7(prop, fecha_ref="2026-04")
    val_act = res.get("valor_propiedad_usd", 0)
    fd = calcular_factores(prop)
    anti_act = fd.get("depreciacion", 1.0)
    sc = fd.get("suma_cruda", 0)
    ft_act = fd.get("total", 1.0)

    # Asignar macrozona
    macro_asignada = "resto"
    for m in macrozonas:
        b = m["bbox"]
        if b["lat_min"] <= lat <= b["lat_max"] and b["lon_min"] <= lon <= b["lon_max"]:
            macro_asignada = m["id"]
            break

    # Buscar tasa RF para esta macrozona
    tasa_rf = 0.006
    for r in resultados_mz:
        if r.get("skip"): continue
        if r["id"] == macro_asignada:
            tasa_rf = abs(r["pendiente_anual"]) / 100
            break

    # Calcular factor anti con tasa RF
    delta_rf = max(-0.60, -(anti_prop * tasa_rf))
    U = -0.18; F = 0.35
    delta_rf_ef = U + (delta_rf - U) * F if delta_rf < U else delta_rf
    anti_rf = max(0.40, 1.0 + delta_rf_ef)

    # Recalcular valor con factor RF
    da = anti_act - 1.0; dn = anti_rf - 1.0
    base = 1 + sc + da
    if base > 0:
        nlp = (ft_act ** 2) / base
        base2 = 1 + sc + dn
        if base2 > 0:
            ft_rf = (base2 * nlp) ** 0.5
            ratio = ft_rf / ft_act if ft_act > 0 else 1.0
            val_rf = round(val_act * ratio, 0)
            dif_pct = (val_rf / val_act - 1) * 100
        else:
            val_rf, dif_pct = val_act, 0.0
    else:
        val_rf, dif_pct = val_act, 0.0

    print(f"{nombre:<15} {macro_asignada:<20} {anti_prop:>5} {anti_act:>11.4f} {anti_rf:>12.4f} ${val_act:>8,.0f} ${val_rf:>8,.0f} {dif_pct:>+6.2f}%")

print()

# ─── CONCLUSION ───
print("=" * 80)
print("CONCLUSION")
print("=" * 80)

# Analizar resultados
bajas = [r for r in resultados_mz if not r.get("skip") and r["clase"] == "baja"]
medias = [r for r in resultados_mz if not r.get("skip") and r["clase"] == "media"]
altas = [r for r in resultados_mz if not r.get("skip") and r["clase"] == "alta"]

print(f"""
  Resumen por macrozona:
    Baja depreciacion (<=0.25%/ano): {[r['id'] for r in bajas]}
    Media depreciacion (0.25-0.45%): {[r['id'] for r in medias]}
    Alta depreciacion (>=0.45%/ano):  {[r['id'] for r in altas]}
""")

print("  Preguntas:")
print(f"  a) Senal estable por macrozona?")

estabilidad = all(r.get("imp_anti_pct", 0) > 5 for r in resultados_mz if not r.get("skip"))
print(f"     {'SI' if estabilidad else 'NO'}: La importancia de anti es {'>5% en todas' if estabilidad else 'baja en algunas'} las macrozonas")

print(f"  b) Suficientemente fuerte para produccion?")
fuerte = any(r["clase"] != "baja" for r in resultados_mz if not r.get("skip"))
print(f"     {'SI' if fuerte else 'NO'}: {'Hay macrozonas con senal media/alta' if fuerte else 'Todas son baja'}")

print(f"  c) Macrozonas que justifican revision:")
for r in resultados_mz:
    if r.get("skip"): continue
    if r["clase"] != "baja":
        print(f"     - {r['id']}: pendiente {r['pendiente_anual']:+.2f}%/ano ({r['clase']})")

print(f"  d) Macrozonas que NO justifican tocar:")
for r in resultados_mz:
    if r.get("skip"): continue
    if r["clase"] == "baja":
        print(f"     - {r['id']}: pendiente {r['pendiente_anual']:+.2f}%/ano (baja)")

# Recomendacion final
print(f"""
  e) Recomendacion:
""")

if not resultados_mz:
    print("     Sin datos suficientes. No se puede concluir.")
elif all(r.get("clase") == "baja" for r in resultados_mz if not r.get("skip")):
    print("     Senal demasiado debil en todas las macrozonas.")
    print("     NO conviene avanzar con depreciacion zonificada.")
    print("     Mantener curva unica actual (0.6%/ano).")
elif any(r.get("clase") == "baja" for r in resultados_mz if not r.get("skip")):
    print("     Senal diferenciada entre macrozonas.")
    print("     CONVIENE preparar una propuesta acotada de depreciacion zonificada")
    print("     para las macrozonas con senal media/alta.")
    print("     Las macrozonas con senal baja mantendrian la curva actual.")
else:
    print("     Senal fuerte y consistente en todas las macrozonas.")
    print("     CONVIENE avanzar con una propuesta formal de depreciacion zonificada.")

print()
print("Reportes generados:")
print("  - reports/rf_depreciacion_macrozonas.csv")
print("  - reports/rf_depreciacion_grid.csv")
print("  - reports/rf_depreciacion_heatmap.png (si se genero)")
print()
print("=" * 80)
