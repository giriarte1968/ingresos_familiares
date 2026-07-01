# TAREA-099 — Cerrar gap: _official_result en primera valuación — Riesgo BAJO

## Contexto
TAREA-098 protege el header durante modo preview usando `_official_result`.
Pero si `_official_result` no existe (primera valuación, post-"Limpiar"),
el header cambia al tocar Retro/Flex/Slider.

## Causa raíz
`_official_result` solo se guarda en `persistir_valuacion(commit=True)`.
La primera valuación (o post-Limpiar) no pasa por ese camino.

## Cambio único
Antes de `mostrar_detalle_valu`, si NO es modo preview y no existe
`_official_result`, guardar `copy.deepcopy(resultado)` como oficial.

## Debug flag
`[DEBUG-OFFICIAL-FIRST]` — rastrea cuándo se guarda por primera vez.

## Regression test
Test #55: verifica que en primera valuación (sin _official_result),
el header se congela correctamente.
