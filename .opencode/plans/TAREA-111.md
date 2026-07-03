# TAREA-111: Estabilización de Percentiles vía CV Normalizado por Macrozona

**Riesgo:** BAJO  
**Estado:** COMPLETADA  
**Fecha:** 2026-07-03

## Contexto
El sistema usaba umbrales universales de CV (0.25, 0.35, 0.45) para seleccionar percentil, causando saltos bruscos de precio (~$20k USD) al cambiar la ventana de tiempo (Natural→Retro) porque el aumento de muestra disparaba el paso a P50 sin considerar la dispersión real de la zona.

## Solución
Se introdujo **CV de referencia por macrozona** (`cv_ref`) y se selecciona percentil según ratio `cv_actual / cv_ref`:

- n≥10 y ratio < 1.10 → P50
- n≥8  y ratio < 1.30 → P45
- n≥5  y ratio < 1.60 → P40
- else → P33

## Archivos modificados
| Archivo | Cambio |
|---------|--------|
| `data/zonas_depreciacion.json` | Nuevo campo `cv_ref` en cada macrozona |
| `parsers/cluster_filters.py` | `seleccionar_percentil_por_calidad_pool()` acepta `cv_ref` opcional |
| `parsers/mercado_inmobiliario.py` | Nueva función `obtener_cv_ref()` + cache `_CV_REF_CONFIG` |
| `valu.py` | UI editable para `cv_ref` en expander "Ajuste por Tamaño" |
| `tests/test_cluster_filters.py` | 6 nuevos tests ratio-based |
| `tests/test_regression.py` | 2 nuevos tests (`test_percentil_ratio_mabel_p50`, `test_percentil_ratio_obtener_cv_ref`) |
| `docs/ALGORITMOS.md` | Documentada nueva regla de percentil dinámico |
| `docs/BITACORA_AGENTES.md` | Registro de implementación |

## Validación
- 63/63 regression tests pasan
- auto_validate OK
