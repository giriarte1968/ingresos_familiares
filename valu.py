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
from parsers.profiler import profile_block, profile_start, profile_end, StepLedger

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
        from parsers.git_sync import try_sync
        try_sync([PROPIEDADES_FILE])
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

    # ─── TABLA PAGINADA ───
    POR_PAGINA = 25
    total_pag = max(1, (len(props_filtradas) + POR_PAGINA - 1) // POR_PAGINA)
    pagina = st.selectbox(
        "Pagina",
        range(1, total_pag + 1),
        format_func=lambda p: f"Pag. {p} / {total_pag}",
        key="pagina_portfolio"
    )

    inicio = (pagina - 1) * POR_PAGINA
    props_pag = props_filtradas[inicio:inicio + POR_PAGINA]

    def _fmt(v, fmt=None):
        """Convierte a string manejando None y '' sin romper Arrow."""
        if v is None or v == '':
            return '—'
        if fmt:
            return fmt(v)
        return str(v)

    rows = []
    for p in props_pag:
        nombre = p.get('nombre', '')
        res = resultados.get(nombre, {})
        m2_val = res.get('m2_equivalentes', 0) if res else None
        dorms = p.get('dormitorios')
        rows.append({
            'Nombre': nombre,
            'Zona': _fmt(p.get('zona')),
            'Tipo': _fmt(p.get('tipo_inmueble')),
            'Dorms': _fmt(dorms),
            'm2': f"{m2_val:.1f}" if isinstance(m2_val, (int, float)) and m2_val else '—',
            'Valor USD': (
                f"${res.get('valor_propiedad_usd', 0):,.0f}"
                if res and res.get('valor_propiedad_usd') else '— Pendiente —'
            ),
            'Cap Rate': (
                f"{res.get('cap_rate', 0)*100:.1f}%"
                if res and res.get('cap_rate') else '—'
            ),
            'Alquiler': (
                f"${res.get('alquiler_estimado_ars', 0):,.0f}"
                if res and res.get('alquiler_estimado_ars') else '—'
            ),
        })

    df = pd.DataFrame(rows)

    orden_map = {
        "Valor USD ↓": ("Valor USD", False),
        "Valor USD ↑": ("Valor USD", True),
        "Cap Rate ↓": ("Cap Rate", False),
        "Cap Rate ↑": ("Cap Rate", True),
        "Alquiler ↓": ("Alquiler", False),
        "Alquiler ↑": ("Alquiler", True),
        "Nombre A-Z": ("Nombre", True),
        "Nombre Z-A": ("Nombre", False),
    }
    if orden in orden_map:
        col, asc = orden_map[orden]
        df = df.sort_values(col, ascending=asc)

    # Convertir todas las columnas a string para evitar errores Arrow
    df = df.astype(str)
    st.dataframe(df, width='stretch', hide_index=True)

    st.markdown(f"**{len(props_filtradas)}** propiedades · **{len(grupos)}** zonas · Pagina {pagina}/{total_pag}")

    # Boton Ver detalle por fila
    for i, row in df.iterrows():
        c1, c2 = st.columns([4, 1])
        with c1:
            st.write(f"**{row['Nombre']}** — {row['Zona']}")
        with c2:
            if st.button("Ver detalle", key=f"det_{pagina}_{i}"):
                st.session_state.prop_sel = row['Nombre']
                st.session_state.page = "Detalle"
                st.rerun()


def mostrar_detalle_valu(prop, res, guardar_fn):
    nombre = prop.get('nombre', '')
    dolar = res.get('usdt_ars', 1480)
    valor_usd = res.get('valor_propiedad_usd', 0)

    _dl = StepLedger("mostrar_detalle_valu_ledger", nombre)
    _dl.mark("start")

    from valu_detail_sections import (
        render_actions, render_header, render_rango, render_metricas,
        render_razonamiento, render_mapa_propiedad, render_tabla_comparables,
        render_catastro, render_street_view, render_historial, generar_reporte_pdf,
    )
    _dl.mark("after_imports")

    with profile_block("render_actions", prop):
        render_actions(prop, guardar_fn)
    _dl.mark("after_render_actions")
    with profile_block("render_header", prop):
        render_header(prop, res)
    _dl.mark("after_render_header")

    st.markdown("<br>", unsafe_allow_html=True)
    with profile_block("render_rango", prop):
        render_rango(res, valor_usd)
    _dl.mark("after_render_rango")
    st.markdown("<br>", unsafe_allow_html=True)

    with profile_block("render_metricas", prop):
        render_metricas(prop, res, valor_usd, dolar)
    _dl.mark("after_render_metricas")
    st.markdown("<br>", unsafe_allow_html=True)

    # ─── 📊 Comparables ───
    with st.expander("📊 Comparables", expanded=False):
        with st.expander("🗺️ Mapa", expanded=False):
            with profile_block("render_mapa_propiedad", prop):
                render_mapa_propiedad(res)
        _dl.mark("after_render_mapa")

        comparables = res.get('comparables_venta', [])
        n_comps = len(comparables)
        with st.expander(f"{n_comps} Propiedades Comparables", expanded=False):
            with profile_block("render_tabla_comparables", prop):
                render_tabla_comparables(res)
        _dl.mark("after_render_tabla_comparables")
    _dl.mark("after_section_comparables")

    # ─── 📋 Valuaciones ───
    with st.expander("📋 Valuaciones", expanded=False):
        with profile_block("render_razonamiento", prop):
            render_razonamiento(prop, res)
        _dl.mark("after_render_razonamiento")

        with profile_block("render_historial", prop):
            render_historial(nombre)
        _dl.mark("after_render_historial")
    _dl.mark("after_section_valuaciones")

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
                    "Reporte PDF",
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

    _dl.close()

def mostrar_dashboard():
    from parsers.motor_vpp_core import valuar_con_cache
    # CSS para transicion suave entre paginas
    st.markdown("""
    <style>
    .main .block-container { transition: opacity 0.15s ease; min-height: 60vh; }
    </style>
    """, unsafe_allow_html=True)
    
    page = st.session_state.page
    
    # Limpiar residuos visuales de la pagina anterior
    if 'page' in st.session_state and 'prev_page' in st.session_state:
        if st.session_state.prev_page != page:
            st.session_state['_cleanup'] = True
    st.session_state.prev_page = page
    
    # ─── FLUJO DETALLE: funciona desde cualquier página (Portfolio, Portfolio2, etc.) ───
    _routing_ctx = profile_start("ROUTING_TOTAL")
    if st.session_state.prop_sel:
        with profile_block("detalle_cargar_propiedades", None):
            _cl = StepLedger("detalle_cargar_propiedades_ledger", None)
            _cl.mark("start")
            propiedades = cargar_propiedades()
            _cl.mark("after_cargar_propiedades")
            from parsers.valuacion_cache import cargar_cache_valuaciones, CACHE_VERSION
            _cl.mark("after_import_valuacion_cache")
            _cl.close()

        with profile_block("detalle_buscar_prop", None):
            p_obj = next((p for p in propiedades if p['nombre'] == st.session_state.prop_sel), None)
        if p_obj:
            forzar = st.session_state.pop(f'forzar_recalculo_{p_obj["nombre"]}', False)

            with profile_block("detalle_cache_check", p_obj):
                cache_existente = cargar_cache_valuaciones()
                entrada_antigua = cache_existente.get(p_obj['nombre'], {})
                if entrada_antigua.get('cache_version', '') != CACHE_VERSION and not forzar:
                    st.info(f"🔄 Actualizando valuación de **{p_obj['nombre']}** "
                            f"a la nueva versión del motor ({CACHE_VERSION})...")

            def actualizar_propiedad(nueva_data):
                props = cargar_propiedades()
                for i, p in enumerate(props):
                    if p.get('nombre') == p_obj.get('nombre'):
                        props[i] = nueva_data
                        break
                guardar_propiedades(props)

            _loader = st.empty()
            _loader.markdown("""
<div style="
    position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
    background: #000; z-index: 99999;
    display: flex; align-items: center; justify-content: center;
">
    <div style="font-size:28px">⏳</div>
</div>
""", unsafe_allow_html=True)
            try:
                with profile_block("detalle_spinner_valuar", p_obj):
                    _sl = StepLedger("detalle_spinner_valuar_ledger", p_obj.get('nombre'))
                    _sl.mark("before_valuar")
                    resultado = valuar_con_cache(p_obj, forzar_recalculo=forzar, consultar_infomapa=False)
                    _sl.mark("after_valuar_con_cache")

                with profile_block("detalle_volver_btn", None):
                    if st.button("← Volver al Portafolio"):
                        st.session_state.prop_sel = None
                        st.rerun()

                with profile_block("mostrar_detalle_valu_total", p_obj):
                    mostrar_detalle_valu(p_obj, resultado, actualizar_propiedad)

                _sl.mark("after_render")
                _sl.close()
            finally:
                _loader.empty()


        profile_end(_routing_ctx)
        return

    # ─── PÁGINAS ───
    if page == "Portfolio":
        import logging
        logging.warning(f"[ROUTING_MARKER] Entrando a Portfolio (prop_sel={st.session_state.get('prop_sel')})")
        from valu_portfolio2 import mostrar_portfolio2
        with profile_block("ROUTING:portfolio", None):
            mostrar_portfolio2(
                cargar_propiedades_fn=cargar_propiedades,
                obtener_usdt_fn=obtener_usdt_ars_binance,
            )

    elif st.session_state.page == "Mercado de propiedades":
        st.header("Mercado de propiedades")
        st.caption("Ejecutar solo cuando sea necesario.")

        # ─── Actualizar base de mercado ───
        with st.container(border=True):
            st.subheader("Actualizar la base de datos de mercado")
            if st.button("Actualizar base de mercado", type="primary", use_container_width=True):
                barra = st.progress(0.0, text="Preparando actualización...")
                estado = st.empty()
                inicio = time.time()
                try:
                    barra.progress(0.10, text="Iniciando actualización de mercado...")
                    estado.info("Actualizando datos de mercado. Esta operación puede demorar varios minutos.")
                    from parsers.motor_vpp_core import actualizar_mercado_vpp_full
                    ok = actualizar_mercado_vpp_full()
                    barra.progress(1.0, text="Actualización finalizada")
                    duracion = time.time() - inicio
                    if ok:
                        estado.success(f"Base de mercado actualizada. Tiempo total: {duracion/60:.1f} min.")
                    else:
                        estado.error("La actualización terminó con errores. Revisá los logs.")
                except Exception as e:
                    barra.progress(1.0, text="Actualización interrumpida")
                    estado.error(f"No se pudo actualizar la base de mercado: {e}")

        st.markdown("---")

        # ─── Recalcular todo ───
        with st.container(border=True):
            props = cargar_propiedades()
            n = len(props)

            st.subheader("Recalcular valuaciones")
            st.markdown(f"Fuerza el recalculo de las **{n} propiedades**.")

            if st.button("Recalcular todo", type="primary", use_container_width=True):
                if n == 0:
                    st.info("No hay propiedades para recalcular.")
                else:
                    barra = st.progress(0.0, text=f"Preparando recalculo de {n} propiedades...")
                    estado = st.empty()
                    inicio = time.time()
                    for i, p_prop in enumerate(props):
                        nombre = p_prop.get('nombre', '?')
                        estado.info(f"Valuando **{nombre}** ({i+1}/{n})")
                        valuar_con_cache(p_prop, forzar_recalculo=True)

                        avance = (i + 1) / n
                        transcurrido = time.time() - inicio
                        promedio = transcurrido / (i + 1)
                        restante = max(0, promedio * (n - i - 1))
                        barra.progress(
                            avance,
                            text=(
                                f"{i+1}/{n} valuaciones completadas · "
                                f"restan ~{restante/60:.1f} min"
                            ),
                        )
                    duracion = time.time() - inicio
                    estado.success(f"{n} propiedades recalculadas. Tiempo total: {duracion/60:.1f} min.")

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


        # ─── Profiling de rendimiento ───
        st.markdown("---")
        with st.expander("⏱️ Perfilado de Rendimiento", expanded=False):
            from parsers.profiler import dump_results, save_results, PROFILING_ENABLED
            if not PROFILING_ENABLED:
                st.info("Profiling desactivado. Activarlo con `PROFILING_ENABLED=true` (env var en DO Console).")
            else:
                data = dump_results()
                blocks = data.get("blocks", {})
                if not blocks:
                    st.info("Aún no hay datos de profiling. Ejecute una valuación primero.")
                else:
                    rows = []
                    for key, info in blocks.items():
                        rows.append({
                            "Bloque": key,
                            "Veces": info["count"],
                            "Total (ms)": info["total_ms"],
                            "Promedio (ms)": info["avg_ms"],
                            "Min (ms)": info["min_ms"],
                            "Max (ms)": info["max_ms"],
                        })
                    rows.sort(key=lambda r: r["Total (ms)"], reverse=True)
                    st.dataframe(rows, use_container_width=True, hide_index=True)
                    if st.button("📥 Descargar perfilado JSON", key="dl_profile"):
                        path = save_results()
                        st.success(f"Guardado en `{path}`")
                    if st.button("🔄 Resetear perfilado", key="reset_profile"):
                        from parsers.profiler import reset
                        reset()
                        st.rerun()
    profile_end(_routing_ctx)

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

    # ─── Overlay para transición landing → dashboard ───
    _loader = None
    if st.session_state.pop('_loading_overlay', False):
        _loader = st.empty()
        _loader.markdown("""
<div style="
    position: fixed; top: 0; left: 0; width: 100vw; height: 100vh;
    background: #000; z-index: 99999;
    display: flex; align-items: center; justify-content: center;
">
    <div style="font-size:28px">⏳</div>
</div>
""", unsafe_allow_html=True)

    _main_ctx = profile_start("MAIN_TOTAL")

    with st.sidebar:
        st.markdown('<div style="padding:10px 0;"><h2 style="color:white;margin:0;">🏠 Valu</h2><p style="color:#006AFF;font-size:11px;margin:0;font-weight:700;text-transform:uppercase;letter-spacing:1px;">Valuador de Propiedades</p></div>', unsafe_allow_html=True)
        
        def ir_al_inicio():
            st.session_state.vista_actual = 'landing'
            
        st.button("← Volver al Inicio", width='stretch', on_click=ir_al_inicio)
        st.markdown("---")
        
        nav_options = ["Portfolio", "Mercado de propiedades", "Configuración"]
        forced_nav = st.session_state.pop("_force_nav_page", None)
        if forced_nav in nav_options:
            st.session_state["nav_page_radio"] = forced_nav
        if "nav_page_radio" not in st.session_state:
            st.session_state["nav_page_radio"] = st.session_state.page if st.session_state.page in nav_options else "Portfolio"
        with profile_block("MAIN_sidebar_nav", None):
            st.radio("NAVEGACIÓN", nav_options, key="nav_page_radio")
        new_page = st.session_state["nav_page_radio"]
        # Si cambió la página desde el sidebar, limpiar prop_sel para que la navegación funcione
        if st.session_state.page != new_page:
            st.session_state.prop_sel = None
        st.session_state.page = new_page
        
        st.markdown("---")
        with profile_block("MAIN_sidebar_cargar_datos", None):
            datos = cargar_datos()
        # Derivar fecha automáticamente del campo 'fecha' dentro del JSON
        with profile_block("MAIN_sidebar_cache_mtime", None):
            cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache_scraping.json")
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r', encoding='utf-8') as _f:
                        _meta = json.load(_f)
                    _raw = _meta.get('fecha', '')
                    # Truncar ISO timestamp a YYYY-MM-DD
                    fecha_cache = _raw[:10] if _raw else datetime.now().strftime('%Y-%m')
                except Exception:
                    fecha_cache = datetime.now().strftime('%Y-%m')
            else:
                fecha_cache = datetime.now().strftime('%Y-%m')
            st.caption(f"📅 Datos de mercado: {fecha_cache}")
        
        # Usar la fecha del cache como referencia (ya no es un selectbox)
        mes_sel = fecha_cache
        
        st.markdown("---")
        with profile_block("MAIN_sidebar_snapshots", None):
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

    _r_prop = "detalle" if st.session_state.get("prop_sel") else st.session_state.get("page", "?")
    with profile_block(f"MAIN_routing_{_r_prop}", None):
        mostrar_dashboard()

    if _loader is not None:
        _loader.empty()

    profile_end(_main_ctx)

if __name__ == "__main__":
    with profile_block("APP_SCRIPT_TOTAL", "global"):
        main()
