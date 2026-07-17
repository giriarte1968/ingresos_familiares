#!/usr/bin/env python3
"""
ML Insights Comparativo: OLD cache vs NEW cache
Basado en el reporte original del 2026-06-04 sobre cache_scraping.json
"""
import json
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from collections import Counter

# ── Load Data ──
def load_props(path, label):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    props = data.get("propiedades", [])
    df = pd.DataFrame(props)
    df["dataset"] = label
    return df

print("=" * 70)
print("ML INSIGHTS COMPARATIVO: OLD vs NEW")
print("=" * 70)

df_old = load_props("cache_scraping.json", "OLD")
df_new = load_props("cache_scraping_nuevo.json", "NEW")

# Filter departamentos venta only (main analysis)
old_venta = df_old[(df_old["tipo"] == "Departamento") & (df_old["operacion"] == "venta")].copy()
new_venta = df_new[(df_new["tipo"] == "Departamento") & (df_new["operacion"] == "venta")].copy()

# Combined for joint analysis
combined = pd.concat([old_venta, new_venta], ignore_index=True)

print("\nDataset OLD: %d departamentos venta" % len(old_venta))
print("Dataset NEW: %d departamentos venta" % len(new_venta))
print("Combined: %d" % len(combined))

# ── Macrozona assignment ──
def assign_macrozona(lat, lon):
    if pd.isna(lat) or pd.isna(lon):
        return "sin_coords"
    if -32.96 <= lat <= -32.93 and -60.67 <= lon <= -60.63:
        return "centro_premium"
    if -32.96 <= lat <= -32.92 and -60.68 <= lon <= -60.65:
        return "macrocentro"
    if lat > -32.93:
        return "norte"
    if lat < -32.96:
        return "sur"
    if lon < -60.68:
        return "oeste"
    return "otro"

for df in [old_venta, new_venta, combined]:
    df["macrozona"] = df.apply(lambda r: assign_macrozona(r.get("lat"), r.get("lon")), axis=1)

# Filter valid
old_v = old_venta[old_venta["valor_m2"] > 0].copy()
new_v = new_venta[new_venta["valor_m2"] > 0].copy()
comb = combined[combined["valor_m2"] > 0].copy()

print("\nCon valor_m2 > 0: OLD=%d, NEW=%d" % (len(old_v), len(new_v)))

# ════════════════════════════════════════════════════════════════════
# 1. DBSCAN GEO-CLUSTERING
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("1. DBSCAN GEO-CLUSTERING (eps=127m, min_samples=5)")
print("=" * 70)

from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

def run_dbscan(df, label):
    coords = df[["lat", "lon"]].dropna()
    if len(coords) < 10:
        print("  %s: insufficient data" % label)
        return None, None
    
    # Convert to radians for haversine
    coords_rad = np.radians(coords.values)
    db = DBSCAN(eps=127/6371000, min_samples=5, metric="haversine")
    labels = db.fit_predict(coords_rad)
    
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    noise_pct = (labels == -1).sum() / len(labels) * 100
    
    df_clustered = df.loc[coords.index].copy()
    df_clustered["cluster"] = labels
    
    print("\n  %s: %d clusters, %.1f%% noise" % (label, n_clusters, noise_pct))
    
    # Top clusters by size
    cluster_stats = []
    for c in sorted(set(labels)):
        if c == -1:
            continue
        mask = labels == c
        cluster_df = df_clustered[mask]
        cluster_stats.append({
            "cluster": c,
            "n": mask.sum(),
            "vm2_med": cluster_df["valor_m2"].median(),
            "lat": cluster_df["lat"].mean(),
            "lon": cluster_df["lon"].mean(),
        })
    
    cluster_stats.sort(key=lambda x: -x["n"])
    print("  Top 5 clusters:")
    for cs in cluster_stats[:5]:
        print("    Cluster %d: n=%d, vm2_med=$%.0f, lat=%.2f, lon=%.2f" % (
            cs["cluster"], cs["n"], cs["vm2_med"], cs["lat"], cs["lon"]))
    
    return n_clusters, noise_pct

n_old, noise_old = run_dbscan(old_v, "OLD")
n_new, noise_new = run_dbscan(new_v, "NEW")

