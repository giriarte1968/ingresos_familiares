# TAREA-039 — Retro: Expansión de comparables con Ct + Admin UI curva — Riesgo ALTO

## CONTEXTO

Actualmente los comparables se seleccionan con ventana fija de 365 días y **ningún ajuste temporal** (excepto Puerto Norte con -4.5%/año lineal). La curva Ct completa existe en `scripts/generar_anclas_grid.py` pero no se usa en la valuación normal. El usuario quiere:

1. Ventana natural de **180 días** (6 meses) — propiedades más frescas
2. Más allá de 6 meses: ajuste **Ct** basado en la curva de mercado + factores COCIR
3. Botón "Retro" en UI que expande la ventana trayendo propiedades históricas con Ct ajustado
4. Toda la curva Ct + factores en config, editables desde Admin UI con tabla y gráfico Plotly
5. Factores COCIR con fecha de vigencia y registro histórico

## REGLA DE ORO

- `pytest tests/test_regression.py` pasa después de cada paso
- `python scripts/auto_validate.py` pasa después de cada paso
- La ventana natural default es 180 días (no 365). Los tests existentes deben actualizarse si dependen de 365d.
- Ct se aplica SOLO a comparables con `date_created > 180 días`. Comps ≤180d quedan sin ajuste (time_adjustment=1.0).
- Los factores COCIR (`usado=1.12`, `nuevo=0.95`) tienen `fecha_vigencia` en config. Al guardar nuevos factores, se registran en `config/ct_factors_history.json`.
- La TABLA_CT es editable en Admin UI con botón "Restaurar default".
- Sin Retro: límite 30 comps. Con Retro: límite 60 comps (30 naturales + 30 retro).
- `scripts/generar_anclas_grid.py` debe seguir funcionando idéntico (importa desde el nuevo módulo compartido).

## ALCANCE

| Archivo | Cambio |
|---------|--------|
| `config/anclas_config.json` | Agregar `ct_table`, `natural_window_dias`, `retro_default_meses`, `ct_factors.fecha_vigencia` |
| `parsers/time_adjustment.py` | **Nuevo** — módulo compartido Ct (interpolar, ct_segmento, meses_desde, es_nuevo, calcular_ct) |
| `scripts/generar_anclas_grid.py` | Refactor: importar desde `time_adjustment`, eliminar definiciones duplicadas |
| `parsers/mercado_inmobiliario.py` | `aplicar_filtro_fecha` default 180d; `obtener_mediana_cluster_v2` acepta `retro_dias`, aplica Ct a >180d, límite 30/60 |
| `valu_detail_sections.py` | Botón Retro toggle + slider 12-60 meses + badge "🔙 RETRO" en tabla |
| `valu.py` | Pasar `retro_dias` desde session_state; Admin UI pestaña "Ct / Ajuste Temporal" |
| `config/ct_factors_history.json` | **Nuevo** — registro histórico de factores guardados |
| `docs/ALGORITMOS.md` | Actualizar sección Ct con ventana 180d + Retro |
| `docs/BITACORA_AGENTES.md` | Registrar TAREA-039 |
| `.opencode/plans/TAREAS_INDEX.md` | Agregar entrada TAREA-039 |

---

### PASO 1: Config + módulo compartido `time_adjustment.py`

**Archivo:** `config/anclas_config.json`

**1.1** Agregar al config bajo `generator`:
```json
"natural_window_dias": 180,
"retro_default_meses": 36,
"ct_table": [
  [0, 1.000], [3, 1.011], [6, 1.033], [12, 1.105],
  [18, 1.207], [24, 1.235], [30, 1.267], [36, 1.254],
  [42, 1.203], [48, 1.173], [54, 1.152], [60, 1.131],
  [66, 1.105], [72, 1.067], [78, 1.027], [83, 1.000]
],
"ct_factors": {
  "usado": 1.12,
  "nuevo": 0.95,
  "fecha_vigencia": "2026-01"
}
```

**Archivo:** `parsers/time_adjustment.py` — nuevo

**1.2** Módulo con funciones compartidas que leen desde `load_anclas_config()`:

```python
def get_ct_table():       # desde config.generator.ct_table
def get_ct_factors():     # desde config.generator.ct_factors
def interpolar(tabla, x):
def ct_segmento(meses, factor):
def meses_desde(fecha_str, fecha_ref=None):
def es_nuevo(prop):
def calcular_ct(meses, es_nuevo=False):  # usa get_ct_table + get_ct_factors
```

