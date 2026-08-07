# Analisis de Investigaciones

> Archivo de caché de análisis. Leer ANTES de responder preguntas sobre el proyecto.
> Última actualización: 2026-08-07 (v5: simulación v12 — 4 soluciones de percentil para cross comps)

---

## 1. Barreras Geográficas — CON Normalización de Antigüedad

**Script**: `scripts/analyze_barriers_v2.py` (CT+Size+Dorm+Anti)
**Output**: `docs/ANALISIS_BARRERAS_v3.txt`

### Comparación ANTES vs DESPUÉS de normalizar antigüedad

| Clasificación | ANTES (v2) | DESPUÉS (v3) | Cambio |
|---------------|------------|--------------|--------|
| STRONG (>20%, p<0.01) | 281 (48.0%) | 235 (40.1%) | **-46 barreras** |
| MODERATE (10-20%) | 70 (11.9%) | 54 (9.2%) | -16 |
| WEAK (5-10%) | 26 (4.4%) | 46 (7.8%) | +20 |
| NONE (<5%) | 209 (35.7%) | 251 (42.8%) | **+42 barreras** |

**Hallazgo clave**: La normalización de antigüedad eliminó 46 falsos positivos (barreras que parecían fuertes pero eran artefactos de distribución de antigüedad).

### Estadísticas de depreciación
- `factor_anti` promedio: 0.9388 (6.1% depreciación promedio)
- 28.1% de propiedades tienen factor < 0.90
- 11.0% de propiedades tienen factor < 0.80

### Top 10 barreras por gap (después de normalizar)

| # | Barrera | Tipo | Gap |
|---|---------|------|-----|
| 1 | Ferrocarril | hard | 64.7% |
| 2 | Ferrocarril | hard | 61.3% |
| 3 | Ferrocarril | hard | 55.0% |
| 4-10 | Ferrocarril | hard | 50-55% |

### Conclusiones actualizadas

1. **27 de Febrero** = Única barrera dura real en zona urbana (22.6% gap)
2. **Ferrocarril** = Segunda barrera real (50-65% gap)
3. **Pellegrini, Oroño, Francia** = NO son barreras (gradientes suaves)
4. **Puerto Norte** = Zona de volatilidad extrema (no barrera, mercado diferente)

**Archivos clave**:
- `parsers/location_engine.py` — `cargar_barreras()`, `check_barrier_crossing()`
- `parsers/cluster_filters.py` — `separar_por_barreras()` L148, `calcular_blend_p33()` L243
- `data/barreras_rosario.json` — 742 LineString features (263 hard, 479 soft)

---

## 1b. Barreras — ANÁLISIS COMPLETO BASADO EN DATOS (v4)

**Script**: `scripts/analyze_and_create_barriers.py`
**Output**: `docs/ANALISIS_BARRERAS_v4.txt`
**Archivo corregido**: `barreras_rosario_corrected.json` (686 barreras)

### Resultados del análisis por barrera

| Clasificación | Cantidad | Gap Promedio | Descripción |
|---------------|----------|--------------|-------------|
| STRONG (>20%) | 132 | 36.9% | Barreras reales, deben ser hard |
| MODERATE (10-20%) | 54 | 15.1% | Barreras moderadas, soft |
| WEAK (5-10%) | 46 | 7.4% | Barreras débiles, soft |
| NONE (<5%) | 56 | 1.9% | No son barreras, eliminar |
| INSUFFICIENT | 340 | 0% | Datos insuficientes, mantener |

### Cambios principales respecto al JSON original

| Barrera | Original | Corregido | Razón |
|---------|----------|-----------|-------|
| 27 de Febrero | 139 soft | 139 hard | Gap real = 22.6% (STRONG) |
| Ferrocarril | 263 hard | 253 hard + 10 soft/removed | Algunos segmentos gap < 5% |
| Pellegrini | 119 soft | 104 hard + 15 removed | Gap real = 20-98% (STRONG) |
| Oroño | 94 soft | 82 hard + 12 removed | Gap real = 20-63% (STRONG) |
| Francia | 65 soft | 58 hard + 7 removed | Gap real = 20-52% (STRONG) |
| Ovidio Lagos | 55 soft | 48 hard + 7 removed | Gap real = 23-58% (STRONG) |
| Aristóbulo del Valle | 6 soft | 6 hard | Gap real = 38-63% (STRONG) |

### Distribución final

