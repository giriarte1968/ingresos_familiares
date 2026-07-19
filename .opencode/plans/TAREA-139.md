# TAREA-139: Fix umbral min_con_anio en filtro ±10

## CONTEXTO
El filtro ±10 años tiene `min_con_anio=10` como umbral para activarse. Cuando hay entre 1-9 comparables en rango, el filtro se desactiva y retorna el pool completo. Esto es incorrecto: si hay comparables en el rango, se deben mostrar.

Debug log de Mabel muestra:
```
[DEBUG-AGE-FILTER] pool_age_filtered < min (4 < 10), fallback a pool completo
```

Solo 4 comps están en 1988-2008 (±10 de 1998), pero el umbral de 10 impide activar el filtro.

## CAMBIO
Reducir `min_con_anio` de 10 a **1**. Si hay al menos 1 comparable en ±10 años, activar el filtro. Solo fallback si hay 0 comparables en rango.

## ARCHIVOS
- `parsers/mercado_inmobiliario.py:977` — default param
- `parsers/mercado_inmobiliario.py:1437` — call site
- `tests/test_age_blend_filter.py` — tests

## VERIFICACIÓN
1. pytest tests
2. Mabel en UI → ~4 comps en vez de 30
