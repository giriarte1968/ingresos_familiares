# TAREA-069b: Ghost State — Limpieza de Widget Keys en Session State

## Problema
La inconsistencia persistía después de TAREA-069 (Cache Inspection). El flag `_cache.preview` se inspeccionaba correctamente, pero **widget keys de Streamlit** (`retro_btn_{name}`, `flex_btn_{name}`) sobrevivían entre sesiones.

## Root Cause
Cuando un botón con `key=f'retro_btn_{name}'` es clickeado, Streamlit guarda `st.session_state['retro_btn_X'] = True`. Si el usuario navega al Portfolio (donde el botón no se renderiza), la clave persiste. Al re-ingresar, `retro_btn_clicked = True` salta el bloque Pendiente.

## Solución
1. Función `_limpiar_estado_propiedad(nombre)` en `valu.py`: limpia TODAS las claves de sesión asociadas (27 prefijos fijos + `sel_comp_{name}_*`)
2. Aplicar en: query param handler, `_ir_a_detalle`, sidebar nav, Pendiente block, ambos Volver, Clean flow

## Archivos modificados
- `valu.py`: función + aplicación en 5 puntos
- `valu_portfolio2.py`: `_ir_a_detalle`
- `valu_detail_sections.py`: `render_actions`
