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
