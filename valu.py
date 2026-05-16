import streamlit as st
import os
import json
import pandas as pd
import uuid
import time
import requests
from datetime import datetime
from valu_design import VALU_CSS, kpi_card, property_card, hero_price, metric_card, range_bar, insights_card
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
    dolar = res.get('usdt_ars', 1480)
    valor_usd = res.get('valor_propiedad_usd', 0)

    from valu_detail_sections import (
        render_actions, render_header, render_rango, render_metricas,
        render_razonamiento, render_mapa_y_comparables, render_catastro,
        render_historial,
    )

    render_actions(prop, guardar_fn)
    render_header(prop, res)

    st.markdown("<br>", unsafe_allow_html=True)
    render_rango(res, valor_usd)
    st.markdown("<br>", unsafe_allow_html=True)

    render_metricas(prop, res, valor_usd, dolar)
    st.markdown("<br>", unsafe_allow_html=True)

    render_razonamiento(prop, res)
    render_mapa_y_comparables(res)
    render_catastro(prop, res)
    render_historial(nombre)

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
                
                if forzar_global:
                    from parsers.valuacion_cache import CACHE_VERSION
                    barra = st.progress(0.0, text="Recalculando...")
                    for i, p in enumerate(propiedades):
                        resultados[p['nombre']] = valuar_con_cache(p, forzar_recalculo=True)
                        barra.progress((i+1)/len(propiedades), text=f"Valuando {p['nombre']} ({i+1}/{len(propiedades)})")
                    st.success(f"✅ {len(propiedades)} propiedades recalculadas.")
                else:
                    # Cargar resultados cacheados SIN forzar recálculo masivo
                    for p in propiedades:
                        resultados[p['nombre']] = valuar_con_cache(p, forzar_recalculo=False)
                
                    # Mostrar aviso de versión si hay propiedades desactualizadas
                    from parsers.valuacion_cache import cargar_cache_valuaciones, CACHE_VERSION
                    cache_existente = cargar_cache_valuaciones()
                    por_actualizar = sum(
                        1 for p in propiedades
                        if p['nombre'] not in cache_existente
                        or cache_existente[p['nombre']].get('cache_version', '') != CACHE_VERSION
                    )
                    if por_actualizar > 0:
                        st.info(f"🔄 **{por_actualizar}** propiedades serán actualizadas automáticamente "
                                f"al abrir su detalle. Versión del motor: {CACHE_VERSION}.")
                
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
                st.markdown('<div style="margin-top:18px;"></div>', unsafe_allow_html=True)
                import folium
                from streamlit.components.v1 import html
                props_con_coords = [p for p in propiedades if p.get('lat') and p.get('lon')]
                if props_con_coords:
                    lats = [p['lat'] for p in props_con_coords]
                    lons = [p['lon'] for p in props_con_coords]
                    m = folium.Map(tiles='cartodbpositron')
                    for p in props_con_coords:
                        folium.Marker([p['lat'], p['lon']], popup=f"📍 {p.get('nombre', '')}", icon=folium.Icon(color='blue', icon='home')).add_to(m)
                    # Centrado del mapa: para que las propiedades queden en
                    # el tercio SUPERIOR del viewport hay que agregar mas
                    # padding al SUR (min_lat). Eso mueve el centro del mapa
                    # hacia el sur y las propiedades suben visualmente.
                    lat_range = max(lats) - min(lats)
                    lon_range = max(lons) - min(lons)
                    # Minimo de padding cuando todas las props estan muy juntas
                    base = max(lat_range, 0.012)  # ~1.3km minimo
                    pad_s = base * 0.9            # mucho espacio al sur -> props suben
                    pad_n = base * 0.15           # poco espacio al norte
                    pad_h = max(lon_range * 0.25, 0.01)
                    m.fit_bounds(
                        [[min(lats) - pad_s, min(lons) - pad_h],
                         [max(lats) + pad_n, max(lons) + pad_h]],
                        max_zoom=14
                    )
                    html(m._repr_html_(), height=300)
                    st.caption(f"📍 {len(props_con_coords)} propiedades")
                    st.markdown("<br><br><br>", unsafe_allow_html=True)
                
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
