# TAREA-053: Fix preview valuation leak into Portfolio

## Problema
When the user interacts with a property in preview mode (toggles, selection), `persistir_valuacion(commit=False)` writes the preview result to `valuaciones_cache.json`. When the user returns to Portfolio, `_cargar_resultados_cache` reads from the cache and shows the preview value, even though the user never clicked "Aplicar Cambios". This makes it look like the valuation was committed when it wasn't.

## Causa raíz
`valu_portfolio2.py:_cargar_resultados_cache` treats any cache entry (including previews) as the official result. It should only use cache entries where `_cache.preview == False`. If only a preview exists, it should fall back to `_ultima_valuacion` from `propiedades.json`.

## Solución
### Fix 1: `valu_portfolio2.py` — Skip preview entries in Portfolio
Modify `_cargar_resultados_cache` to ignore cache entries where `resultado.get('_cache', {}).get('preview', False)` is True. This ensures the Portfolio only shows committed values.

Si la entrada de caché existe pero es un preview:
- Saltarla (no usar `resultados[nombre] = resultado`)
- Caer en `elif ultima:` para usar `_ultima_valuacion` de `propiedades.json`
- Si no hay `_ultima_valuacion`, mostrar "Pendiente"

### Fix 2: `parsers/motor_vpp_core.py` — Force recalc for official requests on preview cache
In `valuar_con_cache`, if `preview=False` (official request) but the cached result has `preview=True`, force a recalculation so the official value is committed.

## Archivos modificados
- `valu_portfolio2.py` — `_cargar_resultados_cache`: filter logic for preview entries
- `parsers/motor_vpp_core.py` — `valuar_con_cache`: cache invalidation logic

## Validación
1. Open a Pendiente property → toggles show preview → go back to Portfolio → should show Pendiente (not preview value)
2. Open an already-valued property → toggles show preview → go back to Portfolio → should show old committed value (not preview)
3. Click "Aplicar Cambios" → go to Portfolio → should show the new committed value
4. `python scripts/auto_validate.py` → OK
