# TAREA-059: barrier_penalty faltante en ruta principal de comparables_reales

## Diagnóstico
El cache de valuación (`valuaciones_cache.json`) contenía `comparables_venta` sin el campo `barrier_penalty`. Esto ocurría porque la ruta principal (n≥2) de `obtener_mediana_cluster_v2` en `parsers/mercado_inmobiliario.py:1288` construía `comparables_reales` sin incluir `barrier_penalty` y con `precio_m2_ajustado` que excluía `_penalizacion_barrier`.

La ruta fallback (n<2, línea 1136) sí lo incluía, creando una inconsistencia.

## Cambios realizados

### `parsers/mercado_inmobiliario.py`
- **Línea 1293** (insertado): `'barrier_penalty': round(p.get('_penalizacion_barrier', 1.0), 4),`
- **Línea 1294** (modificado): `'precio_m2_ajustado': round(p.get('valor_m2', 0) * p.get('_time_adjustment', 1.0) * p.get('_penalizacion_barrier', 1.0), 2),`

### `data/valuaciones_cache.json`
- Eliminado para forzar regeneración con el nuevo formato.

## Efecto esperado
- Preview de Francia 250b (2 comps) → **$4,262** (MEDIA con penalización 0.97)
- Badge **BARRERA(3%)** visible
- Delta **$0** vs header
- Todas las futuras valuaciones guardan `barrier_penalty` en cache

## Commit
`2257b0f` — main
