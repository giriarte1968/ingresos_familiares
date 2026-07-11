# Flujo UI — AVM Rosario

Documentación completa del flujo de interacción del usuario desde el Portfolio hasta la
aplicación de selección de comparables, incluyendo todos los estados de session_state,
puntos de decisión y efectos secundarios.

---

## 1. MAPA GENERAL DEL FLUJO

```
[Portfolio]
    │ Click tarjeta (URL: ?prop=X)
    ▼
[main() intercepta query param]
    │ _limpiar_estado_propiedad() → limpia TODAS las keys de la propiedad anterior
    │ st.session_state.prop_sel = nombre
    │ st.rerun()
    ▼
[mostrar_dashboard()]
    │
    ├── 1a. ¿Hay prop_sel? → NO → renderiza Portfolio
    │                        → SÍ → continúa
    │
    ├── 1b. ¿Hay flag clean_comparables_? → SÍ → recarga comparables desde disco
    │
    ├── 1c. ¿Primera entrada (vista_valuacion_ no existe)?
    │         → SÍ → Restaurar parámetros desde _ultima_valuacion (retro, flex, etc.)
    │         → NO → Usar valores actuales de session_state
    │
    ├── 1d. ¿Hay forzar_recalculo_? → SÍ → Saltar cache, forzar recálculo motor
    │                                   → NO → Usar cache si coincide fecha_ref y retro_dias
    │
    ├── 1e. ¿Hay comp_excluded_ en session_state?
    │         → SÍ → Aplicar exclusión post-motor (calcular_vm2_por_seleccion)
    │
    ├── 1f. ¿UV tenía exclusión pero resultado fresco no?
    │         → SÍ → Restaurar exclusión desde UV
    │
    └── 1g. mostrar_detalle_valu(p_obj, resultado)
                │
                ▼
          [Property Detail View]
```

---

## 2. PASO A PASO DETALLADO

### PASO 0: Portfolio → Click tarjeta

**Archivo:** `valu_portfolio2.py` → `_render_cards()` (línea 576)

Cada tarjeta es un `<a href="?prop={nombre}">`. El click es navegación URL, no un
callback de Streamlit.

**Session state:** Ninguno (el click va directo a URL)

---

### PASO 1: main() intercepta el query param

**Archivo:** `valu.py` → `main()` (líneas 1863-1876)

```python
if 'prop' in st.query_params:
    old_prop = st.session_state.get('prop_sel')
    if old_prop:
        _limpiar_y_borrar_cache_si_hay_manuales(old_prop)
    prop_name = st.query_params['prop']
    _limpiar_estado_propiedad(prop_name)
    st.session_state.prop_sel = prop_name
    st.session_state.vista_actual = 'dashboard'
    st.query_params.clear()
    st.rerun()
```

**Efectos:**
- `_limpiar_estado_propiedad(prop_name)` — Borra TODAS las keys de session_state
  que empiezan con estos prefijos (para la propiedad nueva también, dejando estado limpio):
  `preview_mode_`, `retro_active_`, `flex_active_`, `forzar_recalculo_`,
  `manual_preview_`, `comp_excluded_`, `comp_selection_`, `vista_valuacion_`,
  `retro_meses_`, `retro_meses_slider_`, `manual_params_`, `retro_btn_`, `flex_btn_`,
  `aplicar_cambios_`, `infomapa_catastro_`, `ph_sel_`, `comp1_`, `comp2_`,
  `manual_ancla_`, `manual_usd_m2_`, `manual_fh_`, `manual_aj_`, `manual_inc_`,
  `clean_comparables_`, `comp_interacted_`, `pendiente_comparables_`, `act_comparables_`,
  `sel_comp_{prop_name}_*`, `_comp_interacted_*`
- `st.session_state.prop_sel = prop_name`
- `st.session_state.vista_actual = 'dashboard'`

---

### PASO 2: mostrar_dashboard() — Fase de entrada

**Archivo:** `valu.py` → `mostrar_dashboard()` (línea 478)

#### 2a. Prop_sel check (línea 499)
```python
if st.session_state.prop_sel:
    propiedades = cargar_propiedades()
    p_obj = next((p for p in propiedades if p['nombre'] == st.session_state.prop_sel), None)
```

