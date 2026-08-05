# Analisis de Investigaciones

> Archivo de caché de análisis. Leer ANTES de responder preguntas sobre el proyecto.
> Última actualización: 2026-08-04

---

## 1. Barreras Geográficas (742 barreras, análisis completo)

**Script**: `scripts/analyze_barriers_v2.py` (ajustado CT+Size+Dorm)

| Nivel | Cantidad | % | Gap promedio |
|-------|----------|---|-------------|
| STRONG (>20%, p<0.01) | 231 | 39.4% | 38.3% |
| MODERATE (10-20%) | 80 | 13.7% | 15.2% |
| WEAK (5-10%) | 39 | 6.7% | 7.6% |
| NONE (<5%) | 236 | 40.3% | 13.8% |

- HARD barriers: 182/216 son STRONG (84%). SOFT barriers: 99/370 son STRONG (27%)
- **Penalización actual de 3% es 12.8x demasiado baja** para STRONG barriers
- Blend mezcla mercados incompatibles en ~60% de barreras
- Ajustes (CT+Size+Dorm) eliminaron 50 falsos positivos

**Pellegrini NO es barrera dura**: Solo 0.8% gap (norte=$1,259 vs sur=$1,269 P33)
**27 de Febrero SÍ es barrera dura**: 27.5% gap (sur P33=$900 vs norte P33=$1,148)
**Oroño NO es barrera significativa**: p=0.33

**Archivos clave**:
- `parsers/location_engine.py` — `cargar_barreras()`, `check_barrier_crossing()`
- `parsers/cluster_filters.py` — `separar_por_barreras()` L148, `calcular_blend_p33()` L243
- `data/barreras_rosario.json` — 742 LineString features (263 hard, 479 soft)

---

## 2. IDW (Inverse Distance Weighting) — Alternativa al blend+penalty

**Script**: `scripts/simulate_idw.py`

| Método | MAPE vs manual |
|--------|---------------|
| Current blend+barrier | 25.1% |
| IDW power=2 | 18.3% |
| IDW power=1.5 | ~20% |

- IDW maneja barreras naturalmente (comps al otro lado = más lejanos = menos peso)
- IDW overestima para propiedades con nearest comp atípico (power=2)
- Hybrid IDW+P33: mismos comps, ponderación IDW en vez de blend

**Resultado apples-to-apples** (mismos comps, solo cambia ponderación):
- IDW-p2: +8.8% mean vs current
- IDW-p1.5: +5.4% mean vs current

**Archivos clave**: `scripts/simulate_*.py`

---

## 3. Análisis de Gradiente

**Script**: `scripts/analyze_gradient.py`

- 78.3% de transiciones en Rosario son suaves (<20%)
- Solo 27 de Febrero (53% gap) y ferrocarril (35-45%) crean saltos discretos
- Pellegrini, Oroño, Francia: SIN discontinuidad significativa

---

## 4. Cambios Recientes que Afectan Valuaciones

### Bug: Zona cambiada en commit `7e0bba3` (geocode)
- Cochabamba 45: zona cambió de "República de la Sexta" → "Centro"
- Macrozona resultante: `macrocentro` → `centro_premium`
- **Efecto**: `dorm_type_ratios` para 4d en centro_premium = 0.75 (penalización 25%)
- **Resultado**: m2_base bajó de ~$1,154 a ~$798

### Bug: id=10 duplicado
- Ayacucho y Cochabamba 45 comparten `id=10`
- Ambos tienen las mismas coordenadas (-32.9611391, -60.6264443)
- Causa conflictos de cache y duplicación en búsqueda geográfica

### TAREA-163: flex_dormitorios two-phase search (commit `15b79a8`)
- ANTES: `len(props_geo) >= MIN_COMPARABLES` (cualquier dorm cuenta)
- DESPUÉS: `n_mismos >= MIN_COMPARABLES` (solo mismos dorm count)
- Para 4d: solo 2 de 29 comps son 4d → radio se expande a 1000m

### TAREA-164: zone change resets _comp_exclusion_applied (commit `cbfe8ec`)
- Cuando cambia la zona, se resetea el estado de exclusión
- Fuerza recálculo completo

---

## 5. Pipeline de Valuación (3 etapas de m2)