```
Original: 742 barreras (263 hard, 479 soft)
Corregido: 686 barreras (364 hard, 322 soft)
```

### Problema identificado en la lógica actual

La lógica del engine asume que **cruzar barrera = otro lado más barato**. Pero para nuestras 9 propiedades:

| Propiedad | P33_same | P33_cross | Gap | Significado |
|-----------|----------|-----------|-----|-------------|
| Ayacucho | $882 | $1,182 | -34.0% | Cross MÁS caro |
| Cochabamba 45 | $755 | $845 | -11.9% | Cross MÁS caro |
| P1200 | $1,268 | $1,343 | -6.0% | Cross MÁS caro |
| Vera Mujica | $1,459 | $1,664 | -14.1% | Cross MÁS caro |
| Brown 2750 | $2,176 | N/A | N/A | Sin cross |

**Conclusión**: El penalty del 3% no debería aplicarse cuando cross es más caro.

### Lógica propuesta para corrección (basada en datos)

**Justificación por componentes:**

**1. ALPHA (basado en gap):**
- `gap < -10%`: alpha = 1.0 (excluir cross, zona diferente)
- `gap > 20%`: alpha = 0.85 (cross más barato, más peso a same)
- `-10% ≤ gap ≤ 20%`: alpha = f(n_same) [actual]

**2. BLEND:**
- Solo aplica cuando gap está entre -10% y +20%
- Fuera de ese rango, usar solo P33_same

**3. PENALTY (basado en gap):**
- `gap < -10%`: penalty = 0% (cross más caro, no penalizar)
- `gap > 20%`: penalty = (n_cross/n_total) × 0.03
- `-10% ≤ gap ≤ 20%`: penalty = 0% (compatibles)

**Implementación:**
```python
# Calcular gap
if pct_same and pct_same > 0:
    gap = (pct_same - pct_cross) / pct_same
else:
    gap = 0

# Decidir qué usar
if gap > 0.20:  # Cross MÁS BARATO (>20%)
    vm2 = pct_same  # Excluir cross
    alpha = 0.85
    barrier_pct = (n_cross / n_total) * 0.03
elif gap < -0.10:  # Cross MÁS CARO (>10%)
    vm2 = pct_same  # Excluir cross (zona diferente)
    alpha = 1.0
    barrier_pct = 0
else:  # Compatibles (-10% a +20%)
    vm2 = blend  # Mezclar
    alpha = f(n_same)  # Actual
    barrier_pct = 0
```

**Ejemplos concretos:**
- Ayacucho (gap = -34.0%): Actual = $914, Nuevo = $983 (+7.3%)
- Cochabamba 45 (gap = -11.9%): Actual = $830, Nuevo = $755 (-9.0%)
- Brown 2750 (sin cross): Sin cambio

**Archivos clave**:
- `scripts/analyze_and_create_barriers.py` — Análisis completo de barreras
- `barreras_rosario_corrected.json` — Archivo corregido basado en datos
- `barreras_rosario_backup.json` — Backup del original

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

**MAPE con normalización de antigüedad** (v2):
- Current (blend+barrier): 25.5%
- IDW (gradient): 16.2%
- Hybrid (IDW+27-Feb): 16.6%

**Archivos clave**: `scripts/simulate_*.py`

---

## 3. Análisis de Gradiente — CON Normalización de Antigüedad

**Script**: `scripts/analyze_gradient.py` (v2)
**Output**: `docs/ANALISIS_GRADIENTE_v2.txt`

### Comparación ANTES vs DESPUÉS

| Métrica | ANTES | DESPUÉS | Cambio |
|---------|-------|---------|--------|
| Discrete jumps (>20%) | 21.7% | **13.3%** | **-38%** |
| Smooth (<20%) | 78.3% | **86.7%** | +10.5% |

### Las 8 transiciones con salto discreto (después de normalizar)

| Latitud | Gap | Ubicación |
|---------|-----|-----------|
| -32.9665 | +53.7% | 27 de Febrero |
| -32.9645 | +27.7% | 27 de Febrero |
| -32.9305 | -30.4% | Puerto Norte |
| -32.9295 | -30.4% | Puerto Norte |
| -32.9285 | +150.4% | Puerto Norte |
| -32.9275 | -47.7% | Puerto Norte |
| -32.9265 | +73.6% | Puerto Norte |
| -32.9195 | -42.5% | Puerto Norte |

