# 📝 BITÁCORA DE AGENTES — AVM ROSARIO

Este documento es el "diario de trabajo". Cada agente de IA que trabaje en este proyecto debe registrar aquí el progreso para que el siguiente sepa exactamente dónde retomar.

---

## 📅 2026-05-24 — MONUMENTO A LA BANDERA EN 3RA FEATURE CARD

### Objetivo:
Reemplazar la foto de la tercera card de features (Infomapa Rosario) por el Monumento a la Bandera.

### Acciones realizadas:
1. Cambio de icono en `landing_content.py` línea 281: Unsplash `photo-1524661135-423995f22d0b` → Pexels `29342907` (Monumento a la Bandera)
2. `python scripts/auto_validate.py` OK
3. `pytest tests/test_regression.py` 39/39 passed
4. Commit `2238cfa` + push a `origin main`

### Verificado:
- Nested Mapa expander dentro de Comparables en valu.py:253 intacto

---

## 📅 2026-05-11 — REFACTORIZACIÓN LANDING PAGE A PLANTILLAS DINÁMICAS

### Objetivo:
Reemplazar constantes estáticas de HTML por funciones generadoras que inyecten datos reales del motor de valuación (VPP).

### Acciones realizadas:
1. **Refactorización de `landing_content.py`**:
   - Reemplazo de cadenas estáticas por funciones (`get_hero_html`, `get_example_html`, etc.).
   - Creación de `get_landing_stats()` para leer `cache_scraping.json` y `propiedades.json`.
   - Se removieron emojis y se implementaron SVGs inline.
2. **Refactorización de `landing.py`**:
   - Cambio del flujo de renderizado para llamar a las funciones.
   - El botón CTA se movió al interior de `landing.py` antes del footer.
3. **Estilos en `valu_design.py`**:
   - Incorporación de las clases faltantes para la tarjeta de ejemplo y el hero (`.mockup-card`, `.mockup-price`, etc.).

---

## 📅 2026-05-11 — IMPLEMENTACIÓN DE LANDING PAGE PROFESIONAL (AVM)

### Objetivo:
Crear una página de aterrizaje (landing page) inspirada en Zillow/Redfin para presentar Valu a nuevos usuarios, explicando la propuesta de valor y las limitaciones del modelo estadístico.

### Acciones realizadas:
1. **Nuevo Módulo** `landing_content.py`:
   - 9 secciones HTML (Hero, Problema, Cómo funciona, Features, Ejemplo Real, Target, Trust/Disclaimer, CTA, Footer).
   - Uso de tipografía Inter y paleta de colores corporativa (Navy/Emerald).
   - Implementación de animaciones de scroll (Reveal on scroll) mediante Intersection Observer.

2. **Estilos** en `valu_design.py`:
   - Definición de `LANDING_CSS` con variables CSS, grids responsivos y animaciones.

3. **Routing en `valu.py`**:
   - Implementación de estado `vista_actual` para alternar entre Landing y Dashboard.
   - Ocultamiento de sidebar de Streamlit durante la visualización de la landing.
   - Botón "Volver al Inicio" integrado en el sidebar del dashboard.

4. **Transparencia y Trust**:
   - Sección explícita de "Lo que Valu es y lo que no es" para gestionar expectativas del usuario.

### Resultados:
- Experiencia de onboarding mejorada para nuevos usuarios.
- Diseño profesional y responsivo que eleva la percepción de marca.
- Mayor claridad sobre la metodología estadística (modelo hedónico) vs IA.

---

## 📅 2026-05-11 — SISTEMA DE HISTORIAL DE VALUACIONES (v15.0)

### Objetivo:
Implementar un registro inmutable y permanente de cada tasación para evitar la pérdida de datos en recálculos y permitir el análisis temporal.

### Acciones realizadas:
1. **Nuevo Módulo** `parsers/valuacion_historial.py`:
   - Persistencia en JSONL (`data/valuaciones_historial.jsonl`)
   - Sistema de snapshots de scraping con hash MD5 en `data/scraping_history/`
   - Funciones para cargar, filtrar y comparar registros históricos.

2. **Integración en Core**:
   - `motor_vpp_core.py` (función `valuar_con_cache`) ahora invoca `registrar_valuacion` en cada acierto de recálculo.

3. **Interfaz de Usuario (valu.py)**:
   - Sección expandible "📈 Historial de Valuaciones" en el detalle de propiedad.
   - Gráfico de evolución de valor usando Plotly.
   - Herramienta de comparación entre dos fechas con desglose de variaciones.
   - Historial de snapshots de scraping en la barra lateral.

4. **Herramientas de Soporte**:
   - CLI: `scripts/ver_historial.py` para consultas rápidas desde terminal.
   - Tests: `tests/test_historial.py` (7 tests de integridad y lógica).

### Resultados:
- Las valuaciones ya no se sobrescriben.
- Es posible auditar por qué cambió un precio (cambio en dólares vs. cambio en mercado).
- Se preserva el contexto exacto (snapshot) de cada comparable usado.

### Tests:
- 7/7 passed en `test_historial.py`

---

## 📅 2026-05-10 — RAZONAMIENTO NARRATIVO DE VALUACIÓN (Prompt 1)

### Acciones realizadas:
1. **Nueva función** `generar_razonamiento_valuacion()` en `parsers/mercado_inmobiliario.py`:
   - 6 párrafos: identificación, mercado, factores +/-, valor, rental, plusvalía
   - Lenguaje humano profesional (no técnico)
   - Incluye nombre, zona, m², año, antigüedad, comparables, cap rate

2. **Integración al motor**:
   - El razonamiento se genera automáticamente en `valuar_propiedad_v7`
   - Se agrega al return como `'razonamiento'`

3. **Display en UI**:
   - `valu.py` ahora muestra el narrativo en expander "📋 Informe de Valuación"
   - Fallback al formato viejo si no existe el campo

### Tests:
- 19/19 regression tests passing

---

## 📅 2026-05-09 — REDISEÑO UI A 2 NIVELES (Dashboard + Detalle)

### Acciones realizadas:
1. **Título cambiado**: "Gestor de Ingresos Familiares" → "VPP Rosario — Valuador de Propiedades"

2. **Arquitectura 2-niveles**:
   - Nivel 1: Dashboard con cards compactos (3 por fila) + mapa general
   - Nivel 2: Detalle de propiedad con valor, rango, métricas, mapa

3. **comparables_venta** añadidos al return del motor:
   - Puntos azules sintéticos en el mapa de detalle
   - Hasta 20 por propiedad

4. **Limpieza**:
   - Expander "Editar propiedades" colapsado por defecto
   - Formulario original en sección de mostrar_propiedades

### Tests:
- 19/19 regression tests passing

---

## 📅 2026-05-08 — CAP RATE DATA-DRIVEN (v8.1)

### Acciones realizadas:
1. **Cap Rate derivado del mercado local**:
   - `calcular_cap_rate_local()` obtiene clusters de venta/alquiler
   - Formula: cap_rate = (alquiler_P50_anual_USD) / (venta_P33_USD)
   - Requiere >= 5 comparables de alquiler

2. **Fallback con badge**:
   - Si no hay datos → ROI_ZONAL estimado
   - UI muestra 🔴 ROJO si fallback, ✅ VERDE si data-driven

3. **Separación de escenarios**:
   - Valor Lista = escenario MERCADO (base_mercado, no conservadora)
   - Rango: conservador < mercado < optimista

### Resultados Mabel:
| Campo | Valor |
|------|-------|
| Cap Rate | 5.47% |
| Método | mercado_local |
| Confianza | ALTA |
| Alquiler | $516,911 ARS/mes |
| Fallback | False |