# ════════════════════════════════════════════════════════════════════
# 2. HEDONIC REGRESSION (OLS)
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("2. HEDONIC REGRESSION (log(valor_m2) ~ m2 + dorms + zona + lat + lon)")
print("=" * 70)

from sklearn.linear_model import LinearRegression
from scipy import stats

def run_hedonic(df, label):
    df_h = df[["valor_m2", "m2", "dormitorios", "lat", "lon"]].dropna()
    if len(df_h) < 50:
        print("  %s: insufficient data" % label)
        return
    
    # Create zone dummies
    df_h = df_h.copy()
    df_h["log_vm2"] = np.log(df_h["valor_m2"])
    
    # Simple OLS: log(vm2) ~ m2 + dorms + lat + lon
    X = df_h[["m2", "dormitorios", "lat", "lon"]].values
    y = df_h["log_vm2"].values
    
    model = LinearRegression()
    model.fit(X, y)
    r2 = model.score(X, y)
    
    # Coefficients
    feature_names = ["m2", "dormitorios", "lat", "lon"]
    coefs = dict(zip(feature_names, model.coef_))
    
    # Statistical significance via t-tests
    n = len(y)
    k = X.shape[1]
    residuals = y - model.predict(X)
    mse = np.sum(residuals**2) / (n - k - 1)
    se = np.sqrt(mse * np.diag(np.linalg.inv(X.T @ X)))
    t_stats = model.coef_ / se
    p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), df=n-k-1))
    
    print("\n  %s: R² = %.4f" % (label, r2))
    print("  Coefficients:")
    for fname, coef, pv in zip(feature_names, model.coef_, p_values):
        sig = "***" if pv < 0.001 else "**" if pv < 0.01 else "*" if pv < 0.05 else "ns"
        print("    %s: %.4f (p=%.4f) %s" % (fname, coef, pv, sig))
    
    return {"r2": r2, "coefs": coefs, "p_values": dict(zip(feature_names, p_values))}

hed_old = run_hedonic(old_v, "OLD")
hed_new = run_hedonic(new_v, "NEW")

# ════════════════════════════════════════════════════════════════════
# 3. RANDOM FOREST + FEATURE IMPORTANCE (replaces XGBoost)
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("3. RANDOM FOREST FEATURE IMPORTANCE (replaces XGBoost)")
print("=" * 70)

from sklearn.ensemble import RandomForestRegressor

def run_rf(df, label):
    df_rf = df[["valor_m2", "m2", "dormitorios", "lat", "lon"]].dropna()
    if len(df_rf) < 100:
        print("  %s: insufficient data" % label)
        return
    
    X = df_rf[["m2", "dormitorios", "lat", "lon"]].values
    y = df_rf["valor_m2"].values
    
    rf = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
    rf.fit(X, y)
    r2 = rf.score(X, y)
    
    importances = dict(zip(["m2", "dormitorios", "lat", "lon"], rf.feature_importances_))
    
    # Partial dependence for m2
    m2_range = np.linspace(20, 200, 50)
    X_m2 = X.copy()
    preds_m2 = []
    for m2_val in m2_range:
        X_m2[:, 0] = m2_val
        preds_m2.append(rf.predict(X_m2).mean())
    
    print("\n  %s: R² = %.4f" % (label, r2))
    print("  Feature Importance:")
    for fname, imp in sorted(importances.items(), key=lambda x: -x[1]):
        print("    %s: %.3f (%.1f%%)" % (fname, imp, imp * 100))
    
    # Size discount
    base_50 = preds_m2[np.argmin(np.abs(m2_range - 50))]
    base_100 = preds_m2[np.argmin(np.abs(m2_range - 100))]
    base_200 = preds_m2[np.argmin(np.abs(m2_range - 200))]
    print("  Size discount:")
    print("    50m2 -> $%.0f/m2" % base_50)
    print("    100m2 -> $%.0f/m2 (%.1f%% vs 50m2)" % (base_100, (base_100/base_50 - 1) * 100))
    print("    200m2 -> $%.0f/m2 (%.1f%% vs 50m2)" % (base_200, (base_200/base_50 - 1) * 100))
    
    return {"r2": r2, "importances": importances, "size_curve": list(zip(m2_range.tolist(), preds_m2))}

