# 🏠 AVM ROSARIO — MEMORIA DEL PROYECTO
## Sistema de Valuación Automática de Propiedades
**Última actualización:** Abril 2026
**Versión del modelo:** v7

> ⚠️ INSTRUCCIÓN PARA CUALQUIER IA QUE LEA ESTO:
> Este archivo es la fuente de verdad del proyecto.
> Antes de modificar CUALQUIER código, leer este archivo completo.
> Si un cambio viola una "Regla de Oro", NO implementarlo sin
> aprobación explícita del usuario (Gustavo).
>
> ### 📍 RUTA DEL PROYECTO (CRÍTICO)
> - **Directorio de trabajo:** `C:\Users\Gustavo\ingresos_familiares_st`
> - **NUNCA usar:** `C:\Users\Gustavo\opencode` (esta carpeta es diferente)
> - **UI entrada:** `streamlit run valu.py` (desde el directorio de trabajo)
> - **Motor de valuación:** `parsers/mercado_inmobiliario.py` → función `valuar_propiedad_v7()`
> - **Tests:** `tests/test_regression.py` (ejecutar con `pytest`)

---

## 1. MISIÓN DEL SISTEMA

Tasar propiedades residenciales en la ciudad de Rosario, Argentina.
El modelo es Data-Driven: los precios emergen del mercado real
(scraping de portales), NO de anclas fijas definidas manualmente.

**Stack:** Python + Streamlit + scikit-learn + shapely + geopandas

**Archivos críticos:**
- `parsers/mercado_inmobiliario.py` → Motor principal de valuación (`valuar_propiedad_v7`)
- `parsers/location_engine.py` → Clustering geoespacial (DBSCAN + IDW)
- `parsers/motor_vpp_core.py` → Scraping y utilidades (`get_binance_usdt_ars`)
- `parsers/nlp_inmobiliario.py` → Análisis de descripción libre
- `barreras_rosario.json` → 745 LineStrings de barreras (OSM)
- `cache_scraping.json` → ~10.000 propiedades scrapeadas
- `tests/test_regression.py` → Tests de regresión (rangos INAMOVIBLES)

---

## 2. REGLAS DE ORO
### ⛔ NUNCA violar sin aprobación explícita de Gustavo

**RO-01:** NO filtrar comparables por string de zona. Solo usar distancia geográfica (lat/lon). 
*RAZÓN: "Martin" vs "martin" vs "Barrio Martín" → bugs eternos.*

**RO-02:** NO actualizar el baseline de `test_regression.py` sin aprobación humana explícita. 
*RAZÓN: El test valida correctitud de negocio, no consistencia.*

**RO-03:** NO aplicar depreciación por antigüedad cuando la base viene de Ventana 3 (P33). 
*RAZÓN: La estratificación P33 ya incorpora implícitamente la edad.*

**RO-04:** NLP entra DENTRO del sqrt, no como multiplicador externo. 
*RAZÓN: Evita doble amortiguación.*

**RO-05:** En alquiler, usar MEDIANA COMPLETA (no P33). 
*RAZÓN: El inquilino no descuenta antigüedad igual que el comprador.*

**RO-06:** Excluir propiedades amuebladas del cluster de alquiler. 
*Keywords: ['amoblado', 'amueblado', 'equipado', 'con muebles']*

**RO-07:** `lambda_val = 0.012` en IDW. `MAX_PESO_NODO = 0.60`. NUNCA bajar lambda (genera dominancia de nodo único cercano).

**RO-08:** NO usar "ancla física" como componente del precio base. El sistema es 100% Data-Driven desde v7.

**RO-09:** MAD solo aplicar si N >= 8. Con N < 8: usar todos los comparables sin filtrar.

**RO-12:** La UI SIEMPRE llama a `valuar_propiedad_v7()`. Existe una función `_verificar_imports()` en `app.py` que audita el código en cada arranque para prevenir el uso de lógica obsoleta.

**RO-13:** Los TTLs del caché de Streamlit se gestionan por entorno (`APP_ENV`). En `development`, los TTLs son 0 (frescura total). En `production`, se permiten TTLs largos (10hs a 7 días).

**RO-14:** (Espacio reservado)

**RO-15:** La fórmula de `factor_total` tiene `delta_anti` DENTRO del `sqrt`. NUNCA mover `delta_anti` fuera del `sqrt` sin aprobación humana. Razón: BUG-05 estableció que todos los factores estructurales (estado, calidad, antigüedad, NLP) se amortiguan juntos.

