# 🔍 Auditoría de Cumplimiento Normativo — Valu frente a Normas TTN (NNV) e IRAM

**Fecha:** 2026-08-31
**Alcance:** Motor AVM de Valu (`Valu_react/backend/house_valuation_engine.py`, `valuation_engine.py`)
**Tipo:** Análisis de conformidad normativa (sin cambios de código)

> ⚠️ Documento de auditoría. Los hallazgos NC-1 a NC-7 describen incumplimientos respecto del marco normativo citado por la propia metodología de Valu. No se ha modificado código; la remediación se planifica por separado.

---

## 1. Objeto y alcance

Este documento audita el motor de tasación masiva y puntual (**AVM**) de Valu Argentina frente a las **Normas Nacionales de Valuación (NNV / TTN)** dictadas por el **Tribunal de Tasaciones de la Nación** y frente a las **normas IRAM** citadas por la propia metodología (`METODOLOGIA_VALUACION_ARGENTINA.md` y su espejo en `docs/ALGORITMOS.md`).

El objetivo es identificar **qué normas NO está respetando** la motorización actual, con evidencia en el código, para fundamentar un plan de remediación posterior.

---

## 2. Marco normativo aplicable

### 2.1 Tribunal de Tasaciones de la Nación (TTN) — Normas Nacionales de Valuación (NNV)

| Norma | Contenido | Relevancia para Valu |
|---|---|---|
| **TTN 1.6** | Principios y Conceptos de Valor. Valor de Tasación | Fundamentos de todo el motor |
| **TTN 2.4** | Definiciones Técnicas y Legales | Terminología de superficies y tipologías |
| **TTN 3.1** | **Método de Comparación** (Método Comparativo) | Enfoque base → NC-1 |
| **TTN 4.1** | **Método del Costo** | Costo de Reposición → NC-3 |
| **TTN 5.2** | Planillas de comparación de valores de la tierra | Ajuste de terreno → NC-5 |
| **TTN 6.3** | Planillas de comparación de valores venales | Valores de mercado |
| **TTN 10.5** | Requisitos de un Informe de Tasación | Trazabilidad → NC-6 |
| **TTN 14.2** | **Planilla CRD (Costo de Reposición Depreciado)** | Depreciación Ross–Heidecke → NC-3 |
| **TTN 16.3** | Método Residual para Terrenos | Lotes y loteos |

### 2.2 Normas IRAM citadas por la metodología

| Norma | Contenido | Relevancia |
|---|---|---|
| **IRAM 11603** | Cómputo de superficies ponderadas | Homologación de superficies → NC-4 |
| **IRAM-ISO 17024** | Requisitos para organismos de certificación de personas (tasadores) | Competencia profesional / reporte |
| **IRAM-ISO 34850** (serie) | Normalización de tasaciones | Trazabilidad → NC-6 |
| **IVS** (International Valuation Standards) | Estándares internacionales de valuación | Marco general → NC-6 |

### 2.3 Aclaración técnica

A pesar de que el método cita implícitamente una curva tipo "IRAM 11601" para la depreciación, la **depreciación por edad y estado física con criterio de Ross & Heidecke es un criterio de la Norma TTN 14.2 (Planilla CRD)**, no una norma IRAM de valuación. Por ello, el incumplimiento de depreciación se imputa a **TTN 4.1 / 14.2** y no a una norma IRAM específica.

---

## 3. Hallazgos de incumplimiento (NC)

> Referencias de código: `house_valuation_engine.py` (HVE) y `valuation_engine.py` (VE).

---

### 🔴 NC-1 — VIOLACIÓN CENTRAL: Mezcla de valor físico con comparables (rompe el *Principio de Mercado Puro*)

- **Norma afectada:** TTN 3.1 (Método de Comparación) + Principio interno inviolable (Sección 7 de la metodología).
- **Evidencia:** `HVE:1417-1442` implementa el **"Blended AVM Dinámico Adaptativo"**:
  ```python
  valor_tasacion = (w_hed * valor_hedonico) + (w_comps * med_comps)
  # w_comps = 0.50 / 0.30 / 0.10 según CV
  ```
- **Incumplimiento:** La Sección 7 declara *“Bajo ninguna circunstancia ... mezclar porcentajes de costos teóricos. El Valor Central surge 100% de la Mediana Estadística de los Comparables Homologados.”* Para **casas**, el motor mezcla hasta **50–90% de valor físico (costo de reposición + tierra)** con la mediana de comparables, diluyendo la referencia de mercado pura que exige TTN 3.1.
- **Contradicción interna:** La propia metodología se auto-contradice: la **Sección 14** prescribe expresamente el blend, mientras la **Sección 7** lo prohíbe como "inviolable". El documento tiene dos doctrinas incompatibles que el motor resuelve a favor del blend.

