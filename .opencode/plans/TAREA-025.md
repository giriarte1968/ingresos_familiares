# TAREA-025 — PASO 3 en enriquecimiento: nearest PH misma calle por coordenadas — Riesgo BAJO

## CONTEXTO

Propiedades como "Centeno 1500" y "Alberdi 700" tienen `calle_limpia`/`numero_limpio` correctos, coordenadas correctas, pero el número específico no existe en el catastro de PHs. Los 3 pasos actuales fallan porque exigen match exacto de número (PASO 0), token containment + bloque ≤30m (PASO 1), o token + bloque ≤60m (PASO 2).

Solución: agregar PASO 3 que encuentra el PH más cercano con la **misma calle normalizada** por coordenadas, sin exigir bloque ni número exacto.

**Análisis:** De los ~1,747 que fallan PASO 0-2, **414 (23.9%)** tienen un PH en la misma `calle_limpia` a ≤60m (mediana: 14m). Ejemplos: Centeno (23m), Alberdi (7m), Iriondo (0m).

## REGLA DE ORO

- Solo se modifica `enriquecer_anio_comparable()`, no el motor de valuación
- `pytest tests/test_regression.py` pasa después del cambio
- Los valores de valuación NO cambian para propiedades que ya tenían año enriquecido
- El PASO 3 es el último recurso, solo si PASO 0-2 fallan

## ALCANCE

| Archivo | Cambio |
|---|---|
| `parsers/mercado_inmobiliario.py` | Agregar PASO 3 en `enriquecer_anio_comparable()` después de PASO 2 |
| `docs/POST_SCRAPING.md` | Agregar nota sobre PASO 3 en "Tareas que NO requieren acción post-scraping" |

## PASO 1: Agregar PASO 3 en `enriquecer_anio_comparable`

**Archivo:** `parsers/mercado_inmobiliario.py` — `enriquecer_anio_comparable()` (líneas 780-816, después de PASO 2)

**1.1** Insertar PASO 3 entre el cierre de PASO 2 y `return None`:

```python
    # ─── PASO 3: Nearest PH misma calle_norm por coordenadas ≤60m → MEDIA ───
    # Fallback cuando PASO 0-2 fallan: busca el PH mas cercano con la misma
    # calle normalizada (sin exigir bloque ni numero exacto)
    mejor_dist = float('inf')
    mejor_row = None
    for entry in cercanos_norm:
        r = entry['row']
        if not entry['cn']:
            continue
        # Misma calle normalizada: el cn del PH debe coincidir con el cn del comparable
        if not any(entry['cn'] == cn for cn, _ in calles if cn):
            continue
        d = calcular_distancia_km(lat, lon, r['latitud'], r['longitud']) * 1000
        if d < mejor_dist:
            mejor_dist = d
            mejor_row = r

    if mejor_row is not None and mejor_dist <= 60:
        return {
            'anio_estimado': int(mejor_row['year']),
            'ph_match': str(mejor_row.get('ph', '?')),
            'distancia_m': round(mejor_dist, 1),
            'confianza': 'MEDIA',
            'match_calle': True,
            'direccion_catastro': str(mejor_row.get('direccion_nominatim', ''))
        }
```

**COMMIT:** `"TAREA-025: PASO 3 - nearest PH misma calle por coordenadas ≤60m"`

**VERIFICAR:** `pytest tests/test_regression.py` (39 tests) + re-valuar propiedades test

## VALIDACION FINAL

```
☐ pytest tests/test_regression.py pasa (39 tests)
☐ python scripts/auto_validate.py OK
☐ Valuaciones de test (P1200, Brown, Mabel, Ayacucho, Vera, Entre Rios) sin cambios importantes
```

## DOCS A ACTUALIZAR

- `docs/POST_SCRAPING.md` — actualizar sección "Tareas que NO requieren acción post-scraping"
- `docs/BITACORA_AGENTES.md`
- `.opencode/plans/TAREAS_INDEX.md` (agregar TAREA-025)
