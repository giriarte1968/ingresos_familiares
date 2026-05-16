"""
Secciones del detalle de propiedad. Funciones de renderizado UI puras.
Cada funcion recibe datos y renderiza una seccion especifica.
Son llamadas desde mostrar_detalle_valu() en valu.py.
"""
import streamlit as st
import pandas as pd
from datetime import datetime
from valu_design import kpi_card, metric_card, hero_price, range_bar, insights_card, property_card
from streamlit.components.v1 import html


def render_actions(prop, guardar_fn):
    """Barra de acciones: Volver, Editar, Revaluar."""
    nombre = prop.get('nombre', '')
    col_back, col_edit, col_recalc = st.columns(3)
    with col_back:
        if st.button("<- Volver", width='stretch'):
            st.session_state.prop_sel = None
            st.rerun()
    with col_edit:
        if st.button("Editar", width='stretch'):
            st.session_state[f"edit_{prop['id']}"] = True
    with col_recalc:
        if st.button("Revaluar", width='stretch'):
            st.session_state[f'forzar_recalculo_{nombre}'] = True
            st.rerun()

    if st.session_state.get(f"edit_{prop['id']}", False):
        with st.form(f"f_edit_{prop['id']}"):
            from valu_forms import ui_formulario_propiedad
            new_data = ui_formulario_propiedad(prop_inicial=prop, key_suffix="edit", show_geocode=False)
            if st.form_submit_button("Guardar Cambios", type="primary"):
                guardar_fn(new_data)
                st.session_state[f"edit_{prop['id']}"] = False
                st.rerun()
            if st.form_submit_button("Cancelar"):
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


def render_mapa_y_comparables(res):
    """Mapa + tabla desplegable de comparables."""
    st.markdown("---")
    mapa_html = res.get('mapa_html', '')
    if mapa_html:
        html(mapa_html, height=350)
        n_comps_reales = len(res.get('comparables_venta', []))
        st.caption(f" {n_comps_reales} comparables de venta")
    else:
        st.caption(" Mapa no disponible")

    comparables = res.get('comparables_venta', [])
    if comparables:
        with st.expander(f" {len(comparables)} propiedades comparables utilizadas"):
            rows = []
            for i, c in enumerate(comparables):
                rows.append({
                    '#': i+1, 'Precio': f"${c.get('precio', 0):,.0f}",
                    'm2': f"{c.get('m2', 0):.0f}", 'Precio/m2': f"${c.get('precio_m2', 0):,.0f}",
                    'Dorm.': c.get('dormitorios', '?'), 'Tipo': (c.get('tipo') or '')[:12] if c.get('tipo') else '',
                    'Ano est.': c.get('anio_estimado', '') if c.get('anio_estimado') else '',
                    'Dist.': f"{c.get('distancia_m', 0):.0f}m" if c.get('distancia_m') else '',
                })
            st.dataframe(pd.DataFrame(rows), width='stretch', hide_index=True)


def render_catastro(prop, res):
    """Datos catastrales con seleccion de PH y boton de plano."""
    nombre = prop.get('nombre', '')
    catastro = res.get('catastro_detalle', None)
    candidatos = catastro.get('candidatos', []) if catastro else []
    imagenes_por_ph = catastro.get('imagenes_disponibles', {}) if catastro else {}

    st.markdown("---")
    st.subheader("Datos Catastrales")

    if not candidatos:
        with st.container(border=True):
            st.info("Sin datos catastrales para esta ubicacion")
        return

    key_ph = f"ph_sel_{nombre}"
    if key_ph not in st.session_state:
        rec = next((c for c in candidatos if c.get('recomendado')), candidatos[0])
        st.session_state[key_ph] = rec['ph']

    ph_sel = st.session_state[key_ph]

    with st.container(border=True):
        col_botones, col_info = st.columns(2)
        with col_botones:
            st.write("**Candidatos disponibles:**")
            for c in candidatos:
                is_sel = c['ph'] == ph_sel
                label = c.get('direccion_nominatim', 'PH ' + str(c['ph']))
                d = float(c.get('distancia', 0)) * 111000
                sub = f"({d:.0f}m)" + (" OK" if c.get('recomendado') else "")
                st.button(f"{label} {sub}", key=f"btn_{nombre}_ph_{c['ph']}",
                         type="primary" if is_sel else "secondary", width='stretch',
                         on_click=lambda ph=c['ph'], k=key_ph: st.session_state.update({k: ph}))

        with col_info:
            sel_data = next((c for c in candidatos if c['ph'] == ph_sel), None)
            if sel_data:
                st.write(f"**PH:** {sel_data['ph']}")
                anio = int(float(sel_data['year'])) if sel_data.get('year') else 'N/A'
                st.write(f"**Ano:** {anio}")
                secc = int(float(sel_data['seccion'])) if sel_data.get('seccion') else '-'
                mza = int(float(sel_data['manzana'])) if sel_data.get('manzana') else '-'
                graf = int(float(sel_data['grafico'])) if sel_data.get('grafico') else '-'
                st.write(f"**Seccion {secc} . Manzana {mza} . Grafico {graf}**")

            imagenes = imagenes_por_ph.get(ph_sel, [])
            if len(imagenes) > 1:
                idx = st.selectbox("Imagen:", options=range(len(imagenes)),
                                   format_func=lambda i: imagenes[i]['ruta'].rsplit('/', 1)[-1],
                                   key=f"img_sel_{nombre}_{ph_sel}")
                st.link_button("Abrir Plano", imagenes[idx]['url'], type="primary", width='stretch')
            elif len(imagenes) == 1:
                st.link_button("Ver Plano Original (PDF)", imagenes[0]['url'], type="primary", width='stretch')
            else:
                st.button("Plano no disponible", disabled=True, width='stretch')


def render_historial(nombre):
    """Historial de valuaciones con tabla y grafico."""
    st.markdown("---")
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