rf_old = run_rf(old_v, "OLD")
rf_new = run_rf(new_v, "NEW")

# ════════════════════════════════════════════════════════════════════
# 4. ANOMALY DETECTION (Isolation Forest)
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("4. ANOMALY DETECTION (Isolation Forest)")
print("=" * 70)

from sklearn.ensemble import IsolationForest

def run_anomalies(df, label):
    df_a = df[["valor_m2", "m2", "dormitorios"]].dropna()
    if len(df_a) < 50:
        print("  %s: insufficient data" % label)
        return
    
    X = df_a[["valor_m2", "m2"]].values
    
    iso = IsolationForest(contamination=0.02, random_state=42)
    preds = iso.fit_predict(X)
    
    n_outliers = (preds == -1).sum()
    outlier_pct = n_outliers / len(preds) * 100
    
    outliers = df_a[preds == -1]
    normals = df_a[preds == 1]
    
    print("\n  %s: %d outliers (%.1f%%)" % (label, n_outliers, outlier_pct))
    print("  Outlier stats:")
    print("    valor_m2: mean=$%.0f, median=$%.0f" % (outliers["valor_m2"].mean(), outliers["valor_m2"].median()))
    print("    m2: mean=%.0f, median=%.0f" % (outliers["m2"].mean(), outliers["m2"].median()))
    print("  Normal stats:")
    print("    valor_m2: mean=$%.0f, median=$%.0f" % (normals["valor_m2"].mean(), normals["valor_m2"].median()))
    print("    m2: mean=%.0f, median=%.0f" % (normals["m2"].mean(), normals["m2"].median()))
    
    return {"n_outliers": n_outliers, "pct": outlier_pct}

anom_old = run_anomalies(old_v, "OLD")
anom_new = run_anomalies(new_v, "NEW")

# ════════════════════════════════════════════════════════════════════
# 5. DISTRIBUTION COMPARISON + KS TEST
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("5. DISTRIBUTION COMPARISON (KS Test + Percentiles)")
print("=" * 70)

from scipy.stats import ks_2samp, ttest_ind

def compare_distributions(old_vals, new_vals, name):
    ks_stat, ks_p = ks_2samp(old_vals, new_vals)
    t_stat, t_p = ttest_ind(old_vals, new_vals, equal_var=False)
    
    old_pcts = np.percentile(old_vals, [10, 25, 50, 75, 90])
    new_pcts = np.percentile(new_vals, [10, 25, 50, 75, 90])
    
    print("\n  %s:" % name)
    print("    KS test: stat=%.4f, p=%.2e %s" % (ks_stat, ks_p, "***" if ks_p < 0.001 else "ns"))
    print("    t-test:  stat=%.4f, p=%.2e %s" % (t_stat, t_p, "***" if t_p < 0.001 else "ns"))
    print("    Percentiles:")
    print("      %10s  %25s  %50s  %75s  %90s" % ("P10", "P25", "P50", "P75", "P90"))
    print("      OLD: %s" % "  ".join("$%.0f" % p for p in old_pcts))
    print("      NEW: %s" % "  ".join("$%.0f" % p for p in new_pcts))
    print("    Mean: OLD=$%.0f, NEW=$%.0f (%.1f%%)" % (
        np.mean(old_vals), np.mean(new_vals),
        (np.mean(new_vals) / np.mean(old_vals) - 1) * 100))

compare_distributions(old_v["valor_m2"].values, new_v["valor_m2"].values, "valor_m2")
compare_distributions(old_v["m2"].values, new_v["m2"].values, "m2")

# ════════════════════════════════════════════════════════════════════
# 6. MACROZONA COMPARISON
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("6. MACROZONA COMPARISON")
print("=" * 70)

