"""
Secciones del detalle de propiedad. Funciones de renderizado UI puras.
Cada funcion recibe datos y renderiza una seccion especifica.
Son llamadas desde mostrar_detalle_valu() en valu.py.
"""
import streamlit as st
import pandas as pd
import json, os
from datetime import datetime
from valu_design import kpi_card, metric_card, hero_price, range_bar, insights_card, property_card
from streamlit.components.v1 import html


def render_actions(prop, guardar_fn):
    """Barra de acciones: Volver, Editar, Revaluar, Eliminar."""
    nombre = prop.get('nombre', '')
    col_back, col_edit, col_recalc, col_delete = st.columns(4)
    with col_back:
        if st.button("<- Volver", type="primary", use_container_width=True):
            st.session_state.prop_sel = None
            st.rerun()
    with col_edit:
        if st.button("Editar", type="primary", use_container_width=True):
            st.session_state[f"edit_{prop['id']}"] = True
    with col_recalc:
        if st.button("Revaluar con comparables", type="primary", use_container_width=True):
            st.session_state[f'forzar_recalculo_{nombre}'] = True
            st.rerun()
    with col_delete:
        if st.button("Eliminar", type="primary", use_container_width=True):
            st.session_state[f"delete_confirm_{prop['id']}"] = True

    # Confirmacion de eliminacion
    if st.session_state.get(f"delete_confirm_{prop['id']}", False):
        st.warning(f"Confirma que desea eliminar la propiedad **{nombre}**?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Si, eliminar", type="primary", use_container_width=True):
                props = cargar_propiedades()
                props = [p for p in props if p.get('id') != prop['id']]
                guardar_propiedades(props)
                # Invalidar cache de valuación
                try:
                    from parsers.valuacion_cache import cargar_cache_valuaciones, guardar_cache_valuaciones
                    cache_v = cargar_cache_valuaciones()
                    cache_v.pop(nombre, None)
                    guardar_cache_valuaciones(cache_v)
                except Exception:
                    pass
                st.session_state.pop(f"delete_confirm_{prop['id']}", None)
                st.session_state.prop_sel = None
                st.rerun()
        with c2:
            if st.button("Cancelar", use_container_width=True):
                st.session_state.pop(f"delete_confirm_{prop['id']}", None)
                st.rerun()

    if st.session_state.get(f"edit_{prop['id']}", False):
        from valu_forms import ui_formulario_propiedad
        # Usamos un key_suffix único para evitar colisiones y habilitamos el geocoding automático reactivo
        new_data = ui_formulario_propiedad(prop_inicial=prop, key_suffix=f"edit_{prop['id']}", show_geocode=True)
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("Guardar Cambios", type="primary", key=f"save_edit_{prop['id']}", use_container_width=True):
                # Por seguridad, si la dirección cambió y no se disparó el callback (ej: clic directo), geocodificamos antes de guardar
                nueva_dir = (new_data.get('direccion') or '').strip()
                vieja_dir = (prop.get('direccion') or '').strip()
                if nueva_dir and nueva_dir != vieja_dir:
                    try:
                        from parsers.geocoder import geocoding_manager
                        geo = geocoding_manager(nueva_dir)
                        if geo and geo.get('lat'):
                            new_data['lat'] = geo['lat']
                            new_data['lon'] = geo['lon']
                    except Exception:
                        pass
                
                guardar_fn(new_data)
                
                # Limpiar el estado de edición
                keys_to_clear = [k for k in st.session_state.keys() if k.endswith(f"_edit_{prop['id']}")]
                for k in keys_to_clear:
                    st.session_state.pop(k, None)
                st.session_state[f"edit_{prop['id']}"] = False
                st.rerun()
                
        with col_b2:
            if st.button("Cancelar", key=f"cancel_edit_{prop['id']}", use_container_width=True):
                # Limpiar el estado de edición al cancelar
                keys_to_clear = [k for k in st.session_state.keys() if k.endswith(f"_edit_{prop['id']}")]
                for k in keys_to_clear:
                    st.session_state.pop(k, None)
                st.session_state[f"edit_{prop['id']}"] = False
                st.rerun()


