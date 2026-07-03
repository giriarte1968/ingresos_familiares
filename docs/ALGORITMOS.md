# Documentación Técnica: Algoritmos de Valuación VPP

Este documento detalla la lógica matemática y algorítmica implementada en el motor de valuación `mercado_inmobiliario.py`.

## 1. Clustering de Precio por IQR (Interquartile Range)

Para evitar que propiedades con precios fuera de mercado afecten el promedio, se implementó `filtrar_cluster_m2`:
- **Segmentación**: Se diferencia por tipo de inmueble (Casa vs Departamento) y cantidad de dormitorios.
- **Filtrado**: Se eliminan valores fuera de los percentiles estadísticos según el tamaño de la muestra (N).

## 2. Ponderación por Distancia (IDW)

La función de cálculo geográfico asigna pesos a los comparables:
$$Peso = \frac{1}{Distancia^2 + 0.1}$$
Esto asegura que la tasación sea extremadamente sensible a la microzona (cuadra/manzana).

### Selección del Percentil Base por Operación
El motor utiliza diferentes percentiles del cluster limpio (post-IQR) para determinar el precio base por m², compensando la falta de datos de antigüedad en el scraping:

| Operación | Percentil | Nombre Técnico | Razón |
| :--- | :--- | :--- | :--- |
| **Venta** | **P33** | Base Conservadora | Proxy antigüedad: comparables sin año de construcción. Se posiciona en la parte baja-media para representar stock usado. |
| **Alquiler** | **P50** | Mediana de Mercado | Mercado homogéneo: la antigüedad pesa menos en alquiler que en venta. |

**Nota Crítica**: El inmueble objetivo SÍ posee año de construcción y recibe su ajuste individual (`delta_anti`) sobre esta base conservadora (P33). Cambiar P33 $\rightarrow$ P50 en venta requeriría recalibrar todo el modelo y los tests de regresión.

Referencia: `parsers/mercado_inmobiliario.py`, función `obtener_mediana_cluster` (v12.3).

## 3. Fórmula de Factores — Modelo Multiplicativo Puro (TAREA-071)

Lógica de base: El valor de mercado es sensible al tiempo. Para comparativas de regresión y tasaciones actuales, el parámetro `fecha_ref` debe coincidir con el mes de ejecución para evitar desviaciones por inflación o tendencia de mercado.

A partir de TAREA-071, se eliminó el modelo aditivo (suma de deltas) y se reemplazó por un modelo **multiplicativo puro**:

$$Factor_{total} = factor_{estado} \times factor_{calidad} \times factor_{anti}$$

Donde:
- **factor_estado**: Tabla lookup según `estado_detalle` (malo→0.85, regular→0.92, bueno→1.00, muy bueno→1.03, excelente→1.05, a_estrenar→1.08)
- **factor_calidad**: Tabla lookup según `calidad_edificio` (baja→0.95, media→1.00, alta→1.04, excelente→1.06, premium→1.08)
- **factor_anti**: Depreciación por antigüedad (0.6% anual, cap mínimo 0.40)
- **Sin clamp final**: El producto de factores no se acota a [0.70, 1.35]

### Factores eliminados (ruido)

Ya no forman parte de la fórmula:
- vista (frente/contrafrente)
- piso (altura, PB)
- ubicación_tipo (calle/avenida)
- gas_ok
- tipo_balcon / balcón
- funcional (lavadero/placares)
- amenities (seguridad, pileta, parrilla, etc.)
- disposicion
- cocina
- preinst (preinstalación de aire)

Estos factores eran ruido estadístico: no correlacionaban significativamente con el precio de venta en el mercado de Rosario. Su eliminación simplifica el modelo y reduce la varianza.



## 3.x. Atenuación Dinámica de Antigüedad (Venta P33)

Para evitar la "doble penalización" en propiedades antiguas valuadas con la base conservadora (P33), se aplica una función de atenuación por tramos (piecewise) al $\Delta \text{Antigüedad}$.

### Justificación
El percentil P33 ya actúa como un proxy de stock usado/antiguo. Aplicar un castigo lineal severo adicional sobre una base ya baja destruye el valor de mercado de propiedades premium antiguas (ej. pisos altos céntricos de los 70s).$$

**Configuración Actual:**
- `UMBRAL_PENALIZACION`: -0.15
- `FACTOR_EXCESO`: 0.10
- `ATENUACION_BASE`: 1.00

## 4. Análisis de Alquiler y ROI

### Cap Rate Derivado del Mercado Local (v8.1)

El alquiler se calcula derivando el Cap Rate directamente de los datos de scraping:

1. **Cluster de VENTA** (P33) y **Cluster de ALQUILER** (P50) para la misma ubicación
2. **Fórmula**: `cap_rate = (alquiler_P50_m2_anual_USD) / (venta_P33_m2_USD)`
3. **Requisito**: >= 5 comparables de alquiler en el radio

**Fallback**: Si no hay datos suficientes:
- → ROI_ZONAL estimado (tabla de referencia por zona)
- → La UI muestra badge 🔴 ROJO avisando que es estimación

**Rango de alquiler**:
- Si data-driven: derivado de confianza (ALTA: ±8%, MEDIA: ±12%, BAJA: ±15%)
- Si fallback: ±15% fijo

---

### Valores de Valuación (v8.2)

| Escenario | Base usada | Descripción |
|-----------|-----------|------------|
| **Conservador** | base_conservadora = min(P25, blend) | Precio mínimo de mercado |
| **Mercado** | base_mercado = blend(P33, α=0.60) | **Valor Lista** (valor de publicación) |
| **Optimista** | base_optimista = max(P75, blend) | Precio máximo de mercado |

**Importante**: El Valor Lista = escenario Mercado (no conservador).

### Ancla Algorítmica de Alquiler
Si la muestra de alquileres es insuficiente, se proyecta:
$$Renta = (AnclaVentaUSD \times 0.045 / 12) \times USDT\_ARS$$

### Ajuste v14.0: Patio Grande en Planta Baja

Para propiedades en Planta Baja (piso=0) con patio grande:

**1. Coeficiente de superficie descubierta:**
- Si `m2_descubiertos >= 20m²`: coeficiente sube de 0.20 a 0.25
- Reconoce el valor social/recreativo del patio en mercado Rosario

**2. Mitigación de惩罚 por planta baja:**
- Piso 0 estándar: factor = 0.88 (-12%)
- Piso 0 + patio >= 15m²: factor = 0.98 (-2%)
- El patio compensa falta de altura con aire y luz natural

**Caso ejemplo: Vera Mujica 912**
- m² cubiertos: 35, m² descubiertos: 24, m² comunes: 25
-Antes: m² equiv = 43.55, Valor = $49,531
-Después: m² equiv = 43.75, Valor = $55,530 (+46% plusvalía)

---

## Leyes del Motor VPP - Calibración Rosario 2026 (TAREA-073)

### 1. Fórmula de Venta — Modelo Base Puro
La valuación de venta para departamentos/PH usa:

```
valor_venta = (m2_equiv × m2_microzona × size_adjustment(m2, macrozona)) + cocheras + baulera
```

Aclaraciones:
- `m2_microzona = m2_base_venta` (cluster Data-Driven siempre — RO-08). Ancla solo como referencia informativa, no como precio base.
- `size_adjustment(m2, macrozona)` = `calcular_size_adjustment(m2, macrozona)_venta()`: descuento progresivo para unidades >80m².
- **No hay factores hedónicos** (estado, calidad, antigüedad, NLP). El análisis ML demostró que:
  - Ubicación explica ~80% del precio (XGBoost: lat=44%, lon=36%)
  - m² explica ~16%
  - Edad es **confounding effect** con ubicación (grid RF por celda: Mabel +0.2% en 55 años)
  - Estado/calidad = double premiums sobre el anchor
- Activos aditivos (cocheras + baulera) se suman vía `calcular_valor_activos()`.

### 2. Fórmula de Alquiler (mantiene lógica original)
```
alquiler_mensual_ars = m2_equiv_alq × m2_base_alq × factores_alq × gap_alq × (1 + nlp_capped)
```

- `factores_alq = factor_estado × factor_calidad × factor_anti × f_puros` (atenuación 50% en estado/calidad)
- `nlp_capped`: 3% para 1 dorm, 5% para 2+ dorm
- NLP y factores hedónicos se conservan en alquiler (decisión TAREA-073)

### HISTÓRICO: Factores eliminados en TAREA-073
Los siguientes factores se usaban en TAREA-071 y fueron eliminados por decisión ML:
- `factor_estado`: lookup (malo→0.85 ... a_estrenar→1.08)
- `factor_calidad`: lookup (baja→0.95 ... premium→1.08)
- `factor_anti`: depreciación 0.6% anual con atenuación dinámica
- `ajuste_nlp`: NLP cap 3% / 5%
- `f_puros` (ventilación, piso): solo en alquiler

### 7. Exclusión de factor_pasillo
- `factor_pasillo` NO forma parte de la fórmula general de departamentos/PH.
- Si existiera una lógica futura para casas/PH especiales, debe vivir en un motor separado.

## 7. Barreras Geográficas (Rosario)

### Tipología de Barreras
| Tipo | Ejemplos | Comportamiento | Peso en IDW |
| :--- | :--- | :--- | :--- |
| **DURA** | Ferrocarril FC Mitre, Circunvalación | Exclusión total | weight *= 0.20 (80% penalty) |
| **BLANDA** | Av. Pellegrini, Av. 27 de Febrero, Av. Oroño, Av. Francia, Av. Del Valle | Fricción (no exclusión) | weight *= 0.90 (10% penalty) |

### Ancla Algorítmica de Alquiler
Si la muestra de alquileres es insuficiente, se proyecta:
$$Renta = (AnclaVentaUSD \times 0.045 / 12) \times USDT\_ARS$$

### Ajuste v14.0: Patio Grande en Planta Baja

Para propiedades en Planta Baja (piso=0) con patio grande:

**1. Coeficiente de superficie descubierta:**
- Si `m2_descubiertos >= 20m²`: coeficiente sube de 0.20 a 0.25
- Reconoce el valor social/recreativo del patio en mercado Rosario

**2. Mitigación de惩罚 por planta baja:**
- Piso 0 estándar: factor = 0.88 (-12%)
- Piso 0 + patio >= 15m²: factor = 0.98 (-2%)
- El patio compensa falta de altura con aire y luz natural

**Caso ejemplo: Vera Mujica 912**
- m² cubiertos: 35, m² descubiertos: 24, m² comunes: 25
-Antes: m² equiv = 43.55, Valor = $49,531
-Después: m² equiv = 43.75, Valor = $55,530 (+46% plusvalía)

---

## Leyes del Motor VPP - Calibración Rosario 2026 (TAREA-073)

### 1. Fórmula de Venta — Modelo Base Puro
La valuación de venta para departamentos/PH usa:

```
valor_venta = (m2_equiv × m2_microzona × size_adjustment(m2, macrozona)) + cocheras + baulera
```

Aclaraciones:
- `m2_microzona = m2_base_venta` (cluster Data-Driven siempre — RO-08). Ancla solo como referencia informativa, no como precio base.
- `size_adjustment(m2, macrozona)` = `calcular_size_adjustment(m2, macrozona)_venta()`: descuento progresivo para unidades >80m².
- **No hay factores hedónicos** (estado, calidad, antigüedad, NLP). El análisis ML demostró que:
  - Ubicación explica ~80% del precio (XGBoost: lat=44%, lon=36%)
  - m² explica ~16%
  - Edad es **confounding effect** con ubicación (grid RF por celda: Mabel +0.2% en 55 años)
  - Estado/calidad = double premiums sobre el anchor
- Activos aditivos (cocheras + baulera) se suman vía `calcular_valor_activos()`.

### 2. Fórmula de Alquiler (mantiene lógica original)
```
alquiler_mensual_ars = m2_equiv_alq × m2_base_alq × factores_alq × gap_alq × (1 + nlp_capped)
```

- `factores_alq = factor_estado × factor_calidad × factor_anti × f_puros` (atenuación 50% en estado/calidad)
- `nlp_capped`: 3% para 1 dorm, 5% para 2+ dorm
- NLP y factores hedónicos se conservan en alquiler (decisión TAREA-073)

