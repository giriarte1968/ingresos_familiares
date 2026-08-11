import json
import sys
import os
import numpy as np
from collections import Counter

try:
    from scipy import stats
except ImportError:
    stats = None
    print("[WARN] scipy not available, will skip significance tests")

try:
    from sklearn.cluster import KMeans
    from sklearn.linear_model import LinearRegression
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    print("[WARN] sklearn not available, will skip ML analyses")

# ---------------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------------
BASE = r"C:\Users\Gustavo\ingresos_familiares_st"
OLD_PATH = os.path.join(BASE, "cache_scraping.json")
NEW_PATH = os.path.join(BASE, "cache_scraping_nuevo.json")
ZONAS_PATH = os.path.join(BASE, "data", "zonas_depreciacion.json")

# ---------------------------------------------------------------------------
# LOAD DATA
# ---------------------------------------------------------------------------
print("=" * 80)
print("ANALISIS COMPARATIVO: DEPARTAMENTOS - CACHE ANTIGUO vs NUEVO")
print("=" * 80)

with open(OLD_PATH, "r", encoding="utf-8") as f:
    old_data = json.load(f)
with open(NEW_PATH, "r", encoding="utf-8") as f:
    new_data = json.load(f)
with open(ZONAS_PATH, "r", encoding="utf-8") as f:
    zonas_json = json.load(f)

print(f"\nOLD file date: {old_data.get('fecha', 'N/A')}")
print(f"NEW file date: {new_data.get('fecha', 'N/A')}")
print(f"OLD total props: {len(old_data['propiedades'])}")
print(f"NEW total props: {len(new_data['propiedades'])}")

# ---------------------------------------------------------------------------
# FILTER: DEPARTAMENTOS ONLY
# ---------------------------------------------------------------------------
old_deps = [p for p in old_data["propiedades"] if p.get("tipo", "").lower() == "departamento"]
new_deps = [p for p in new_data["propiedades"] if p.get("tipo", "").lower() == "departamento"]

print(f"\nOLD departamentos: {len(old_deps)}")
print(f"NEW departamentos: {len(new_deps)}")

# Split by operacion
def by_op(deps, operacion):
    return [p for p in deps if p.get("operacion", "").lower() == operacion]

old_venta = by_op(old_deps, "venta")
new_venta = by_op(new_deps, "venta")
old_alq = by_op(old_deps, "alquiler")
new_alq = by_op(new_deps, "alquiler")

print(f"\nOLD venta: {len(old_venta)} | OLD alquiler: {len(old_alq)}")
print(f"NEW venta: {len(new_venta)} | NEW alquiler: {len(new_alq)}")

# ---------------------------------------------------------------------------
# HELPER: safe numeric arrays
# ---------------------------------------------------------------------------
def get_field(deps, field, exclude_zeros=False):
    vals = []
    for p in deps:
        v = p.get(field)
        if v is not None:
            try:
                v = float(v)
                if exclude_zeros and v == 0:
                    continue
                vals.append(v)
            except (ValueError, TypeError):
                pass
    return np.array(vals, dtype=float)

def stats_summary(arr, label=""):
    if len(arr) == 0:
        return {"label": label, "n": 0}
    return {
        "label": label,
        "n": len(arr),
        "mean": np.mean(arr),
        "median": np.median(arr),
        "std": np.std(arr, ddof=1) if len(arr) > 1 else 0,
        "min": np.min(arr),
        "max": np.max(arr),
        "p10": np.percentile(arr, 10),
        "p25": np.percentile(arr, 25),
        "p50": np.percentile(arr, 50),
        "p75": np.percentile(arr, 75),
        "p90": np.percentile(arr, 90),
    }

def print_stats(s):
    if s["n"] == 0:
        print(f"  {s['label']}: NO DATA")
        return
    print(f"  {s['label']}: n={s['n']}")
    print(f"    mean={s['mean']:.2f}  median={s['median']:.2f}  std={s['std']:.2f}")
    print(f"    min={s['min']:.2f}  max={s['max']:.2f}")
    print(f"    p10={s['p10']:.2f}  p25={s['p25']:.2f}  p50={s['p50']:.2f}  p75={s['p75']:.2f}  p90={s['p90']:.2f}")