**RO-16:** Jerarquía de Verdad: Si dos documentos se contradicen, `MEMORIA_PROYECTO.md` siempre tiene la prioridad absoluta. `ALGORITMOS.md` y otros documentos son secundarios. Si hay contradicción, reportar al usuario, no decidir solo.

---

## 3. ARQUITECTURA DE LA FÓRMULA DE VENTA
`valor_lista = m2_equiv × m2_base × factor_total`

donde:
- `m2_equiv = m2_cubiertos + (m2_semi × 0.30) + (m2_desc × 0.10)`
- `m2_base = mediana del cluster geoespacial (ver Sección 5)`
- `factor_total = sqrt( (1 + suma_cruda + delta_anti) × (1 + nlp_capped) )`
- `suma_cruda = delta_estado + delta_calidad + delta_vista + delta_piso + delta_ventilacion + delta_ubicacion`

**delta_anti (Tramos v12.0):**
- Si `ventana_usada == 3` → `delta_anti = 0.0` (implícito en P33)
- Si `ventana_usada == 1 o 2` → Tramos:
  - 0-5 años: 0.0%/año
  - 5-10 años: 0.7%/año
  - 10-20 años: 0.9%/año
  - 20-30 años: 1.1%/año (Tramo Mabel)
  - 30-50 años: 0.6%/año
  - 50+ años: 0.3%/año
  - **CAP:** max castigo 40% (Factor min 0.60)
- `nlp_capped = min(ajuste_nlp, 0.15)`

**GAP venta:**
- Antigüedad > 20 años → `gap = 0.90`
- Antigüedad <= 20 años → `gap = 0.92`
- `valor_cierre = valor_lista × gap`

### Tabla de deltas estructurales
- **ESTADO:** excelente → +0.15, muy_bueno → +0.10, bueno → 0.00, regular → -0.15, malo → -0.30
- **CALIDAD EDIFICIO:** premium → +0.20, alta → +0.10, media → 0.00, baja → -0.15
- **VENTILACIÓN:** cruzada → +0.10, simple → 0.00
- **PISO:** planta_baja → -0.05, piso 1-3 → 0.00, piso 4+ → +0.05, piso 8+ → +0.10

---

## 4. ARQUITECTURA DE LA FÓRMULA DE ALQUILER
`alquiler_mensual_ars = m2_equiv_alq × m2_base_alq × factores_alq × gap_alq`

- `m2_equiv_alq = m2_cubiertos + (m2_semi × 0.30) + (m2_desc × 0.10)` ← INCLUYE semicubiertos al 30%
- `m2_base_alq`: 
  - **PRIMARIO:** mediana completa del cluster de alquiler (progresión geo)
  - **FALLBACK:** `(m2_base_venta_zona × 0.0045) × usdt_ars` (usa mediana COMPLETA de venta, NO P33)
- `factores_alq = sqrt(1 + suma_cruda_alq)`
- `suma_cruda_alq = (delta_estado × 0.50) + (delta_calidad × 0.50) + (delta_nlp × 0.70) + delta_ventilacion + delta_piso`
- `delta_anti` en alquiler = 0.0 SIEMPRE.
- **GAP alquiler** = 0.96 (mercado más rígido que venta)
- **ROI** = (alquiler_mensual × 12) / (valor_cierre_usd × usdt_ars)

---

## 5. LÓGICA DEL CLUSTER GEOESPACIAL

### 5.1 Obtención del precio base (venta)
**PROGRESIÓN DE RADIOS:** [300m, 500m, 800m, 1.200m, 2.000m]
**N_MIN = 8** comparables limpios para usar el radio.

Para cada radio:
1. Filtrar por: tipo (casa/dpto), dormitorios, operacion='venta'
2. Filtrar por distancia <= radio (lat/lon, NO string de zona)
3. Excluir si cruza barrera dura (`check_barrier_crossing`)
4. Limpiar outliers:
   - Filtro absoluto PRIMERO: [400, 5000] USD/m²
   - IQR después: [mediana×0.60, mediana×1.60]
   - MAD solo si N >= 8
5. Si N_limpio >= 8 → calcular mediana → PARAR

**VENTANAS POR ANTIGÜEDAD:**
- Ventana 1: ±10 años del año de construcción
- Ventana 2: ±20 años
- Ventana 3: sin filtro de edad → usar P33 del cluster (proxy stock antiguo)

