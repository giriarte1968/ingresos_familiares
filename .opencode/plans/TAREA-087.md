# TAREA-087: Guard preview fallido no debe pisar cache exitoso

## Problema
Cuando `valuar_con_cache` se llama con `preview=True` y los parámetros
producen un resultado fallido (insuficientes_comparables, error, valor=0),
`persistir_valuacion(commit=False)` sobrescribe el cache, borrando el
resultado exitoso previo. En el próximo render, el cache tiene el resultado
fallido y el usuario ve un error aunque antes había una valuación válida.

Caso concreto: Francia 250 bis perdió su valuación exitosa ($665,387 USD,
6 comparables) cuando un preview con `retro_dias=0` produjo
`insuficientes_comparables` y pisó el cache.

## Cambios

### 1. `parsers/motor_vpp_core.py:valuar_con_cache` — Guard condicional
- Antes de persistir, si `preview=True` y el nuevo resultado es fallido
  (error o valor=0), verificar si el cache actual tiene un resultado exitoso
  (valor>0, sin error). Si es así, NO persistir el preview fallido.
- Agregar flag `[CACHE-PREVIEW-SKIP]` cuando se saltea persist
- Agregar flag `[CACHE-PREVIEW-PERSIST]` cuando se persiste preview exitoso

### 2. `tests/test_regression.py` — Tests RO-CACHE-PREVIEW-08/09
- `test_preview_fallido_no_pisa_cache`: Preview fallido no debe sobrescribir
  cache con resultado exitoso previo
- `test_preview_exitoso_actualiza_cache`: Preview exitoso sí debe actualizar
  cache (regresión)

## Verificación
1. `python scripts/auto_validate.py` sin errores
2. `pytest tests/test_regression.py -v` todos pasan