# ===================================================================
# 1. BASIC STATS COMPARISON
# ===================================================================
print("\n" + "=" * 80)
print("1. BASIC STATS COMPARISON")
print("=" * 80)

for op_name, old_sub, new_sub in [("VENTA", old_venta, new_venta), ("ALQUILER", old_alq, new_alq)]:
    print(f"\n--- {op_name} ---")
    for field in ["precio", "m2", "valor_m2", "dormitorios"]:
        old_arr = get_field(old_sub, field, exclude_zeros=(field == "valor_m2"))
        new_arr = get_field(new_sub, field, exclude_zeros=(field == "valor_m2"))
        s_old = stats_summary(old_arr, f"OLD {field}")
        s_new = stats_summary(new_arr, f"NEW {field}")
        print_stats(s_old)
        print_stats(s_new)

        # T-test
        if stats and len(old_arr) > 1 and len(new_arr) > 1:
            try:
                t_stat, p_val = stats.ttest_ind(old_arr, new_arr, equal_var=False)
                sig = "***" if p_val < 0.001 else "**" if p_val < 0.01 else "*" if p_val < 0.05 else "ns"
                print(f"    t-test: t={t_stat:.4f}, p={p_val:.6f} {sig}")
            except Exception:
                pass
        print()

# ===================================================================
# 2. DISTRIBUTION ANALYSIS
# ===================================================================
print("\n" + "=" * 80)
print("2. DISTRIBUTION ANALYSIS (valor_m2 VENTA)")
print("=" * 80)

old_v2_venta = get_field(old_venta, "valor_m2", exclude_zeros=True)
new_v2_venta = get_field(new_venta, "valor_m2", exclude_zeros=True)

print(f"\nOLD valor_m2 venta: n={len(old_v2_venta)}")
print(f"NEW valor_m2 venta: n={len(new_v2_venta)}")

# Percentiles
for label, arr in [("OLD", old_v2_venta), ("NEW", new_v2_venta)]:
    if len(arr) == 0:
        continue
    pcts = [5, 10, 25, 50, 75, 90, 95]
    vals = np.percentile(arr, pcts)
    print(f"\n  {label} percentiles:")
    for p, v in zip(pcts, vals):
        print(f"    p{p}: {v:.2f}")

# IQR
for label, arr in [("OLD", old_v2_venta), ("NEW", new_v2_venta)]:
    if len(arr) < 4:
        continue
    q1, q3 = np.percentile(arr, [25, 75])
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    n_outliers = int(np.sum((arr < lower) | (arr > upper)))
    print(f"\n  {label} IQR: Q1={q1:.2f}, Q3={q3:.2f}, IQR={iqr:.2f}")
    print(f"    bounds: [{lower:.2f}, {upper:.2f}], outliers: {n_outliers} ({100*n_outliers/len(arr):.1f}%)")

# KS test
if stats and len(old_v2_venta) > 1 and len(new_v2_venta) > 1:
    ks_stat, ks_p = stats.ks_2samp(old_v2_venta, new_v2_venta)
    sig = "***" if ks_p < 0.001 else "**" if ks_p < 0.01 else "*" if ks_p < 0.05 else "ns"
    print(f"\n  KS test (OLD vs NEW valor_m2 venta): D={ks_stat:.4f}, p={ks_p:.6f} {sig}")

# ===================================================================
# 3. GEOGRAPHIC ANALYSIS - MACROZONAS
# ===================================================================
print("\n" + "=" * 80)
print("3. GEOGRAPHIC ANALYSIS BY MACROZONA")
print("=" * 80)

macrozonas = zonas_json["macrozonas"]

