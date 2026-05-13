# 📝 BITÁCORA DE AGENTES — AVM ROSARIO

Este documento es el "diario de trabajo". Cada agente de IA que trabaje en este proyecto debe registrar aquí el progreso para que el siguiente sepa exactamente dónde retomar.

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

# Docs .MD a mantener sincronizados:
- ALGORITMOS.md (lógica)
- DICCIONARIO_DATOS.md (datos)
- MEMORIA_PROYECTO.md (reglas)
- STATUS_ACTUAL.md (estado)
- BITACORA_AGENTES.md (decisiones)
```
