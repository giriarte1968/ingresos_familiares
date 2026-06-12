# TAREA-041: Preview valuation — toggles Retro/Flex sin persistir en Pendiente

## Estado: COMPLETADA

## Pasos

### Paso 1: `persistir_valuacion(commit=False)` ✅
- **Archivo**: `parsers/valuacion_cache.py:123`
- Parámetro `commit: bool = True`
- `commit=False` → solo cache, no escribe `_ultima_valuacion` en `propiedades.json`

### Paso 2: `valuar_con_cache(preview=True)` ✅
- **Archivo**: `parsers/motor_vpp_core.py:1333`
- Parámetro `preview: bool = False`
- Pasa `commit=not preview` a `persistir_valuacion`
- Guarda `preview` en `_cache` metadata

### Paso 3: Retro Flexible OR logic ✅
- **Archivo**: `parsers/mercado_inmobiliario.py:977,1044`
- Ya implementado: `(dormitorios in flex_dormitorios or dormitorios == dorms)` — OR inclusion

### Paso 4: valu.py — toggles setean `preview_mode` ✅
- Toggle Retro/Flex: setea `forzar_recalculo=True` + `preview_mode=True`
- "Aplicar cambios": setea `forzar_recalculo=True`, limpia `preview_mode`
- `mostrar_dashboard`: pasa `preview=preview_mode` a `valuar_con_cache`

### Paso 5: Validación ✅
- `python scripts/auto_validate.py` → OK
- Regression tests → OK
- Syntax → OK
- Imports → OK
- Performance → OK

## Comportamiento esperado
- **Pendiente + toggle Retro/Flex**: comps visibles inmediatamente, portfolio sigue Pendiente
- **Pendiente + "Aplicar cambios"**: portfolio muestra valuada
- **Ya valuada + toggle**: comps visibles, portfolio sigue valuada (sin cambios de comportamiento)
