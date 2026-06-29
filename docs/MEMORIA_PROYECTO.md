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

**RO-04:** NLP entra como multiplicador externo del producto de factores.
*RAZÓN: NLP ajusta percepción comercial sobre el valor base, no es un factor estructural.*

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

**RO-15:** (OBSOLETO por TAREA-071) La fórmula es ahora multiplicativa pura: `factor_total = factor_estado × factor_calidad × factor_anti`. No hay sqrt ni suma_cruda.

**RO-16:** Jerarquía de Verdad: Si dos documentos se contradicen, `MEMORIA_PROYECTO.md` siempre tiene la prioridad absoluta. `ALGORITMOS.md` y otros documentos son secundarios. Si hay contradicción, reportar al usuario, no decidir solo.

**RO-17 (RETRO SLIDER — DEFAULT 36):** Cuando el usuario activa Retro, el slider default es **36 meses**. El valor `retro_meses` que recibe el motor SIEMPRE debe coincidir con el valor mostrado por el slider. Cualquier cambio en este default debe ser aprobado por el usuario. Ver tests `test_retro_dias_36_incluye_comparable`, `test_retro_dias_12_excluye_comparable`.

**RO-18 (RETRO SLIDER — FILTRO DE FECHA):** El Retro slider restringe los comparables por fecha: `ventana = retro_meses × 30 días`. Un comparable con `date_created` anterior a `fecha_ref - ventana` es EXCLUIDO. Con `retro=12` (ventana=360d), el comparable Condominios del Alto (2025-06-19, 373d antes del 2026-06-27) NO debe aparecer. Con `retro=36` (ventana=1080d), SÍ debe aparecer. Ver tests `test_retro_dias_36_incluye_comparable`, `test_retro_dias_12_excluye_comparable`.

**RO-19 (RETRO SLIDER — BYPASS DE CACHE):** El bypass en `valu.py:611-618` solo debe usar el resultado cacheado si TANTO `fecha_ref` como `retro_dias` coinciden con los valores actuales. Si `retro_dias` del cache difiere del slider actual, el bypass debe rechazar el cache y forzar recálculo. Ver tests `test_retro_bypass_respeta_cambio_dias`, `test_retro_bypass_valu_py_coherencia`.

**RO-20 (RETRO SLIDER — TESTS INAMOVIBLES):** Los tests `test_retro_dias_*` y `test_retro_bypass_*` en `tests/test_regression.py` son INAMOVIBLES. Cualquier cambio en el código que los haga fallar debe ser aprobado por el usuario antes de modificarlos. No alterar estos tests sin consulta explícita.

**RO-CACHE-PREVIEW-01 (commit=False PERSISTE A CACHE):** `persistir_valuacion(commit=False)` debe SIEMPRE escribir a cache en disco (con `_cache.preview=True`). Antes de esta regla, `commit=False` no guardaba nada — el preview de Flex/Retro se perdía en el siguiente rerun. Ver test `test_preview_cache_persiste_en_disco`.

**RO-CACHE-PREVIEW-02 (commit=False NO ACTUALIZA _ultima_valuacion):** El flag `commit=False` solo afecta persistencia a cache. NUNCA debe actualizar `_ultima_valuacion` en `propiedades.json`. La propiedad sigue apareciendo como Pendiente en Portfolio. Ver test `test_preview_cache_no_afecta_ultima_valuacion`.

**RO-CACHE-PREVIEW-03 (PENDIENTE PRESERVA PREVIEW VÁLIDO):** El bloque Pendiente en `valu.py` NO debe limpiar ni mostrar empty state si existe un preview cacheado con datos válidos (`valor_propiedad_usd > 0` y `error` nulo), aunque `forzar_recalculo` sea `False`. Esto evita perder el preview en reruns espurios. Caches inválidos (error o sin valor) SÍ deben limpiarse. Ver test `test_pendiente_preserva_preview_valido`.

**RO-CACHE-PREVIEW-04 (forzar_recalculo SE LIMPIA POST-EXCLUSIÓN):** Después de `persistir_valuacion(commit=True)` en el bloque de exclusión de comparables ("Aplicar selección"), la key `forzar_recalculo_{prop_name}` debe eliminarse de `st.session_state` en un bloque `finally` para evitar recálculos infinitos en reruns posteriores.