### HISTÓRICO: Factores eliminados en TAREA-073
Los siguientes factores se usaban en TAREA-071 y fueron eliminados por decisión ML:
- `factor_estado`: lookup (malo→0.85 ... a_estrenar→1.08)
- `factor_calidad`: lookup (baja→0.95 ... premium→1.08)
- `factor_anti`: depreciación 0.6% anual con atenuación dinámica
- `ajuste_nlp`: NLP cap 3% / 5%
- `f_puros` (ventilación, piso): solo en alquiler

### 7. Exclusión de factor_pasillo
- `factor_pasillo` NO forma parte de la fórmula general de departamentos/PH.
- Si existiera una lógica futura para casas/PH especiales, debe vivir en un motor separado.

## 7. Barreras Geográficas (Rosario)

### Tipología de Barreras
| Tipo | Ejemplos | Comportamiento | Peso en IDW |
| :--- | :--- | :--- | :--- |
| **DURA** | Ferrocarril FC Mitre, Circunvalación | Exclusión total | weight *= 0.20 (80% penalty) |
| **BLANDA** | Av. Pellegrini, Av. 27 de Febrero, Av. Oroño, Av. Francia, Av. Del Valle | Fricción (no exclusión) | weight *= 0.90 (10% penalty) |

### Lógica de Implementación
- `check_barrier_crossing()` retorna: `'hard'`, `'soft'` o `False`
- **En Cluster (obtener_mediana_cluster_v2)**: Solo excluye barreras DURAS
- **En IDW (calcular_precio_m2)**: Aplica penalty según tipo

### Justificación
En Rosario, las grandes avenidas son una "fricción" pero no un "corte". Un castigo del 10% es suficiente para que el motor prefiera propiedades del mismo lado, pero sin ignorar datos relevantes del otro lado. Los ferrocarriles (vía en trinchera) sí representan una división real del tejido urbano.

## 8. Superficies Diferenciadas (Propias vs Uso Común Exclusivo)

### Coeficientes diferenciados (Rosario 2026)
| Campo | Descripción | Coef Normal | Coef Patio Grande (≥20m²) |
| :--- | :--- | :--- | :--- |
| **m2_cubiertos** | Superficie cubierta habitable | 100% | 100% |
| **m2_semicubiertos** | Balcón, terraza techada | 45% | 45% |
| **m2_descubiertos_propios** | Patio propio, jardín escriturado | 0.25 | 0.30 |
| **m2_descubiertos_comun_exclusivo** | Balcón descubierto, terasa común uso exclusivo | 0.15 | 0.20 |

### Coeficientes especiales por contexto
| Contexto | Coeficiente | Justificación |
| :--- | :--- | :--- |
| PB con patio ≥10m² | 0.40 | Extensión funcional del living |
| Piso alto, < 20m² | 0.15 | Balcón/terraza recreativo |
| Piso alto, ≥ 20m² | 0.20 | Terraza grande |

### Justificación legal
- **m2_descubiertos_propios**: Dominio pleno del propietario → mayor valor
- **m2_descubiertos_comun_exclusivo**: Bien común sujeto a reglamento de copropiedad → menor valor
- **PB patio**: En Rosario, patio en PB es extensión habitable (no solo recreativo)

### UI Simplified (Opción A)
4 campos exactos:
1. m² cubiertos
2. m² semicubiertos  
3. m² descubiertos propios
4. m² descubiertos uso común

### Campos eliminados del UI
- m² comunes (escritura)
- m² comunes exclusivos
- m² semicubiertos propios / uso exclusivo
- Selectbox "Tamaño" semicubiertos
- Selectbox "Tipo balcón"
- Checkbox "Balcón"
- Amenities duplicados (balcon_terraza, terraza_comun)

## 9. Sistema de Historial de Valuaciones (v15.0)

Para garantizar la auditabilidad y el seguimiento de activos en el tiempo, se implementó un sistema de historial inmutable basado en el estándar JSONL (JSON Lines).

### Lógica de Persistencia
1. **Append-Only**: Cada evento de valuación (recálculo por scraping, cambio manual o TTL) genera un nuevo registro en `data/valuaciones_historial.jsonl`. Nunca se borran registros antiguos.
2. **Snapshot Completo**: Cada registro guarda el estado exacto del momento:
   - **snapshot_propiedad**: Los 45+ atributos usados para el cálculo.
   - **snapshot_mercado**: Dólar Binance, m² base de zona, cantidad de comparables y hash del scraping.
   - **resultado**: Valor de mercado, escenarios conservador/optimista y Cap Rate.
3. **Control de Versiones de Scraping**:
   - Cada vez que se detecta un cambio en `cache_scraping.json`, se genera un snapshot en `data/scraping_history/`.
   - Se utiliza un hash MD5 para evitar duplicar archivos de scraping idénticos.

### Capacidades de Análisis
- **Evolución Temporal**: Generación de gráficos de serie de tiempo comparando los tres escenarios de precio.
- **Detección de Variación**: Herramienta de comparación entre dos fechas arbitrarias para descomponer el cambio de valor (ej. "¿Cuánto del aumento fue por el dólar y cuánto por el mercado local?").
- **Auditoría de Errores**: Posibilidad de reconstruir cualquier tasación pasada con los mismos datos originales.

---

## 11b. Ventanas Progresivas de Edad

La función `_filtrar_por_ventana_edad()` usa dos ventanas progresivas:

```
±15 años → si n ≥ 5, acepta pool
±30 años → si n ≥ 5, acepta pool (si ±15 no alcanzó)
           si n < 5 en ambas, fallback al pool completo (P33)
```

El umbral es ≥5 porque el selector `seleccionar_percentil_por_edad()` ya discrimina entre 5-7 (P33_age_blend) y 8+ (P40/P45/P50). Antes se exigía ≥8, lo que impedía activar `P33_age_blend` para 5-7 comparables.

Esto evita que propiedades modernas en zonas con edificios viejos (ej. Centro) se vean contaminadas por comparables 25+ años más antiguos, manteniendo estabilidad en propiedades donde ±15 ya captura suficientes comparables de edad similar.