def assign_macrozona(lat, lon):
    if lat is None or lon is None:
        return "resto_rosario"
    for mz in macrozonas:
        bbox = mz.get("bbox")
        if bbox is None:
            continue
        if (bbox["lat_min"] <= lat <= bbox["lat_max"] and
            bbox["lon_min"] <= lon <= bbox["lon_max"]):
            return mz["id"]
    return "resto_rosario"

for op_name, old_sub, new_sub in [("VENTA", old_venta, new_venta), ("ALQUILER", old_alq, new_alq)]:
    print(f"\n--- {op_name} ---")
    old_mz_counts = Counter()
    new_mz_counts = Counter()
    old_mz_vals = {}
    new_mz_vals = {}

    for p in old_sub:
        mz = assign_macrozona(p.get("lat"), p.get("lon"))
        old_mz_counts[mz] += 1
        v = p.get("valor_m2")
        if v and float(v) > 0:
            old_mz_vals.setdefault(mz, []).append(float(v))

    for p in new_sub:
        mz = assign_macrozona(p.get("lat"), p.get("lon"))
        new_mz_counts[mz] += 1
        v = p.get("valor_m2")
        if v and float(v) > 0:
            new_mz_vals.setdefault(mz, []).append(float(v))

    all_mz = sorted(set(list(old_mz_counts.keys()) + list(new_mz_counts.keys())))
    for mz_id in all_mz:
        mz_name = mz_id
        for mz in macrozonas:
            if mz["id"] == mz_id:
                mz_name = mz["nombre"]
                break
        c_old = old_mz_counts.get(mz_id, 0)
        c_new = new_mz_counts.get(mz_id, 0)
        v_old = np.mean(old_mz_vals.get(mz_id, [0])) if mz_id in old_mz_vals else 0
        v_new = np.mean(new_mz_vals.get(mz_id, [0])) if mz_id in new_mz_vals else 0
        n_old = len(old_mz_vals.get(mz_id, []))
        n_new = len(new_mz_vals.get(mz_id, []))
        print(f"  {mz_name}:")
        print(f"    OLD: n={c_old} (con valor_m2: {n_old}), valor_m2_mean={v_old:.2f}")
        print(f"    NEW: n={c_new} (con valor_m2: {n_new}), valor_m2_mean={v_new:.2f}")
        if n_old > 1 and n_new > 1 and stats:
            try:
                t, p = stats.ttest_ind(old_mz_vals[mz_id], new_mz_vals[mz_id], equal_var=False)
                sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
                print(f"    t-test: t={t:.4f}, p={p:.6f} {sig}")
            except Exception:
                pass

# ===================================================================
# 4. ML ANALYSES
# ===================================================================
print("\n" + "=" * 80)
print("4. ML ANALYSES")
print("=" * 80)

if not HAS_SKLEARN:
    print("\n  [SKIP] sklearn not available")
