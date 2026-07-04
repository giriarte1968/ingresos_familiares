"""
Analisis rolling de CT (Coeficiente de Tiempo) por macrozona.
Calcula el factor CT real observado en el mercado USD/m² usando
rolling windows, y lo compara con la tabla CT actual.

NO modifica archivos productivos. Genera reports/ct_rolling_analysis.csv.

Uso: python scripts/analizar_ct_rolling.py
"""
import json, sys, os, csv
import statistics
from datetime import datetime, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 100)
print("ANALISIS ROLLING: CT (Coeficiente de Tiempo) real vs tabla actual")
print("=" * 100)

# ─── CARGAR DATOS ───
with open("cache_scraping.json", encoding="utf-8") as f:
    cache = json.load(f)
props = cache["propiedades"]
print(f"\nTotal propiedades en cache: {len(props)}")

# ─── CARGAR MACROZONAS ───
with open("data/zonas_depreciacion.json", encoding="utf-8") as f:
    zonas_cfg = json.load(f)
macrozonas = [m for m in zonas_cfg["macrozonas"] if m.get("bbox")]

# ─── CARGAR CT TABLE ACTUAL ───
with open("config/anclas_config.json", encoding="utf-8") as f:
    anclas_cfg = json.load(f)
ct_table = anclas_cfg.get("generator", {}).get("ct_table", [])
ct_factors = anclas_cfg.get("generator", {}).get("ct_factors", {"usado": 1.12, "nuevo": 0.95})
FACTOR_USADO = ct_factors.get("usado", 1.12)

def interpolar_ct(tabla, meses):
    if not tabla:
        return 1.0
    if meses <= tabla[0][0]:
        return tabla[0][1]
    if meses >= tabla[-1][0]:
        return 1.0
    for i in range(len(tabla) - 1):
        x1, y1 = tabla[i]
        x2, y2 = tabla[i + 1]
        if x1 <= meses <= x2:
            return y1 + (y2 - y1) * (meses - x1) / (x2 - x1)
    return 1.0

def get_month_key(date_str):
    if not date_str:
        return None
    try:
        dt = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
        return dt.strftime("%Y-%m")
    except:
        return None

def add_months(year_month, n):
    """Suma n meses a un YYYY-MM, retorna YYYY-MM."""
    year, month = int(year_month[:4]), int(year_month[5:7])
    total = year * 12 + (month - 1) + n
    return f"{total // 12:04d}-{total % 12 + 1:02d}"

def months_diff(a, b):
    """Diferencia en meses entre dos YYYY-MM (a - b)."""
    ya, ma = int(a[:4]), int(a[5:7])
    yb, mb = int(b[:4]), int(b[5:7])
    return (ya - yb) * 12 + (ma - mb)

# ─── FILTRAR Y ASIGNAR MACROZONAS ───
ventas_con_fecha = 0
macrozona_items = defaultdict(list)  # macrozona_id -> lista de vm2 por mes

for p in props:
    if p.get("operacion") != "venta":
        continue
    if p.get("moneda") not in (None, "USD"):
        continue
    m2, vm2 = p.get("m2"), p.get("valor_m2")
    if not all([m2, vm2]):
        continue
    if vm2 < 200 or vm2 > 5000 or m2 < 15 or m2 > 500:
        continue
    try:
        lat, lon = float(p.get("lat", 0)), float(p.get("lon", 0))
    except:
        continue
    if not lat or not lon:
        continue

    # Asignar macrozona (orden: primer match)
    macro = "resto_rosario"
    for mz in macrozonas:
        b = mz["bbox"]
        if b["lat_min"] <= lat <= b["lat_max"] and b["lon_min"] <= lon <= b["lon_max"]:
            macro = mz["id"]
            break

    mk = get_month_key(p.get("date_created"))
    if not mk:
        continue
    ventas_con_fecha += 1
    macrozona_items[macro].append((mk, float(vm2)))

print(f"\nVentas USD con fecha: {ventas_con_fecha}")

# ─── COMPUTAR MEDIANA POR MES POR MACROZONA ───
monthly_median = {}  # macrozona_id -> {YYYY-MM: median_vm2}

for mz_id, items in sorted(macrozona_items.items()):
    by_month = defaultdict(list)
    for mk, vm2 in items:
        by_month[mk].append(vm2)
    
    medians = {}
    for mk in sorted(by_month):
        vals = sorted(by_month[mk])
        n = len(vals)
        if n < 5:
            continue  # skip meses con pocos datos
        med = statistics.median(vals)
        medians[mk] = med
    monthly_median[mz_id] = medians
    print(f"  {mz_id:<25} meses_con_datos={len(medians):>3}  total_props={len(items):>6}")

