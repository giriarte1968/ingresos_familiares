# TAREA-163 — Fix flex_dormitorios destruye pool de comparables — Riesgo MEDIO

## CONTEXTO

Cuando el usuario activa "Todos los dormitorios" (flex_dormitorios), la busqueda geografica progresiva se detiene en un radio MAS CORTO (300m) porque los 2-3 dorm inflan el pool y cumplen `MIN_COMPARABLES=10` antes de llegar al radio donde estan los mismos-dorm (800m). Esto **destruye** el pool natural en vez de **enriquecerlo**.

**Bug introducido en commit `b1c9717`** (25 Jul 2026): "Fix: flex dormitorios in primary search". El fix paso `flex_dormitorios` a Step 1 (busqueda geografica progresiva), que antes siempre usaba `tolerancia_dorms=0`.

**Ejemplo Cochabamba 45 (4 dorm):**
- Flex OFF: radio 800m -> 2 comps (ambos 4 dorm)
- Flex ON: radio 300m -> ~10 comps (mayoria 2-3 dorm, 0 comps 4 dorm)

## REGLA DE ORO

- **RO-FLEX-ENRICH**: flex_dormitorios SOLO enriquece, NUNCA destruye el pool de mismos-dorm
- El motor automatico NO cambia comportamiento sin flex
- `pytest` pasa despues de cada paso
- Todo cambio debe tener debug flag `[DEBUG-FLEX-RADIO]`

## ALCANCE

| Archivo | Cambio |
|---|---|
| `parsers/mercado_inmobiliario.py` | Two-phase search en `obtener_mediana_cluster_v2`: Step 1 busca solo mismos-dorm, Step 1b agrega flex como enrichment |
| `parsers/mercado_inmobiliario.py` | Debug flags `[DEBUG-FLEX-RADIO]` en cada paso del radio loop |
| `parsers/cluster_filters.py` | Nueva funcion `contar_por_dormitorios()` para desglose mismos vs flex |
| `tests/test_regression.py` | Tests de regresion: flex ON no pierde mismos-dorm, flex OFF sin cambio |
| `docs/ALGORITMOS.md` | Documentar two-phase search strategy |
| `docs/BITACORA_AGENTES.md` | Registrar bug `b1c9717` y fix TAREA-163 |

---

## PASO 1: Two-phase search en `obtener_mediana_cluster_v2()`

**Archivo:** `parsers/mercado_inmobiliario.py` — funcion `obtener_mediana_cluster_v2()` (linea ~1223)

**JUSTIFICACION RO:** No se viola RO-FLEX-ENRICH porque el fix IMPLEMENTA la regla: flex solo enriquece. Se revierte parcialmente el cambio de `b1c9717` manteniendo el beneficio (enrichment) sin el dano (destruccion del pool).

**1.1** En el loop progresivo (linea 1223-1240), CAMBIAR la logica:

```python
# ANTES (bug b1c9717):
for radio in RADIOS_PROGRESIVOS:
    props_geo = cluster_filters.filtrar_por_radio(...)
    props_geo = cluster_filters.filtrar_por_tipo_operacion_dorms(
        ..., flex_dormitorios=flex_dormitorios  # BUG: infla pool
    )
    props_geo = [p for p in props_geo if p.get('valor_m2', 0) > 0]
    props_geo = aplicar_filtro_fecha(props_geo, fecha_ref)
    if len(props_geo) >= MIN_COMPARABLES:
        mejor_resultado = (props_geo, radio, "busqueda_geografica")
        break

# DESPUES (TAREA-163):
for radio in RADIOS_PROGRESIVOS:
    props_geo = cluster_filters.filtrar_por_radio(...)
    props_geo_todos = cluster_filters.filtrar_por_tipo_operacion_dorms(
        ..., flex_dormitorios=flex_dormitorios  # pool completo
    )
    props_geo_todos = [p for p in props_geo_todos if p.get('valor_m2', 0) > 0]
    props_geo_todos = aplicar_filtro_fecha(props_geo_todos, fecha_ref)
    
    # FASE 1: Contar SOLO mismos-dorm
    n_mismos = sum(1 for p in props_geo_todos if p.get('dormitorios') == dormitorios)
    
    print(f"[DEBUG-FLEX-RADIO] radio={radio}m: total={len(props_geo_todos)}, mismos={n_mismos}, flex={len(props_geo_todos)-n_mismos}, MIN={MIN_COMPARABLES}")
    
    # Break solo si hay suficientes MISMOS-dorm
    if n_mismos >= MIN_COMPARABLES:
        mejor_resultado = (props_geo_todos, radio, "busqueda_geografica")
        break
    # Si flex esta OFF, mantener logica original (cualquier comp cuenta)
    elif flex_dormitorios is None and len(props_geo_todos) >= MIN_COMPARABLES:
        mejor_resultado = (props_geo_todos, radio, "busqueda_geografica")
        break
```

