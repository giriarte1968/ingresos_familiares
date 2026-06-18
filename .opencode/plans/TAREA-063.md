# TAREA-063: Read widget keys directly for instant header sync on checkbox

## Problema
El header se actualizaba 1 rerun atrasado respecto al click del checkbox. Esto causaba que algunos clicks no sincronizaran el header inmediatamente.

## Causa
El Apply block leía `sel_key` de `st.session_state`, pero `render_tabla_comparables` actualiza `sel_key` DESPUÉS del Apply block (en el mismo rerun). El Apply block siempre veía el valor del RERUN ANTERIOR, no el actual.

```
Rerun N: checkbox click → sel_key actualizado en render_tabla_comparables (DESPUÉS del Apply)
Rerun N+1: Apply lee sel_key actualizado → header se actualiza (1 rerun tarde)
```

## Solución
Reemplazar la lectura de `sel_key` (stale) por lectura directa de los widget keys de cada checkbox:

```python
# En vez de:
selected_ids = st.session_state[sel_key]  # stale

# Hacer:
for cid in comp_ids:
    wk = f'sel_comp_{prop_name}_{cid}'
    if st.session_state.get(wk, True):
        selected_ids.add(cid)
```

El widget key (`sel_comp_{prop_name}_{comp_id}`) es gestionado por Streamlit y siempre refleja el valor ACTUAL del checkbox, incluso en el mismo rerun donde el usuario hizo click.

## Flujo corregido
| Rerun | Widget state | Apply block lee | Header |
|---|---|---|---|
| 1ra carga | No existe | `_comp_excluded` (si hay) o None | Motor |
| Checkbox click | Desmarcado | Widget key → desmarcado | **Actualizado inmediatamente** |
| Siguiente click | Marcado/Desmarcado | Widget key → estado actual | **Actualizado inmediatamente** |

## Archivos
- `valu.py`: líneas 573-585 (lectura widget keys en vez de sel_key)

## Commit
`1439df2` — main