## 12. Valores de Referencia (TAREA-071 — Modelo Multiplicativo)

Estos son los valores definitivos con el nuevo modelo multiplicativo puro.
Reemplazan todos los valores de calibración previos.

| Propiedad   | Año  | Pool total | n_age | %ile usado | Valor ref  | Cambio vs aditivo |
|-------------|------|-----------|-------|------------|------------|-------------------|
| Mabel       | 1998 | 46        | 25    | P50        | ~$86,092   | +16%              |
| Ayacucho    | 2002 | 46        | 16    | P45        | ~$43,160   | +11%              |
| Vera Mujica | 2009 | 27        | 8     | P40        | ~$64,636   | +52% (sin desc PB)|
| P1200       | 1977 | 36        | 12    | P45        | ~$190,957  | (sin cambios)     |

**Nota**: El incremento en Vera se debe a la eliminación del factor_piso (PB con patio ya no recibe descuento). Es intencional según TAREA-071 — los factores de ruido (vista, piso, balcón, etc.) fueron eliminados del modelo.

**Regla de percentil dinámico (CV normalizado, TAREA-111):**

El motor selecciona el percentil según la **dispersión del pool** medida por el coeficiente de variación (CV), normalizado por el CV de referencia de la macrozona (`cv_ref`):

```
ratio = cv_actual / cv_ref
```

| n   | ratio cv/cv_ref | Percentil | Etiqueta |
|-----|----------------|-----------|----------|
| ≥10 | < 1.10         | P50       | P50      |
| ≥8  | < 1.30         | P45       | P45      |
| ≥5  | < 1.60         | P40       | P40      |
| any | ≥ 1.60 o n<5   | P33       | P33      |

**CV_REF** se almacena en `data/zonas_depreciacion.json` por macrozona y es editable desde la UI (expander "Ajuste por Tamaño"). Los valores iniciales se midieron empíricamente del caché de valuaciones:

| Macrozona | CV_REF |
|-----------|--------|
| Centro Premium | 0.339 |
| Macrocentro | 0.438 |
| Norte | 0.489 |
| Oeste | 0.494 |
| Sur (default) | 0.416 |
| Resto de Rosario | 0.416 |

**Ejemplo Mabel**: Centro Premium, n=24, cv=0.35, cv_ref=0.339 → ratio=1.032 < 1.10 → **P50** (estable, no salta entre ventanas Natural/Retro).

**Fallback legacy**: Si no se provee `cv_ref`, se usan umbrales absolutos históricos:
- n≥10 y CV<25% → P50
- n≥8 y CV<35% → P45
- n≥5 y CV<45% → P40
- else → P33

Implementación en `parsers/cluster_filters.py` → `seleccionar_percentil_por_calidad_pool()`.

### FASE 3: Age Blend para 5-7 Comparables

Cuando hay 5-7 comparables de edad similar, el motor NO descarta toda la señal de edad. En lugar de volcar al pool completo, aplica un blend lineal:

```
base_final = alpha_age * base_age + (1 - alpha_age) * base_all
```

Donde:
- `base_age` = P33 del pool filtrado por edad (con blend same/cross α=0.70)
- `base_all` = P33 del pool completo (sin filtro de edad, mismo blend)
- `alpha_age` según n:

| n_age | alpha_age | Interpretación |
|-------|-----------|----------------|
| 7     | 0.75      | 75% peso del pool etario |
| 6     | 0.60      | 60% peso del pool etario |
| 5     | 0.45      | 45% peso del pool etario (mayoría pool completo) |

**Comportamiento:**
- Si n_age ≥ 8 → igual que hoy (P40/P45/P50 directo)
- Si 5 ≤ n_age < 8 → blend suave, NO se pierde señal de edad
- Si n_age < 5 → pool completo (igual que hoy)

**Metadata expuesta en `meta` del cluster:**
- `age_blend_applied`: True/False
- `alpha_age_blend`: valor de alpha aplicado
- `base_age`: P33 del pool etario
- `base_all`: P33 del pool completo

**En UI (detalle técnico):** se muestra un recuadro azul con:
"Cluster con edad similar insuficiente (n=6). Se aplicó blend entre pool etario y pool completo. Alpha edad = 0.60."

### Método de Cálculo del Percentil

El motor usa **percentil posicional discreto** (no interpolación lineal):

```
idx = int(n * p / 100)
idx = min(idx, n - 1)
idx = max(idx, 0)
valor = lista_ordenada[idx]
```

**NO se usa `np.percentile()` con interpolación lineal porque:**
- El sistema fue calibrado sobre percentiles discretos desde su origen
- Con muestras chicas (8-12 comparables) la interpolación genera drift artificial de hasta ~3.6%
- En comparables inmobiliarios es más defendible usar valores realmente observados en el mercado
- El método discreto es más auditable: cualquier persona puede verificar que el percentil es un valor real de la muestra

Implementación en `parsers/cluster_filters.py` → `calcular_percentil()`.

---

## 13. Recalibración Temporal de Anclas (v4.1)

### Ventanas temporales progresivas

Cada ancla se recalibra contra el scraping actual usando ventanas con prioridad a lo más reciente:

| Ventana | Ponderación | Objetivo |
|---------|------------|----------|
| 90 días | P50 simple | Mercado inmediato (77 anclas alcanzan) |
| 180 días | P50 simple | Mercado reciente (1 ancla adicional) |
| 365 días | P50 con decay exponencial (λ=0.005) | Mercado amplio (0 adicionales) |
| Sin datos | Mantener v3 | Zonas sin cobertura (44 anclas) |

### Decaimiento temporal

`peso = exp(-0.005 * dias)`:
- 90 días → pesa 64%
- 180 días → pesa 41%  
- 365 días → pesa 16%

### Clasificación

| Estado | Criterio | Acción |
|--------|----------|--------|
| auto_aprobable | n≥100 y desvío≤20% | Reemplazar v3 automáticamente |
| revision_manual | n≥20 (resto) | Revisar antes de reemplazar |
| mantener_v3 | n<20 en 365d | Mantener valor original |

### Resultados (122 anclas)

