# TAREA-126: Restaurar botones Valuación Manual + Renombrar a "Aplicar Selección" / "Limpiar"

## CONTEXTO

### Problema
El botón "Guardar Valuacion Manual" fue ocultado (desaparecía cuando `can_save=False`) para evitar prompts innecesarios, pero el usuario pide que **siempre esté visible** (disabled cuando no aplica).

Además, los nombres deben ser consistentes con la sección de Comparables:
- "Guardar Valuacion Manual" → "✅ Aplicar Selección"
- "Eliminar Valuacion Manual" → "🔄 Limpiar"

### Riesgo
El error original que motivó el ocultamiento fue la contaminación de `auto_valor_usd`. Ya está resuelto por:
- **TAREA-122**: `setdefault('auto_valor_usd', 0)` en save manual
- **TAREA-125**: `_verificar_invariante_portfolio_manual` en portfolio
- **RU-MANUAL-SAVE-02**: Guardrail `_verificar_invariante_auto_valor_usd` en save

## REGLAS DE ORO
- `pytest` pasa después de cada paso
- Botón "✅ Aplicar Selección" SIEMPRE visible (disabled cuando `can_save=False`)
- Botón "🔄 Limpiar" visible solo cuando hay valuación manual guardada
- Guardrails de contaminación se mantienen intactos

## ALCANCE

| Archivo | Cambio |
|---|---|
| `valu_detail_sections.py:1546-1622` | Botón siempre visible con `disabled=not can_save` en vez de if/else oculto |
| `valu_detail_sections.py:1549` | Texto: "Guardar Valuacion Manual" → "✅ Aplicar Selección" |
| `valu_detail_sections.py:1627` | Texto: "Eliminar Valuacion Manual" → "🔄 Limpiar" |
| `tests/test_regression.py` | Test actualizado + 1 nuevo test |
| `docs/BITACORA_AGENTES.md` | Nueva entrada |
| `.opencode/plans/TAREAS_INDEX.md` | Nueva entrada |

---

### PASO 1: Botón "✅ Aplicar Selección" siempre visible + disabled

**Archivo:** `valu_detail_sections.py:1546-1622`

**Cambio:**
```python
# ANTES:
        can_save = usd_m2_input > 0 and params_changed
        if can_save:
            if st.button("Guardar Valuacion Manual", type="primary", ...):
                ...
        else:
            pass

# DESPUES:
        can_save = usd_m2_input > 0 and params_changed
        if st.button("✅ Aplicar Selección", type="primary", ...,
                     disabled=not can_save):
            ...
```

El `disabled` parameter de Streamlit `st.button` mantiene el botón visible pero gris.

### PASO 2: Renombrar "Eliminar Valuacion Manual" → "🔄 Limpiar"

**Archivo:** `valu_detail_sections.py:1627`

```python
# ANTES:
            if st.button("Eliminar Valuacion Manual", ...):

# DESPUES:
            if st.button("🔄 Limpiar", ...):
```

### PASO 3: Tests

- **Actualizado:** `test_ui_manual_save_visible_disabled_when_no_changes` (antes `test_ui_manual_save_hidden_on_no_changes`)
  - Verifica que el botón "✅ Aplicar Selección" está presente aunque sin cambios
  - Verifica que `disabled=True` está en los kwargs del botón
- **Nuevo:** `test_ui_manual_limpiar_button_name`
  - Verifica que el botón "🔄 Limpiar" aparece (en vez de "Eliminar Valuacion Manual")
  - Verifica que NO hay llamadas con "Eliminar Valuacion"

### VALIDACION FINAL
```
☐ pytest tests/test_regression.py (25 tests)
☐ python scripts/auto_validate.py
☐ Botón "✅ Aplicar Selección" siempre visible (disabled si no hay cambios)
☐ Botón "🔄 Limpiar" visible cuando hay valuación manual
☐ Guardrails RU-MANUAL-SAVE-02 y RU-PORTFOLIO-01 intactos
```

### ARCHIVOS A COMMIT
- `valu_detail_sections.py`
- `tests/test_regression.py`
- `docs/BITACORA_AGENTES.md`
- `.opencode/plans/TAREA-126.md`
- `.opencode/plans/TAREAS_INDEX.md`
