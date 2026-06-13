# TAREA-056: Persistent Apply Selection & Fix Preview Delta

## Problema
1. **Delta de preview erróneo**: `$3,213 vs original` debería ser `$3,213 vs $4,262`. El código compara P33 contra `res.get('valor_m2', 0)`, que es 0 hasta que el usuario aplica la selección (el motor usa `valor_m2_actual_usd`, no `valor_m2`).
2. **Selección aplicada se pierde al mover slider**: `comp_excluded` se almacenaba como índices y se borraba del estado tras el primer render. Al cambiar el slider (retro_dias), el estado desaparece y la valuación vuelve al valor por defecto del motor.

## Solución
### 1. Delta de preview (`valu_detail_sections.py`)
Cambiar `res.get('valor_m2', 0)` por `res.get('valor_m2_actual_usd', res.get('m2_base_venta', 0))`.

### 2. Persistencia de selección (`valu_detail_sections.py` + `valu.py`)
**Cambio clave**: usar IDs en lugar de índices para `comp_excluded`.

- **`valu_detail_sections.py`**:
  - `excluded_ids` se calcula como `[cid for cid in all_ids if cid not in selected_ids]`.
  - `is_applied` compara `set(resultado.get('_comp_excluded', [])) == set(excluded_ids)`.
  - Al clickear "Apply Selection": guarda `excluded_ids` (IDs) en `st.session_state`.

- **`valu.py`**:
  - El bloque Apply Selection se activa si `comp_excluded_key in st.session_state` O si `resultado.get('_comp_excluded')` existe.
  - Lee exclusiones de `st.session_state` (cambio de slider reciente) o del `resultado` cacheado (aplicación anterior).
  - Filtra `comps_venta` usando IDs: `[c for c in comps_orig if c.get('id') not in excluded_ids]`.
  - Si algún ID excluído ya no está en los nuevos comparables (slider cambió el pool), lo limpia automáticamente.
  - Guarda `resultado['_comp_excluded'] = excluded_ids` para persistir en cache.
  - **NO** hace `pop` de `comp_excluded_key` del session_state, para que sobreviva a reruns.

### 3. Consistencia de header
- `m2_base_venta` ya se actualiza en el bloque Apply (TAREA-054/055).
- Con la persistencia, al mover el slider la selección sigue activa y el header refleja los IDs guardados.

## Archivos modificados
- `valu_detail_sections.py`
- `valu.py`

## Validación
- `python scripts/auto_validate.py` → OK
- Tests de regresión → OK
- Slider mueve → selección aplicada persiste → header m² correcto
- Checkbox deselecciona → preview delta contra motor