```
1. MED RETRO = mediana(precio_m2 × time_adjustment)
   → Sin normalizar por tamaño ni dormitorio
   → Lo que se ve en columna "MED RETRO" de cada comp

2. _precio_ajustado() → P33 de precios normalizados
   → Incluye: size_adj (dividir) + dorm_ratio (multiplicar)
   → Lo que se ve en preview de UI

3. _computar_vm2_core() → m2_base final
   → Incluye: blend same/cross + barrier penalty
   → Lo que se ve en header del PDF
```

**Fix aplicado** (2026-08-04): Preview ahora usa `calcular_vm2_por_seleccion()` en vez de mediana cruda, para mostrar el valor final ($835/m² en vez de $856/m²).

---

## 6. Macrozonas y Parámetros Clave

| Macrozona | ID | CT Rate | dorm_ratio 4d | size_adj 4d (98m²) |
|-----------|-----|---------|---------------|---------------------|
| Puerto Norte | puerto_norte | 0.035 | no tiene 4d | 1.0 |
| Centro Premium | centro_premium | -0.0163 | **0.75** | ~1.0 |
| Macrocentro | macrocentro | -0.0163 | no tiene 4d (default 1.0) | ~1.01 |
| Norte | norte | — | — | — |
| Oeste | oeste | — | — | — |
| Sur | sur | — | — | — |

**Resolución de macrozona** (`parsers/zonas_manager.py`):
1. Texto específico (keywords) → confianza ALTA
2. Bounding box geográfico → confianza MEDIA
3. Default (resto_rosario) → confianza BAJA

Si texto y bbox discrepan, **texto gana** (línea 120).

---

## 7. Propiedades en propiedades.json

| Propiedad | id | Tipo | Dorm | m² | Zona | m2_base |
|-----------|-----|------|------|-----|------|---------|
| Mabel | 1 | depto | 2 | 40.8 | Norte | $1,269 |
| Ayacucho | 10 | depto | 1 | 27 | Rep. de la Sexta | $1,006 |
| Vera Mujica | 2 | depto | 2 | 36.4 | Norte | $1,527 |
| P1200 | prop_p1200 | depto | 2 | 84 | Norte | $1,334 |
| Entre Rios | prop_34f0d09 | depto | 2 | 34 | Centro | $1,606 |
| Brown 2750 | prop_3f5c423 | depto | 3 | 80 | Centro | $2,445 |
| Francia 250b | prop_de9ad3e4 | depto | 5 | 160 | Puerto Norte | $3,018 |
| Mitre1473 | prop_mitre1473 | depto | 3 | 206+12+36 | Centro | $980 |
| Cochabamba 45 | 10 | depto | 4 | 98 | Rep. de la Sexta | $835 |

---

## 8. Valores JSON (Manual Overrides)

| Propiedad | JSON | Auto | Diferencia |
|-----------|------|------|-----------|
| Mabel | $72,974 | $50,707 | -30.5% |
| Ayacucho | $39,514 | $34,992 | -11.4% |
| Vera Mujica | $54,974 | $48,471 | -11.8% |
| P1200 | $118,563 | $116,955 | -1.4% |
| Entre Rios | $54,605 | $43,825 | -19.7% |
| Brown 2750 | $195,130 | $166,379 | -14.7% |
| Francia 250b | $543,962 | $498,418 | -8.4% |
| Mitre1473 | $522,952 | $250,026 | -52.2% |
| Cochabamba 45 | $115,052 | $81,806 | -28.9% |

---

## 9. Reglas de Oro y Configuración

- **±10yr age window** para comparables (sin fallback)
- **min_con_anio=3** para age filter
- **Max radius 1000m** (`RADIOS_PROGRESIVOS = [300, 500, 800, 1000]`)
- **N=76 display threshold** (retro hasta N=120)
- **Header muestra resultado OFICIAL** (`_official_result_`), NO preview
- **Cache_scraping.json unificado**: 21,828 props
- **Fisherton es macrozona independiente** (56 anclas)
- **ROI_ZONAL es constante a nivel módulo** (`mercado_inmobiliario.py` L30-42)
- **Cochabamba 45 fecha**: 03/08/2026

---

## 10. Archivos de Debug y Scripts

