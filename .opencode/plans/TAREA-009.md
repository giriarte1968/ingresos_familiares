# TAREA-009 — Conectar `P33_age_blend` para 5–7 comparables de edad — Riesgo MEDIO

## Contexto

`seleccionar_percentil_por_edad()` ya contempla `P33_age_blend` para 5–7 comparables, pero `_filtrar_por_ventana_edad()` tiene `min_con_anio=10`, impidiendo activar el camino cuando hay 5–7 comparables con año. Segunda ventana es ±20, debería ser ±30.

## Diagnóstico (Brown 2700 año 2010)
- ±15 años: 3 comparables
- ±30 años: 6 comparables
- `age_filter_applied: False` (nunca llega a 10 con año)
- `percentil_usado: P33` (pool completo con comparables 1968/1975)

## Cambio
1. `min_con_anio=10` → `min_con_anio=5`
2. Segunda ventana: 20 → 30
3. Simplificar control flow (return on first success, no best_pool tracking)
4. Fallback retorna `len(pool_con_anio)` en vez de 0

## Archivos
| Archivo | Cambio |
|---------|--------|
| `parsers/mercado_inmobiliario.py` | `_filtrar_por_ventana_edad()` |
| `tests/test_age_blend_filter.py` | Test nuevo: 6 comparables activan blend |
| `docs/*` | Actualizar |

## Commit: `544c598` (TAREA-008 parent)
