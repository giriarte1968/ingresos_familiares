# TAREA-011 — Normalización y calibración prudente de amenities + deduplicación NLP

## Estado: COMPLETADO ✅

## Cambios

### Centralización
- `parsers/mercado_inmobiliario.py`: Nueva función `calcular_delta_amenities()` + constantes `AMENITY_WEIGHTS` y `AMENITY_TOTAL_CAP=0.06`. Reemplaza bloque seguridad-aditivo en `calcular_factores()`.

### Taxonomía
- `parrilla` → `parrilla_propia` (+0.020) / `parrilla_compartida` (+0.005)
- Legacy `parrilla` → tratada como `parrilla_compartida`
- `valu_forms.py` y `app.py`: actualizados

### Pesos prudentes
| Amenity | Delta |
|---|---:|
| seguridad_24hs | 0.030 (antes 0.06) |
| seguridad_tag | 0.008 |
| seguridad_camaras | 0.006 |
| aberturas_premium | 0.020 |
| pileta | 0.015 |
| parrilla_propia | 0.020 |
| parrilla_compartida | 0.005 |
| terraza_compartida | 0.005 |
| sum | 0.010 |
| gym | 0.005 |

### Anti doble conteo NLP
- `parsers/nlp_inmobiliario.py`: `amenities_present` param, `AMENITY_NLP_EXCLUSION_MAP`
- Pesos NLP de amenities comunes reducidos drásticamente (0.01-0.02)
- `valuar_propiedad_v7()` pasa `detalles_categoria` al NLP

### Impacto en ancla
- Mabel: USD 78,776 (sin cambios, rango 75k-85k) ✓
- Ayacucho: USD 46,430 (sin cambios, rango 44k-50k) ✓
- 39/39 regression tests pasan, 11 nuevos tests de amenities

### Archivos modificados
- `parsers/mercado_inmobiliario.py`
- `parsers/nlp_inmobiliario.py`
- `datos_mercado.json`
- `valu_forms.py`
- `app.py`
- `docs/ALGORITMOS.md`
- `docs/BITACORA_AGENTES.md`
- `docs/STATUS_ACTUAL.md`

### Archivos nuevos
- `tests/test_amenities.py`
- `.opencode/plans/TAREA-011.md`
