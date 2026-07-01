# TAREA-098 — Header no debe cambiar en modo preview — Riesgo MEDIO

## Contexto
Al apagar "Todos los dormitorios" (Flex OFF), el motor se ejecuta en
modo preview y devuelve un resultado con 2 comparables. Aunque el usuario
NO aplicó la selección (era imposible porque < 3), el header se actualiza
con este valor preview, lo cual es incorrecto.

## Causa raíz
`mostrar_detalle_valu` usa el mismo objeto `resultado` tanto para el
header como para la tabla de comparables. En modo preview, el resultado
es el preview — no el valor oficial.

## Cambios

### 1. `valu.py` — Guardar resultado oficial tras commit (line 885)
Después de `persistir_valuacion(commit=True)`, guardar una copia del
resultado en `st.session_state[f'_official_result_{prop_name}']`.

### 2. `valu.py` — `mostrar_detalle_valu` usar oficial en preview
Si `preview_mode` es True y existe `_official_result`, usar ese resultado
para `render_header`, `render_rango` y `render_metricas`. Usar el
resultado preview solo para `render_tabla_comparables`.

### 3. `valu.py` — Limpiar oficial en "Limpiar" (line 511-536)
Agregar `st.session_state.pop(f'_official_result_{prop_name}', None)`
en el bloque de limpieza de comparables.

### 4. Debug flag `[DEBUG-OFFICIAL]`

### 5. Regression test
Nuevo test que verifica que toggle Flex no cambia el header.

## Riesgo
MEDIO. Se modifica la lógica de renderizado del header.
Requiere validación manual de que el header se actualiza correctamente
al aplicar selección y al limpiar.