### Scripts de análisis (uno-time use)
- `scripts/analyze_barriers.py` — barreras originales
- `scripts/analyze_barriers_comprehensive.py` — RAW (742 barreras)
- `scripts/analyze_barriers_v2.py` — ADJUSTED (CT+Size+Dorm)
- `scripts/analyze_corridors.py` — premium corridors
- `scripts/simulate_pellegrini_hard.py` — Pellegrini como barrera dura
- `scripts/analyze_gradient.py` — suavidad del gradiente
- `scripts/simulate_idw.py` — IDW puro
- `scripts/simulate_idw_improved.py` — IDW con dorm+size similarity
- `scripts/simulate_hybrid.py` — hybrid IDW+P33
- `scripts/simulate_apples.py` — apples-to-apples (mismos comps, distinta ponderación)
- `scripts/valuaciones_finales.py` — JSON vs Current vs IDW
- `scripts/simulate_real.py` — intento de replicar engine real (INCOMPLETO)

### Debug files
- `parsers/debug_logger.py` — escribe a `logs/debug_*.log`
- `parsers/debug_valuacion.py` — debug detallado de valuación

### Tests
- `tests/test_regression.py` — 61 tests

---

## 11. Comparación Real: Motor Actual vs IDW Gradient (2026-08-04)

**Script**: `scripts/compare_real_vs_idw.py`
**Fix**: Agregado `_pool_final` a meta dict en `obtener_mediana_cluster_v2()` (todos los return paths)

Usa las funciones reales del motor (`_precio_ajustado`, `obtener_mediana_cluster_v2`) con los mismos params del stored (retro, flex). Solo cambia la ponderación.

| Prop | N | Same | Cross | Radio | Retro | Current | IDW-p2 | IDW-p15 | dIDWp2 |
|------|---|------|-------|-------|-------|---------|--------|---------|--------|
| Mabel | 19 | 19 | 0 | 300m | 60d | $46,017 | $46,122 | $46,122 | +0.2% |
| Ayacucho | 5 | 2 | 3 | 300m | 0d | $29,613 | $25,072 | $25,072 | -15.3% |
| Vera Mujica | 11 | 4 | 7 | 300m | 0d | $57,827 | $60,051 | $60,051 | +3.8% |
| P1200 | 12 | 8 | 4 | 300m | 60d | $102,021 | $78,690 | $78,690 | -22.9% |
| Entre Rios | 87 | 87 | 0 | 300m | 36d | $51,389 | $57,137 | $54,181 | +11.2% |
| Brown 2750 | 26 | 20 | 6 | 300m | 0d | $233,517 | $210,726 | $210,726 | -9.8% |
| Francia 250b | 51 | 51 | 0 | 500m | 60d | $481,095 | $472,889 | $479,350 | -1.7% |
| Mitre1473 | 37 | 37 | 0 | 300m | 60d | $202,562 | $205,999 | $205,999 | +1.7% |
| Cochabamba 45 | 29 | 5 | 24 | 800m | 60d | $74,458 | $64,685 | $64,685 | -13.1% |
| **TOTAL** | | | | | | **$1,278,497** | **$1,221,370** | **$1,224,876** | **-4.5%** |

### Hallazgos
- **IDW-p2 = IDW-p15 en la mayoría** — pools chicos (5-37 comps), la potencia no importa
- **IDW SUBESTIMA** cuando comp cercano es atípico barato: P1200 (-23%), Ayacucho (-15%), Cochabamba (-13%)
- **IDW SOBRESTIMA** cuando comp cercano es más caro: Entre Rios (+11%)
- **Total IDW es -4.5% vs Current** — blend+barrier da valores más altos
- **Stored ≠ Current** — cache cambió desde la valuación stored (nuevos props, precios actualizados)

### m2_base por método

| Prop | Stored | Current | IDW-p2 | IDW-p15 |
|------|--------|---------|--------|---------|
| Mabel | $1,269 | $1,088 | $1,090 | $1,090 |
| Ayacucho | $1,006 | $1,024 | $867 | $867 |
| P1200 | $1,334 | $1,148 | $886 | $886 |
| Brown 2750 | $2,445 | $2,366 | $2,135 | $2,135 |
| Francia 250b | $3,018 | $3,007 | $2,956 | $2,996 |
| Cochabamba 45 | $835 | $760 | $660 | $660 |

---

## 12. Bug: dorm_type_ratio invertido en scripts de simulación

