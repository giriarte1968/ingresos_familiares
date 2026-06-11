# TAREA-040 — Preview valuation: toggles Retro/Flex muestran comps sin persistir a portfolio

## CONTEXTO

Actualmente las propiedades Pendiente se comportan así:
- Al abrir: $0, 0 comps, mapa del sujeto ✅
- Al togglear Retro ON: se setea `forzar_recalculo=True` → engine encuentra comps ✅
- PERO también persiste `_ultima_valuacion` con `fuente: auto` → portfolio muestra la propiedad como valuada ❌

Cuando se intentó arreglar removiendo `forzar_recalculo` del toggle, Retro dejó de funcionar (el toggle no disparaba la búsqueda de comps).

## REGLA DE ORO

1. `pytest tests/test_regression.py` pasa después de cada paso
2. `python scripts/auto_validate.py` pasa después de cada paso
3. **NO romper funcionalidad existente** — Retro toggle debe seguir mostrando comps inmediatamente
4. Una propiedad Pendiente NO debe aparecer como valuada en el portfolio hasta que el usuario presione "Aplicar cambios"

## ALCANCE

El problema es que `forzar_recalculo` (trigger del toggle) y `"Aplicar cambios"` usan el mismo mecanismo y ambos persisten `_ultima_valuacion` via `persistir_valuacion()`.

**Solución propuesta:** Agregar modo "preview" que calcula y cachea comps pero NO escribe `_ultima_valuacion` en `propiedades.json`.

| Archivo | Cambio |
|---------|--------|
| `parsers/motor_vpp_core.py` | `valuar_con_cache` recibe `preview=False`. Cuando `True`, llama `persistir_valuacion(commit=False)` |
| `parsers/valuacion_cache.py` | `persistir_valuacion` recibe `commit=True`. Cuando `False`, solo actualiza cache (no escribe `_ultima_valuacion`) |
| `valu.py` | Toggle Retro/Flex setea `forzar_recalculo` + `preview_mode=True`. "Aplicar cambios" setea `forzar_recalculo` + elimina `preview_mode`. Pasar `preview=preview_mode` a `valuar_con_cache` |

---

### PASO 1: `persistir_valuacion` — parámetro `commit`

**Archivo:** `parsers/valuacion_cache.py:123-177`

**1.1** Cambiar firma:
```python
def persistir_valuacion(nombre: str, prop: dict, resultado: dict, cache: dict, commit: bool = True) -> bool:
```

**1.2** Envolver el bloque 3-4 (actualizar `propiedades.json` con `_ultima_valuacion`):
```python
# 3. Actualizar propiedades.json con _ultima_valuacion
if commit and os.path.exists(PROPIEDADES_PATH):
    ...
    # (código existente de _ultima_valuacion)
    ...

# 4. Escribir propiedades.json a disco
if commit:
    atomic_write_json(PROPIEDADES_PATH, props_data)
```

**1.3** Los pasos 1-2 (cache en memoria + disco) siempre se ejecutan (sin importar commit).

**⚠️ Verificar:** `pytest tests/test_regression.py` — los tests existentes llaman `valuar_con_cache` sin `preview`, deben seguir persistiendo normal.

**COMMIT:** `"TAREA-040-paso1: persistir_valuacion parametro commit"`

---

### PASO 2: `valuar_con_cache` — parámetro `preview`

**Archivo:** `parsers/motor_vpp_core.py:1333-1455`

**2.1** Cambiar firma:
```python
def valuar_con_cache(prop: dict, ... , preview: bool = False) -> dict:
```

**2.2** En el bloque que llama `persistir_valuacion` (~línea 1404):
```python
ok_persist = persistir_valuacion(nombre, prop, resultado, cache, commit=not preview)
```

**2.3** En el cache `_cache` metadata, registrar si fue preview:
```python
resultado['_cache'] = {
    'recalculado': True,
    'razon': razon,
    'retro_dias': retro_dias,
    'flex_dormitorios': flex_dormitorios,
    'preview': preview,  # <-- nuevo
    'timestamp': datetime.now().isoformat()
}
```

**COMMIT:** `"TAREA-040-paso2: valuar_con_cache parametro preview"`

---

