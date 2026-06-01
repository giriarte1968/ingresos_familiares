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

### PASO 3 — Commit y push

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

## Historial de cambios

| Fecha | Cambio |
|-------|--------|
| 2026-05-30 | TAREA-020: Creación de `scripts/corregir_coords_cache.py` |
| 2026-05-31 | TAREA-021: Mejora de `extraer_calle_numero()` + guardar `calle_limpia`/`numero_limpio` |
| 2026-05-31 | Fix: "Santa Fe" como calle (no provincia) en parser |
