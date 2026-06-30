# TAREA-096 — Header oculta valuación si < 3 comps — Riesgo BAJO

## CONTEXTO
Con flex OFF, el motor solo encuentra 2 comps (3-dormitorio en PN).
El header muestra una valuación con esos 2 comps, pero el botón
"Aplicar selección" dice "Mínimo 3" (disabled). Esto es inconsistente:
si el mínimo para aplicar es 3, el header no debería mostrar valuación.

### Problemas detectados
1. `render_tabla_comparables:499`: `if n_sel == n_total` se activa con
   2 comps → footer muestra "Motor de selección" en vez de informar
   que faltan comps.
2. `render_header`: No hay guard para < 3 comps → siempre muestra
   el valor del motor.
3. `mostrar_detalle_valu`: `render_rango`/`render_metricas` se ejecutan
   si `valor_usd > 0`, pero no hay check de `n_propiedades < 3`.

## CAMBIOS

### 1. `valu_detail_sections.py:499` — Footer preview
Cambiar `if n_sel == n_total:` → `if n_sel == n_total and n_sel >= 3:`.
Para 2 comps, cae a `elif len(selected_comps) >= 2:` → `calcular_vm2_por_seleccion`
retorna fallback → footer dice "Valor original del pool • 2 comps (mín. 3 req.)".

### 2. `valu_detail_sections.py:render_header` — Ocultar valuación
Si `n_comps < 3`, setear `v_auto=0`, `v_manual=0`, `m2_microzona=0`,
`m2_micro_auto=0`, `m2_line_auto="—"`.

### 3. `valu.py:mostrar_detalle_valu` — Ocultar rango y métricas
Si `n_propiedades < 3`, setear `valor_usd=0` para que `render_rango`
y `render_metricas` no se ejecuten. Mostrar warning de insuficientes.

### 4. Debug flag `[DEBUG-INSUF-COMPS]`

### 5. Regression test
`test_min_3_comps_for_valuation`: verifica que header/valor/rango
se ocultan con < 3 comps.

### 6. Docs: BITACORA_AGENTES.md, STATUS_ACTUAL.md

## RIESGO
BAJO. Solo afecta display; no toca motor ni persistencia.