### 5.2 Obtención del precio base (alquiler)
**PROGRESIÓN:** [300m, 500m, 800m, 1.200m, 2.000m]
**N_MIN = 5** (mercado de alquiler tiene menos datos)

Filtros adicionales para alquiler:
- Excluir amueblados (ver RO-06)
- Solo moneda ARS (no USD)
- Solo publicaciones <= 90 días
- Usar MEDIANA COMPLETA (no P33)

### 5.3 IDW (Inverse Distance Weighting)
```python
lambda_val = 0.012       # decaimiento exponencial
MAX_PESO_NODO = 0.60     # ningún nodo > 60% del peso total
MIN_NODOS = 5            # mínimo para usar IDW

weight = min(exp(-lambda_val × d_metros), MAX_PESO_NODO)
```

---

## 6. BARRERAS GEOGRÁFICAS

**Archivo:** `barreras_rosario.json`  
**Formato:** GeoJSON FeatureCollection, 745 features (263 hard + 482 soft)

### Tipos de barreras (implementación 2026-05)

| Tipo | barrier_type | Efecto Cluster | peso IDW |
|------|-------------|----------------|----------|
| Duras | `hard` | **Excluir** comparable | 0.20 |
| Blandas | `soft` | **Mantener** comparable | 0.90 |

### Barreras implementadas

- **Duras**: Ferrocarril FC Mitre (peso = 0.20 → exclusión efectiva)
- **Blandas**: Av. Pellegrini, Av. 27 de Febrero, Av. Oroño, Av. Francia (peso = 0.90)
- Bv. 27 de Febrero (tramos específicos)

### Barreras blandas (peso × β)

| Arteria | Factor β |
|---------|----------|
| Bv. Oroño | 0.85 |
| Av. Pellegrini | 0.90 |
| Bv. 27 de Febrero (general) | 0.80 |

### Atractores (decaimiento e^(-λd))

| Punto de interés | λ | Radio efectivo |
|------------------|---|-----------------|
| Parque Independencia | 0.008 | ~400m |
| Puerto Norte | 0.006 | ~500m |
| Frente Bv. Oroño | 0.015 | ~200m |

### Caso crítico: Ayacucho 1800

- **Ubicación:** al NORTE de Cochabamba
- El cluster NO debe traer comparables al SUR del Bv. 27
- Radio 300m → no hay problema naturalmente
- Radio > 500m → las barreras son OBLIGATORIAS

---

## 7. VALORES DE REFERENCIA (GROUND TRUTH)

⛔ INAMOVIBLES — Validados con precio real de mercado

### MABEL (test ID: 'mabel')

- **Zona:** Barrio Martín
- **Coordenadas:** -32.9541, -60.6316
- **m2_cubiertos:** 41.0 | **m2_semicubiertos:** 7.5
- **Año construcción:** 2000 (26 años)
- **Estado:** muy bueno | **Calidad:** media
- **Ventilación:** cruzada | **Piso:** 2
- **Descripción:** "luminoso, con aire acondicionado"

| Métrica | Rango |
|--------|-------|
| valor_lista | $68,000 - $76,000 USD |
| valor_cierre | $62,000 - $70,000 USD |
| alquiler_ars | $380,000 - $460,000 ARS |
| roi_anual | 4.0% - 6.0% |

### AYACUCHO (test ID: 'ayacucho')

- **Zona:** Sexta Pellegrini
- **Coordenadas:** -32.9603, -60.6299
- **m2_cubiertos:** 27.0
- **Año construcción:** 2002 (24 años)
- **Estado:** excelente | **Calidad:** media
- **Dormitorios:** 1

| Métrica | Rango |
|--------|-------|
| valor_lista | $42,000 - $52,000 USD |
| valor_cierre | $38,000 - $48,000 USD |
| alquiler_ars | $270,000 - $350,000 ARS |
| roi_anual | 4.5% - 6.5% |

---

## 8. HISTORIAL DE DECISIONES CLAVE

Por qué se tomaron — para no revertirlas accidentalmente

### DEC-01: Eliminar ancla física del cálculo base

- **Fecha:** Abril 2026
- **Razón:** El sistema es Data-Driven. La ancla inflaba valores cuando el scraping tenía pocos datos.
- **Impacto:** `calcular_base_calibrada` ya NO pondera ancla.

### DEC-02: Filtrar por distancia geográfica, NO por string de zona

- **Fecha:** Abril 2026
- **Razón:** Strings inconsistentes en scraping causaban 0 comparables. "Martin" ≠ "martin" ≠ "Barrio Martín"
- **Impacto:** `obtener_mediana_cluster` usa lat/lon, ignora campo 'zona'.

