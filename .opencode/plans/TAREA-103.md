# TAREA-103: Limpiar manual_valor_usd al eliminar valuación manual

## Problema
Al eliminar una valuación manual, `manual_valor_usd` en `_ultima_valuacion`
seguía con el valor anterior (ej. $83.851). El portfolio lo lee y muestra
"Manual $83.851" aunque la valuación manual ya fue borrada.

## Causa raíz
`valu_detail_sections.py:1567` — El handler `Eliminar Valuación Manual`
resetea `fuente/activa` y borra `manual_params`, pero NUNCA toca
`manual_valor_usd` ni revierte `valor_usd` al auto.

## Fix
- `manual_valor_usd = 0` → portfolio deja de mostrar "Manual"
- `valor_usd = auto_valor_usd` → la propiedad queda valuada con comparables

## Debug flags
`[DEBUG-DELETE-103]`

## Tests
- 57/57 regression OK