---

### 🔴 NC-2 — Radio de búsqueda supera el tope infranqueable declarado

- **Norma afectada:** TTN 3.1 + política interna de homogeneidad territorial (Sección 6, basada en variograma empírico).
- **Evidencia:** `HVE:962` (`if dist_km <= 2.5`), `HVE:1460` (`radios_evaluados_km: [0.3, 0.5, 1.0, 2.5]`), `HVE:1689` (`radio_busqueda_km: 3.0`).
- **Incumplimiento:** La Sección 6 declara **máximo infranqueable de 1.0 km** en tramas urbanas consolidadas y permite **2.5 km solo** en countries/loteos de baja densidad con <3 comparables. El motor usa 2.5 km como rescate genérico para todos los casos y **reporta 3.0 km** en metadata. A 1.5–2.5 km el error medido es 19–25% (fuga de microzona), precisamente lo que la norma busca prohibir.

---

### 🟠 NC-3 — Depreciación simplificada ≠ CRD TTN 14.2 / criterio Ross–Heidecke estándar

- **Norma afectada:** TTN 4.1 + TTN 14.2 (Planilla CRD).
- **Evidencia:** `HVE:1271-1281`:
  ```python
  x = antig_anios/80; deprec = 0.5*(x+x**2)
  f_rh = max(0.62, min(1.10, 1.0 - deprec*0.15*coef_est))
  ```
  Para casas, `f_antiguedad` por escalones discretos (`HVE:529`): 1.00 / 0.96 / 0.90 / 0.82.
- **Incumplimiento:** Es una fórmula ad-hoc, no la Planilla CRD oficial con coeficientes de **Ross & Heidecke** (depreciación por edad y estado con **expectativa de vida remanente** determinada por inspección profesional). No hay separación formal **Tierra (TTN 5.2) + Mejoras (TTN 14.2)** en el valor central adoptado, hay pisos arbitrarios (0.62) y coeficientes redondeados sin base normativa.
- **Agravante:** En PH, la depreciación se aplica **dentro de la homologación de comparables** (`f_rh_suj / f_rh_c`, `HVE:1304-1305`), lo que puede distorsionar la referencia de mercado (confluye con NC-1).

---

### 🟠 NC-4 — Ponderaciones de superficie inconsistentes con IRAM 11603 declarada

- **Norma afectada:** IRAM 11603 (cómputo de superficies ponderadas).
- **Evidencia:** La fórmula general (Sección 1) establece cubierta 1.0 + semi **0.50** + descubierta **0.20**. Departamentos usan 0.5/0.2 ✓, pero el **PH usa semi 0.45 + patio 0.35 + terraza 0.25** (`HVE:1269`, `HVE:1297`). El código homóloga departamento con `0.5*semi` sin descubierta (`HVE:1336`, `HVE:1357`).
- **Incumplimiento:** Se utilizan **dos convenciones simultáneas** sin declarar cuál es la norma base. Falta un único estándar de homologación de superficies aplicado de forma consistente al sujeto y a todos los comparables.

---

### 🟠 NC-5 — Inferencia de terreno del comparable sin sustento de planilla (TTN 5.2)

- **Norma afectada:** TTN 5.2 (Planillas de comparación de tierra) + TTN 3.1.
- **Evidencia:** `HVE:1362-1378` infiere `m2_t_c` por heurísticas (×4.5, ×2.2, ×1.0 o `ratio_suj`) cuando el comparable no declara lote; el ajuste usa `usd_m2_tierra_mkt` zonales estáticos (`HVE:1341-1343`).
- **Incumplimiento:** Las asunciones morfométricas reemplazan el relevamiento real de superficie de tierra que exigen las normas; el `adj_tierra` resultante se sustenta en USD/m² de tierra estáticos y no en planillas de comparación de tierra relevadas.

---

### 🟠 NC-6 — Trazabilidad del informe de tasación no verificable (TTN 10.5 / IRAM-ISO 34850 / IVS)

