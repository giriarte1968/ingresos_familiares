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

## 3. Fórmula Unificada de Factores (v11.2)
 
Lógica de base: El valor de mercado es sensible al tiempo. Para comparativas de regresión y tasaciones actuales, el parámetro `fecha_ref` debe coincidir con el mes de ejecución para evitar desviaciones por inflación o tendencia de mercado.
 
La fórmula final del valor de lista unifica factores físicos, NLP (análisis de descripción) y antigüedad:
 
$$Factor_{raw} = (1 + SumaCruda_{clamped} + DeltaAnti_{efectiva}) \times (1 + NLPCapped)$$
$$Factor_{total} = \text{clamp}(Factor_{raw}, 0.70, 1.35)$$
 
Donde:
- **SumaCruda**: Suma de deltas de estado, calidad, vista, piso, balcón, etc. Se acota al rango $[-0.40, +0.40]$ para evitar premios o castigos estructurales excesivos.
- **NLPCapped**: Ajuste por palabras clave en la descripción (limitado al 15%).
- **DeltaAntiEfectivo**: Depreciación por antigüedad (0.6% anual). En Venta (base P33), se aplica una Atenuación Dinámica No Lineal para evitar la doble penalización en propiedades antiguas (ver sección 3.x).

### Control de Volatilidad (Guardrails V13.0)

Se eliminó la raíz cuadrada (`sqrt`) que anteriormente comprimía el factor, sustituyéndola por clamps explícitos. Esto proporciona un control lineal y predecible:
- **SumaCruda Clamped**: Evita que la acumulación de muchos factores positivos o negativos distorsione la base.
- **Factor Total Clamped**: Garantiza que el multiplicador final esté estrictamente entre $0.70$ (-30%) y $1.35$ (+35%).



## 3.x. Atenuación Dinámica de Antigüedad (Venta P33)

Para evitar la "doble penalización" en propiedades antiguas valuadas con la base conservadora (P33), se aplica una función de atenuación por tramos (piecewise) al $\Delta \text{Antigüedad}$.

### Justificación
El percentil P33 ya actúa como un proxy de stock usado/antiguo. Aplicar un castigo lineal severo adicional sobre una base ya baja destruye el valor de mercado de propiedades premium antiguas (ej. pisos altos céntricos de los 70s).

### Lógica Matemática
Si $\text{operación} = \text{'venta'}$ y $\text{percentil} = \text{'P33'}$ y $\Delta \text{anti} < 0$:

1. **Castigo Normal ($\Delta \text{anti} \ge \text{UMBRAL\_PENALIZACION}$):**
   $$\Delta \text{efectivo} = \Delta \text{anti} \times \text{ATENUACION\_BASE}$$
2. **Castigo Severo ($\Delta \text{anti} < \text{UMBRAL\_PENALIZACION}$):**
   $$\text{Exceso} = \Delta \text{anti} - \text{UMBRAL\_PENALIZACION}$$
   $$\Delta \text{efectivo} = (\text{UMBRAL\_PENALIZACION} \times \text{ATENUACION\_BASE}) + (\text{Exceso} \times \text{FACTOR\_EXCESO})$$

### Lógica Matemática
Si $\text{operación} = \text{'venta'}$ y $\text{percentil} = \text{'P33'}$ y $\Delta \text{anti} < 0$:

1. **Castigo Normal ($\Delta \text{anti} \ge \text{UMBRAL\_PENALIZACION}$):**
   $$\Delta \text{efectivo} = \Delta \text{anti} \times \text{ATENUACION\_BASE}$$
2. **Castigo Severo ($\Delta \text{anti} < \text{UMBRAL\_PENALIZACION}$):**
   $$\text{Exceso} = \Delta \text{anti} - \text{UMBRAL\_PENALIZACION}$$
   $$\Delta \text{efectivo} = (\text{UMBRAL\_PENALIZACION} \times \text{ATENUACION\_BASE}) + (\text{Exceso} \times \text{FACTOR\_EXCESO})$$

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

## Leyes del Motor VPP - Calibración Rosario 2026

### 1. Fórmula de Venta
La valuación de venta para departamentos/PH usa:

```
valor_venta = m2_equiv × m2_base_venta × (1 + suma_cruda_clamped + delta_anti_efectivo) × (1 + ajuste_nlp)
```

Aclaraciones:
- `m2_base_venta` proviene del cluster geolocalizado v2.
- `venta` usa **P33** como base conservadora.
- `alquiler` usa **P50/mediana**.
- `suma_cruda_clamped` es la suma de ajustes de atributos físicos/comerciales, con clamp.
- `delta_anti_efectivo` se aplica de forma lineal dentro del bloque estructural.
- `ajuste_nlp` se aplica como multiplicador externo.

### 2. Clamp de Suma Cruda
- `SUMA_CRUDA_MIN = -0.40`
- `SUMA_CRUDA_MAX = +0.40`

Evita explosión por acumulación de atributos positivos y negativos.

### 3. NLP cap por tipología
- Propiedades de **1 dormitorio**: NLP máximo = **+3%**
- Propiedades de **2 o más dormitorios**: NLP máximo = **+5%**

En Rosario, la descripción comercial no debería mover más de 3% en unidades chicas. En unidades mayores, el mercado tolera hasta 5% de premio por percepción/comercialización.

### 4. Atenuación dinámica de antigüedad
Se activa solo si `delta_anti_raw < -0.18`:
- `UMBRAL_PENALIZACION_SEVERA = -0.18`
- `FACTOR_ATENUACION = 0.35`