#### 2b. Clean comparables flag (línea 514)
```python
if st.session_state.pop(f'clean_comparables_{nombre}', False):
    # Recargar comparables desde disco
```
**Propósito:** Botón "🔄 Limpiar" en el header — recarga datos frescos.

#### 2c. Re-entry: restaurar parámetros (línea 751)
```python
vista_key = f'vista_valuacion_{nombre}'
if ya_valuado and not forzar and not st.session_state.get(vista_key, False):
    # Primera entrada en este ciclo de vida
    uv = p_obj.get('_ultima_valuacion', {})
    st.session_state[f'retro_active_{nombre}'] = uv.get('retro_activo', False)
    st.session_state[f'retro_meses_{nombre}'] = uv.get('retro_dias', 36)
    st.session_state[f'retro_meses_slider_{nombre}'] = uv.get('retro_dias', 36)
    st.session_state[f'flex_active_{nombre}'] = uv.get('flex_dormitorios') is not None
    st.session_state[vista_key] = True  # No volver a restaurar en este ciclo
```

| Key | Valor inicial | Fuente |
|-----|--------------|--------|
| `vista_valuacion_{nombre}` | `True` | Propia (guard) |
| `retro_active_{nombre}` | `_ultima_valuacion.retro_activo` | Disco |
| `retro_meses_{nombre}` | `_ultima_valuacion.retro_dias` (default 36) | Disco |
| `retro_meses_slider_{nombre}` | `_ultima_valuacion.retro_dias` (default 36) | Disco |
| `flex_active_{nombre}` | `_ultima_valuacion.flex_dormitorios is not None` | Disco |

#### 2d. Cache check (línea 800)
```python
forzar = st.session_state.pop(f'forzar_recalculo_{nombre}', False)
if ya_valuado and not forzar and bool(cache.get('resultado_completo')):
    if cached_fecha_ref == hoy and cached_retro == retro_dias:
        resultado = cache   # ← Usar cache
        usar_cache = True
```

| Condición | Resultado |
|-----------|-----------|
| `forzar == True` | NO usa cache, fuerza recálculo |
| Cache fresco (`fecha_ref==hoy`, `retro_dias==cached`) | Usa cache |
| Cache no coincide | NO usa cache, recalcula |

#### 2e. Flag forzar_recalculo consumido (línea 552)
```python
forzar = st.session_state.pop(f'forzar_recalculo_{p_obj["nombre"]}', False)
```
**Importante:** La key se elimina al leerla. Si hay un rerun sin nuevo `forzar_recalculo`,
el flag no existe y se usa cache.

#### 2f. Exclusión post-motor (línea 919-1049)
```python
comp_excluded_key = f'comp_excluded_{nombre}'
if comp_excluded_key in st.session_state:
    excluded_ids = st.session_state.pop(comp_excluded_key)  # ← Se consume aquí
    from_apply = True
    # Aplicar exclusión: recalcular con subset de comparables
    comps_filtrados = [c for c in comps_orig if _get_comp_id(c) not in excluded_ids]
    preview = calcular_vm2_por_seleccion(comps_filtrados, resultado)
    if preview and not preview.get('fallback'):
        resultado['valor_propiedad_usd'] = round(preview['valor_total'], 0)
        resultado['m2_base_venta'] = preview['vm2']
        ...
    resultado['_comp_excluded'] = excluded_ids
    resultado['_comp_exclusion_applied'] = True
    persistir_valuacion(..., commit=True)
```

#### 2g. Restauración de exclusión desde UV (línea 903)
```python
uv_excl = p_obj.get('_ultima_valuacion', {})
if not resultado.get('_comp_exclusion_applied') and \
   uv_excl.get('_comp_exclusion_applied') and \
   not st.session_state.get(f'comp_excluded_{nombre}', False):
    resultado['_comp_excluded'] = uv_excl.get('_comp_excluded', [])
    resultado['_comp_exclusion_applied'] = True
```
**Propósito:** Al re-entrar a una propiedad que ya tenía exclusión aplicada, restaurarla.

---

### PASO 3: Property Detail View — Interacción del usuario

**Archivo:** `valu.py` → `mostrar_detalle_valu()` (línea 274)

#### 3a. Preview mode (línea 279)
```python
preview_mode = st.session_state.get(f'preview_mode_{nombre}', False)
official_key = f'_official_result_{nombre}'
official_res = st.session_state.get(official_key)
if preview_mode and official_res:
    res = official_res  # Usar resultado oficial congelado
```