**RO-CACHE-PREVIEW-05 (VALUACIÓN PERSISTE EN RETORNO DE PORTFOLIO):** Una valuación oficial persistida con `persistir_valuacion(commit=True)` debe sobrevivir al flujo Detalle → Portfolio → Detalle. En re-entry, `obtener_resultado_cacheado` debe retornar el mismo `resultado_completo` con los mismos valores (`valor_propiedad_usd`, `m2_base_venta`, `comparables_venta`, `m2_equivalentes`). El cache NO debe tener `preview=True` para valuaciones oficiales. La `_ultima_valuacion` en `propiedades.json` debe estar presente con `valor_usd` y `comps` correctos. Ver test `test_valuacion_persiste_retorno_portfolio`.

**RO-CACHE-PREVIEW-06 (TOGGLE AUTO/MANUAL PRESERVA EXCLUSIÓN):** Cambiar entre fuente Auto y Manual NO debe perder la exclusión de comparables aplicada. Para esto, el cache check en `valu.py` NO debe depender de `fuente_activa` — el cache se intenta usar siempre (independientemente de la fuente activa). Si el cache está fresco (fecha_ref == hoy, retro_dias coincide), se usa directamente. Si el cache está viejo/miss y la fuente activa NO es `'auto'`, se llama `valuar_con_cache` con `preview=True` para obtener un resultado válido con comparables SIN pisar `_ultima_valuacion` (que preserva la exclusión y los datos manuales). `valuar_con_cache` con `preview=False` (commit=True) solo se usa cuando `fuente_activa_saved == 'auto'`. Esto garantiza que la exclusión de comparables sobrevive al toggle de fuentes y que el Auto card muestra comps válidos incluso en Manual mode. Ver test `test_toggle_fuente_preserva_exclusion`.

**RO-CACHE-PREVIEW-07 (PENDIENTE NO PISA PREVIEW VÁLIDO):** Cuando `ya_valuado=False` (Pendiente) y el cache tiene un preview válido (`valor_propiedad_usd > 0`, sin `error`, `_cache.preview=True`), el bloque Pendiente en `valu.py` debe setear `preview_mode=True` en `st.session_state`. Esto evita que `valuar_con_cache(preview=False)` se llame inadvertidamente, lo que forzaría un recálculo con `commit=True` (vía `motor_vpp_core.py:1386` "reemplazar_preview_por_oficial") y destruiría el preview. Con `preview_mode=True`, `valuar_con_cache` se llama con `preview=True` → `commit=False` → el preview se preserva y la propiedad sigue apareciendo como Pendiente en Portfolio. Ver test `test_pendiente_preview_no_se_sobrescribe`.

**RO-CACHE-PREVIEW-08 (PREVIEW DESTROYED ON EXIT — MEMORIA DE TRABAJO):** Al hacer clic en "Volver al Portafolio", la función `_limpiar_estado_propiedad` debe:
1. Limpiar todo el Session State de la propiedad (memoria).
2. Eliminar del archivo `valuaciones_cache.json` cualquier entrada cuyo `_cache.preview == True` (disco).
Esto garantiza que los Previews no sobrevivan a la navegación y no contaminen la siguiente entrada a la propiedad. La `_ultima_valuacion` en `propiedades.json` NUNCA debe ser modificada por esta limpieza. Ver debug flag `[DEBUG-CLEANUP]`.

**RO-CACHE-PREVIEW-09 (RE-ENTRY LEE PARAMS DESDE UV):** Al re-entrar a una propiedad con `ya_valuado=True`, los controles Retro/Flex deben leer sus parámetros (`retro_dias`, `flex_dormitorios`) desde `_ultima_valuacion` en `propiedades.json`, NO desde el cache del motor (`valuaciones_cache.json`). Esto evita que un preview previo haya contaminado los parámetros mostrados. Para UV legacy (sin `retro_dias`/`flex_dormitorios`), se usa el cache del motor como fallback. Ver debug flag `[DEBUG-REENTRY]`.

