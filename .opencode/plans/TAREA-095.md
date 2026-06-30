# TAREA-095 — Fix "Restablecer Todos" no respeta motor — Riesgo BAJO

## CONTEXTO
Tras "Aplicar Selección", el botón "Restablecer Todos" no revertía el header al valor
base del motor. Posible fuga de estado desde preview/UI persistence.

## REGLA DE ORO
- No agregar botones nuevos.
- No cambiar interfaz.
- El header debe retornar al valor del motor tras reset.

## CAMBIOS

### 1. valu.py — Defensa adicional en _reset_all_ block (L775)
- Después de persistir, forzar `_auto_result` como `resultado` (self-ref limpio).
- Log `[DEBUG-RESET-CLEAN]` con valor final de `m2_base_venta`, `m2_microzona`,
  `n_propiedades`, y `_comp_exclusion_applied`.

### 2. valu.py — Asegurar limpieza de forzar_recalculo
- Si reset_key fue popeado exitosamente, limpiar forzar_recalculo del session_state
  para evitar re-ejecuciones infinitas.

### 3. Debug (Obligatorio)
- Flag `[DEBUG-RESET-CLEAN]` en valu.py.

### 4. Regression Test (Obligatorio)
- `test_reset_all_restores_motor_value` en test_regression.py.
  Verifica: motor base, exclusión aplicada, reset, verifica retorno a base.

### 5. Documentación (Obligatorio)
- BITACORA_AGENTES.md y STATUS_ACTUAL.md.

## TEST PLAN
pytest tests/test_regression.py -v
auto_validate