### Valores finales (Mayo 2026):
| Propiedad | Conservador | Mercado(Lista) | Optimista |
|-----------|-------------|----------------|----------|
| Mabel | $78,371 | $83,451 | $88,531 |
| Ayacucho | $48,737 | $52,144 | $55,551 |
| Vera | $49,802 | $54,132 | $58,463 |
| P1200 | $149,812 | $166,458 | $183,103 |

### Tests: 13/13 PASSED

---

## 📅 2026-05-08 — CORRECCIÓN VALOR LISTA = MERCADO

### Acciones realizadas:
1. **Cap Rate derivado del mercado local**:
   - `calcular_cap_rate_local()` obtiene clusters de venta/alquiler
   - Formula: cap_rate = (alquiler_P50_anual_USD) / (venta_P33_USD)
   - Requiere >= 5 comparables de alquiler

2. **Fallback con badge**:
   - Si no hay datos → ROI_ZONAL estimado
   - UI muestra 🔴 ROJO si fallback, ✅ VERDE si data-driven

3. **Nuevos campos en respuesta**:
   - `cap_rate`, `alquiler_rango`, `es_fallback_alquiler`
   - `confianza_alquiler`, `metodo_alquiler`, `cap_rate_info`

### Resultados Mabel:
| Campo | Valor |
|------|-------|
| Cap Rate | 5.47% |
| Método | mercado_local |
| Confianza | ALTA |
| Alquiler | $516,911 ARS/mes |
| Fallback | False |

### Tests: 13/13 PASSED

---

## 📅 2026-05-05 — BARRERAS DIFERENCIADAS + AUTOMAÇÃO

### Acciones realizadas:
1. **Implementación de barreras diferenciadas**:
   - `check_barrier_crossing()` ahora retorna 'hard'/'soft'/False
   - Cluster: solo excluye hard (ferrocarril)
   - IDW: soft penalty = 0.90, hard penalty = 0.20
   - ALGORITMOS.md §7 agregado

2. **Automatización de validación**:
   - `scripts/auto_validate.py` - tests + syntax + imports
   - `scripts/update_docs.py` - actualiza .MD
   - `scripts/init_reminder.py` - recordatorio de flujo
   - AGENTS.md actualizado conworkflow

3. **Sincronización UI-CLI**:
   - `calcular_base_calibrada` ahora usa `obtener_mediana_cluster_v2`
   - Valores CLI = UI (verificados)

### Valores finales ( Mayo 2026):
| Propiedad | USD | m2_base | n |
|-----------|-----|--------|---|
| Mabel | $81,907 | $1,633 | 81 |
| Ayacucho | $48,024 | $1,520 | 42 |
| Vera | $58,774 | $1,436 | 24 |
| Amenabar | $74,596 | $1,594 | 10 |
| P1200 | $157,418 | $1,501 | 34 |

### Tests: 5/5 PASSED

---

## 📅 2026-05-05 — CALIBRACIÓN COMPLETADA

### Acciones realizadas:
1. **Documentación de Leyes del Motor** en `ALGORITMOS.md`:
   - Fórmula de venta (P33 venta / P50 alquiler)
   - Clamp suma cruda (-0.40 a +0.40)
   - NLP cap (1 dorm: 3%, 2+ dorm: 5%)
   - Atenuación antigüedad (UMBRAL: -0.18, FACTOR: 0.35)
   - Exclusión de factor_pasillo

2. **Actualización DICCIONARIO_DATOS.md**:
   - Constantes documentadas

3. **Tests de no-regresión** agregados:
   - test_antiguedad_atenuacion.py (4 tests)

4. **Auditoría de alquileres**:
   - Cap rates en rango 2.5% - 3.5%
   - GAP_ALQUILER: 0.85 (sin cambios)
   - Recomendación: Mantener GAP actual

### Valores finales de venta:
- Mabel: $80,121
- Ayacucho: $44,632
- Vera: $53,346
- P1200: $143,460

### Tests: 5/5 (regresión) + 4/4 (atenuación)

---

## 🎯 PROTOCOLO DE TRABAJO (OBLIGATORIO)

### Antes de modificar código:
1. **COMMIT INICIAL**: hacer commit del estado actual a GitHub antes de cualquier cambio
   ```bash
   git add -A
   git commit -m "SAVEPOINT: estado antes de [descripcion]"
   git push
   ```

2. **IMPLEMENTAR CAMBIOS**: realizar las modificaciones necesarias

3. **COMMIT FINAL**: verificar que los cambios funcionan y subir
   ```bash
   git add -A
   git commit -m "FIX: [descripcion]"
   git push
   ```

---

## 🏗️ TAREA ACTUAL: Sincronización UI y Estabilidad de Fórmula (VPP)
**Estado:** Finalizado ✅
**Agente:** OpenCode (Gemma 4)
**Objetivo:** Resolver divergencia de precios UI vs Python y blindar la fórmula de valuación.

### Acciones Realizadas:
1. **Sincronización de Fecha**: Implementado el paso de `fecha_ref` desde la UI hasta el cluster en `obtener_mediana_cluster`, asegurando que ambos entornos filtren el mismo subconjunto de datos.
2. **Guard RO-12**: Implementado `_verificar_imports()` en `app.py` para bloquear el arranque si se detectan llamadas a `calcular_valor_vpp` (motor obsoleto).
3. **Fix de Caché (RO-13)**: Implementado control de TTLs por entorno (`APP_ENV`). En `development`, TTL=0 para evitar visualización de datos obsoletos.
4. **Sustitución de Sqrt por Clamps (V13.0)**: Eliminada la raíz cuadrada (`sqrt`) del cálculo del factor final para evitar compresiones no lineales difíciles de calibrar. Se implementaron clamps explícitos sobre la `SumaCruda` ($[-0.4, 0.4]$) y el `FactorTotal` ($[0.7, 1.35]$) para evitar la sobreinflación de precios por acumulación de factores positivos.
5. **Atenuación Dinámica (V12.4)**: Implementada lógica de saturación no lineal para el $\Delta \text{Antigüedad}$ en Venta P33. Se reemplazó el factor $K$ lineal por una función por tramos (Piecewise) para evitar la doble penalización en propiedades antiguas.
6. **Sincronización de Contexto**: Actualizados los tests de regresión para usar `fecha_ref="2026-04"`, eliminando la divergencia de $10k USD causada por el uso de promedios históricos en los tests vs datos actuales en la UI.
7. **Validación**: Ejecutados tests de regresión; confirmada convergencia de valores.
8. **Blindaje de Docs**: Actualizada `MEMORIA_PROYECTO.md` con **RO-15**, **RO-16** y **BUG-14**. Actualizado `ALGORITMOS.md` y `DICCIONARIO_DATOS.md` con la nueva lógica de atenuación y guardrails.

### Próximos Pasos (ROADMAP):
- [ ] Crear `GUIA_INSTALACION.md` con dependencias y requerimientos de entorno.
- [ ] Implementar los tests de regresión faltantes mencionados en la Memoria (Sección 11).
- [ ] Validar la guía de instalación en un entorno limpio.

---

## FLUJO OBLIGATORIO (记忆)