| Estado | Cantidad |
|--------|----------|
| Auto-aprobables | 31 |
| Revisión manual | 47 |
| Mantener v3 | 44 |

---

## 14. Arquitectura de Funciones (post FASE 5)

### Motor de Clustering
```
obtener_mediana_cluster_v2() → orquestador (~100 líneas)
  └── parsers/cluster_filters.py (7 helpers)
      ├── filtrar_por_radio()           — filtro geoespacial
      ├── filtrar_por_tipo_operacion_dorms() — filtro por atributos
      ├── filtrar_por_fecha()           — filtro por ventana temporal
      ├── separar_por_barreras()        — separación same/cross/hard
       ├── calcular_percentil()          — percentil discreto (no interpola)
      ├── calcular_blend_p33()          — blend de P33 same/cross
      └── seleccionar_percentil_por_edad() — regla de percentil dinámico
```

### Motor de Valuación
```
valuar_propiedad_v7() → función principal (~400 líneas, 6 secciones)
  
  Secciones internas:
  ├── SECCIÓN 1: Datos de entrada y logging
  ├── SECCIÓN 2: m2 equivalentes y antigüedad
  ├── SECCIÓN 3: Rango de venta (inline, márgenes IQR)
  ├── SECCIÓN 4: Resolution metadata (delegada a helper)
  │   └── parsers/valuacion_helpers.py → ensamblar_metadata_resolucion()
  ├── SECCIÓN 5: Razonamiento narrativo
  └── SECCIÓN 6: Return con resultado completo

## 15. Enriquecimiento de Año de Construcción para Comparables (3-Step Lookup)

`enriquecer_anio_comparable(comp, max_dist_m=30, max_dist_exacta=200)` asigna `anio_construccion` a cada comparable usando `rosario_avm_full.csv` como única fuente (el scraping no tiene año).

**ADVERTENCIA (TAREA-014/015):** La versión original del 3-step (≤50m + esquina ≤30m) inflaba valuaciones (P1200: $137,888 → $190,957). Se reemplazó por match exacto + token ≤30m sin esquina.

### Los 3 pasos:

**Paso 0 — Match exacto por dirección (≤200m, siempre ALTA)**
- Consulta `_CATASTRO_INDEX` con `(calle_normalizada, numero)` del comparable
- Si existe un PH catastral con la misma dirección (calle+número) y está a ≤200m → ALTA
- La distancia amplia (200m) es segura porque sabemos que es el mismo edificio, incluso si las coordenadas del scraping son imprecisas
- Este índice de ~14.500 direcciones se construye en `cargar_catastro()` pero nunca se consultaba — dead code reactivado

**Paso 1 — Token containment (≤30m, siempre ALTA)**
- Busca en catastro PHs a ≤30m del comparable
- Aplica `_token_contenido()`: todos los tokens de la dirección del comparable deben estar contenidos en el string de dirección catastral
- Filtra además con `_filtrar_calle_diccionario()` sobre el resultado del bbox (solo 15-20 filas) usando `calles_rosario.json`
- Siempre confianza ALTA

**Paso 2 — Intersecciones con nearest + token (≤30m, siempre MEDIA)**
- Si Pasos 0-1 fallaron, encuentra el PH catastral más cercano dentro del bbox (±0.001°)
- Valida que los tokens de su dirección contengan los tokens del comparable
- Siempre asigna confianza MEDIA

### Confianza
| Paso | Distancia | Confianza |
|------|-----------|-----------|
| 0    | ≤200m     | ALTA      |
| 1    | ≤30m      | ALTA      |
| 2    | ≤30m      | MEDIA     |
| Ninguno | —      | NONE      |

### Helpers internos
- `_token_contenido(tokens_comp, tokens_catastro)`: retorna True si todos los tokens del comparable están contenidos en la lista de tokens catastrales
- `_filtrar_calle_diccionario(calle_raw, calles_dict)`: normaliza la calle usando `calles_rosario.json` con prefijo matching (mínimo 2 caracteres): "ov" → "ovidio", "av" → "avenida"
- `_extraer_interseccion(dir_str)`: detecta intersecciones en texto RAW (antes de reemplazos): "Av. del Valle y Ovidio Lagos" → ("Av. del Valle", "Ovidio Lagos")

### Resultados (Brown 2700)
| Métrica | Antes (1-word match) | Después (3-step) |
|---------|---------------------|------------------|
| Enriquecidos | ~11/25 (44%) | 27/33 (82%) |
| ALTA | ~6 | 15 |
| MEDIA | ~5 | 12 |
| NONE | ~14 | 6 |

### Carga lazy de calles_rosario.json
- `_CALLES_ROSARIO` se carga en el primer llamado a `_filtrar_calle_diccionario()`, no al importar el módulo
- `_CALLES_DICT_FILTER_CACHE` cachea resultados de `_filtrar_calle_diccionario()` en memoria

---

## 16. Amenities y Anti Doble Conteo NLP (v10.0)

Los amenities estructurados cargados por formulario (`detalles_categoria`) tienen **prioridad** sobre el NLP.
Si un amenity está presente en `detalles_categoria`, las keywords equivalentes en `descripcion_libre` no suman nuevamente.

### Centralización

Todos los amenities se procesan en `calcular_delta_amenities()` en `mercado_inmobiliario.py`.
Retorna un delta aditivo que se suma a `suma_cruda` en `calcular_factores()`.

### Pesos (datos_mercado.json → AMENITY_WEIGHTS)

| Amenity | Delta |
|---|---:|
| caldera_central | 0.010 |
| radiadores | 0.010 |
| seguridad_24hs | 0.030 |
| seguridad_tag | 0.008 |
| seguridad_camaras | 0.006 |
| seguridad_totem | 0.006 |
| aberturas_premium | 0.020 |
| balcon_terraza | 0.010 |
| terraza_comun | 0.005 |
| terraza_compartida | 0.005 |
| parrilla_propia | 0.020 |
| parrilla_compartida | 0.005 |
| pileta | 0.015 |
| sum | 0.010 |
| gym | 0.005 |

**Cap total:** `AMENITY_TOTAL_CAP = 0.06` (6%).

### Legacy

`parrilla` en datos existentes se trata automáticamente como `parrilla_compartida`.

### Anti doble conteo NLP

`AMENITY_NLP_EXCLUSION_MAP` en `nlp_inmobiliario.py` mapea cada amenity estructurado a sus keywords NLP equivalentes.
Si el amenity está en `detalles_categoria`, esas keywords se excluyen del análisis NLP.

**Ejemplo:**
- `parrilla_compartida` en amenities → bloquea NLP de "parrilla", "parrillero"
- `terraza_compartida` → bloquea NLP de "terraza compartida", "terraza común"

### Pesos NLP reducidos (amenities comunes)

Los pesos NLP de amenities comunes se redujeron para no saturar el cap NLP (3% monoambientes, 5% 2+ dorm):

| Keyword NLP | Peso |
|---|---:|
| pileta, piscina | 0.02 |
| parrilla, parrillero | 0.01 |
| terraza compartida/común | 0.01 |
| sum | 0.01 |
| gimnasio, gym | 0.01 |
| seguridad 24 horas | 0.02 |

## 7. Rango de Valuación (3 Escenarios) — FASE 2

El rango de valuación se calcula como un margen simétrico alrededor del valor principal (`valor_venta`), usando la dispersión estadística del cluster.

### Algoritmo (`calcular_rango_venta()` en `valuacion_helpers.py`)

Es la única fuente de verdad del rango de venta. No hay lógica inline duplicada.

```
1. Calcular IQR relativo del cluster:
   iqr_rel = (P75 - P25) / P50
   half_iqr_rel = iqr_rel / 2

