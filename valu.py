import streamlit as st
import os
import json
import pandas as pd
import uuid
import time
import requests
import logging
from datetime import datetime
from valu_design import VALU_CSS, kpi_card, property_card, hero_price, metric_card, range_bar, insights_card
from valu_forms import ui_formulario_propiedad
from landing import mostrar_landing
from valu_detail_sections import _get_comp_id
from parsers.mercado_inmobiliario import _calcular_mediana, _generar_html_mapa, calcular_vm2_por_seleccion
from parsers.profiler import profile_block, profile_start, profile_end, StepLedger
logger = logging.getLogger(__name__)

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

def _limpiar_estado_propiedad(nombre: str) -> None:
    """Limpia TODO el estado de sesion asociado a una propiedad."""
    if not nombre:
        return
    _PREFIJOS = [
        'preview_mode_', 'retro_active_', 'flex_active_',
        'forzar_recalculo_', 'manual_preview_', 'comp_excluded_',
        'comp_selection_', 'vista_valuacion_', 'retro_meses_', 'retro_meses_slider_',
        'manual_params_', 'retro_btn_', 'flex_btn_', 'aplicar_cambios_',
        'infomapa_catastro_', 'ph_sel_', 'comp1_', 'comp2_',
        'manual_ancla_', 'manual_usd_m2_', 'manual_fh_',
        'manual_aj_', 'manual_inc_', 'clean_valuacion_',
        'clean_comparables_', 'comp_interacted_',
    ]
    for p in _PREFIJOS:
        st.session_state.pop(f'{p}{nombre}', None)
    sufixo = f'sel_comp_{nombre}_'
    claves_a_borrar = [k for k in st.session_state.keys() if k.startswith(sufixo)]
    for k in claves_a_borrar:
        del st.session_state[k]