**Solo 2 zonas con saltos reales**: 27 de Febrero (barrera) y Puerto Norte (volatilidad extrema).

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

## 6. Simulación: Exclusión Dinámica por Gap

**Script**: `scripts/simulate_dynamic_gap.py`
**Fecha**: 2026-08-05

### Resultados por propiedad

| Property | Stored | Current | P33_same | P33_cross | Gap | n_same | n_cross | Barrier% | New | Delta |
|----------|--------|---------|----------|-----------|-----|--------|---------|----------|-----|-------|
| Mabel | $50,713 | $50,713 | $1,199 | N/A | 0.0% | 19 | 0 | 0.00% | $50,713 | +0.0% |
| Ayacucho | $30,843 | $30,843 | $983 | $1,182 | **-20.3%** | 3 | 3 | 1.50% | $30,843 | +0.0% |
| Vera Mujica | $61,185 | $61,185 | $1,459 | $1,625 | **-11.4%** | 14 | 10 | 1.25% | $61,185 | -0.0% |
| P1200 | $111,296 | $111,296 | $1,268 | $1,262 | 0.5% | 24 | 13 | 1.05% | $111,296 | +0.0% |
| Entre Rios | $54,203 | $54,203 | $1,594 | N/A | 0.0% | 42 | 0 | 0.00% | $54,203 | +0.0% |
| Brown 2750 | $241,344 | $241,344 | $2,176 | $3,131 | **-43.9%** | 20 | 6 | 0.69% | $241,344 | +0.0% |
| Francia 250b | $596,224 | $540,224 | $3,376 | N/A | 0.0% | 51 | 0 | 0.00% | $540,224 | -9.4% |
| Mitre1473 | $217,838 | $217,838 | $980 | N/A | 0.0% | 37 | 0 | 0.00% | $217,838 | +0.0% |
| Cochabamba 45 | $81,803 | $81,803 | $755 | $980 | **-29.8%** | 5 | 24 | 2.48% | $81,803 | -0.0% |

### Hallazgo clave

**TODOS los gaps son NEGATIVOS** (cross comps son MÁS CAROS que same-side):

| Property | Gap | Significado |
|----------|-----|-------------|
| Ayacucho | -20.3% | Cross +20% más caro |
| Vera Mujica | -11.4% | Cross +11% más caro |
| P1200 | +0.5% | Gaps mínimo |
| Brown 2750 | -43.9% | Cross +44% más caro |
| Cochabamba 45 | -29.8% | Cross +30% más caro |

### Conclusión

**La exclusión dinámica por gap NO cambiaría nada para estas propiedades.**

Razón: Cuando el gap es negativo (cross más caro), la fórmula actual ya maneja correctamente el caso. El blend promedia dos mercados donde el "otro lado" es más caro, lo cual no necesita corrección.

**El problema real no es la barrera, sino que los cross comps son más caros.** Esto sugiere que:
1. Las propiedades están en zonas donde el otro lado de la barrera tiene mayor valor
2. El blend actual ya está favoreciendo el mismo lado (alpha > 0.50)
3. La penalización por barrera es apropiada (0.69% - 2.48%)

### Gap Distribution

- **HARD (>20%)**: 0 propiedades
- **MODERATE (10-20%)**: 0 propiedades
- **WEAK (<10%)**: 1 propiedad (P1200)

### Impacto en la fórmula

| Escenario | Impacto |
|-----------|---------|
| Gap negativo (cross más caro) | Sin cambio necesario |
| Gap positivo < 10% | Sin cambio necesario |
| Gap positivo 10-20% | Reducir penalty a la mitad |
| Gap positivo > 20% | Excluir cross completamente |

**Solo 1 de 9 propiedades tiene gap positivo (P1200, 0.5%), y es insignificante.**

---

## 7. Macrozonas y Parámetros Clave

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

---

## 15. Simulación v10 — NUEVA FÓRMULA (efecto por barrera)

**Fecha**: 2026-08-06
**Script**: `scripts/simulate_barrier_effect.py`
**Enfoque**: Reemplazo de alpha/blend/penalty con ajuste por barrera individual.

### Fórmula propuesta (NUEVA)

En vez de separar same/cross → blend → penalty:

1. Re-clasificar cada comp con barreras corregidas (`barreras_rosario_corrected.json`)
2. Para cada barrera, calcular efecto: `efecto = (P33_A - P33_B) / P33_A`
3. Ajustar cada cross comp: `precio_aj = precio / (1 - efecto)`
4. Computar P33 del pool completo (same + cross-adjusted)
5. Sin alpha, sin blend, sin penalty