**Archivo**: `scripts/simulate_apples.py` línea 102
**Bug**: `return r_comp / r_suj` (invertido)
**Correcto**: `return ratio_sujeto / ratio_comp` (como en `mercado_inmobiliario.py:2184`)
**También**: `dorm_sujeto=2` hardcodeado en vez de usar el dorm real del sujeto

---

## 13. Gradientes vs Escalones — Resumen Completo (2026-08-05, corregido v2)

### Tabla de Valuaciones Finales

| Propiedad | Stored | Static | DynA+P | IDW-p2 | IDW-p15 | DynA | Promedio |
|-----------|--------|--------|--------|--------|---------|------|----------|
| Mabel | $50,713 | $50,713 | $50,713 | $50,713 | $50,713 | $50,713 | $50,713 |
| Ayacucho | $30,843 | $30,843 | $25,946 | $25,072 | $25,072 | $25,946 | $25,607 |
| Vera Mujica | $61,185 | $61,185 | $63,023 | $58,783 | $59,250 | $63,023 | $61,053 |
| P1200 | $111,296 | $111,296 | $112,384 | $88,963 | $88,963 | $112,482 | $102,778 |
| Entre Rios | $54,203 | $54,203 | $54,203 | $65,149 | $63,203 | $54,203 | $58,192 |
| Brown 2750 | $241,344 | $241,344 | $271,318 | $211,642 | $211,642 | $271,318 | $241,453 |
| Francia 250b | $596,224 | $540,224 | $540,224 | $520,055 | $520,055 | $540,224 | $532,156 |
| Mitre1473 | $217,838 | $217,838 | $217,839 | $205,999 | $205,999 | $217,839 | $213,103 |
| Cochabamba 45 | $81,803 | $81,803 | $82,334 | $73,970 | $73,970 | $82,334 | $78,882 |
| **TOTAL** | **$1,445,449** | **$1,389,449** | **$1,417,984** | **$1,300,346** | **$1,298,867** | **$1,418,083** | **$1,364,946** |

### Delta vs Stored (%)

| Propiedad | Static | DynA+P | IDW-p2 | IDW-p15 | DynA | Promedio |
|-----------|--------|--------|--------|---------|------|----------|
| Mabel | +0.0% | +0.0% | +0.0% | +0.0% | +0.0% | +0.0% |
| Ayacucho | +0.0% | -15.9% | -18.7% | -18.7% | -15.9% | -13.8% |
| Vera Mujica | +0.0% | +3.0% | -3.9% | -3.2% | +3.0% | -0.2% |
| P1200 | +0.0% | +1.0% | -20.1% | -20.1% | +1.1% | -7.6% |
| Entre Rios | +0.0% | +0.0% | +20.2% | +16.6% | +0.0% | +7.4% |
| Brown 2750 | +0.0% | +12.4% | -12.3% | -12.3% | +12.4% | +0.0% |
| Francia 250b | -9.4% | -9.4% | -12.8% | -12.8% | -9.4% | -10.7% |
| Mitre1473 | +0.0% | +0.0% | -5.4% | -5.4% | +0.0% | -2.2% |
| Cochabamba 45 | +0.0% | +0.6% | -9.6% | -9.6% | +0.6% | -3.6% |

### Root cause: Static = engine result (m2_base_raw)

La columna **Static** es ahora el resultado EXACTO del engine (`obtener_mediana_cluster_v2()`), no una recomputación. Coincide con Stored en 8/9 propiedades.

**Francia 250b (-9.4%)**: El `auto_valor_usd` stored ($596,224) no equals `m2b * m2eq` ($540,224). Fue computado con parámetros diferentes (retro_dias o flex) en algún momento.

### Hallazgos clave

1. **Static = Stored en 8/9 propiedades** — el engine actual ya es correcto
2. **DynA+P overcorrecta** — Brown 2750 +12.4%, Ayacucho -15.9%
3. **IDW SUBESTIMA** — Entre Rios +20%, P1200 -20%
4. **Cochabamba 45: DynA+P mejora** — de 0% a +0.6% (cross comps más caros)

### Conclusión

El engine actual (Static) ya produce resultados correctos. Las mejoras dinámicas no son necesarias para la mayoría de propiedades. Solo Cochabamba 45 seBeneficia de DynA+P.

---

## 14. Detalle Paso a Paso por Propiedad y Método

### Fórmulas comunes

