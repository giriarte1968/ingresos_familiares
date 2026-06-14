# TAREA-068: Limpiar preview_mode al navegar para evitar stale preview en re-entry

## Contexto
Al hacer preview en una propiedad Pendiente (Retro/Flex toggle), navegar al
Portfolio vía sidebar, y re-entrar a la misma propiedad, se mostraba el
preview stale en vez de Pendiente.

## Causa raíz
`preview_mode_{name}` en `st.session_state` nunca se limpia al navegar
vía sidebar (solo con "← Volver al Portafolio"). Al re-entrar, el bloque
Pendiente (línea 506) chequeaba `preview_mode` como guardián del cleanup:
al estar `True` (leaked), salteaba la limpieza del cache.

## Cambios

### Fix 1 — `valu.py:505-515` (Pendiente block)
Eliminar el guard `if not preview_mode:`. Siempre limpiar cache en re-entry
Pendiente. El guard `not forzar and not retro_btn_clicked` ya protege los
casos de preview activo (Carga Natural, Retro click).

### Fix 2 — `valu.py:1243-1247` (sidebar nav handler)
Al navegar a otra página (sidebar radio), limpiar `preview_mode_{old_prop}`
antes de setear `prop_sel = None`.

### Fix 3 — `valu_portfolio2.py:381` (`_ir_a_detalle`)
Al navegar desde Portfolio a una propiedad, limpiar `preview_mode_{nombre}`
para evitar leaks de sesiones previas.

## Validación
- `python scripts/auto_validate.py` ✅
- Pendiente → Retro preview → sidebar Portfolio → re-enter → Pendiente
- Pendiente → Retro preview → "← Volver" → re-enter → Pendiente
- Committed property → sin cambios

## Archivos modificados
- `valu.py` (Fix 1 + Fix 2)
- `valu_portfolio2.py` (Fix 3)