def _limpiar_y_borrar_cache_si_hay_manuales(nombre: str) -> None:
    """Soportar la logica de 'Limpiar Valuacion' al navegar fuera si hay cambios manuales."""
    if not nombre:
        return
    _limpiar_estado_propiedad(nombre)


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
    # Determinar si hay valuación manual paralela y qué fuente mostrar
    auto_result = res.get('_auto_result', res)
    manual_result = res.get('_manual_result')
    fuente_activa = res.get('_fuente_activa', 'auto')

    if fuente_activa == 'manual' and manual_result:
        display_result = manual_result
    else:
        display_result = auto_result

    insuficientes = auto_result.get('error') == 'insuficientes_comparables'

    nombre = prop.get('nombre', '')
    dolar = display_result.get('usdt_ars', 1480)
    valor_usd = display_result.get('valor_propiedad_usd', 0)

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
    if valor_usd > 0:
        with profile_block("render_rango", prop):
            render_rango(display_result, valor_usd)
        _dl.mark("after_render_rango")
        st.markdown("<br>", unsafe_allow_html=True)

    if insuficientes:
        st.warning(
            "**No se encontraron suficientes comparables** "
            "(mínimo 2). "
            "Usá la sección **📐 Valuación Manual** debajo "
            "para definir el valor manualmente."
        )

    if valor_usd > 0:
        with profile_block("render_metricas", prop):
            render_metricas(prop, display_result, valor_usd, dolar)
        _dl.mark("after_render_metricas")
        st.markdown("<br>", unsafe_allow_html=True)

    # ─── 📊 Comparables ───
    prop_name = prop.get('nombre', '')
    with st.expander(f"📊 Valuación por Comparables — {prop_name}", expanded=False):
        retro_key = f'retro_active_{prop_name}'
        flex_key = f'flex_active_{prop_name}'
        retro_active = st.session_state.get(retro_key, False)
        col_limpiar, col_btn, col_cb, col_slider = st.columns([1.2, 1.2, 1.0, 2.6])
        with col_limpiar:
            if st.button("🔄 Limpiar", type="secondary", use_container_width=True, key=f"cln_comps_{prop_name}"):
                st.session_state[f"clean_comparables_{prop_name}"] = True
                st.rerun()
        with col_btn:
            label = "🔙 Retro Activado" if retro_active else "🔙 Retro"
            if st.button(label, type="primary" if retro_active else "secondary", use_container_width=True, key=f'retro_btn_{prop_name}'):
                nuevo_valor = not retro_active
                st.session_state[retro_key] = nuevo_valor
                if nuevo_valor:
                    sv = st.session_state.get(f'retro_meses_slider_{prop_name}', 36)
                    st.session_state[f'retro_meses_{prop_name}'] = sv
                if not nuevo_valor:
                    st.session_state.pop(f'flex_active_{prop_name}', None)
                    st.session_state.pop(f'comp_excluded_{prop_name}', None)
                    st.session_state.pop(f'retro_meses_{prop_name}', None)
                    st.session_state.pop(f'retro_meses_slider_{prop_name}', None)
                # Resetear selección de comparables al cambiar modo retro
                st.session_state.pop(f'comp_selection_{prop_name}', None)
                st.session_state[f'forzar_recalculo_{prop_name}'] = True
                st.session_state[f'preview_mode_{prop_name}'] = True
                st.rerun()
        with col_cb:
            if retro_active:
                def _on_flex_change(prop_name=prop_name):
                    st.session_state[f'forzar_recalculo_{prop_name}'] = True
                    st.session_state[f'preview_mode_{prop_name}'] = True
                    st.session_state.pop(f'comp_selection_{prop_name}', None)
                    st.session_state.pop(f'comp_excluded_{prop_name}', None)
                st.checkbox("🔍 Todos los dormitorios", key=flex_key, on_change=_on_flex_change)
        with col_slider:
            if retro_active:
                def _on_retro_slider_change(prop_name=prop_name):
                    sv = st.session_state.get(f'retro_meses_slider_{prop_name}', 36)
                    st.session_state[f'retro_meses_{prop_name}'] = sv
                    st.session_state[f'forzar_recalculo_{prop_name}'] = True
                    st.session_state[f'preview_mode_{prop_name}'] = True
                    st.session_state.pop(f'comp_selection_{prop_name}', None)
                    st.session_state.pop(f'comp_excluded_{prop_name}', None)
                st.slider("Meses atrás", 12, 60, value=36,
                          key=f'retro_meses_slider_{prop_name}', on_change=_on_retro_slider_change)

        with st.expander(f"🗺️ Mapa — {prop_name}", expanded=False):
            with profile_block("render_mapa_propiedad", prop):
                render_mapa_propiedad(res)
        _dl.mark("after_render_mapa")

        comparables = res.get('comparables_venta', [])
        n_comps = len(comparables)
        with st.expander(f"Detalle de Comparables — {prop_name}", expanded=False):
            st.caption(f"{n_comps} propiedades comparables")
            render_tabla_comparables({**res, 'comparables_venta': comparables}, prop_name=prop_name)
        _dl.mark("after_render_tabla_comparables")
    _dl.mark("after_section_comparables")

    # ─── 📐 Valuación Manual ───
    with st.expander(f"📐 Valuacion Manual — {prop_name}", expanded=False):
        with profile_block("render_valuacion_manual", prop):
            render_valuacion_manual(prop, res)
    _dl.mark("after_section_manual")

    # ─── 📋 Valuaciones ───
    with st.expander(f"📋 Valuaciones — {prop_name}", expanded=False):
        with profile_block("render_razonamiento", prop):
            render_razonamiento(prop, res)
        _dl.mark("after_render_razonamiento")

        with profile_block("render_historial", prop):
            render_historial(nombre)
        _dl.mark("after_render_historial")
    _dl.mark("after_section_valuaciones")

    # ─── ⚡ Acciones ───
    with st.expander(f"⚡ Acciones — {prop_name}", expanded=False):
        with profile_block("generar_reporte_pdf", prop):
            pdf_bytes = generar_reporte_pdf(prop, display_result, auto_result=auto_result)

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
            from parsers.valuacion_cache import cargar_cache_valuaciones, guardar_cache_valuaciones, CACHE_VERSION
            _cl.mark("after_import_valuacion_cache")
            _cl.close()

        with profile_block("detalle_buscar_prop", None):
            p_obj = next((p for p in propiedades if p['nombre'] == st.session_state.prop_sel), None)
        if p_obj:
            prop_name = p_obj.get('nombre', '')
            # Limpiar Valuación: borrar cache, _ultima_valuacion y manual staging
            if st.session_state.get(f"clean_valuacion_{prop_name}", False):
                _limpiar_estado_propiedad(prop_name)
                try:
                    from parsers.valuacion_cache import cargar_cache_valuaciones, guardar_cache_valuaciones
                    cache_v = cargar_cache_valuaciones()
                    cache_v.pop(prop_name, None)
                    guardar_cache_valuaciones(cache_v)
                    
                    props = cargar_propiedades()
                    for p in props:
                        if p.get('nombre') == prop_name:
                            p.pop('_ultima_valuacion', None)
                            break
                    guardar_propiedades(props)
                except Exception as e:
                    print(f"Error limpiando valuacion: {e}")
                # Redirigir al portafolio para evitar que la carga natural re-valuate
                st.session_state.prop_sel = None
                st.session_state['_force_nav_page'] = 'Portfolio'
                if 'prop' in st.query_params:
                    st.query_params.clear()
                st.rerun()

            # Limpiar solo comparables: borra cache, conserva manual si existe
            if st.session_state.pop(f"clean_comparables_{prop_name}", False):
                try:
                    from parsers.valuacion_cache import cargar_cache_valuaciones, guardar_cache_valuaciones
                    cache_v = cargar_cache_valuaciones()
                    cache_v.pop(prop_name, None)
                    guardar_cache_valuaciones(cache_v)
                    props = cargar_propiedades()
                    for p in props:
                        if p.get('nombre') == prop_name:
                            uv = p.get('_ultima_valuacion', {})
                            if uv.get('manual_params'):
                                uv['fuente'] = 'manual'
                                uv['fuente_activa'] = 'manual'
                            else:
                                p.pop('_ultima_valuacion', None)
                            break
                    guardar_propiedades(props)
                except Exception as e:
                    print(f"Error limpiando comparables: {e}")
                st.session_state.pop(f'preview_mode_{prop_name}', None)
                st.session_state.pop(f'retro_active_{prop_name}', None)
                st.session_state.pop(f'flex_active_{prop_name}', None)
                st.session_state.pop(f'comp_excluded_{prop_name}', None)
                st.session_state.pop(f'comp_selection_{prop_name}', None)
                st.session_state.pop(f'retro_meses_{prop_name}', None)
                st.session_state.pop(f'retro_meses_slider_{prop_name}', None)
                st.session_state.pop(f'retro_btn_{prop_name}', None)
                st.session_state.pop(f'flex_btn_{prop_name}', None)
                st.rerun()

            # Solo aplicar preview manual si la fuente guardada en disco es 'manual'
            uv_saved = p_obj.get('_ultima_valuacion', {}) or {}
            fuente_activa_saved = uv_saved.get('fuente_activa', 'auto')
            if fuente_activa_saved == 'manual':
                manual_preview = st.session_state.get(f'manual_preview_{prop_name}', {})
                if manual_preview:
                    p_obj.update(manual_preview)
            
            forzar = st.session_state.pop(f'forzar_recalculo_{p_obj["nombre"]}', False)
            preview_mode = st.session_state.get(f'preview_mode_{p_obj["nombre"]}', False)
            retro_active_ss = st.session_state.get(f'retro_active_{p_obj["nombre"]}', False)
            flex_active_ss = st.session_state.get(f'flex_active_{p_obj["nombre"]}', False)

            with profile_block("detalle_cache_check", p_obj):
                cache_existente = cargar_cache_valuaciones()
                entrada_antigua = cache_existente.get(p_obj['nombre'], {})

            def actualizar_propiedad(nueva_data):
                prop_name = p_obj.get('nombre', '')
                # Almacenar en staging (preview) en lugar de guardar en disco inmediatamente
                st.session_state[f'manual_preview_{prop_name}'] = nueva_data
                # Actualizar objeto local para que la UI refleje los cambios inmediatamente
                p_obj.update(nueva_data)
                # Invalidar cache de valuación para que refleje los cambios en el próximo recálculo
                try:
                    from parsers.valuacion_cache import cargar_cache_valuaciones, guardar_cache_valuaciones
                    cache_v = cargar_cache_valuaciones()
                    cache_v.pop(prop_name, None)
                    guardar_cache_valuaciones(cache_v)
                except Exception:
                    pass

            # ── Si nunca fue valuado (Pendiente): mostrar detalle con 0 comps ──
            uv = p_obj.get('_ultima_valuacion', {})
            ya_valuado = bool(uv.get('valor_usd')) or (uv.get('fuente') == 'manual')
            # Detectar si el boton Retro fue clickeado (el `if st.button()` inline aun no evaluo)
            retro_btn_key = f'retro_btn_{p_obj["nombre"]}'
            retro_btn_clicked = st.session_state.get(retro_btn_key, False)
            if retro_btn_clicked:
                st.session_state[f'preview_mode_{p_obj["nombre"]}'] = True
            if not ya_valuado:
                print(f"[DEBUG-FLOW] {p_obj['nombre']}: Pendiente block - forzar={forzar}, retro_btn={retro_btn_clicked}")
                # Pendiente: limpiar cache de preview (no comprometido) si existe
                cache_existente = cargar_cache_valuaciones()
                entrada_cache = cache_existente.get(p_obj['nombre'], {})
                resultado_cacheado = entrada_cache.get('resultado_completo', {}) or {}
                cache_preview = resultado_cacheado.get('_cache', {}).get('preview', True)
                cache_valido = resultado_cacheado.get('valor_propiedad_usd') and not resultado_cacheado.get('error')
                print(f"[DEBUG-FLOW] {p_obj['nombre']}: Pendiente - cache_exists={bool(resultado_cacheado)}, cache_preview={cache_preview}, cache_error={resultado_cacheado.get('error')}, cache_valido={cache_valido}")
                if resultado_cacheado and cache_preview:
                    # Cache de preview no comprometido: limpiar al entrar solo si no hay recalculo activo
                    # Conservar si el preview tiene datos validos (evita perder preview en reruns espurios)
                    if not forzar and not cache_valido:
                        print(f"[DEBUG-FLOW] {p_obj['nombre']}: LIMPIANDO cache preview (no forzar, invalido)")
                        st.session_state.pop(f'preview_mode_{p_obj["nombre"]}', None)
                        st.session_state.pop(f'retro_active_{p_obj["nombre"]}', None)
                        st.session_state.pop(f'flex_active_{p_obj["nombre"]}', None)
                        st.session_state.pop(f'manual_preview_{p_obj["nombre"]}', None)
                        del cache_existente[p_obj['nombre']]
                        guardar_cache_valuaciones(cache_existente)
                    else:
                        print(f"[DEBUG-FLOW] {p_obj['nombre']}: CONSERVANDO cache preview (forzar={forzar}, valido={cache_valido})")
                # Si es re-entry pasivo (sin recalculación forzada), mostrar vacío
                # (no mostrar vacío si hay preview valido en cache)
                if not forzar and not retro_btn_clicked and not cache_valido:
                    st.info(f"**{p_obj['nombre']}** está pendiente de valuación. "
                            "Usa los controles Retro/Flex para generar una previsualización.")
                    
                    # Generar mapa básico solo con el sujeto para que el usuario vea la ubicación
                    mapa_sujeto = _generar_html_mapa(p_obj, {
                        'comparables_venta': [],
                        'valor_propiedad_usd': 0,
                        'resolution_metadata': {'radio_usado': 300}
                    })
                    mostrar_detalle_valu(p_obj, {'mapa_html': mapa_sujeto}, actualizar_propiedad)
                    profile_end(_routing_ctx)
                    return

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
                    vista_key = f'vista_valuacion_{prop_name}'
                    # Re-entry: solo la primera vez usar params cacheados
                    if ya_valuado and not forzar and not st.session_state.get(vista_key, False):
                        cache_params = entrada_antigua.get('resultado_completo', {}).get('_cache', {})
                        retro_dias = cache_params.get('retro_dias', 0)
                        flex_dormitorios = cache_params.get('flex_dormitorios', None)
                        st.session_state[f'retro_active_{prop_name}'] = retro_dias > 0
                        if retro_dias > 0:
                            st.session_state[f'retro_meses_{prop_name}'] = retro_dias
                            st.session_state[f'retro_meses_slider_{prop_name}'] = retro_dias
                        st.session_state[f'flex_active_{prop_name}'] = flex_dormitorios is not None
                        st.session_state[vista_key] = True
                    else:
                        st.session_state[vista_key] = True
                        retro_active = st.session_state.get(f'retro_active_{prop_name}', False)
                        retro_meses = st.session_state.get(f'retro_meses_{prop_name}', 36) if retro_active else 0
                        retro_dias = retro_meses if retro_active else 0
                        flex_active = st.session_state.get(f'flex_active_{prop_name}', False)
                        flex_dormitorios = [1, 2, 3, 4, 5] if flex_active else None
                    usar_cache = False
                    print(f"[DEBUG] {prop_name}: pre-valuacion params: forzar={forzar}, ya_valuado={ya_valuado}, retro_active={retro_active}, retro_dias={retro_dias}, flex_active={flex_active}, preview_mode={preview_mode}")
                    if ya_valuado and fuente_activa_saved == 'auto' and not forzar and bool(entrada_antigua.get('resultado_completo')):
                        cached_result = entrada_antigua['resultado_completo']
                        if cached_result.get('error'):
                            print(f"[CACHE] {prop_name}: saltando resultado con error={cached_result['error']}")
                        else:
                            cached_fecha_ref = (cached_result.get('resolution_metadata') or {}).get('fecha_ref', '')
                            cached_retro = (cached_result.get('_cache') or {}).get('retro_dias', 0)
                            hoy = datetime.now().strftime('%Y-%m-%d')
                            if cached_fecha_ref == hoy and cached_retro == retro_dias:
                                resultado = cached_result
                                usar_cache = True
                                print(f"[CACHE] {prop_name}: usando resultado_completo grabado ({len(resultado.get('comparables_venta',[]))} comps, retro={cached_retro})")
                            else:
                                print(f"[CACHE] {prop_name}: cache stale (fecha_ref={cached_fecha_ref}, retro_cache={cached_retro}, retro_actual={retro_dias}, hoy={hoy}), recalculando")
                    if not usar_cache:
                        resultado = valuar_con_cache(p_obj, forzar_recalculo=forzar, consultar_infomapa=False, retro_dias=retro_dias, flex_dormitorios=flex_dormitorios, preview=preview_mode, manual_data=st.session_state.get(f'manual_preview_{prop_name}', None))
                    _sl.mark("after_valuar_con_cache")
                    if not usar_cache:
                        n_comps = len(resultado.get('comparables_venta', []))
                        print(f"[DEBUG] {prop_name}: post-valuacion: error={resultado.get('error')}, n_comps={n_comps}, valor_usd={resultado.get('valor_propiedad_usd')}, m2_base={resultado.get('m2_base_venta')}, m2_eq={resultado.get('m2_equivalentes')}")
                        if resultado.get('error'):
                            print(f"[DEBUG] {prop_name}: RESULTADO CON ERROR, mensaje={resultado.get('mensaje')}")

                    # ── Valuación manual paralela (siempre computada, nunca sobreescribe) ──
                    uv = p_obj.get('_ultima_valuacion', {})
                    manual_params_saved = uv.get('manual_params')
                    resultado_manual = None
                    if manual_params_saved:
                        try:
                            from parsers.mercado_inmobiliario import generar_resultado_manual
                            resultado_manual = generar_resultado_manual(p_obj, manual_params_saved, auto_result=resultado)
                        except Exception as e:
                            logger.error(f"[MANUAL] Error generando resultado manual para {prop_name}: {e}")
                            resultado_manual = None
                    _sl.mark("after_manual_parallel")

                    # Determinar fuente activa (default 'auto' si no hay manual)
                    fuente_activa = uv.get('fuente_activa', 'auto')
                    if not manual_params_saved:
                        fuente_activa = 'auto'

                    # Inyectar datos paralelos para que la UI elija qué mostrar
                    resultado['_auto_result'] = resultado
                    resultado['_manual_result'] = resultado_manual
                    resultado['_manual_params'] = manual_params_saved
                    resultado['_fuente_activa'] = fuente_activa
                    _sl.mark("after_inject_parallel")

                    # ── Aplicar exclusión de comparables seleccionada por el usuario ──
                    comp_excluded_key = f'comp_excluded_{prop_name}'
                    comps_orig = resultado.get('comparables_venta')
                    print(f"[DEBUG-EXCL] {prop_name}: inicio exclusion: n_comps_orig={len(comps_orig) if comps_orig else 0}, key_in_session={comp_excluded_key in st.session_state}")
                    print(f"[DEBUG-STATE] {prop_name}: ya_valuado={ya_valuado}, forzar={forzar}, preview_mode={preview_mode}, retro_active={st.session_state.get('retro_active_' + prop_name, False)}, flex_active={st.session_state.get('flex_active_' + prop_name, False)}")
                    print(f"[DEBUG-STATE] {prop_name}: keys en session: forzar={f'forzar_recalculo_{prop_name}' in st.session_state}, comp_excluded={f'comp_excluded_{prop_name}' in st.session_state}")
                    
                    # Si el resultado base es error, no aplicar exclusión (no hay valores que modificar)
                    if not resultado.get('error') and comps_orig:
                        excluded_ids = None
                        from_apply = False

                        reset_key = f'_reset_all_{prop_name}'
                        if st.session_state.pop(reset_key, False):
                            try:
                                from parsers.valuacion_cache import cargar_cache_valuaciones, persistir_valuacion
                                _cv = cargar_cache_valuaciones()
                                persistir_valuacion(prop_name, p_obj, resultado, _cv, commit=True)
                                print(f"[RESET] {prop_name}: Exclusión limpiada y persistida")
                            except Exception as e:
                                logger.warning(f"[RESET] {prop_name}: persist error: {e}")
                                st.session_state[f'forzar_recalculo_{prop_name}'] = True
                        elif comp_excluded_key in st.session_state:
                            excluded_ids = st.session_state.pop(comp_excluded_key)
                            from_apply = True
                            print(f"[DEBUG-EXCL] {prop_name}: desde session_state: {len(excluded_ids)} excluidos, from_apply=True")
                        else:
                            # Solo restaurar exclusiones ya persistidas.
                            # NO leer widget state (checkboxes) — eso es solo visual.
                            if resultado.get('_comp_excluded') is not None:
                                excluded_ids = resultado['_comp_excluded']
                                print(f"[DEBUG-EXCL] {prop_name}: desde resultado._comp_excluded: {len(excluded_ids)} excluidos")
                            elif p_obj.get('_ultima_valuacion', {}).get('_comp_exclusion_applied'):
                                excluded_ids = p_obj['_ultima_valuacion'].get('_comp_excluded', [])
                                from_apply = True
                                print(f"[APPLY] {prop_name}: Restaurando exclusión desde _ultima_valuacion, {len(excluded_ids)} comps excluidos")
                            else:
                                print(f"[DEBUG-EXCL] {prop_name}: sin exclusion previa, excluded_ids=None")
                        if excluded_ids is not None:
                            print(f"[DEBUG-EXCL] {prop_name}: excluded_ids={excluded_ids}, from_apply={from_apply}, _comp_exclusion_applied={resultado.get('_comp_exclusion_applied')}, _comp_excluded={resultado.get('_comp_excluded')}")
                            # Verificar si la selección actual ya coincide con una exclusión aplicada y persistida
                            # Para evitar recálculos redundantes y pérdida de estado en re-entry
                            is_already_applied = (
                                resultado.get('_comp_exclusion_applied') is True and 
                                set(resultado.get('_comp_excluded', [])) == set(excluded_ids)
                            )
                            print(f"[DEBUG-EXCL] {prop_name}: is_already_applied={is_already_applied}, _cache.recalculado={resultado.get('_cache', {}).get('recalculado')}")
                            
                            if is_already_applied and not from_apply and not resultado.get('_cache', {}).get('recalculado'):
                                # Ya está aplicada y coincide: mantenemos el valor y el estado
                                print(f"[DEBUG-EXCL] {prop_name}: SALTANDO recálculo (ya aplicado y coincide)")
                            else:
                                # Guardar originales para delta del preview
                                resultado['_original_m2_base'] = resultado.get('m2_base_venta', 0)
                                resultado['_original_valor_usd'] = resultado.get('valor_propiedad_usd', 0)
                                _meta = resultado.get('resolution_metadata', {})
                                resultado['_original_m2_puro'] = _meta.get('_m2_puro', 0)
                                if excluded_ids:
                                        # Solo recalcular cuando hay exclusiones reales
                                        comps_filtrados = [c for c in comps_orig if _get_comp_id(c) not in excluded_ids]
                                        print(f"[DEBUG-EXCL] {prop_name}: calculando preview con {len(comps_filtrados)}/{len(comps_orig)} comps, m2_base_orig={resultado.get('m2_base_venta')}, m2_eq={resultado.get('m2_equivalentes')}")
                                        preview = calcular_vm2_por_seleccion(comps_filtrados, resultado)
                                        print(f"[DEBUG-EXCL] {prop_name}: preview result={preview.get('valor_total','None') if preview else 'None'}, fallback={preview.get('fallback') if preview else 'N/A'}")
                                        if preview is not None and not preview.get('fallback'):
                                            nuevo_vm2 = preview['vm2']
                                            nuevo_valor = preview['valor_total']
                                            v_cons = nuevo_valor * 0.93
                                            v_opt = nuevo_valor * 1.07
                                            resultado = dict(resultado)
                                            resultado['_auto_result'] = resultado
                                            resultado['valor_propiedad_usd'] = round(nuevo_valor, 0)
                                            resultado['valor_m2'] = nuevo_vm2
                                            resultado['m2_base_venta'] = nuevo_vm2
                                            resultado['valor_m2_actual_usd'] = round(nuevo_valor / resultado.get('m2_equivalentes', 1), 2)
                                            resultado['valor_venta_conservador'] = v_cons
                                            resultado['valor_venta_optimista'] = v_opt
                                            resultado['_n_excluidos'] = len(excluded_ids)
                                            print(f"[APPLY] {prop_name}: {preview['n_sel']} comps, P{preview['percentil']}, valor=${nuevo_valor:,.0f}")
                                        elif preview is not None and preview.get('fallback'):
                                            # < 3 comps: mantener valor original del pool
                                            resultado = dict(resultado)
                                            resultado['_auto_result'] = resultado
                                            resultado['_n_excluidos'] = len(excluded_ids)
                                            print(f"[APPLY] {prop_name}: {preview['n_sel']} comps (fallback), valor original=${resultado.get('valor_propiedad_usd', 0):,.0f}")
                                        else:
                                            # Menos de 2 comps seleccionados o preview falló → limpiar header solo si no hay valor original válido
                                            if resultado.get('valor_propiedad_usd') and resultado.get('m2_base_venta'):
                                                print(f"[APPLY] {prop_name}: <2 comps pero valor original existe, conservando (preview=None, excl={len(excluded_ids)})")
                                                resultado['_n_excluidos'] = len(excluded_ids)
                                            else:
                                                resultado = dict(resultado)
                                                resultado['_auto_result'] = resultado
                                                resultado['valor_propiedad_usd'] = 0
                                                resultado['valor_m2'] = 0
                                                resultado['m2_base_venta'] = 0
                                                resultado['valor_m2_actual_usd'] = 0
                                                resultado['valor_venta_conservador'] = 0
                                                resultado['valor_venta_optimista'] = 0
                                                resultado['_n_excluidos'] = len(excluded_ids)
                                                print(f"[APPLY] {prop_name}: <2 comps y sin valor original, header limpiado")
                                
                                resultado['_comp_excluded'] = excluded_ids
                                if from_apply:
                                    resultado['_comp_exclusion_applied'] = True
                                    try:
                                        from parsers.valuacion_cache import cargar_cache_valuaciones, persistir_valuacion
                                        _cache_v = cargar_cache_valuaciones()
                                        if '_cache' in resultado:
                                            resultado['_cache']['preview'] = False
                                        print(f"[DEBUG-PERSIST] {prop_name}: VALORES a persistir: valor_usd={resultado.get('valor_propiedad_usd')}, valor_m2={resultado.get('valor_m2')}, m2_base={resultado.get('m2_base_venta')}, n_comps={len(resultado.get('comparables_venta',[]))}, excluded={excluded_ids}, preview={resultado.get('_cache',{}).get('preview')}")
                                        persistir_valuacion(prop_name, p_obj, resultado, _cache_v, commit=True)
                                        print(f"[APPLY] {prop_name}: Persistida exclusión de {len(excluded_ids)} comps a cache+propiedades")
                                    except Exception as e:
                                        logger.warning(f"[APPLY] {prop_name}: No se pudo persistir exclusión: {e}")
                                    finally:
                                        # Limpiar flag de forzar recalculo para evitar re-ejecuciones infinitas
                                        if f'forzar_recalculo_{prop_name}' in st.session_state:
                                            del st.session_state[f'forzar_recalculo_{prop_name}']
                                            print(f"[DEBUG-FLOW] {prop_name}: forzar_recalculo limpiado post-persist")
                                else:
                                    resultado['_comp_exclusion_applied'] = False

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



        # --- Ajuste por Tamano (TAREA-074) ---
        st.markdown("---")
        with st.expander("📐 Ajuste por Tamano (size_adjustment)", expanded=False):
            _ruta_zonas = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "zonas_depreciacion.json")
            try:
                with open(_ruta_zonas, "r", encoding="utf-8") as _f:
                    _zonas_data = json.load(_f)
            except:
                _zonas_data = {"macrozonas": []}
            
            for _mz in _zonas_data.get("macrozonas", []):
                _sa = _mz.get("size_adjustment")
                if not _sa:
                    continue
                _pts = _sa.get("points", [])
                if not _pts:
                    continue
                
                st.markdown("**{}** ({})".format(_mz.get('nombre', _mz['id']), _mz['id']))
                
                _df = pd.DataFrame(_pts)
                
                _edited = st.data_editor(
                    _df,
                    column_config={
                        "m2": st.column_config.NumberColumn("m²", min_value=0, max_value=500, step=10, format="%.0f"),
                        "factor": st.column_config.NumberColumn("Factor", min_value=0.0, max_value=3.0, step=0.01, format="%.2f"),
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="sa_{}".format(_mz['id']),
                    num_rows="fixed"
                )
                
                try:
                    _x = [r["m2"] for _, r in _edited.iterrows()]
                    _y = [r["factor"] for _, r in _edited.iterrows()]
                    _fig = go.Figure()
                    _fig.add_trace(go.Scatter(x=_x, y=_y, mode="lines+markers", name=_mz.get("nombre", _mz["id"])))
                    _fig.update_layout(height=200, margin=dict(l=0, r=0, t=0, b=0), xaxis_title="m²", yaxis_title="Factor", showlegend=False)
                    st.plotly_chart(_fig, use_container_width=True, key="chart_{}".format(_mz['id']))
                except:
                    pass
                
                for _sub_id, _sub in _sa.get("subzonas", {}).items():
                    st.markdown("&nbsp;&nbsp; └ Subzona: **{}**".format(_sub_id))
                    _sub_pts = _sub.get("points", [])
                    if _sub_pts:
                        _sub_df = pd.DataFrame(_sub_pts)
                        _sub_edited = st.data_editor(
                            _sub_df,
                            column_config={
                                "m2": st.column_config.NumberColumn("m²", min_value=0, max_value=500, step=10, format="%.0f"),
                                "factor": st.column_config.NumberColumn("Factor", min_value=0.0, max_value=3.0, step=0.01, format="%.2f"),
                            },
                            hide_index=True,
                            use_container_width=True,
                            key="sa_{}_{}".format(_mz['id'], _sub_id),
                            num_rows="fixed"
                        )
                        try:
                            _sx = [r["m2"] for _, r in _sub_edited.iterrows()]
                            _sy = [r["factor"] for _, r in _sub_edited.iterrows()]
                            _sfig = go.Figure()
                            _sfig.add_trace(go.Scatter(x=_sx, y=_sy, mode="lines+markers", name=_sub_id))
                            _sfig.update_layout(height=150, margin=dict(l=0, r=0, t=0, b=0), xaxis_title="m²", yaxis_title="Factor", showlegend=False)
                            st.plotly_chart(_sfig, use_container_width=True, key="chart_{}_{}".format(_mz['id'], _sub_id))
                        except:
                            pass
                
                st.markdown("---")
            
            if st.button("💾 Guardar curvas size_adjustment", type="primary", use_container_width=True):
                for _mz in _zonas_data.get("macrozonas", []):
                    _sa = _mz.get("size_adjustment")
                    if not _sa:
                        continue
                    _pts = _sa.get("points", [])
                    if not _pts:
                        continue
                    _edited = st.session_state.get("sa_{}".format(_mz['id']))
                    if _edited is not None:
                        _sa["points"] = [{"m2": int(r["m2"]), "factor": round(float(r["factor"]), 4)} for _, r in _edited.iterrows()]
                    for _sub_id in _sa.get("subzonas", {}):
                        _sub_edited = st.session_state.get("sa_{}_{}".format(_mz['id'], _sub_id))
                        if _sub_edited is not None:
                            _sa["subzonas"][_sub_id]["points"] = [{"m2": int(r["m2"]), "factor": round(float(r["factor"]), 4)} for _, r in _sub_edited.iterrows()]
                with open(_ruta_zonas, "w", encoding="utf-8") as _f:
                    json.dump(_zonas_data, _f, ensure_ascii=False, indent=2)
                import parsers.mercado_inmobiliario as _mi
                _mi._SIZE_ADJ_CONFIG = None
                st.success("Curvas guardadas. Cache invalidada.")
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
        # Limpiar la propiedad que estamos dejando antes de entrar a la nueva
        old_prop = st.session_state.get('prop_sel')
        if old_prop:
            _limpiar_y_borrar_cache_si_hay_manuales(old_prop)
            
        prop_name = st.query_params['prop']
        _limpiar_estado_propiedad(prop_name)
        st.session_state.prop_sel = prop_name
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
            old_prop = st.session_state.prop_sel
            if old_prop:
                _limpiar_y_borrar_cache_si_hay_manuales(old_prop)
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