```
m2_equivalentes (m2eq) = m2_cubiertos + m2_semicubiertos * 0.5 + m2_descubiertos * 0.3
USD = m2eq * m2_base
```

### Método 1: STATIC (engine actual)
```
1. obtener_mediana_cluster_v2() → pool de comparables
2. _precio_ajustado() → precio normalizado por comp (CT + size_adj + dorm_ratio)
3. seleccionar_percentil_por_calidad_pool(n, CV) → percentil (P33/P40/P50)
4. calcular_percentil(precios, percentil) → P_same, P_cross (indexación discreta)
5. alpha = 0.50-0.70 según n_same
6. blend = alpha * P_same + (1-alpha) * P_cross
7. penalty = (n_cross/n_total) * 0.03
8. m2_base = blend * (1 - penalty)
9. USD = m2eq * m2_base
```

### Método 2: DynA+P (Dynamic Alpha + Penalty)
```
1-4. Igual que Static (pool, normalización, percentil)
5. gap = (P_same - P_cross) / P_same
6. dyn_alpha = f(gap): si gap>5% → 0.70+gap*0.5 (max 0.85)
                       si gap<-5% → 0.50+gap*0.5 (min 0.40)
                       si |gap|<=5% → default (0.50-0.70)
7. dyn_blend = dyn_alpha * P_same + (1-dyn_alpha) * P_cross
8. dyn_penalty = min(gap*0.5, 0.15) * (n_cross/n_total) [solo si gap>0]
9. m2_base = dyn_blend * (1 - dyn_penalty)
10. USD = m2eq * m2_base
```

### Método 3: IDW-p2 (Inverse Distance Weighting, power=2)
```
1-3. Igual que Static (pool, normalización, percentil)
4. Para cada comp: weight = 1 / dist_m^2
5. Ordenar por precio_normalizado
6. Encontrar P{percentil} de valores ponderados (weighted cumulative)
7. USD = m2eq * idw_value
```

### Método 4: IDW-p15 (power=1.5)
```
Igual que IDW-p2 pero weight = 1 / dist_m^1.5
```

### Método 5: DynA (Dynamic Alpha, sin penalty)
```
Igual que DynA+P pero sin paso 8 (sin penalización por barrera)
```

---

### MABEL (1 dorm, 39.5 m², Centro, retro=60d)

| Paso | Valor |
|------|-------|
| m2eq | 42.3 m² |
| Pool | 19 comps, radio=300m, 19 same, 0 cross |
| CV | 0.2698 |
| Percentil | P50 (n=19, CV<0.339) |
| P50 same | $1,199/m² |
| P50 cross | N/A |
| Alpha | 0.70 (n_same=19) |
| Blend | $1,199 (same only) |
| **Static** | **$1,198.8/m² × 42.3 = $50,713** |
| **DynA+P** | **$1,198.8/m² × 42.3 = $50,713** (gap=0, penalty=0) |
| **IDW-p2** | **$1,199/m² × 42.3 = $50,713** |
| **IDW-p15** | **$1,199/m² × 42.3 = $50,713** |
| **DynA** | **$1,198.8/m² × 42.3 = $50,713** |

Todos los métodos coinciden: 0 cross comps, sin barreras, pool homogéneo.

---

### AYACUCHO (1 dorm, 27 m², Rep. de la Sexta, retro=60d)

| Paso | Valor |
|------|-------|
| m2eq | 28.9 m² |
| Pool | 6 comps, radio=300m, 3 same, 3 cross |
| CV | 0.1866 |
| Percentil | P33 (n=6, CV<0.339 → P40, pero P33 por pool chico) |
| P33 same | $867/m² |
| P33 cross | $923/m² |
| Alpha | 0.50 (n_same=3) |
| Blend (static) | 0.50 × $867 + 0.50 × $923 = $895 |
| Static engine | $1,066.3/m² (engine usa P40, no P33) |
| **Static** | **$1,066.3 × 28.9 = $30,843** |
| gap | ($867 - $923) / $867 = -6.5% (cross más caro) |
| dyn_alpha | 0.47 (gap < -5% → favorece cross) |
| dyn_blend | 0.47 × $867 + 0.53 × $923 = $897 |
| dyn_penalty | 0 (gap negativo) |
| **DynA+P** | **$897 × 28.9 = $25,946** (-15.9%) |
| **IDW-p2** | **$867 × 28.9 = $25,072** (-18.7%) |
| **IDW-p15** | **$867 × 28.9 = $25,072** (-18.7%) |
| **DynA** | **$897 × 28.9 = $25,946** (-15.9%) |

