# TAREA-078 — Percentil por calidad del pool (CV) + Eliminación edad — Riesgo ALTO

## CONTEXTO

El percentil actual se basa en `seleccionar_percentil_por_edad()`, que usa la cantidad de comparables con año conocido como proxy de confianza. ML demostró que la edad NO es factor causal de precio en Rosario (confounding effect con ubicación). Además, el filtro `_filtrar_por_ventana_edad` reduce el pool artificialmente, duplicando la penalización.

## REGLA DE ORO

- `pytest tests/test_regression.py` pasa después de cada paso (38 tests)
- `pytest tests/test_cluster_filters.py` pasa después de cada paso
- Los rangos de valuación de Mabel y Ayacucho se mantienen estables (o se ajustan conscientemente)
- `python scripts/auto_validate.py` pasa al final

## ALCANCE

| Archivo | Cambio |
|---|---|
| `parsers/cluster_filters.py` | Nuevas funciones `_calcular_cv()` y `seleccionar_percentil_por_calidad_pool()` |
| `parsers/mercado_inmobiliario.py` | Eliminar edad del flujo, agregar size_adj + CV, early return 0 para n<3 |
| `valu_detail_sections.py` | Reemplazar percentil preview |
| `main_valu_detail_sections.py` | Reemplazar percentil preview |
| `valu.py` | Reemplazar percentil con CV calculado de precios disponibles |
| `main_valu.py` | Reemplazar percentil con CV calculado de precios disponibles |
| `tests/test_regression.py` | Eliminar tests de age_blend, actualizar percentil tests |
| `tests/test_cluster_filters.py` | Reemplazar tests de edad con tests de calidad pool |
| `tests/test_age_blend_filter.py` | Eliminar solo lines que verifican P33_age_blend |

---

### PASO 1: Funciones auxiliares en cluster_filters.py

**Archivo:** `parsers/cluster_filters.py` — al final del archivo

Agregar `_calcular_cv()` y `seleccionar_percentil_por_calidad_pool()`. Mantener `seleccionar_percentil_por_edad()` por backward compat con scripts de diagnóstico.

**COMMIT:** `"TAREA-078: Add _calcular_cv and seleccionar_percentil_por_calidad_pool"`

**VERIFICAR:** `pytest tests/test_cluster_filters.py` (los tests legacy todavía existen)

---

### PASO 2: Modificar obtener_mediana_cluster_v2

**Archivo:** `parsers/mercado_inmobiliario.py`

**2.1** Agregar `m2_equiv=None` al signature (line 885)

**2.2** Agregar `_aplicar_size_adj_a_comparables()` helper antes de `obtener_mediana_cluster_v2`

**2.3** Reemplazar `_filtrar_por_ventana_edad()` por `pool_final = unicos` (lines 1267-1277)

**2.4** Agregar resolución de macrozona después de dedup

**2.5** Cambiar early return n<3 a `return 0.0` (line 1316)

**2.6** Reemplazar `seleccionar_percentil_por_edad()` por `seleccionar_percentil_por_calidad_pool()` (lines 1386-1393)

**2.7** Eliminar bloque P33_age_blend (lines 1487-1525)

**2.8** Actualizar metadata: eliminar age fields, agregar `cv_pool`

**COMMIT:** `"TAREA-078: Remove age filter, add CV-based percentil, n<3 returns 0"`

**VERIFICAR:** `pytest tests/test_regression.py`

---

### PASO 3: Callers de obtener_mediana_cluster_v2

**Archivo:** `parsers/mercado_inmobiliario.py`

**3.1** `valuar_propiedad_v7` (line 3142): pasar `m2_equiv=m2_equiv`

**3.2** `calcular_base_calibrada` (~line 1641): pasar `m2_equiv=calcular_m2_equivalentes(prop_data)`

**COMMIT:** `"TAREA-078: Pass m2_equiv to cluster from callers"`

---

### PASO 4: UI files

**Archivos:** `valu_detail_sections.py`, `main_valu_detail_sections.py`, `valu.py`, `main_valu.py`

**4.1** Detail sections: reemplazar `seleccionar_percentil_por_edad(True, n_sel)` por `seleccionar_percentil_por_calidad_pool(n_sel, 0.25)`

**4.2** valu.py/main_valu.py: calcular CV de `precios_sorted` y usar `seleccionar_percentil_por_calidad_pool`

**COMMIT:** `"TAREA-078: Update UI percentil preview to use calidad_pool"`

---

### PASO 5: Tests

**Archivos:** `tests/test_cluster_filters.py`, `tests/test_regression.py`, `tests/test_age_blend_filter.py`

**5.1** `test_cluster_filters.py`: reemplazar tests de edad (lines 249-288) con 6 tests de calidad pool + CV

**5.2** `test_regression.py`: eliminar tests age_blend, reemplazar percentil tests, ajustar rangos

**5.3** `test_age_blend_filter.py`: eliminar lines 33-35 y 61-63 (verificación P33_age_blend)

**COMMIT:** `"TAREA-078: Update tests for CV-based percentil"`

---

### VALIDACION FINAL

```
☐ pytest tests/test_regression.py pasa (38 tests)
☐ pytest tests/test_cluster_filters.py pasa
☐ pytest tests/test_age_blend_filter.py pasa
☐ python scripts/auto_validate.py pasa
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `docs/STATUS_ACTUAL.md`
- `docs/ALGORITMOS.md` (Sección 17: percentil por calidad, no por edad)
- `.opencode/plans/TAREAS_INDEX.md` (agregar entrada TAREA-078)

### ARCHIVO DE PLAN

Este plan se guarda permanentemente en `.opencode/plans/TAREA-078.md`.