**RO-MANUAL-COMP-01 (COMPARABLES MANUALES — FUENTE Y EDICIÓN):** Los comparables manuales se almacenan en `cache_scraping.json` con `fuente="manual"` y un `id_manual` único. El motor de valuación NO filtra por `fuente`, por lo que los manuales participan automáticamente en clusters, radios y percentiles. Solo los comparables con `fuente="manual"` pueden editarse o eliminarse desde la UI de Configuración. Los provenientes de scraping son inmutables. Ver test `test_manual_comparable_crud` y módulo `parsers/manual_comparables.py`.

---

## 3. ARQUITECTURA DE LA FÓRMULA DE VENTA (TAREA-073 — Modelo Base Puro)
`valor_venta = (m2_equiv × m2_microzona × size_discount) + cocheras + baulera`

donde:
- `m2_equiv = m2_cubiertos + (m2_semi × 0.45) + (m2_desc_propios × 0.25) + (m2_desc_comun_exclusivo × 0.15)`  (coeficientes varían según contexto PB/patio grande)
- `m2_microzona = valor_ancla_geo.usd_m2` (ancla más cercana por coordenadas, fallback a cluster P33/P50)
- `size_discount = calcular_size_discount_venta()` (descuento progresivo para >80m²)
- `cocheras + baulera`: valor aditivo de activos vía `calcular_valor_activos()`
- **No hay factores hedónicos** (estado, calidad, antigüedad, NLP). Análisis ML demostró que ubicación explica ~80% del precio (XGBoost). Edad es confounding effect. Estado/calidad son double premiums sobre el anchor.

### RO-18: Factores hedónicos eliminados en venta (TAREA-073)
`calcular_factores()` retorna 1.0 para todos los factores (estado, calidad, anti). La fórmula de venta NO multiplica por factores de propiedad. NLP NO se aplica en venta. Alquiler conserva su lógica original (con NLP, estado, calidad, anti, f_puros).

---

## 4. ARQUITECTURA DE LA FÓRMULA DE ALQUILER (TAREA-071)
`alquiler_mensual_ars = m2_equiv_alq × m2_base_alq × factores_alq × gap_alq`

- `m2_equiv_alq = m2_cubiertos + (m2_semi × 0.45) + (m2_desc_propios × 0.25) + (m2_desc_comun_exclusivo × 0.15)`
- `m2_base_alq`: 
  - **PRIMARIO:** mediana completa del cluster de alquiler (progresión geo)
  - **FALLBACK:** `(m2_base_venta_zona × 0.0045) × usdt_ars` (usa mediana COMPLETA de venta, NO P33)
- `factores_alq = factor_estado × factor_calidad × (1 + ajuste_nlp × 0.70)` (factores atenuados al 50% vs venta)
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
**Formato:** GeoJSON FeatureCollection, 751 features (263 hard + 488 soft)

### Tipos de barreras (implementación 2026-05)

| Tipo | barrier_type | Efecto Cluster | peso IDW |
|------|-------------|----------------|----------|
| Duras | `hard` | **Excluir** comparable | 0.20 |
| Blandas | `soft` | **Mantener** comparable | 0.90 |

### Barreras implementadas

- **Duras**: Ferrocarril FC Mitre (peso = 0.20 → exclusión efectiva)
- **Blandas**: Av. Pellegrini, Av. 27 de Febrero, Av. Oroño, Av. Francia, Av. Del Valle (peso = 0.90)
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

### DEC-06: NLP como multiplicador externo (TAREA-071)

- **Fecha:** Junio 2026
- **Razón:** Con el modelo multiplicativo puro, NLP ya no está dentro de sqrt. Ajusta percepción comercial sobre el valor base.
- **Impacto:** factor = factor_estado × factor_calidad × factor_anti × (1 + nlp)

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

### BUG-05: ✅ SUPERSEDED by TAREA-071 — NLP fuera del sqrt