#### 3b. Botón Retro ON/OFF (línea 372)
```python
if st.button("🔙 Retro Activado", key=f'retro_btn_{nombre}'):
    st.session_state[retro_key] = True    # retro_active_
    sv = st.session_state.get(f'retro_meses_slider_{nombre}', 36)
    st.session_state[f'retro_meses_{nombre}'] = sv
    st.session_state.pop(f'retro_meses_{nombre}', None)       # Si OFF
    st.session_state.pop(f'retro_meses_slider_{nombre}', None) # Si OFF
    st.session_state.pop(f'comp_excluded_{nombre}', None)     # ← Limpia exclusión!
    st.session_state.pop(f'comp_selection_{nombre}', None)
    st.session_state[f'forzar_recalculo_{nombre}'] = True     # ← Fuerza recálculo
    st.session_state[f'preview_mode_{nombre}'] = True
    st.rerun()
```

| Acción | Keys que cambian |
|--------|-----------------|
| Retro ON | `retro_active_=True`, `retro_meses_=slider`, `forzar_recalculo_=True`, `preview_mode_=True`, `comp_excluded_` eliminado, `comp_selection_` eliminado |
| Retro OFF | `retro_active_=False`, `flex_active_` eliminado, `comp_excluded_` eliminado, `retro_meses_` eliminado, `retro_meses_slider_` eliminado, `comp_selection_` eliminado, `forzar_recalculo_=True`, `preview_mode_=True` |

#### 3c. Checkbox Flex (línea 391)
```python
def _on_flex_change(prop_name=prop_name):
    st.session_state[f'forzar_recalculo_{nombre}'] = True
    st.session_state[f'preview_mode_{nombre}'] = True
    st.session_state.pop(f'comp_selection_{nombre}', None)
    st.session_state.pop(f'comp_excluded_{nombre}', None)  # ← Limpia exclusión!
st.checkbox("🔍 Todos los dormitorios", key=flex_key, on_change=_on_flex_change)
```

#### 3d. Slider Retro (línea 398)
```python
def _on_retro_slider_change(prop_name=prop_name):
    sv = st.session_state.get(f'retro_meses_slider_{nombre}', 36)
    st.session_state[f'retro_meses_{nombre}'] = sv
    st.session_state[f'forzar_recalculo_{nombre}'] = True
    st.session_state[f'preview_mode_{nombre}'] = True
    st.session_state.pop(f'comp_selection_{nombre}', None)
    st.session_state.pop(f'comp_excluded_{nombre}', None)  # ← Limpia exclusión!
st.slider("Meses atrás", 12, 60, key=_slider_key, on_change=_on_retro_slider_change)
```

---

### PASO 4: Tabla de Comparables — render_tabla_comparables()

**Archivo:** `valu_detail_sections.py` → `render_tabla_comparables()` (línea 401)

#### 4a. Init: stored_sel desde res o default (línea 414)
```python
sel_key = f'comp_selection_{nombre}'
comp_ids = [_get_comp_id(c) for c in comparables]
stored_sel = st.session_state.get(sel_key, None)
if stored_sel is None:
    excluded = res.get('_comp_excluded')
    if excluded:
        stored_sel = set(cid for cid in comp_ids if cid not in excluded)
    else:
        stored_sel = set(comp_ids)   # ← Todos seleccionados por defecto
    st.session_state[sel_key] = stored_sel
```

#### 4b. current_sel desde checkboxes vivos (línea 428)
```python
current_sel = set()
for cid in comp_ids:
    chk_key = f'sel_comp_{nombre}_{cid}'
    if chk_key in st.session_state:
        if st.session_state[chk_key]:
            current_sel.add(cid)
    elif cid in stored_sel:
        current_sel.add(cid)
```

