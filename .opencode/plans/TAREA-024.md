# TAREA-024 — Mejora matching catastral: normalización acentos/ñ en token + fix "bis" — Riesgo BAJO

## CONTEXTO

Al ejecutar `corregir_coords_cache.py`, 1,278 propiedades en `cache_scraping.json` quedan sin match de PH catastral. Diagnóstico reveló dos causas principales:

1. **`_token_contenido()`** comparaba tokens sin normalizar mayúsculas/acentos — aunque `extraer_calle_numero` ya normaliza, `_token_contenido` es llamado desde `enriquecer_anio_comparable()` y otras rutas donde los tokens pueden venir sin normalizar
2. **"bis" pegado a la calle** — "Wilde 455 Bis" → `cn="wilde bis"` en vez de `cn="wilde"` porque "bis" no estaba en `_RE_GARBAGE_WORDS`

## REGLA DE ORO

- Solo se modifican funciones de matching/extracción, NO el motor de valuación
- `pytest tests/test_regression.py` pasa después del cambio
- Los valores de valuación NO cambian (el matching afecta año de construccion y coordenadas, no la fórmula)

## ALCANCE

| Archivo | Cambio |
|---|---|
| `parsers/mercado_inmobiliario.py` | `_token_contenido()`: normalizar tokens (lowercase + NFKD) antes de comparar |
| `parsers/mercado_inmobiliario.py` | `_RE_GARBAGE_WORDS`: agregar "bis" |

## PASO 1: Normalizar acentos/ñ en `_token_contenido`

**Archivo:** `parsers/mercado_inmobiliario.py` — `_token_contenido()` (líneas 569-590)

**1.1** Agregar función `norm(t)` interna que lowercase + NFKD-strip-accents

**1.2** Aplicar `norm()` a ambos sets de tokens antes de iterar

## PASO 2: Agregar "bis" a `_RE_GARBAGE_WORDS`

**Archivo:** `parsers/mercado_inmobiliario.py` — `_RE_GARBAGE_WORDS` regex (línea 94-102)

**2.1** Agregar `bis` al final de la lista de palabras basura

## PASO 3: Re-ejecutar `corregir_coords_cache.py` sobre `cache_scraping.json`

**3.1** Ejecutar con backup automático

**3.2** Verificar cuántos PHs nuevos se encontraron vs corrida anterior

## VALIDACION FINAL

```
☐ pytest tests/test_regression.py pasa
☐ python scripts/auto_validate.py OK
☐ corregir_coords_cache.py muestra mejora en PHs encontrados
```

## DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `.opencode/plans/TAREAS_INDEX.md` (agregar TAREA-024)