# ─── CALCULAR CT ROLLING REAL ───
EDADES_MESES = [3, 6, 9, 12, 15, 18, 24, 30, 36, 42, 48]
resultados = []

for mz_id, medians in sorted(monthly_median.items()):
    meses_ordenados = sorted(medians.keys())
    if len(meses_ordenados) < 6:
        print(f"\n  {mz_id}: SKIP (solo {len(meses_ordenados)} meses con datos)")
        continue
    
    # Por cada mes de referencia (debe tener suficientes meses antes)
    ct_observations = defaultdict(list)  # edad -> [ct_values]
    
    for i, mes_ref in enumerate(meses_ordenados):
        vm2_hoy = medians[mes_ref]
        
        for edad in EDADES_MESES:
            mes_pasado = add_months(mes_ref, -edad)
            if mes_pasado in medians:
                vm2_entonces = medians[mes_pasado]
                if vm2_entonces > 0:
                    ct_real = vm2_hoy / vm2_entonces
                    ct_observations[edad].append(ct_real)
    
    # CT rolling: solo usa pares donde ambos meses caen en los ultimos 12 meses
    # CT historico: promedio de todos los pares disponibles
    if len(meses_ordenados) < 3:
        continue
    
    ultimos_12_meses = meses_ordenados[-12:] if len(meses_ordenados) >= 12 else meses_ordenados
    if len(ultimos_12_meses) < 3:
        ultimos_12_meses = meses_ordenados
    
    ct_rolling_12m = {}
    ct_historico = {}
    
    for edad in EDADES_MESES:
        vals_all = ct_observations.get(edad, [])
        if not vals_all:
            continue
        
        # Historicos: todos los pares
        ct_historico[edad] = statistics.median(vals_all) if len(vals_all) >= 2 else vals_all[0]
        
        # Rolling 12m: solo pares donde mes_ref esta en los ultimos 12 meses de datos
        vals_recientes = []
        for i, mes_ref in enumerate(meses_ordenados):
            if mes_ref not in ultimos_12_meses:
                continue
            mes_pasado = add_months(mes_ref, -edad)
            if mes_pasado in medians:
                vm2_hoy = medians[mes_ref]
                vm2_entonces = medians[mes_pasado]
                if vm2_entonces > 0:
                    vals_recientes.append(vm2_hoy / vm2_entonces)
        
        ct_rolling_12m[edad] = statistics.median(vals_recientes) if len(vals_recientes) >= 2 else (vals_recientes[0] if vals_recientes else None)
    
    # CT actual de la tabla (sin factor usado)
    ct_actual = {}
    for edad in EDADES_MESES:
        ct_actual[edad] = interpolar_ct(ct_table, edad)
    
    # CT actual CON factor usado (lo que realmente aplica el pipeline)
    ct_actual_con_factor = {}
    for edad in EDADES_MESES:
        ct_base = interpolar_ct(ct_table, edad)
        ct_actual_con_factor[edad] = 1.0 + (ct_base - 1.0) * FACTOR_USADO
    
    # Guardar resultados
    for edad in EDADES_MESES:
        if edad not in ct_historico:
            continue
        ct_h = ct_historico.get(edad)
        ct_r = ct_rolling_12m.get(edad)
        ct_a = ct_actual.get(edad, 1.0)
        ct_af = ct_actual_con_factor.get(edad, 1.0)
        dif_h = (ct_h / ct_a - 1.0) * 100 if ct_h and ct_a else None
        dif_r = (ct_r / ct_a - 1.0) * 100 if ct_r and ct_a else None
        n_obs = len(ct_observations.get(edad, []))
        
        resultados.append({
            "macrozona": mz_id,
            "edad_meses": edad,
            "ct_actual_tabla": round(ct_a, 4),
            "ct_actual_con_factor": round(ct_af, 4),
            "ct_historico_mediana": round(ct_h, 4) if ct_h else None,
            "ct_rolling_12m_mediana": round(ct_r, 4) if ct_r else None,
            "dif_historico_vs_tabla_pct": round(dif_h, 2) if dif_h is not None else None,
            "dif_rolling_vs_tabla_pct": round(dif_r, 2) if dif_r is not None else None,
            "n_pares": n_obs,
        })

