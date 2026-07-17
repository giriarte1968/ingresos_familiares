#!/usr/bin/env python3
"""
ML Insights sobre dataset COMBINADO (old + new scraping)
"""
import json
import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
from collections import defaultdict

# ── Load Data ──
with open("cache_scraping.json", "r", encoding="utf-8") as f:
    old = json.load(f)["propiedades"]
with open("cache_scraping_nuevo.json", "r", encoding="utf-8") as f:
    new = json.load(f)["propiedades"]

all_props = old + new
df = pd.DataFrame(all_props)
df = df[(df["tipo"] == "Departamento") & (df["operacion"] == "venta") & (df["valor_m2"] > 0)].copy()

print("=" * 70)
print("ML INSIGHTS: DATASET COMBINADO (OLD + NEW)")
print("=" * 70)
print("Total departamentos venta con valor_m2 > 0:", len(df))

# ── Macrozona ──
def assign_macrozona(lat, lon):
    if pd.isna(lat) or pd.isna(lon):
        return "sin_coords"
    if -32.945 <= lat <= -32.9 and -60.78 <= lon <= -60.72:
        return "fisherton"
    if -32.94 <= lat <= -32.925 and -60.64 <= lon <= -60.62:
        return "puerto_norte"
    if -32.96 <= lat <= -32.92 and -60.67 <= lon <= -60.62:
        return "centro_premium"
    if -32.975 <= lat <= -32.92 and -60.69 <= lon <= -60.625:
        return "macrocentro"
    if lat > -32.93:
        return "norte"
    if lat < -32.975:
        return "sur"
    if lon < -60.69:
        return "oeste"
    return "otro"

df["macrozona"] = df.apply(lambda r: assign_macrozona(r.get("lat"), r.get("lon")), axis=1)

# ════════════════════════════════════════════════════════════════════
# 1. DBSCAN
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("1. DBSCAN GEO-CLUSTERING (eps=127m, min_samples=5)")
print("=" * 70)

from sklearn.cluster import DBSCAN

coords = df[["lat", "lon"]].dropna()
coords_rad = np.radians(coords.values)
db = DBSCAN(eps=127/6371000, min_samples=5, metric="haversine")
labels = db.fit_predict(coords_rad)

n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
noise_pct = (labels == -1).sum() / len(labels) * 100

print("Clusters: %d, Noise: %.1f%%" % (n_clusters, noise_pct))

df_c = df.loc[coords.index].copy()
df_c["cluster"] = labels

# Top clusters
for c in sorted(set(labels))[:10]:
    if c == -1:
        continue
    mask = labels == c
    c_df = df_c[mask]
    mz = c_df["macrozona"].mode().iloc[0] if len(c_df) > 0 else "?"
    print("  Cluster %d: n=%d, vm2_med=$%.0f, lat=%.2f, lon=%.2f, macro=%s" % (
        c, mask.sum(), c_df["valor_m2"].median(), c_df["lat"].mean(), c_df["lon"].mean(), mz))

# ════════════════════════════════════════════════════════════════════
# 2. HEDONIC REGRESSION
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("2. HEDONIC REGRESSION (log(vm2) ~ m2 + dorms + lat + lon)")
print("=" * 70)

from sklearn.linear_model import LinearRegression
from scipy import stats

df_h = df[["valor_m2", "m2", "dormitorios", "lat", "lon"]].dropna()
df_h = df_h.copy()
df_h["log_vm2"] = np.log(df_h["valor_m2"])

X = df_h[["m2", "dormitorios", "lat", "lon"]].values
y = df_h["log_vm2"].values

model = LinearRegression()
model.fit(X, y)
r2 = model.score(X, y)

n = len(y)
k = X.shape[1]
residuals = y - model.predict(X)
mse = np.sum(residuals**2) / (n - k - 1)
se = np.sqrt(mse * np.diag(np.linalg.inv(X.T @ X)))
t_stats = model.coef_ / se
p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), df=n-k-1))

print("R-sq = %.4f (n=%d)" % (r2, n))
feature_names = ["m2", "dormitorios", "lat", "lon"]
for fname, coef, pv in zip(feature_names, model.coef_, p_values):
    sig = "***" if pv < 0.001 else "**" if pv < 0.01 else "*" if pv < 0.05 else "ns"
    print("  %s: %.4f (p=%.4f) %s" % (fname, coef, pv, sig))