**1.2** Agregar fallback: si el loop termina sin break, usar el ultimo radio con el pool completo:

```python
# Al final del loop, si no hubo break:
if mejor_resultado is None and props_geo_todos:
    mejor_resultado = (props_geo_todos, RADIOS_PROGRESIVOS[-1], "busqueda_geografica_fallback")
    print(f"[DEBUG-FLEX-RADIO] fallback: radio={RADIOS_PROGRESIVOS[-1]}m, total={len(props_geo_todos)}, mismos={n_mismos}")
```

**1.3** Aplicar la misma logica a Step 2 (buscar_en_zona con radio, linea 1264-1270):

```python
# ANTES:
for radio in RADIOS_PROGRESIVOS:
    props = buscar_en_zona(zona_normalizada, dormitorios, operacion, ...)
    props = aplicar_filtro_fecha(props, fecha_ref)
    if len(props) >= MIN_COMPARABLES:
        mejor_resultado = (props, radio, zona_normalizada)
        break

# DESPUES:
for radio in RADIOS_PROGRESIVOS:
    props = buscar_en_zona(zona_normalizada, dormitorios, operacion, ...)
    props = aplicar_filtro_fecha(props, fecha_ref)
    n_mismos_zona = sum(1 for p in props if p.get('dormitorios') == dormitorios)
    
    print(f"[DEBUG-FLEX-RADIO] Step2 radio={radio}m zona={zona_normalizada}: total={len(props)}, mismos={n_mismos_zona}")
    
    if n_mismos_zona >= MIN_COMPARABLES:
        mejor_resultado = (props, radio, zona_normalizada)
        break
    elif flex_dormitorios is None and len(props) >= MIN_COMPARABLES:
        mejor_resultado = (props, radio, zona_normalizada)
        break
```

---

## PASO 2: Funcion auxiliar `contar_por_dormitorios()`

**Archivo:** `parsers/cluster_filters.py`

**2.1** Agregar funcion:

```python
def contar_por_dormitorios(comparables, dorm_sujeto):
    """Desglosa comparables por dormitorios: mismos vs flex."""
    n_mismos = sum(1 for c in comparables if c.get('dormitorios') == dorm_sujeto)
    n_flex = len(comparables) - n_mismos
    return {'n_mismos': n_mismos, 'n_flex': n_flex, 'total': len(comparables)}
```

---

## PASO 3: Tests de regresion

**Archivo:** `tests/test_regression.py`

**3.1** Test: flex ON no pierde mismos-dorm comparables

```python
def test_flex_on_preserves_same_dorm_comps():
    """TAREA-163: flex ON debe PRESERVAR comparables de mismos dorm, no destruirlos."""
    from parsers.mercado_inmobiliario import obtener_mediana_cluster_v2
    
    # Propiedad de 4 dorm en Sexta (Cochabamba 45 coords)
    mediana_flex, n_flex, meta_flex = obtener_mediana_cluster_v2(
        zona='Sexta', dormitorios=4, operacion='venta',
        lat_ref=-32.9534, lon_ref=-60.6393,
        flex_dormitorios=[1, 2, 3, 4, 5]
    )
    
    mediana_no_flex, n_no_flex, meta_no_flex = obtener_mediana_cluster_v2(
        zona='Sexta', dormitorios=4, operacion='venta',
        lat_ref=-32.9534, lon_ref=-60.6393,
        flex_dormitorios=None
    )
    
    # Flex ON debe encontrar AL MENOS los mismos comps que flex OFF
    assert n_flex >= n_no_flex, f"flex ON ({n_flex}) perdio comps vs flex OFF ({n_no_flex})"
    
    # Flex ON debe tener radio >= radio de flex OFF (no mas corto)
    radio_flex = meta_flex.get('radio_usado', 0)
    radio_no_flex = meta_no_flex.get('radio_usado', 0)
    assert radio_flex >= radio_no_flex, f"flex ON radio ({radio_flex}m) < flex OFF radio ({radio_no_flex}m)"
```