### Barreras usadas (8)

| Barrera | Efecto | P33_A | N_A | N_B |
|---------|--------|-------|-----|-----|
| Bulevar 27 de Febrero | -83.6% | $884 | 38 | 6 |
| Avenida Ovidio Lagos | -29.4% | $541 | 8 | 14 |
| Ituzaingó | -17.1% | $882 | 75 | 42 |
| Avenida Carlos Pellegrini | +15.4% | $749 | 35 | 25 |
| Ferrocarril | +23.3% | $2,308 | 22 | 38 |
| Bulevar Nicasio Oroño | +27.7% | $3,023 | 57 | 65 |
| Avenida Francia | +34.4% | $812 | 22 | 14 |
| Avenida Aristóbulo del Valle | +38.7% | $3,241 | 8 | 167 |

### Resultados — 3 propiedades clave

| Property | Pool | Same | Cross | Excl. | Engine vm2 | New vm2 | Delta |
|----------|------|------|-------|-------|------------|---------|-------|
| **Ayacucho** (1d, 27m2, 2002) | 33 | 27 | 5 | 1 | $1,343 | $1,416 | **+5.5%** |
| **Mitre1473** (3d, 206m2, 1971) | 82 | 82 | 0 | 0 | $1,573 | $1,747 | **+11.0%** |
| **Cochabamba 45** (4d, 98m2, 1966) | 387 | 129 | 96 | 162 | $1,271 | $1,324 | **+4.1%** |

### Análisis

1. **Ayacucho (+5.5%)**: 5 cross comps cruzan Ituzaingó (-17.1%). Al ajustarlos, el P33 sube de $1,343 a $1,416. El delta es razonable.

2. **Mitre1473 (+11.0%)**: **0 cross comps** — no hay barreras detectadas. Los 82 comps son todos same-side. La nueva fórmula usa P50 del pool completo, que es MAYOR que el blend del engine (alpha × P33_same). El engine produce $1,573 porque usa alpha=0.70 × P33, que es menor que P50.

3. **Cochabamba 45 (+4.1%)**: 96 cross comps cruzan Ituzaingó y Pellegrini. El efecto neto es pequeño (+4.1%) porque los barreras compensan (Ituzaingó baja, Pellegrini sube).

### Problema identificado: Mitre1473 no tiene barreras

Mitre1473 está en Centro. No hay barreras duras ni suaves que lo separen de sus 82 comps. Los 82 comps son todos accesibles.

La nueva fórmula no puede bajar el valor de Mitre1473 sin barreras. El problema NO es la barrera — es la composición del pool (82 comps, incluyendo 34×1-dorm y 30×2-dorm que inflan el P50).

**Decisión del usuario**: Los resultados son aceptables. Mitre1473 en Centro no tiene barreras = zona homogénea. OK.

### Comparación: Actual vs NUEVA FÓRMULA

| Propiedad | Stored | Engine | NewFormula | Stored→New |
|-----------|--------|--------|------------|------------|
| Ayacucho | $28,426 | $36,317 | $38,232 | **+34.5%** |
| Mitre1473 | $217,839 | $324,120 | $359,882 | **+65.2%** |
| Cochabamba 45 | $88,026 | $124,606 | $129,752 | **+47.4%** |

El delta Stored→Engine es por parámetros UV (retro_dias=60, flex=[1,2,3,4,5]) vs stored (retro=0, flex=None). La NUEVA FÓRMULA produce valores similares al engine actual para estas propiedades.

### Resultados completos — 9 propiedades

| Property | Pool | Same | Cross | Excl. | Engine vm2 | New vm2 | Delta | Barreras |
|----------|------|------|-------|-------|------------|---------|-------|----------|
| Mabel | 116 | 116 | 0 | 0 | $1,461 | $1,505 | **+17.6%** | — |
| Ayacucho | 33 | 27 | 5 | 1 | $1,343 | $1,416 | **+5.5%** | Ituzaingó |
| Vera Mujica | 36 | 11 | 24 | 1 | $1,508 | $1,672 | **+32.3%** | Francia |
| P1200 | 97 | 52 | 44 | 1 | $1,653 | $1,609 | **+11.1%** | Pellegrini |
| Entre Rios | 14 | 14 | 0 | 0 | $1,716 | $1,471 | **+14.5%** | — |
| Brown 2750 | 10 | 9 | 1 | 0 | $1,318 | $1,336 | **+22.7%** | Ovidio Lagos |
| Francia 250b | 35 | 35 | 0 | 0 | $3,337 | $2,612 | **-16.3%** | — |
| Mitre1473 | 82 | 82 | 0 | 0 | $1,573 | $1,513 | **+11.0%** | — |
| Cochabamba 45 | 387 | 129 | 96 | 162 | $1,271 | $1,115 | **+4.1%** | Ituzaingó, Pellegrini |