```
[Código] → python scripts/auto_validate.py
              ↓
[OK] → git add . && git commit -m "..." && git push
              ↓
[FAIL] → Corregir errores → Repe

---

## 📅 2026-05-12 — OPTIMIZACIÓN: Flujo Portfolio separado en A (general) vs B (detalle)

### Cambios:
- `valu.py`: El Portfolio ahora bifurca en dos caminos:
  - **Flujo A (sin selección)**: itera todas las propiedades y muestra grid
  - **Flujo B (con `prop_sel`)**: valúa solo 1 propiedad y muestra detalle
- Botón "🔄" → "🔄 Recalcular valuación" con label visible

### Impacto:
- Con N=1000 propiedades: ver detalle antes hacía 1000 iteraciones → ahora hace 1
- Usa `st.session_state.pop()` en vez de get+set para más claridad

---

## 📅 2026-05-12 — INFOMAPA: Candidatos múltiples + selección manual + imágenes múltiples

### Cambios:
- `parsers/infomapa_api.py`: Refactor completo. `enriquecer_con_infomapa()` retorna lista de candidatos (top 10 por coordenadas) + imágenes disponibles por PH.
- `parsers/mercado_inmobiliario.py`: Bloque simplificado que propaga `candidatos[]` e `imagenes_disponibles{}`.
- `valu.py`: Nueva UI interactiva en detalle de propiedad:
  - Columna izquierda: botones para cada candidato (clic → selecciona)
  - Columna derecha: info del PH seleccionado + selector de imágenes si hay varias + botón "Abrir Plano"
  - El recomendado por dirección se marca con "✅" y se selecciona automáticamente

### Decisiones:
- Límite de 10 candidatos para evitar ~50 llamadas API
- Tolerancia de coordenadas aumentada a 0.0006° (~67m)
- `st.session_state` persiste la selección de PH entre re-renders
- Opción A para imágenes múltiples: selectbox + botón "Abrir Plano"

---

## 📅 2026-05-12 — GEOCODING + MATCHING INFOMAPA POR DIRECCIÓN

### Cambios:
- `parsers/infomapa_api.py`: Nueva función `_match_por_direccion()` que busca el PH por calle+número en todo el CSV. `enriquecer_con_infomapa()` ahora prioriza: 1) match por dirección (siempre incluido) + 2) top 2 por coordenadas.
- `valu_forms.py`: Botón "📍 Geocodificar dirección" que llama a Nominatim para auto-completar lat/lon (campos siguen siendo editables).

### Resultados de matching:
- Ayacucho 1805 → PH 17817 ✅ (recomendado por dirección)
- 3 de Febrero 520 → PH 6966 (3 de Febrero 519) ✅ (diff=1)

---

## 📅 2026-05-12 — FASE 2: Cierre y decisión definitiva

El filtro de edad + percentil ajustado está completo y es correcto.

El target anterior de Mabel ($75-79k) estaba calibrado sobre un pool contaminado con edificios más nuevos que inflaban el P50. Al filtrar por antigüedad similar (1983-2013), el valor baja a $72k, que es el precio correcto para ese segmento de mercado.

**Decisión:** NO se ajusta el percentil ni la ventana de edad. Los valores actuales son los definitivos para Fase 2.

**Impacto de la mejora:**
- Mabel: pasó de compararse con torres 2022 a edificios 1983-2013
- P1200: pasó de compararse con stock moderno a stock del Centro viejo
- El modelo ahora compara lo comparable, no lo cercano

**Tabla de referencia definitiva:**

| Propiedad   | Año  | Pool | n_age | %ile | Valor ref  |
|-------------|------|------|-------|------|------------|
| Mabel       | 1998 | 81   | 27    | P50  | $72,241    |
| Ayacucho    | 2002 | 43   | 16    | P45  | $52,047    |
| Vera Mujica | 2009 | 27   | 8     | P40  | $52,062    |
| P1200       | 1977 | 36   | 12    | P45  | $137,888   |

**Tests:** 27/27 pasando con rangos actualizados.

---

## 📅 2026-05-15 — FASE 1 — Limpieza de archivos obsoletos

### Archivos movidos a _archive/

| Categoría | Cantidad | Destino |
|-----------|----------|---------|
| Anclas viejas | 5 | `_archive/anclas_viejas/` |
| Scripts debug/diagnóstico | 49 | `_archive/scripts_debug/` |
| Scripts calibración one-shot | 19 | `_archive/scripts_calibracion/` |
| Backups (cache, logs) | 3 | `_archive/backups/` |
| Tests sueltos de raíz | 33 | `_archive/tests_sueltos/` |
| Directorios enteros | 3 (scratch, logs, reports) | `_archive/` |
| **Total archivado** | **~112** | |

### Archivos activos que permanecen

| Categoría | Archivos restantes |
|-----------|-------------------|
| Anclas en `data/` | `anclas_rosario_v3_grid.json`, `anclas_rosario_v5_1_limpio.json` |
| Anclas en raíz | `anclas_rosario_v3_grid.json` |
| Tests oficiales | `tests/test_regression.py` |
| Scripts activos | `scripts/auto_validate.py`, `scripts/ver_historial.py` |

### Resultados
- **31/31 tests pasando** (sin cambios en lógica de valuación)
- Ningún archivo eliminado (todo en `_archive/`)
- Ningún archivo activo afectado

---

## 📅 2026-05-15 — FASE 5.1 — Helpers de cluster (preparación)

### Cambios realizados

| Archivo | Acción |
|---------|--------|
| `parsers/cluster_filters.py` | **Creado** — 7 funciones helper puras |
| `tests/test_cluster_filters.py` | **Creado** — 31 tests unitarios |

### Nuevas funciones (7)
1. `filtrar_por_radio()` — filtro geoespacial por distancia
2. `filtrar_por_tipo_operacion_dorms()` — filtro por atributos
3. `filtrar_por_fecha()` — filtro por ventana temporal
4. `separar_por_barreras()` — separación same/cross/hard
5. `calcular_percentil()` — percentil vía numpy
6. `calcular_blend_p33()` — blend de P33 same/cross
7. `seleccionar_percentil_por_edad()` — regla de percentil dinámico

### NO se modificó
- `obtener_mediana_cluster_v2()` — intacta
- `valuar_propiedad_v7()` — intacta
- Ningún valor de venta/alquiler

### Tests: **62/62 pasando** (31 nuevos + 31 regresión)

---

## 📅 2026-05-15 — FASE 5.4 — Decisión de Congelamiento

### Decisión
Se decidió NO extraer `calcular_rango_venta()` ni `procesar_alquiler()` como helpers externos de `valuar_propiedad_v7()`.

### Razón técnica
- Ambos bloques tienen lógica compleja acoplada al contexto (márgenes dinámicos por IQR, size_discount, cap_rate_local vs fallback)
- Los helpers creados en FASE 5.3 quedaron simplificados y no replicaban la lógica real
- Forzar la extracción tiene más riesgo de romper valores que el beneficio de reducir líneas

### Razón de ingeniería
- Principio YAGNI: no refactorizar lo que no se va a reutilizar
- La función ya bajó de 552 a ~400 líneas organizadas
- Las secciones críticas (cluster, metadata) ya están modularizadas
- 10 helpers extraídos con 45 tests unitarios

### Estado final post FASE 5

| Métrica | Antes | Después |
|---------|-------|---------|
| `obtener_mediana_cluster_v2()` | 580 líneas monolíticas | ~100 líneas (orquestador) |
| `valuar_propiedad_v7()` | 552 líneas | ~400 líneas (6 secciones) |
| Helpers con tests | 0 | 10 |
| Tests unitarios nuevos | 0 | 45 |
| Valores ancla | — | Intactos |

## 2026-05-16 — FIX: FASE 5 contaminó percentil con np.percentile (baseline restored)

### Bug detectado
En FASE 5 (2026-05-15), `calcular_percentil()` en `cluster_filters.py` se implementó
usando `np.percentile()` con interpolación lineal. El código original usaba un método
discreto por índice entero.

### Impacto real
Vera (pool=8 comps, P40): drift de hasta ~3.6%
P1200 (pool=12 comps, P45): drift de ~1-2%
Mabel/Ayacucho (81/43 comps): sin impacto apreciable

### Causa raíz
`np.percentile()` interpola entre los dos valores más cercanos al percentil.
El método original (`int(n * p / 100)`) selecciona un valor real de la muestra.
Para pools chicos la diferencia es significativa y no defendible en un AVM de real estate.

### Fix
- `calcular_percentil()` vuelve a método discreto (sin numpy)
- Eliminado `import numpy as np` de `cluster_filters.py`
- Tests actualizados y fortalecidos con casos reales (P40_n8, P45_n12, P50_n4)

### Validacion
**92/92 tests pasando. Baseline restaurado al 100%:**

| Propiedad | Antes (FASE 5 roto) | Despues (fix) | Diferencia |
|-----------|---------------------|---------------|------------|
| Mabel | $72,241 | $72,241 | 0.00% |
| Ayacucho | $52,135 | $52,047 | -0.17% |
| Vera Mujica | $50,026 | $52,062 | +4.07% |
| P1200 | $134,650 | $137,888 | +2.40% |

### Leccion aprendida
Cualquier refactor que toque `calcular_percentil()` debe validar contra baseline completo.
Cambiar metodo de percentil altera resultados sin cambiar datos ni logica de negocio.

---

# Docs .MD a mantener sincronizados:
- ALGORITMOS.md (lógica)
- DICCIONARIO_DATOS.md (datos)
- MEMORIA_PROYECTO.md (reglas)
- STATUS_ACTUAL.md (estado)
- BITACORA_AGENTES.md (decisiones)
```