### DEC-03: P33 en venta (Ventana 3) como proxy de antigüedad

- **Fecha:** Abril 2026
- **Razón:** 0% de los dptos en scraping tienen año de construcción. P33 correlaciona empíricamente con propiedades antiguas.
- **Impacto:** Cuando cae a Ventana 3, delta_anti = 0.0.

### DEC-04: Mediana completa en alquiler (no P33)

- **Fecha:** Abril 2026
- **Razón:** Inquilino valora ubicación+estado, no antigüedad.
- **Impacto:** `obtener_mediana_alquiler_geografica` usa np.median completo.

### DEC-05: lambda = 0.012 en IDW

- **Fecha:** Abril 2026
- **Razón:** Con lambda=0.005, un nodo a 28m tenía peso 0.87 → dominaba. Con lambda=0.012 el mismo nodo tiene peso 0.71.
- **Impacto:** `location_engine.py`, `calcular_precio_m2()`.

### DEC-06: NLP dentro del sqrt

- **Fecha:** Abril 2026
- **Razón:** NLP como multiplicador externo causaba doble amortiguación.
- **Impacto:** factor = sqrt((1+suma_cruda+delta_anti) × (1+nlp))

### DEC-07: MAD solo con N >= 8

- **Fecha:** Abril 2026
- **Razón:** Con N=4, MAD expulsaba los comparables más cercanos y los reemplazaba por lejanos. Peor que no filtrar.
- **Impacto:** `filtrar_mad()` tiene guard: `if len(pool) < 8: return pool`

---

## 9. BUGS CONOCIDOS Y RESUELTOS

Para no reintroducirlos

### BUG-01: ✅ RESUELTO — Nodo a 28m dominaba la valuación

- **Síntoma:** Mabel valía $90k+
- **Causa:** lambda=0.005 → peso 0.87 para nodo cercano
- **Fix:** lambda=0.012 + MAX_PESO_NODO=0.60

### BUG-02: ✅ RESUELTO — "0 propiedades" en cluster

- **Síntoma:** Sistema caía a ancla, ignoraba mercado
- **Causa:** Filtro zona case-sensitive ("Martin" ≠ "martin")
- **Fix:** Filtro por distancia, eliminar filtro por zona string

### BUG-03: ✅ RESUELTO — Doble depreciación en Ventana 3

- **Síntoma:** Propiedades antiguas valuadas muy bajas
- **Causa:** P33 ya era base baja + delta_anti aplicado encima
- **Fix:** ventana_usada==3 → delta_anti=0.0

### BUG-04: ✅ RESUELTO — Comparables del sur en Ayacucho

- **Síntoma:** Base de $439-$942/m² para zona de $1.400+
- **Causa:** Radio 1km sin barreras cruzaba Bv. 27
- **Fix:** Progresión 300m→... + barreras activas en `obtener_mediana_cluster`

### BUG-05: ✅ RESUELTO — NLP fuera del sqrt

- **Síntoma:** Factor inflado, valor lista ~$82k para Mabel
- **Causa:** valor = base × sqrt(factores) × 1.05 (NLP afuera)
- **Fix:** valor = base × sqrt(factores × (1+nlp))

### BUG-06: ✅ RESUELTO — ROI incorrecto en UI

- **Síntoma:** ROI 3.26% cuando debería ser ~5%
- **Causa:** Dividía alquiler anual por valor_lista×usdt incorrecto
- **Fix:** ROI = (alq_mensual×12) / (valor_cierre_usd × usdt_ars)

### BUG-07: ✅ RESUELTO — Amueblados contaminando cluster alquiler

- **Síntoma:** Propiedades amuebladas con ARS/m² distorsionado
- **Fix:** Excluir keywords ['amoblado','amueblado','equipado']

### BUG-08: ✅ RESUELTO — Barreras no conectadas a obtener_mediana_cluster

- **Síntoma:** check_barrier_crossing existía pero no se llamaba
- **Estado:** RESUELTO — Verificado en `parsers/mercado_inmobiliario.py:130`
- **Fix:** Llamada activa en el loop de candidatos

### BUG-09: ✅ RESUELTO — delta_anti aplicado en alquiler
- **Síntoma:** Alquileres de propiedades antiguas daban valores muy bajos (~$248k).
- **Causa:** Se aplicaba depreciación por edad, violando RO-05.
- **Fix:** Forzar factor antigüedad = 1.0 en el path de alquiler.