Fórmula exacta:
- Si `delta_anti_raw >= -0.18`, entonces: `delta_anti_efectivo = delta_anti_raw`
- Si `delta_anti_raw < -0.18`, entonces:
  - `exceso = delta_anti_raw - (-0.18)`
  - `delta_anti_efectivo = -0.18 + (exceso × 0.35)`

**Ejemplo con P1200:**
- 49 años → delta raw ≈ -0.294
- exceso ≈ -0.114
- delta efectivo ≈ -0.220
- Propósito: evitar sobrecastigar propiedades antiguas cuando la base P33 ya es conservadora.

### 5. Ajustes finos aplicados
- Funcional (lavadero/placares): reducida de 0.02 → 0.015
- Balcón corrido: reducido de 0.04 → 0.02

Fueron calibraciones para bajar Mabel a rango realista sin romper Ayacucho ni Vera.

### 6. Exclusión de factor_pasillo
- `factor_pasillo` NO forma parte de la fórmula general de departamentos/PH.
- Si existiera una lógica futura para casas/PH especiales, debe vivir en un motor separado.

## 7. Barreras Geográficas (Rosario)

### Tipología de Barreras
| Tipo | Ejemplos | Comportamiento | Peso en IDW |
| :--- | :--- | :--- | :--- |
| **DURA** | Ferrocarril FC Mitre, Circunvalación | Exclusión total | weight *= 0.20 (80% penalty) |
| **BLANDA** | Av. Pellegrini, Av. 27 de Febrero, Av. Oroño, Av. Francia | Fricción (no exclusión) | weight *= 0.90 (10% penalty) |


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

## Leyes del Motor VPP - Calibración Rosario 2026

### 1. Fórmula de Venta
La valuación de venta para departamentos/PH usa:

```
valor_venta = m2_equiv × m2_base_venta × (1 + suma_cruda_clamped + delta_anti_efectivo) × (1 + ajuste_nlp)
```

Aclaraciones:
- `m2_base_venta` proviene del cluster geolocalizado v2.
- `venta` usa **P33** como base conservadora.
- `alquiler` usa **P50/mediana**.
- `suma_cruda_clamped` es la suma de ajustes de atributos físicos/comerciales, con clamp.
- `delta_anti_efectivo` se aplica de forma lineal dentro del bloque estructural.
- `ajuste_nlp` se aplica como multiplicador externo.

### 2. Clamp de Suma Cruda
- `SUMA_CRUDA_MIN = -0.40`
- `SUMA_CRUDA_MAX = +0.40`

Evita explosión por acumulación de atributos positivos y negativos.

### 3. NLP cap por tipología
- Propiedades de **1 dormitorio**: NLP máximo = **+3%**
- Propiedades de **2 o más dormitorios**: NLP máximo = **+5%**

En Rosario, la descripción comercial no debería mover más de 3% en unidades chicas. En unidades mayores, el mercado tolera hasta 5% de premio por percepción/comercialización.

### 4. Atenuación dinámica de antigüedad
Se activa solo si `delta_anti_raw < -0.18`:
- `UMBRAL_PENALIZACION_SEVERA = -0.18`
- `FACTOR_ATENUACION = 0.35`

Fórmula exacta:
- Si `delta_anti_raw >= -0.18`, entonces: `delta_anti_efectivo = delta_anti_raw`
- Si `delta_anti_raw < -0.18`, entonces:
  - `exceso = delta_anti_raw - (-0.18)`
  - `delta_anti_efectivo = -0.18 + (exceso × 0.35)`

**Ejemplo con P1200:**
- 49 años → delta raw ≈ -0.294
- exceso ≈ -0.114
- delta efectivo ≈ -0.220
- Propósito: evitar sobrecastigar propiedades antiguas cuando la base P33 ya es conservadora.

### 5. Ajustes finos aplicados
- Funcional (lavadero/placares): reducida de 0.02 → 0.015
- Balcón corrido: reducido de 0.04 → 0.02

Fueron calibraciones para bajar Mabel a rango realista sin romper Ayacucho ni Vera.

### 6. Exclusión de factor_pasillo
- `factor_pasillo` NO forma parte de la fórmula general de departamentos/PH.
- Si existiera una lógica futura para casas/PH especiales, debe vivir en un motor separado.

## 7. Barreras Geográficas (Rosario)

### Tipología de Barreras
| Tipo | Ejemplos | Comportamiento | Peso en IDW |
| :--- | :--- | :--- | :--- |
| **DURA** | Ferrocarril FC Mitre, Circunvalación | Exclusión total | weight *= 0.20 (80% penalty) |
| **BLANDA** | Av. Pellegrini, Av. 27 de Febrero, Av. Oroño, Av. Francia | Fricción (no exclusión) | weight *= 0.90 (10% penalty) |

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

## 12. Valores de Referencia (Fase 2 — Age-Aware)

Estos son los valores definitivos con filtro de edad activo.
Reemplazan los valores de calibración previos.

| Propiedad   | Año  | Pool total | n_age | %ile usado | Valor ref  |
|-------------|------|-----------|-------|------------|------------|
| Mabel       | 1998 | 81        | 27    | P50        | $72,241    |
| Ayacucho    | 2002 | 43        | 16    | P45        | $52,047    |
| Vera Mujica | 2009 | 27        | 8     | P40        | $52,062    |
| P1200       | 1977 | 36        | 12    | P45        | $137,888   |

**Regla de percentil dinámico:**
- Si hay filtro de edad (age_filter_applied):
  - n_age ≥ 20 → P50
  - 10 ≤ n_age < 20 → P45
  - 8 ≤ n_age < 10 → P40
- Si NO hay filtro de edad → P33 (conservador histórico)

---

**Generado por**: Antigravity (IA de Desarrollo)
**Fecha**: 2026-05-12