**3.2** Test: flex OFF sin cambio de comportamiento

```python
def test_flex_off_unchanged_behavior():
    """TAREA-163: flex OFF no debe cambiar comportamiento pre-existente."""
    from parsers.mercado_inmobiliario import obtener_mediana_cluster_v2
    
    # Mabel (1 dorm, Martin)
    mediana, n, meta = obtener_mediana_cluster_v2(
        zona='Martin', dormitorios=1, operacion='venta',
        lat_ref=-32.9541, lon_ref=-60.6316,
        flex_dormitorios=None
    )
    
    # Debe encontrar comparables (sin flex es comportamiento original)
    assert n >= 2, f"flex OFF encontro solo {n} comps (deberia ser >= 2)"
    assert meta.get('radio_usado', 0) > 0, "radio_usado no seteado"
```

---

## PASO 4: Debug flags para prevenir regresiones

**Archivo:** `parsers/mercado_inmobiliario.py`

**4.1** Agregar debug flags en cada punto del radio loop:

```python
# Step 1 - Geographic search
print(f"[DEBUG-FLEX-RADIO] Step1: zona=geo, dorms={dormitorios}, flex={flex_dormitorios}")

# Step 2 - Zone search  
print(f"[DEBUG-FLEX-RADIO] Step2: zona={zona_normalizada}, dorms={dormitorios}, flex={flex_dormitorios}")

# Al final del function
print(f"[DEBUG-FLEX-RADIO] Resultado: radio={mejor_resultado[1]}m, source={mejor_resultado[2]}, total={len(mejor_resultado[0])}")
```

**4.2** Agregar flag de validacion anti-regresion:

```python
# Al final de obtener_mediana_cluster_v2, antes del return:
if flex_dormitorios is not None and mejor_resultado is not None:
    _pool = mejor_resultado[0]
    _n_mismos = sum(1 for p in _pool if p.get('dormitorios') == dormitorios)
    _n_total = len(_pool)
    if _n_mismos == 0 and _n_total > 0:
        print(f"[DEBUG-FLEX-RADIO] WARNING: flex activo pero 0 mismos-dorm en pool de {_n_total} comps. Radio={mejor_resultado[1]}m")
```

---

## PASO 5: Documentacion

**5.1** `docs/ALGORITMOS.md` — Agregar seccion "Two-Phase Comparable Search":

```markdown
## Two-Phase Comparable Search (TAREA-163)

Cuando "Todos los dormitorios" esta activo, la busqueda usa estrategia two-phase:

1. **Fase 1 (busqueda progresiva):** Busca comparables de MISMOS dormitorios.
   El `break` del loop solo se activa cuando `n_mismos >= MIN_COMPARABLES`.
   Los comparables de otros dormitorios se incluyen en el pool pero NO cuentan
   para el threshold de break.

2. **Fase 2 (enrichment):** Los comparables de otros dormitorios se agregan al pool
   ya seleccionado, nutriendo la muestra sin destruir la base de mismos-dorm.

**Regla RO-FLEX-ENRICH:** flex_dormitorios SOLO enriquece, NUNCA destruye.
```

**5.2** `docs/BITACORA_AGENTES.md` — Registrar:

```markdown
## Bug flex_dormitorios (TAREA-163)

- **Fecha:** 2026-08-03
- **Commit bug:** `b1c9717` (25 Jul 2026) — "Fix: flex dormitorios in primary search"
- **Problema:** flex_dormitorios en Step 1 (geo progresivo) infla pool -> break a 300m -> destruye mismos-dorm comps
- **Fix:** Two-phase search: break solo con n_mismos >= MIN_COMPARABLES
- **Regla RO-FLEX-ENRICH:** flex solo enriquece, nunca destruye
```

---

## VERIFICACION

1. `python -m pytest tests/test_regression.py -v` -> todos pasan
2. `python scripts/auto_validate.py` -> OK
3. Probar manualmente en UI: Cochabamba 45 con flex ON -> debe mantener 4-dorm comps + agregar otros
4. Probar propiedad de 1 dorm (Mabel) con flex ON -> sin cambio visible
5. `git commit && git push`