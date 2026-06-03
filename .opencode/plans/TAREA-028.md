# TAREA-028 — Disposición + Ambientes (datos estructurados) — Riesgo BAJO

## CONTEXTO

Hoy `disposición` (frente/contrafrente/pasante/interna/lateral) y `ambientes` (cantidad de ambientes) no existen como campos estructurados. Solo aparecen en texto libre (`descripcion_libre`). El motor de factores premia `vista` (río +25%, interna -10%) y `ventilacion_cruzada` (+5%), pero no captura la posición de la unidad en la planta.

El riesgo de agregar `disposición` es duplicar lo que ya premia `vista`/`ventilacion`. Por eso:
- `pasante` NO suma (ya cubierto por ventilación cruzada)
- Solo penalizaciones: `contrafrente` -0.5%, `interna` -1.0% (con tope si vista ya castiga)

`Ambientes` se agrega solo como campo informativo — sin factor de precio — para evitar duplicar con `layout_flexible` (+4%).

## REGLA DE ORO

- `pytest` pasa después de cada paso
- Los valores de las 4 propiedades de calibración (Mabel, Ayacucho, Entre Ríos, Vera Mujica) NO cambian
- La suma cruda clamp (±40%) y AMENITY_TOTAL_CAP (6%) no se modifican
- `disposición` NUNCA suma más que `vista` cuando vista ya tiene premio fuerte
- `ambientes` NO entra en la fórmula de precio (solo datos + narrativa)

## ALCANCE

| Archivo | Cambio |
|---|---|
| `valu_forms.py` | Agregar campo `disposicion` (select) y `ambientes` (number input) al formulario |
| `propiedades.json` | Nuevos campos opcionales en el modelo de datos |
| `parsers/mercado_inmobiliario.py` | Agregar `factor_disposicion` en `calcular_factores()` — solo penalizaciones, sin premio a pasante |
| `parsers/mercado_inmobiliario.py` | Mencionar `disposición` y `ambientes` en `generar_razonamiento_valuacion()` |
| `docs/DICCIONARIO_DATOS.md` | Documentar ambos campos nuevos |
| `tests/test_regression.py` | Test unitario de `factor_disposicion` |

---

### PASO 1: Agregar campos al formulario (`valu_forms.py`)

**Archivo:** `valu_forms.py` — sección de datos generales (~líneas 240-280)

**1.1** Insertar `disposicion` como selectbox después del campo `vista`:
```python
disposiciones = ["frente", "contrafrente", "pasante", "interna", "lateral"]
disposicion = st.selectbox(
    "Disposición",
    disposiciones,
    index=disposiciones.index(prop_inicial.get('disposicion', 'frente'))
        if prop_inicial.get('disposicion') in disposiciones else 0,
    key=f"disp_{key_suffix}",
    help="Posición de la unidad en la planta del edificio. Pasante ya está cubierto por ventilación cruzada."
)
```

**1.2** Insertar `ambientes` como number input, cerca de `dormitorios`:
```python
ambientes = st.number_input(
    "Ambientes",
    min_value=1, max_value=20, step=1,
    value=prop_inicial.get('ambientes', 0) or 0,
    key=f"amb_{key_suffix}",
    help="Cantidad total de ambientes (incluye dormitorios, living, comedor, etc.)"
)
```

**1.3** Agregar al ensamblado `data`:
```python
'disposicion': disposicion,
'ambientes': ambientes if ambientes > 0 else None,
```

---

### PASO 2: Agregar `factor_disposicion` en `calcular_factores()`

**Archivo:** `parsers/mercado_inmobiliario.py` — dentro de `calcular_factores()` (~línea 1990)

**2.1** Insertar lógica de disposición (solo penalizaciones):
```python
# Factor disposicion (TAREA-028): solo penalizaciones, sin premio a pasante
disposicion_raw = prop.get('disposicion')
if disposicion_raw is None:
    delta_disposicion = 0.0  # propiedades legacy sin cambios
else:
    disp = disposicion_raw.lower()
    vista = prop.get('vista', 'frente').lower()
    penalizaciones = {
        'contrafrente': -0.005,
        'interna': -0.01,
    }
    delta_disposicion = penalizaciones.get(disp, 0.0)
    # Evitar doble castigo si vista ya es interna/pulmon
    if delta_disposicion < 0 and vista in ('interna', 'pulmon'):
        delta_disposicion = max(delta_disposicion, -0.005)
```

**2.2** Agregar `delta_disposicion` a `suma_cruda`.

Incluir `factor_disposicion` y `delta_disposicion` en el dict de retorno.

---

### PASO 3: Actualizar narrativa

**Archivo:** `parsers/mercado_inmobiliario.py` — `generar_razonamiento_valuacion()` (~línea 3980)

**3.1** Mención de `disposición` en características funcionales:
```python
disp = prop.get('disposicion', '')
if disp == 'interna':
    lineas_func_neg.append("disposición interna con menor exposición")
elif disp == 'contrafrente':
    lineas_func_neg.append("disposición al contrafrente")
```

**3.2** Mención de `ambientes` en párrafo 1 (identificación):
```python
amb = prop.get('ambientes', 0)
if amb and amb > dorms:
    texto_amb = f" de {amb} ambientes"
else:
    texto_amb = ""
```

---

### PASO 4: Actualizar documentación

**Archivo:** `docs/DICCIONARIO_DATOS.md`

Agregar secciones para `disposicion` y `ambientes`.

---

### PASO 5: Tests

Agregar tests unitarios en `tests/test_disposicion.py`:
- Propiedad sin `disposicion` → delta 0
- `disposicion: "pasante"` → delta 0
- `disposicion: "contrafrente"` → delta -0.005
- `disposicion: "interna"` → delta -0.01
- `disposicion: "interna"` + `vista: "interna"` → delta -0.005 (doble castigo reducido)
- `ambientes` no afecta precio

---

### VALIDACION FINAL

```
☐ pytest pasa (39+ tests)
☐ Mabel, Ayacucho, Entre Ríos, Vera Mujica sin cambios
☐ Propiedad con disposicion "interna" muestra -1% en factor
☐ Propiedad con vista "interna" + disposicion "interna" → solo -0.5%
☐ PDF y razonamiento narrativo mencionan disposicion/ambientes
☐ auto_validate.py OK
```

### DOCS A ACTUALIZAR

- `docs/DICCIONARIO_DATOS.md`
- `docs/BITACORA_AGENTES.md`
- `docs/STATUS_ACTUAL.md`
- `.opencode/plans/TAREAS_INDEX.md`
- `.opencode/plans/TAREA-028.md` (este archivo)
