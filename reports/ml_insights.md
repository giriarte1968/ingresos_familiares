# ML Insights Report

> Generado: análisis sobre 8,368 ventas del cache_scraping.json
> Fecha: 2026-06-04

## Resumen Ejecutivo

| Análisis | Hallazgo Clave |
|---|---|
| **DBSCAN geo** | centro_premium es 97% homogéneo (1 cluster). macrocentro tiene 41 clusters → diverso. |
| **Hedonic** | R²=0.195. Puerto Norte: +47% sobre Centro (p=0.022). "Otro": -24% (p=0.009). |
| **XGBoost** | R²=0.839. **lat+lon = 80% de importancia**. m²=15.5%. dorms=2.8%. Zona labels: <0.5%. |
| **Anomalías** | 168 outliers (2%). Todos en zona "Otro". Mayormente propiedades con m² extremos. |

---

## 1. DBSCAN Geo-Clustering (eps=127m, min_samples=5)

**151 clusters naturales**, 13.4% noise.

### Coincidencia con nuestras macrozonas:

| Macrozona | n | Top cluster | % en top cluster | Clusters dentro |
|---|---|---|---|---|
| centro_premium | 4,309 | 0 | **97.1%** | 6 |
| macrocentro | 1,627 | 0 | 57.2% | **41** |
| norte | 1,326 | 1 | 9.6% | **63** |
| sur_default | 571 | 51 | 5.4% | 29 |
| oeste | 530 | 20 | 14.3% | 28 |

### Clusters destacados (top 10 por tamaño):

| Cluster | n | vm2_med | Lat | Lon | Macro |
|---|---|---|---|---|---|
| 0 | 5,116 | $1,700 | -32.95 | -60.65 | centro_premium |
| 1 | 143 | $938 | -32.92 | -60.68 | norte |
| 14 | 41 | **$2,531** | -32.93 | -60.66 | centro_premium |
| 17 | 23 | **$2,600** | -32.92 | -60.67 | centro_premium |
| 16 | 30 | $2,161 | -32.91 | -60.68 | norte |
| 51 | 34 | $739 | -32.98 | -60.65 | sur_default |
| 25 | 40 | $749 | -32.95 | -60.68 | macrocentro |

### Interpretación:
- **centro_premium** está bien definido: 97% en cluster 0. La bbox es correcta.
- **macrocentro** es heterogéneo: 41 sub-clusters. La bbox actual agrupa zonas con precios muy distintos. Considerar subdividir.
- **Puerto Norte** aparece como clusters 14 ($2,531/m²) y 17 ($2,600/m²) → consistente con nuestra clasificación premium.

---

## 2. Hedonic Regression (OLS)

**Modelo:** log(valor_m2) ~ m2 + dorms + zona + lat + lon + lat*lon

**R² = 0.195** — bajo, porque el modelo lineal no captura la complejidad espacial.

### Coeficientes significativos:

| Feature | Coef | p-value | Interpretación |
|---|---|---|---|
| dormitorios | -0.018 | 0.004 | Cada dorm adicional: -1.8% en $/m² |
| zona_Otro | -0.276 | 0.009 | "Otro" vale 24% menos que Centro (referencia) |
| **zona_Puerto Norte** | **+0.388** | **0.022** | **Puerto Norte vale 47% más que Centro** |
| lat | +5755 | 0.000 | Efecto latitudinal fuerte |
| lon | +3126 | 0.000 | Efecto longitudinal fuerte |

### Premium por zona (vs Centro):

| Zona | Premium % | Significancia |
|---|---|---|
| **Puerto Norte** | **+47.5%** | * (p=0.02) |
| Sexta | +9.5% | ns |
| Pellegrini | +7.3% | ns |
| Centro | ref | — |
| Pichincha | -11.4% | ns |
| Martin | -14.7% | ns |
| Otro | -24.1% | ** (p=0.009) |
| Facultades | -35.8% | ns (n=1) |

---

## 3. XGBoost + SHAP (modelo no-lineal)

**R² = 0.839** — 84% de la varianza explicada. Mucho mejor que hedonic.

### Feature Importance:

| Feature | Importancia | SHAP mean |
|---|---|---|
| **lat** | **0.443 (44%)** | **317** |
| **lon** | **0.361 (36%)** | **369** |
| m² | 0.155 (16%) | 136 |
| dormitorios | 0.028 (3%) | 43 |
| zona_Otro | 0.004 | 7 |
| zona_Puerto Norte | 0.004 | 1 |

**Ubicación (lat+lon) explica el 80%** del precio. m² solo 16%, dormitorios 3%. Las etiquetas de zona aportan ruido (0.4%).

### Dependencia parcial (m² controlando ubicación):

| m² | Predicción media | vs 50m² |
|---|---|---|
| 50 | **$1,460/m²** | — |
| 100 | **$1,398/m²** | -4.2% |
| 200 | **$1,173/m²** | -19.7% |

→ **Size discount confirmado**: el doble de m² no duplica el precio.

---

## 4. Anomaly Detection (Isolation Forest)

**168 outliers** (2% del total). Todos en zona "Otro".

### Más sobrevalorados (overpriced):

| m² | vm2 | Esperado | Ratio |
|---|---|---|---|
| 75 | $3,000 | $1,735 | 1.73× |
| 175 | $1,600 | $1,134 | 1.41× |
| 500 | $2,000 | $1,496 | 1.34× |

### Más subvalorados (underpriced):

| m² | vm2 | Esperado | Ratio |
|---|---|---|---|
| 310 | $419 | $889 | 0.47× |
| 233 | $416 | $861 | 0.48× |
| 384 | $518 | $968 | 0.54× |

→ Los outliers son propiedades atípicas en m² (310, 384, 500m²). Posibles terrenos, locales comerciales, o errores de carga.

---

## 5. Acciones Recomendadas

| # | Acción | Basado en | Prioridad |
|---|---|---|---|
| 1 | **Mantener bbox centro_premium** | DBSCAN: 97% homogéneo | ✅ |
| 2 | **Revisar bbox macrocentro** — tiene 41 sub-clusters con precios dispares | DBSCAN | Media |
| 3 | **Reducir peso de dorms en f_dict** — XGBoost dice 3% | XGBoost SHAP | Media |
| 4 | **No usar zona label como feature fuerte** — 0.4% importance vs lat/lon 80% | XGBoost | Alta |
| 5 | **Calibrar size discount** — 50→200m²: -20% en $/m² | XGBoost dep. parcial | Alta |
| 6 | **Mantener Puerto Norte premium en factores** (+47% confirmado) | Hedonic | ✅ |
| 7 | **Revisar el ~2% de outliers** — posible ruido en datos de entrada | Isolation Forest | Baja |
