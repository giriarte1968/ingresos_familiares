# TAREA-022 — Cap dinámico de factor_total según cluster quality — Riesgo MEDIO

## CONTEXTO

El factor `f_dict['total']` actualmente se clamp hard a [0.70, 1.35] dentro de `calcular_factores()`. En `valuar_propiedad_v7()`, existe un soft cap `MAX_BONUS_ATRIBUTOS = 1.30` (línea 358) que modifica `factores_base` (líneas 3042-3045), pero `valor_venta` (línea 3057) usa `f_dict['total']` directamente, NO `factores_base` → **código muerto**.

Propiedades como Brown 2750 con `f_dict['total'] = 1.346` no tienen cap real. Un cluster ALTA (n≥15, radio≤300) no debería permitir factores tan extremos.

## REGLA DE ORO

- `pytest` pasa después de cada paso
- `calcular_factores()` NO se modifica (fórmula aditiva, deltas)
- age blend, barreras, percentiles, NLP, amenities, deltas → NO se tocan
- Cluster formula NO se modifica
- `f_dict['cap_dinamico']` se guarda siempre para trazabilidad

## ALCANCE

| Archivo | Cambio |
|---|---|
| `parsers/mercado_inmobiliario.py` | 2 nuevas funciones + reemplazar cap muerto en `valuar_propiedad_v7()` |
| `tests/test_regression.py` | Ajustar benchmarks de Brown y P1200 |

---

### PASO 1: Agregar `obtener_caps_factor_por_cluster()` y `aplicar_cap_dinamico_factor()`

**Archivo:** `parsers/mercado_inmobiliario.py` — después de la línea 358 (junto a `MAX_BONUS_ATRIBUTOS`)

**1.1** Agregar función `obtener_caps_factor_por_cluster(meta_venta, n_v)`

**1.2** Agregar función `aplicar_cap_dinamico_factor(f_dict, meta_venta, n_v)`

**VERIFICAR:** `python -c "from parsers.mercado_inmobiliario import obtener_caps_factor_por_cluster, aplicar_cap_dinamico_factor; print('OK')"` + `pytest`

---

### PASO 2: Reemplazar el cap muerto en `valuar_propiedad_v7()`

**Archivo:** `parsers.mercado_inmobiliario.py` — líneas 3042-3047

Reemplazar soft cap muerto por llamado a `aplicar_cap_dinamico_factor()`.

**VERIFICAR:** `pytest` (esperar algunos benchmarks rotos)

---

### PASO 3: Actualizar benchmarks de tests

**Archivo:** `tests/test_regression.py`

Ejecutar `pytest -v` y expandir rangos donde fallen.

**VERIFICAR:** `pytest tests/test_regression.py -v` → 39/39

---

### VALIDACION FINAL

```
☐ pytest pasa (39 tests)
☐ Brown 2750: f_dict['total'] 1.346 → 1.15 (cluster ALTA)
☐ P1200: f_dict['total'] >1.25 → 1.25 (cluster MEDIA)
☐ Mabel/Ayacucho/Vera: f_dict['total'] sin cambios
☐ f_dict['cap_dinamico'] presente en resultado de valuar_propiedad_v7()
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `docs/STATUS_ACTUAL.md`
- `docs/ALGORITMOS.md` (nuevo paso de cap dinámico)
- `.opencode/plans/TAREAS_INDEX.md`