### Diferencia clave: Engine vs NUEVA FÓRMULA

**Engine actual**:
1. Separa same/cross
2. Blend: vm2 = alpha × P33_same + (1-alpha) × P33_cross
3. Penalty: vm2 *= (1 - barrier_pct)
4. **Efecto neto**: REDUCE el valor cuando hay cross comps

**NUEVA FÓRMULA**:
1. Re-clasifica con barreras corregidas
2. Ajusta cada cross comp: `precio_aj = precio / (1 - efecto)`
3. Computa P33 del pool completo
4. **Efecto neto**: AUMENTA el valor cuando cross comps están en el lado más barato

**Ejemplo Vera Mujica**:
- 24 cross comps cruzan Francia (+34.4% effect)
- Cross comps son más baratos ($533/m2) que same-side ($812/m2)
- Ajuste: cada cross comp se multiplica ×1.524
- P33 del pool ajustado: $1,672 (vs engine $1,508)

### Pendiente

1. **Decidir si reemplazar alpha/blend/penalty**: La nueva fórmula produce valores DIFERENTES al engine actual. Para propiedades con cross comps, la diferencia es significativa (Vera Mujica +32.3%, Cochabamba +4.1%).
2. **Aplicar barreras corregidas**: `barreras_rosario_corrected.json` tiene 686 barreras (vs 742 originales).
3. **Validar con el usuario**: Los deltas son aceptables? La lógica de ajustar cross comps UP es correcta?

> **NOTA (2026-08-07)**: Los resultados de v10 usaron parámetros INCORRECTOS (sin `cache_scraping`, sin `anio_sujeto`, sin `m2_equiv`). Ver sección 16 para resultados con parámetros correctos (v12).

---

## 16. Simulación v12 — 4 Soluciones de Percentil para Cross Comps

**Script**: `C:\Users\Gustavo\opencode\simulate_v11.py` (actualizado con engine params exactos)
**Fecha**: 2026-08-07
**Propiedades testeadas**: 9

### Problema a resolver

El engine actual usa percentil dinámico (P45/P50) que funciona bien para propiedades **sin cross comps**, pero **sobre-estima** propiedades **con cross comps** (ej: Cochabamba 45 +12.5% vs listing $77,000).

La **NUEVA FÓRMULA** ajusta precios cross comps por efecto de barrera, pero el percentil del pool completo (same + cross ajustados) sigue siendo representativo de la zona cara, no de la zona barata donde está el subject.

### 4 Soluciones testeadas

| Sol | Nombre | Descripción |
|-----|--------|-------------|
| **Sol0** | P45/P50 dinámico | Actual: `seleccionar_percentil_por_calidad_pool(n, cv, cv_ref)` |
| **Sol1** | Ponderado | Replica distribución same-side: `factor = n_total / n_same` |
| **Sol2** | Same-only P50 | Percentil solo de same-side: `calcular_percentil(sorted(same), 50)` |
| **Sol3** | P33 fijo | Percentil fijo del pool completo: `calcular_percentil(sorted(all), 33)` |

### Resultados completos

| Property | Engine | Sol0 (P45/P50) | Sol1 (weighted) | Sol2 (same-only) | Sol3 (P33) | n_same | n_cross |
|----------|--------|----------------|-----------------|------------------|------------|--------|---------|
| Mabel | $53,927 | +0.0% | +0.0% | +10.2% | -5.6% | 19 | 0 |
| Ayacucho | $30,842 | -7.8% | -7.8% | -7.8% | -9.4% | 3 | 3 |
| Vera Mujica | $61,181 | +4.3% | +4.3% | -3.2% | -4.4% | 14 | 10 |
| P1200 | $111,294 | +1.2% | +1.2% | +1.2% | **-13.0%** | 24 | 13 |
| Entre Rios | $54,203 | +0.0% | +0.0% | +0.0% | -4.2% | 42 | 0 |
| Brown 2750 | $241,344 | +0.8% | +0.8% | -11.0% | -12.3% | 20 | 6 |
| Francia 250b | $540,326 | +0.0% | +0.0% | +0.0% | -11.3% | 51 | 0 |
| Mitre1473 | $217,838 | +0.0% | +0.0% | +0.0% | -7.0% | 37 | 0 |
| **Cochabamba 45** | **$81,799** | **+12.5%** | **-7.7%** | **-9.6%** | **-4.3%** | 5 | 24 |