## 📅 2026-05-19 — FASE 2: UNIFICAR LÓGICA DEL RANGO DE VALUACIÓN

### Objetivo:
Eliminar la lógica paralela de rango de valuación. Antes había 2 rutas: el bloque inline en `valuar_propiedad_v7()` y el helper `calcular_rango_venta()` que nunca se llamaba. Ahora el helper es la única fuente de verdad.

### Acciones realizadas:
1. **Reescritura completa de `calcular_rango_venta()`** en `valuacion_helpers.py`:
   - Nueva firma: `valor_estimado, p25/p50/p75_cluster, n_muestras, radio, confidence`
   - Replica exactamente la lógica productiva: IQR → half → raw_margin → floor/cap por calidad de cluster → confidence BAJA aumenta cap → margen simétrico
   - Retorna `{'rango_venta': {min, mid, max, spread_pct, margen_error, percentiles}}`
2. **Refactor del motor** (`mercado_inmobiliario.py`):
   - Líneas 2736-2789 (rango inline) reemplazadas por llamada a `calcular_rango_venta()`
   - Import actualizado: se agregó `calcular_rango_venta`, se eliminó `seleccionar_percentil_por_edad` (nunca llamada)
   - Líneas 2844-2845 (`rango_min/MAX = valor_venta * ±10%`) eliminadas
   - `rango_m2` ahora usa el rango real del helper (antes era ±10% hardcodeado)
   - `rango_venta` dict en return simplificado: ahora apunta directamente al dict del helper
3. **Tests actualizados** (`test_valuacion_helpers.py`):
   - 6 tests nuevos para la nueva firma: básico, margen con IQR, confidence baja, sin dispersión, valor cero, muestras grandes
   - Los 15 tests pasan

### Impacto en valuaciones:
- El valor principal (`valor_venta`) no cambia — es el mismo blending P33/P45/P50
- El `margen_error` ahora usa la misma lógica IQR + floors/caps (exactamente igual que antes)
- **Cambio visible**: `rango_m2` ya no es ±10% hardcodeado; ahora es el rango real del cluster
  - Para clusters grandes (≥50, ≤300m): margen más ajustado (0.08)
  - Para clusters chicos (<10): margen más amplio (0.10-0.18)
  - Antes siempre era ±10% independiente de la calidad del cluster

### Tests: 82/82 pasando
- 15 tests `test_valuacion_helpers.py` ✅
- 34 tests `test_cluster_filters.py` ✅
- 33 tests `test_regression.py` ✅ (incluye baseline Mabel $76k, Ayacucho $53k, Vera $53k, P1200 $142k)

---

## 📅 2026-05-19 — FASE 3: CONSOLIDAR HELPERS DE PERCENTIL Y BLEND

### Objetivo:
Eliminar duplicación de lógica en percentiles, bases y helpers muertos. Consolidar `seleccionar_percentil_por_edad()` y `calcular_blend_p33()` como fuentes únicas de verdad.

### Acciones realizadas:
1. **PASO 1 — Auditoría completa de helpers**:
   - `calcular_percentil`: ALIVE (called from producción líneas 852-853)
   - `calcular_blend_p33`: ALIVE (solo usado en blend_cons; mkt/opt eran inline)
   - `seleccionar_percentil_por_edad`: **DEAD** — import removido en FASE 2, lógica duplicada inline
   - `calcular_rango_venta`: ALIVE (FASE 2)

2. **PASO 2 — Consolidación de percentil selection**:
   - Se agregó `seleccionar_percentil_por_edad` al import
   - Se reemplazaron 15 líneas inline (líneas 834-848) por `seleccionar_percentil_por_edad(age_filter_applied, n_age_filtered)`
   - Lógica idéntica: mismo `P33 → P40 → P45 → P50` escalado por `n_age_filtered`

3. **PASO 3 — Consolidación de blend**:
   - `blend_mkt = ALPHA_MERCADO * pct_same + (1 - ALPHA_MERCADO) * pct_cross` → `calcular_blend_p33(pct_same, pct_cross, alpha=ALPHA_MERCADO)`
   - `blend_opt = alpha_opt * pct_same + (1 - alpha_opt) * pct_cross` → `calcular_blend_p33(pct_same, pct_cross, alpha=alpha_opt)`
   - Todos los blends ahora exponen la misma fórmula: simple álgebra lineal.

4. **PASO 4 — Verificación de rango residuals**:
   - Los ±10% `rango_min/rango_max` restantes están en funciones legacy (`calcular_valuacion_v5`, `AVM v6`), NO en `valuar_propiedad_v7()`. Sin cambios.

5. **PASO 5 — Eliminación de helpers muertos**:
   - Los 4 helpers de cluster están 100% activos. Ninguno eliminado.

6. **PASO 6 — Tests de fuente de verdad**:
   - **82/82 tests pasan** (49 helper + 33 regression)
   - `auto_validate.py` ✅ — sintaxis e imports OK

### Impacto en valuaciones:
- **Sin cambios numéricos.** La fórmula de blend es algebraicamente idéntica: `alpha * same + (1-alpha) * cross`
- La lógica de percentil es idéntica: las mismas condiciones y los mismos valores
- **Baseline intacto:** Mabel $72,241 / Ayacucho $52,047 / Vera $52,062 / P1200 $137,888

### Estado de helpers post-FASE 3:
| Helper | Antes | Ahora |
|--------|-------|-------|
| `calcular_percentil` | ALIVE | ALIVE |
| `calcular_blend_p33` | ALIVE (1 caller) | ALIVE (4 callers) |
| `seleccionar_percentil_por_edad` | DEAD (import removido) | ALIVE (1 caller) |
| `calcular_rango_venta` | ALIVE | ALIVE |

---

## 📅 2026-05-20 — FASE 3 EXT: AGE BLEND PARA 5-7 COMPARABLES