`calcular_ct` implementa:
```python
def calcular_ct(meses, es_nuevo=False):
    tabla = get_ct_table()
    factores = get_ct_factors()
    ct_base = interpolar(tabla, meses)
    factor = factores['nuevo'] if es_nuevo else factores['usado']
    return 1.0 + (ct_base - 1.0) * factor
```

**COMMIT:** `"TAREA-039-paso1: config Ct + parsers/time_adjustment.py"`

**VERIFICAR:** `python -c "from parsers.time_adjustment import calcular_ct, interpolar; print('Ct 24m usado:', calcular_ct(24, False)); print('Ct 24m nuevo:', calcular_ct(24, True))"`

---

### PASO 2: Refactor `scripts/generar_anclas_grid.py`

**Archivo:** `scripts/generar_anclas_grid.py`

**2.1** Reemplazar definiciones locales de `TABLA_CT`, `FACTOR_USADO`, `FACTOR_NUEVO`, `interpolar`, `ct_segmento`, `es_nuevo`, `meses_desde` por imports desde `parsers.time_adjustment`.

**2.2** Eliminar las líneas duplicadas (mantener `FECHA_REF` que es local del script).

**2.3** Verificar que el output del script es idéntico al anterior (mismas anclas, mismo Ct dual).

**COMMIT:** `"TAREA-039-paso2: refactor generar_anclas_grid.py usa time_adjustment"`

**VERIFICAR:** `python scripts/generar_anclas_grid.py --grid-size 400 --min-props 5` → 322 anclas, misma distribución que antes

---

### PASO 3: Ventana 180d + Retro en `obtener_mediana_cluster_v2`

**Archivo:** `parsers/mercado_inmobiliario.py`

**3.1** Modificar `aplicar_filtro_fecha`:
```python
def aplicar_filtro_fecha(props, fecha_ref, dias=None):
    if dias is None:
        cfg = load_anclas_config()
        dias = cfg.get('generator', {}).get('natural_window_dias', 180)
    return filtrar_por_fecha(props, fecha_ref, dias=dias)
```

**3.2** Modificar signature de `obtener_mediana_cluster_v2`:
```python
def obtener_mediana_cluster_v2(zona, dormitorios, operacion='venta', lat_ref=None, lon_ref=None,
                               fecha_ref=None, anio_sujeto=None, tipo_inmueble=None,
                               cache_scraping=None, retro_dias=0):
```

**3.3** Al inicio de la función, calcular la ventana total:
```python
cfg = load_anclas_config()
natural_dias = cfg.get('generator', {}).get('natural_window_dias', 180)
total_dias = natural_dias + retro_dias * 30 if retro_dias > 0 else natural_dias
# Usar total_dias en lugar de 365 para el filtro de fecha
```

**3.4** Después del filtro de fecha y antes de barreras/dedup, agregar paso de Ct:
```python
from parsers.time_adjustment import calcular_ct, meses_desde, es_nuevo
for p in props:
    dc = p.get('date_created', '')
    if not dc: continue
    try:
        m = meses_desde(dc, fecha_ref)
        if m > natural_dias / 30:  # > 6 meses
            p['_time_adjustment'] = calcular_ct(m, es_nuevo(p))
    except:
        pass
```

**3.5** Límite de comparables:
```python
max_comps = 60 if retro_dias > 0 else 30
comparables_reales = [...] for p in pool_final[:max_comps]
```

**3.6** Agregar `retro_activo` al meta retorno:
```python
meta_venta['retro_activo'] = bool(retro_dias)
meta_venta['total_dias_ventana'] = total_dias
```

**COMMIT:** `"TAREA-039-paso3: ventana 180d + retro_dias + Ct en obtener_mediana_cluster_v2"`

**VERIFICAR:** `pytest tests/test_regression.py` (pueden requerir ajuste de valores si algún test esperaba ventana 365d)

---

### PASO 4: UI — Botón Retro en Comparables

**Archivo:** `valu_detail_sections.py`

