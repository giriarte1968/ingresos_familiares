# TAREA-055: Show Apply Selection button even when all comparables selected

## Problema
The "Apply Selection" button was hidden when `excluded = []` (all comparables selected) because the code used `elif excluded:` which is falsy for an empty list. The user saw a P33 preview of $3,213/m² but the header showed $4,262/m² and there was no button to apply the preview.

## Solución
### Fix 1: `valu_detail_sections.py`
Changed `elif excluded:` to `else:`, so the button is always shown when `is_applied` is False and `n_sel >= 2`.

### Fix 2: `valu.py`
Changed the trigger condition from `if comp_excluded and ...` to `if 'comp_excluded_key' in st.session_state and ...`. This allows `comp_excluded = []` (all selected, nothing excluded) to still trigger the recalculation.

## Archivos modificados
- `valu_detail_sections.py` — button visibility logic (line 380)
- `valu.py` — condition check for `comp_excluded` (line 552-553)

## Validación
- `python scripts/auto_validate.py` → OK
- Flujo con 2 comps (todos seleccionados): botón "Aplicar selección (2/2)" visible
- Flujo con exclusiones: botón visible
- Flujo ya aplicado: botón "✅ Selección Aplicada" (deshabilitado)
