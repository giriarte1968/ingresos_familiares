# TAREA-021 — Mejorar `extraer_calle_numero` + re-corregir cache — Riesgo BAJO

## CONTEXTO

TAREA-020 corrigió coordenadas vía centroide para 3.289 propiedades. Pero dejó **~5.559 sin PH match** porque `extraer_calle_numero` produce street names corruptos:

```
"Alvear bis 199, Rosario, Santa Fe" → ("alvear bis provincia de", 199) ✗
"Iriondo 1571- Unidad 01-02"        → ("iriondo unidad", 1571)        ✗
"Brown 2700, Rosario, Santa Fe"     → ("brown rosario", 2700)         ✗
```

Si `extraer_calle_numero` produjera `(calle, num)` limpios, el pipeline de `buscar_ph()` + centroide podría matchear más entradas, corregir más coordenadas, y esas propiedades llevarían su PH y año correcto a las valuaciones.

El motor de valuación (`enriquecer_anio_comparable`) NO se toca — ya funciona con `_extraer_interseccion`. Solo se mejora la calidad de los datos en cache.

## REGLA DE ORO

- `pytest` pasa
- `_extraer_interseccion` NO se modifica
- `enriquecer_anio_comparable` NO se modifica
- `_token_contenido` NO se modifica
- Solo se toca `extraer_calle_numero` + el script de corrección

## ALCANCE

| Archivo | Cambio |
|---|---|
| `parsers/mercado_inmobiliario.py` — `extraer_calle_numero` | Limpiar city/provincia/garbage del street name |
| `parsers/mercado_inmobiliario.py` — `_filtrar_calle_diccionario` | Agregar patrones de limpieza (opcional si ya existen) |
| `scripts/corregir_coords_cache.py` | Guardar `(calle, num)` limpio en cada entry corregido |
| `cache_scraping.json` | Re-corregido con más matches |
| `tests/test_regression.py` | Si cambian valores, expandir rangos |

---

### PASO 1: Mejorar `extraer_calle_numero`

**Archivo:** `parsers/mercado_inmobiliario.py` — función `extraer_calle_numero`

Después de extraer `(cn, num)`, aplicar limpieza que remueva estos tokens finales:
- `rosario`, `santa fe`, `santa fe argentina`, `argentina`, `provincia de santa fe`
- `unidad`, `departamento`, `dpto`, `local`, `oficina`, `piso`, `depto`, `casa`, `ph`
- `al ` (al 1200 → que no se pegue a la calle)

**Lógica:**
1. Tomar `cn` crudo de `extraer_calle_numero`
2. Tokenizar y remover los tokens basura del final
3. Retornar `(cn_limpio, num)`

**Verificar:**
```python
extraer_calle_numero("Alvear bis 199, Rosario, Santa Fe")  → ("alvear bis", 199)
extraer_calle_numero("Iriondo 1571- Unidad 01-02")         → ("iriondo", 1571)
extraer_calle_numero("Brown 2700, Rosario, Santa Fe")      → ("brown", 2700)
```

**No tocar** `_filtrar_calle_diccionario` (ese limpia cosas distintas como "avenida"→"av.").

---

### PASO 2: Guardar `(calle, num)` limpio en cache + re-ejecutar corrección

**Archivo:** `scripts/corregir_coords_cache.py`

Al final del loop de corrección (después de `buscar_ph`), guardar en cada entry:
```python
p['calle_limpia'] = cn_limpio
p['numero_limpio'] = num_limpio
```

**Ejecutar:** `python scripts/corregir_coords_cache.py`

**Verificar:** Comparar stats pre/post de cuántos PH se matchearon.

---

### PASO 3: Actualizar tests

**Archivo:** `tests/test_regression.py`

Si los nuevos matches de PH cambian coordenadas de algún comparable usado en los tests de valuación, expandir rangos.

**Verificar:** `pytest tests/test_regression.py -v`

---

## VALIDACION FINAL

```
☐ pytest pasa (39 tests)
☐ extraer_calle_numero("Alvear bis 199, Rosario, Santa Fe") → ("alvear bis", 199)
☐ extraer_calle_numero("Iriondo 1571- Unidad 01-02") → ("iriondo", 1571)
☐ corregir_coords_cache.py corre más PHs que antes
☐ cache_scraping.json tiene campo calle_limpia y numero_limpio
```

## DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `docs/STATUS_ACTUAL.md`
- `docs/DICCIONARIO_DATOS.md` (nuevos campos calle_limpia, numero_limpio)
- `.opencode/plans/TAREAS_INDEX.md`
