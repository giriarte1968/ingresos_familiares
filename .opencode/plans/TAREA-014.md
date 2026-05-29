# TAREA-014 — Restrictive comparable year enrichment — Riesgo ALTO

## CONTEXTO

El TAREA-012 (3-step enrichment: token containment ≤50m + nearest PH + token ≤50m + esquina ≤30m) causó inflación de valores en P1200 ($137,888 → $190,957, +38%) porque:

1. Intersecciones (Paso 2) como "Sarmiento y Montevideo" a 209m recibían años de PHs cercanos y pasaban el age filter con $/m² más altos que los de Pellegrini
2. Esquina fallback (Paso 3) asignaba años sin validación de calle, contaminando el pool etario

Simulación restrictiva (≤20m, sin esquina) muestra P1200 en **$150,482**, solo +9% sobre baseline de $137,888.

## REGLA DE ORO

- `enriquecer_anio_comparable()` solo retorna año si hay alta confianza en el match
- No modificar ninguna otra función del motor (age filter, percentiles, IQR, etc.)
- Firma de función y formato de retorno idénticos
- `pytest tests/test_regression.py` pasa después del cambio
- La lógica de `_filtrar_por_ventana_edad` y `obtener_mediana_cluster_v2` no se toca

## CAMBIO

| Archivo | Cambio |
|---|---|
| `parsers/mercado_inmobiliario.py` | `enriquecer_anio_comparable()`: distancia máxima 20m, sin esquina |

## PASO 1: Modificar enriquecer_anio_comparable

**Archivo:** `parsers/mercado_inmobiliario.py` — función `enriquecer_anio_comparable` (líneas 591-717)

**1.1** Cambiar default `max_dist_m` de 50 a 20

**1.2** Paso 1 (token containment): solo ≤20m, siempre ALTA (eliminar bifurcación ALTA/MEDIA por distancia)

**1.3** Paso 2 (nearest + token validation): solo ≤20m, siempre MEDIA (eliminar camino `if mejor_dist < 30: conf = 'ALTA'`)

**1.4** Paso 3 (esquina fallback): eliminar completamente

```python
def enriquecer_anio_comparable(comp, max_dist_m=20):
```

## VALIDACION

```
☐ pytest tests/test_regression.py pasa (sin nuevas fallas)
☐ P1200 valuation ~$150k (simulación coincide)
☐ auto_validate.py OK
```

## DOCS A ACTUALIZAR

- `docs/ALGORITMOS.md` — §15 actualizar distancias y eliminar esquina
- `docs/BITACORA_AGENTES.md` — esta tarea
- `docs/STATUS_ACTUAL.md` — §14 actualizado
- `.opencode/plans/TAREAS_INDEX.md` — TAREA-014 agregada