#### 4c. Banner + Restablecer (línea 438) — SOLO si hay desmarcados
```python
if len(current_sel) < len(comparables):
    # MUESTRA: banner naranja + botón Restablecer
    # "X/Y comparables activos — N desmarcado(s). Aplicar selección para recalcular."
    if st.button("↩️ Restablecer todos", key=f'reset_comp_sel_{nombre}'):
        for cid in comp_ids:
            st.session_state[f'sel_comp_{nombre}_{cid}'] = True
        st.session_state[f'comp_selection_{nombre}'] = set(comp_ids)
        st.session_state.pop(f'comp_excluded_{nombre}', None)
        st.session_state.pop(f'_comp_interacted_{nombre}', None)
        st.session_state[f'forzar_recalculo_{nombre}'] = True  # SÍ forza recálculo (RO-UI-01)
        st.rerun()
    # ⚠️ setea forzar_recalculo para preview consistente, pero NO persiste
```

**Condición de banner:** `len(current_sel) < len(comparables)` — hay al menos 1 desmarcado.

#### 4d. Checkbox rendering por comparable (línea 462)
```python
for i, c in enumerate(comparables):
    chk_key = f'sel_comp_{nombre}_{comp_id}'
    if chk_key not in st.session_state:
        st.session_state[chk_key] = comp_id in stored_sel
    checked = cols[0].checkbox("", key=chk_key)
    if checked:
        selected_ids.add(comp_id)
    else:
        if comp_id in stored_sel:
            stored_sel.remove(comp_id)
```

#### 4e. Guardar selección actual (línea 502)
```python
st.session_state[sel_key] = selected_ids
```

#### 4f. Preview + is_applied check (línea 504-522)
```python
n_sel = len(selected_ids)
excluded_ids = [cid for cid in all_ids if cid not in selected_ids]
is_applied = set(res.get('_comp_excluded', [])) == set(excluded_ids) \
             and res.get('_comp_exclusion_applied', False)
```

#### 4g. Botón Aplicar Selección (línea 543-569) — SIEMPRE visible si n_sel>=3 y no aplicado
```python
if n_sel < 3:
    st.button("Mínimo 3 comparables", disabled=True)
elif is_applied:
    st.button("✅ Selección Aplicada", disabled=True)
else:  # ← Cambiado de `elif n_sel < len(comparables):` a `else:` (TAREA-120)
    if st.button(f"✅ Aplicar selección ({n_sel}/{len(comparables)})",
                 key=f'apply_comp_sel_{nombre}', type='primary'):
        # Sync slider value before applying
        slider_val = st.session_state.get(f'retro_meses_slider_{nombre}', 36)
        st.session_state[f'retro_meses_{nombre}'] = slider_val
        # Set exclusion + trigger recalculation
        st.session_state[f'comp_excluded_{nombre}'] = excluded
        st.session_state[f'forzar_recalculo_{nombre}'] = True
        st.rerun()
```

| Condición del botón | Qué se muestra |
|--------------------|----------------|
| `n_sel < 3` | "Mínimo 3 comparables" (disabled) |
| `is_applied == True` | "✅ Selección Aplicada" (disabled) |
| `n_sel >= 3` y NO aplicado | "✅ Aplicar selección (N/M)" (primary, activo) |

---

### PASO 5: Ciclo post-Aplicar

```
[Click "Aplicar selección"]
    ├── retro_meses_{nombre} = slider_val (sync)
    ├── comp_excluded_{nombre} = [ids excluidos]
    ├── forzar_recalculo_{nombre} = True
    └── st.rerun()
         │
         ▼
    [mostrar_dashboard()]
         │ Pop forzar_recalculo_ → True → saltar cache
         │ Llamar valuar_con_cache(forzar=True, retro_dias=retro_meses_)
         │    → Motor recalcula
         │ Pop comp_excluded_ → lista de IDs excluidos
         │ Filtrar comparables, calcular_vm2_por_seleccion()
         │ Actualizar resultado con nuevo valor
         │ resultado['_comp_excluded'] = excluded_ids
         │ resultado['_comp_exclusion_applied'] = True
         │ persistir_valuacion(commit=True)  → disco
         │ st.session_state['_official_result_{nombre}'] = deepcopy(resultado)
         │
         ▼
    [mostrar_detalle_valu()]
         │ Header muestra nuevo valor (menos comps)
         │ render_tabla_comparables()
         │    → stored_sel se inicializa desde _comp_excluded
         │    → is_applied = True → botón muestra "✅ Selección Aplicada" (disabled)
```

---

## 3. INVENTARIO COMPLETO DE SESSION STATE KEYS

