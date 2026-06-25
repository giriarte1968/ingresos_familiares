# TAREA-083: Fix colisión checkboxes ↔ motor de exclusión automática

## Fecha
2026-06-25

## Problema
El fix de checkboxes (condicional init en `valu_detail_sections.py:441`) desbloqueó los checkboxes visualmente, pero activó un camino automático de exclusión en `valu.py:664-674` que lee el estado de los widgets en cada rerun. Esto causa:

1. **Valor cae a 0**: Al desmarcar 1 de 2 comps, el motor detecta < 2 comps y setea `valor_propiedad_usd = 0`.
2. **Comparables desaparecen**: El motor devuelve resultado de `insuficientes_comparables`, alterando la lista de comps.
3. **Botón "Restablecer todas" desaparece**: La metadata de exclusión se pierde en el recálculo que produce el error.
4. **Antes no pasaba**: El bug anterior (sync forzado línea 441) congelaba los checkboxes, por lo que el motor nunca veía cambios.

## Causa raíz
`valu.py:664-674` implementa un camino de exclusión que **lee el estado actual de los widgets checkbox** y aplica el recálculo inmediatamente, sin esperar al botón "Aplicar selección". Esto es incorrecto: los checkboxes deben ser puramente visuales, y solo "Aplicar selección" debe disparar el recálculo.

## Solución
Eliminar la lectura automática de widget keys (`sel_comp_*`) en `valu.py`. Mantener solo la restauración de exclusiones persistidas (desde `resultado['_comp_excluded']` o `_ultima_valuacion`).

### Archivos a modificar
- `valu.py` — Eliminar bloque de lectura de widget state (líneas 661-674), mantener solo los caminos de restauración (675-679).
- `docs/BITACORA_AGENTES.md` — Registrar.
- `.opencode/plans/TAREAS_INDEX.md` — Agregar entrada.

### No se modifica
- `valu_detail_sections.py` — El fix condicional init se mantiene.
- `parsers/` — Sin cambios en el motor.

## Flujo resultante
1. **Desmarcar checkbox**: Cambio visual + "Valor/m² por selección" se actualiza. NO toca el motor.
2. **Click "Aplicar selección"**: Setea `comp_excluded_key` → `from_apply=True` → recálculo real.
3. **Restauración post-navegación**: Lee de `resultado['_comp_excluded']` o `_ultima_valuacion`.

## Validación
- `python scripts/auto_validate.py`: OK
- `pytest tests/test_regression.py -v`: 32/32 OK
- Verificar que checkboxes responden visualmente sin alterar valor.
- Verificar que "Aplicar selección" sigue funcionando.