else:
    # --- 4a. CLUSTERING ---
    print("\n--- 4a. K-MEANS CLUSTERING (venta, 4 clusters) ---")

    def build_feature_matrix(deps):
        X = []
        for p in deps:
            precio = p.get("precio", 0) or 0
            m2 = p.get("m2", 0) or 0
            vm2 = p.get("valor_m2", 0) or 0
            dorm = p.get("dormitorios", 0) or 0
            if precio > 0 and m2 > 0 and vm2 > 0:
                X.append([m2, precio, vm2, dorm])
        return np.array(X, dtype=float)

    X_old = build_feature_matrix(old_venta)
    X_new = build_feature_matrix(new_venta)

    if len(X_old) >= 4 and len(X_new) >= 4:
        scaler_old = StandardScaler()
        X_old_s = scaler_old.fit_transform(X_old)
        scaler_new = StandardScaler()
        X_new_s = scaler_new.fit_transform(X_new)

        km_old = KMeans(n_clusters=4, random_state=42, n_init=10)
        labels_old = km_old.fit_predict(X_old_s)

        km_new = KMeans(n_clusters=4, random_state=42, n_init=10)
        labels_new = km_new.fit_predict(X_new_s)

        feature_names = ["m2", "precio", "valor_m2", "dormitorios"]
        print("\n  OLD cluster centroids (scaled):")
        for i, c in enumerate(km_old.cluster_centers_):
            counts = int(np.sum(labels_old == i))
            print(f"    Cluster {i} (n={counts}): " + " ".join(f"{fn}={v:.4f}" for fn, v in zip(feature_names, c)))

        print("\n  NEW cluster centroids (scaled):")
        for i, c in enumerate(km_new.cluster_centers_):
            counts = int(np.sum(labels_new == i))
            print(f"    Cluster {i} (n={counts}): " + " ".join(f"{fn}={v:.4f}" for fn, v in zip(feature_names, c)))

        # Cluster size distribution
        print("\n  OLD cluster sizes:", dict(Counter(labels_old)))
        print("  NEW cluster sizes:", dict(Counter(labels_new)))
    else:
        print("  Not enough data for clustering")

    # --- 4b. REGRESSION ---
    print("\n--- 4b. LINEAR REGRESSION: precio ~ m2 + dormitorios + lat + lon ---")

    def build_regression(deps):
        X, y = [], []
        for p in deps:
            precio = p.get("precio", 0) or 0
            m2 = p.get("m2", 0) or 0
            dorm = p.get("dormitorios", 0) or 0
            lat = p.get("lat", 0) or 0
            lon = p.get("lon", 0) or 0
            if precio > 0 and m2 > 0 and lat != 0 and lon != 0:
                X.append([m2, dorm, lat, lon])
                y.append(precio)
        return np.array(X, dtype=float), np.array(y, dtype=float)

    X_old_r, y_old_r = build_regression(old_venta)
    X_new_r, y_new_r = build_regression(new_venta)

    reg_names = ["m2", "dormitorios", "lat", "lon"]
    for label, Xr, yr in [("OLD", X_old_r, y_old_r), ("NEW", X_new_r, y_new_r)]:
        if len(Xr) < 5:
            print(f"  {label}: not enough data for regression")
            continue
        scaler = StandardScaler()
        Xs = scaler.fit_transform(Xr)
        reg = LinearRegression()
        reg.fit(Xs, yr)
        r2 = reg.score(Xs, yr)
        print(f"\n  {label}: n={len(Xr)}, R²={r2:.4f}")
        for name, coef in zip(reg_names, reg.coef_):
            print(f"    {name}: {coef:.4f}")
        print(f"    intercept: {reg.intercept_:.4f}")

    # --- 4c. ANOMALY DETECTION ---
    print("\n--- 4c. ISOLATION FOREST ANOMALY DETECTION ---")

    def build_anomaly(deps):
        X = []
        for p in deps:
            precio = p.get("precio", 0) or 0
            m2 = p.get("m2", 0) or 0
            vm2 = p.get("valor_m2", 0) or 0
            if precio > 0 and m2 > 0 and vm2 > 0:
                X.append([m2, precio, vm2])
        return np.array(X, dtype=float)

    X_old_a = build_anomaly(old_venta)
    X_new_a = build_anomaly(new_venta)

    if len(X_old_a) >= 10 and len(X_new_a) >= 10:
        scaler = StandardScaler()
        X_old_as = scaler.fit_transform(X_old_a)
        X_new_as = scaler.transform(X_new_a)

        iso = IsolationForest(contamination=0.05, random_state=42)
        iso.fit(X_old_as)

        labels_old_a = iso.predict(X_old_as)
        labels_new_a = iso.predict(X_new_as)

        n_anom_old = int(np.sum(labels_old_a == -1))
        n_anom_new = int(np.sum(labels_new_a == -1))
        print(f"  OLD anomalies: {n_anom_old} ({100*n_anom_old/len(labels_old_a):.1f}%)")
        print(f"  NEW anomalies: {n_anom_new} ({100*n_anom_new/len(labels_new_a):.1f}%)")

        # Find anomalies in NEW that would NOT have been anomalous in OLD distribution
        # Use OLD scaler + OLD model for fair comparison
        iso_old = IsolationForest(contamination=0.05, random_state=42)
        iso_old.fit(X_old_as)
        labels_new_via_old = iso_old.predict(X_new_as)
        n_new_anom_via_old = int(np.sum(labels_new_via_old == -1))
        n_new_normal_via_old = int(np.sum(labels_new_via_old == 1))
        print(f"  NEW props flagged anomalous by OLD model: {n_new_anom_via_old} ({100*n_new_anom_via_old/len(labels_new_via_old):.1f}%)")
        print(f"  NEW props NORMAL by OLD model: {n_new_normal_via_old}")

        # Check if NEW anomalies are different from OLD anomaly profile
        anom_old_idx = set(np.where(labels_old_a == -1)[0])
        anom_new_via_old_idx = set(np.where(labels_new_via_old == -1)[0])

        if anom_old_idx and anom_new_via_old_idx:
            # Characterize old anomalies
            old_anom_vals = X_old_a[list(anom_old_idx)]
            new_anom_vals = X_new_a[list(anom_new_via_old_idx)]
            print(f"\n  OLD anomaly centroids:")
            print(f"    m2={np.mean(old_anom_vals[:,0]):.2f}, precio={np.mean(old_anom_vals[:,1]):.2f}, valor_m2={np.mean(old_anom_vals[:,2]):.2f}")
            print(f"  NEW anomaly centroids (via OLD model):")
            print(f"    m2={np.mean(new_anom_vals[:,0]):.2f}, precio={np.mean(new_anom_vals[:,1]):.2f}, valor_m2={np.mean(new_anom_vals[:,2]):.2f}")
    else:
        print("  Not enough data for anomaly detection")

    # --- 4d. TREND DETECTION ---
    print("\n--- 4d. DISTRIBUTION SHAPE ANALYSIS ---")

    from scipy.stats import skew, kurtosis as kurt_func

    for label, arr in [("OLD", old_v2_venta), ("NEW", new_v2_venta)]:
        if len(arr) < 4:
            continue
        cv = np.std(arr, ddof=1) / np.mean(arr) if np.mean(arr) != 0 else 0
        sk = skew(arr)
        ku = kurt_func(arr)
        print(f"  {label} valor_m2 venta: CV={cv:.4f}, skewness={sk:.4f}, kurtosis={ku:.4f}")

    # Also for precio
    old_p_venta = get_field(old_venta, "precio", exclude_zeros=True)
    new_p_venta = get_field(new_venta, "precio", exclude_zeros=True)
    for label, arr in [("OLD", old_p_venta), ("NEW", new_p_venta)]:
        if len(arr) < 4:
            continue
        cv = np.std(arr, ddof=1) / np.mean(arr) if np.mean(arr) != 0 else 0
        sk = skew(arr)
        ku = kurt_func(arr)
        print(f"  {label} precio venta: CV={cv:.4f}, skewness={sk:.4f}, kurtosis={ku:.4f}")