| Prefijo | Ejemplo | Creado por | Leído por | Limpiado por |
|---------|---------|-----------|-----------|-------------|
| `prop_sel` | `prop_sel` | URL intercept (main) | `mostrar_dashboard()` | `render_actions()` Volver |
| `vista_actual` | `vista_actual` | `main()` | `main()` (routing) | Nav a landing |
| `preview_mode_{n}` | `preview_mode_Casa_1` | Retro/flex/slider change | `mostrar_detalle_valu()` | `_limpiar_estado_propiedad()` |
| `retro_active_{n}` | `retro_active_Casa_1` | Retro btn, re-entry | `mostrar_detalle_valu()` | Retro OFF, `_limpiar_estado_propiedad()` |
| `retro_meses_{n}` | `retro_meses_Casa_1` | Slider change, Apply btn, re-entry | `mostrar_dashboard()` (retro_dias) | Retro OFF, `_limpiar_estado_propiedad()` |
| `retro_meses_slider_{n}` | `retro_meses_slider_Casa_1` | Slider widget, re-entry | Apply btn (line 561) | Retro OFF, `_limpiar_estado_propiedad()` |
| `flex_active_{n}` | `flex_active_Casa_1` | Flex checkbox, re-entry | `mostrar_dashboard()` | Retro OFF (via retro OFF), `_limpiar_estado_propiedad()` |
| `forzar_recalculo_{n}` | `forzar_recalculo_Casa_1` | Retro/flex/slider change, Apply btn | `mostrar_dashboard()` (pop line 552) | Pop al leer, Apply persistence |
| `comp_excluded_{n}` | `comp_excluded_Casa_1` | Apply btn (line 565) | `mostrar_dashboard()` (pop line 936) | Pop al leer, Restablecer, Retro/flex/slider change |
| `comp_selection_{n}` | `comp_selection_Casa_1` | `render_tabla_comparables()` init/update | `render_tabla_comparables()` | Restablecer, Retro/flex/slider change, `_limpiar_estado_propiedad()` |
| `sel_comp_{n}_{id}` | `sel_comp_Casa_1_a1b2c3` | Checkbox widget (auto), Restablecer | Checkbox widget value | Restablecer (todos True), `_limpiar_estado_propiedad()` |
| `vista_valuacion_{n}` | `vista_valuacion_Casa_1` | Re-entry guard (line 751) | Re-entry guard check | `_limpiar_estado_propiedad()` |
| `_official_result_{n}` | `_official_result_Casa_1` | Apply persistence, after motor | `mostrar_detalle_valu()` preview | Clean, `_limpiar_estado_propiedad()` |
| `manual_params_{n}` | `manual_params_Casa_1` | `render_valuacion_manual()` init | `render_valuacion_manual()` | Manual save/delete |
| `manual_preview_{n}` | `manual_preview_Casa_1` | `actualizar_propiedad()` en dashboard | `mostrar_dashboard()` manual_data | `_limpiar_estado_propiedad()` |
| `pendiente_comparables_{n}` | `pendiente_comparables_Casa_1` | Clean action (line 540) | `mostrar_dashboard()`, `mostrar_detalle_valu()` | Applied (line 364, 1059) |
| `act_comparables_{n}` | `act_comparables_Casa_1` | "📊 Comparables" btn (line 363) | `mostrar_dashboard()` (pop line 718) | Pop al leer |
| `clean_comparables_{n}` | `clean_comparables_Casa_1` | "🔄 Limpiar" btn (line 370) | `mostrar_dashboard()` (pop line 514) | Pop al leer |
| `_comp_interacted_{n}` | `_comp_interacted_Casa_1` | Restablecer (reset) | Restablecer (check) | Restablecer |

---

## 4. REGLAS DE CONSISTENCIA (FLUJO)

### F1 — Sync slider antes de aplicar
Cuando se hace clic en "Aplicar selección", se sincroniza `retro_meses_{nombre}`
desde `retro_meses_slider_{nombre}` ANTES de setear `forzar_recalculo`.
Esto asegura que el motor use el valor actual del slider, no un valor stale.

### F2 — Restablecer SÍ forza recálculo preview (RO-UI-01)
"Restablecer todos" reselecciona checkboxes, limpia `comp_excluded`,
y setea `forzar_recalculo=True` para preview consistente del valor natural.
NO persiste ni comitea — el usuario debe hacer clic en "Aplicar selección" para persistir.

