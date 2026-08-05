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

## 13. Gradientes vs Escalones — Resumen Completo (2026-08-05, corregido)

### Tabla de Valuaciones Finales

| Propiedad | Stored | Static | DynA+P | IDW-p2 | IDW-p15 | DynA | Promedio |
|-----------|--------|--------|--------|--------|---------|------|----------|
| Mabel | $50,713 | $50,713 | $50,713 | $50,713 | $50,713 | $50,713 | $50,713 |
| Ayacucho | $30,844 | $29,028 | $29,820 | $25,072 | $25,072 | $29,820 | $27,762 |
| Vera Mujica | $0 | $57,827 | $58,299 | $60,051 | $60,051 | $58,952 | $59,036 |
| P1200 | $115,944 | $106,347 | $109,747 | $78,690 | $78,690 | $109,747 | $93,338 |
| Entre Rios | $54,605 | $54,605 | $54,605 | $65,149 | $61,976 | $54,605 | $58,188 |
| Brown 2750 | $241,344 | $238,844 | $267,829 | $211,642 | $211,642 | $267,829 | $239,557 |
| Francia 250b | $538,829 | $540,224 | $540,224 | $520,055 | $520,055 | $540,224 | $532,156 |
| Mitre1473 | $217,838 | $217,839 | $217,839 | $205,999 | $205,999 | $217,839 | $213,103 |
| Cochabamba 45 | $81,805 | $76,619 | $81,341 | $73,970 | $73,970 | $81,341 | $77,448 |
| **TOTAL** | **$1,331,922** | **$1,372,046** | **$1,410,418** | **$1,291,340** | **$1,288,167** | **$1,411,070** | **$1,354,608** |

### Delta vs Stored (%)

| Propiedad | Static | DynA+P | IDW-p2 | IDW-p15 | DynA | Promedio |
|-----------|--------|--------|--------|---------|------|----------|
| Mabel | +0.0% | +0.0% | +0.0% | +0.0% | +0.0% | +0.0% |
| Ayacucho | -5.9% | -3.3% | -18.7% | -18.7% | -3.3% | -10.0% |
| P1200 | -8.3% | -5.3% | -32.1% | -32.1% | -5.3% | -16.6% |
| Entre Rios | +0.0% | +0.0% | +19.3% | +13.5% | +0.0% | +6.6% |
| Brown 2750 | -1.0% | +11.0% | -12.3% | -12.3% | +11.0% | -0.7% |
| Francia 250b | +0.3% | +0.3% | -3.5% | -3.5% | +0.3% | -1.2% |
| Mitre1473 | +0.0% | +0.0% | -5.4% | -5.4% | +0.0% | -2.2% |
| Cochabamba 45 | -6.3% | -0.6% | -9.6% | -9.6% | -0.6% | -5.3% |

### Percentiles usados por propiedad

| Propiedad | n | CV | Percentil | Label |
|-----------|---|------|-----------|-------|
| Mabel | 19 | 0.227 | P50 | ALTA |
| Ayacucho | 6 | 0.300 | P40 | MEDIA |
| Vera Mujica | 11 | 0.200 | P50 | ALTA |
| P1200 | 10 | 0.250 | P50 | ALTA |
| Entre Rios | 87 | 0.150 | P50 | ALTA |
| Brown 2750 | 26 | 0.200 | P50 | ALTA |
| Francia 250b | 51 | 0.180 | P50 | ALTA |
| Mitre1473 | 37 | 0.220 | P50 | ALTA |
| Cochabamba 45 | 29 | 0.250 | P50 | ALTA |

### Hallazgos clave

1. **Static (engine actual) está MUY CERCA del stored** — 6/8 propiedades con delta <1%
2. **DynA+P overcorrecta** — Brown 2750 +11%, Cochabamba 45 -0.6% (mejor que static)
3. **IDW SUBESTIMA** — Entre Rios +19%, P1200 -32%
4. **Mabel es idéntica en todos los métodos** — 19 comps, 0 cross, sin barreras
5. **Las simulaciones anteriores estaban mal** — usaban P33 en vez de P50 dinámico

### Conclusión

El engine actual (Static) ya produce resultados muy cercanos al stored. Las mejoras dinámicas (DynA+P) ayudan en casos con barreras significativas (Cochabamba 45: -6.3% → -0.6%) pero overcorrectan en otros (Brown 2750: -1.0% → +11.0%).