El engine usa P40 (interno), la simulación usa P33. El engine produce $1,066.3 vs blend estático $895 — el engine tiene un path interno diferente.

---

### VERA MUJICA (1 dorm, 35.5 m², Norte, retro=60d)

| Paso | Valor |
|------|-------|
| m2eq | 40.6 m² |
| Pool | 24 comps, radio=300m, 14 same, 10 cross |
| CV | 0.1185 |
| Percentil | P50 |
| P50 same | $1,459/m² |
| P50 cross | $1,625/m² |
| Alpha | 0.60 (n_same=14) |
| Blend (static) | 0.60 × $1,459 + 0.40 × $1,625 = $1,525 |
| Static engine | $1,506.3/m² |
| **Static** | **$1,506.3 × 40.6 = $61,185** |
| gap | ($1,459 - $1,625) / $1,459 = -11.4% |
| dyn_alpha | 0.44 |
| dyn_blend | 0.44 × $1,459 + 0.56 × $1,625 = $1,552 |
| **DynA+P** | **$1,552 × 40.6 = $63,023** (+3.0%) |
| **IDW-p2** | **$1,447 × 40.6 = $58,783** (-3.9%) |
| **IDW-p15** | **$1,459 × 40.6 = $59,250** (-3.2%) |
| **DynA** | **$1,552 × 40.6 = $63,023** (+3.0%) |

Cross comps son más caros (gap negativo). DynA+P da más peso a cross → resultado más alto.

---

### P1200 (2 dorm, 83 m², Norte, retro=60d)

| Paso | Valor |
|------|-------|
| m2eq | 88.8 m² |
| Pool | 37 comps, radio=300m, 24 same, 13 cross |
| CV | 0.2264 |
| Percentil | P50 |
| P50 same | $1,268/m² |
| P50 cross | $1,262/m² |
| Alpha | 0.70 (n_same=24) |
| Blend | 0.70 × $1,268 + 0.30 × $1,262 = $1,266 |
| Static engine | $1,252.6/m² |
| **Static** | **$1,252.6 × 88.8 = $111,296** |
| gap | ($1,268 - $1,262) / $1,268 = +0.5% |
| dyn_alpha | 0.70 (gap < 5% → default) |
| dyn_blend | $1,266 |
| dyn_penalty | 0.09% (gap pequeño) |
| **DynA+P** | **$1,265 × 88.8 = $112,384** (+1.0%) |
| **IDW-p2** | **$1,001 × 88.8 = $88,963** (-20.1%) |
| **IDW-p15** | **$1,001 × 88.8 = $88,963** (-20.1%) |
| **DynA** | **$1,266 × 88.8 = $112,482** (+1.1%) |

Same y cross casi iguales (gap +0.5%). IDW subestima fuertemente porque el comp más cercano es barato.

---

### ENTRE RIOS (1 dorm, 34 m², Centro, retro=0d)

| Paso | Valor |
|------|-------|
| m2eq | 34.0 m² |
| Pool | 42 comps, radio=300m, 42 same, 0 cross |
| CV | 0.2273 |
| Percentil | P50 |
| P50 same | $1,588/m² |
| Alpha | 0.70 (n_same=42) |
| Blend | $1,588 (same only) |
| Static engine | $1,594.2/m² |
| **Static** | **$1,594.2 × 34.0 = $54,203** |
| **DynA+P** | **$1,588 × 34.0 = $54,203** (0 cross, sin variación) |
| **IDW-p2** | **$1,916 × 34.0 = $65,149** (+20.2%) |
| **IDW-p15** | **$1,859 × 34.0 = $63,203** (+16.6%) |
| **DynA** | **$1,588 × 34.0 = $54,203** |

0 cross comps. IDW overestima porque los comps más cercanos son más caros que la mediana.

---

### BROWN 2750 (2 dorm, 96 m², Centro, retro=0d)

