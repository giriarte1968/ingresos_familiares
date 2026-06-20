# TAREA-074 — Size Adjustment por Macrozona — Riesgo MEDIO

## CONTEXTO

El size_discount global actual (-5 a -15% para >100m²) es incorrecto para TODAS las macrozonas.
Análisis de cache_scraping (2024-2025, 8,297 propiedades venta) revela 3 patrones distintos:

| Macrozona | S =60 | M 60-100 | L 100-150 | XL =150 | Patrón |
|-----------|:-----:|:--------:|:---------:|:-------:|--------|
| centro_premium | ,814 | ,875 | ,054 | ,439 | U invertida |
| + Puerto Norte | ,733 | ,906 | ,451 | ,631 | **premio** |
| macrocentro | ,384 | ,078 |  |  | Acantilado -37% |
| norte | ,312 | ,338 |  | ,126 | Bañadera |
| oeste | ,050 |  |  |  | Declive |
| sur_default |  |  |  |  | Pendiente suave |

## REGLA DE ORO

- pytest pasa después de cada paso
- El anchor (m2_microzona) sigue siendo el driver principal de precio
- El cambio es exclusivo para venta (alquiler no se toca)
- auto_validate pasa antes del commit
- Los tests existentes se recalibran (38 tests)

## ALCANCE

| Archivo | Cambio |
|---------|--------|
| data/zonas_depreciacion.json | Agregar size_adjustment a las 5 macrozonas + subzona PN |
| parsers/mercado_inmobiliario.py | calcular_size_discount_venta() ? calcular_size_adjustment() config-driven |
| parsers/mercado_inmobiliario.py | Pasar macrozona+ancla_id desde valuar_propiedad_v7() |
| Admin UI | Editor de curvas size_adjustment en configuración |
| tests/test_regression.py | Recalibrar valores esperados |
| docs/SIZE_ADJUSTMENT.md | Documentación completa con justificación |
| docs/MEMORIA_PROYECTO.md | RO-19 size_adjustment per macrozona |
| docs/ALGORITMOS.md | Fórmula actualizada |
| docs/BITACORA_AGENTES.md | Registrar decisión |
| .opencode/plans/TAREAS_INDEX.md | TAREA-073 y TAREA-074 |

---

### PASO 1: Curvas size_adjustment en zonas_depreciacion.json

Agregar size_adjustment a cada macrozona con curvas piecewise lineales.
Puerto Norte como subzona de centro_premium con match por anchor_id.

### PASO 2: Renombrar y modificar función de descuento

calcular_size_discount_venta(m2_equiv) ? calcular_size_adjustment(m2_equiv, macrozona_id, ancla_id):
- Si no hay config ? 1.0
- match subzona por anchor_id ? usar curva de subzona
- Interpolación lineal entre puntos

### PASO 3: Pasar macrozona desde valuar_propiedad_v7()

La función ya determina macrozona_id (via resolver_macrozona). Pasar a calcular_size_adjustment().

### PASO 4: Admin UI para editar curvas

Sección "Configuración ? Ajuste por Tamaño" con st.data_editor y gráfico preview.

### PASO 5: Recalibrar tests

Actualizar valores esperados en test_regression.py. Validar Francia 250b.

### PASO 6: Documentación

docs/SIZE_ADJUSTMENT.md con metodología, datos, y justificación completa.

---

## VALIDACION FINAL

`
? pytest pasa (38 tests)
? Francia 250b valor > 
? auto_validate pasa
? docs/SIZE_ADJUSTMENT.md completo
`

## DOCS A ACTUALIZAR

- docs/BITACORA_AGENTES.md
- docs/MEMORIA_PROYECTO.md (RO-19)
- docs/ALGORITMOS.md
- docs/STATUS_ACTUAL.md
- docs/SIZE_ADJUSTMENT.md (nuevo)
- .opencode/plans/TAREAS_INDEX.md
