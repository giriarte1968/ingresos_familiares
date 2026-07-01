# TAREA-102: Fallback a UV snapshot si recálculo falla

## Problema
Mabel muestra valuación manual en el card de Portfolio, pero al entrar al detalle aparece "sin valuación". Causa:
1. `fecha_ref` no se escribe en `resolution_metadata` del cache → stale check siempre falla → siempre recalcula
2. Recálculo puede devolver `n_comps < 3` (0 comparables) → `render_header` oculta valuación
3. Engine Guard (TAREA-100) solo restaura si `resultado.error=True`, no si `n_comps < 3`

## Solución
Si `ya_valuado=True` y el resultado tiene `error=True` o `n_comps < 3`, construir fallback desde `_ultima_valuacion`.

### Cambios
- `valu.py`: Bloque TAREA-102 tras `valuar_con_cache` y antes de valuación manual paralela
- `propiedades.json`: Mabel `fuente`/`fuente_activa → "manual"`

### Debug flags
`[DEBUG-FALLBACK-102]`

### Tests
57/57 OK
