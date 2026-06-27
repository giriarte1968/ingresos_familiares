# TAREA: TAREA-086 — Fix cambio Manual→Comparable: carga desde cache físico — Riesgo ALTO

## CONTEXTO
Al valuar por Comparables, aplicar, presionar "Manual" y luego volver a "Por Comparables", la cantidad de comparables mostrada no coincide con la que se había aplicado y grabado originalmente. Causas raíz:

1. **`manual_preview` contaminaba `p_obj`**: los datos de preview del modo manual se aplicaban siempre sobre `p_obj`, incluso al cambiar a Comparable, adulterando los datos de propiedad que recibe `valuar_con_cache`.

2. **`valuar_con_cache` recalculaba en vez de devolver lo grabado** al volver a Comparable sin forzar recálculo, produciendo otra cantidad de comparables.

3. **`_ultima_valuacion` no se actualizaba al cambiar a 'auto'**, causando que portfolio cards mostraran el valor manual en vez del auto.

## REGLA DE ORO
- `pytest tests/test_regression.py` pasa después de cada paso
- No se modifican imports nuevos (todo ya está en scope)
- No se reformatea indentación ni comillas fuera de los bloques reemplazados
- Apply Selection sigue funcionando correctamente

## ALCANCE

| Archivo | Cambio |
|---|---|
| `valu.py` | Limpiar DEBUG prints (BUG7, DASH, SLIDER, DETALLE) |
| `valu.py` | `manual_preview` condicional según `fuente_activa_saved` |
| `valu_detail_sections.py` | `_set_fuente_activa('auto')` actualiza `_ultima_valuacion` con valor auto del cache |
| `valu.py` | Bypass de `valuar_con_cache` si `fuente_activa_saved == 'auto'` y hay `resultado_completo` |
| `valu_detail_sections.py` | Limpiar DEBUG print |
| `valu_portfolio2.py` | Limpiar DEBUG print |
| `main_valu.py` | Limpiar DEBUG prints |

## IMPLEMENTACIÓN

### Paso 1: Limpiar prints DEBUG
Archivos: `valu.py`, `valu_detail_sections.py`, `valu_portfolio2.py`, `main_valu.py`
Remover todas las líneas con `[DEBUG-BUG7]`, `[DEBUG-DASH]`, `[DEBUG-SLIDER]`, `[DEBUG-DETALLE]`.

### Paso 2: `manual_preview` condicional según fuente guardada
Archivo: `valu.py` (~línea 506-509)
Solo aplicar `manual_preview` si `_ultima_valuacion.fuente_activa` es `'manual'`.

### Paso 3: `_set_fuente_activa` actualiza `_ultima_valuacion`
Archivo: `valu_detail_sections.py` (~línea 111-121)
Al setear `fuente='auto'`, leer `resultado_completo` del cache y actualizar `valor_usd`, `comps`, `fuente`, `_comp_excluded`, `_comp_exclusion_applied` en `_ultima_valuacion`.

### Paso 4: Bypass de `valuar_con_cache` en modo Auto (v3 fix)
Archivo: `valu.py` (~línea 610)
Si `fuente_activa_saved == 'auto'` y `not forzar` y hay `resultado_completo` en `entrada_antigua`:
1. Verificar que `resolution_metadata.fecha_ref` del cache coincida con `datetime.now().strftime('%Y-%m-%d')`.
2. Si coinciden → usar resultado cacheado directamente (log `[CACHE] ... usando resultado_completo grabado`)
3. Si NO coinciden → cache stale → log `[CACHE] ... cache stale (fecha_ref=..., hoy=...), recalculando` → ejecutar `valuar_con_cache`

## VALIDACION FINAL
```
☐ pytest pasa (32 tests) ✅
☐ Sintaxis OK ✅
```

## DOCS A ACTUALIZAR
- `docs/BITACORA_AGENTES.md`
- `.opencode/plans/TAREAS_INDEX.md`
