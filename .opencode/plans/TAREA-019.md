# TAREA-019 — Enriquecimiento años: filtro de bloque + PASO 2 a 60m

## CONTEXTO

El enriquecimiento 3-pasos (TAREA-015) usaba token containment + nearest-PH con un threshold único de 30m. Esto causaba dos problemas:

1. **Falsos positivos**: "Av. del Valle 2700" mapeaba a PH 6683 (2647, bloque 2600) a 22.8m — misma calle pero cuadra equivocada. Token containment no alcanzaba a filtrarlo.
2. **Falsos negativos**: "Av. del Valle 2700" correcto para PH 12549 (2799, bloque 2700) quedaba a 52.1m — fuera del rango de 30m. El error de geocoding del scraping (~20-30m del edificio real) sumado a la numeración no lineal de calles dejaba matches válidos fuera.

## SOLUCIÓN CONSERVADORA

| Paso | Threshold | Filtros | Confianza |
|---|---|---|---|
| PASO 0 (exacto) | ≤200m | (calle_norm, num) en `_CATASTRO_INDEX` | ALTA |
| PASO 1 (token) | ≤30m + **bloque** | Token containment + bloque | ALTA |
| PASO 2 (nearest) | ≤60m + **bloque** | Token + bloque + nearest | MEDIA |

El filtro de bloque:
- Extrae el número de altura del comparable y del PH
- Compara `(num // 100) * 100` — si difieren, el PH se descarta
- Para esquinas (sin número), se salta el filtro

## CAMBIO

| Archivo | Cambio |
|---|---|
| `parsers/mercado_inmobiliario.py` | `enriquecer_anio_comparable()`: +bloque en PASO 1, reemplazar PASO 2 con token+bloque+nearest a 60m |

## RESULTADOS SIMULACIÓN

**Brown 2750**: $306,681 (0.00%), enriquecidos 6/25 → 11/25
**Vera Mujica**: $48,873 → $53,031 (+8.51%)
**P1200**: $125,412 → $141,545 (+12.86%)
**Entre Ríos**: $77,446 → $72,325 (-6.61%)

Impacto aceptable: los cambios reflejan que los comparables ahora tienen años más precisos, activando el age-filter correctamente.
