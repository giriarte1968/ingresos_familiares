# TAREA-002 — CTA gradiente verde + Reporte PDF valuación — Riesgo BAJO

## CONTEXTO

El CTA final de la landing ("Empezá ahora") usa gradiente `#064e3b → #022c22` que visualmente es casi negro. El usuario reporta que "el gradiente verde no se ve". CSS en `valu_design.py:851-859`.

Además, el detalle de propiedad muestra valor, rango, métricas, catastro e histórico, pero no existe forma de exportar un reporte PDF para analistas inmobiliarios. `fpdf2` ya está instalado (2.8.7).

## REGLA DE ORO

- No tocar motor de valuación
- No modificar tests de regresión
- No modificar landing.py, landing_content.py, valu_portfolio2.py
- PDF se genera en memoria (BytesIO), no escribe archivos
- Tests deben pasar sin cambios

## ALCANCE

| Archivo | Cambio |
|---------|--------|
| `valu_design.py:851-859` | Fix CSS `.final-cta` background verde visible |
| `valu_detail_sections.py` | Nueva función `generar_reporte_pdf(prop, res) -> bytes` |
| `valu.py:220-238` | Importar + botón descarga PDF |
| `docs/BITACORA_AGENTES.md` | Registrar |
| `docs/STATUS_ACTUAL.md` | Actualizar |
| `.opencode/plans/TAREAS_INDEX.md` | Agregar TAREA-002 |

## PASOS

### PASO 1: Fix gradiente verde CTA

**Archivo:** `valu_design.py` — bloque `.final-cta` (líneas 851-859)

- `circle at 20% 20%` → `circle at 50% 30%`
- `rgba(16,185,129,0.22)` → `rgba(16,185,129,0.35)`
- `linear-gradient(135deg, #0f172a, #111827)` → `linear-gradient(135deg, #065f46, #064e3b)`

**COMMIT:** `"FIX: CTA final gradiente verde visible #065f46->#064e3b"`

### PASO 2: Función generar_reporte_pdf

**Archivo:** `valu_detail_sections.py` — nueva función al final, antes de helpers

Usa `fpdf2` para generar PDF con:
- Header: nombre, dirección, tipo, zona, fecha
- Valor estimado USD + rango conservador/optimista
- Métricas: alquiler, cap rate, m² base, m² equiv.
- Factores: factor total, depreciación, NLP, calidad
- Comparables: n, precio/m² prom, distancia prom, confianza
- Catastro: PH, año, sección/manzana/gráfico
- Metadata: versión cache, fecha scraping, age blend

**COMMIT:** `"FEAT: funcion generar_reporte_pdf con fpdf2"`

### PASO 3: Botón descarga en detalle

**Archivo:** `valu.py` — función `mostrar_detalle_valu`

- Importar `generar_reporte_pdf`
- Insertar `st.download_button` entre `render_razonamiento` y `render_mapa_y_comparables`

**COMMIT:** `"FEAT: boton descargar reporte PDF en detalle propiedad"`

### PASO 4: Validación

- `python -m compileall valu.py valu_detail_sections.py valu_design.py`
- `pytest tests/test_regression.py -v --timeout=120`

## DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `docs/STATUS_ACTUAL.md`
- `.opencode/plans/TAREAS_INDEX.md`

## ENTREGABLES

- CTA con fondo verde visible
- Reporte PDF descargable desde detalle de propiedad
- Plan archivado en `.opencode/plans/TAREA-002.md`
