# TAREA-128: Desacoplar Ct del Anchor — Valuación Manual con Ct runtime

## CONTEXTO

### Problema
El anchor de_mayo_sur tiene usd_m2=2041, calculado el 2026-06-01 con un ct_table que ya no existe (TAREA-113 lo elimino). El Ct old inflaba propiedades viejas mas que el Ct new (ct_annual_rate), creando una brecha del 24% entre la valuacion manual ($83,851) y el auto engine ($67,544) para la propiedad Mabel.

### Causa raiz
- **Anchor**: usd_m2 = MEDIANA(valor_m2 x Ct_old) — Ct embebido, estatico
- **Cluster**: Usa ct_annual_rate de zonas_depreciacion.json — Ct dinamico
- **Manual**: Usa nchor.usd_m2 directamente — sin Ct en runtime

### Objetivo
Cuando se actualice ct_annual_rate, los anclas NO necesiten regenerarse. El Ct se aplica en runtime.

## REGLAS DE ORO
- pytest pasa despues de cada paso
- Backward compatibility: params guardados con usd_m2 legacy siguen funcionando
- El anchor mantiene usd_m2 legacy para fallback
- uto_validate.py pasa antes de commit

## ALCANCE

| Archivo | Cambio |
|---------|--------|
| scripts/generar_anclas_grid.py | Agregar usd_m2_raw, vg_meses al output |
| parsers/mercado_inmobiliario.py | generar_resultado_manual(): usar usd_m2_raw x ct |
| parsers/location_engine.py | calcular_precio_m2(): soportar usd_m2_raw |
| alu_detail_sections.py | UI: calcular y mostrar valor efectivo |
| data/anclas_v7_*.json | Regenerar con nuevos campos |
| 	ests/test_regression.py | Tests de Ct runtime |
| docs/ALGORITMOS.md | Documentar Ct runtime |
| docs/BITACORA_AGENTES.md | Entrada TAREA-128 |
| .opencode/plans/TAREAS_INDEX.md | Nueva entrada |

---

### PASO 1: Actualizar generador de anclas

**Archivo:** scripts/generar_anclas_grid.py

**Cambios:**
1. Lineas 124-135: Agregar meses al dict de cada propiedad (ya existe)
2. Lineas 159-163: Calcular usd_m2_raw = mediana de alor_m2 (sin Ct)
3. Linea 195-207: Agregar usd_m2_raw y vg_meses al output

**Verificacion:** Ejecutar python scripts/generar_anclas_grid.py y verificar que el JSON de salida tiene los nuevos campos.

---

### PASO 2: Regenerar anclas

**Archivo:** data/anclas_v7_*.json

**Accion:** Ejecutar el generador para producir nclas_v7_YYYYMMDD_HHMMSS.json con los nuevos campos.

**Verificacion:** Verificar que los 322 anclas tienen usd_m2_raw y vg_meses.

---

### PASO 3: Actualizar generar_resultado_manual()

**Archivo:** parsers/mercado_inmobiliario.py, funcion generar_resultado_manual() (linea 3990)

**Cambios:**
1. Importar calcular_ct y 
esolver_macrozona
2. Obtener usd_m2_raw del anchor (con fallback a usd_m2)
3. Calcular Ct basado en la edad de la propiedad
4. Aplicar: usd_m2_effective = usd_m2_raw x ct

**Verificacion:** Test manual con Mabel: usd_m2_raw del anchor x Ct de la propiedad.

---

### PASO 4: Actualizar UI del formulario manual

**Archivo:** alu_detail_sections.py, lineas 1245-1377

**Cambios:**
1. Linea 1369: Calcular effective_usd_m2 cuando se selecciona anchor
2. Mostrar valor efectivo en el number_input
3. Habilitar campo para override manual

**Verificacion:** Abrir UI, seleccionar anchor, verificar que el campo muestra el valor efectivo.

---

### PASO 5: Actualizar calcular_precio_m2() en location_engine

**Archivo:** parsers/location_engine.py, funcion calcular_precio_m2() (linea 54)

**Cambios:**
1. Linea 84: Usar usd_m2_raw si existe, con fallback a usd_m2
2. El caller debe aplicar Ct por separado si es necesario

**Verificacion:** Verificar que el fallback del cluster sigue funcionando.

---

### PASO 6: Tests

**Archivo:** 	ests/test_regression.py

**Tests a agregar:**
1. 	est_ct_runtime_manual_valuation: Verificar que generar_resultado_manual aplica Ct correctamente
2. 	est_anchor_raw_fields: Verificar que los anclas nuevos tienen usd_m2_raw
3. 	est_ct_macrozona_direccionalidad: Verificar Ct positivo para "sur", negativo para "norte"

---

### PASO 7: Documentacion

**Archivos:**
- docs/ALGORITMOS.md: Seccion 6.5 — actualizar Ct runtime
- docs/BITACORA_AGENTES.md: Entrada TAREA-128
- .opencode/plans/TAREAS_INDEX.md: Nueva entrada

---

### PASO 8: Validacion y commit

1. Ejecutar python scripts/auto_validate.py
2. Ejecutar pytest tests/test_regression.py -v
3. Verificar manualmente con Mabel: auto ~$67K, manual ~$76K (con Ct correcto)
4. Commit: "TAREA-128: Desacoplar Ct del anchor — Ct runtime en valuacion manual"
5. Push a GitHub

---

## RIESGOS

| Riesgo | Mitigacion |
|--------|------------|
| Aproximacion del Ct: pool tiene propiedades de edades mixtas | Para propiedades nuevas Ct~1.0, buena approx. Para viejas, error aceptable |
| Backward compatibility: params guardados con usd_m2 legacy | Detectar usd_m2_raw faltante y calcular desde usd_m2 / ct_old |
| Anclas sin macrozona valida | get_ct_rate() tiene fallback a -0.02 |
| calcular_precio_m2() en location_engine afecta cluster fallback | Cambio coordinado en PASO 5 |

---

## NOTA: Fix bug auto card blank (completada)

El bug del auto card blank (commit 6f78756) fue causado por el guardrail _verificar_invariante_auto_valor_usd que detectaba falsos positivos. Ya esta resuelto y hecho push.
