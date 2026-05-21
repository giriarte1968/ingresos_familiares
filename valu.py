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

    from valu_detail_sections import (
        render_actions, render_header, render_rango, render_metricas,
        render_razonamiento, render_mapa_y_comparables, render_catastro,
        render_street_view, render_historial,
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
    render_street_view(prop)
    render_historial(nombre)

def mostrar_dashboard():
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
    if st.session_state.prop_sel:
        propiedades = cargar_propiedades()
        from parsers.motor_vpp_core import valuar_con_cache
        from parsers.valuacion_cache import cargar_cache_valuaciones, CACHE_VERSION

        p_obj = next((p for p in propiedades if p['nombre'] == st.session_state.prop_sel), None)
        if p_obj:
            forzar = st.session_state.pop(f'forzar_recalculo_{p_obj["nombre"]}', False)

            cache_existente = cargar_cache_valuaciones()
            entrada_antigua = cache_existente.get(p_obj['nombre'], {})
            if entrada_antigua.get('cache_version', '') != CACHE_VERSION and not forzar:
                st.info(f"🔄 Actualizando valuación de **{p_obj['nombre']}** "
                        f"a la nueva versión del motor ({CACHE_VERSION})...")

            with st.spinner(f"Abriendo detalle de {p_obj['nombre']}..."):
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
        return

    # ─── PÁGINAS ───
    if page == "Portfolio":
        from valu_portfolio2 import mostrar_portfolio2
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
                        from parsers.motor_vpp_core import valuar_con_cache
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

    elif st.session_state.page == "Auditoría Técnica":
        st.header("🧾 Auditoría Técnica")
        propiedades = cargar_propiedades()
        nombres = [p['nombre'] for p in propiedades]
        sel_nombre = st.selectbox("Seleccionar propiedad", nombres, key="audit_prop_sel")
        from parsers.audit_logger import cargar_audit_logs, obtener_ultimo_audit_log
        logs = cargar_audit_logs(propiedad=sel_nombre)
        if not logs:
            st.info("No hay audit_logs para esta propiedad. Recalcule la valuación primero.")
        else:
            opciones = {f"{ts.split('__')[0]}": ts for ts, log in logs}
            sel_log_key = st.selectbox("Snapshot de auditoría",
                                       list(opciones.keys()),
                                       key="audit_snap_sel")
            sel_log_path = opciones[sel_log_key]
            audit = next(log for p, log in logs if p == sel_log_path)
            tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(
                ["Inputs", "Superficies", "Cluster Venta", "Factores", "Venta", "Alquiler", "JSON crudo"]
            )
            with tab1:
                p = audit.get("propiedad", {})
                cols = st.columns(2)
                with cols[0]:
                    st.markdown(f"**Nombre:** {p.get('nombre', '')}")
                    st.markdown(f"**Zona:** {p.get('zona', '')}")
                    st.markdown(f"**Tipo:** {p.get('tipo_inmueble', '')}")
                    st.markdown(f"**Dirección:** {p.get('direccion', '')}")
                    st.markdown(f"**Lat/Lon:** {p.get('lat', '')}, {p.get('lon', '')}")
                with cols[1]:
                    st.markdown(f"**Año constr.:** {p.get('anio_construccion', '')}")
                    st.markdown(f"**Dormitorios:** {p.get('dormitorios', '')}")
                    st.markdown(f"**Estado:** {p.get('estado_detalle', '')}")
                    st.markdown(f"**Calidad:** {p.get('calidad_edificio', '')}")
                    st.markdown(f"**Piso:** {p.get('piso', '')}/{p.get('total_pisos', '')}")
                    st.markdown(f"**Ventilación:** {p.get('ventilacion', '')}")
                st.markdown(f"**Timestamp:** {audit.get('timestamp', '')}")
                st.markdown(f"**Motor:** {audit.get('motor_version', '')}")
            with tab2:
                s = audit.get("superficies", {})
                cols = st.columns(2)
                with cols[0]:
                    st.markdown(f"**m² cubiertos:** {s.get('m2_cubiertos', '')}")
                    st.markdown(f"**m² semicubiertos:** {s.get('m2_semicubiertos', '')}")
                    st.markdown(f"**m² desc. propios:** {s.get('m2_descubiertos_propios', '')}")
                with cols[1]:
                    st.markdown(f"**m² desc. común excl.:** {s.get('m2_descubiertos_comun_exclusivo', '')}")
                    st.markdown(f"**m² comunes:** {s.get('m2_comunes', '')}")
                    st.markdown(f"**m² equivalentes:** **{s.get('m2_equiv', '')}**")
            with tab3:
                c = audit.get("cluster_venta", {})
                cols = st.columns(3)
                with cols[0]:
                    st.markdown("**Pool**")
                    st.markdown(f"n total: {c.get('n_total_cluster', '')}")
                    st.markdown(f"n con año: {c.get('n_con_anio', '')}")
                    st.markdown(f"% con año: {c.get('pct_con_anio', '')}")
                    st.markdown(f"Radio: {c.get('radio_usado', '')}m")
                with cols[1]:
                    st.markdown("**Age Filter**")
                    st.markdown(f"Aplicado: {'✅' if c.get('age_filter_applied') else '❌'}")
                    st.markdown(f"n age: {c.get('n_age_filtered', '')}")
                    st.markdown(f"Rango años: {c.get('rango_anio_usado', '')}")
                    st.markdown(f"Percentil: {c.get('percentil_usado', '')}")
                with cols[2]:
                    st.markdown("**Bases**")
                    st.markdown(f"P33 same: {c.get('p33_same', '')}")
                    st.markdown(f"P33 cross: {c.get('p33_cross', '')}")
                    st.markdown(f"Base ppal: {c.get('base_principal', '')}")
                    st.markdown(f"Blend edad: {'✅' if c.get('age_blend_applied') else '❌'} α={c.get('alpha_age_blend', '')}")
                st.markdown("**Comparables usados**")
                comps = c.get("comparables_usados", [])
                if comps:
                    data = [{"Dirección": cmp.get("direccion", ""),
                             "Dist (m)": cmp.get("dist_m", ""),
                             "Precio/m²": cmp.get("precio_m2", ""),
                             "Año": cmp.get("anio_estimado", ""),
                             "Grupo": cmp.get("grupo", "")} for cmp in comps]
                    st.dataframe(data, use_container_width=True, hide_index=True)
                else:
                    st.caption("Sin datos de comparables individuales en este log.")
            with tab4:
                fx = audit.get("factores", {})
                data = [
                    ("Estado", fx.get("estado"), ""),
                    ("Calidad", fx.get("calidad"), ""),
                    ("Depreciación", fx.get("depreciacion"), f"raw={fx.get('delta_anti_raw')}, ef={fx.get('delta_anti_efectivo')}"),
                    ("Suma cruda", fx.get("suma_cruda"), f"raw={fx.get('suma_cruda_raw')}"),
                    ("Factor estructural", fx.get("f_estructural"), ""),
                    ("NLP bruto", fx.get("nlp_bruto"), f"cap={fx.get('nlp_cap_aplicado')}"),
                    ("Factor NLP", fx.get("f_nlp"), ""),
                ]
                for label, val, extra in data:
                    st.markdown(f"**{label}:** {val}  {extra if extra else ''}")
            with tab5:
                v = audit.get("venta", {})
                cols = st.columns(2)
                with cols[0]:
                    st.markdown(f"**Conservador:** ${v.get('valor_conservador', ''):,}")
                    st.markdown(f"**Mercado:** ${v.get('valor_mercado', ''):,}")
                    st.markdown(f"**Optimista:** ${v.get('valor_optimista', ''):,}")
                with cols[1]:
                    st.markdown(f"**Valor principal:** ${v.get('valor_principal', ''):,}")
                    st.markdown(f"**Realizable:** ${v.get('valor_realizable', ''):,}")
                    st.markdown(f"**Spread:** {v.get('spread_pct', '')}%")
                    st.markdown(f"**m² base:** ${v.get('m2_base_venta', '')}")
                st.caption(f"Fuente: {v.get('m2_base_source', '')}")
            with tab6:
                a = audit.get("alquiler", {})
                cols = st.columns(2)
                with cols[0]:
                    st.markdown(f"**Método:** {a.get('metodo_alquiler', '')}")
                    st.markdown(f"**Cap Rate:** {a.get('cap_rate', '')}")
                    st.markdown(f"**Cap Rate min/max:** {a.get('cap_rate_min', '')} / {a.get('cap_rate_max', '')}")
                    st.markdown(f"**Alquiler mensual:** ${a.get('alq_mensual_ars', ''):,} ARS")
                with cols[1]:
                    st.markdown(f"**Rango:** ${a.get('alq_rango_min', ''):,} - ${a.get('alq_rango_max', ''):,}")
                    st.markdown(f"**Size discount:** {a.get('size_discount_alquiler', '')}")
                    st.markdown(f"**n alquiler:** {a.get('n_alquiler', '')}")
                    st.markdown(f"**Fallback:** {'✅' if a.get('es_fallback_alquiler') else '❌'}")
            with tab7:
                st.code(json.dumps(audit, ensure_ascii=False, indent=2, default=str))
                if st.button("📥 Descargar JSON", key="dl_audit"):
                    import os as _os
                    from datetime import datetime as _dt
                    _d = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "data", "history", "audit_logs")
                    _os.makedirs(_d, exist_ok=True)
                    _fn = f"{_dt.now().strftime('%Y-%m-%d_%H-%M-%S')}__{sel_nombre.replace(' ', '_')}_export.json"
                    _fp = _os.path.join(_d, _fn)
                    with open(_fp, "w", encoding="utf-8") as _f:
                        json.dump(audit, _f, ensure_ascii=False, indent=2, default=str)
                    st.success(f"Archivo guardado: `{_fn}`")

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
        
        nav_options = ["Portfolio", "Mercado de propiedades", "Configuración"]
        forced_nav = st.session_state.pop("_force_nav_page", None)
        if forced_nav in nav_options:
            st.session_state["nav_page_radio"] = forced_nav
        if "nav_page_radio" not in st.session_state:
            st.session_state["nav_page_radio"] = st.session_state.page if st.session_state.page in nav_options else "Portfolio"
        st.radio("NAVEGACIÓN", nav_options, key="nav_page_radio")
        new_page = st.session_state["nav_page_radio"]
        # Si cambió la página desde el sidebar, limpiar prop_sel para que la navegación funcione
        if st.session_state.page != new_page:
            st.session_state.prop_sel = None
        st.session_state.page = new_page
        
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