- **Norma afectada:** TTN 10.5 (requisitos de informe), IRAM-ISO 34850, IVS.
- **Evidencia:** La metodología (Sección 13) declara ponderación preferencial intra-edificio (Gold Standard W=1.8) y filtro anti-auto-referencia (`VE:151`, `es_autoreferencia_circular`). El informe `detalles_avm` reporta `outliers_excluidos_count: 0` y `escalera_penalizacion_aplicada: False` fijos (`HVE:1688`, `HVE:1691`).
- **Incumplimiento:** El AVM no expone la **matriz de homologación completa** por comparable (Δterreno / Δcubierta / Δpileta / pesos intra-edificio), ni los supuestos y criterios de inspección que la TTN 10.5 exige documentar para que el informe sea defendible.

---

### 🟡 NC-7 — Ajustes post-homologación sin cap de absorción zonal (riesgo de doble cómputo)

- **Norma afectada:** TTN 3.1 + Principio de Contribución (Sección 10 del método).
- **Evidencia:** `HVE:1492-1501` aplica `valor_tasacion × (1 + f_confort_pct) + activos_confort_usd` **después** de la mediana de comparables, y luego `× f_doc × f_funcional` (`HVE:1503`). El tope de absorción zonal (Sección 10: +6..+12%) se aplica al `f_confort_pct` vía `nlp_national`, pero no se evidencia el **cap final** cuando el atributo ya fue contabilizado en el desglose físico.
- **Incumplimiento:** Riesgo de **doble cómputo**: el mismo atributo (pileta, terminaciones, confort) contado en el blend físico y de nuevo como plus post-mediana sin techo de absorción comprobable.

---

## 4. Resumen ejecutivo (qué norma → qué se viola)

| # | Gravedad | Norma | Incumplimiento |
|---|---|---|---|
| NC-1 | 🔴 Crítica | TTN 3.1 | Blend físico+comps en casas (rompe "100% Mercado") |
| NC-2 | 🔴 Crítica | TTN 3.1 / Sección 6 | Radio 2.5–3.0 km vs tope infranqueable de 1.0 km |
| NC-3 | 🟠 Alta | TTN 4.1 / 14.2 | Depreciación simplificada no-CRD Ross–Heidecke |
| NC-4 | 🟠 Media | IRAM 11603 | Doble convención de superficies (0.5/0.2 vs 0.45/0.35/0.25) |
| NC-5 | 🟠 Media | TTN 5.2 / 3.1 | Terreno inferido por heurísticas + USD/m² tierra estáticos |
| NC-6 | 🟠 Media | TTN 10.5 / IRAM-ISO 34850 | Informe sin matriz de homologación ni trazabilidad |
| NC-7 | 🟡 Baja/Media | Sección 10 / TTN 3.1 | Posible doble cómputo en ajuste post-mediana sin cap final |

---

## 5. Próximos pasos sugeridos (remediación)

1. **Paso 1 — NC-1 (decisión de negocio):** Resolver la contradicción doctrinal entre la Sección 7 (Mercado Puro) y la Sección 14 (Blend Adaptativo). Recomendación: adoptar **Mercado Puro** como doctrina (la marcada como "inviolable"); que el desglose físico quede **solo como reporte pedagógico** (tal como indica la Sección 7.3).
2. **Paso 2 — NC-2:** Restringir el rescate a 2.5 km solo para countries/loteos con <3 comparables; máximo 1.0 km en tramas urbanas; corregir `radio_busqueda_km` reportado (3.0 → 1.0/2.5 según caso).
3. **Paso 3 — NC-3:** Reemplazar la depreciación ad-hoc por curva CRD **Ross–Heidecke** (TTN 14.2) con expectativa de vida por tipología y separar Tierra (TTN 5.2) de Mejoras (TTN 14.2).
4. **Paso 4 — NC-4:** Unificar a **un único criterio de superficie** (recomendado: IRAM 11603 1.0/0.5/0.2) aplicado a sujeto y comparables; documentarlo en `ALGORITMOS.md` y `DICCIONARIO_DATOS.md`.
5. **Paso 5 — NC-5:** No inventar el lote del comparable por heurística para el ajuste monetario; excluir el `adj_tierra` no sustentado en planilla.
6. **Paso 6 — NC-6:** Exponer la matriz de homologación real por comparable y eliminar los valores fijos de `outliers_excluidos_count: 0` / `escalera_penalizacion_aplicada: False`.
7. **Paso 7 — NC-7:** Aplicar el tope de absorción zonal sobre el valor final para prevenir doble cómputo.

Cada paso de remediación se planificará en formato **TAREA** (`.opencode/plans/TAREA-NNN.md`) con su sección **JUSTIFICACIÓN RO** y validación obligatoria (`scripts/auto_validate.py` + `tests/test_regression.py`).