### BUG-10: ✅ RESUELTO — GAP alquiler 0.93 en lugar de 0.96

- **Síntoma:** El precio final de alquiler era un 3% menor al esperado.
- **Causa:** Constante GAP_ALQUILER seteada en 0.93.
- **Fix:** Cambiar a 0.96 según Sección 4 de la Memoria.

### BUG-11: ✅ RESUELTO — Fórmula factores alquiler incorrecta
- **Síntoma:** Los factores de estado/calidad se multiplicaban linealmente, inflando o deflactando de más.
- **Causa:** No se seguía la fórmula sqrt(1 + suma_cruda_alq).
- **Fix:** Implementar fórmula exacta de la Memoria y unificar el factor NLP dentro del sqrt.

### BUG-14: ✅ RESUELTO — Intento de mover delta_anti fuera del sqrt
- **Síntoma:** Mabel y Ayacucho quedaron fuera de rango (subvaluados $\approx 1\%$).
- **Causa:** Error de interpretación de ALGORITMOS.md moviendo la depreciación fuera de la raíz.
- **Fix:** Revertir inmediatamente. La fórmula correcta mantiene `delta_anti` dentro del `sqrt` para amortiguar el impacto, coherente con BUG-05.


---

## 10. TESTS DE REGRESIÓN

| test_id | Dirección | Operación | Rango esperado |
|--------|-----------|-----------|---------------|
| mabel | Mabel 1400 | valor_lista | $65,000 - $73,000 USD |
| mabel | Mabel 1400 | valor_cierre | $62,000 - $70,000 USD |
| mabel | Mabel 1400 | alquiler | $380,000 - $460,000 ARS |
| ayacucho | Ayacucho 1800 | valor_lista | $42,000 - $52,000 USD |
| ayacucho | Ayacucho 1800 | valor_cierre | $38,000 - $48,000 USD |
| ayacucho | Ayacucho 1800 | alquiler | $270,000 - $350,000 ARS |

### Contexto de ejecución

- **Cache de market data:** `cache/cache_scraping.json` (~10k propiedades)
- **Barreras:** `data/barreras_rosario.json` (745 features)
- **Fuente ground truth:** Zona Norte Rosario — Scraping Portal Inmobiliario

---

## 11. DEUDA TÉCNICA

Ordenada por prioridad — Issues pendientes de resolver

### ⚠️ ALTA PRIORIDAD

| # | Task | Estado | Notes |
|---|------|--------|-------|
| DT-01 | Enriquecer scraper: año/condición de ZonaProp y ML | ⏳ PENDIENTE | 0% dptos tienen año → todo cae a Ventana 3 |

### 📌 MEDIA PRIORIDAD

| # | Task | Estado | Notes |
|---|------|--------|-------|
| DT-02 | Integrar shapefile radios censales INDEC (Censo 2022) | ⏳ PENDIENTE | JOIN espacial → Prior antigüedad por radio |
| DT-03 | Calibrar curva de depreciación con escrituras | ⏳ PENDIENTE | Colegio Escribanos Santa Fe 2da |

### 🔽 BAJA PRIORIDAD

| # | Task | Estado | Notes |
|---|------|--------|-------|
| DT-04 | Prior bayesiano por barrio | ⏳ PENDIENTE | Requiere Redatam INDEC |
| DT-05 | Kriging anisotrópico | ⏳ PENDIENTE | Requiere N >> 50 por zona |

### Notas de implementación

- **DT-01:** Extraer `año_construccion` del HTML de ZonaProp/ML. Si no disponible, inferir por barrio (RADIO CENSAL).
- **DT-02:** Descargar shapefile INDEC, fazer JOIN espacial con cache, calcular mediana año por radio.
- **DT-03:** Solicitar datos al Colegio de Escribanos (Santa Fe 2da Circunscripción).

---

## 11. TESTS DE REGRESIÓN OBLIGATORIOS

⛔ LOS RANGOS DE ESTOS TESTS SON INAMOVIBLES — Si un "fix" los hace fallar → el fix está MAL, no el test

### Python: tests/test_regression.py