# ===================================================================
# 5. CT IMPACT ANALYSIS
# ===================================================================
print("\n" + "=" * 80)
print("5. CT IMPACT ANALYSIS")
print("=" * 80)

mean_old = np.mean(old_v2_venta) if len(old_v2_venta) > 0 else 0
mean_new = np.mean(new_v2_venta) if len(new_v2_venta) > 0 else 0
pct_change = ((mean_new - mean_old) / mean_old * 100) if mean_old != 0 else 0

print(f"\n  OLD mean valor_m2 venta: {mean_old:.2f}")
print(f"  NEW mean valor_m2 venta: {mean_new:.2f}")
print(f"  Change: {pct_change:+.2f}%")

if pct_change > 0:
    print(f"  -> Market APPRECIATION detected. CT rate might need downward adjustment.")
    # Estimate adjustment needed: if CT was calibrated at mean_old, new mean suggests
    # properties are worth more, so CT rate could be lower
    est_adj = 1.0 / (1 + pct_change / 100)
    print(f"  -> Estimated CT adjustment factor: {est_adj:.4f} (multiply current rate)")
elif pct_change < 0:
    print(f"  -> Market DEPRECIATION detected. CT rate might need upward adjustment.")
    est_adj = 1.0 / (1 + pct_change / 100)
    print(f"  -> Estimated CT adjustment factor: {est_adj:.4f} (multiply current rate)")
