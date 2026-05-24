# Performance Baselines

## Cold Start — Import + Valuación

| Operación | Max (ms) | Fecha baseline |
|-----------|----------|----------------|
| `import parsers.mercado_inmobiliario` | 200 | 2026-05-24 |
| `valuar_propiedad_v7` (1 prop) | 2500 | 2026-05-24 |

## Detail page render (desde StepLedger)

| Bloque | Max (ms) | Notas |
|--------|----------|-------|
| after_imports | 10 | imports lazy de valu_detail_sections |
| render_header | 10 | markdown estático |
| render_rango | 10 | markdown estático |
| render_metricas | 10 | markdown estático |
| render_razonamiento | 10 | texto narrativo |
| render_mapa_propiedad | 150 | folium map |
| render_tabla_comparables | 100 | dataframe pandas |
| generar_reporte_pdf | 200 | generación PDF |
| render_catastro | 10 | botón o datos catastrales |
| render_street_view | 5 | botón link |
| render_historial | 50 | carga historial + plotly |

## Regla

Si un bloque excede el `Max` por más de 1s, el cambio requiere optimización o actualización consciente del baseline en `auto_validate.py`.