# ─── GUARDAR REPORTE ───
csv_path = "reports/ct_rolling_analysis.csv"
with open(csv_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=[
        "macrozona", "edad_meses",
        "ct_actual_tabla", "ct_actual_con_factor",
        "ct_historico_mediana", "ct_rolling_12m_mediana",
        "dif_historico_vs_tabla_pct", "dif_rolling_vs_tabla_pct",
        "n_pares"
    ])
    w.writeheader()
    for r in resultados:
        w.writerow(r)

print(f"\nReporte guardado: {csv_path}")

# ─── RESUMEN POR MACROZONA ───
print("\n" + "=" * 100)
print("RESUMEN CT POR MACROZONA")
print("=" * 100)

for mz_id in sorted(set(r["macrozona"] for r in resultados)):
    print(f"\n--- {mz_id} ---")
    print(f"{'Edad':>6} {'CT_tabla':>10} {'CT_factor':>10} {'CT_hist':>10} {'CT_roll12':>10} {'dif_hist%':>10} {'dif_roll%':>10} {'n':>5}")
    print("-" * 75)
    for r in sorted([rr for rr in resultados if rr["macrozona"] == mz_id], key=lambda x: x["edad_meses"]):
        print(f"{r['edad_meses']:>6} "
              f"{r['ct_actual_tabla']:>10.4f} "
              f"{r['ct_actual_con_factor']:>10.4f} "
              f"{r['ct_historico_mediana'] or 0:>10.4f} "
              f"{r['ct_rolling_12m_mediana'] or 0:>10.4f} "
              f"{r['dif_historico_vs_tabla_pct'] or 0:>+9.2f}% "
              f"{r['dif_rolling_vs_tabla_pct'] or 0:>+9.2f}% "
              f"{r['n_pares']:>5}")

# ─── TASA ANUAL IMPLICITA ───
print("\n" + "=" * 100)
print("TASA ANUAL IMPLICITA (CT rolling 12m convertida a % anual)")
print("=" * 100)
print(f"{'Macrozona':<22} {'6m':>10} {'12m':>10} {'18m':>10} {'24m':>10} {'30m':>10} {'36m':>10}")
print("-" * 75)

for mz_id in sorted(set(r["macrozona"] for r in resultados)):
    line = f"{mz_id:<22}"
    for edad in [6, 12, 18, 24, 30, 36]:
        matches = [r for r in resultados if r["macrozona"] == mz_id and r["edad_meses"] == edad]
        if matches and matches[0]["ct_rolling_12m_mediana"]:
            ct = matches[0]["ct_rolling_12m_mediana"]
            anos = edad / 12
            tasa = (ct ** (1 / anos) - 1) * 100 if ct > 0 else 0
            line += f"{tasa:>+9.2f}% "
        else:
            line += f"{'N/A':>10} "
    print(line)

# Tambien mostrar tasa anual del CT historico
print("\nTASA ANUAL - CT HISTORICO (promedio del periodo completo):")
print(f"{'Macrozona':<22} {'6m':>10} {'12m':>10} {'18m':>10} {'24m':>10} {'30m':>10} {'36m':>10}")
print("-" * 75)
for mz_id in sorted(set(r["macrozona"] for r in resultados)):
    line = f"{mz_id:<22}"
    for edad in [6, 12, 18, 24, 30, 36]:
        matches = [r for r in resultados if r["macrozona"] == mz_id and r["edad_meses"] == edad]
        if matches and matches[0]["ct_historico_mediana"]:
            ct = matches[0]["ct_historico_mediana"]
            anos = edad / 12
            tasa = (ct ** (1 / anos) - 1) * 100 if ct > 0 else 0
            line += f"{tasa:>+9.2f}% "
        else:
            line += f"{'N/A':>10} "
    print(line)

# Tasa actual de la tabla para comparacion
print("\nTASA ANUAL - CT TABLA ACTUAL (sin factor usado):")
print(f"{'6m':>10} {'12m':>10} {'18m':>10} {'24m':>10} {'30m':>10} {'36m':>10}")
for edad in [6, 12, 18, 24, 30, 36]:
    ct = interpolar_ct(ct_table, edad)
    anos = edad / 12
    tasa = (ct ** (1 / anos) - 1) * 100 if ct > 0 else 0
    print(f"{tasa:>+9.2f}% ", end="")
print()

print("\n" + "=" * 100)
print("FIN ANALISIS CT ROLLING")
print("=" * 100)