else:
    print(f"  -> No change detected.")

# Per macrozona CT impact
print("\n  Per-macrozona CT impact:")
for mz in macrozonas:
    mz_id = mz["id"]
    old_arr = []
    new_arr = []
    for p in old_venta:
        if assign_macrozona(p.get("lat"), p.get("lon")) == mz_id:
            v = p.get("valor_m2")
            if v and float(v) > 0:
                old_arr.append(float(v))
    for p in new_venta:
        if assign_macrozona(p.get("lat"), p.get("lon")) == mz_id:
            v = p.get("valor_m2")
            if v and float(v) > 0:
                new_arr.append(float(v))

    if len(old_arr) >= 5 and len(new_arr) >= 5:
        m_old = np.mean(old_arr)
        m_new = np.mean(new_arr)
        pct = ((m_new - m_old) / m_old * 100)
        direction = "APPRECIATION" if pct > 0 else "DEPRECIATION"
        print(f"    {mz['nombre']}: OLD={m_old:.2f}, NEW={m_new:.2f}, change={pct:+.2f}% ({direction})")
    else:
        print(f"    {mz['nombre']}: insufficient data (old={len(old_arr)}, new={len(new_arr)})")

# ===================================================================
# 6. VOLUME ADJUSTMENT IMPACT
# ===================================================================
print("\n" + "=" * 80)
print("6. VOLUME ADJUSTMENT IMPACT")
print("=" * 80)

old_m2_v = get_field(old_venta, "m2", exclude_zeros=True)
new_m2_v = get_field(new_venta, "m2", exclude_zeros=True)

print("\n--- M2 Distribution (venta) ---")
for label, arr in [("OLD", old_m2_v), ("NEW", new_m2_v)]:
    s = stats_summary(arr, label)
    print_stats(s)

if stats and len(old_m2_v) > 1 and len(new_m2_v) > 1:
    t, p = stats.ttest_ind(old_m2_v, new_m2_v, equal_var=False)
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
    print(f"  t-test (m2): t={t:.4f}, p={p:.6f} {sig}")

    ks, kp = stats.ks_2samp(old_m2_v, new_m2_v)
    sig = "***" if kp < 0.001 else "**" if kp < 0.01 else "*" if kp < 0.05 else "ns"
    print(f"  KS-test (m2): D={ks:.4f}, p={kp:.6f} {sig}")

print("\n--- Dormitorios Distribution (venta) ---")
old_d_v = get_field(old_venta, "dormitorios", exclude_zeros=True)
new_d_v = get_field(new_venta, "dormitorios", exclude_zeros=True)

for label, arr in [("OLD", old_d_v), ("NEW", new_d_v)]:
    s = stats_summary(arr, label)
    print_stats(s)

if stats and len(old_d_v) > 1 and len(new_d_v) > 1:
    t, p = stats.ttest_ind(old_d_v, new_d_v, equal_var=False)
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
    print(f"  t-test (dormitorios): t={t:.4f}, p={p:.6f} {sig}")

# Frequency distribution
old_d_freq = Counter(int(d) for d in old_d_v)
new_d_freq = Counter(int(d) for d in new_d_v)
all_d = sorted(set(list(old_d_freq.keys()) + list(new_d_freq.keys())))
print("\n  Dormitorios frequency:")
print(f"    {'dorm':>6} {'OLD_n':>8} {'OLD_%':>8} {'NEW_n':>8} {'NEW_%':>8}")
for d in all_d:
    oc = old_d_freq.get(d, 0)
    nc = new_d_freq.get(d, 0)
    op = 100 * oc / len(old_d_v) if len(old_d_v) > 0 else 0
    np_ = 100 * nc / len(new_d_v) if len(new_d_v) > 0 else 0
    print(f"    {d:>6} {oc:>8} {op:>7.1f}% {nc:>8} {np_:>7.1f}%")