**4.1** Dentro de la sección de comparables (antes de expander "📊 Comparables" o dentro), agregar:
```python
prop_id = prop.get('id', '')
retro_key = f'retro_active_{prop_id}'
retro_active = st.session_state.get(retro_key, False)

col_btn, col_status, col_slider = st.columns([1.5, 1, 2])
with col_btn:
    label = "🔙 Retro activo" if retro_active else "🔙 Retro"
    if st.button(label, type="primary" if retro_active else "secondary", use_container_width=True):
        st.session_state[retro_key] = not retro_active
        st.session_state[f'forzar_recalculo_{prop["nombre"]}'] = True
        st.rerun()
with col_status:
    if retro_active:
        meses = st.session_state.get(f'retro_meses_{prop_id}', 36)
        st.caption(f"📆 +{meses} meses")
with col_slider:
    if retro_active:
        meses = st.slider("Meses atrás", 12, 60, st.session_state.get(f'retro_meses_{prop_id}', 36),
                          key=f'retro_meses_{prop_id}')
        st.session_state[f'retro_meses_{prop_id}'] = meses
```

**4.2** En `render_tabla_comparables`, modificar el badge de precio/m²: si `time_adjustment != 1.0`:
- Mostrar badge `🔙 RETRO` junto al precio ajustado
- Color naranja para el precio ajustado, gris para el original
- Mantener el formato actual de flecha para ajuste

**4.3** Si `res.get('retro_activo')`, mostrar caption: `"🔙 Retro activo: ventana de {res.get('total_dias_ventana')} días"`

**COMMIT:** `"TAREA-039-paso4: UI boton Retro + slider + badge en comparables"`

**VERIFICAR:** Revisar visualmente en `streamlit run valu.py` que el botón, slider y badge aparecen correctamente.

---

### PASO 5: `valu.py` — pasar retro_dias + Admin UI Ct

**Archivo:** `valu.py`

**5.1** En el bloque donde se llama la valuación, leer retro desde session_state:
```python
retro_dias = 0
prop_id = p_obj.get('id', '')
if st.session_state.get(f'retro_active_{prop_id}', False):
    meses = st.session_state.get(f'retro_meses_{prop_id}', 36)
    retro_dias = meses * 30  # aprox días por mes

# Pasar retro_dias al engine (se agrega como parámetro donde corresponda)
```

**5.2** Admin UI — Nueva pestaña "Ct / Ajuste Temporal":

```python
# Dentro de la sección admin, agregar pestaña
with tab_ct:
    # 1. Tabla Ct editable
    st.markdown("### 📊 Tabla Ct")
    cfg = load_anclas_config()
    ct_table = cfg.get('generator', {}).get('ct_table', [])
    df_ct = pd.DataFrame(ct_table, columns=['Meses', 'Ct_base'])
    edited_ct = st.data_editor(df_ct, num_rows="dynamic", key="ct_table_editor")
    if st.button("Restaurar default"):
        # restaurar tabla original
        pass
    
    # 2. Gráfico Plotly
    st.markdown("### 📈 Tendencia histórica")
    import plotly.graph_objects as go
    fig = go.Figure()
    # Ct_base, Ct_usado, Ct_nuevo
    meses_range = list(range(0, 97))
    ct_base_vals = [interpolar(ct_table, m) for m in meses_range]
    ct_usado_vals = [1.0 + (b-1.0)*1.12 for b in ct_base_vals]
    ct_nuevo_vals = [1.0 + (b-1.0)*0.95 for b in ct_base_vals]
    fig.add_trace(go.Scatter(x=meses_range, y=ct_base_vals, name='Ct base'))
    fig.add_trace(go.Scatter(x=meses_range, y=ct_usado_vals, name='Ct usado (×1.12)'))
    fig.add_trace(go.Scatter(x=meses_range, y=ct_nuevo_vals, name='Ct nuevo (×0.95)'))
    # Líneas verticales
    fig.add_vline(x=6, line_dash="dash", line_color="gray", annotation_text="6m (ventana natural)")
    fig.add_vline(x=36, line_dash="dash", line_color="orange", annotation_text="36m (retro default)")
    st.plotly_chart(fig, use_container_width=True)
    
    # 3. Factores COCIR con fecha vigencia
    st.markdown("### ⚙️ Factores Bassini/COCIR")
    factors = cfg.get('generator', {}).get('ct_factors', {})
    f_usado = st.number_input("Factor usado", 0.5, 2.0, factors.get('usado', 1.12), 0.01)
    f_nuevo = st.number_input("Factor nuevo", 0.5, 2.0, factors.get('nuevo', 0.95), 0.01)
    f_fecha = st.text_input("Fecha vigencia", factors.get('fecha_vigencia', '2026-01'))
    
    # 4. Parámetros ventana
    st.markdown("### 🪟 Parámetros de ventana")
    natural_dias = st.number_input("Ventana natural (días)", 30, 730, 
                                    cfg.get('generator', {}).get('natural_window_dias', 180))
    retro_meses = st.number_input("Retro default (meses)", 6, 120,
                                   cfg.get('generator', {}).get('retro_default_meses', 36))
    
    if st.button("💾 Guardar configuración Ct", type="primary"):
        # Guardar histórico de factores si cambiaron
        old_factors = cfg['generator']['ct_factors']
        if (old_factors['usado'] != f_usado or old_factors['nuevo'] != f_nuevo):
            history_path = os.path.join(os.path.dirname(__file__), 'config', 'ct_factors_history.json')
            history = []
            if os.path.exists(history_path):
                with open(history_path) as f: history = json.load(f)
            history.append({
                'usado': f_usado, 'nuevo': f_nuevo,
                'fecha_vigencia': f_fecha,
                'guardado': datetime.now().isoformat()
            })
            with open(history_path, 'w') as f: json.dump(history, f, indent=2)
        
        # Actualizar config
        cfg['generator']['ct_table'] = edited_ct.values.tolist()
        cfg['generator']['ct_factors'] = {'usado': f_usado, 'nuevo': f_nuevo, 'fecha_vigencia': f_fecha}
        cfg['generator']['natural_window_dias'] = int(natural_dias)
        cfg['generator']['retro_default_meses'] = int(retro_meses)
        save_anclas_config(cfg)
        bump_cache_version()
        st.success("Configuración Ct guardada. Caché invalidada.")
        st.rerun()
```