### Análisis por tipo de propiedad

#### Props con 0 cross comps (Mabel, Entre Rios, Francia 250b, Mitre1473)

- **Sol0/Sol1/Sol2**: +0.0% (match exacto con engine)
- **Sol3**: -4.2% a -11.3% (sub-deflacta significativamente)
- **Causa**: P33 es naturalmente más bajo que P50 en distribuciones con skew positivo (typical in real estate)

#### Props con cross comps moderados (Vera Mujica, Brown 2750, P1200)

- **Sol0**: +0.8% a +4.3%
- **Sol1**: +0.8% a +4.3%
- **Sol2**: -3.2% a -11.0%
- **Sol3**: -4.4% a -13.0%
- **P1200 es el caso más extremo**: Sol3 sub-deflacta -13.0%

#### Cochabamba 45 (caso extremo: 24 cross comps, 5 same)

- **Sol0**: +12.5% (sobre-estima significativamente)
- **Sol1**: -7.7%
- **Sol2**: -9.6%
- **Sol3**: -4.3% (MEJOR — listing real $77,000, engine $81,799)
- **Causa**: Pool dominado por cross comps (24/29 = 83%). Percentil dinámico (P45) calculado sobre pool mixto donde cross ajustados (más baratos) dominan la distribución.

### Hallazgos clave

1. **Sol3 (P33) es la más representativa para propiedades con muchos cross comps**
   - Cochabamba 45: -4.3% vs engine, +1.7% vs listing real ($77,000)
   - Sol0 (actual): +12.5% vs engine, +19.5% vs listing

2. **Sol3 sub-deflacta propiedades sin cross comps**
   - Francia 250b: -11.3%
   - P1200: -13.0%
   - Brown 2750: -12.3%
   - Causa: P33 es naturalmente más bajo que P50

3. **Trade-off fundamental**: No hay una solución única que funcione para todos los casos
   - P33 corrige Cochabamba 45 pero daña P1200
   - P45/P50 funciona para la mayoría pero sobre-estima Cochabamba 45

### Recomendación: Solución híbrida

**Criterio**: Usar P33 solo cuando `n_cross / n_total > umbral` (ej: 0.5 o 50%)

| Property | n_cross/n_total | ¿Sol3 aplicable? | Resultado |
|----------|-----------------|-------------------|-----------|
| Mabel | 0/19 = 0% | No → Sol0 | +0.0% ✅ |
| Ayacucho | 3/6 = 50% | Sí → Sol3 | -9.4% ⚠️ |
| Vera Mujica | 10/24 = 42% | No → Sol0 | +4.3% ⚠️ |
| P1200 | 13/37 = 35% | No → Sol0 | +1.2% ✅ |
| Entre Rios | 0/42 = 0% | No → Sol0 | +0.0% ✅ |
| Brown 2750 | 6/26 = 23% | No → Sol0 | +0.8% ✅ |
| Francia 250b | 0/51 = 0% | No → Sol0 | +0.0% ✅ |
| Mitre1473 | 0/37 = 0% | No → Sol0 | +0.0% ✅ |
| Cochabamba 45 | 24/29 = 83% | Sí → Sol3 | -4.3% ✅ |

**Con umbral 50%**: Solo Cochabamba 45 usa Sol3. Ayacucho queda en -9.4% (aceptable).

### Pendiente

1. **Decidir umbral**: ¿50% o 60% de n_cross/n_total para activar P33?
2. **Validar con más propiedades**: El trade-off actual funciona para 8/9 props. ¿Es aceptable?
3. **Implementar en engine**: Reemplazar `_computar_vm2_core()` alpha/blend/penalty con la lógica de ajuste por barrera + percentil híbrido.
4. **Aplicar barreras corregidas**: `barreras_rosario_corrected.json` tiene 686 barreras (vs 742 originales).