### Objetivo:
Evitar que el motor descarte completamente la señal de edad cuando hay 5-7 comparables de edad similar (regla anterior: n < 8 → pool completo). Implementar un blend suave entre el pool etario y el pool completo.

### Cambios realizados:
1. **`parsers/cluster_filters.py` — `seleccionar_percentil_por_edad()`**:
   - Nuevo rango `5 <= n_age_filtered < 8` → retorna `(33, 'P33_age_blend')`
   - `n_age_filtered < 5` → retorna `(33, 'P33')` (fallback total, igual que antes)

2. **`parsers/mercado_inmobiliario.py` — `obtener_mediana_cluster_v2()`**:
   - Cuando `percentil_usado == 'P33_age_blend'`, calcula `base_all` desde `unicos` (pool completo) usando P33 con blend same/cross α=0.70
   - Aplica blend: `valor = alpha * base_age + (1-alpha) * base_all`
   - alpha = 0.75 (n=7), 0.60 (n=6), 0.45 (n=5)
   - Agrega metadata: `age_blend_applied`, `alpha_age_blend`, `base_age`, `base_all`

3. **`valu_detail_sections.py` — `render_razonamiento()`**:
   - Muestra `st.info()` azul con detalles del blend si `age_blend_applied == True`

4. **Tests**:
   - `test_cluster_filters.py`: 4 tests nuevos (n7, n6, n5, n4_fallback)
   - `test_regression.py`: 6 tests nuevos (alpha n7/n6/n5, fallback n4, anclas no regresión, metadata solo donde corresponde)
   - Total: **137 tests pasan** (antes 131)

### Baseline:
- **Sin cambios en anclas**: Mabel $72,241 / Ayacucho $52,047 / Vera $52,062 / P1200 $137,888
- El nuevo blend solo se activa cuando una propiedad cae en rango 5-7 (ninguna ancla actual lo usa)

### Impacto futuro:
- Propiedades con n_age 5-7 ya no saltan bruscamente al pool completo
- Ejemplo: "Entre Ríos 400 (2016)" — si cae en 5-7, el blend mantiene señal de edad
- El modelo es más continuo y menos binario

---

## 📅 2026-05-20 — TAREA: Recalibración de factores constructivos

### Objetivo:
Separar `premium` de estado de conservación, moverlo a calidad, y suavizar ventilación para evitar saltos excesivos en la valuación.

### Problema detectado:
Cambiar `bueno/media/simple` → `premium/excelente/cruzada` producía un salto de $61,231 → $85,270 (+39.2%) sin cambios en m2_base. El salto se explicaba por compounding de factores que llevaba la suma_cruda al clamp +0.40.

### Cambios realizados:

| Archivo | Acción |
|---------|--------|
| `parsers/mercado_inmobiliario.py` | `calcular_factores()`: nuevo helper `normalizar_estado_y_calidad()`; `premium` quitado de `factor_estado`; agregado a `factor_calidad` (1.08); ventilación suavizada (0.95/1.05); tablas recalibradas |
| `datos_mercado.json` | Sección `factores.calidad` actualizada con premium, excelente, alta, baja |
| `tests/test_factores_helpers.py` | **Creado** — 9 tests: premium no es estado, calidad premium, ventilación suavizada, no doble premio, tablas completas, ratio 1.15-1.25 del caso problemático |
| `tests/test_regression.py` | Rango Ayacucho ajustado (48k-52k→44k-50k) por recalibración |
| `docs/ALGORITMOS.md` | Sección 6 agregada con tablas de nuevos factores y normalización |

### Nuevos valores de factor:

**factor_estado** (sin premium):
- a_estrenar=1.08, excelente=1.05, muy_bueno=1.03, bueno=1.0, regular=0.92, malo=0.85

**factor_calidad** (con premium):
- premium=1.08, excelente=1.06, alta=1.04, media=1.0, baja=0.95

**Ventilación**:
- simple=0.95, doble=1.0, cruzada=1.05 (swing 10% vs 20% anterior)

### Normalización defensiva:
Cuando `estado_detalle = "premium"`:
- Se normaliza a estado `excelente` (1.05)
- Si calidad es `media` o vacía → promueve a calidad `premium` (1.08)
- Nunca hay doble premio estado+calidad

### Tests: 146/146 pasando
- 9 nuevos tests de factores
- Anclas intactas (Mabel $79,069, dentro de rango $75k-$85k)
- Ayacucho $46,430 (ajuste esperado por recalibración)

---

## 📅 2026-05-20 — TAREA: Log Técnico de Auditoría de Valuación

### Objetivo:
Crear un log técnico completo, persistente y auditable por valuación, accesible desde la aplicación.

### Cambios realizados:

| Archivo | Acción |
|---------|--------|
| `parsers/audit_logger.py` | **Creado** — módulo con `generar_audit_log()`, `guardar_audit_log()`, `cargar_audit_logs()`, `obtener_ultimo_audit_log()` |
| `parsers/mercado_inmobiliario.py` | `valuar_propiedad_v7()` refactorizada: return convertido a variable `resultado`; se inyecta `audit_log` y se persiste vía `guardar_audit_log()` |
| `valu.py` | Nueva opción "Auditoría Técnica" en navegación; pantalla con selectbox de propiedad, selector de snapshot, 7 tabs (Inputs, Superficies, Cluster, Factores, Venta, Alquiler, JSON crudo) + botón descarga |
| `tests/test_audit_logger.py` | **Creado** — 6 tests: retención, campos mínimos, consistencia valores, positivos, generación directa, no alteración |

### Estructura del audit_log:
```
audit_log = {
  timestamp, motor_version, nombre,
  propiedad: { nombre, zona, tipo, dirección, lat, lon, año, dorms, estado, calidad, piso, ... },
  superficies: { m2_cubiertos, m2_semi, m2_desc, m2_equiv },
  cluster_venta: { n_total, n_con_anio, age_filter, percentil, p33_same/cross, bases, comparables_usados[] },
  factores: { estado, calidad, depreciacion, suma_cruda, f_estructural, nlp, es_ventana3 },
  venta: { conservador, mercado, optimista, spread, m2_base },
  alquiler: { metodo, cap_rate, rango, size_discount, fallback },
  final: { valor_venta, realizable, alquiler, plusvalia, cap_rates },
  resolution_metadata: { ... }
}
```

### Persistencia:
- Archivos en `data/history/audit_logs/YYYY-MM-DD_HH-MM-SS__Nombre.json`
- Acceso desde Configuración → "🧾 Auditoría Técnica"

### Tests: 152/152 pasando
- 6 nuevos tests de audit_logger
- 146 existentes intactos (sin cambios en lógica)

---

## 📅 2026-05-21 — TAREA-001: Filtro catastral por centena exacta

### Problema
`_match_por_direccion()` usaba `diff <= 10` para seleccionar candidatos catastrales. Para "Pellegrini 1200" (P1200), esto seleccionaba "Pellegrini 1195" (centena 11xx) como candidato recomendado, siendo una cuadra diferente. En Rosario la centena define la cuadra.

### Cambio
- `_match_por_direccion()` ahora filtra por `centena_csv == centena_sujeto` antes de evaluar diff
- Solo candidatos de la **misma centena** (misma cuadra) pueden ser "recomendados"
- Los candidatos por coordenadas llevan `centena_match = 'coordenadas'`
- UI muestra badge "📍 Misma cuadra" o "📍 Coordenadas" según el tipo