```python
# tests/test_regression.py
# ⛔ LOS RANGOS DE ESTOS TESTS SON INAMOVIBLES
# Si un "fix" los hace fallar → el fix está MAL, no el test

def test_mabel_venta():
    r = ejecutar_valuacion('mabel')
    assert 65_000 <= r['valor_lista'] <= 73_000
    assert 62_000 <= r['valor_cierre'] <= 70_000

def test_mabel_alquiler():
    r = ejecutar_valuacion('mabel')
    assert 380_000 <= r['alquiler_ars'] <= 460_000
    assert 4.0 <= r['cap_rate_anual'] <= 6.0, f"ROI {r['cap_rate_anual']}% fuera de rango"
    r = ejecutar_valuacion('ayacucho')
    assert 42_000 <= r['valor_lista'] <= 52_000

def test_ayacucho_alquiler():
    r = ejecutar_valuacion('ayacucho')
    assert 270_000 <= r['alquiler_ars'] <= 350_000
    assert 4.5 <= r['roi_anual'] <= 6.5

def test_barrera_bv27_ayacucho():
    """Ningún comparable de Ayacucho debe estar al sur del Bv.27"""
    from parsers.mercado_inmobiliario import obtener_mediana_cluster
    mediana, meta = obtener_mediana_cluster(
        lat=-32.9603, lon=-60.6299,
        tipo='departamento', dorms=1
    )
    assert mediana >= 1300, f"Base baja ({mediana}): comparables del sur filtrándose"

def test_nlp_dentro_sqrt():
    """El factor NLP debe estar dentro del sqrt"""
    r_sin = ejecutar_valuacion('mabel_sin_nlp')
    r_con = ejecutar_valuacion('mabel')
    ratio = r_con['valor_lista'] / r_sin['valor_lista']
    assert ratio < 1.05, f"NLP no está dentro del sqrt (ratio={ratio})"

def test_ventana3_sin_depreciacion():
    """Con Ventana 3, delta_anti debe ser 0.0"""
    from parsers.mercado_inmobiliario import calcular_factores
    f = calcular_factores({'anio_construccion': 1990}, ventana_usada=3)
    assert f['detalles']['anti'] == 0.0

def test_amueblados_excluidos():
    comparables = get_comparables_alquiler(lat=-32.9603, lon=-60.6299)
    for c in comparables:
        titulo = c.get('titulo', '').lower()
        assert 'amoblado' not in titulo
        assert 'amueblado' not in titulo
```

### Diferencias con el archivo actual

| Test | Archivo actual | Spec MEMORIA | Notas |
|------|-------------|------------|-----------|
| Mabel venta lista | $62k-$78k | $62k-$70k | **Spec es más estricto** |
| Mabel venta cierre | $57k-$73k | $57k-$65k | **Spec es más estricto** |
| test_barrera_bv27_ayacucho | ❌ No existe | ✅ REQUERIDO | FALTA |
| test_nlp_dentro_sqrt | ❌ No existe | ✅ REQUERIDO | FALTA |
| test_ventana3_sin_depreciacion | ❌ No existe | ✅ REQUERIDO | FALTA |
| test_amueblados_excluidos | ⚠️ Parcial (línea 278) | ✅ Completo | Mejora Needed |

### Acción requerida

**El archivo `tests/test_regression.py` debe actualizarse** para igualar los rangos de la MEMORIA (más estricto).

---

## 12. PROTOCOLO PARA LA IA PROGRAMADORA

Leer esto antes de cada sesión de código

### ANTES DE MODIFICAR CUALQUIER CÓDIGO:

1. Leer secciones 2 (Reglas de Oro) y 7 (Ground Truth)
2. Correr: `pytest tests/test_regression.py`
3. Si algún test falla ANTES de tu cambio $\rightarrow$ reportar, no arreglar

### DURANTE EL CAMBIO:

4. Un cambio a la vez. No refactorizar y corregir bug simultáneamente.
5. Si el cambio toca `calcular_factores`, `valuar_propiedad_v7`, o `calcular_precio_m2` $\rightarrow$ correr tests después de CADA modificación.

### DESPUÉS DEL CAMBIO:

6. Correr todos los tests
7. Si un test de rango falla $\rightarrow$ el cambio está MAL
   NO actualizar el rango. Revertir y analizar.
8. Actualizar sección 8 (Historial) si tomaste una decisión nueva.

### PROHIBIDO (EXCEPTO QUE APRUEBE GUSTAVO):

- ❌ Cambiar los rangos de `test_mabel_rango_real()` o `test_ayacucho_rango_real()`
- ❌ Reintroducir ancla física en el cálculo base
- ❌ Filtrar comparables por string de zona
- ❌ Aplicar `delta_anti` cuando `ventana_usada == 3`
- ❌ Poner NLP fuera del sqrt
- ❌ Subir `lambda_val` por encima de 0.012 sin aprobación
