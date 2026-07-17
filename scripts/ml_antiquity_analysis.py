#!/usr/bin/env python3
"""
ML con ANTiquity: analisis de si la antiguedad del edificio afecta el precio
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
with open("cache_scraping_nuevo_v2.json", "r", encoding="utf-8") as f:
    new = json.load(f)["propiedades"]

all_props = old + new
df = pd.DataFrame(all_props)
df = df[(df["tipo"] == "Departamento") & (df["operacion"] == "venta") & (df["valor_m2"] > 0)].copy()

print("=" * 70)
print("ML CON ANTiquity: DEPARTAMENTOS VENTA (COMBINED)")
print("=" * 70)
print("Total:", len(df))

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

# ── Clean antiquity ──
# antiquity=-1 means unknown, treat as NaN
df["antiquity_clean"] = df["antiquity"].replace(-1, np.nan)
df["antiquity_valid"] = df["antiquity_clean"].notna()

print("\nAntiquity coverage:")
print("  Valid (>=0):", df["antiquity_valid"].sum(), "(%.1f%%)" % (df["antiquity_valid"].mean() * 100))
print("  Unknown (-1):", (~df["antiquity_valid"]).sum())

# ════════════════════════════════════════════════════════════════════
# 1. DISTRIBUTION BY AGE GROUP
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("1. VM2 BY AGE GROUP")
print("=" * 70)

def age_group(a):
    if pd.isna(a):
        return "unknown"
    if a == 0:
        return "0 (nuevo)"
    if a <= 5:
        return "1-5 anos"
    if a <= 10:
        return "6-10 anos"
    if a <= 20:
        return "11-20 anos"
    if a <= 30:
        return "21-30 anos"
    if a <= 40:
        return "31-40 anos"
    return "40+ anos"

df["age_group"] = df["antiquity_clean"].apply(age_group)

age_stats = df.groupby("age_group").agg(
    n=("valor_m2", "count"),
    vm2_med=("valor_m2", "median"),
    vm2_mean=("valor_m2", "mean"),
    m2_med=("m2", "median"),
).sort_values("vm2_med", ascending=False)

print("\n%-15s %5s %8s %8s %8s" % ("Age Group", "n", "vm2_med", "vm2_mean", "m2_med"))
print("-" * 50)
for ag, row in age_stats.iterrows():
    print("%-15s %5d $%6.0f $%6.0f %6.0f" % (ag, row["n"], row["vm2_med"], row["vm2_mean"], row["m2_med"]))

# ════════════════════════════════════════════════════════════════════
# 2. HEDONIC WITH ANTiquity
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("2. HEDONIC: log(vm2) ~ m2 + dorms + lat + lon + antiquity")
print("=" * 70)

from sklearn.linear_model import LinearRegression
from scipy import stats

# Model WITHOUT antiquity (baseline)
df_h1 = df[["valor_m2", "m2", "dormitorios", "lat", "lon"]].dropna()
X1 = df_h1[["m2", "dormitorios", "lat", "lon"]].values
y1 = np.log(df_h1["valor_m2"].values)
m1 = LinearRegression().fit(X1, y1)
r2_1 = m1.score(X1, y1)

# Model WITH antiquity
df_h2 = df[["valor_m2", "m2", "dormitorios", "lat", "lon", "antiquity_clean"]].dropna()
X2 = df_h2[["m2", "dormitorios", "lat", "lon", "antiquity_clean"]].values
y2 = np.log(df_h2["valor_m2"].values)
m2 = LinearRegression().fit(X2, y2)
r2_2 = m2.score(X2, y2)

print("\nBaseline (sin antiquity): R2 = %.4f (n=%d)" % (r2_1, len(y1)))
print("Con antiquity:            R2 = %.4f (n=%d)" % (r2_2, len(y2)))
print("Delta R2:                 %.4f (%.1f%%)" % (r2_2 - r2_1, (r2_2/r2_1 - 1) * 100))

# Coefficients
n = len(y2)
k = X2.shape[1]
residuals = y2 - m2.predict(X2)
mse = np.sum(residuals**2) / (n - k - 1)
se = np.sqrt(mse * np.diag(np.linalg.inv(X2.T @ X2)))
t_stats = m2.coef_ / se
p_values = 2 * (1 - stats.t.cdf(np.abs(t_stats), df=n-k-1))

print("\nCoeficientes con antiquity:")
for fname, coef, pv in zip(["m2", "dormitorios", "lat", "lon", "antiquity"], m2.coef_, p_values):
    sig = "***" if pv < 0.001 else "**" if pv < 0.01 else "*" if pv < 0.05 else "ns"
    print("  %s: %.6f (p=%.4f) %s" % (fname, coef, pv, sig))

# Interpretation
ant_coef = m2.coef_[4]
print("\nInterpretacion:")
print("  Cada ano de antiguedad: %.2f%% en vm2" % (ant_coef * 100))
print("  Un depto de 30 anos vs nuevo: %.1f%%" % ((np.exp(ant_coef * 30) - 1) * 100))

# ════════════════════════════════════════════════════════════════════
# 3. RANDOM FOREST WITH ANTiquity
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("3. RANDOM FOREST CON ANTiquity")
print("=" * 70)

from sklearn.ensemble import RandomForestRegressor

# Without antiquity
df_rf1 = df[["valor_m2", "m2", "dormitorios", "lat", "lon"]].dropna()
X_rf1 = df_rf1.values
y_rf1 = df_rf1["valor_m2"].values
rf1 = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
rf1.fit(X_rf1, y_rf1)
r2_rf1 = rf1.score(X_rf1, y_rf1)

# With antiquity
df_rf2 = df[["valor_m2", "m2", "dormitorios", "lat", "lon", "antiquity_clean"]].dropna()
X_rf2 = df_rf2.values
y_rf2 = df_rf2["valor_m2"].values
rf2 = RandomForestRegressor(n_estimators=100, max_depth=10, random_state=42, n_jobs=-1)
rf2.fit(X_rf2, y_rf2)
r2_rf2 = rf2.score(X_rf2, y_rf2)

print("\nBaseline (sin antiquity): R2 = %.4f" % r2_rf1)
print("Con antiquity:            R2 = %.4f" % r2_rf2)
print("Delta R2:                 %.4f" % (r2_rf2 - r2_rf1))

feat_names = ["m2", "dormitorios", "lat", "lon", "antiquity"]
print("\nFeature Importance (con antiquity):")
for fname, imp in sorted(zip(feat_names, rf2.feature_importances_), key=lambda x: -x[1]):
    print("  %s: %.3f (%.1f%%)" % (fname, imp, imp * 100))

# ════════════════════════════════════════════════════════════════════
# 4. BY MACROZONA + AGE
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("4. VM2 BY MACROZONA + AGE GROUP")
print("=" * 70)

pivot = df[df["antiquity_valid"]].groupby(["macrozona", "age_group"]).agg(
    n=("valor_m2", "count"),
    vm2_med=("valor_m2", "median"),
).reset_index()

for mz in pivot["macrozona"].unique():
    mz_data = pivot[pivot["macrozona"] == mz].sort_values("vm2_med", ascending=False)
    if mz_data["n"].sum() < 20:
        continue
    print("\n  %s:" % mz)
    for _, row in mz_data.iterrows():
        if row["n"] >= 5:
            print("    %-15s n=%4d vm2=$%.0f" % (row["age_group"], row["n"], row["vm2_med"]))

print("\nDONE")
