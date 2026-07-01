# TAREA-097 — Restablecer Todo debe ser solo efecto visual — Riesgo BAJO

## Contexto
El botón "Restablecer todos" estaba provocando un recálculo completo
del motor, lo que contaminaba el header con valores incorrectos.
El usuario pidió explícitamente que sea solo un efecto visual:
seleccionar todas las propiedades no seleccionadas, habilitar el botón
"Aplicar selección", pero NO modificar el header ni el resultado del motor.

## Causa raíz
El botón en `valu_detail_sections.py:441` seteaba dos flags que
disparaban lógica peligrosa en `valu.py`:
1. `_reset_all_{prop_name} = True` — activaba el bloque de "reset" en valu.py
2. `forzar_recalculo_{prop_name} = True` — forzaba re-ejecución del motor

El bloque `_reset_all_` en `valu.py:786-801` intentaba "limpiar" el
resultado llamando a `persistir_valuacion(commit=True)`, lo que
contaminaba el cache con objetos modificados in-place.

## Cambios

### 1. `valu_detail_sections.py:441-453`
Remover:
- `st.session_state[f'_reset_all_{prop_name}'] = True`
- `st.session_state[f'forzar_recalculo_{prop_name}'] = True`

Mantener:
- Checkbox keys a True
- `comp_selection` = set(comp_ids)
- `comp_excluded` pop
- `_comp_interacted` pop
- `st.rerun()`

### 2. `valu.py:785-801`
Eliminar completamente el bloque `if st.session_state.pop(reset_key, False):`.

### 3. Debug flag
Agregar `[DEBUG-RESET-VISUAL]` en el botón de valu_detail_sections.py
para registrar que solo se modificó el estado visual.

### 4. Regression test
Refactorizar `test_reset_all_restores_motor_value` (#52) para verificar
que el botón NO altera el resultado del motor ni el cache.

### 5. Docs
BITACORA_AGENTES.md, STATUS_ACTUAL.md, TAREAS_INDEX.md

## Riesgo
BAJO. Solo afecta el comportamiento de un botón. No toca lógica
de valuación ni persistencia.
