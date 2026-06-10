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
    insuficientes = res.get('error') == 'insuficientes_comparables'

    nombre = prop.get('nombre', '')
    dolar = res.get('usdt_ars', 1480)
    valor_usd = res.get('valor_propiedad_usd', 0)

    _dl = StepLedger("mostrar_detalle_valu_ledger", nombre)
    _dl.mark("start")

    from valu_detail_sections import (
        render_actions, render_header, render_rango, render_metricas,
        render_razonamiento, render_mapa_propiedad, render_tabla_comparables,
        render_catastro, render_street_view, render_historial, generar_reporte_pdf,
        render_valuacion_manual,
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

    if insuficientes:
        st.warning(
            "**No se encontraron suficientes comparables** "
            "(mínimo 2). "
            "Usá la sección **📐 Valuación Manual** debajo "
            "para definir el valor manualmente."
        )

    with profile_block("render_metricas", prop):
        render_metricas(prop, res, valor_usd, dolar)
    _dl.mark("after_render_metricas")
    st.markdown("<br>", unsafe_allow_html=True)

    # ─── 📊 Comparables ───
    with st.expander("📊 Comparables", expanded=False):
        prop_name = prop.get('nombre', '')
        retro_key = f'retro_active_{prop_name}'
        retro_active = st.session_state.get(retro_key, False)
        col_btn, col_status, col_slider = st.columns([1.5, 1.5, 2])
        with col_btn:
            label = "🔙 Retro Activado" if retro_active else "🔙 Retro"
            if st.button(label, type="primary" if retro_active else "secondary", use_container_width=True):
                st.session_state[retro_key] = not retro_active
                st.session_state[f'forzar_recalculo_{prop_name}'] = True
                st.rerun()
        with col_status:
            if retro_active:
                meses = st.session_state.get(f'retro_meses_{prop_name}', 36)
                st.caption(f"📆 +{meses} meses")
        with col_slider:
            if retro_active:
                st.slider("Meses atrás", 12, 60, st.session_state.get(f'retro_meses_{prop_name}', 36),
                          key=f'retro_meses_{prop_name}')

        # Retro Flexible: checkboxes inline con el botón
        flex_key = f'flex_active_{prop_name}'
        flex_active = st.session_state.get(flex_key, False)
        col_fb, col_fs = st.columns([1.5, 3.5])
        with col_fb:
            flex_label = "🔍 Retro Flexible Activado" if flex_active else "🔍 Retro Flexible"
            if st.button(flex_label, type="primary" if flex_active else "secondary", use_container_width=True, key=f"flex_btn_{prop_name}"):
                st.session_state[flex_key] = not flex_active
                st.session_state[f'forzar_recalculo_{prop_name}'] = True
                if not st.session_state.get(retro_key, False):
                    st.session_state[retro_key] = True
                st.rerun()
        with col_fs:
            if flex_active:
                todos_key = f'flex_todos_{prop_name}'
                todos_val = st.session_state.get(todos_key, True)
                st.checkbox("Todos", value=todos_val, key=todos_key)
                if not todos_val:
                    dorm_cols = st.columns([1]*5)
                    for idx, d in enumerate([1, 2, 3, 4, 5]):
                        with dorm_cols[idx]:
                            st.checkbox(f"{d}", key=f'flex_dorm_cb_{prop_name}_{d}')

        with st.expander("🗺️ Mapa", expanded=False):
            with profile_block("render_mapa_propiedad", prop):
                render_mapa_propiedad(res)
        _dl.mark("after_render_mapa")

        comparables_todos = res.get('comparables_venta', [])
        flex_active = st.session_state.get(f'flex_active_{prop_name}', False)
        if flex_active:
            todos_val = st.session_state.get(f'flex_todos_{prop_name}', True)
            if todos_val:
                comparables = comparables_todos
            else:
                checked_dorms = [d for d in [1, 2, 3, 4, 5] if st.session_state.get(f'flex_dorm_cb_{prop_name}_{d}', False)]
                comparables = [c for c in comparables_todos if c.get('dormitorios') in checked_dorms] if checked_dorms else []
        else:
            comparables = comparables_todos
        n_comps = len(comparables)
        expander_label = f"{n_comps} Propiedades Comparables"
        if len(comparables) != len(comparables_todos):
            expander_label += f" (de {len(comparables_todos)} totales)"
        with st.expander(expander_label, expanded=False):
            render_tabla_comparables({**res, 'comparables_venta': comparables}, prop_name=prop_name)
        _dl.mark("after_render_tabla_comparables")
    _dl.mark("after_section_comparables")

    # ─── 📐 Valuación Manual ───
    with st.expander("📐 Valuacion Manual", expanded=insuficientes):
        with profile_block("render_valuacion_manual", prop):
            render_valuacion_manual(prop, res)
    _dl.mark("after_section_manual")

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
    button[kind="secondary"] { background-color: #2e7d32 !important; border-color: #1b5e20 !important; color: white !important; }
    button[kind="primary"] { background-color: #4caf50 !important; border-color: #388e3c !important; color: white !important; border-radius: 8px !important; font-weight: 600 !important; }
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
                # Invalidar cache de valuación para que refleje los cambios
                try:
                    from parsers.valuacion_cache import cargar_cache_valuaciones, guardar_cache_valuaciones
                    cache_v = cargar_cache_valuaciones()
                    cache_v.pop(p_obj['nombre'], None)
                    guardar_cache_valuaciones(cache_v)
                except Exception:
                    pass

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
                    prop_name = p_obj.get('nombre', '')
                    retro_active = st.session_state.get(f'retro_active_{prop_name}', False)
                    retro_meses = st.session_state.get(f'retro_meses_{prop_name}', 36) if retro_active else 0
                    retro_dias = retro_meses if retro_active else 0
                    flex_active = st.session_state.get(f'flex_active_{prop_name}', False)
                    if flex_active:
                        # Fetch all bedrooms; client-side filter via checkboxes
                        flex_dormitorios = [1, 2, 3, 4, 5]
                    else:
                        flex_dormitorios = None
                    resultado = valuar_con_cache(p_obj, forzar_recalculo=forzar, consultar_infomapa=False, retro_dias=retro_dias, flex_dormitorios=flex_dormitorios)
                    _sl.mark("after_valuar_con_cache")

                    # Override con valuación manual si está persistida
                    uv = p_obj.get('_ultima_valuacion', {})
                    if uv.get('fuente') == 'manual' and uv.get('manual_params'):
                        from parsers.mercado_inmobiliario import generar_resultado_manual
                        manual_result = generar_resultado_manual(p_obj, uv['manual_params'])
                        # Preservar comparables y retro del resultado original
                        manual_result['comparables_venta'] = resultado.get('comparables_venta', [])
                        manual_result['retro_activo'] = resultado.get('retro_activo', False)
                        manual_result['total_dias_ventana'] = resultado.get('total_dias_ventana', 180)
                        resultado = manual_result
                    _sl.mark("after_manual_override")

                with profile_block("detalle_volver_btn", None):
                    if st.button("← Volver al Portafolio"):
                        st.session_state.prop_sel = None
                        st.session_state['nav_page_radio'] = 'Portfolio'
                        if 'prop' in st.query_params:
                            st.query_params.clear()
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
        if not st.session_state.get("_mercado_unlocked", False):
            st.markdown("""
            <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:60vh;gap:1rem;">
                <div style="font-size:64px;">🔒</div>
                <h2 style="margin:0;">Acceso restringido</h2>
                <p style="color:rgba(255,255,255,0.6);">Ingresá la contraseña en la barra lateral para acceder al mercado de propiedades.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
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

        # ─── Constructoras ───
        CONSTR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "constructoras_rosario.json")
        def _cargar_constructoras():
            try:
                with open(CONSTR_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        def _guardar_constructoras(data):
            with open(CONSTR_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        st.markdown("---")
        with st.expander("🏗️ Administrar Constructoras", expanded=False):
            constr_data = _cargar_constructoras()

            if not isinstance(constr_data, list):
                constr_data = []

            # Formulario de alta
            with st.form("nueva_constructora", clear_on_submit=True):
                cols = st.columns([3, 1, 1])
                with cols[0]:
                    nueva_desc = st.text_input("Nombre de la constructora")
                with cols[1]:
                    nuevo_pct = st.number_input("Porcentaje %", value=0.0, step=0.5, format="%.2f",
                        help="Positivo = bonus sobre precio base, Negativo = descuento")
                with cols[2]:
                    st.write("")
                    st.write("")
                    submitted = st.form_submit_button("➕ Agregar", use_container_width=True)
                if submitted and nueva_desc.strip():
                    constr_data.append({"descripcion": nueva_desc.strip(), "porcentaje": nuevo_pct})
                    _guardar_constructoras(constr_data)
                    st.success(f"Constructora '{nueva_desc.strip()}' agregada con {nuevo_pct:+.2f}%")
                    st.rerun()

            # Tabla existente
            if constr_data:
                st.markdown("---")
                st.markdown("**Constructoras registradas:**")
                for i, c in enumerate(list(constr_data)):
                    cols = st.columns([3, 1, 0.5, 0.5])
                    with cols[0]:
                        st.text(c.get('descripcion', ''))
                    with cols[1]:
                        pct = c.get('porcentaje', 0)
                        color = "green" if pct >= 0 else "red"
                        st.markdown(f":{color}[{pct:+.2f}%]")
                    with cols[2]:
                        edit_key = f"edit_{i}"
                        if st.button("✏️", key=edit_key):
                            st.session_state[f"editando_constr_{i}"] = True
                    with cols[3]:
                        if st.button("🗑️", key=f"del_{i}"):
                            constr_data.pop(i)
                            _guardar_constructoras(constr_data)
                            st.rerun()

                    # Edición inline
                    if st.session_state.get(f"editando_constr_{i}", False):
                        with st.form(f"edit_constr_{i}", clear_on_submit=True):
                            ec = st.columns([3, 1, 1])
                            with ec[0]:
                                edit_desc = st.text_input("Nombre", value=c.get('descripcion', ''), key=f"ed_desc_{i}")
                            with ec[1]:
                                edit_pct = st.number_input("Porcentaje %", value=float(c.get('porcentaje', 0)), step=0.5, format="%.2f", key=f"ed_pct_{i}")
                            with ec[2]:
                                st.write("")
                                st.write("")
                                if st.form_submit_button("💾 Guardar", use_container_width=True):
                                    constr_data[i] = {"descripcion": edit_desc.strip(), "porcentaje": edit_pct}
                                    _guardar_constructoras(constr_data)
                                    st.session_state[f"editando_constr_{i}"] = False
                                    st.rerun()
                        if st.button("Cancelar", key=f"cancel_edit_{i}"):
                            st.session_state[f"editando_constr_{i}"] = False
                            st.rerun()
            else:
                st.info("No hay constructoras registradas. Agregue una usando el formulario de arriba.")

        # ─── Zonas / Anclas ───
        from parsers.motor_vpp_core import (
            _get_anclas_file, cargar_anclas_cached, load_anclas_config,
            save_anclas_config, bump_cache_version, set_active_anchor_file
        )
        ANCLAS_PATH = _get_anclas_file()
        def _cargar_anclas_completo():
            try:
                with open(ANCLAS_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return data if isinstance(data, dict) else {"anclas": data if isinstance(data, list) else []}
            except:
                return {"anclas": []}
        def _guardar_anclas_completo(data):
            with open(ANCLAS_PATH, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        st.markdown("---")
        st.markdown("### ⚙️ Pipeline de Anclas")

        # ─── Listar archivos de anclas disponibles ───
        DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
        config = load_anclas_config()
        active_file_rel = config.get('runtime', {}).get('active_anchor_file', '')
        active_file_name = os.path.basename(active_file_rel) if active_file_rel else ''
        anchor_files = sorted([f for f in os.listdir(DATA_DIR) if f.endswith('.json') and ('anclas_v7_' in f or 'anclas_rosario_v5' in f)])

        tab1, tab2, tab3, tab4 = st.tabs(["📂 Archivos", "⚡ Generar", "✏️ Editor Manual", "📈 Ct / Ajuste Temporal"])

        # ─── TAB 1: Archivos Disponibles ───
        with tab1:
            st.caption("Archivos de anclas disponibles. El archivo activo se usa en todas las valuaciones.")
            for fname in anchor_files:
                fpath = os.path.join("data", fname)
                is_active = (fpath == active_file_rel) or (fname == active_file_name)
                col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                col1.write(f"**{fname}**" if is_active else fname)
                fsize = os.path.getsize(os.path.join(DATA_DIR, fname))
                col2.caption(f"{fsize//1024} KB")
                if is_active:
                    col3.success("ACTIVO")
                else:
                    if col3.button("Activar", key=f"act_{fname}"):
                        set_active_anchor_file(fpath)
                        bump_cache_version()
                        cargar_anclas_cached(force_reload=True)
                        st.success(f"Activado: {fname}. Caché invalidada.")
                        st.rerun()
                try:
                    with open(os.path.join(DATA_DIR, fname), encoding='utf-8') as f:
                        adata = json.load(f)
                    anclas_list = adata.get('anclas', adata) if isinstance(adata, dict) else adata
                    col4.caption(f"{len(anclas_list)} anclas")
                except:
                    col4.caption("?")

        # ─── TAB 2: Generar Nuevas Anclas ───
        with tab2:
            st.caption("Regenerar anclas desde el cache actual. Cada generación produce un archivo timestamped.")
            gen_cfg = config.get('generator', {})
            grid_size = st.number_input("Grid size (m)", min_value=100, max_value=2000, value=gen_cfg.get('grid_size_m', 400), step=50)
            min_props = st.number_input("Min props por celda", min_value=2, max_value=50, value=gen_cfg.get('min_props_per_cell', 5), step=1)

            if st.button("🚀 Generar Nuevas Anclas", type="primary", use_container_width=True):
                import subprocess, sys
                result = subprocess.run(
                    [sys.executable, "scripts/generar_anclas_grid.py", "--grid-size", str(grid_size), "--min-props", str(min_props)],
                    capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__))
                )
                if result.returncode == 0:
                    st.success("Generación completada!")
                    # Parse output for summary
                    lines = result.stdout.split('\n')
                    for line in lines:
                        if 'Output:' in line:
                            st.code(line.strip())
                        elif 'Anclas generadas:' in line:
                            st.code(line.strip())
                        elif 'Cobertura' in line:
                            st.code(line.strip())
                    # Find the generated file path
                    out_path = ''
                    for line in lines:
                        if 'Output:' in line:
                            out_path = line.split('Output:')[1].strip()
                            break
                    if out_path and os.path.exists(out_path):
                        with st.expander("📊 Vista previa", expanded=True):
                            st.text(result.stdout)
                        fname = os.path.basename(out_path)
                        if st.button(f"✅ Activar {fname}", use_container_width=True):
                            rel_path = os.path.join("data", fname)
                            set_active_anchor_file(rel_path)
                            bump_cache_version()
                            cargar_anclas_cached(force_reload=True)
                            st.success(f"Activado: {fname}. Caché invalidada.")
                            st.rerun()
                else:
                    st.error("Error en generación:")
                    st.code(result.stderr)

        # ─── TAB 3: Editor Manual de Anclas (existente) ───
        with tab3:
            anclas_data = _cargar_anclas_completo()
            anclas = anclas_data.get("anclas", [])
            if not isinstance(anclas, list):
                anclas = []

            # Link cada propiedad al ancla más cercana por distancia Haversine
            todos_props = cargar_propiedades()
            ancla_props = {}
            import math
            for a in anclas:
                ancla_props[a['id']] = []
            for p in todos_props:
                p_lat = p.get('lat')
                p_lon = p.get('lon')
                if p_lat is None or p_lon is None:
                    continue
                best_id = None
                best_dist = float('inf')
                for a in anclas:
                    a_lat = a.get('lat')
                    a_lon = a.get('lon')
                    if a_lat is None or a_lon is None:
                        continue
                    R = 6371
                    lat1, lon1, lat2, lon2 = math.radians(p_lat), math.radians(p_lon), math.radians(a_lat), math.radians(a_lon)
                    dlat, dlon = lat2 - lat1, lon2 - lon1
                    dist = 2 * R * math.asin(math.sqrt(math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2))
                    if dist < best_dist:
                        best_dist = dist
                        best_id = a['id']
                if best_id:
                    ancla_props[best_id].append(p.get('nombre', '?'))

            st.caption(f"{len(anclas)} anclas en el archivo activo · editá el USD/m² directo en la tabla")
            st.info("Los cambios se guardan en el archivo activo actual. Para cambiar de archivo, usá la pestaña Archivos.")
            df_anclas = []
            for a in anclas:
                df_anclas.append({
                    "id": a.get('id', ''),
                    "USD/m²": a.get('usd_m2', 0),
                    "lat": a.get('lat', 0),
                    "lon": a.get('lon', 0),
                    "fecha": a.get('fecha_calibracion', '')[:10],
                })
            df_a = pd.DataFrame(df_anclas)

            edited = st.data_editor(
                df_a[["id", "USD/m²", "lat", "lon", "fecha"]],
                column_config={
                    "id": st.column_config.TextColumn("Ancla ID", disabled=True, width="medium"),
                    "USD/m²": st.column_config.NumberColumn("USD/m²", min_value=0, step=50.0, format="$%.0f", width="small"),
                    "lat": st.column_config.NumberColumn("Lat", disabled=True, format="%.4f", width="small"),
                    "lon": st.column_config.NumberColumn("Lon", disabled=True, format="%.4f", width="small"),
                    "fecha": st.column_config.TextColumn("Fecha", disabled=True, width="small"),
                },
                hide_index=True,
                use_container_width=True,
                key="anclas_editor"
            )

            if st.button("💾 Guardar cambios", type="primary", use_container_width=True):
                cambios = 0
                for _, row in edited.iterrows():
                    a_id = row["id"]
                    nuevo_usd = row["USD/m²"]
                    for a in anclas:
                        if a["id"] == a_id and abs(a.get("usd_m2", 0) - nuevo_usd) > 0.5:
                            a["usd_m2"] = nuevo_usd
                            a["fecha_calibracion"] = datetime.now().strftime("%Y-%m-%d")
                            cambios += 1
                if cambios:
                    anclas_data["anclas"] = anclas
                    _guardar_anclas_completo(anclas_data)
                    cargar_anclas_cached(force_reload=True)
                    st.success(f"{cambios} ancla(s) actualizadas. Caché invalidada.")
                    st.rerun()
                else:
                    st.info("Sin cambios detectados.")

            # Link propiedades
            with st.expander("🔗 Propiedades por ancla", expanded=False):
                for a in anclas:
                    linked = ancla_props.get(a['id'], [])
                    if linked:
                        st.markdown(f"**{a['id']}** (${a.get('usd_m2',0):.0f}): {', '.join(linked)}")

        # ─── TAB 4: Ct / Ajuste Temporal ───
        with tab4:
            st.caption("Curva de Ajuste Temporal (Ct) y Factores COCIR")
            st.markdown("---")

            # ct_table editor
            st.markdown("**Tabla Ct (mes → factor)**")
            ct_table = gen_cfg.get('ct_table', [[0, 1.0]])
            ct_df = pd.DataFrame(ct_table, columns=["meses", "Ct"])
            edited_ct = st.data_editor(
                ct_df, num_rows="dynamic", use_container_width=True,
                key="ct_table_editor"
            )
            if st.button("💾 Guardar Tabla Ct", key="save_ct_table", use_container_width=True):
                new_ct = [[int(r.meses), float(r.Ct)] for _, r in edited_ct.iterrows()]
                cfg = load_anclas_config(force_reload=True)
                cfg['generator']['ct_table'] = new_ct
                save_anclas_config(cfg)
                load_anclas_config(force_reload=True)
                bump_cache_version()
                st.success("Tabla Ct guardada. Caché invalidada.")
                st.rerun()

            # Gráfico Plotly de Ct
            try:
                import plotly.graph_objects as go
                ct_sorted = sorted(ct_table, key=lambda x: x[0])
                meses_vals = [r[0] for r in ct_sorted]
                ct_vals = [r[1] for r in ct_sorted]
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=meses_vals, y=ct_vals, mode='lines+markers',
                    name='Ct',
                    line=dict(color='#ff6b35', width=3),
                    marker=dict(size=8)
                ))
                # Línea vertical en ventana natural (180d = 6 meses)
                fig.add_vline(x=6, line_dash="dash", line_color="green",
                              annotation_text="ventana natural (6m)")
                # Línea horizontal en 1.0
                fig.add_hline(y=1.0, line_dash="dot", line_color="gray",
                              annotation_text="Ct=1.0 (sin ajuste)")
                fig.update_layout(
                    title="Curva Ct - Ajuste Temporal",
                    xaxis_title="Meses desde publicación",
                    yaxis_title="Factor Ct",
                    template="plotly_dark"
                )
                st.plotly_chart(fig, use_container_width=True)
            except ImportError:
                st.info("Plotly no disponible. Instalar con `pip install plotly`")

            st.markdown("---")

            # Factores nuevo-usado
            st.markdown("**Factores nuevo-usado**")
            cf = gen_cfg.get('ct_factors', {})
            col_f1, col_f2, col_f3 = st.columns(3)
            with col_f1:
                nuevo_factor = st.number_input("Factor NUEVO", min_value=0.5, max_value=2.0, value=cf.get('nuevo', 0.95), step=0.01, key="ct_nuevo")
            with col_f2:
                usado_factor = st.number_input("Factor USADO", min_value=0.5, max_value=2.0, value=cf.get('usado', 1.12), step=0.01, key="ct_usado")
            with col_f3:
                fv = st.text_input("Fecha vigencia (YYYY-MM)", value=cf.get('fecha_vigencia', '2026-01'), key="ct_fv")

            if st.button("💾 Guardar Factores nuevo-usado", key="save_ct_factors", use_container_width=True):
                cfg = load_anclas_config(force_reload=True)
                cfg['generator']['ct_factors'] = {
                    'usado': usado_factor,
                    'nuevo': nuevo_factor,
                    'fecha_vigencia': fv
                }
                save_anclas_config(cfg)
                load_anclas_config(force_reload=True)
                bump_cache_version()
                st.success("Factores nuevo-usado guardados. Caché invalidada.")
                st.rerun()

            # Histórico de cambios de factores
            try:
                hist_path = os.path.join(CONFIG_DIR, "ct_factors_history.json")
                if os.path.exists(hist_path):
                    with open(hist_path, encoding='utf-8') as f:
                        history = json.load(f)
                    if history:
                        st.markdown("---")
                        st.markdown("**Historial de cambios**")
                        st.json(history)
            except:
                pass

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

        # ─── Agregar Nueva Propiedad (último, porque ui_formulario_propiedad hace st.stop()) ───
        st.markdown("---")
        with st.expander("➕ Agregar Nueva Propiedad", expanded=False):
            new_prop = ui_formulario_propiedad(key_suffix="new")
            if st.button("Guardar Propiedad", type="primary"):
                props = cargar_propiedades()
                props.append(new_prop)
                guardar_propiedades(props)
                st.success(f"Propiedad {new_prop['nombre']} guardada!")
                st.rerun()
    profile_end(_routing_ctx)

# --- MAIN APP ---
@st.cache_resource
def git_pull_once_per_process():
    try:
        from parsers.git_sync import try_pull
        return try_pull()
    except Exception as e:
        return False

def main():
    # Sincronizar propiedades.json una vez por proceso (no una vez por sesión/pestaña)
    git_pull_once_per_process()

    # ─── Interceptar ?prop=xxx antes de cualquier check de landing ───
    if 'prop' in st.query_params:
        st.session_state.prop_sel = st.query_params['prop']
        st.session_state.vista_actual = 'dashboard'
        st.query_params.clear()
        st.rerun()
        return

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
            st.session_state.prop_sel = None
            st.session_state.pop('_force_nav_page', None)
            if 'nav_page_radio' in st.session_state:
                del st.session_state['nav_page_radio']

        # ─── Password gate (solo para Mercado) ───
        pwd = st.text_input("🔑 Acceso a Mercado", type="password", placeholder="••••••", key="_nav_pwd")
        mercado_unlocked = (pwd == "001122")
        st.session_state._mercado_unlocked = mercado_unlocked
        if mercado_unlocked:
            st.success("✅ Mercado desbloqueado")
        else:
            st.caption("Ingresá la contraseña para acceder al Mercado")

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