**COMMIT:** `"TAREA-039-paso5: pasar retro_dias desde UI + Admin pestaña Ct"`

**VERIFICAR:** `python scripts/auto_validate.py`

---

### PASO 6: Actualizar documentación

**6.1** `docs/ALGORITMOS.md`: agregar sección "8. Ajuste Temporal (Ct) y Retro":
- Ventana natural 180 días
- Ct: curva de mercado + factores COCIR (usado ×1.12, nuevo ×0.95)
- Retro: expansión opcional con slider 12-60 meses
- Fórmula: `precio_ajustado = precio_original × (1.0 + (Ct_base(meses) - 1.0) × factor_segmento)`

**6.2** `docs/BITACORA_AGENTES.md`: registrar TAREA-039

**6.3** `.opencode/plans/TAREAS_INDEX.md`: entrada TAREA-039

**COMMIT:** `"TAREA-039-paso6: docs Ct + Retro"`

---

## VALIDACION FINAL

```
☐ auto_validate.py OK
☐ pytest test_regression.py (39/39)
☐ python scripts/generar_anclas_grid.py produce mismas 322 anclas
☐ Sin Retro: 180d window, máx 30 comps
☐ Con Retro: 180+retro_dias window, máx 60 comps, badge RETRO en >180d
☐ Tabla Ct editable en Admin UI
☐ Gráfico Plotly con 3 trazos + líneas verticales
☐ Factores COCIR se guardan en config + histórico
☐ Botón Retro toggle on/off + slider 12-60 meses
```

## DOCS A ACTUALIZAR

- `docs/ALGORITMOS.md`: sección 8 Ct + Retro
- `docs/BITACORA_AGENTES.md`: registro TAREA-039
- `.opencode/plans/TAREAS_INDEX.md`: entrada TAREA-039

## ARCHIVO DE PLAN

El plan se guarda permanentemente en `.opencode/plans/TAREA-039.md`.
NO se elimina al ejecutar.

## ENTREGABLES

- `config/anclas_config.json` actualizado con ct_table, natural_window_dias, retro_default_meses, fecha_vigencia
- `parsers/time_adjustment.py` (nuevo) — módulo Ct compartido
- `scripts/generar_anclas_grid.py` refactorizado (importa desde time_adjustment)
- `parsers/mercado_inmobiliario.py` — ventana 180d, retro_dias, Ct para >180d, límite 30/60
- `valu_detail_sections.py` — botón Retro + slider + badge RETRO
- `valu.py` — pasar retro_dias + Admin UI pestaña Ct con tabla, gráfico Plotly, factores editables
- `config/ct_factors_history.json` — histórico de cambios de factores
- `pytest` + `auto_validate` pasando
