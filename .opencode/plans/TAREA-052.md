# TAREA-052: Fix "is_applied" false positive in selection UI

## Problema
The `is_applied` detection in `valu_detail_sections.py` suffers from a false positive. It compares the current excluded IDs with the `_comp_excluded` list from the result.

```python
excluded_indices = res.get('_comp_excluded', []) # Returns [] if key doesn't exist
...
is_applied = (actual_excluded_ids == current_excluded_ids)
```

When a user opens a property for the first time, `_comp_excluded` is absent (defaulting to `[]`). If the user unchecks a property and then re-checks it, the current excluded set returns to `[]`. Since `[] == []`, `is_applied` becomes `True`, and the UI shows "✅ Selección Aplicada" (disabled) even though the user never clicked the Apply button.

## Solución
Distinguish between the "default" state (no selection applied) and the "applied all-selected" state. A selection is only truly "applied" if the `_comp_excluded` key explicitly exists in the result dictionary.

In `valu_detail_sections.py`:
```python
# BEFORE:
excluded_indices = res.get('_comp_excluded', [])
current_excluded_ids = {all_ids[i] for i in excluded_indices if i < len(all_ids)}
actual_excluded_ids = set(all_ids) - selected_ids
is_applied = (actual_excluded_ids == current_excluded_ids)

# AFTER:
has_applied = '_comp_excluded' in res
excluded_indices = res.get('_comp_excluded', [])
current_excluded_ids = {all_ids[i] for i in excluded_indices if i < len(all_ids)}
actual_excluded_ids = set(all_ids) - selected_ids
is_applied = has_applied and (actual_excluded_ids == current_excluded_ids)
```

## Archivos modificados
- `valu_detail_sections.py` — lines 345-348: updated `is_applied` logic

## Validación
1. **Cold Start**: Open property -> No "Apply" button (since `excluded = []` and `is_applied = False`).
2. **Modification**: Uncheck one property -> "Apply Selection" button appears (`excluded` is truthy, `is_applied = False`).
3. **Revert to Default**: Re-check the property -> No button appears (instead of "Applied") because `has_applied` is False.
4. **Apply**: Click "Apply Selection" -> "✅ Selección Aplicada" button appears (`has_applied = True` and selection matches).
5. **Re-modify**: Uncheck property -> "Apply Selection" button appears (`is_applied = False`).
6. **Revert to Applied State**: Re-check property -> "✅ Selección Aplicada" button reappears.