### Resultado
| Propiedad | Antes | Después |
|-----------|-------|---------|
| P1200 (Pellegrini 1200) | 1195 como recomendado | Solo candidatos por coordenadas (sin 11xx como dirección) |
| Ayacucho (Ayacucho 1805) | Normal | Sin cambio |
| Mabel (3 de Febrero 520) | Normal | Sin cambio |

### Archivos
- `parsers/infomapa_api.py` — filtro de centena + propagación
- `valu_detail_sections.py` — badge en UI
- `docs/DICCIONARIO_DATOS.md` §7 — campo `centena_match`
- `.opencode/plans/TAREA-001.md` — plan archivado
- `.opencode/plans/TAREAS_INDEX.md` — índice actualizado

### Tests: 152/152 pasando

## 📅 2026-05-20 — TAREA: Ventanas progresivas de edad ±10→±15→±20

### Problema
`_filtrar_por_ventana_edad()` saltaba de ±15 a ±30, permitiendo que propiedades 25+ años más viejas que el sujeto entraran al pool. Para "Entre Ríos 400" (2016, premium, Centro), los comparables de 1991/1993 pasaban el filtro con ±30, alcanzando n=8 y saltándose el age_blend (que requiere 5-7).

### Cambio
`_filtrar_por_ventana_edad()` ahora usa ventanas progresivas:

```
±10 → si n ≥ 8, acepta
±15 → si n ≥ 8, acepta
±20 → si n ≥ 8, acepta
      si 5 ≤ n < 8, acepta (activa P33_age_blend)
      si n < 5, fallback al pool completo (P33)
```

| Parámetro | Antes | Después |
|-----------|-------|---------|
| Ventanas | [15, 30] | [10, 15, 20] |
| Fallback | ±30 con min 8 | ±20 con min 5 (blend 5-7) |
| Blend | Solo si n_age 5-7 llegaba | Ahora llega en más casos |

### Archivos modificados
- `parsers/mercado_inmobiliario.py`: `_filtrar_por_ventana_edad()` rewriten, call site actualizado
- `tests/test_regression.py`: rango Ayacucho ajustado de $44k-$52k a $36k-$44k
- `docs/ALGORITMOS.md`: §11b nuevo (ventanas progresivas), §12 tabla actualizada
- `docs/BITACORA_AGENTES.md`: esta entrada

### Impacto
- **Entre Ríos 400**: ±10→0, ±15→~3, ±20→6 → **P33_age_blend activado** (alpha=0.75). Valor $69,599 (correcto, sin comparables 1991/1993)
- **Mabel**: ±10 da 11 → P45_age → $78,250 (cambio mínimo, -1%)
- **Ayacucho**: ±10 da 8 → P40_age → $39,896 (antes $46,430 con ±15). El nuevo valor refleja solo comparables 1992-2012 sin inflación de viejos
- **Anclas sin cambios**: Vera Mujica, P1200 intactos

### Tests: 39/39 regression, 152/152 total pasando

---

## 📅 2026-05-20 — TAREA: Ajuste a ventanas prudentes (±15 → ±20 → blend)

### Problema detectado
La estrategia anterior (±10→±15→±20) era demasiado agresiva. Para propiedades como Ayacucho (2002), ±10 redujo el pool de 16 a 8 comps y bajó el percentil de P45 a P40, generando una caída de ~14% ($46,430 → $39,896). En Rosario, departamentos usados con 10-15 años de diferencia siguen siendo comercialmente comparables.

### Cambio final
Se reemplazó ±10→±15→±20 por una política más prudente:

```
±15 → si n ≥ 8, acepta (mantiene comportamiento histórico en ~90% de casos)
±20 → si n ≥ 8, acepta
      si 5 ≤ n < 8, activa age_blend
      si n < 5, fallback al pool completo
```

### Impacto final
| Propiedad | Antes (±15→±30) | Después (±15→±20→blend) | Cambio |
|-----------|:----------------:|:------------------------:|:------:|
| Mabel     | $79,069          | $79,069                  | 0%     |
| Ayacucho  | $46,430          | $46,430                  | 0%     |
| Vera Mujica | $52,062       | $52,062                  | 0%     |
| P1200     | $137,888         | $137,888                 | 0%     |
| **Entre Ríos 400** | inflado por 1991/1993 | **$69,599** (con blend) | ✅ |

### Archivos modificados
- `parsers/mercado_inmobiliario.py`: `_filtrar_por_ventana_edad()` con ventanas [15, 20]
- `tests/test_regression.py`: rangos Ayacucho restaurados a $44k-$50k y $44k-$52k
- `docs/ALGORITMOS.md`: §11b actualizado, tabla valores ref restaurada
- `docs/BITACORA_AGENTES.md`: esta entrada

### Tests: 39/39 regression, 152/152 total pasando

---

## 📅 2026-05-21 — FIX: Landing hero mockup no renderizaba (CSS faltante)

### Problema
La landing page no mostraba el hero con el mockup enriquecido de valuación. El HTML era válido pero aparecía como texto invisible sobre fondo blanco.

### Causa raíz
`mostrar_landing()` inyecta solo `LANDING_CSS`, pero las clases CSS del hero (`.hero-with-image`, `.hero-overlay`, `.hero-content`, `.hero-title`) estaban definidas únicamente en `VALU_CSS`, que no se inyecta en la landing. Sin estas clases:
- Sin `.hero-overlay` → no hay fondo oscuro degradado → texto negro sobre blanco
- Sin `.hero-content { color: white }` → texto del hero invisible
- Sin `.hero-with-image { min-height }` → la sección colapsaba

### Fix
- **`valu_design.py`**: Se copiaron las 4 clases CSS faltantes a `LANDING_CSS`
- **`landing.py`**: Se eliminó `_html.unescape(_html.unescape(...))` innecesario (la función ya retorna HTML real)

### Archivos
- `valu_design.py` — hero classes agregadas a `LANDING_CSS`
- `landing.py` — `_html.unescape()` removido

### Tests: sin impacto (solo CSS/HTML)

---

## 📅 2026-05-21 — RAZONAMIENTO NARRATIVO HOLÍSTICO CUALITATIVO

### Objetivo
Reemplazar el razonamiento numérico/técnico por una narrativa cualitativa que explique los drivers de valor en lenguaje natural, como lo haría un tasador profesional.

### Cambios
- **`parsers/mercado_inmobiliario.py`**: 
  - `generar_razonamiento_valuacion()` reescrita completamente
  - 7 párrafos: identificación → mercado → factores → edad → NLP → valor + rango → alquiler → plusvalía
  - Cada factor estructural se explica cualitativamente (vista, calidad, estado, ventilación, piso, ubicación, gas, balcón, funcionales, seguridad, ascensores)
  - NLP: detecta keywords de la descripción y las menciona con su percepción
  - Rango: explicación cualitativa de la dispersión ("acotado", "moderado", "amplio")
  - Antigüedad: segmentada en 5 rangos etarios con descripción específica
  - Alquiler: contextualizado contra promedio de Rosario
  - Se movió macrozona_info antes de SECCIÓN 5 para disponibilidad en el razonamiento
  - Se agregaron `f_dict`, `n_comps`, `tiene_barreras` y `meta_venta` al resultado completo

### Principio
- Cero porcentajes en factores o mercado
- Solo lenguaje cualitativo: "excepcional", "determinante", "modera el precio", "contribuye positivamente", "desgaste moderado", etc.

## 📅 2026-05-22 — TAREA-003: Orden candidatos catastrales por distancia (no centena)

