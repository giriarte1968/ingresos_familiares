# TAREA-123: Fix 🔄 Limpiar borra valuación manual (RU-CLEAN-MANUAL-01)

## Descripción
El botón "🔄 Limpiar" dentro del expander "📊 Valuación por Comparables" borraba TODO el `_ultima_valuacion`, incluyendo la valuación manual guardada.

## Contexto
TAREA-088 (`617b699`) ya intentó arreglar esto pero el fix no contempló el escenario:
1. Usuario guarda valuación manual (fuente=manual, valor_usd=$735K)
2. Usuario abre expander 📊 Valuación por Comparables
3. Usuario hace clic en "🔄 Limpiar"
4. `p.pop('_ultima_valuacion', None)` borra TODO
5. La propiedad vuelve a estado Pendiente, perdiendo la manual

## Causa raíz
`valu.py:525` (antes del fix): `p.pop('_ultima_valuacion', None)` sin verificar `fuente`.

## Fix
**RU-CLEAN-MANUAL-01**: Si `tiene_manual` (fuente=manual o fuente_activa=manual), preserva claves esenciales en vez de hacer pop completo.

### Archivos modificados
- `valu.py:513-555`: Lógica de clean con preservación condicional
- `valu.py:2026-2056`: `_verificar_invariante_clean_comparables()` — guardrail post-clean
- `tests/test_regression.py`: 5 tests nuevos (2 lógica + 3 guardrail)

### DEBUG flags
- `[DEBUG-CLEAN-PRESERVE]`: Muestra valor preservado tras clean con manual
- `[GUARDRAIL-CLEAN]`: Confirmación POST-CLEAN de manual preservada

### Guardrail
- `_verificar_invariante_clean_comparables(uv, nombre)`: Detecta si manual fue borrada
- DEBUG: `[GUARDRAIL-EXCL]` con violación

### Tests
19/19 pasando:
- `test_clean_comparables_preserves_manual_valuation`: Lógica de preservación
- `test_clean_comparables_cleans_when_no_manual`: Sin manual, pop completo (no regression)
- `test_guardrail_clean_comparables_detects_violation`: Guardrail detecta violación
- `test_guardrail_clean_comparables_auto_corrects`: Casos borde del guardrail
- `test_guardrail_clean_comparables_integration`: Flujo completo con disco real
