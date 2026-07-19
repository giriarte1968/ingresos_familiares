# TAREA-138: Filtro ±10 Años Fijo para Comparables

## CONTEXTO

El filtro de edad (`_filtrar_por_ventana_edad`) fue deshabilitado en TAREA-078 porque "edad no es factor causal en Rosario". Sin embargo, análisis reciente muestra que propiedades viejas (24-49 años) en zonas mixtas se contaminan con comparables nuevos de precio distinto. Se solicitó un filtro **fijo de ±10 años** usando `antiquity` (Propia API) como fuente primaria.

## REGLA DE ORO

- **RO-03:** NO aplicar depreciación por antigüedad cuando la base viene de Ventana 3 (P33). El filtro ±10 NO es depreciación, es selección de comparables.
- **RO-08:** m2_microzona siempre cluster (Data-Driven). El filtro ±10 se aplica AL pool del cluster, no lo reemplaza.
- `pytest` pasa después de cada paso.

## ALCANCE

| Archivo | Cambio |
|---------|--------|
| `parsers/mercado_inmobiliario.py:977-1019` | Reescribir `_filtrar_por_ventana_edad` con ±10 fijo + `antiquity` |
| `parsers/mercado_inmobiliario.py:1428-1431` | Reemplazar bypass con call a `_filtrar_por_ventana_edad` |
| `parsers/mercado_inmobiliario.py:~1645` | Agregar `age_filter_applied`, `n_age_filtered` al meta dict |
| `tests/test_age_blend_filter.py` | Reescribir 5 tests para ±10 fijo |
| `tests/test_regression.py` | Verificar 55 tests pasan |
| `docs/ALGORITMOS.md:314-326` | Actualizar sección "Ventanas Progresivas de Edad" |
| `docs/BITACORA_AGENTES.md` | Agregar entrada TAREA-138 |
| `docs/STATUS_ACTUAL.md` | Actualizar estado |
| `.opencode/plans/TAREAS_INDEX.md` | Agregar TAREA-138 |

## PASOS

### PASO 1: Reescribir `_filtrar_por_ventana_edad`
- Ventana fija ±10 (no progresiva)
- Fuente primaria: `antiquity` (ANIO_ACTUAL - antiquity)
- Fallback: `anio_estimado` → `anio_construccion`
- `min_con_anio=10`
- Si pool filtrado < 10: retorna pool completo

### PASO 2: Rehabilitar call site (línea 1428)
- Reemplazar bypass con call a `_filtrar_por_ventana_edad`

### PASO 3: Agregar campos al meta dict
- `age_filter_applied`, `n_age_filtered`, `anio_min_filtro`, `anio_max_filtro`

### PASO 4: Actualizar tests
- Reescribir 5 tests en `test_age_blend_filter.py`

### PASO 5: Actualizar documentación
- ALGORITMOS.md, BITACORA_AGENTES.md, STATUS_ACTUAL.md, TAREAS_INDEX.md

## VALIDACION FINAL
- pytest pasa (55 tests)
- Filtro ±10 activo para Ayacucho
- Filtro NO afecta a propiedades nuevas
- Docs actualizados
