# TAREA-012 — Regla estricta de fuente de año para comparables

## Objetivo
Reemplazar la lógica de `enriquecer_anio_comparable()` con reglas estrictas: años de scraping → ALTA confianza, años de AVM → MEDIA confianza solo con matching riguroso (misma calle+numero exacto o misma calle+≤20m).

## Cambios en código

### `parsers/mercado_inmobiliario.py`

1. **`normalizar_calle_nombre(direccion)`** — nueva helper:
   - lowercase, sin tildes, sin puntuación
   - Normaliza "Av"/"Avenida" → removido
   - Normaliza "Bv"/"Bulevar" → removido
   - Elimina prefijos honoríficos (Almirante, General, San, Doctor, etc.)
   - Colapsa espacios múltiples

2. **`extraer_calle_numero(direccion)`** — nueva helper:
   - Extrae (calle_normalizada, numero_int) de direcciones libres
   - Maneja "al 2100", "Piso X", "4º X" (ordinales), intersecciones
   - Retorna (None, None) si no hay dirección válida

3. **`obtener_anio_scraping(comp)`** — nueva helper:
   - Busca año en: `anio_construccion` → `anio_estimado` → `year` → `antiguedad` (ANIO_ACTUAL - antiguedad)
   - Valida rango 1900-2027
   - Retorna dict con `anio_estimado`, `source='scraping'`, `confianza='ALTA'`, `match_tipo='campo_scraping'`

4. **`enriquecer_anio_comparable()` reescrita**:
   - Primero: `obtener_anio_scraping()` → ALTA si tiene año
   - Segundo: sin lat/lon → None
   - Tercero: Regla A (calle+número exactos) → MEDIA
   - Cuarto: Regla B (calle+número distinto, distancia ≤20m) → MEDIA
   - Resto: None

5. **Call site (FASE 1)**:
   - Contadores: `n_anio_source_scraping`, `n_anio_source_avm`, `n_anio_source_none`
   - Metadata en `comparables_reales`: `anio_source`, `anio_confianza`, `anio_match_tipo`, `anio_distancia_match`, `anio_ph_match`, `anio_direccion_catastro`
   - Contadores en `meta`: `n_con_anio_scraping`, `n_con_anio_avm`, `n_con_anio_none`

6. **Fix bug**: `radio_usado: None` crash en `generar_razonamiento_valuacion()` → `if radio is None: radio = 300`

### `tests/test_age_enrichment.py` (nuevo, 26 tests)
- 4 tests: `normalizar_calle_nombre`
- 5 tests: `extraer_calle_numero`
- 6 tests: `obtener_anio_scraping`
- 4 tests: `enriquecer_anio_comparable` (scraping priority, sin latlon, sin calle, calle distinta)
- 2 tests: AVM reglas (calle+numero exactos, normalización permite match)

## Efectos colaterales esperados

### Regression tests que cambian (5/39 FAIL):
| Test | Antes ($) | Después ($) | Causa |
|------|-----------|-------------|-------|
| `test_mabel_venta` | ~79k | ~88,920 | 3/79 comps con AVM años (3.8%) |
| `test_patio_grande_vera` | ~52k | ~39,531 | Menos años → sin age filter → P33 |
| `test_ui_vs_python_no_diverge` | ~79k | ~88,920 | Misma causa |
| `test_alquiler_p1200_con_discount` | ~873k | ~945,806 | Menos años → sin age filter |
| `test_fase1_no_cambia_valores` | ~79k | ~88,920 | Misma causa |

**NO actualizar tests de regresión sin autorización humana** (per TAREA reglas).

### `pct_con_anio`
- Mabel: ~50% → ~3.8% (3/79 comps con AVM años)
- Esto es intencional: la tarea prioriza confianza sobre cobertura

## Archivos modificados
- `parsers/mercado_inmobiliario.py` — helpers + enriquecer_anio_comparable reescrita + fix radio_usado
- `tests/test_age_enrichment.py` — nuevo, 26 tests

## Docs actualizados
- `docs/BITACORA_AGENTES.md` — entrada TAREA-012
- `docs/ALGORITMOS.md` — Sección "Fuentes de año de comparables"
- `docs/STATUS_ACTUAL.md` — Sección 15
- `docs/DICCIONARIO_DATOS.md` — campos nuevos
- `.opencode/plans/TAREAS_INDEX.md` — entrada TAREA-012