### F3 — Retro/flex/slider limpian exclusión + resetean selección (RO-UI-05)
Cualquier cambio en Retro toggle, Flex checkbox o slider de meses
ELIMINA `comp_excluded_{nombre}` y `comp_selection_{nombre}`,
forzando al usuario a re-aplicar la selección si quiere exclusión.
Además, se resetear todos los checkboxes a True (selección completa) y
se muestra un mensaje `st.info()` informando al usuario del cambio.
Esto es intencional: el pool de comparables cambia con estos parámetros.

### F4 — comp_excluded se consume una sola vez
`comp_excluded_{nombre}` se crea en `render_tabla_comparables()` (Apply btn)
y se consume (pop) en `mostrar_dashboard()` post-motor.
Si el motor recalcula sin que esta key exista, no hay exclusión.

### F5 — forzar_recalculo se consume una sola vez
Similar a F4: se crea en varios triggers y se consume (pop) en
`mostrar_dashboard()` línea 552. No persiste entre reruns.

### F6 — is_appiled detecta estado actual vs res
`is_applied` compara `set(res.get('_comp_excluded', []))` con los IDs
actualmente desmarcados. Si coinciden Y `_comp_exclusion_applied == True`,
el botón muestra "✅ Selección Aplicada" (disabled).

### F7 — Header solo cambia con exclusión activa (RO-HEADER-04)
El header solo muestra el valor recalculado del preview cuando hay una
exclusión de comparables activa (`_comp_exclusion_applied=True` en el
resultado o `comp_excluded_` en session_state). Cambios de Retro/Flex/Slider
sin exclusión NO afectan el header — se usa `_official_result_` si existe.

---

## 5. DIAGRAMA DE ESTADOS DE LA TABLA DE COMPARABLES

```
                    ┌──────────────┐
                    │  Sin banner  │  ← len(current_sel) == len(comparables)
                    │  Todos sel.  │      (selección completa)
                    └──────┬───────┘
                           │ Usuario desmarca ≥1 checkbox
                           ▼
                    ┌──────────────┐
                    │ Con banner   │  ← len(current_sel) < len(comparables)
                    │ "X/Y act."   │
                    │ [Restablecer]│  ← Visual-only, NO recalcula
                    │ [Aplicar N/M]│  ← Sí recalcula
                    └──────┬───────┘
               ┌───────────┴───────────┐
               ▼                       ▼
    ┌──────────────────┐   ┌──────────────────┐
    │ Click            │   │ Click            │
    │ [Restablecer]    │   │ [Aplicar N/M]    │
    ├──────────────────┤   ├──────────────────┤
    │ checkboxes=True  │   │ comp_excluded=[] │
    │ comp_excluded ✗  │   │ forzar_recalculo │
    │ NO forzar_recalc │   │ st.rerun()       │
    │ st.rerun()       │   │ → motor recalcula│
    │ → vuelve a       │   │ → resultado      │
    │   "Sin banner"   │   │   actualizado    │
    └──────────────────┘   │ → is_applied=True│
                           │ → "Selec.Aplic." │
                           └──────────────────┘
                                │ Retro/flex/slider
                                │ change → limpia todo
                                ▼
                           ┌──────────────┐
                           │  Sin banner  │
                           │  (fresco)    │
                           └──────────────┘
```

---

## 6. REFERENCIAS CRUZADAS

- **RO-UI-01** (MEMORIA_PROYECTO.md): Restablecer forza recálculo preview (TAREA-132), no persiste
- **RO-UI-02** (MEMORIA_PROYECTO.md): Aplicar Selección visible siempre
- **RO-UI-03** (MEMORIA_PROYECTO.md): UI Guardrails obligatorios
- **STATUS_ACTUAL.md §8**: Comportamiento UI — tabla de botones
- **valu_detail_sections.py**: `render_tabla_comparables()`, `render_valuacion_manual()`
- **valu.py**: `mostrar_dashboard()`, `mostrar_detalle_valu()`
- **tests/test_regression.py**: `test_ui_apply_button_visible_when_all_selected`,
  `test_ui_reset_all_visual_only`, `test_ui_manual_save_hidden_on_no_changes`,
  `test_comparables_banner_hidden_when_full_selection`