2. Margen raw (solo 50% del half-IQR):
   raw_margin = half_iqr_rel * 0.50

3. Floors y caps según calidad del cluster:
   ≥50 muestras y radio ≤300m → floor=0.05, cap=0.08
   ≥25 muestras               → floor=0.06, cap=0.10
   ≥10 muestras               → floor=0.08, cap=0.14
   <10 muestras               → floor=0.10, cap=0.18
   Confianza BAJA             → cap = max(cap, 0.20)

4. Margen final:
   margen_error = clamp(raw_margin, floor, cap)

5. 3 escenarios simétricos:
   conservador = valor * (1 - margen_error)
   mercado     = valor
   optimista   = valor * (1 + margen_error)

6. Spread:
   spread_pct = (opt - cons) / mercado * 100
```

### Output dict (`rango_venta`):
```python
{
    'min': int,           # valor conservador
    'mid': int,           # valor principal (centro)
    'max': int,           # valor optimista
    'spread_pct': float,  # spread relativo (%)
    'margen_error': float,# margen aplicado (decimal)
    'p25_cluster': float, # P25 del cluster (USD/m²)
    'p50_cluster': float, # P50 del cluster (USD/m²)
    'p75_cluster': float, # P75 del cluster (USD/m²)
    'metodo_rango': str,  # 'valor_estimado_mas_margen_estadistico'
}
```

**Nota**: El `rango_m2` que ve el usuario en UI ya no es ±10% hardcodeado. Usa el rango real del cluster. Para clusters grandes (≥50 muestras, ≤300m) el margen puede ser tan ajustado como ±5%; para clusters chicos puede llegar a ±18%.

### Helpers integrados (todos activos y con tests):
```
calcular_rango_venta()    ← fuente única de rango (IQR + floors/caps)
procesar_alquiler()       ← alquiler con cap rate data-driven o fallback zonal
ensamblar_metadata_resolucion() ← metadata de resolución para UI
```

---

## 6. Generación de Anclas por Grilla Espacial (TAREA-035)

### 6.1 Problema original

Las 117 anclas artesanales (`v5_1`) tenían:
- **Cobertura insuficiente**: solo 46% de propiedades a ≤300m de un ancla
- **Sesgo `v3_heredada`**: 12 anclas del sistema anterior estaban 40-50% sobreestimadas vs mercado actual
- **PN mal posicionado**: `rio_puerto_norte` estaba 2.8km de su posición real (en el puerto, no en Av. Carballo)

### 6.2 Solución: Grid Espacial 400m

Se reemplazan las anclas artesanales por una grilla regular de 400m × 400m sobre toda la ciudad de Rosario.

#### Algoritmo

```
Entrada: cache_scraping.json (8.366 propiedades venta con lat/lon + valor_m2 + date_created)
         TABLA_CT (curva de ajuste temporal, ver sección 6.5)

1. Para cada propiedad:
   a. Calcular meses desde su date_created hasta fecha_ref (2026-06-01)
   b. Calcular Ct según segmento:
      - USADO (99.9%): Ct = 1.0 + (Ct_base - 1.0) × 1.12
      - NUEVO (0.1%):  Ct = 1.0 + (Ct_base - 1.0) × 0.95
   c. lista_hoy = valor_m2 × Ct

2. Asignar a grilla:
   dlat = 400m → grados latitud
   dlon = 400m → grados longitud (ajustado por coseno de latitud)
   ix = floor((lon_prop - lon_min) / dlon)
   iy = floor((lat_prop - lat_min) / dlat)

3. Para cada celda con ≥5 propiedades:
   a. Centroide geográfico: lat = avg(lat_props), lon = avg(lon_props)
   b. Valor ancla: mediana de lista_hoy de las propiedades en la celda
   c. Nombre: calle más frecuente + zona comercial (con filtro de distancia)
   d. Zona comercial:
      - Se toma la `zona` más común entre las propiedades de la celda
      - Se valida que el centroide esté dentro del radio de referencia (ej. Martin ≤ 1.5km)
      - Si está fuera del radio o no hay zona, cae a macrozona geográfica
   e. Macrozona de respaldo: asignada por posición geográfica (centro/norte/sur/oeste)
