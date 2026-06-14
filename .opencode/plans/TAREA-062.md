# TAREA-062: Live header update on checkbox change

## Problema
Al deseleccionar un comparable en la tabla, el monto total (header) no se actualizaba. Solo se veía el delta de m² en la sección preview.

## Causa
El Apply block en `valu.py` solo leía `comp_excluded` (seteado por botón "Aplicar selección"). El estado de los checkboxes (`comp_selection_{prop_name}`) era ignorado.

## Solución
1. **valu.py**: Modificar el Apply block para leer desde `comp_selection` (checkbox state) en CADA rerun, no solo desde `comp_excluded` (Apply button):
   - Prioridad: `comp_excluded` > `comp_selection` > `_comp_excluded`
   - `comp_excluded` se hace `pop` tras leerlo, para que cambios posteriores de checkbox tomen efecto
   - Se guardan `_original_m2_base` y `_original_valor_usd` antes de modificar (para delta del preview)

2. **valu_detail_sections.py**: Delta en preview usa `_original_m2_base` en vez de `m2_base_venta` (que se sobrescribe)

### Flujo corregido:
| Acción | Header | Preview delta |
|---|---|---|
| Primera carga | Motor (todos comps) | 0 vs original |
| Deseleccionar comp #4 | **Se actualiza** con 7 comps | Delta contra original |
| Click "Aplicar selección" | Igual (ya actualizado) | Aplicado (commit) |

## Archivos
- `valu.py`: líneas 564-577 (lectura de sel_key, pop comp_excluded, _original_m2_base)
- `valu_detail_sections.py`: línea 373 (delta usa _original_m2_base)

## Commit
`dbd432b` — main
