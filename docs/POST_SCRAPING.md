# POST_SCRAPING.md — Procedimiento post-scraping

> ⚠️ Cada vez que se genera un nuevo `cache_scraping.json` (scraping fresco), hay que ejecutar estos pasos.

## Flujo completo

```
Nuevo cache_scraping.json (raw desde portales)
         │
         ▼
  ┌─────────────────────────────┐
  │ PASO 1: corregir_coords     │
  │ python scripts/corregir_    │
  │       coords_cache.py       │
  └─────────────────────────────┘
         │
         ▼
  cache_scraping.json listo para valuar
  (coordenadas corregidas + calle_limpia/numero_limpio)
```

### PASO 1 — Corrección de coordenadas + parseo de direcciones

**Script:** `scripts/corregir_coords_cache.py`

**Qué hace:**
1. Backup automático de `cache_scraping.json` → `cache_scraping.json.bak` (y `.bak2` si ya existe `.bak`)
2. Carga centroides de parcelas desde `data/geometry/parcelas_seccion*_json.csv` (21 archivos, ~274k polígonos)
3. Carga catastro PH desde `data/rosario_avm_full.csv`
4. Para cada propiedad en `cache_scraping.json`:
   - Extrae `(calle, numero)` vía `extraer_calle_numero()`
   - Busca PH catastral por calle+bloque (mismo bloque primero, bloques adyacentes después)
   - Asigna `lat`/`lon` del centroide de la parcela del PH
   - Solo reemplaza si error >60m de la coordenada original
   - Guarda `calle_limpia` / `numero_limpio` en cada entry
5. Guarda `cache_scraping.json` actualizado

**Resultados esperados:**
- ~3,300 propiedades con coordenadas corregidas
- ~8,700+ propiedades con `calle_limpia`/`numero_limpio`
- ~1,300 propiedades sin PH catastral (sin cambio de coordenadas, sin `calle_limpia`)

**Dependencias:**
- `data/geometry/parcelas_seccion*_json.csv` — geometría parcelaria (generada por `parsers/infomapa_api.py` + uniones CSV)
- `data/rosario_avm_full.csv` — catastro PH con calles normalizadas

### PASO 2 — Verificación

```bash
python scripts/auto_validate.py
```

Confirma que:
- Tests de regresión pasan (39 tests)
- Sintaxis Python válida
- Imports correctos
- Performance aceptable

### PASO 3 (opcional) — Regenerar anclas

Si hay datos nuevos significativos en el scraping, se pueden regenerar las anclas:

```bash
# Desde Admin UI → pestaña Anclas → "Generar Nuevas Anclas"
# O via CLI:
python scripts/generar_anclas_grid.py --grid-size 400 --min-props 5
```

El generador produce un archivo timestamped `data/anclas_v7_AAAAMMDD_HHMMSS.json`.
Revisar el preview de cobertura en la UI. Si es满意, hacer clic en "Activar".

**NO** se sobreescribe el archivo activo directamente. La activación desde la UI:
1. Cambia `active_anchor_file` en `config/anclas_config.json`
2. Bump de `cache_version` (invalida valuaciones previas)
3. Recarga en memoria

### PASO 4 — Commit y push

```bash
git add -A
git commit -m "post-scraping: corregir coords + direcciones"
git push origin main
```

---

## Tareas que NO requieren acción post-scraping

| Tarea | Por qué |
|-------|---------|
| Enriquecimiento de año (PH→comparable) | Corre automático en cada valuación (Fase 1 del motor). PASO 3 (nearest PH misma calle por coordenadas ≤60m) también es automático. |
| Cap dinámico de factor_total | Es lógica del motor, no depende del scraping |
| Age blend / percentiles / filtros | Todo es lógica de valuación, no del cache |

### ⚠️ Advertencia sobre Comparables Manuales (TAREA-092)

Si se han cargado comparables manuales (`fuente="manual"`) vía **Configuración → Comparables Manuales**, un scraping fresco **los sobrescribirá**, ya que los scrapers reemplazan la lista completa `propiedades` de `cache_scraping.json`.

**Recomendación antes de scrapear:**
1. Hacer backup de `cache_scraping.json` (el script `corregir_coords_cache.py` ya genera `.bak` automáticamente).
2. Después del scraping, volver a añadir los manuales desde Configuración.
3. O bien restaurar `cache_scraping.json.bak` y fusionar manualmente.

## Historial de cambios

| Fecha | Cambio |
|-------|--------|
| 2026-06-29 | TAREA-092: Advertencia sobre comparables manuales y scraping |
| 2026-05-30 | TAREA-020: Creación de `scripts/corregir_coords_cache.py` |
| 2026-05-31 | TAREA-021: Mejora de `extraer_calle_numero()` + guardar `calle_limpia`/`numero_limpio` |
| 2026-05-31 | Fix: "Santa Fe" como calle (no provincia) en parser |