```

### 6.3 Naming de Anclas

Formato: `calle_mas_comun_zona_comercial`

Ejemplos:
- `montevideo_martin` (Martin)
- `pellegrini_pellegrini` (Pellegrini)
- `french_puerto_norte` (Puerto Norte)
- `carballo_norte` (Macrozona Norte)
- `francia_sur` (Macrozona Sur)

Limpieza de calles: se eliminan tokens de ruido (tipos de propiedad, descriptores, artículos) y tokens mixtos letras+números que no sean calles tipo "3_de_febrero".

Zona comercial única (no dos calles) para evitar inestabilidad en celdas pequeñas (5-28 props).

### 6.4 Macrozona y Zona Comercial

Asignada por posición geográfica relativa al centro (-32.92776, -60.69769). Las zonas comerciales se asignan solo si el centroide de la celda está dentro del radio de referencia calculado desde cache_scraping.json:

| Zona | Centro real | Radio | Anclas |
|------|------------|-------|--------|
| Centro (macro) | Radio < 1.5km del centro | - | 32 |
| Norte (macro) | Al norte, corredor ribereño | - | 44 |
| Sur (macro) | Al sur, corredor ribereño | - | 162 |
| Oeste (macro) | Tierra adentro (al oeste) | - | 60 |
| Pellegrini | (-32.9551, -60.6507) | 1500m | 8 |
| Martin | (-32.9500, -60.6525) | 1500m | 5 |
| Pichincha | (-32.9373, -60.6581) | 1200m | 4 |
| Puerto Norte | (-32.9250, -60.6660) | 1200m | 4 |
| Abasto | (-32.9589, -60.6453) | 1200m | 3 |

### 6.5 Tabla Ct (Ajuste Temporal)

La tabla representa el movimiento del mercado de departamentos de Rosario desde el piso de 2023 hasta el amesetamiento de 2026:

| Meses | Ct_base | Ct_usado (×1.12) | Descripción |
|-------|---------|-------------------|-------------|
| 0 | 1.000 | 1.000 | Hoy |
| 3 | 1.011 | 1.012 | |
| 6 | 1.033 | 1.037 | |
| 12 | 1.105 | 1.118 | |
| 18 | 1.207 | 1.232 | |
| 24 | 1.235 | 1.263 | |
| 30 | 1.267 | 1.299 | Pico del mercado |
| 36 | 1.254 | 1.284 | |
| 42 | 1.203 | 1.227 | |
| 48 | 1.173 | 1.194 | |
| 54 | 1.152 | 1.170 | |
| 60 | 1.131 | 1.147 | |
| 66 | 1.105 | 1.118 | |
| 72 | 1.067 | 1.075 | |
| 78 | 1.027 | 1.030 | |
| ≥83 | 1.000 | 1.000 | Anteriores a 2019 |

Fuente: COCIR + IIE-UNR (ciclo 2018-2024), MeLi+UdeSA (2024-2026), Zonaprop ZP Index.

### 6.6 Cobertura

| Métrica | Viejas (117) | Nuevas (322) |
|---------|-------------|--------------|
| Propiedades a ≤300m de un ancla | 3.815 (46%) | **8.014 (96%)** |
| Cobertura de la ciudad | 47% | ~100% (urbano continuo) |

### 6.7 Diferenciación Ct por Segmento (Nuevo vs Usado)

Basado en datos de Bassini (COCIR, Enero 2026):
- **Usado**: apreció 10-15% más que el índice general → factor 1.12 sobre (Ct-1.0)
- **Nuevo/Estrenar**: mercado competitivo, apreció 5% menos → factor 0.95 sobre (Ct-1.0)

Impacto práctico: como el 99.9% de las propiedades en caché son usadas, la mediana de las anclas cambia solo ~1% vs la tabla única. El mayor impacto se verá al valuar propiedades nuevas individualmente.

### 6.8 Pipeline de Regeneración de Anclas (TAREA-038)

A partir de TAREA-038, las anclas se gestionan mediante un pipeline configurable:

**Arquitectura:**
```
config/anclas_config.json  (parámetros + active_anchor_file + cache_version)
         │
         ▼
scripts/generar_anclas_grid.py  (lee config, output timestamped)
         │
         ▼
data/anclas_v7_AAAAMMDD_HHMMSS.json  (cada generación)
         │
         ▼ (activación desde Admin UI)
config/anclas_config.json → active_anchor_file actualizado + cache_version bump
         │
         ▼
Runtime (motor_vpp_core.py, location_engine.py, valuacion_cache.py, valu.py)
         lee active_anchor_file + cache_version desde config