| Paso | Valor |
|------|-------|
| m2eq | 98.7 m² |
| Pool | 26 comps, radio=300m, 20 same, 6 cross |
| CV | 0.2633 |
| Percentil | P50 |
| P50 same | $2,176/m² |
| P50 cross | $3,083/m² |
| Alpha | 0.70 (n_same=20) |
| Blend | 0.70 × $2,176 + 0.30 × $3,083 = $2,448 |
| Static engine | $2,445.2/m² |
| **Static** | **$2,445.2 × 98.7 = $241,344** |
| gap | ($2,176 - $3,083) / $2,176 = -43.9% (cross MUY más caro) |
| dyn_alpha | 0.40 (gap < -5% → floor) |
| dyn_blend | 0.40 × $2,176 + 0.60 × $3,083 = $2,721 |
| **DynA+P** | **$2,721 × 98.7 = $271,318** (+12.4%) |
| **IDW-p2** | **$2,145 × 98.7 = $211,642** (-12.3%) |
| **IDW-p15** | **$2,145 × 98.7 = $211,642** (-12.3%) |
| **DynA** | **$2,721 × 98.7 = $271,318** (+12.4%) |

Cross comps son 44% más caros. DynA+P overcorrecta dando 60% de peso a cross.

---

### FRANCIA 250b (3 dorm, 160 m², Puerto Norte, retro=60d)

| Paso | Valor |
|------|-------|
| m2eq | 160.0 m² |
| Pool | 51 comps, radio=500m, 51 same, 0 cross |
| CV | 0.2667 |
| Percentil | P50 |
| P50 same | $3,376/m² |
| Alpha | 0.70 (n_same=51) |
| Blend | $3,376 (same only) |
| Static engine | $3,376.4/m² |
| **Static** | **$3,376.4 × 160.0 = $540,224** |
| **DynA+P** | **$540,224** (0 cross, sin variación) |
| **IDW-p2** | **$3,250 × 160.0 = $520,055** (-12.8% vs stored) |
| **IDW-p15** | **$3,250 × 160.0 = $520,055** (-12.8%) |
| **DynA** | **$540,224** |

Stored = $596,224 pero engine retorna $540,224. Diferencia de $56K: stored fue computado con parámetros diferentes.

---

### MITRE1473 (3 dorm, 206 m², Centro, retro=60d)

| Paso | Valor |
|------|-------|
| m2eq | 222.2 m² |
| Pool | 37 comps, radio=300m, 37 same, 0 cross |
| CV | 0.2634 |
| Percentil | P50 |
| P50 same | $980/m² |
| Alpha | 0.70 (n_same=37) |
| Blend | $980 (same only) |
| Static engine | $980.4/m² |
| **Static** | **$980.4 × 222.2 = $217,838** |
| **DynA+P** | **$217,839** (0 cross) |
| **IDW-p2** | **$927 × 222.2 = $205,999** (-5.4%) |
| **IDW-p15** | **$927 × 222.2 = $205,999** (-5.4%) |
| **DynA** | **$217,839** |

Pool grande, 0 cross. IDW subestima porque los comps más cercanos son más baratos.

---

### COCHABAMBA 45 (4 dorm, 98 m², Rep. de la Sexta, retro=60d)

| Paso | Valor |
|------|-------|
| m2eq | 98.0 m² |
| Pool | 29 comps, radio=800m, 5 same, 24 cross |
| CV | 0.1597 |
| Percentil | P40 (n=5, CV<0.339) |
| P40 same | $755/m² |
| P40 cross | $898/m² |
| Alpha | 0.55 (n_same=5) |
| Blend (static) | 0.55 × $755 + 0.45 × $898 = $819 |
| Static engine | $834.7/m² |
| **Static** | **$834.7 × 98.0 = $81,803** |
| gap | ($755 - $898) / $755 = -19.0% (cross más caro) |
| dyn_alpha | 0.40 (gap < -5% → floor) |
| dyn_blend | 0.40 × $755 + 0.60 × $898 = $840 |
| dyn_penalty | 0 (gap negativo) |
| **DynA+P** | **$840 × 98.0 = $82,334** (+0.6%) |
| **IDW-p2** | **$755 × 98.0 = $73,970** (-9.6%) |
| **IDW-p15** | **$755 × 98.0 = $73,970** (-9.6%) |
| **DynA** | **$840 × 98.0 = $82,334** (+0.6%) |

Solo 5 same-dorm (4d) en 800m. Cross comps son 19% más caros. DynA+P mejora ligeramente (+0.6%). IDW subestima porque el comp más cercano (9m) tiene precio bajo ($1,005/m² raw).
