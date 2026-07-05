# TAREA-120: Restaurar botones UI + Guardrails de regresión — Riesgo ALTO

## CONTEXTO

Dos regresiones críticas en la UI de comparables:

1. **Botón "Aplicar Selección" desaparece** cuando todos los comparables están seleccionados (`n_sel == len(comparables)`). En TAREA-114 el botón era visible siempre. El cambio en `valu_detail_sections.py:571` usa `else: st.write("")` que oculta el botón, impidiendo al usuario "ratificar" el estado todo-seleccionado.

~~2. **"Restablecer Todas" no forza recálculo** — TAREA-097 lo hizo visual-only. ❌ CORREGIDO: Restablecer es SOLO visual (reselecciona checkboxes, no toca el motor). El recálculo ocurre exclusivamente al hacer clic en "Aplicar Selección".~~

3. **No existen tests de UI con mocks** que protejan contra estas regresiones.

### REGLA DE ORO

- `pytest` pasa (tests existentes + nuevos)
- Botón "Aplicar Selección" visible incluso con 6/6 checks
- "Restablecer Todas" es VISUAL-ONLY: reselecciona checkboxes, NO forza recálculo
- Tests con mocks de Streamlit protegen el comportamiento
- No se purgan tests existentes

### ALCANCE

| Archivo | Cambio |
|---|---|
| `valu_detail_sections.py` | Botón visible siempre; Restablecer es visual-only |
| `tests/test_regression.py` | UI guardrail tests + fix syntax error |
| `docs/TASK_TEMPLATE.md` | Nuevo paso obligatorio: UI guardrails |
| `docs/BITACORA_AGENTES.md` | Log TAREA-120 |
| `docs/STATUS_ACTUAL.md` | Actualizar estado |
| `.opencode/plans/TAREAS_INDEX.md` | Agregar TAREA-120 |

---

### PASO 1: Documentación

**Archivos múltiples** — docs y plan

**1.1** Crear `.opencode/plans/TAREA-120.md` (este archivo)

**1.2** Agregar entrada en `.opencode/plans/TAREAS_INDEX.md`

**1.3** Agregar entrada en `docs/BITACORA_AGENTES.md`

**1.4** Actualizar `docs/STATUS_ACTUAL.md`

**1.5** Actualizar `docs/TASK_TEMPLATE.md`: agregar "UI Guardrails" como sección obligatoria

**1.6** Actualizar `docs/MAPA_PROYECTO.md`: mención a tests con mocks de Streamlit

---

### PASO 2: Tests de regresión UI con mocks

**Archivo:** `tests/test_regression.py`

**2.1** Fix syntax error: `'_ultima_//_valuacion'` → `'_ultima_valuacion'`

**2.2** Agregar `test_apply_button_visible_when_all_selected`:
- Mock `streamlit.button`, `streamlit.write`, `streamlit.checkbox`, `streamlit.columns`, `streamlit.metric`, `streamlit.caption`, `streamlit.markdown`
- Crear 6 comparables, seleccionar todos
- Verificar que `st.button` sea llamado (botón visible)

**2.3** Agregar `test_ui_reset_all_visual_only`:
- Mock `streamlit.button` con side_effect que retorna True para el botón reset
- Verificar que Restablecer setea todos los checkboxes a True y elimina `comp_excluded`
- Verificar que NO setea `forzar_recalculo`

**2.4** Preservar `test_comparables_banner_hidden_when_full_selection` existente

---

### PASO 3: Fix código — Botón visible siempre

**Archivo:** `valu_detail_sections.py` — línea 570-572

**3.1** Cambiar:
```python
            else:
                # Selección total: El botón desaparece para evitar redundancia al entrar desde Portfolio
                st.write("") 
```
a:
```python
            else:
                # Botón visible incluso si no hay exclusiones (TAREA-114)
                if st.button(
                    f"✅ Aplicar selección ({n_sel}/{len(comparables)})",
                    key=f'apply_comp_sel_{prop_name}',
                    type='primary',
                    use_container_width=True,
                ):
                    from datetime import datetime
                    print(f"[DEBUG-APPLY] ===== INICIO Aplicar selección {prop_name} =====")
                    print(f"[DEBUG-APPLY] {prop_name}: n_sel={n_sel}, n_total={len(comparables)}, n_excluded={len(excluded)}")
                    slider_val = st.session_state.get(f'retro_meses_slider_{prop_name}', 36)
                    st.session_state[f'retro_meses_{prop_name}'] = slider_val
                    st.session_state[f'comp_excluded_{prop_name}'] = excluded
                    st.session_state[f'forzar_recalculo_{prop_name}'] = True
                    print(f"[DEBUG-APPLY] {prop_name}: Set forzar_recalculo=True, excluded={excluded}")
                    st.rerun()
```

---

### PASO 4: (NO APLICA — Restablecer NO forza recálculo)

**Decisión:** "Restablecer Todas" es SOLO visual — reselecciona checkboxes, NO setea `forzar_recalculo`.
El recálculo ocurre exclusivamente al hacer clic en "Aplicar Selección".
Esta lógica quedó documentada en `STATUS_ACTUAL.md §8` como RO-UI-01.

---

### VALIDACION FINAL

```
☑ pytest tests/test_regression.py — 9/9 pasando
☑ test_ui_apply_button_visible_when_all_selected pasa
☑ test_comparables_banner_hidden_when_full_selection pasa
☑ test_ui_reset_all_visual_only pasa (renombrado, verifica visual-only)
☑ test_ui_manual_save_hidden_on_no_changes pasa
☑ No se purgaron tests existentes
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `docs/STATUS_ACTUAL.md`
- `docs/TASK_TEMPLATE.md`
- `docs/MAPA_PROYECTO.md`
- `.opencode/plans/TAREAS_INDEX.md` (agregar entrada)

### ARCHIVO DE PLAN

Plan guardado permanentemente en `.opencode/plans/TAREA-120.md`.
ID secuencial 120 (último ID en TAREAS_INDEX.md: 114).

### ENTREGABLES

- `valu_detail_sections.py` — 2 fixes
- `tests/test_regression.py` — UI guardrail tests añadidos
- Documentación actualizada
- `pytest` pasando
- Plan archivado