```

**Configuración centralizada** (`config/anclas_config.json`):
- **generator**: grid_size_m, min_props_per_cell, ct_factors, city_center, noise_tokens
- **zones**: centroides y radios de zonas comerciales (martin, pellegrini, puerto_norte, etc.)
- **runtime**: active_anchor_file, cache_version, cache_ttl_minutes

**Script Generador** (`scripts/generar_anclas_grid.py`):
1. Lee `config/anclas_config.json` (parámetros, zona_centroides)
2. CLI overrides: `--grid-size`, `--min-props`, `--output`
3. Output: `data/anclas_v7_AAAAMMDD_HHMMSS.json` (timestamped, no sobreescribe)
4. Reporta cobertura, distribución, top 10 cambios

**Activación desde Admin UI (valu.py):**
1. Pestaña "Archivos": lista todos los archivos `anclas_v7_*.json`, indica activo, botón "Activar"
2. Pestaña "Generar": parámetros + botón "Generar" → preview → "Activar"
3. Pestaña "Editor Manual": tabla data_editor para ajustar USD/m² del archivo activo
4. Pestaña "Config": editor inline de `config/anclas_config.json`

**Al activar nuevas anclas:**
1. `set_active_anchor_file()` escribe el path relativo en config
2. `bump_cache_version()` incrementa cache_version (invalida valuaciones previas)
3. `cargar_anclas_cached(force_reload=True)` recarga en memoria

**Runtime dinámico:**
- `active_anchor_file` se lee desde config en cada carga de anclas
- `cache_version` se lee desde config dinámicamente (no es constante de módulo)
- `load_anclas_config()` con caché de 60s + `force_reload`

---

## 17. Depreciación en Rosario: Evidencia ML (TAREA-073 + TAREA-076)

### Decisión

La depreciación por antigüedad NO existe como factor de mercado independiente en Rosario.
**NO se muestra como referencia en la UI de Valuación Manual** (TAREA-076).
La fórmula genérica `-0.6%/año × antigüedad` (standard contable internacional) no tiene sustento empírico en el mercado local.

### Evidencia del Análisis ML

**XGBoost (R²=0.839) sobre 8,368 ventas:**

| Feature | Importancia | SHAP mean |
|---------|-------------|-----------|
| lat | 44.3% | $317 |
| lon | 36.1% | $369 |
| m² | 15.5% | $136 |
| dormitorios | 2.8% | $43 |
| Etiquetas de zona | <0.5% | <$7 |

`antigüedad` no fue un feature relevante — ni siquiera se incluyó en el modelo final porque no aportaba poder predictivo.

**RandomForest por macrozona (scripts/explorar_depreciacion_rf.py):**

| Macrozona | n | R² | Importancia edad | Pendiente/año | Clase |
|-----------|---|----|------------------|---------------|-------|
| centro_premium | 3,950 | 0.796 | 8.4% | **-0.18%** | Baja (≈cero) |
| macrocentro | 819 | 0.933 | 6.3% | **-0.28%** | Media-baja |
| norte | 1,554 | 0.903 | 5.7% | **+0.06%** | Baja (aprecia) |
| oeste | 112 | 0.948 | 13.5% | **-0.85%** | Alta (muestra chica) |

**Grid RF por celda (40×40, controlando ubicación exacta):**
- Evaluando el mismo RF en coordenadas fijas: Mabel +0.2% en 55 años (2025→1970)
- Muchas celdas muestran pendiente **positiva** (propiedades más viejas valen más en ciertas ubicaciones premium)

### Conclusión

La edad aparenta correlacionar con precio porque las propiedades viejas están en zonas más céntricas (edificios años 50-70 en Centro), mientras que las nuevas están en la periferia en expansión (norte, oeste). Al controlar por ubicación exacta (misma cuadra), el efecto edad desaparece. Es **confounding effect**, no causalidad.

### Diferencia clave: factores de propiedad vs factores de mercado

| Factor | Tipo | ¿Existe en Rosario? | ¿Se muestra en UI? |
|--------|------|---------------------|-------------------|
| **Estado** (a_estrenar/excelente/regular) | Observable de propiedad | Sí, la condición física es real | ✅ Referencia |
| **Calidad** (premium/alta/media/baja) | Observable de propiedad | Sí, la calidad constructiva es real | ✅ Referencia |
| **Amenities** (pileta, SUM, seguridad) | Observable de propiedad | Sí, son características listadas | ✅ Referencia |
| **NLP** (cocina silestone, preinst AA) | Observable de propiedad | Sí, son terminaciones específicas | ✅ Referencia |
| **Depreciación por edad** | Factor de mercado | **NO** — confounding effect con ubicación | ❌ Eliminado |

### Referencias

- `reports/ml_insights.md` — Reporte completo de ML (XGBoost, DBSCAN, Hedonic)
- `reports/ml_xgb_importance.csv` — Feature importance XGBoost
- `reports/rf_depreciacion_macrozonas.csv` — RF por macrozona
- `reports/rf_depreciacion_grid.csv` — Grid RF 40×40 (1,600 celdas)
- `scripts/explorar_depreciacion_rf.py` — Script completo de análisis RF
- `parsers/mercado_inmobiliario.py:2048` — `calcular_factores_display()` sin depreciación
- TAREA-073: Eliminación de factores hedónicos del motor automático
- TAREA-076: Eliminación de depreciación del display de subfactores

---

## 18. Retro Slider — Filtro Temporal de Comparables (TAREA-086)

### Propósito
Permitir al usuario restringir los comparables a una ventana temporal hacia atrás desde la fecha de referencia, para evitar que propiedades muy antiguas distorsionen la valuación.

### Algoritmo

```
retro_meses = slider value (default 36, rango 12-60)
retro_dias = retro_meses (0 si retro está inactivo)

ventana_dias = retro_dias * 30  si retro_dias > 0
             = get_natural_window_dias() (=180)  si retro_dias == 0

fecha_limite = fecha_ref - ventana_dias

Para cada comparable:
    if comparable.date_created < fecha_limite:
        EXCLUIR
    else:
        INCLUIR
```

### Default del slider
- **36 meses** cuando el usuario activa Retro por primera vez en la sesión
- El `st.slider` usa `value=36` explícito para que coincida con el valor que recibe el motor
- Tras togglear Retro off/on, el slider se reinicia a 36 (sesión _state se limpia)

### Bypass de cache (`valu.py:611-618` y `motor_vpp_core.py:1382-1388`)
El cache se usa solo si coinciden AMBAS condiciones:
1. `fecha_ref` del cache == `fecha_ref` actual (misma fecha de referencia)
2. `retro_dias` del cache == `retro_dias` actual (mismo slider)

Si alguna difiere, se fuerza recálculo completo.

### Validación con Francia 250b (Puerto Norte)
| retro_dias | Ventana | Condominios del Alto (2025-06-19) | Resultado |
|-----------|---------|-----------------------------------|-----------|
| 0 | 180d (natural) | 373d > 180d → EXCLUIDO | 0 comps |
| 12 | 360d | 373d > 360d → EXCLUIDO | 0 comps |
| 36 | 1080d | 373d < 1080d → INCLUIDO | 1 comp |

### Archivos clave
- `valu.py:352-353` — `st.slider("Meses atrás", 12, 60, value=36, key=...)` con `on_change=_on_retro_slider_change`
- `valu.py:345-351` — `_on_retro_slider_change`: actualiza `retro_meses`, `forzar_recalculo`, `preview_mode`
- `valu.py:319-334` — Botón Retro: al activar setea `retro_meses = sv` (default 36)
- `valu.py:611-618` — Bypass de cache: verifica `fecha_ref` y `retro_dias`
- `motor_vpp_core.py:1382-1388` — Verifica `cached_retro != retro_dias` para recálculo
- `mercado_inmobiliario.py:1043,1114,1167` — `window_dias_usado = retro_dias * 30 if retro_dias > 0 else get_natural_window_dias()`
- `tests/test_regression.py` — Tests `test_retro_dias_*` y `test_retro_bypass_*` (INAMOVIBLES)


**Generado por**: OpenCode
**Fecha**: 2026-06-27