# Zone premiums (dummy regression)
df_h2 = df[["valor_m2", "m2", "dormitorios", "lat", "lon", "macrozona"]].dropna()
df_h2 = pd.get_dummies(df_h2, columns=["macrozona"], drop_first=True)
zone_cols = [c for c in df_h2.columns if c.startswith("macrozona_")]
X2 = df_h2[["m2", "dormitorios", "lat", "lon"] + zone_cols].values
y2 = np.log(df_h2["valor_m2"].values)
model2 = LinearRegression()
model2.fit(X2, y2)
r2_2 = model2.score(X2, y2)
print("\nWith zone dummies: R-sq = %.4f" % r2_2)
for fname, coef in zip(["m2", "dormitorios", "lat", "lon"] + zone_cols, model2.coef_):
    print("  %s: %.4f" % (fname, coef))

# ════════════════════════════════════════════════════════════════════
# 3. RANDOM FOREST
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("3. RANDOM FOREST FEATURE IMPORTANCE")
print("=" * 70)

from sklearn.ensemble import RandomForestRegressor

df_rf = df[["valor_m2", "m2", "dormitorios", "lat", "lon"]].dropna()
X_rf = df_rf[["m2", "dormitorios", "lat", "lon"]].values
y_rf = df_rf["valor_m2"].values

rf = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
rf.fit(X_rf, y_rf)
r2_rf = rf.score(X_rf, y_rf)

print("R-sq = %.4f (n=%d)" % (r2_rf, len(y_rf)))
importances = dict(zip(["m2", "dormitorios", "lat", "lon"], rf.feature_importances_))
for fname, imp in sorted(importances.items(), key=lambda x: -x[1]):
    print("  %s: %.3f (%.1f%%)" % (fname, imp, imp * 100))

# Size discount
m2_range = np.linspace(20, 200, 50)
X_m2 = X_rf.copy()
preds = []
for m2_val in m2_range:
    X_m2[:, 0] = m2_val
    preds.append(rf.predict(X_m2).mean())

print("\nSize discount curve:")
for m2 in [30, 40, 50, 60, 80, 100, 120, 150, 200]:
    idx = np.argmin(np.abs(m2_range - m2))
    print("  %3dm2 -> $%.0f/m2" % (m2, preds[idx]))

# ════════════════════════════════════════════════════════════════════
# 4. ANOMALY DETECTION
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("4. ANOMALY DETECTION (Isolation Forest)")
print("=" * 70)

from sklearn.ensemble import IsolationForest

df_a = df[["valor_m2", "m2", "dormitorios"]].dropna()
X_a = df_a[["valor_m2", "m2"]].values
iso = IsolationForest(contamination=0.02, random_state=42)
preds_a = iso.fit_predict(X_a)

outliers = df_a[preds_a == -1]
normals = df_a[preds_a == 1]
print("Outliers: %d (%.1f%%)" % (len(outliers), len(outliers)/len(df_a)*100))
print("  Outlier vm2: mean=$%.0f, med=$%.0f" % (outliers["valor_m2"].mean(), outliers["valor_m2"].median()))
print("  Outlier m2:  mean=%.0f, med=%.0f" % (outliers["m2"].mean(), outliers["m2"].median()))
print("  Normal vm2:  mean=$%.0f, med=$%.0f" % (normals["valor_m2"].mean(), normals["valor_m2"].median()))
print("  Normal m2:   mean=%.0f, med=%.0f" % (normals["m2"].mean(), normals["m2"].median()))

# ════════════════════════════════════════════════════════════════════
# 5. MACROZONA BREAKDOWN
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("5. MACROZONA BREAKDOWN")
print("=" * 70)

mz_stats = df.groupby("macrozona").agg(
    n=("valor_m2", "count"),
    vm2_med=("valor_m2", "median"),
    vm2_mean=("valor_m2", "mean"),
    vm2_std=("valor_m2", "std"),
    m2_med=("m2", "median"),
    precio_med=("precio", "median"),
).sort_values("n", ascending=False)

print("%-20s %5s %8s %8s %8s %8s" % ("Macrozona", "n", "vm2_med", "vm2_std", "m2_med", "precio_med"))
print("-" * 75)
for mz, row in mz_stats.iterrows():
    print("%-20s %5d $%6.0f $%6.0f %6.0f $%8.0f" % (
        mz, row["n"], row["vm2_med"], row["vm2_std"], row["m2_med"], row["precio_med"]))

print("\nDONE")
