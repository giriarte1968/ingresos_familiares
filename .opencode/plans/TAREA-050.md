# TAREA-050: Fix P33/P50 inversion in selection UI preview

## Problema
The UI selection preview in `valu_detail_sections.py` uses inverted P33/P50 logic:
```python
p33_p50 = p33 if n_sel >= 8 else p50  # WRONG: uses P33 for large samples, P50 for small
```

The Core Motor (`seleccionar_percentil_por_edad` in `cluster_filters.py`) uses:
- n ≥ 20 → P50
- 10 ≤ n < 20 → P45
- 8 ≤ n < 10 → P40
- 5 ≤ n < 8 → P33_age_blend
- n < 5 → P33

The UI should mirror this: **conservative P33 for small samples** (n<8), **higher percentiles for large samples** (n≥8).

## Solución
In `valu_detail_sections.py:352`:
```python
# BEFORE:
p33_p50 = p33 if n_sel >= 8 else p50

# AFTER:
p33_p50 = p50 if n_sel >= 8 else p33
```

Also updated the label caption from `P{'33' if n_sel >= 8 else '50'}` to `P{'50' if n_sel >= 8 else '33'}`.

## Archivos modificados
- `valu_detail_sections.py` — line 352: inverted P33/P50 logic, line 359: label

## Validación
- `python scripts/auto_validate.py` → OK
- Tests de regresión → OK
