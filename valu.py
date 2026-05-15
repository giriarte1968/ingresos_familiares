import streamlit as st
import os
import json
import pandas as pd
import uuid
import time
import requests
from datetime import datetime
from valu_design import VALU_CSS, kpi_card, property_card, hero_price, metric_card, range_bar, LANDING_HTML, insights_card
from valu_forms import ui_formulario_propiedad
from landing import mostrar_landing

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Valu — Valuador de Propiedades", page_icon="🏠", layout="wide")
st.markdown(VALU_CSS, unsafe_allow_html=True)

DATOS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'datos.json')
PROPIEDADES_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'propiedades.json')

# --- DATA HELPERS ---
def cargar_datos():
    try:
        if os.path.exists(DATOS_FILE):
            with open(DATOS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except: pass
    return {'activos': [], 'meses': {}}

def cargar_propiedades():
    try:
        if os.path.exists(PROPIEDADES_FILE):
            with open(PROPIEDADES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get('propiedades', [])
    except: pass
    return []

def guardar_propiedades(propiedades):
    try:
        with open(PROPIEDADES_FILE, 'w', encoding='utf-8') as f:
            json.dump({'propiedades': propiedades}, f, indent=2, ensure_ascii=False)
    except Exception as e:
        st.error(f"Error guardando: {e}")

@st.cache_data(ttl=3600)
def obtener_usdt_ars_binance(fecha=None):
    try:
        url = 'https://min-api.cryptocompare.com/data/pricemulti?fsyms=USDT&tsyms=ARS'
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if 'USDT' in data: return data['USDT']['ARS']
    except: pass
    return 1480.0

@st.cache_data(ttl=3600)
def obtener_precios_historicos(fecha=None):
    # Simplificado para Valu
    return 950.0, obtener_usdt_ars_binance()

# --- UI COMPONENTS ---

def mostrar_dashboard_valu(propiedades, resultados):
    st.markdown('<div class="page-header"><div><h1 style="margin:0;color:#1A2B5C;">🏘️ Portfolio</h1><p style="margin:0;color:#6B7280;">Rosario, Argentina</p></div></div>', unsafe_allow_html=True)
    
    # === FILTROS ===
    zonas = sorted(set(p.get('zona', '') for p in propiedades))
    tipos = sorted(set(p.get('tipo_inmueble', '') for p in propiedades))
    dorms_op = sorted(set(p.get('dormitorios', 0) for p in propiedades))

    col_f1, col_f2, col_f3, col_f4 = st.columns(4)
    with col_f1: f_zona = st.multiselect("Zona", zonas, key="filtro_zona")
    with col_f2: f_tipo = st.multiselect("Tipo", tipos, key="filtro_tipo")
    with col_f3: f_dorms = st.multiselect("Dorm.", dorms_op, key="filtro_dorms")
    with col_f4: f_busq = st.text_input("🔍 Buscar", placeholder="Nombre o dirección", key="filtro_busq")

    col_s1, col_s2, col_s3 = st.columns(3)
    max_valor = max((r.get('valor_propiedad_usd', 0) for r in resultados.values()), default=500000)
    with col_s1: f_valor_min, f_valor_max = st.slider("Rango valor USD", 0, int(max_valor * 1.1), (0, int(max_valor * 1.1)), key="filtro_valor")
    with col_s2: f_cap_min = st.slider("Cap Rate min.", 0.0, 10.0, 0.0, 0.5, key="filtro_cap", format="%.1f%%")
    with col_s3:
        orden = st.selectbox("Ordenar", [
            "Valor USD ↓", "Valor USD ↑",
            "Cap Rate ↓", "Cap Rate ↑",
            "Alquiler ↓", "Alquiler ↑",
            "Nombre A→Z", "Nombre Z→A",
        ], key="filtro_orden")

    # === FILTRAR ===
    props_filtradas = []
    for p in propiedades:
        nombre = p.get('nombre', '')
        res = resultados.get(nombre, {})
        zona = p.get('zona', '')
        tipo = p.get('tipo_inmueble', '')
        dorms = p.get('dormitorios', 0)
        valor = res.get('valor_propiedad_usd', 0)
        cap = res.get('cap_rate', 0)
        alq = res.get('alquiler_estimado_ars', 0)
        dir_ = p.get('direccion', '')

        if f_zona and zona not in f_zona: continue
        if f_tipo and tipo not in f_tipo: continue
        if f_dorms and dorms not in f_dorms: continue
        if f_busq and f_busq.lower() not in nombre.lower() and f_busq.lower() not in dir_.lower(): continue
        if not (f_valor_min <= valor <= f_valor_max): continue
        if cap < f_cap_min / 100: continue

        props_filtradas.append(p)

    if not props_filtradas:
        st.info("😶 Ninguna propiedad coincide con los filtros.")
        return

    # === AGRUPAR POR ZONA ===
    grupos = {}
    for p in props_filtradas:
        zona = p.get('zona', 'Sin zona')
        nombre = p.get('nombre', '')
        res = resultados.get(nombre, {})
        if zona not in grupos:
            grupos[zona] = {'props': [], 'valor_total': 0, 'alquiler_total': 0, 'cap_rates': []}
        grupos[zona]['props'].append(p)
        grupos[zona]['valor_total'] += res.get('valor_propiedad_usd', 0)
        grupos[zona]['alquiler_total'] += res.get('alquiler_estimado_ars', 0)
        cap = res.get('cap_rate')
        if cap: grupos[zona]['cap_rates'].append(cap)

    st.markdown(f"**{len(props_filtradas)}** propiedades encontradas en **{len(grupos)}** zonas")

    # === ORDENAR GRUPOS ===
    zonas_ordenadas = sorted(grupos.keys())

    # === TABLA PARA MUCHOS, CARDS PARA POCOS ===
    if len(props_filtradas) <= 12:
        cols = st.columns(3)
        for i, p in enumerate(props_filtradas):
            nombre = p.get('nombre', '')
            res = resultados.get(nombre, {})
            with cols[i % 3]:
                alq_r = res.get('alquiler_rango', {})
                st.markdown(property_card(
                    nombre, p.get('zona', ''), res.get('m2_equivalentes', 0),
                    p.get('dormitorios', 0), p.get('tipo_inmueble', 'Depto'),
                    res.get('valor_propiedad_usd', 0), res.get('cap_rate', 0),
                    res.get('alquiler_estimado_ars', 0),
                    res.get('resolution_metadata', {}).get('n_propiedades', 0),
                    alq_min=alq_r.get('min', 0), alq_max=alq_r.get('max', 0)
                ), unsafe_allow_html=True)
                if st.button(f"Ver detalle de {nombre} →", key=f"btn_{nombre}", width='stretch'):
                    st.session_state.prop_sel = nombre
                    st.session_state.page = "Detalle"
                    st.rerun()
    else:
        # Tabla compacta
        rows = []
        for p in props_filtradas:
            nombre = p.get('nombre', '')
            res = resultados.get(nombre, {})
            meta = res.get('resolution_metadata', {})
            pct_label = meta.get('percentil_usado', meta.get('method', ''))
            rows.append({
                'Nombre': nombre,
                'Zona': p.get('zona', ''),
                'Tipo': p.get('tipo_inmueble', ''),
                'Dorms': p.get('dormitorios', 0),
                'm²': res.get('m2_equivalentes', 0),
                'Valor USD': res.get('valor_propiedad_usd', 0),
                'Cap Rate': f"{res.get('cap_rate', 0)*100:.1f}%",
                'Alquiler': f"${res.get('alquiler_estimado_ars', 0):,.0f}",
                'Conf.': pct_label[:6],
            })

        df = pd.DataFrame(rows)

        orden_map = {
            "Valor USD ↓": ("Valor USD", False),
            "Valor USD ↑": ("Valor USD", True),
            "Cap Rate ↓": ("Cap Rate", False),
            "Cap Rate ↑": ("Cap Rate", True),
            "Alquiler ↓": ("Alquiler", False),
            "Alquiler ↑": ("Alquiler", True),
            "Nombre A→Z": ("Nombre", True),
            "Nombre Z→A": ("Nombre", False),
        }
        if orden in orden_map:
            col, asc = orden_map[orden]
            df = df.sort_values(col, ascending=asc)

        st.dataframe(df, width='stretch', hide_index=True)

        # Selector de propiedad
        nombres = df['Nombre'].tolist()
        sel = st.selectbox("Seleccionar propiedad para ver detalle", nombres, key="portfolio_sel")
        if st.button("📄 Ver detalle completo", type="primary", width='stretch'):
            st.session_state.prop_sel = sel
            st.session_state.page = "Detalle"
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    st.caption(f"💡 {len(props_filtradas)} propiedades mostradas · {len(grupos)} zonas · "
               f"Datos de caché · {'Cards' if len(props_filtradas) <= 12 else 'Tabla'}")


def mostrar_detalle_valu(prop, res, guardar_fn):
    nombre = prop.get('nombre', '')
    
    # Barra de acciones: 3 botones iguales contiguos a la izquierda
    col_back, col_edit, col_recalc = st.columns(3)
    with col_back:
        if st.button("← Volver", width='stretch'):
            st.session_state.prop_sel = None
            st.rerun()
    with col_edit:
        if st.button("✏️ Editar", width='stretch'):
            st.session_state[f"edit_{prop['id']}"] = True
    with col_recalc:
        if st.button("🔄 Revaluar", width='stretch'):
            st.session_state[f'forzar_recalculo_{nombre}'] = True
            st.rerun()

    if st.session_state.get(f"edit_{prop['id']}", False):
        with st.form(f"f_edit_{prop['id']}"):
            new_data = ui_formulario_propiedad(prop_inicial=prop, key_suffix="edit", show_geocode=False)
            if st.form_submit_button("Guardar Cambios", type="primary"):
                guardar_fn(new_data)
                st.session_state[f"edit_{prop['id']}"] = False
                st.rerun()
            if st.form_submit_button("Cancelar"):
                st.session_state[f"edit_{prop['id']}"] = False
                st.rerun()

    zona = prop.get('zona', 'Oeste')
    dolar = res.get('usdt_ars', 1480)
    valor_usd = res.get('valor_propiedad_usd', 0)
    m2_base = res.get('m2_base_venta', 0)
    n_comps = res.get('resolution_metadata', {}).get('n_propiedades', 0)

    # HERO
    c_h1, c_h2 = st.columns([3, 2])
    with c_h1:
        st.markdown(f"""
        <div style="background:white;border-radius:16px;padding:28px;box-shadow:0 4px 12px rgba(0,0,0,0.08);height:100%;">
            <div style="margin-bottom:12px;">
                <span class="badge" style="background:#006AFF15;color:#006AFF;">{prop.get('tipo_inmueble','').upper()}</span>
                <span class="badge" style="background:#0D948815;color:#0D9488;margin-left:5px;">{zona.upper()}</span>
                <span class="badge" style="background:#F4F6FB;color:#6B7280;margin-left:5px;">AÑO {prop.get('anio_construccion','?')}</span>
            </div>
            <h1 style="color:#1A2B5C;margin:0;font-size:36px;">📍 {nombre}</h1>
            <p style="color:#6B7280;font-size:16px;">{prop.get('direccion', 'Rosario, Argentina')}</p>
            <div style="display:flex;align-items:center;margin-top:20px;">
                <span style="width:12px;height:12px;border-radius:50%;background:#16A34A;margin-right:8px;"></span>
                <span style="color:#1A2B5C;font-weight:600;font-size:14px;">Alta confianza</span>
                <span style="color:#9CA3AF;font-size:14px;margin-left:8px;">({n_comps} comparables)</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
    with c_h2:
        st.markdown(hero_price(valor_usd, valor_usd*dolar, dolar, m2_base, n_comps, zona), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    # RANGO
    v_cons = res.get('valor_venta_conservador', valor_usd)
    v_opt = res.get('valor_venta_optimista', valor_usd)
    st.markdown(range_bar(v_cons, v_opt, res.get('rango_venta', {}).get('spread_pct', 0)), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # METRICAS
    m1, m2, m3 = st.columns(3)
    alq_ars = res.get('alquiler_estimado_ars', 0)
    alq_r = res.get('alquiler_rango', {})
    alq_min, alq_max = alq_r.get('min', 0), alq_r.get('max', 0)
    cap = res.get('cap_rate', 0)
    
    if alq_min > 0 and alq_max > 0:
        val_alq = f"${alq_min:,.0f} - ${alq_max:,.0f}"
    else:
        val_alq = f"${alq_ars:,.0f}"

    with m1: st.markdown(metric_card("💰", "Alquiler Estimado", f"{val_alq} ARS", f"${alq_ars/dolar:,.0f} USD/mes promedio"), unsafe_allow_html=True)
    with m2: st.markdown(metric_card("📈", "Cap Rate Neto", f"{cap*100:.1f}% anual", f"Cierre est: ${valor_usd*0.92:,.0f} USD", border_color="#16A34A"), unsafe_allow_html=True)
    
    valor_compra = prop.get('valor_compra_usd', 0)
    if valor_compra > 0:
        gain = valor_usd - valor_compra
        pct = (gain/valor_compra)*100
        with m3: st.markdown(metric_card("📊", "Plusvalía", f"+${gain:,.0f} USD", f"{pct:+.1f}% desde compra", border_color="#F59E0B"), unsafe_allow_html=True)
    else:
        with m3: st.markdown(metric_card("📊", "Plusvalía", "—", "Sin datos de compra", border_color="#F59E0B"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # RAZONAMIENTO DE VALUACION (nuevo formato narrativo)
    razonamiento = res.get('razonamiento', '')
    
    # Regenerar si el cache tiene texto concatenado (bug legacy)
    if razonamiento and 'incertidumbresignificativa' in razonamiento.replace(' ', ''):
        from parsers.mercado_inmobiliario import generar_razonamiento_valuacion
        meta = res.get('resolution_metadata', {})
        razonamiento = generar_razonamiento_valuacion(prop, res, meta)
        # Persistir en cache para que no se regenere en cada vista
        try:
            from parsers.valuacion_cache import cargar_cache_valuaciones, guardar_cache_valuaciones
            cache = cargar_cache_valuaciones()
            nombre_prop = prop.get('nombre', '')
            if nombre_prop in cache:
                cache[nombre_prop]['resultado_completo']['razonamiento'] = razonamiento
                guardar_cache_valuaciones(cache)
        except:
            pass
        razonamiento = generar_razonamiento_valuacion(prop, res, meta)
    
    if razonamiento:
        with st.expander("📋 Informe de Valuación", expanded=False):
            for parrafo in razonamiento.split('\n\n'):
                if parrafo.strip():
                    st.write(parrafo.strip())
    else:
        # Fallback al formato viejo si no hay razonamiento
        m2_equiv = res.get('m2_equivalentes', 0)
        factor = res.get('factor_total', 1.0)
        delta_anti = res.get('delta_anti', 1.0)
        nlp = res.get('nlp_ajuste', 0)
        m2_base = res.get('m2_base_venta', 0)
        
        arguments = [
            f"Base de mercado establecida en ${m2_base:,.0f} USD/m2 para {zona}.",
            f"Superficie ponderada de {m2_equiv:.1f} m2 (ajustada por tipo de superficie).",
            f"Ajuste por atributos estructurales: {(factor-1)*100:+.1f}%.",
            f"Factor de depreciacion por antiguedad: {(delta_anti-1)*100:+.1f}%.",
        ]
        if nlp != 0:
            arguments.append(f"Ajuste por descripcion cualitativa (NLP): {nlp*100:+.1f}%.")
        
        st.markdown(insights_card(f"Analisis de Valor para {nombre}", arguments), unsafe_allow_html=True)

    # === MAPA CON COMPARABLES (HTML cacheado - sin recalcular) ===
    st.markdown("---")
    mapa_html = res.get('mapa_html', '')
    if mapa_html:
        import streamlit.components.v1 as components
        # Envolvemos en un contenedor con altura fija
        components.html(mapa_html, height=350)
        radio = res.get('resolution_metadata', {}).get('radio_usado', 300)
        st.caption(f"🗺️ {n_comps} comparables de venta")
    else:
        st.caption("🗺️ Mapa no disponible")

    # === TABLA DE COMPARABLES ===
    comparables = res.get('comparables_venta', [])
    if comparables:
        with st.expander(f"📊 {len(comparables)} propiedades comparables utilizadas"):
            comp_rows = []
            for i, c in enumerate(comparables):
                comp_rows.append({
                    '#': i+1,
                    'Precio': f"${c.get('precio', 0):,.0f}",
                    'm²': f"{c.get('m2', 0):.0f}",
                    'Precio/m²': f"${c.get('precio_m2', 0):,.0f}",
                    'Dorm.': c.get('dormitorios', '?'),
                    'Tipo': (c.get('tipo') or '')[:12] if c.get('tipo') else '',
                    'Zona': (c.get('zona') or '')[:15],
                    'Año est.': c.get('anio_estimado', '') if c.get('anio_estimado') else '',
                    'Dist.': f"{c.get('distancia_m', 0):.0f}m" if c.get('distancia_m') else '',
                })
            st.dataframe(pd.DataFrame(comp_rows), width='stretch', hide_index=True)

    # === DOCUMENTACIÓN OFICIAL ===
    st.markdown("---")
    st.subheader("📋 Datos Catastrales")
    
    catastro = res.get('catastro_detalle', None)
    candidatos = catastro.get('candidatos', []) if catastro else []
    imagenes_por_ph = catastro.get('imagenes_disponibles', {}) if catastro else {}
    
    if not candidatos:
        with st.container(border=True):
            st.info("Sin datos catastrales para esta ubicación")
    else:
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
                    sub = f"({d:.0f}m)"
                    if c.get('recomendado'):
                        sub += " ✅"
                    text = f"{label} {sub}"
                    st.button(
                        text,
                        key=f"btn_{nombre}_ph_{c['ph']}",
                        type="primary" if is_sel else "secondary",
                        width='stretch',
                        on_click=lambda ph=c['ph'], k=key_ph: st.session_state.update({k: ph})
                    )
            
            with col_info:
                sel_data = next((c for c in candidatos if c['ph'] == ph_sel), None)
                if sel_data:
                    st.write(f"**PH:** {sel_data['ph']}")
                    anio = int(float(sel_data['year'])) if sel_data.get('year') else 'N/A'
                    st.write(f"**Año:** {anio}")
                    secc = int(float(sel_data['seccion'])) if sel_data.get('seccion') else '-'
                    mza = int(float(sel_data['manzana'])) if sel_data.get('manzana') else '-'
                    graf = int(float(sel_data['grafico'])) if sel_data.get('grafico') else '-'
                    st.write(f"**Sección {secc} · Manzana {mza} · Gráfico {graf}**")
                
                imagenes = imagenes_por_ph.get(ph_sel, [])
                if len(imagenes) > 1:
                    idx = st.selectbox(
                        "Imagen:",
                        options=range(len(imagenes)),
                        format_func=lambda i: imagenes[i]['ruta'].rsplit('/', 1)[-1],
                        key=f"img_sel_{nombre}_{ph_sel}"
                    )
                    st.link_button("📄 Abrir Plano", imagenes[idx]['url'],
                                  type="primary", width='stretch')
                elif len(imagenes) == 1:
                    st.link_button("📄 Ver Plano Original (PDF)", imagenes[0]['url'],
                                  type="primary", width='stretch')
                else:
                    st.button("📄 Plano no disponible", disabled=True, width='stretch')

    # === HISTORIAL DE VALUACIONES (NUEVO) ===
    st.markdown("---")
    from parsers.valuacion_historial import cargar_historial, comparar_valuaciones
    
    with st.expander("📈 Historial de Valuaciones"):
        historial = cargar_historial(propiedad=nombre, limite=20)

        if not historial:
            st.info("Sin historial disponible. Se generará al primer recálculo.")
        else:
            # Tabla de historial
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

                razones_legibles = {
                    'primera_vez': '1° vez',
                    'propiedad_modificada': 'Datos cambiaron',
                    'scraping_actualizado': 'Nuevo scraping',
                    'ttl_expirado': 'Actualización 24h',
                    'forzado_por_usuario': 'Manual'
                }

                data_tabla.append({
                    'Fecha': fecha_fmt,
                    'Valor USD': f"${r_res.get('valor_venta', 0):,.0f}",
                    'Cap Rate': f"{r_res.get('cap_rate', 0)*100:.1f}%",
                    'Base m²': f"${r_mkt.get('m2_base_venta', 0):,.0f}",
                    'Dólar': f"${r_mkt.get('dolar_binance', 0):,.0f}",
                    'Comps': r_mkt.get('n_comparables_venta', 0),
                    'Motivo': razones_legibles.get(r_razon, r_razon)
                })

            st.dataframe(pd.DataFrame(data_tabla), hide_index=True, width='stretch')

            # Gráfico de evolución de valor
            if len(historial) > 1:
                try:
                    import plotly.graph_objects as go

                    fechas = []
                    valores = []
                    conservadores = []
                    optimistas = []

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
                    fig.add_trace(go.Scatter(
                        x=fechas, y=optimistas,
                        fill=None, mode='lines',
                        line_color='rgba(246,195,67,0.3)',
                        name='Optimista'
                    ))
                    fig.add_trace(go.Scatter(
                        x=fechas, y=conservadores,
                        fill='tonexty', mode='lines',
                        fillcolor='rgba(52,152,219,0.1)',
                        line_color='rgba(52,152,219,0.3)',
                        name='Conservador'
                    ))
                    fig.add_trace(go.Scatter(
                        x=fechas, y=valores,
                        mode='lines+markers',
                        line=dict(color='#2ecc71', width=2),
                        marker=dict(size=8),
                        name='Valor Mercado'
                    ))
                    fig.update_layout(
                        title=f"Evolución del valor — {nombre}",
                        yaxis_title="USD",
                        xaxis_title="Fecha",
                        height=350,
                        showlegend=True,
                        margin=dict(l=0, r=0, t=40, b=0)
                    )
                    st.plotly_chart(fig, width='stretch')
                except Exception as e:
                    st.error(f"Error generando gráfico: {e}")

            # Comparador de dos fechas
            if len(historial) >= 2:
                st.markdown("**Comparar dos valuaciones:**")
                col1, col2 = st.columns(2)

                ids = [r['id'] for r in historial]
                fechas_labels = []
                for r in historial:
                    try:
                        f = datetime.fromisoformat(r['timestamp']).strftime("%d/%m %H:%M")
                    except:
                        f = r['timestamp'][:16]
                    fechas_labels.append(f"{f} — {r.get('razon_recalculo', '')}")

                with col1:
                    idx1 = st.selectbox("Primera valuación", range(len(historial)),
                                        format_func=lambda i: fechas_labels[i],
                                        key=f"comp1_{nombre}")
                with col2:
                    idx2 = st.selectbox("Segunda valuación", range(len(historial)),
                                        index=min(1, len(historial)-1),
                                        format_func=lambda i: fechas_labels[i],
                                        key=f"comp2_{nombre}")

                if idx1 != idx2:
                    diff = comparar_valuaciones(nombre, ids[idx1], ids[idx2])
                    if diff.get('diferencias'):
                        st.markdown("**Diferencias:**")
                        for campo, vals in diff['diferencias'].items():
                            var = vals['variacion']
                            pct = vals['pct']
                            emoji = "📈" if var > 0 else "📉"
                            st.write(f"{emoji} **{campo.replace('_', ' ').capitalize()}:** "
                                     f"${vals['antes']:,.0f} → ${vals['despues']:,.0f} "
                                     f"({pct:+.1f}%)")

def mostrar_dashboard():
    page = st.session_state.page
    
    if page == "Portfolio":
        propiedades = cargar_propiedades()
        
        if not propiedades:
            st.info("No tienes propiedades cargadas aún. Ve a Configuración para agregar una.")
        else:
            from parsers.motor_vpp_core import valuar_con_cache
            
            # ─── FLUJO B: DETALLE DE UNA PROPIEDAD ───
            if st.session_state.prop_sel:
                p_obj = next((p for p in propiedades if p['nombre'] == st.session_state.prop_sel), None)
                if p_obj:
                    forzar = st.session_state.pop(f'forzar_recalculo_{p_obj["nombre"]}', False)
                    
                    from parsers.valuacion_cache import cargar_cache_valuaciones, CACHE_VERSION
                    cache_existente = cargar_cache_valuaciones()
                    entrada_antigua = cache_existente.get(p_obj['nombre'], {})
                    if entrada_antigua.get('cache_version', '') != CACHE_VERSION and not forzar:
                        st.info(f"🔄 Actualizando valuación de **{p_obj['nombre']}** "
                                f"a la nueva versión del motor ({CACHE_VERSION})...")
                    
                    with st.spinner(f"Valuando {p_obj['nombre']}..."):
                        resultado = valuar_con_cache(p_obj, forzar_recalculo=forzar)
                    
                    def actualizar_propiedad(nueva_data):
                        props = cargar_propiedades()
                        for i, p in enumerate(props):
                            if p.get('nombre') == p_obj.get('nombre'):
                                props[i] = nueva_data
                                break
                        guardar_propiedades(props)
                    
                    if st.button("← Volver al Portafolio"):
                        st.session_state.prop_sel = None
                        st.rerun()
                    
                    mostrar_detalle_valu(p_obj, resultado, actualizar_propiedad)
            
            # ─── FLUJO A: VISTA GENERAL DEL PORTFOLIO ───
            else:
                st.title("📂 Mi Portafolio")
                
                col_global, _ = st.columns([1, 4])
                with col_global:
                    if st.button("🔄 Recalcular todo", help="Recalcula TODAS las propiedades ignorando el caché"):
                        st.session_state['forzar_recalculo_global'] = True
                        st.rerun()
                
                resultados = {}
                forzar_global = st.session_state.pop('forzar_recalculo_global', False)
                
                # Detectar cuántas propiedades tienen cache desactualizado
                from parsers.valuacion_cache import cargar_cache_valuaciones, CACHE_VERSION
                cache_existente = cargar_cache_valuaciones()
                por_actualizar = sum(
                    1 for p in propiedades
                    if p['nombre'] not in cache_existente
                    or cache_existente[p['nombre']].get('cache_version', '') != CACHE_VERSION
                )
                
                if por_actualizar > 0 and not forzar_global:
                    st.info(f"🔄 **{por_actualizar}** propiedades serán actualizadas automáticamente "
                            f"a la nueva versión del motor de valuación ({CACHE_VERSION}).")
                    st.caption("Esto ocurre solo una vez por propiedad después de mejoras en el algoritmo.")
                
                n_recalculadas = 0
                barra = st.progress(0.0, text="Preparando valuaciones...")
                
                for i, p in enumerate(propiedades):
                    resultados[p['nombre']] = valuar_con_cache(p, forzar_recalculo=forzar_global)
                    
                    # Verificar si realmente se recalculó (rastrear cambios de versión)
                    cache_actual = cargar_cache_valuaciones()
                    entrada = cache_actual.get(p['nombre'], {})
                    if entrada.get('cache_version') == CACHE_VERSION:
                        n_recalculadas += 1
                    
                    barra.progress((i + 1) / len(propiedades),
                                   text=f"Valuando {p['nombre']} ({i+1}/{len(propiedades)})")
                
                if forzar_global:
                    st.success(f"✅ **{len(propiedades)}** propiedades recalculadas por solicitud manual.")
                elif n_recalculadas > 0:
                    st.success(f"✅ **{n_recalculadas}** propiedades actualizadas a {CACHE_VERSION}.")
                
                # KPIS DEL PORTFOLIO
                total_usd = sum(r.get('valor_propiedad_usd', 0) for r in resultados.values())
                n_props = len(propiedades)
                cap_prom = sum(r.get('cap_rate', 0) for r in resultados.values()) / n_props if n_props else 0
                usdt_ars = obtener_usdt_ars_binance()
                
                c1, c2, c3, c4 = st.columns(4)
                with c1: st.markdown(kpi_card("💼", "Portfolio Total", f"${total_usd:,.0f} USD", f"${total_usd*usdt_ars/1e6:.1f}M ARS"), unsafe_allow_html=True)
                with c2: st.markdown(kpi_card("🏘️", "Propiedades", f"{n_props}", "activas"), unsafe_allow_html=True)
                with c3: st.markdown(kpi_card("📈", "Cap Rate Prom.", f"{cap_prom*100:.1f}%", "rendimiento neto", border_color="#16A34A"), unsafe_allow_html=True)
                with c4:
                    alq_total = sum(r.get('alquiler_estimado_ars', 0) for r in resultados.values())
                    st.markdown(kpi_card("💰", "Alquiler Total", f"${alq_total:,.0f} ARS", f"${alq_total/usdt_ars:,.0f} USD", border_color="#F59E0B"), unsafe_allow_html=True)
                
                # MAPA DE ACTIVOS
                import folium
                from streamlit.components.v1 import html
                props_con_coords = [p for p in propiedades if p.get('lat') and p.get('lon')]
                if props_con_coords:
                    lats = [p['lat'] for p in props_con_coords]
                    lons = [p['lon'] for p in props_con_coords]
                    m = folium.Map(tiles='cartodbpositron')
                    for p in props_con_coords:
                        folium.Marker([p['lat'], p['lon']], popup=f"📍 {p.get('nombre', '')}", icon=folium.Icon(color='blue', icon='home')).add_to(m)
                    m.fit_bounds([[min(lats), min(lons)], [max(lats), max(lons)]], padding=(200,200), max_zoom=12)
                    html(m._repr_html_(), height=300)
                    st.caption(f"📍 {len(props_con_coords)} propiedades")
                
                st.markdown("---")
                
                mostrar_dashboard_valu(propiedades, resultados)

    elif st.session_state.page == "Inventario":
        st.header("📋 Inventario de Propiedades")
        props = cargar_propiedades()
        if not props:
            st.info("Sin propiedades.")
        else:
            df = pd.DataFrame(props)
            # Columnas a mostrar
            display_cols = {
                'nombre': 'Nombre',
                'zona': 'Zona',
                'm2_cubiertos': 'm² Cub.',
                'dormitorios': 'Dorm.',
                'fecha_publicacion': 'Publicada el',
                'id': 'ID'
            }
            
            # Asegurar que existan todas las columnas
            for col in display_cols.keys():
                if col not in df.columns:
                    df[col] = "—"
            
            df_display = df[list(display_cols.keys())].rename(columns=display_cols)
            # Convertir todas las columnas a string para evitar errores de tipo en Streamlit
            df_display = df_display.astype(str)
            st.dataframe(df_display, width='stretch', hide_index=True)
            st.caption("💡 Puedes editar la fecha de publicación desde el detalle de cada propiedad o en el menú de Configuración.")

    elif st.session_state.page == "Cargar Mercado":
        st.header("🔄 Actualización de Mercado")
        st.info("Esta sección permite sincronizar con los portales inmobiliarios.")
        if st.button("Sincronizar VPP Sync (Scraping)", type="primary"):
            st.warning("Iniciando scraping en background...")

    elif st.session_state.page == "Configuración":
        st.header("⚙️ Configuración")
        with st.expander("➕ Agregar Nueva Propiedad", expanded=True):
            new_prop = ui_formulario_propiedad(key_suffix="new")
            if st.button("Guardar Propiedad", type="primary"):
                props = cargar_propiedades()
                props.append(new_prop)
                guardar_propiedades(props)
                st.success(f"Propiedad {new_prop['nombre']} guardada!")
                st.rerun()

# --- MAIN APP ---
def main():
    if 'vista_actual' not in st.session_state:
        st.session_state.vista_actual = 'landing'
    
    if st.session_state.vista_actual == 'landing':
        from landing import mostrar_landing
        mostrar_landing()
        return

    if 'page' not in st.session_state: st.session_state.page = "Portfolio"
    if 'prop_sel' not in st.session_state: st.session_state.prop_sel = None

    with st.sidebar:
        st.markdown('<div style="padding:10px 0;"><h2 style="color:white;margin:0;">🏠 Valu</h2><p style="color:#006AFF;font-size:11px;margin:0;font-weight:700;text-transform:uppercase;letter-spacing:1px;">Valuador de Propiedades</p></div>', unsafe_allow_html=True)
        
        def ir_al_inicio():
            st.session_state.vista_actual = 'landing'
            
        st.button("← Volver al Inicio", width='stretch', on_click=ir_al_inicio)
        st.markdown("---")
        
        st.session_state.page = st.radio("NAVEGACIÓN", ["Portfolio", "Inventario", "Cargar Mercado", "Configuración"])
        
        st.markdown("---")
        datos = cargar_datos()
        # Derivar fecha automáticamente del último scraping (usar mtime del archivo)
        import os
        from datetime import datetime
        cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache_scraping.json")
        if os.path.exists(cache_file):
            # Usar el mtime del archivo como fuente de verdad
            mtime = os.path.getmtime(cache_file)
            fecha_dt = datetime.fromtimestamp(mtime)
            fecha_cache = fecha_dt.strftime('%Y-%m-%d')
            st.caption(f"📅 Datos de mercado: {fecha_cache}")
        else:
            fecha_cache = datetime.now().strftime('%Y-%m')
        
        # Usar la fecha del cache como referencia (ya no es un selectbox)
        mes_sel = fecha_cache
        
        st.markdown("---")
        with st.expander("🗄️ Historial de Scrapings"):
            from parsers.valuacion_historial import listar_snapshots_scraping
            snapshots = listar_snapshots_scraping()

            if not snapshots:
                st.info("Sin snapshots guardados aún.")
            else:
                st.caption(f"{len(snapshots)} scrapings archivados")
                for s in snapshots[:10]:
                    st.text(f"📦 {s['fecha']} — {s['tamanio_kb']} KB")
                if len(snapshots) > 10:
                    st.caption(f"... y {len(snapshots) - 10} más")
        
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown('<p style="color:rgba(255,255,255,0.3);font-size:10px;text-align:center;">v2.5 · Powered by VPP Engine</p>', unsafe_allow_html=True)

    mostrar_dashboard()

if __name__ == "__main__":
    main()
