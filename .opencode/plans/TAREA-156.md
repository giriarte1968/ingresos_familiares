# TAREA: Refactor de Fórmula de Alquiler

## CONTEXTO
El cálculo de alquiler tiene dos caminos que se contradicen:
1. **Stage 1 (lines 3465-3530)**: Cluster-based — obtiene alquileres del mercado, aplica CT alquiler, aplica GAP_ALQUILER=0.92
2. **Stage 2 (lines 3558-3563)**: Cap Rate override — cuando `cap_info` NO es fallback, **SOBRESCRIBE** el resultado del Stage 1 con `valor_venta × cap_rate / 12`

**Problema**: Stage 2 descarta todo el cálculo del cluster. El resultado final (`metodo_alquiler: mercado_local`) ignora los alquileres reales del mercado.

**Insight del artículo**: "Valor venta NUNCA entra en el cálculo del alquiler" — son dos outputs independientes. Cap rate es OUTPUT, nunca INPUT.

## REGLA DE ORO
- El alquiler debe venir del cluster de alquileres cuando hay datos suficientes (≥5 comps)
- Cap rate es OUTPUT calculado al final, NO input al cálculo
- GAP_ALQUILER = 0.92 es juicio experto → eliminar
- Cuando no hay suficientes alquileres, usar `valor_manual × cap_rate / 12` con etiqueta "confianza baja"

## ALCANCE

| Archivo | Cambio |
|---------|--------|
| `parsers/mercado_inmobiliario.py` | Eliminar override de Stage 2, eliminar GAP_ALQUILER, hacer cap_rate OUTPUT |
| `valu_detail_sections.py` | Agregar label "confianza baja" cuando alquiler usa fallback |
| `main_valu_detail_sections.py` | Agregar label "confianza baja" (legacy UI) |

---

## PASO 1: Eliminar GAP_ALQUILER

**Archivo:** `parsers/mercado_inmobiliario.py`

Eliminar línea 3516:
```python
# ELIMINAR:
GAP_ALQUILER = 0.92
alquiler_mensual_ars = m2_equiv_alquiler * m2_base_alquiler * factores_alquiler * GAP_ALQUILER

# REEMPLAZAR POR:
alquiler_mensual_ars = m2_equiv_alquiler * m2_base_alquiler * factores_alquiler
```

**COMMIT:** `"refactor(alquiler): eliminate GAP_ALQUILER expert judgment factor"`

---

## PASO 2: Eliminar Cap Rate override de Stage 2

**Archivo:** `parsers/mercado_inmobiliario.py`

El Stage 2 actual (lines 3558-3563):
```python
if cap_info is not None and not cap_info.get('es_fallback', True):
    cap_rate = cap_info['cap_rate']
    alquiler_mensual_usd = valor_venta * cap_rate / 12  # ← SOBRESCRIBE cluster
    alquiler_mensual_ars = alquiler_mensual_usd * usdt_ars
    metodo_alquiler = 'mercado_local'
```

**Nuevo flujo:**
1. Si `n_alq >= 5` (alquileres del cluster): usar `alquiler_mensual_ars` del Stage 1 como valor final
2. Si `n_alq < 5` (sin datos suficientes): usar `valor_venta × cap_rate / 12` con `metodo_alquiler = 'fallback_cap_rate'` y `confianza_alq = 'BAJA'`
3. Calcular `cap_rate_output = (alquiler_mensual_ars * 12) / (valor_venta * usdt_ars)` — OUTPUT, no input

```python
# NUEVO:
if n_a >= 5:
    # Alquiler viene del cluster (datos de mercado)
    alquiler_mensual_usd = alquiler_mensual_ars / usdt_ars
    metodo_alquiler = 'cluster_alquiler'
    confianza_alq = 'ALTA' if n_a >= 10 else 'MEDIA'
    es_fallback = False
    # Calcular cap rate como OUTPUT
    cap_rate = (alquiler_mensual_ars * 12) / (valor_venta * usdt_ars) if valor_venta > 0 else 0.05
else:
    # Fallback: usar cap rate del mercado local
    # ... mantener lógica actual de cap_rate ...
    metodo_alquiler = 'fallback_cap_rate'
    confianza_alq = 'BAJA'
```

**COMMIT:** `"refactor(alquiler): cluster-based alquiler as primary path, cap_rate as fallback only"`

---

## PASO 3: Agregar label "confianza baja" en UI

**Archivo:** `valu_detail_sections.py`

En `render_metricas()`, cuando `metodo_alquiler` contiene "fallback" o "confianza" es "BAJA", agregar texto explicativo debajo del alquiler:

```python
if metodo_alquiler and 'fallback' in metodo_alquiler:
    st.caption("⚠️ Alquiler estimado por cap rate (pocos alquileres en zona). Para mayor precisión, agregar más propiedades de alquiler.")
elif confianza_alq == 'BAJA':
    st.caption("⚠️ Confianza baja en estimación de alquiler.")
```

**Archivo:** `main_valu_detail_sections.py`

Mismo cambio en la UI legacy.

**COMMIT:** `"ui(alquiler): add confidence warning when using cap_rate fallback"`

---

## PASO 4: Sincronizar docs

Actualizar `docs/MEMORIA_PROYECTO.md`:
- Eliminar mención de GAP_ALQUILER
- Documentar que cap_rate es OUTPUT, no INPUT
- Documentar flujo: cluster ≥5 → alquiler directo, cluster <5 → fallback cap_rate

**COMMIT:** `"docs: update alquiler formula documentation"`

---

## VALIDACION FINAL
```
☐ python scripts/auto_validate.py pasa
☐ Alquiler con ≥5 comps: metodo_alquiler='cluster_alquiler', confianza ALTA/MEDIA
☐ Alquiler con <5 comps: metodo_alquiler='fallback_cap_rate', confianza BAJA + warning
☐ GAP_ALQUILER eliminado de la fórmula
☐ Cap rate calculado como OUTPUT al final
☐ UI muestra warning de confianza cuando aplica
☐ No hay regressiones en test_regression.py
```
