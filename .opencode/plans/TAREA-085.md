## TAREA: TAREA-085 — Fix "Restablecer todos" no resetea exclusión persistida — Riesgo BAJO

### CONTEXTO

El botón "↩️ Restablecer todos" en `render_tabla_comparables` no funciona correctamente:
- No re-selecciona los comparables (checkboxes quedan desmarcados)
- No resetea el valor de valuación al estado sin exclusión

**Causa raíz**: El botón limpia `comp_excluded_{prop_name}` de `session_state` (línea 381), pero la exclusión se re-aplica automáticamente desde `p_obj['_ultima_valuacion']` en `valu.py:665-666` porque `_comp_exclusion_applied=True` persiste en el portfolio.

**Flujo del bug**:
1. Usuario clickea "Restablecer todos"
2. Botón: `st.session_state.pop('comp_excluded_X')`, `forzar_recalculo=True`, `st.rerun()`
3. `valuar_con_cache` corre fresco → resultado sin `_comp_excluded`
4. `valu.py:663`: `resultado.get('_comp_excluded')` es `None`
5. `valu.py:665`: `p_obj['_ultima_valuacion'].get('_comp_exclusion_applied')` es `True`
6. Exclusión se re-aplica desde `_ultima_valuacion.get('_comp_excluded', [])`
7. Checkboxes y valor vuelven al estado excluido

### REGLA DE ORO

- "Restablecer todos" debe dejar todos los comparables seleccionados y el valor del motor sin exclusión
- `pytest` pasa (32 tests)
- El botón "Aplicar selección" sigue funcionando después del reset

### ALCANCE

| Archivo | Cambio |
|---|---|
| `valu_detail_sections.py` | Simplificar botón: limpiar selection keys, setear flag `_reset_all` |
| `valu.py` | Interceptar `_reset_all` flag ANTES de restaurar exclusión, persistir estado limpio |

---

### PASO 1: Botón más simple en valu_detail_sections.py

**Archivo:** `valu_detail_sections.py` — `render_tabla_comparables` (líneas 370-385)

**1.1** Limpiar todas las keys de selección individual (`sel_comp_*`) y la key de selección set (`comp_selection_*`) de session_state.

**1.2** Setear flag `_reset_all_{prop_name}` para que `valu.py` intercepte la restauración de exclusión.

**1.3** Setear `forzar_recalculo` y rerun.

```python
# Después:
                if st.button("↩️ Restablecer todos", key=f'reset_comp_sel_{prop_name}', use_container_width=True):
                    for k in list(st.session_state.keys()):
                        if k.startswith(f'sel_comp_{prop_name}_') or k == f'comp_selection_{prop_name}':
                            del st.session_state[k]
                    st.session_state[f'_reset_all_{prop_name}'] = True
                    st.session_state[f'forzar_recalculo_{prop_name}'] = True
                    st.rerun()
```

**COMMIT:** `"fix: simplify reset_all button, clean selection keys and set _reset_all flag (TAREA-085)"`

**VERIFICAR:** `pytest tests/test_regression.py`

---

### PASO 2: Interceptar reset en valu.py

**Archivo:** `valu.py` — bloque de exclusión (líneas 649-668)

**2.1** Insertar el chequeo del flag `_reset_all` al inicio del bloque `else` (después de `comps_orig` check).

**2.2** Si el flag está presente: persistir el resultado limpio (sin exclusión) y mantener `excluded_ids = None` para que el bloque de recálculo se salte.

```python
# Antes (líneas 654-668):
                    else:
                        excluded_ids = None
                        from_apply = False
                        if comp_excluded_key in st.session_state:
                            excluded_ids = st.session_state.pop(comp_excluded_key)
                            from_apply = True
                        else:
                            if resultado.get('_comp_excluded') is not None:
                                excluded_ids = resultado['_comp_excluded']
                            elif p_obj.get('_ultima_valuacion', {}).get('_comp_exclusion_applied'):
                                excluded_ids = p_obj['_ultima_valuacion'].get('_comp_excluded', [])
                                from_apply = True

# Después:
                    else:
                        excluded_ids = None
                        from_apply = False

                        reset_key = f'_reset_all_{prop_name}'
                        if st.session_state.pop(reset_key, False):
                            try:
                                from parsers.valuacion_cache import cargar_cache_valuaciones, persistir_valuacion
                                _cv = cargar_cache_valuaciones()
                                persistir_valuacion(prop_name, p_obj, resultado, _cv, commit=True)
                            except Exception as e:
                                logger.warning(f"[RESET] {prop_name}: persist error: {e}")
                                st.session_state[f'forzar_recalculo_{prop_name}'] = True
                        elif comp_excluded_key in st.session_state:
                            excluded_ids = st.session_state.pop(comp_excluded_key)
                            from_apply = True
                        else:
                            if resultado.get('_comp_excluded') is not None:
                                excluded_ids = resultado['_comp_excluded']
                            elif p_obj.get('_ultima_valuacion', {}).get('_comp_exclusion_applied'):
                                excluded_ids = p_obj['_ultima_valuacion'].get('_comp_excluded', [])
                                from_apply = True
```

**VERIFICAR:** `pytest tests/test_regression.py`

---

### VALIDACION FINAL

```
☐ pytest pasa (32 tests)
☐ Click "Restablecer todos" → todos los checkboxes seleccionados
☐ Click "Restablecer todos" → header muestra valor sin exclusión
☐ Click "Restablecer todos" → info/button desaparecen (n_excluidos=0)
☐ Click "Aplicar selección" después del reset → funciona correctamente
```

### DOCS A ACTUALIZAR

- `.opencode/plans/TAREAS_INDEX.md`

### ARCHIVO DE PLAN

Plan archivado permanentemente en `.opencode/plans/TAREA-085.md`.

### ENTREGABLES

- `valu_detail_sections.py` modificado
- `valu.py` modificado
- `pytest` pasando (32 tests)
- Plan archivado