# Size bins
m2_bins = [0, 35, 50, 70, 100, 150, 999]
m2_labels = ["<35m2", "35-50m2", "50-70m2", "70-100m2", "100-150m2", ">150m2"]
print("\n  M2 size distribution (venta):")
print(f"    {'bin':>12} {'OLD_n':>8} {'OLD_%':>8} {'NEW_n':>8} {'NEW_%':>8}")
for i in range(len(m2_bins) - 1):
    lo, hi = m2_bins[i], m2_bins[i + 1]
    oc = int(np.sum((old_m2_v >= lo) & (old_m2_v < hi)))
    nc = int(np.sum((new_m2_v >= lo) & (new_m2_v < hi)))
    op = 100 * oc / len(old_m2_v) if len(old_m2_v) > 0 else 0
    np_ = 100 * nc / len(new_m2_v) if len(new_m2_v) > 0 else 0
    print(f"    {m2_labels[i]:>12} {oc:>8} {op:>7.1f}% {nc:>8} {np_:>7.1f}%")

# ===================================================================
# 7. ZONE SHIFT ANALYSIS
# ===================================================================
print("\n" + "=" * 80)
print("7. ZONE SHIFT ANALYSIS")
print("=" * 80)

old_lats = get_field(old_deps, "lat", exclude_zeros=True)
new_lats = get_field(new_deps, "lat", exclude_zeros=True)
old_lons = get_field(old_deps, "lon", exclude_zeros=True)
new_lons = get_field(new_deps, "lon", exclude_zeros=True)

print("\n--- Latitude distribution (all departamentos) ---")
for label, arr in [("OLD", old_lats), ("NEW", new_lats)]:
    s = stats_summary(arr, label)
    print_stats(s)

print("\n--- Longitude distribution (all departamentos) ---")
for label, arr in [("OLD", old_lons), ("NEW", new_lons)]:
    s = stats_summary(arr, label)
    print_stats(s)

if stats and len(old_lats) > 1 and len(new_lats) > 1:
    t, p = stats.ttest_ind(old_lats, new_lats, equal_var=False)
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
    print(f"  t-test (lat): t={t:.4f}, p={p:.6f} {sig}")

    t, p = stats.ttest_ind(old_lons, new_lons, equal_var=False)
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
    print(f"  t-test (lon): t={t:.4f}, p={p:.6f} {sig}")

# Zone concentration
print("\n--- Macrozona concentration (departamentos, venta) ---")
old_mz_c = Counter()
new_mz_c = Counter()
for p in old_venta:
    mz = assign_macrozona(p.get("lat"), p.get("lon"))
    old_mz_c[mz] += 1
for p in new_venta:
    mz = assign_macrozona(p.get("lat"), p.get("lon"))
    new_mz_c[mz] += 1

all_mz = sorted(set(list(old_mz_c.keys()) + list(new_mz_c.keys())))
total_old = sum(old_mz_c.values()) or 1
total_new = sum(new_mz_c.values()) or 1

print(f"  {'Macrozona':<25} {'OLD_n':>8} {'OLD_%':>8} {'NEW_n':>8} {'NEW_%':>8} {'shift':>8}")
for mz_id in all_mz:
    mz_name = mz_id
    for mz in macrozonas:
        if mz["id"] == mz_id:
            mz_name = mz["nombre"]
            break
    oc = old_mz_c.get(mz_id, 0)
    nc = new_mz_c.get(mz_id, 0)
    op = 100 * oc / total_old
    np_ = 100 * nc / total_new
    shift = np_ - op
    print(f"  {mz_name:<25} {oc:>8} {op:>7.1f}% {nc:>8} {np_:>7.1f}% {shift:>+7.1f}%")

print("\n" + "=" * 80)
print("END OF ANALYSIS")
print("=" * 80)