def macrozona_analysis(old_df, new_df, label):
    old_mz = old_df.groupby("macrozona").agg(
        n=("valor_m2", "count"),
        vm2_med=("valor_m2", "median"),
        vm2_mean=("valor_m2", "mean"),
        m2_med=("m2", "median"),
    ).reset_index()
    
    new_mz = new_df.groupby("macrozona").agg(
        n=("valor_m2", "count"),
        vm2_med=("valor_m2", "median"),
        vm2_mean=("valor_m2", "mean"),
        m2_med=("m2", "median"),
    ).reset_index()
    
    merged = old_mz.merge(new_mz, on="macrozona", suffixes=("_old", "_new"), how="outer").fillna(0)
    
    print("\n  %s:" % label)
    print("  %-20s %8s %8s %8s %8s %8s" % ("Macrozona", "n_OLD", "n_NEW", "vm2_OLD", "vm2_NEW", "Cambio"))
    for _, row in merged.iterrows():
        cambio = ""
        if row["vm2_med_old"] > 0:
            cambio = "%+.1f%%" % ((row["vm2_med_new"] / row["vm2_med_old"] - 1) * 100)
        print("  %-20s %8d %8d %8.0f %8.0f %8s" % (
            row["macrozona"], row["n_old"], row["n_new"],
            row["vm2_med_old"], row["vm2_med_new"], cambio))

macrozona_analysis(old_v, new_v, "Departamentos Venta")

# ════════════════════════════════════════════════════════════════════
# 7. SIZE DISCOUNT CURVE COMPARISON
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("7. SIZE DISCOUNT CURVE COMPARISON")
print("=" * 70)

if rf_old and rf_new:
    m2_pts = [30, 40, 50, 60, 80, 100, 120, 150, 200]
    print("\n  m2     OLD vm2    NEW vm2    Cambio")
    for m2 in m2_pts:
        idx_old = np.argmin(np.abs(np.array([p[0] for p in rf_old["size_curve"]]) - m2))
        idx_new = np.argmin(np.abs(np.array([p[0] for p in rf_new["size_curve"]]) - m2))
        old_val = rf_old["size_curve"][idx_old][1]
        new_val = rf_new["size_curve"][idx_new][1]
        cambio = (new_val / old_val - 1) * 100 if old_val > 0 else 0
        print("  %3d   $%.0f     $%.0f     %+.1f%%" % (m2, old_val, new_val, cambio))

# ════════════════════════════════════════════════════════════════════
# 8. ACCIONES RECOMENDADAS
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("8. VEREDICTO: CAMBIAN NUESTRAS VERDADES?")
print("=" * 70)

# Compute deltas
old_med_vm2 = old_v["valor_m2"].median()
new_med_vm2 = new_v["valor_m2"].median()
delta_vm2 = (new_med_vm2 / old_med_vm2 - 1) * 100

old_med_m2 = old_v["m2"].median()
new_med_m2 = new_v["m2"].median()
delta_m2 = (new_med_m2 / old_med_m2 - 1) * 100

print("""
| Verdad | Antes | Ahora | Cambio | Impacto |
|---|---|---|---|---|
| valor_m2 mediana | $%.0f | $%.0f | %.1f%% | %s |
| m2 mediana | %.0f | %.0f | %.1f%% | %s |
| DBSCAN clusters | %s | %s | — | %s |
| RF R² | %s | %s | — | %s |
| Anomalías | %s | %s | — | %s |
""" % (
    old_med_vm2, new_med_vm2, delta_vm2,
    "CT ajuste necesario" if abs(delta_vm2) > 3 else "marginal",
    old_med_m2, new_med_m2, delta_m2,
    "Factor volumen afectado" if abs(delta_m2) > 5 else "marginal",
    "%s" % n_old if n_old else "?",
    "%s" % n_new if n_new else "?",
    "Revisar bbox macrozonas" if n_new and n_old and abs(n_new - n_old) > 20 else "estable",
    "%.3f" % rf_old["r2"] if rf_old else "?",
    "%.3f" % rf_new["r2"] if rf_new else "?",
    "modelo cambió" if rf_old and rf_new and abs(rf_old["r2"] - rf_new["r2"]) > 0.05 else "estable",
    "%d" % (anom_old["n_outliers"] if anom_old else 0),
    "%d" % (anom_new["n_outliers"] if anom_new else 0),
    "revisar" if anom_new and anom_old and anom_new["n_outliers"] > anom_old["n_outliers"] * 1.5 else "estable",
))

print("DONE")
