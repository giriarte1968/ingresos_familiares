# TAREA-077: Fix exclusión de comparables tras Guardar Valuacion Manual

## Problema
Tras hacer clic en "Guardar Valuacion Manual", el botón de exclusión de comparables
vuelve a mostrar "✅ Aplicar selección" en vez del estado previo "✅ Selección Aplicada".
Esto ocurre porque el handler de guardado manual no preserva `_comp_excluded` y
`_comp_exclusion_applied` del UV existente, y al limpiar el caché el recálculo
con `preview=True` produce un resultado fresco sin estado de exclusión.

## Diagnóstico
1. `valu_detail_sections.py:1465-1502`: El handler de guardado manual:
   - Hace `cache.pop(nombre)` → fuerza recálculo, perdiendo exclusión
   - Guarda solo `valor_usd`, `fuente`, `fuente_activa`, `manual_params` en UV
   - NO preserva explícitamente `_comp_excluded`, `_comp_exclusion_applied`,
     `auto_valor_usd`, `manual_valor_usd`
2. `parsers/valuacion_cache.py:198-201`: La lógica de preservación de exclusión
   en `persistir_valuacion` solo se activa cuando `manual_data` es provisto,
   pero el handler actual no usa `persistir_valuacion`.
3. `parsers/valuacion_cache.py:224-228`: Al restaurar `valor_usd`/`fuente` desde
   `old_uv`, no se restauran `_comp_excluded` ni `_comp_exclusion_applied`.

## Cambios

### 1. `valu_detail_sections.py` — Handler de Guardar Valuacion Manual
- NO limpiar el caché (preservar resultado completo con exclusión)
- Preservar explícitamente `_comp_excluded`, `_comp_exclusion_applied` desde UV existente
- Guardar `auto_valor_usd` (desde `auto_result`) y `manual_valor_usd`
- Agregar flags `[DEBUG-MANUAL]`

### 2. `parsers/valuacion_cache.py` — `persistir_valuacion`
- En bloque `if old_uv.get('manual_params'):` (L224-228),
  restaurar también `_comp_excluded` y `_comp_exclusion_applied` desde old_uv
- Agregar flag `[DEBUG-PERSIST]` al restaurar exclusión manual

### 3. `valu.py` — Restauración de exclusión (L703-710)
- Agregar flag `[DEBUG-EXCL-RESTORE]` adicional para trazar condiciones de restauración

## Verificación
1. `python scripts/auto_validate.py` sin errores
2. `pytest tests/test_regression.py -v` todos pasan
3. Prueba manual: abrir propiedad, aplicar exclusión, guardar manual, verificar que
   botón muestra "✅ Selección Aplicada"