- **Síntoma:** Factor inflado, valor lista ~$82k para Mabel (modelo aditivo anterior)
- **Causa:** valor = base × sqrt(factores) × 1.05 (NLP afuera del sqrt)
- **Fix original:** valor = base × sqrt(factores × (1+nlp))
- **Nota TAREA-071:** El modelo multiplicativo puro no usa sqrt. NLP es multiplicador externo: `(1 + nlp)`. Este bug queda obsoleto.

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

### BUG-11: ✅ SUPERSEDED by TAREA-071 — Fórmula factores alquiler incorrecta
- **Síntoma:** Los factores de estado/calidad se multiplicaban linealmente.
- **Causa:** No se seguía la fórmula sqrt(1 + suma_cruda_alq) del modelo aditivo anterior.
- **Nota TAREA-071:** El alquiler ahora usa `factor_estado × factor_calidad × (1 + nlp_atenuado)`. Sin sqrt, sin suma_cruda.

### BUG-14: ✅ SUPERSEDED by TAREA-071 — Intento de mover delta_anti fuera del sqrt
- **Síntoma:** Mabel y Ayacucho quedaron fuera de rango (subvaluados $\approx 1\%$).
- **Causa:** Error de interpretación de ALGORITMOS.md moviendo la depreciación fuera de la raíz.
- **Fix original:** Revertir inmediatamente. La fórmula correcta mantiene `delta_anti` dentro del `sqrt`.
- **Nota TAREA-071:** El modelo multiplicativo puro no usa sqrt. `factor_anti` es un multiplicador independiente. Este bug queda obsoleto.


---

## 10. TESTS DE REGRESIÓN

| test_id | Dirección | Operación | Rango esperado |
|--------|-----------|-----------|---------------|
| mabel | Mabel 1400 | valor_lista | $77,500 - $94,500 USD |
| mabel | Mabel 1400 | valor_cierre | $75,000 - $90,000 USD |
| mabel | Mabel 1400 | alquiler | $570,000 - $695,000 ARS |
| ayacucho | Ayacucho 1800 | valor_lista | $39,000 - $47,500 USD |
| ayacucho | Ayacucho 1800 | valor_cierre | $37,000 - $45,000 USD |
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

def test_nlp_multiplicador_externo():
    """TAREA-071: NLP es multiplicador externo del producto de factores"""
    r_sin = ejecutar_valuacion('mabel_sin_nlp')
    r_con = ejecutar_valuacion('mabel')
    ratio = r_con['valor_propiedad_usd'] / r_sin['valor_propiedad_usd']
    assert 1.01 <= ratio <= 1.04, f"NLP ratio={ratio} fuera de rango esperado (1.01-1.04)"

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
| Mabel venta lista | $77,500-$94,500 | $77,500-$94,500 | OK (TAREA-071) |
| Mabel venta cierre | $70,000-$90,000 | $70,000-$90,000 | OK (TAREA-071) |
| test_barrera_bv27_ayacucho | ❌ No existe | ✅ REQUERIDO | FALTA |
| test_nlp_multiplicador_externo | ❌ No existe | ✅ REQUERIDO | FALTA |
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
- ❌ Poner NLP fuera del sqrt (OBSOLETO por TAREA-071 — el modelo multiplicativo no usa sqrt)
- ❌ Subir `lambda_val` por encima de 0.012 sin aprobación

---

## 13. FUENTES DE `direccion_nominatim`

El campo `direccion_nominatim` en `rosario_avm_full.csv` tiene **dos fuentes históricas** con diferentes niveles de confianza:

| Fuente | Método | Cobertura | Confianza | Problema |
|--------|--------|-----------|-----------|----------|
| **Nominatim** (`geocode_rebuild_and_geocode.py`) | Reverse-geocode de coordenadas (lat, lon) via API de OpenStreetMap | 100% (21.017 PHs) | Media | Falla en **intersecciones/esquinas**: devuelve la calle más cercana a las coordenadas, que caen en el cruce de dos+ calles → asigna calle incorrecta |
| **OCR** (`pipeline_gpu.py` en `C:\Users\Gustavo\.gemini\antigravity\scratch\tests\`) | Descarga PDF oficial de Infomapa → render → EasyOCR con GPU → extrae dirección del plano de mensura | ~60% (~12.600 PHs) | Alta (cuando funciona) | Lento (~6s/PDF con GPU), ~40% falla en PDFs pre-1980 (escaneos de baja calidad) |

### Pipeline de construcción de la fuente de verdad

```
1. geocode_rebuild_and_geocode.py
   └→ Consulta Nominatim para cada PH con (lat, lon) del CSV
   └→ Escribe direccion_nominatim             ← cobertura 100%, falla en esquinas

2. pipeline_gpu.py
   └→ Consulta API Infomapa para cada PH sin número en direccion_nominatim
   └→ Descarga PDF oficial → OCR → extrae dirección del plano de mensura
   └→ Actualiza direccion_nominatim            ← cobertura ~60%, 100% correcto

3. Corrección via centroide catastral (TAREA-017, aplicada)
   └→ Para PHs con (seccion, manzana, grafico) válido:
   └→ Busca parcela en geometría (274k parcelas) → calcula centroide
   └→ Reverse-geocode del centroide → calle correcta (dentro del lote, no en intersección)
   └→ Actualiza direccion_nominatim y coordenadas ← 218 PHs corregidos

4. Interpolación de números faltantes via vecinos cercanos (TAREA-017)
   └→ 4.131 PHs tienen direccion_nominatim sin número de calle
   └→ 3.004 (72.7%) están en calles donde otros PHs SÍ tienen número
   └→ Método: nearest-3 con weighted inverse distance + filtro ≥20 referencias
   └→ Verificado: 67% acierto bruto, ~88% con filtro ≥20 refs
   └→ Aplicado: ~2.930 PHs con número interpolado

5. Batch centroide masivo para PHs sin número en calles con <20 refs (TAREA-018)
   └→ ~2.758 PHs restantes sin número, todos con (seccion, manzana, grafico) válidos
   └→ Para cada uno: parcela catastral → centroide → reverse-geocode Nominatim
   └→ Si Nominatim da house_number → aceptar directo (REVERSE, 25%)
   └→ Si solo calle → interpolar (nearest-3 IDW) y verificar con forward-geocode
   └→ Solo aceptar si forward dist <500m (INTERP_OK, 9%)
   └→ Cache de reverse por round(lat,3) redujo llamadas 50%
   └→ Aplicado: +611 PHs (635 REVERSE + 236 INTERP_OK - 260 ya recuperados por v1)
   └→ Total completas: 18.870/21.017 (89%)
```

### DEC-08: Corrección de direcciones en esquinas via centroide catastral

- **Fecha:** Mayo 2026
- **Problema:** PHs en intersecciones tienen `direccion_nominatim` incorrecta porque Nominatim asigna la calle del cruce, no la del lote. Detectado durante enriquecimiento de P1200 (Entre Ríos 411 → debería ser Tucumán 1291).
- **Solución:** Usar geometría catastral (274k parcelas poligonales) para calcular el centroide del lote, que cae DENTRO de la parcela (no en la calle). Reverse-geocodificar ese centroide → calle correcta.
- **Detección de esquinas (3 métodos):**
  1. **Coordenadas compartidas:** 487 grupos de PHs comparten el mismo (lat, lon) — están en la misma intersección
  2. **Distancia centroide:** 251 PHs tienen sus coordenadas a >30m del centroide de su parcela
  3. **Reverse-geocode comparativo:** 84% (21/25) de los PHs con distancia >30m tienen direccion_nominatim diferente a la del centroide
- **Impacto:** ~210 de 21.017 PHs (~1%) tienen direcciones incorrectas por estar en esquinas. La corrección requiere ~5 min (251 calls Nominatim con rate-limit).
- **Archivos afectados:** `data/rosario_avm_full.csv` (actualizar direccion_nominatim + coordenadas)

### DEC-09: Interpolación de números de calle via vecinos cercanos

- **Fecha:** Mayo 2026
- **Problema:** 4.131 PHs en el CSV tienen `direccion_nominatim` sin número de calle (ej: solo "Balcarce" sin número).
- **Solución:** Usar los 16.886 PHs que SÍ tienen número completo como referencia para interpolar el número faltante. Para cada PH sin número:
  1. Encontrar los 3 PHs más cercanos (por coordenadas) en la MISMA calle que tengan número
  2. Interpolar ponderando por distancia inversa (Inverse Distance Weighting)
  3. Filtrar: solo calles con ≥20 referencias (garantiza ~88% de acierto)
- **Cobertura:** 2.930 PHs recuperables de 4.131 (71%)
- **Verificación:** 12 PHs forward-geocodificados contra OSM → 8/12 dentro de 100m, los 4 errores en calles con <20 referencias
- **Archivos afectados:** `data/rosario_avm_full.csv`

### DT-06: Corrección masiva de direcciones en esquinas + batch centroide ✅

| # | Task | Estado | Notas |
|---|------|--------|-------|
| DT-06 | Aplicar centroide catastral → reverse-geocode → corregir direccion_nominatim para ~210 PHs en esquinas | ✅ COMPLETADO | 218 PHs corregidos (commit 7099715) |
| DT-06b | Batch centroide masivo para ~2.758 PHs sin número en calles con <20 refs | ✅ COMPLETADO | +611 PHs recuperados (635 REVERSE + 236 INTERP_OK), 1.326 calls Nominatim con cache |

### DT-07: Interpolación de números faltantes via vecinos cercanos

| # | Task | Estado | Notas |
|---|------|--------|-------|
| DT-07 | Interpolar números de calle para ~2.930 PHs sin número (≥20 refs por calle) | ✅ COMPLETADO | Método nearest-3 IDW, ~88% acierto estimado |

### DEC-10: Batch centroide masivo para PHs sin número en calles con <20 referencias

- **Fecha:** Mayo 2026
- **Problema:** 2.758 PHs sin número en calles con <20 referencias — la interpolación simple no es viable (acierto <50%)
- **Solución:** Combinar tres técnicas en pipeline secuencial:
  1. **Centroide catastral** → parcela (274k polígonos) → centroide del lote (no de la calle)
  2. **Reverse-geocode** del centroide → si Nominatim devuelve `house_number` → aceptar directo (confianza alta, ~33% de casos)
  3. **Interpolación condicional** si solo hay calle → nearest-3 IDW → forward-geocode verificar → solo aceptar si <500m del centroide
- **Cache de reverse:** Agrupar por `round(lat, 3), round(lon, 3)` — dos PHs en la misma cuadra comparten reverse geocode → redujo llamadas ~50% (773 cache hits de 1.326)
- **Filtro de calidad:** Rechazar interpolaciones con forward dist ≥500m (122 de 358 intentos, 34%)
- **Impacto:** +611 PHs recuperados (neto), 18.870 completas (89%), valuaciones de referencia estables
- **Archivos afectados:** `data/rosario_avm_full.csv`

---
### RO-19: Size adjustment configurable por macrozona (TAREA-074)
El ajuste por tamano (`calcular_size_adjustment()`) se define por macrozona en `zonas_depreciacion.json`.
Cada macrozona tiene su curva piecewise linear. Puerto Norte tiene curva separada (subzona) porque
el $/m² AUMENTA con el tamano (contrario al resto de la ciudad). Las curvas se calibran desde
cache_scraping y son editables desde la UI.

### RO-20: Depreciación no es factor de mercado en Rosario (TAREA-076)
La depreciación por antigüedad NO existe como factor de mercado independiente en Rosario.
NO se incluye en el display de subfactores de Valuación Manual.

**Evidencia ML (confirmada en TAREA-073):**
- XGBoost (R²=0.839): ubicación (lat+lon) = 80% del precio. Edad no es feature relevante.
- RandomForest por macrozona: centro_premium -0.18%/año, norte +0.06%/año (aprecia).
  Solo oeste muestra -0.85%/año (pero con solo 112 muestras).
- Grid RF 40×40 controlando ubicación exacta: Mabel +0.2% en 55 años.
- **Conclusión:** Edad es confounding effect con ubicación (las propiedades viejas están en
  zonas céntricas, no porque envejecer baje el precio). Estado, calidad, amenities y NLP
  son observables de propiedad que SÍ se muestran como referencia en la UI.