### Problema
Los candidatos por coordenadas se ordenaban primero por centena (mismos → otros) y luego por distancia dentro de cada grupo. Esto causaba que entradas de calle sin número (que pasaban centena) desplazaran a entradas con número que estaban más cerca pero en centena distinta. Caso concreto: PH=17916 "3 de Febrero 504" a 21m quedaba fuera del top 3, mientras que PH=19899 "3 de Febrero" (sin número) a 49m entraba.

### Cambio
- Eliminado split `mismos/otros` (centena-first)
- Los 3 candidatos por coordenadas se eligen así:
  1. Filtrar a **misma calle** (vía `_misma_calle()`)
  2. Filtrar a **misma centena** — candidatos sin número pasan (`csv_num is None`), candidatos con número distinta centena se excluyen
  3. Ordenar por **distancia** (el pool ya viene ordenado)
  4. Tomar top 3
- Eliminado el relleno secundario (ya no es necesario)
- `centena_match` simplificado: solo `'exacta'` y `'coordenadas'`

### Resultado
| Propiedad | Antes (centena-first) | Después (distancia-first) |
|---|---|---|
| Mabel (3 de Febrero) | PH=14404 "3 de Febrero" 12m, PH=19899 "3 de Febrero" 49m, PH=7389 "3 de Febrero" 59m | PH=14404 "3 de Febrero" 12m, PH=17916 "3 de Febrero 504" 21m, PH=20199 "3 de Febrero 525" 28m |
| Ayacucho (Ayacucho 1800) | PH=17817 1805 41m, PH=10340 1812 45m, PH=22150 1813 49m (solo centena 1800) | PH=17817 1805 41m, PH=10340 1812 45m, PH=22150 1813 49m (sin cambio: mismos filtros) |

### Archivos
- `parsers/infomapa_api.py` — nuevo orden distancia-first + exclusión centena distinta
- `docs/BITACORA_AGENTES.md` — esta entrada

### Tests: 39/39 regression pasando

---

## 📅 2026-05-22 — Opción C: valuaciones_cache.json trackeado en git + Opción A: cache_scraping.json + git write-back

### Problema
Cada deploy de DO crea un contenedor fresco. `valuaciones_cache.json` estaba en `.gitignore` → perdido → recálculo completo en cada deploy. `cache_scraping.json` estaba en `.gitignore` pero ya era trackeado desde commits anteriores (`.gitignore` no afecta archivos ya trackeados). Además, cambios de propiedades hechos desde la UI de DO se perdían en deploy.

### Cambios

| Archivo | Acción |
|---------|--------|
| `.gitignore` | `data/valuaciones_cache.json` removido. `cache_scraping.json` reemplazado por comentario (ya estaba trackeado) |
| `parsers/valuacion_cache.py` | `_calcular_hash_scraping()` retorna `None` si archivo no existe; `necesita_recalcular()` skip si `None` |
| `parsers/git_sync.py` | **Nuevo** — módulo de write-back a git para DO. `try_sync(file_paths)` add+commit+push condicional (`GIT_WRITE_TOKEN`) |
| `valu.py` | `guardar_propiedades()` ahora llama a `try_sync()` para sincronizar cambios de propiedades a git |
| `valu_detail_sections.py` | `guardar_propiedades()` ahora llama a `try_sync()` para cambios en detalle (editar/eliminar) |
| `valu.yaml` | Env var `GIT_WRITE_TOKEN` agregada (requiere GitHub PAT configurado por usuario) |

### Lógica de persistencia
- **`cache_scraping.json`** (~5.7MB, 9,766 props) → ya trackeado → DO tiene datos de mercado
- **`valuaciones_cache.json`** (~324KB) → ahora trackeado → DO sirve cache sin recálculo
- **`propiedades.json`** → siempre trackeado → DO ahora escribe cambios vía `git push` si hay token
- **`GIT_WRITE_TOKEN`** → GitHub PAT con scope `repo` necesario para write-back desde DO
- **⚠️ Deploy loop**: cada push desde DO desencadena `deploy_on_push`. Durante el build el container viejo sigue sirviendo, pero al finalizar las sesiones se interrumpen. Escribir propiedades con moderación.

### Flujo ideal
1. Valuar propiedades localmente (con `cache_scraping.json` local)
2. `valuaciones_cache.json` se actualiza automáticamente
3. Commit + push → DO recibe todo
4. En DO: ver resultados cacheados, y si es necesario agregar/editar propiedades → se sincronizan a git

### Archivos
- `.gitignore` — líneas actualizadas
- `parsers/valuacion_cache.py` — `_calcular_hash_scraping` retorna `None`; skip si `None`
- `parsers/git_sync.py` — **nuevo** módulo de sincronización git
- `valu.py:38-47` — `guardar_propiedades` con `try_sync`
- `valu_detail_sections.py:654-661` — `guardar_propiedades` con `try_sync`
- `valu.yaml` — `GIT_WRITE_TOKEN` env var

### Tests: 39/39 regression pasando

---

## 📅 2026-05-23 — TAREA: Optimización de performance — FASE 1 (Infomapa + CSV + cache_scraping compartido)

### Problema
Profiling en DO mostró cuellos de botella:
- `infomapa_api_calls` (HTTP POST a rosario.gov.ar cada valuación): **3.3s**
- `load_cache_scraping` re-lectura 4 veces (venta + alquiler + cap_rate_venta + cap_rate_alq): **425ms**
- `_cargar_csv()` sin caché: **110ms**

### Cambios

#### `parsers/infomapa_api.py` — Cache persistente de Infomapa
- `_INFOMAPA_CACHE` en memoria + `data/infomapa_cache.json` en disco
- Clave: `f"{lat:.4f}_{lon:.4f}"`, TTL 24h
- `_cargar_cache_infomapa_disco()` se ejecuta al importar el módulo
- `_guardar_cache_infomapa_disco()` persiste tras cada llamada exitosa a la API
- `_cargar_csv()` ahora con caché en memoria TTL 5 min (`_CSV_CACHE`, `_CSV_CACHE_TS`)

#### `parsers/mercado_inmobiliario.py` — Reuso de cache_scraping compartido
- `obtener_mediana_cluster_v2()`: nuevo parámetro `cache_scraping=None` (dict opcional)
- `calcular_cap_rate_local()`: nuevo parámetro `cache_scraping=None`, lo pasa a clusters internos
- `valuar_propiedad_v7()`: carga `cache_scraping_compartido` UNA VEZ y lo pasa a los 3 llamados (cluster_venta, cluster_alquiler, cap_rate)

#### `.gitignore`
- `data/infomapa_cache.json` agregado (no se trackea)

### Archivos modificados
- `parsers/infomapa_api.py`
- `parsers/mercado_inmobiliario.py`
- `.gitignore`
- `docs/BITACORA_AGENTES.md`
- `docs/STATUS_ACTUAL.md`

### Tests: 39/39 regression pasando, auto_validate OK

---

## 📅 2026-05-23 — TAREA: Sacar Infomapa del camino crítico del botón "Ver detalle" (lazy-load on-demand)

### Problema
El profiling en DO mostró que el principal cuello de botella del detalle no es el rango ni la UI, sino la consulta automática a Infomapa:
- `infomapa` frío: ~3.9s
- `infomapa_api_calls`: ~3.6s
- Usuario reporta que el botón "Ver detalle" tarda ~30s (cold start + Streamlit + Infomapa combinados)

### Cambios

