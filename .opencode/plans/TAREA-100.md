# TAREA-100 — Matar el bug del Guard en preview (defensa sistémica) — Riesgo BAJO

## Contexto
Cuando el usuario apaga Retro, el motor retorna 0 comparables.
El Engine Guard en `valuar_con_cache` restaura el último resultado
válido (Retro ON, 6 comps) pisando el return value.
En modo preview, esto causa contradicción: header muestra el
estado real (0 comps) pero la tabla muestra el restaurado.

## Causa raíz
`resultado = _existing` en `motor_vpp_core.py:1435` reemplaza el
return value. Debió solo `_skip_persist = True`.

## Cambio único
En `valuar_con_cache`: si `preview=True`, NO hacer
`resultado = _existing`. Solo `_skip_persist = True` para
proteger el cache en disco.

## Debug flag
`[DEBUG-GUARD-PREVIEW]` — rastrea cuándo preview preserva el fallo.

## Regression tests
- Test #56: `valuar_con_cache(preview=True)` con params que fallan
  verifica que return es el fallo, no el cache restaurado.
- Test #57: Flujo UI completo (valu.py → motor) verifica que un
  preview fallido se muestra en tabla como fallo.
