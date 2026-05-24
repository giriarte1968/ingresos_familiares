# TAREA: TAREA-007 — Botones homogéneos en fila + toggle catastro — Riesgo BAJO

### CONTEXTO

Dentro del expander "⚡ Acciones" del detalle de propiedad, los 3 elementos tienen estilos distintos:
- **Reporte PDF**: `st.download_button` (Streamlit nativo, verde)
- **Catastro**: `st.button` con texto largo (verde)
- **Street View**: `<a class="detail-btn">` (verde oscuro HTML)

El usuario quiere:
1. Los 3 como botones del mismo estilo visual en fila (`st.columns(3)`)
2. Toggle catastro: el botón "🔍 Catastro" pasa a "✕ Ocultar" cuando hay datos cargados, y al clickearlo limpia el cache y vuelve al estado inicial

### REGLA DE ORO

- Sin cambios en lógica de valuación, profiling ni ledgers
- `render_catastro(compact=True)` retorna `True` si hay datos cargados
- `render_catastro(compact=False)` muestra el detalle completo (sin cambios)
- `render_street_view(compact=True)` solo el link, sin texto descriptivo
- Tests 39/39 deben pasar

### ALCANCE

| Archivo | Cambio |
|---------|--------|
| `valu_detail_sections.py` | `render_catastro` admite `compact=True` (solo botón toggle). `render_street_view` admite `compact=True` (solo link). |
| `valu.py` | Reemplazar bloque vertical por `st.columns(3)` + detalle catastro condicional |

---

### PASO 1: Modificar `render_catastro` — modo compact + toggle

**Archivo:** `valu_detail_sections.py` — `render_catastro()` (línea 244)

**1.1** Agregar parámetro `compact=False`. Cuando `compact=True`:
- Si no hay candidatos: muestra botón "🔍 Catastro" con lógica de carga, retorna `False`
- Si hay candidatos: muestra botón "✕ Ocultar" que limpia cache y rerunea, retorna `True`
- NO renderiza el detalle (selectbox, columnas, planos)

Cuando `compact=False`: comportamiento actual (detalle completo), sin retorno.

```python
def render_catastro(prop, res, compact=False):
    nombre = prop.get('nombre', '')
    catastro = res.get('catastro_detalle', None)
    candidatos = catastro.get('candidatos', []) if catastro else []

    if compact:
        if not candidatos:
            key_btn = f"infomapa_catastro_{nombre}"
            if st.button("🔍 Catastro", key=key_btn, use_container_width=True):
                ...  # misma lógica de carga
                st.rerun()
        else:
            key_btn = f"infomapa_catastro_{nombre}"
            if st.button("✕ Ocultar", key=key_btn, use_container_width=True):
                ...  # limpiar cache
                st.rerun()
        return bool(candidatos)

    # ─── modo detalle (compact=False) ───
    ... # resto del código actual desde línea 246 en adelante
```

**1.2** Ajustar el retorno: cuando `compact=True`, retorna `bool(candidatos)`. Cuando `compact=False`, no retorna nada (None).

### PASO 2: Modificar `render_street_view` — modo compact

**Archivo:** `valu_detail_sections.py` — `render_street_view()` (línea 342)

**2.1** Agregar parámetro `compact=True`. Cuando `compact=True`:
- Solo renderiza el link `<a class="detail-btn">` (sin columna descriptiva, sin `st.columns`)

```python
def render_street_view(prop, compact=True):
    lat = prop.get('lat')
    lon = prop.get('lon')
    if not lat or not lon:
        return
    url = f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lon}"
    if compact:
        st.markdown(f'<a href="{url}" target="_blank" class="detail-btn">🏙️ Street View</a>', unsafe_allow_html=True)
        return
    ... # modo expandido actual (con descripción)
```

### PASO 3: Reemplazar bloque "⚡ Acciones" en `mostrar_detalle_valu`

**Archivo:** `valu.py` — `mostrar_detalle_valu()` (líneas 276-300)

**3.1** Reemplazar el bloque actual por:

```python
    # ─── ⚡ Acciones ───
    with st.expander("⚡ Acciones", expanded=False):
        with profile_block("generar_reporte_pdf", prop):
            pdf_bytes = generar_reporte_pdf(prop, res)

        col1, col2, col3 = st.columns(3)
        with col1:
            hay_catastro = render_catastro(prop, res, compact=True)
        with col2:
            render_street_view(prop, compact=True)
        with col3:
            with profile_block("download_button", prop):
                st.download_button(
                    "📄 Reporte PDF",
                    data=pdf_bytes,
                    file_name=f"valuacion_{prop.get('nombre','propiedad').replace(' ','_')}.pdf",
                    mime="application/pdf",
                    type="primary",
                    use_container_width=True,
                )
        _dl.mark("after_pdf_download")

        if hay_catastro:
            st.markdown("<br>", unsafe_allow_html=True)
            with profile_block("render_catastro_detalle", prop):
                render_catastro(prop, res, compact=False)
            _dl.mark("after_render_catastro")
    _dl.mark("after_section_acciones")
```

**COMMIT:** `"feat: Botones homogéneos en fila + toggle catastro en Acciones"`

**VERIFICAR:** `python scripts/auto_validate.py`

---

### VALIDACION FINAL

```
☐ auto_validate.py pasa (39 tests + perf check)
☐ Visual: 3 botones iguales en fila (🔍/✕, 🏙️, 📄)
☐ Toggle catastro: 🔍 → carga datos → ✕ → limpia → 🔍
☐ Street View abre link externo correctamente
☐ PDF descarga correctamente
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md`
- `.opencode/plans/TAREAS_INDEX.md` (agregar TAREA-007)

### ARCHIVO DE PLAN

`.opencode/plans/TAREA-007.md`