| Archivo | Acción |
|---------|--------|
| `parsers/mercado_inmobiliario.py` | `valuar_propiedad_v7()` nuevo parámetro `consultar_infomapa=True`. Cuando `False`, se salta el bloque Infomapa y `catastro_detalle = None` |
| `parsers/motor_vpp_core.py` | `valuar_con_cache()` nuevo parámetro `consultar_infomapa=True`, lo pasa a `valuar_propiedad_v7()` |
| `valu.py` | `valuar_con_cache()` llamado con `consultar_infomapa=False` desde el flujo detalle. Después de `mostrar_detalle_valu()`, si no hay datos catastrales, muestra botón "🔍 Consultar datos catastrales / plano". Al hacer clic, ejecuta `enriquecer_con_infomapa()`, guarda en el cache de valuaciones, y rerunea. |
| `valu_detail_sections.py` | `render_catastro()` ya no muestra "Sin datos catastrales para esta ubicacion" cuando no hay candidatos (return early). |

### Flujo resultante
1. Usuario hace clic en "Ver detalle" → apertura instantánea (~2-3s en lugar de ~30s)
2. La sección de catastro se omite (sin demora, sin llamada HTTP)
3. Si el usuario quiere ver datos catastrales → clic en "🔍 Consultar datos catastrales / plano"
4. Se ejecuta `enriquecer_con_infomapa()` (con su caché de 24h), se persiste en `valuaciones_cache.json`, se rerunea
5. En el rerun, `render_catastro()` recibe los datos del cache y los muestra normalmente

### Principios
- La consulta a Infomapa NO se ejecuta automáticamente al abrir el detalle
- "Ver detalle" es rápido (sin bloqueo de red)
- El usuario decide cuándo/cuántas veces consultar Infomapa
- La información catastral se carga solo cuando el usuario lo solicita
- Sin cambios en: lógica de valuación, clusters, alquiler, rangos, valores, historial, cálculos del motor, anclas

### Tests: 39/39 regression pasando, auto_validate OK

---

## 📅 2026-05-23 — TAREA-005: Eliminar pantallazo numérico con st.status()

### Problema
Al abrir el detalle de una propiedad, `mostrar_detalle_valu()` envía las secciones al frontend secuencialmente (header → rango → métricas → razonamiento → mapa → catastro → street view → historial). El usuario veía números grandes aparecer antes que el resto del contenido (~2.8s de render secuencial).

### Solución
Reemplazar `st.spinner()` + render directo por un wrapper `st.status(expanded=False)` que oculta todo el contenido renderizado hasta que el render completo termina, luego hace `expanded=True` para que todo aparezca a la vez.

### Cambios
- `valu.py` líneas 324-348: `st.spinner` + `mostrar_detalle_valu()` → bloque `st.status()` con expanded=False que engloba valuación + botón volver + render completo

### Flujo visual
1. Aparece `▶ Preparando detalle de Casa en Palermo...` (colapsado)
2. En segundo plano: `valuar_con_cache()` + todas las secciones renderizadas invisibles
3. Al terminar: `✔ Detalle listo` (expandido) → **todo el detalle aparece de una vez**

### Tests: 39/39 regression pasando, auto_validate OK

---

## 📅 2026-05-24 — TAREA-006: Reagrupar secciones del detalle en Comparables, Valuaciones, Acciones

### Cambios
- **📊 Comparables**: nuevo expander que agrupa Mapa de Comparables + sub-expander de Propiedades Comparables
- **📋 Valuaciones**: nuevo expander que agrupa Informe de Valuación + Historial de Valuaciones (cada uno con su expander interno)
- **⚡ Acciones**: expander unificado para Reporte PDF, Catastro y Street View

### Archivo
- `valu.py` — `mostrar_detalle_valu()` reestructurado

### Commit: `55ed6cf`

### Tests: 39/39 regression pasando, auto_validate OK

---

## 📅 2026-05-24 — TAREA-007: Botones homogéneos en fila + toggle catastro

### Cambios
- **`render_catastro()`**: nuevo parámetro `compact=True`. En modo compacto muestra solo el botón toggle "🔍 Catastro" / "✕ Ocultar". Retorna `True` si hay datos cargados.
- **`render_street_view()`**: nuevo parámetro `compact=True`. En modo compacto solo el link sin descripción.
- **"⚡ Acciones"**: los 3 elementos ahora son botones en una fila (`st.columns(3)`) con mismo estilo visual. Si hay datos catastrales, se muestra el detalle debajo de la fila.

### Toggle catastro
- Sin datos: botón "🔍 Catastro" → carga Infomapa → rerun
- Con datos: botón "✕ Ocultar" → limpia cache → rerun
- El detalle catastral completo aparece/desaparece debajo de los botones

### Archivos
- `valu_detail_sections.py` — `compact` param en render_catastro y render_street_view
- `valu.py` — fila de 3 botones + detalle condicional
- `.opencode/plans/TAREA-007.md`

### Commit: `0683d3a`

### Tests: 39/39 regression pasando, auto_validate OK

---

## 📅 2026-05-24 — TAREA-008: Agregar Av. Del Valle como barrera blanda

### Contexto
Brown 2700 Pichincha arrojaba valuación ~21% sobre listing ($236k → ~$300k). Causa: 26 comparables incluyendo propiedades de Av. del Valle (~$3,000/m²) mezcladas 100% con Brown St (~$2,360/m²) por ausencia de barrera entre ambas calles.

### Diagnóstico (OLD barriers, 745 segments)
- Ventas within 1km: 716
- Av. del Valle properties: 26 (23 same_side, 3 soft-por-Oroño)
- Av. del Valle same_side avg: **$3,191/m²** vs Brown St only: **$1,956/m²**
- Inflación directa: las del Valle diluyen el percentil al alza

### Cambios
1. **`scripts/extract_barriers.py`**: agregado `'Del Valle'` a `nombres_clave`
2. **`barreras_rosario.json`**: regenerado → 751 features (263 hard + 488 soft) — 6 nuevos segmentos para Av. Del Valle

### Resultado (NEW barriers, 751 segments)
| Métrica | Antes | Después |
|---------|-------|---------|
| Av. del Valle same_side | 23 | 3 |
| Av. del Valle cross_soft | 3 | 23 |
| Total same_side (1km) | 244 | 229 |
| Total cross_soft (1km) | 427 | 442 |

### Archivos
- `scripts/extract_barriers.py` — `'Del Valle'` en `nombres_clave`
- `barreras_rosario.json` — regenerado con 6 nuevos segmentos soft

### Commit: `544c598`

### Tests: 39/39 regression pasando, auto_validate OK

---

## 📅 2026-05-26 — TAREA-009: Conectar P33_age_blend para 5-7 comparables

### Problema
`seleccionar_percentil_por_edad()` ya contemplaba `P33_age_blend` para 5-7, pero `_filtrar_por_ventana_edad()` tenía `min_con_anio=10` y segunda ventana ±20 (vs ±30). Para Brown 2700 (2010), ±20 daba 4 comparables, insuficiente para activar blend.

### Diagnóstico Brown 2700 (año 2010, radio 300m)
- n_con_anio: 12 de 23
- n_ventana_15 (1995-2025): 3
- n_ventana_30 (1980-2040): 6
- Excluidos: 1968, 1975

### Cambio
- `min_con_anio=10` → `min_con_anio=5`
- Segunda ventana 20 → 30
- Control flow simplificado

### Resultado
| Métrica | Antes | Después |
|---------|-------|---------|
| age_filter_applied | False | True |
| n_age_filtered | 0 | 6 |
| percentil_usado | P33 | P33_age_blend |
| base_principal ($/m²) | 2057.84 | 1763.50 |

### Archivos
- `parsers/mercado_inmobiliario.py` — `_filtrar_por_ventana_edad()` reescrita
- `tests/test_age_blend_filter.py` — nuevo, 5 tests

### Tests: 96/96 pasan, auto_validate OK