def render_header(prop, res):
    """Hero con badges, titulo, confianza y precio."""
    nombre = prop.get('nombre', '')
    zona = prop.get('zona', 'Oeste')
    valor_usd = res.get('valor_propiedad_usd', 0)
    dolar = res.get('usdt_ars', 1480)
    m2_base = res.get('m2_base_venta', 0)
    n_comps = res.get('resolution_metadata', {}).get('n_propiedades', 0)

    c_h1, c_h2 = st.columns([3, 2])
    with c_h1:
        dot = '#16A34A' if n_comps >= 15 else '#F59E0B' if n_comps >= 8 else '#DC2626'
        conf = 'Alta confianza' if n_comps >= 15 else 'Confianza media' if n_comps >= 8 else 'Confianza baja'
        st.markdown(f"""
        <div style="background:white;border-radius:16px;padding:28px;box-shadow:0 4px 12px rgba(0,0,0,0.08);height:100%;">
            <div style="margin-bottom:12px;">
                <span class="badge" style="background:#006AFF15;color:#006AFF;">{prop.get('tipo_inmueble','').upper()}</span>
                <span class="badge" style="background:#0D948815;color:#0D9488;margin-left:5px;">{zona.upper()}</span>
                <span class="badge" style="background:#F4F6FB;color:#6B7280;margin-left:5px;">ANO {prop.get('anio_construccion','?')}</span>
            </div>
            <h1 style="color:#1A2B5C;margin:0;font-size:36px;"> {nombre}</h1>
            <p style="color:#6B7280;font-size:16px;">{prop.get('direccion', 'Rosario, Argentina')}</p>
            <div style="display:flex;align-items:center;margin-top:20px;">
                <span style="width:12px;height:12px;border-radius:50%;background:{dot};margin-right:8px;"></span>
                <span style="color:#1A2B5C;font-weight:600;font-size:14px;">{conf}</span>
                <span style="color:#9CA3AF;font-size:14px;margin-left:8px;">({n_comps} comparables)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c_h2:
        st.markdown(hero_price(valor_usd, valor_usd*dolar, dolar, m2_base, n_comps, zona), unsafe_allow_html=True)


def render_rango(res, valor_usd):
    """Rango de 3 escenarios con barra visual."""
    v_cons = res.get('valor_venta_conservador', valor_usd)
    v_opt = res.get('valor_venta_optimista', valor_usd)
    st.markdown(range_bar(v_cons, v_opt, res.get('rango_venta', {}).get('spread_pct', 0)), unsafe_allow_html=True)


def render_metricas(prop, res, valor_usd, dolar):
    """Metricas de inversion: Alquiler, Cap Rate, Plusvalia."""
    alq_ars = res.get('alquiler_estimado_ars', 0)
    alq_r = res.get('alquiler_rango', {})
    alq_min, alq_max = alq_r.get('min', 0), alq_r.get('max', 0)
    cap = res.get('cap_rate', 0)

    if alq_min > 0 and alq_max > 0:
        val_alq = f"${alq_min:,.0f} - ${alq_max:,.0f}"
    else:
        val_alq = f"${alq_ars:,.0f}"

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(metric_card("", "Alquiler Estimado", f"{val_alq} ARS", f"${alq_ars/dolar:,.0f} USD/mes promedio"), unsafe_allow_html=True)
    with m2:
        st.markdown(metric_card("", "Cap Rate Neto", f"{cap*100:.1f}% anual", f"Cierre est: ${valor_usd*0.92:,.0f} USD", border_color="#16A34A"), unsafe_allow_html=True)

    valor_compra = prop.get('valor_compra_usd', 0)
    with m3:
        if valor_compra > 0:
            gain = valor_usd - valor_compra
            pct = (gain/valor_compra)*100
            st.markdown(metric_card("", "Plusvalia", f"+${gain:,.0f} USD", f"{pct:+.1f}% desde compra", border_color="#F59E0B"), unsafe_allow_html=True)
        else:
            st.markdown(metric_card("", "Plusvalia", "-", "Sin datos de compra", border_color="#F59E0B"), unsafe_allow_html=True)


def render_razonamiento(prop, res):
    """Razonamiento narrativo en expander."""
    razonamiento = res.get('razonamiento', '')
    if razonamiento and 'incertidumbresignificativa' in razonamiento.replace(' ', ''):
        from parsers.mercado_inmobiliario import generar_razonamiento_valuacion
        meta = res.get('resolution_metadata', {})
        razonamiento = generar_razonamiento_valuacion(prop, res, meta)
        try:
            from parsers.valuacion_cache import cargar_cache_valuaciones, guardar_cache_valuaciones
            cache = cargar_cache_valuaciones()
            nombre_prop = prop.get('nombre', '')
            if nombre_prop in cache:
                cache[nombre_prop]['resultado_completo']['razonamiento'] = razonamiento
                guardar_cache_valuaciones(cache)
        except:
            pass

    # FASE 3: Age blend info en detalle técnico
    meta = res.get('resolution_metadata', {})
    if meta.get('age_blend_applied'):
        n_age = meta.get('n_age_filtered', 0)
        alpha = meta.get('alpha_age_blend', 0)
        base_age = meta.get('base_age', 0)
        base_all = meta.get('base_all', 0)
        st.info(
            f"**Cluster con edad similar insuficiente (n={n_age}).**  "
            f"Se aplicó blend entre pool etario y pool completo.  "
            f"Alpha edad = {alpha:.2f}.  "
            f"Base edad: ${base_age:.0f}, Base pool completo: ${base_all:.0f}"
        )

    if razonamiento:
        with st.expander("Informe de Valuacion", expanded=False):
            for parrafo in razonamiento.split('\n\n'):
                if parrafo.strip():
                    st.write(parrafo.strip())
    else:
        zona = prop.get('zona', '')
        m2_equiv = res.get('m2_equivalentes', 0)
        m2_base = res.get('m2_base_venta', 0)
        factor = res.get('factor_total', 1.0)
        delta_anti = res.get('delta_anti', 1.0)
        nlp = res.get('nlp_ajuste', 0)
        args = [
            f"Base de mercado establecida en ${m2_base:,.0f} USD/m2 para {zona}.",
            f"Superficie ponderada de {m2_equiv:.1f} m2 (ajustada por tipo de superficie).",
            f"Ajuste por atributos estructurales: {(factor-1)*100:+.1f}%.",
            f"Factor de depreciacion por antiguedad: {(delta_anti-1)*100:+.1f}%.",
        ]
        if nlp != 0:
            args.append(f"Ajuste por descripcion cualitativa (NLP): {nlp*100:+.1f}%.")
        st.markdown(insights_card(f"Analisis de Valor para {prop.get('nombre', '')}", args), unsafe_allow_html=True)


def render_mapa_propiedad(res):
    """Mapa de comparables."""
    mapa_html = res.get('mapa_html', '')
    if mapa_html:
        with st.container(key="mapa_propiedad"):
            html(mapa_html, height=350)
    else:
        st.caption("Mapa no disponible")


def render_tabla_comparables(res, prop_name=None):
    """Tabla de propiedades comparables utilizadas.
    Returns selected indices list, or None if selection not active.
    """
    if res.get('retro_activo'):
        st.caption(f"🔙 Retro activo: ventana de {res.get('total_dias_ventana', 180)} días")
    flex_bedrooms = res.get('flex_bedrooms', 0)
    sujeto_dorms = res.get('sujeto_dormitorios', None)
    if flex_bedrooms > 0 and sujeto_dorms is not None:
        st.caption(f"🔍 Flexible ±{flex_bedrooms} dorm. (base: {sujeto_dorms})")
    comparables = res.get('comparables_venta', [])
    if not comparables:
        st.caption("Sin comparables disponibles")
        return
    rows = []
    for i, c in enumerate(comparables):
        anio_est = c.get('anio_estimado', '')
        ta = c.get('time_adjustment', 1.0)
        vm2_orig = c.get('precio_m2', 0)
        vm2_ajust = c.get('precio_m2_ajustado', vm2_orig)
        retro_badge = ""
        if ta != 1.0:
            retro_badge = " <span style='background:#ff6b35;color:white;font-size:10px;padding:1px 5px;border-radius:8px;font-weight:bold;'>RETRO</span>"
            precio_m2_str = f"<span style='color:#888'>{'${:,.0f}'.format(vm2_orig)}</span> → <span style='color:#ff6b35;font-weight:bold'>{'${:,.0f}'.format(vm2_ajust)}</span>{retro_badge}"
        if flex_bedrooms > 0 and sujeto_dorms is not None and c.get('dormitorios') != sujeto_dorms:
            flex_badge = " <span style='background:#9b59b6;color:white;font-size:10px;padding:1px 5px;border-radius:8px;font-weight:bold;'>FLEX</span>"
            precio_m2_str += flex_badge
        else:
            precio_m2_str = f"<span style='color:#2ecc71;font-weight:bold'>{'${:,.0f}'.format(vm2_orig)}</span>"
        rows.append({
            '#': i+1, 'Precio': f"${c.get('precio', 0):,.0f}",
            'm2': f"{c.get('m2', 0):.0f}",
            'Precio/m2': precio_m2_str,
            'Dorm.': str(c.get('dormitorios', '?')),
            'Tipo': str((c.get('tipo') or '')[:12]) if c.get('tipo') else '',
            'Dirección': ((c.get('direccion_limpia') or c.get('direccion','')) or '')[:35],
            'Ano est.': str(anio_est) if anio_est is not None and anio_est != '' else '',
            'Dist.': f"{c.get('distancia_m', 0):.0f}m" if c.get('distancia_m') else '',
        })
    df = pd.DataFrame(rows)
    st.markdown(df.to_html(escape=False, index=False), unsafe_allow_html=True)

    # Select/deselect individual comparables
    if not prop_name:
        return
    sel_key = f'comp_selection_{prop_name}'
    all_idx = list(range(len(comparables)))
    default_sel = st.session_state.get(sel_key, all_idx)
    with st.popover("🔽 Seleccionar comparables", use_container_width=True):
        selected = []
        for idx, c in enumerate(comparables):
            checked = st.checkbox(
                f"#{idx+1} – {c.get('direccion_limpia') or c.get('direccion','') or '?'} ({c.get('dormitorios','?')}d, ${c.get('precio_m2_ajustado',0):,.0f}/m2)",
                value=idx in default_sel,
                key=f'comp_cb_{prop_name}_{idx}'
            )
            if checked:
                selected.append(idx)
        st.session_state[sel_key] = selected
        n_sel = len(selected)
        st.caption(f"{n_sel}/{len(comparables)} seleccionados")
        if st.button("Aplicar selección", type="primary", use_container_width=True):
            st.session_state[f'comp_selection_apply_{prop_name}'] = True
            st.rerun()

def render_catastro(prop, res, compact=False):
    """Datos catastrales con seleccion de PH y boton de plano.
    compact=True: solo boton toggle (🔍/✕), retorna True si hay datos cargados.
    compact=False: detalle completo (selectbox, columnas, planos).
    """
    nombre = prop.get('nombre', '')
    catastro = res.get('catastro_detalle', None)
    candidatos = catastro.get('candidatos', []) if catastro else []
    imagenes_por_ph = catastro.get('imagenes_disponibles', {}) if catastro else {}

    def _cargar_catastro():
        with st.spinner("Consultando Infomapa..."):
            from parsers.infomapa_api import enriquecer_con_infomapa
            raw = enriquecer_con_infomapa(prop)
            if raw:
                catastro_detalle = {
                    'candidatos': raw.get('candidatos', []),
                    'imagenes_disponibles': raw.get('imagenes_disponibles', {}),
                }
                from parsers.valuacion_cache import cargar_cache_valuaciones, guardar_cache_valuaciones
                cache = cargar_cache_valuaciones()
                if nombre in cache:
                    cache[nombre]['resultado_completo']['catastro_detalle'] = catastro_detalle
                    guardar_cache_valuaciones(cache)
        st.rerun()

    def _limpiar_catastro():
        from parsers.valuacion_cache import cargar_cache_valuaciones, guardar_cache_valuaciones
        cache = cargar_cache_valuaciones()
        if nombre in cache and 'catastro_detalle' in cache[nombre].get('resultado_completo', {}):
            del cache[nombre]['resultado_completo']['catastro_detalle']
            guardar_cache_valuaciones(cache)
        st.rerun()

    if compact:
        key_btn = f"infomapa_catastro_{nombre}"
        if candidatos:
            if st.button("Ocultar", key=key_btn, use_container_width=True, type="primary"):
                _limpiar_catastro()
        else:
            if st.button("Catastro", key=key_btn, use_container_width=True, type="primary"):
                _cargar_catastro()
        return bool(candidatos)

    if not candidatos:
        key_btn = f"infomapa_catastro_{nombre}"
        if st.button("🔍 Consultar datos catastrales / plano", key=key_btn, use_container_width=True):
            _cargar_catastro()
        return

    key_ph = f"ph_sel_{nombre}"
    if key_ph not in st.session_state:
        rec = next((c for c in candidatos if c.get('recomendado')), candidatos[0])
        st.session_state[key_ph] = rec['ph']

    ph_sel = st.session_state[key_ph]

    with st.container(border=True):
        st.markdown("<div style='padding-top:10px;'></div>", unsafe_allow_html=True)
        col_data, col_docs = st.columns([2, 1])
        
        ph_options = {c['ph']: c for c in candidatos}
        
        with col_data:
            # Selector nativo mucho más limpio que N botones apilados
            def _fmt_candidato(ph):
                c = ph_options[ph]
                dir_ = c.get('direccion_nominatim', f'PH {ph}')
                dist = float(c.get('distancia', 0))*111000
                cm = c.get('centena_match', '')
                badge = {"exacta": "📍 Misma cuadra", "coordenadas": "📍 Coordenadas"}.get(cm, '')
                rec = " ⭐ Recomendado" if c.get('recomendado') else ""
                return f"{dir_} — {dist:.0f}m {badge}{rec}"
            ph_sel = st.selectbox(
                "📍 Coincidencia Catastral", 
                options=[c['ph'] for c in candidatos],
                format_func=_fmt_candidato
            )
            
            sel_data = ph_options[ph_sel]
            anio = int(float(sel_data['year'])) if sel_data.get('year') else 'N/A'
            secc = int(float(sel_data['seccion'])) if sel_data.get('seccion') else '-'
            mza = int(float(sel_data['manzana'])) if sel_data.get('manzana') else '-'
            graf = int(float(sel_data['grafico'])) if sel_data.get('grafico') else '-'
            
            # Distribución limpia de los datos con texto grande
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"""
                <div style="background:#f8fafc;border-radius:10px;padding:12px;text-align:center;">
                    <div style="color:#64748b;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">Cuenta (PH)</div>
                    <div style="color:#0f172a;font-size:1.3rem;font-weight:700;">{sel_data['ph']}</div>
                </div>
            """, unsafe_allow_html=True)
            c2.markdown(f"""
                <div style="background:#f8fafc;border-radius:10px;padding:12px;text-align:center;">
                    <div style="color:#64748b;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">Año Const.</div>
                    <div style="color:#0f172a;font-size:1.3rem;font-weight:700;">{anio}</div>
                </div>
            """, unsafe_allow_html=True)
            c3.markdown(f"""
                <div style="background:#f8fafc;border-radius:10px;padding:12px;text-align:center;">
                    <div style="color:#64748b;font-size:0.75rem;text-transform:uppercase;letter-spacing:0.5px;margin-bottom:4px;">Ubicación</div>
                    <div style="color:#0f172a;font-size:1.3rem;font-weight:700;">S {secc} · M {mza} · G {graf}</div>
                </div>
            """, unsafe_allow_html=True)

        with col_docs:
            imagenes = imagenes_por_ph.get(ph_sel, [])
            
            if len(imagenes) > 1:
                idx = st.selectbox("Archivos oficiales", options=range(len(imagenes)),
                                   format_func=lambda i: imagenes[i]['ruta'].rsplit('/', 1)[-1])
                st.markdown(f'<a href="{imagenes[idx]["url"]}" target="_blank" class="detail-btn">Ver Plano PDF</a>', unsafe_allow_html=True)
            elif len(imagenes) == 1:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                st.markdown(f'<a href="{imagenes[0]["url"]}" target="_blank" class="detail-btn">Ver Plano de Mensura</a>', unsafe_allow_html=True)
            else:
                st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                st.markdown('<div class="detail-btn" style="opacity:0.5;cursor:not-allowed;">Plano no disponible</div>', unsafe_allow_html=True)



def render_street_view(prop, compact=True):
    """Boton para abrir Google Street View.
    compact=True: solo link (para fila de botones).
    compact=False: con texto descriptivo.
    """
    lat = prop.get('lat')
    lon = prop.get('lon')
    if not lat or not lon:
        return
    url = f"https://www.google.com/maps/@?api=1&map_action=pano&viewpoint={lat},{lon}"
    if compact:
        st.link_button("Street View", url, type="primary", use_container_width=True)
        return
    c1, c2 = st.columns([3, 1])
    with c1:
        st.markdown("<p style='color:#64748b; font-size:0.95rem; margin-top:4px;'>Explorá la calle, el barrio y la fachada de la propiedad interactuando en 360° desde Google Street View.</p>", unsafe_allow_html=True)
    with c2:
        st.markdown(f'<a href="{url}" target="_blank" class="detail-btn">Abrir Street View</a>', unsafe_allow_html=True)


def render_historial(nombre):
    """Historial de valuaciones con tabla y grafico."""
    from parsers.valuacion_historial import cargar_historial, comparar_valuaciones

    with st.expander("Historial de Valuaciones"):
        historial = cargar_historial(propiedad=nombre, limite=20)
        if not historial:
            st.info("Sin historial disponible. Se generara al primer recalculo.")
            return

        st.markdown(f"**{len(historial)} valuaciones registradas**")
        data_tabla = []
        for reg in historial:
            ts = reg.get('timestamp', '')
            try:
                fecha_fmt = datetime.fromisoformat(ts).strftime("%d/%m/%Y %H:%M")
            except:
                fecha_fmt = ts[:16]
            r_res = reg.get('resultado', {})
            r_mkt = reg.get('snapshot_mercado', {})
            r_razon = reg.get('razon_recalculo', '')
            razones = {'primera_vez': '1 vez', 'propiedad_modificada': 'Datos cambiaron',
                       'scraping_actualizado': 'Nuevo scraping', 'ttl_expirado': 'Actualizacion 24h',
                       'forzado_por_usuario': 'Manual'}
            data_tabla.append({
                'Fecha': fecha_fmt, 'Valor USD': f"${r_res.get('valor_venta', 0):,.0f}",
                'Cap Rate': f"{r_res.get('cap_rate', 0)*100:.1f}%",
                'Base m2': f"${r_mkt.get('m2_base_venta', 0):,.0f}",
                'Dolar': f"${r_mkt.get('dolar_binance', 0):,.0f}",
                'Comps': r_mkt.get('n_comparables_venta', 0),
                'Motivo': razones.get(r_razon, r_razon)
            })
        st.dataframe(pd.DataFrame(data_tabla), hide_index=True, width='stretch')

        if len(historial) > 1:
            try:
                import plotly.graph_objects as go
                fechas, valores, conservadores, optimistas = [], [], [], []
                for reg in reversed(historial):
                    try:
                        fechas.append(datetime.fromisoformat(reg['timestamp']))
                    except:
                        continue
                    r_res = reg.get('resultado', {})
                    valores.append(r_res.get('valor_venta', 0))
                    conservadores.append(r_res.get('valor_conservador', 0))
                    optimistas.append(r_res.get('valor_optimista', 0))
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=fechas, y=optimistas, fill=None, mode='lines',
                                         line_color='rgba(246,195,67,0.3)', name='Optimista'))
                fig.add_trace(go.Scatter(x=fechas, y=conservadores, fill='tonexty', mode='lines',
                                         fillcolor='rgba(52,152,219,0.1)', line_color='rgba(52,152,219,0.5)', name='Rango'))
                fig.add_trace(go.Scatter(x=fechas, y=valores, mode='lines+markers',
                                         line_color='#006AFF', name='Valor'))
                fig.update_layout(title='Evolucion del valor', xaxis_title='Fecha', yaxis_title='USD', height=350)
                st.plotly_chart(fig, width='stretch')
            except Exception as e:
                st.error(f"Error generando grafico: {e}")

        if len(historial) >= 2:
            st.markdown("**Comparar dos valuaciones:**")
            col1, col2 = st.columns(2)
            ids = [r['id'] for r in historial]
            labels = []
            for r in historial:
                try:
                    f = datetime.fromisoformat(r['timestamp']).strftime("%d/%m %H:%M")
                except:
                    f = r['timestamp'][:16]
                labels.append(f"{f} - {r.get('razon_recalculo', '')}")
            with col1:
                idx1 = st.selectbox("Primera valuacion", range(len(historial)), format_func=lambda i: labels[i], key=f"comp1_{nombre}")
            with col2:
                idx2 = st.selectbox("Segunda valuacion", range(len(historial)), index=min(1, len(historial)-1), format_func=lambda i: labels[i], key=f"comp2_{nombre}")
            if idx1 != idx2:
                diff = comparar_valuaciones(nombre, ids[idx1], ids[idx2])
                if diff.get('diferencias'):
                    st.markdown("**Diferencias:**")
                    for campo, vals in diff['diferencias'].items():
                        var, pct = vals['variacion'], vals['pct']
                        st.write(f"{' +' if var > 0 else ' -'} **{campo.replace('_', ' ').capitalize()}:** "
                                 f"${vals['antes']:,.0f} -> ${vals['despues']:,.0f} ({pct:+.1f}%)")


# ─── REPORTE PDF ───
from io import BytesIO
from fpdf import FPDF

def generar_reporte_pdf(prop: dict, res: dict) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=18)

    w = pdf.w - 20

    # Header
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(w, 10, "VALU - Reporte de Valuacion", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(w, 6, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Propiedad
    pdf.set_fill_color(248, 250, 252)
    pdf.rect(10, pdf.get_y(), w, 40, "F")
    y_start = pdf.get_y() + 4
    pdf.set_xy(14, y_start)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(50, 5, "PROPIEDAD")
    pdf.set_xy(14, y_start + 7)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(90, 7, prop.get("nombre", ""))
    pdf.set_xy(14, y_start + 15)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 116, 139)
    direccion = prop.get("direccion", "Rosario, Argentina")
    tipo = prop.get("tipo_inmueble", "")
    zona = prop.get("zona", "")
    pdf.cell(90, 5, f"{direccion}  |  {tipo}  |  {zona}")
    m2 = prop.get("m2_cubiertos", 0)
    dorm = prop.get("dormitorios", 0)
    anio = prop.get("anio_construccion", "?")
    pdf.set_xy(110, y_start + 7)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(30, 6, f"{m2} m2")
    pdf.set_xy(140, y_start + 7)
    pdf.cell(30, 6, f"{dorm} dorm")
    pdf.set_xy(170, y_start + 7)
    pdf.cell(30, 6, f"Ano {anio}")
    pdf.set_y(y_start + 44)
    pdf.ln(4)

    # Valor estimado
    valor_usd = res.get("valor_propiedad_usd", 0)
    v_cons = res.get("valor_venta_conservador", 0)
    v_opt = res.get("valor_venta_optimista", 0)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(w, 5, "VALOR ESTIMADO", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 24)
    pdf.set_text_color(0, 106, 255)
    pdf.cell(w, 12, f"USD {valor_usd:,.0f}", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(w, 5, f"Conservador: USD {v_cons:,.0f}  |  Optimista: USD {v_opt:,.0f}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Metricas clave
    alq = res.get("alquiler_estimado_ars", 0)
    cap = res.get("cap_rate", 0)
    m2_base = res.get("m2_base_venta", 0)
    m2_eq = res.get("m2_equivalentes", 0)
    dolar = res.get("usdt_ars", 1480)

    pdf.set_fill_color(248, 250, 252)
    pdf.rect(10, pdf.get_y(), w, 28, "F")
    y_met = pdf.get_y() + 4
    labels_met = [
        ("Alquiler estimado", f"ARS {alq:,.0f} / USD {alq/dolar:,.0f}"),
        ("Cap Rate", f"{cap*100:.1f}%"),
        ("Base m2", f"USD {m2_base:,.0f}"),
        ("m2 equivalentes", f"{m2_eq:.1f}"),
    ]
    for i, (lbl, val) in enumerate(labels_met):
        x = 14 + (i % 4) * 46
        pdf.set_xy(x, y_met)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(42, 4, lbl)
        pdf.set_xy(x, y_met + 5)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(42, 6, val)
    pdf.set_y(y_met + 32)

    # Factores de ajuste
    meta = res.get("resolution_metadata", {}) or {}
    factor = res.get("factor_total", 1.0)
    dep = res.get("delta_anti", 1.0)
    nlp = res.get("nlp_ajuste", 0)
    calidad = prop.get("calidad_edificio", "Estandar")

    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(w, 5, "FACTORES DE AJUSTE", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    for lbl, val in [
        ("Factor total", f"{(factor-1)*100:+.1f}%"),
        ("Depreciacion", f"{(dep-1)*100:+.1f}%"),
        ("Ajuste NLP", f"{nlp*100:+.1f}%"),
        ("Calidad", calidad),
    ]:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(50, 5, lbl)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(30, 5, val, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Activos adicionales (cocheras + baulera)
    val_activos = res.get("valor_activos", {}) or {}
    if val_activos.get("total", 0) > 0:
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(16, 185, 129)
        pdf.cell(w, 5, "ACTIVOS ADICIONALES", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        for lbl, val in [
            ("Cocheras", f"USD {val_activos.get('cocheras', 0):,.0f}"),
            ("Baulera", f"USD {val_activos.get('baulera', 0):,.0f}"),
            ("Total activos", f"USD {val_activos['total']:,.0f}"),
        ]:
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(50, 5, lbl)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(30, 5, val, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # Comparables
    comps = res.get("comparables_venta", [])
    n_comps = meta.get("n_propiedades", meta.get("n_filtradas", len(comps)))
    precio_m2_prom = 0
    dist_prom = 0
    if comps:
        precio_m2_prom = sum(c.get("precio_m2", 0) or 0 for c in comps) / len(comps)
        dist_prom = sum(c.get("distancia_m", 0) or 0 for c in comps) / len(comps)

    if n_comps >= 15:
        conf = "Alta"
    elif n_comps >= 8:
        conf = "Media"
    else:
        conf = "Baja"

    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(w, 5, "COMPARABLES", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    for lbl, val in [
        ("Cantidad", str(n_comps)),
        ("Precio/m2 prom.", f"USD {precio_m2_prom:,.0f}"),
        ("Distancia prom.", f"{dist_prom:.0f} m"),
        ("Confianza", conf),
    ]:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(50, 5, lbl)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(30, 5, val, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Catastro
    catastro = res.get("catastro_detalle", None)
    candidatos = catastro.get("candidatos", []) if catastro else []
    if candidatos:
        sel = next((c for c in candidatos if c.get("recomendado")), candidatos[0])
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(16, 185, 129)
        pdf.cell(w, 5, "CATASTRO", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        ph = sel.get("ph", "")
        anio_cat = int(float(sel["year"])) if sel.get("year") else "N/A"
        secc = int(float(sel["seccion"])) if sel.get("seccion") else "-"
        mza = int(float(sel["manzana"])) if sel.get("manzana") else "-"
        graf = int(float(sel["grafico"])) if sel.get("grafico") else "-"
        for lbl, val in [
            ("PH", str(ph)),
            ("Ano const.", str(anio_cat)),
            ("Seccion", str(secc)),
            ("Manzana", str(mza)),
            ("Grafico", str(graf)),
        ]:
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(30, 5, lbl)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(20, 5, val, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # Footer metadata
    from parsers.valuacion_cache import CACHE_VERSION
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache_scraping.json")
    fecha_scraping = ""
    if os.path.exists(cache_path):
        mtime = os.path.getmtime(cache_path)
        fecha_scraping = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")

    pdf.ln(4)
    pdf.set_draw_color(226, 232, 240)
    pdf.line(10, pdf.get_y(), w + 10, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(w, 4, f"Version: {CACHE_VERSION}  |  Mercado: {fecha_scraping}", new_x="LMARGIN", new_y="NEXT")
    if meta.get("age_blend_applied"):
        alpha = meta.get("alpha_age_blend", 0)
        n_age = meta.get("n_age_filtered", 0)
        pdf.cell(w, 4, f"Age blend aplicado: alpha={alpha:.2f}, n_edad={n_age}", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


# ─── HELPERS PARA ELIMINACION ───
def _propiedades_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "propiedades.json")

def cargar_propiedades():
    try:
        p = _propiedades_path()
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f).get("propiedades", [])
    except: pass
    return []

def guardar_propiedades(props):
    try:
        path = _propiedades_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump({"propiedades": props}, f, indent=2, ensure_ascii=False)
        from parsers.git_sync import try_sync
        try_sync([path])
        return True
    except Exception as e:
        st.error(f"Error guardando: {e}")
        return False


def render_valuacion_manual(prop, res):
    """
    UI de Valuacion Manual.
    Si res.get('fuente') == 'manual': modo vista con Revaluar.
    Si no: formulario para crear nueva valuacion manual.
    """
    nombre = prop.get('nombre', '')

    if res.get('fuente') == 'manual':
        mp = res.get('manual_params', {})
        st.info("Valuacion generada con parametros manuales.")

        c1, c2, c3 = st.columns(3)
        with c1:
            st.metric("Ancla", mp.get('ancla_id', 'Sin ancla'))
        with c2:
            st.metric("USD/m²", f"${mp.get('usd_m2', 0):,.0f}")
        with c3:
            constr = res.get('constructora', '')
            if constr:
                fconst = res.get('factor_const', 1.0)
                lp = f"({(fconst - 1) * 100:+.0f}%)" if fconst != 1.0 else ""
                st.metric("Constructora", f"{constr} {lp}".strip())
            else:
                st.metric("Constructora", "—")

        c1, c2, c3 = st.columns(3)
        fh_valor = res.get('factor_hedonico_efectivo', mp.get('factor_hedonico', 1.0))
        with c1:
            st.metric("Factor Hedonico", f"{fh_valor:.4f}")
        with c2:
            st.metric("Ajuste %", f"{mp.get('ajuste_pct', 0):+.1f}%")
        with c3:
            st.metric("Incertidumbre %", f"±{mp.get('incertidumbre_pct', 10):.1f}%")

        # Sub-factors breakdown grouped (misma fórmula que calcular_factores)
        sb = res.get('sub_factors_breakdown', {})
        if sb:
            st.markdown("#### Desglose del Factor Hedonico")
            de = sb.get('delta_edificacion', 0.0)
            da = sb.get('delta_amenities', 0.0)
            dn = sb.get('delta_nlp', 0.0)
            danti = sb.get('delta_anti', 0.0)
            sc = sb.get('suma_cruda', 0.0)
            scl = sb.get('suma_clamped', 0.0)
            stot = sb.get('total', 1.0)
            det_amen = sb.get('detalle_amenities', {})
            det_str = ", ".join(det_amen.keys()) if isinstance(det_amen, dict) else str(det_amen)[:30]

            sc1, sc2, sc3, sc4 = st.columns(4)
            with sc1:
                st.metric("Edificación", f"{de:+.4f}")
                st.caption("estado+calidad+piso+vista+balcón+vent+ubic+gas+func+disp")
            with sc2:
                label_am = f"Amenities ({det_str[:30]})" if det_str else "Amenities"
                st.metric(label_am, f"{da:+.4f}")
            with sc3:
                st.metric("NLP", f"{dn:+.4f}")
                st.caption("cocina+preinst AA")
            with sc4:
                st.metric("Depreciación", f"{danti:+.4f}")
                st.caption("antigüedad")
            st.caption(f"Σ cruda = {sc:+.4f} → clamp(±0.40) = {scl:+.4f} → +1 + anti = 1{scl:+.4f}{danti:+.4f} = {1+scl+danti:.4f} → total = {stot:.4f} [{0.70}, {1.35}]")

        # Activos: cocheras y baulera como metricas grandes
        val_act = res.get('valor_activos', {})
        if val_act.get('cocheras', 0) > 0 or val_act.get('baulera', 0) > 0:
            st.markdown("#### Activos adicionales")
            ac1, ac2 = st.columns(2)
            with ac1:
                st.metric("Cocheras", f"${val_act.get('cocheras', 0):,.0f}")
            with ac2:
                st.metric("Baulera", f"${val_act.get('baulera', 0):,.0f}")
            if val_act.get('detalle'):
                st.caption(val_act['detalle'])

        c_btn = st.columns(2)
        with c_btn[0]:
            if st.button("Re-valuar manualmente", use_container_width=True):
                props = cargar_propiedades()
                for i, p in enumerate(props):
                    if p.get('nombre') == nombre:
                        uv = p.setdefault('_ultima_valuacion', {})
                        uv.pop('manual_params', None)
                        ss_key = f"manual_params_{nombre}"
                        st.session_state.pop(ss_key, None)
                        break
                guardar_propiedades(props)
                st.session_state[f'forzar_recalculo_{nombre}'] = True
                st.rerun()
        with c_btn[1]:
            if st.button("Volver a automatico", use_container_width=True, type="primary"):
                props = cargar_propiedades()
                for i, p in enumerate(props):
                    if p.get('nombre') == nombre:
                        uv = p.setdefault('_ultima_valuacion', {})
                        uv['fuente'] = 'auto'
                        uv.pop('manual_params', None)
                        break
                guardar_propiedades(props)
                st.session_state[f'forzar_recalculo_{nombre}'] = True
                st.rerun()
        return

    # ─── CREATE MODE ───
    from parsers.location_engine import cargar_anclas, get_ancla_mas_cercana
    anclas = cargar_anclas()
    ancla_options = {a.get('id', a.get('nombre', '')): a for a in anclas}
    ancla_list = sorted(k for k in ancla_options if k)
    ancla_list = ["Sin Ancla"] + ancla_list
    # Mapa: display name -> id y valor
    ancla_display_map = {}
    for a in anclas:
        aid = a.get('id', a.get('nombre', ''))
        v = a.get('usd_m2', 0)
        ancla_display_map[f"{aid} (${v:,}/m2)"] = {'id': aid, 'usd_m2': v}
    ancla_display_list = sorted(ancla_display_map.keys())
    ancla_display_list = ["Sin Ancla"] + ancla_display_list

    # Detectar ancla: Haversine primero (mas confiable que el campo zona)
    lat = prop.get('lat')
    lon = prop.get('lon')
    ancla_cercana = get_ancla_mas_cercana(lat, lon, anclas) if lat and lon else None
    if ancla_cercana:
        default_ancla_id = ancla_cercana.get('id', '')
        default_usd_m2 = ancla_cercana.get('usd_m2', 0)
    else:
        # Fallback por zona si no hay coordenadas
        zona_prop = (prop.get('zona') or '').lower().strip()
        zona_key = zona_prop.replace(' ', '_').replace('-', '_')
        ancla_por_zona = next((a for a in anclas if a.get('id', '').lower().startswith(zona_key)), None)
        if not ancla_por_zona:
            ancla_por_zona = next((a for a in anclas if zona_key in a.get('id', '').lower()), None)
        default_ancla_id = ancla_por_zona.get('id', '') if ancla_por_zona else 'Sin Ancla'
        default_usd_m2 = ancla_por_zona.get('usd_m2', 0) if ancla_por_zona else 0

    # Factor hedonico default = factores combinados del motor
    default_factor_hedonico = 1.0
    try:
        from parsers.mercado_inmobiliario import calcular_factores
        f_dict = calcular_factores(prop)
        default_factor_hedonico = round(f_dict['total'], 4)
    except:
        pass

    constr_label = ""
    factor_const = 1.0
    try:
        constr_path = "C:/Users/Gustavo/ingresos_familiares_st/constructoras_rosario.json"
        if os.path.exists(constr_path):
            with open(constr_path, "r", encoding="utf-8") as f:
                constr_list = json.load(f)
            constr_prop = prop.get('constructora', '').lower().strip()
            if constr_prop and isinstance(constr_list, list):
                for entry in constr_list:
                    if constr_prop == entry.get('descripcion', '').lower().strip():
                        pct = entry.get('porcentaje', 0)
                        factor_const = 1.0 + pct / 100.0
                        constr_label = f"{entry['descripcion']} ({pct:+.0f}%)"
                        break
    except:
        pass
    if not constr_label and prop.get('constructora'):
        constr_label = prop.get('constructora', '')

    ss_key = f"manual_params_{nombre}"
    if ss_key not in st.session_state:
        st.session_state[ss_key] = {
            'ancla_id': default_ancla_id,
            'usd_m2': default_usd_m2,
            'factor_hedonico': default_factor_hedonico,
            'ajuste_pct': 0.0,
            'incertidumbre_pct': 10.0,
        }

    saved = st.session_state[ss_key]

    st.markdown("#### Parametros de Valuacion Manual")

    col_a, col_b = st.columns(2)
    with col_a:
        # Mostrar ancla con USD/m2 en el dropdown
        saved_display = "Sin Ancla"
        for dk in ancla_display_list:
            if ancla_display_map.get(dk, {}).get('id') == saved['ancla_id']:
                saved_display = dk
                break
        ancla_display_sel = st.selectbox(
            "Ancla de referencia",
            options=ancla_display_list,
            index=ancla_display_list.index(saved_display),
            key=f"manual_ancla_{nombre}",
        )
        ancla_sel = "Sin Ancla"
        if ancla_display_sel in ancla_display_map:
            ancla_sel = ancla_display_map[ancla_display_sel]['id']
    with col_b:
        tiene_ancla = ancla_sel != "Sin Ancla"
        usd_display = saved['usd_m2']
        if tiene_ancla and ancla_sel in ancla_options:
            usd_display = ancla_options[ancla_sel].get('usd_m2', saved['usd_m2'])
        usd_m2_input = st.number_input(
            "USD/m2",
            min_value=0.0, max_value=10000.0,
            value=float(usd_display or 0),
            step=50.0, format="%.0f",
            disabled=tiene_ancla,
            key=f"manual_usd_m2_{nombre}",
        )
        if tiene_ancla:
            st.caption("Valor determinado por el ancla seleccionada. Deseleccione el ancla para editar manualmente.")

    if constr_label:
        st.caption(f"Constructora: {constr_label} (aplicado automaticamente)")

    cant_cocheras = prop.get('cocheras_cantidad', 0)
    tipo_cochera = prop.get('cocheras_tipo', 'cubierta')
    valor_baulera = prop.get('valor_baulera', 0)

    if cant_cocheras > 0:
        coef_tipo = {'cubierta': 1.0, 'semicubierta': 0.7, 'descubierta': 0.4}.get(tipo_cochera, 1.0)
        vbc = prop.get('valor_cochera_base', usd_m2_input * 12)
        dets = []
        for i in range(1, cant_cocheras + 1):
            fu = 1.0 if i == 1 else 0.7 if i == 2 else 0.5
            v = vbc * coef_tipo * fu
            dets.append(f"Cochera {i}: ${v:,.0f} (utilidad {fu*100:.0f}%)")
        st.caption("Cocheras (solo lectura): " + " | ".join(dets))
    if valor_baulera > 0:
        st.caption(f"Baulera (solo lectura): ${valor_baulera:,.0f}")
    if cant_cocheras == 0 and valor_baulera == 0:
        st.caption("Sin activos adicionales (cocheras / baulera)")

    # Sub-factors breakdown (letra chica, referencia)
    try:
        from parsers.mercado_inmobiliario import _calcular_sub_factors_breakdown
        sb_pre = _calcular_sub_factors_breakdown(prop)
        if sb_pre:
            de = sb_pre.get('delta_edificacion', 0.0)
            da = sb_pre.get('delta_amenities', 0.0)
            dn = sb_pre.get('delta_nlp', 0.0)
            danti = sb_pre.get('delta_anti', 0.0)
            stot = sb_pre.get('total', 1.0)
            st.caption(f"Subfactores: Edif {de:+.4f} · Amen {da:+.4f} · NLP {dn:+.4f} · Anti {danti:+.4f} → Total {stot:.4f}")
    except Exception:
        pass

    col_c, col_d, col_e = st.columns(3)
    with col_c:
        fh = st.number_input(
            "Factor Hedonico",
            min_value=0.0, max_value=5.0,
            value=float(saved['factor_hedonico']),
            step=0.05, format="%.4f",
            key=f"manual_fh_{nombre}",
        )
    with col_d:
        aj = st.number_input(
            "Ajuste %",
            min_value=-100.0, max_value=500.0,
            value=float(saved['ajuste_pct']),
            step=1.0, format="%.1f",
            key=f"manual_aj_{nombre}",
        )
    with col_e:
        inc = st.number_input(
            "Incertidumbre (±%)",
            min_value=0.0, max_value=100.0,
            value=float(saved['incertidumbre_pct']),
            step=1.0, format="%.0f",
            key=f"manual_inc_{nombre}",
        )

    # Preview
    from parsers.mercado_inmobiliario import calcular_m2_equivalentes
    m2_eq = calcular_m2_equivalentes(prop)
    fh_eff = fh if fh != 0 else 1.0
    pre_sub = m2_eq * usd_m2_input * fh_eff * factor_const
    pre_act = 0
    if cant_cocheras > 0:
        coef_tipo = {'cubierta': 1.0, 'semicubierta': 0.7, 'descubierta': 0.4}.get(tipo_cochera, 1.0)
        vbc = prop.get('valor_cochera_base', usd_m2_input * 12)
        for i in range(1, cant_cocheras + 1):
            fu = 1.0 if i == 1 else 0.7 if i == 2 else 0.5
            pre_act += vbc * coef_tipo * fu
    pre_act += valor_baulera
    pre_total = pre_sub + pre_act
    pre_final = pre_total * (1 + aj / 100.0)

    if st.button("Calcular y Guardar Valuacion Manual", type="primary", use_container_width=True):
        if usd_m2_input <= 0:
            st.error("Ingrese un valor de USD/m2 valido.")
            return
        manual_params = {
            'ancla_id': ancla_sel,
            'usd_m2': usd_m2_input,
            'factor_hedonico': fh,
            'ajuste_pct': aj,
            'incertidumbre_pct': inc,
        }
        from parsers.mercado_inmobiliario import generar_resultado_manual
        resultado_manual = generar_resultado_manual(prop, manual_params)

        from parsers.valuacion_cache import persistir_valuacion, cargar_cache_valuaciones
        cache = cargar_cache_valuaciones()
        persistir_valuacion(nombre, prop, resultado_manual, cache)

        props = cargar_propiedades()
        for i, p in enumerate(props):
            if p.get('nombre') == nombre:
                uv = p.setdefault('_ultima_valuacion', {})
                uv['fuente'] = 'manual'
                uv['manual_params'] = manual_params
                break
        guardar_propiedades(props)

        st.success(f"Valuacion manual guardada: ${resultado_manual['valor_propiedad_usd']:,.0f} USD")
        st.rerun()