### PASO 3: `valu.py` — pasar `preview` desde toggles y "Aplicar cambios"

**Archivo:** `valu.py`

**3.1** En el toggle Retro, agregar `preview_mode`:
```python
if st.button(...):
    st.session_state[retro_key] = not retro_active
    if res.get('fuente') is None:
        st.session_state[f'forzar_recalculo_{prop_name}'] = True
        st.session_state[f'preview_mode_{prop_name}'] = True  # <-- nuevo
    st.rerun()
```

**3.2** En el toggle Retro Flexible, igual:
```python
if st.button(...):
    st.session_state[flex_key] = not flex_active
    if res.get('fuente') is None:
        st.session_state[f'forzar_recalculo_{prop_name}'] = True
        st.session_state[f'preview_mode_{prop_name}'] = True  # <-- nuevo
    st.rerun()
```

**3.3** En "Aplicar cambios", limpiar `preview_mode`:
```python
if st.button("✅ Aplicar cambios", ...):
    st.session_state[f'forzar_recalculo_{prop_name}'] = True
    if f'preview_mode_{prop_name}' in st.session_state:
        del st.session_state[f'preview_mode_{prop_name}']  # <-- commit mode
    st.rerun()
```

**3.4** En el bloque donde se llama `valuar_con_cache` (~línea 516):
```python
preview_mode = st.session_state.get(f'preview_mode_{prop_name}', False)
resultado = valuar_con_cache(p_obj, forzar_recalculo=forzar, ..., preview=preview_mode)
```

**3.5** También actualizar el Pendiente early return (~línea 446):
```python
if not ya_valuado and not forzar:
```

Este guard sigue igual — `forzar=True` del toggle pasa de largo. No hay cambios aquí.

**⚠️ Importante:** `preview_mode` se setea SOLO cuando Pendiente (`fuente is None`). Si la propiedad ya está valuada, togglear Retro/Flex no activa preview.

**COMMIT:** `"TAREA-040-paso3: valu.py preview_mode en toggles"`

---

### PASO 4: Cleanup — eliminar `preview_mode` en navegación

**Archivo:** `valu.py`

**4.1** En `ir_al_inicio()` o al hacer clic en "Volver al Portafolio", limpiar `preview_mode`:
```python
def ir_al_inicio():
    ...
    for k in list(st.session_state.keys()):
        if k.startswith('prop_sel') or k.startswith('_force_nav_page') or k.startswith('nav_page_radio') or k.startswith('preview_mode'):
            del st.session_state[k]
```

Esto asegura que al volver al portfolio y re-entrar, `preview_mode` está limpio.

**COMMIT:** `"TAREA-040-paso4: limpiar preview_mode al navegar"`

---

### PASO 5: Prueba manual + validación

**5.1** Probar flujo completo:
1. Abrir propiedad Pendiente → $0, 0 comps, mapa del sujeto
2. Toggle Retro ON → aparecen comps con Retro ✅
3. Ir al portfolio → propiedad muestra Pendiente (no valuada) ✅
4. Re-entrar a propiedad → toggle Retro ON de nuevo → aparecen comps ✅
5. Click "Aplicar cambios" → comps se mantienen ✅
6. Ir al portfolio → propiedad muestra valuada ✅

**5.2** Probar propiedades ya valuadas (sin preview):
1. Abrir propiedad valuada → valuación normal
2. Toggle Retro ON → recálculo con Retro (sin preview)
3. Ir al portfolio → sigue valuada

**COMMIT:** `"TAREA-040-paso5: validacion final"`

---

## VALIDACION FINAL

```
☐ auto_validate.py OK
☐ pytest test_regression.py (39/39)
☐ Toggle Retro ON desde Pendiente → comps visibles, portfolio sigue Pendiente
☐ Click "Aplicar cambios" desde Pendiente → portfolio muestra valuada
☐ Toggle Retro OFF/ON en propiedad ya valuada → preview_mode NO activado
☐ Re-entry a Pendiente después de preview → Pendiente de nuevo (sin preview_mode)
```

## ARCHIVO DE PLAN

El plan se guarda permanentemente en `.opencode/plans/TAREA-040.md`.
NO se elimina al ejecutar.
