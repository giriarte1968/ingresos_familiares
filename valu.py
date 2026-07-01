import streamlit as st
import os
import json
import pandas as pd
import uuid
import time
import requests
import logging
from datetime import datetime
from valu_design import VALU_CSS, kpi_card, property_card, metric_card, range_bar, insights_card
from valu_forms import ui_formulario_propiedad
from landing import mostrar_landing
from valu_detail_sections import _get_comp_id
from parsers.mercado_inmobiliario import _calcular_mediana, _generar_html_mapa, calcular_vm2_por_seleccion
from parsers.profiler import profile_block, profile_start, profile_end, StepLedger
from parsers.debug_logger import log as _file_log
_orig_print = print
def _dbg_print(*args, **kwargs):
    _orig_print(*args, **kwargs)
    msg = ' '.join(str(a) for a in args)
    if msg.startswith(('[DEBUG', '[CACHE')):
        _file_log(msg)
print = _dbg_print
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
        return True
    except Exception as e:
        st.error(f"Error guardando: {e}")
        return False

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
    # Destruir preview cache en disco al salir (memoria de trabajo no persiste)
    try:
        from parsers.valuacion_cache import cargar_cache_valuaciones, guardar_cache_valuaciones
        _c = cargar_cache_valuaciones()
        _entry = _c.get(nombre, {})
        if _entry:
            _rc = _entry.get('resultado_completo', {}) or {}
            if _rc.get('_cache', {}).get('preview', False):
                del _c[nombre]
                guardar_cache_valuaciones(_c)
                print(f"[DEBUG-CLEANUP] {nombre}: preview cache destruido del disco al salir")
    except Exception as e:
        print(f"[DEBUG-CLEANUP] Error limpiando preview cache de {nombre}: {e}")

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
    nombre = prop.get('nombre', '')

    # ── Modo preview: preservar header con resultado oficial ──
    preview_mode = st.session_state.get(f'preview_mode_{nombre}', False)
    official_key = f'_official_result_{nombre}'
    official_res = st.session_state.get(official_key)
    original_res = res  # preservar para tabla de comparables
    if preview_mode and official_res:
        print(f"[DEBUG-OFFICIAL] {nombre}: modo preview activo, header usara resultado oficial")
        res = official_res

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

    # ── < 3 comps: ocultar rango y métricas ──
    n_comps_display = display_result.get('resolution_metadata', {}).get('n_propiedades', 0)
    if 0 < n_comps_display < 3:
        print(f"[DEBUG-INSUF-COMPS] {nombre}: n_comps_display={n_comps_display}, ocultando rango/metricas")
        valor_usd = 0

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
    elif 0 < n_comps_display < 3:
        st.warning(
            f"**Solo {n_comps_display} comparables disponibles.** "
            "Se necesitan al menos 3 para una valuación por selección."
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
                _slider_key = f'retro_meses_slider_{prop_name}'
                if _slider_key not in st.session_state:
                    st.session_state[_slider_key] = 36
                st.slider("Meses atrás", 12, 60,
                          key=_slider_key, on_change=_on_retro_slider_change)

        with st.expander(f"🗺️ Mapa — {prop_name}", expanded=False):
            with profile_block("render_mapa_propiedad", prop):
                render_mapa_propiedad(original_res if (preview_mode and official_res) else res)
        _dl.mark("after_render_mapa")

        comparables = original_res.get('comparables_venta', [])
        n_comps = len(comparables)
        with st.expander(f"Detalle de Comparables — {prop_name}", expanded=False):
            st.caption(f"{n_comps} propiedades comparables")
            render_tabla_comparables({**original_res, 'comparables_venta': comparables}, prop_name=prop_name)
        _dl.mark("after_render_tabla_comparables")
    _dl.mark("after_section_comparables")

    # ─── 📐 Valuación Manual ───
    manual_params_present = bool(res.get('_manual_params'))
    manual_result_present = bool(res.get('_manual_result'))
    fuente_activa = res.get('_fuente_activa', 'N/A')
    print(f"[DEBUG-MANUAL-RESULT] {nombre}: render_valuacion_manual recibiendo: _manual_params={'SI' if manual_params_present else 'NO'}, _manual_result={'SI' if manual_result_present else 'NO'}, _fuente_activa={fuente_activa}")
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
            hay_catastro = render_catastro(prop, original_res if (preview_mode and official_res) else res, compact=True)
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
                render_catastro(prop, original_res if (preview_mode and official_res) else res, compact=False)
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
                            uv_old = p.get('_ultima_valuacion', {})
                            print(f"[DEBUG-CLEAN] {prop_name}: limpiando _ultima_valuacion (tenia fuente={uv_old.get('fuente')}, manual_params={bool(uv_old.get('manual_params'))}, valor_usd={uv_old.get('valor_usd')})")
                            p.pop('_ultima_valuacion', None)
                            break
                    guardar_propiedades(props)
                except Exception as e:
                    print(f"[DEBUG-CLEAN] Error limpiando comparables {prop_name}: {e}")
                st.session_state.pop(f'preview_mode_{prop_name}', None)
                st.session_state.pop(f'_official_result_{prop_name}', None)
                st.session_state.pop(f'retro_active_{prop_name}', None)
                st.session_state.pop(f'flex_active_{prop_name}', None)
                st.session_state.pop(f'comp_excluded_{prop_name}', None)
                st.session_state.pop(f'comp_selection_{prop_name}', None)
                st.session_state.pop(f'retro_meses_{prop_name}', None)
                st.session_state.pop(f'retro_meses_slider_{prop_name}', None)
                st.session_state.pop(f'retro_btn_{prop_name}', None)
                st.session_state.pop(f'flex_btn_{prop_name}', None)
                st.rerun()

            # Solo aplicar preview manual si la fuente activa es 'manual'
            uv_saved = p_obj.get('_ultima_valuacion', {}) or {}
            fuente_activa_saved = st.session_state.get(f'fuente_activa_{prop_name}', uv_saved.get('fuente_activa', 'auto'))
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
            print(f"[DEBUG-YA] {p_obj['nombre']}: ya_valuado={ya_valuado}, uv_valor_usd={uv.get('valor_usd')}, uv_fuente={uv.get('fuente')}, uv_fuente_activa={uv.get('fuente_activa')}, uv_comps={uv.get('comps')}, uv_keys={list(uv.keys()) if uv else 'no_uv'}")
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
                        preview_mode = True
                        st.session_state[f'preview_mode_{p_obj["nombre"]}'] = True
                # Si cache tiene resultado oficial valido (no preview), heredar sus parametros
                # para que sliders Retro/Flex reflejen los valores cacheados
                if resultado_cacheado and not cache_preview and cache_valido:
                    _cache_rs = resultado_cacheado.get('_cache', {}) or {}
                    _retro = _cache_rs.get('retro_dias', 0)
                    _flex = _cache_rs.get('flex_dormitorios', None)
                    if _retro > 0:
                        st.session_state[f'retro_active_{p_obj["nombre"]}'] = True
                    else:
                        st.session_state.pop(f'retro_active_{p_obj["nombre"]}', None)
                    if _retro > 0:
                        st.session_state[f'retro_meses_{p_obj["nombre"]}'] = _retro
                    # Nota: NO setear retro_meses_slider_ para evitar warning de Streamlit
                    # ("value set via Session State API + default value conflict")
                    # Sincronizar flex (faltaba — causaba caída de 9 a 2 comparables)
                    if _flex is not None:
                        st.session_state[f'flex_active_{p_obj["nombre"]}'] = True
                        st.session_state[f'flex_dormitorios_{p_obj["nombre"]}'] = _flex
                    else:
                        st.session_state.pop(f'flex_active_{p_obj["nombre"]}', None)
                        st.session_state.pop(f'flex_dormitorios_{p_obj["nombre"]}', None)
                    print(f"[DEBUG-FLOW] {p_obj['nombre']}: Pendiente con cache oficial valido — heredando params: retro={_retro}d, flex={_flex}")
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
                    # Re-entry: leer params desde UV oficial (consistente con disco)
                    if ya_valuado and not forzar and not st.session_state.get(vista_key, False):
                        uv = p_obj.get('_ultima_valuacion', {})
                        retro_dias = uv.get('retro_dias')
                        flex_dormitorios = uv.get('flex_dormitorios')
                        if retro_dias is None:
                            cache_params = entrada_antigua.get('resultado_completo', {}).get('_cache', {})
                            retro_dias = cache_params.get('retro_dias', 36)
                            print(f"[DEBUG-REENTRY] {prop_name}: retro desde cache (UV legacy)")
                        if flex_dormitorios is None:
                            cache_params = entrada_antigua.get('resultado_completo', {}).get('_cache', {})
                            flex_dormitorios = cache_params.get('flex_dormitorios', None)
                            print(f"[DEBUG-REENTRY] {prop_name}: flex desde cache (UV legacy)")
                        retro_active = retro_dias > 0
                        flex_active = flex_dormitorios is not None
                        retro_meses = retro_dias if retro_active else 0
                        st.session_state[f'retro_active_{prop_name}'] = retro_active
                        if retro_dias > 0:
                            st.session_state[f'retro_meses_{prop_name}'] = retro_dias
                            st.session_state[f'retro_meses_slider_{prop_name}'] = retro_dias
                        st.session_state[f'flex_active_{prop_name}'] = flex_active
                        if flex_active and flex_dormitorios is not None:
                            st.session_state[f'flex_dormitorios_{prop_name}'] = flex_dormitorios
                        st.session_state[vista_key] = True
                        print(f"[DEBUG-REENTRY] {prop_name}: params desde UV — retro={retro_dias}, flex={flex_dormitorios}")
                    else:
                        st.session_state[vista_key] = True
                        retro_active = st.session_state.get(f'retro_active_{prop_name}', False)
                        retro_meses = st.session_state.get(f'retro_meses_{prop_name}', 36) if retro_active else 0
                        retro_dias = retro_meses if retro_active else 0
                        flex_active = st.session_state.get(f'flex_active_{prop_name}', False)
                        flex_dormitorios = st.session_state.get(f'flex_dormitorios_{prop_name}', [1, 2, 3, 4, 5]) if flex_active else None
                    usar_cache = False
                    print(f"[DEBUG] {prop_name}: pre-valuacion params: forzar={forzar}, ya_valuado={ya_valuado}, retro_active={retro_active}, retro_dias={retro_dias}, flex_active={flex_active}, preview_mode={preview_mode}")
                    cache_condition = (ya_valuado, not forzar, bool(entrada_antigua.get('resultado_completo')))
                    print(f"[CACHE-CHECK] {prop_name}: condiciones: ya_valuado={cache_condition[0]}, not forzar={cache_condition[1]}, tiene_resultado_completo={cache_condition[2]}, fuente_activa_saved={fuente_activa_saved}, entrada_keys={list(entrada_antigua.keys()) if entrada_antigua else 'vacia'}")
                    # Intentar cache siempre (independientemente de fuente_activa) para preservar exclusion
                    if ya_valuado and not forzar and bool(entrada_antigua.get('resultado_completo')):
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
                    else:
                        fallo_por = []
                        if not ya_valuado: fallo_por.append("no_ya_valuado")
                        if forzar: fallo_por.append("forzar=True")
                        if not entrada_antigua.get('resultado_completo'): fallo_por.append("sin_resultado_completo")
                        print(f"[CACHE-CHECK] {prop_name}: cache NO INTENTADO por: {', '.join(fallo_por)}")
                    # Recalcular si cache miss: en Auto usa preview_mode real,
                    # en Manual fuerza preview=True para no pisar UV ni exclusion
                    if not usar_cache:
                        if fuente_activa_saved == 'auto':
                            print(f"[CACHE-CHECK] {prop_name}: llamando valuar_con_cache (forzar={forzar}, preview={preview_mode}, retro={retro_dias}, flex={flex_dormitorios})")
                            print(f"[DEBUG-FLEX-PASS] {prop_name}: flex_dormitorios={flex_dormitorios}" if flex_dormitorios else f"[DEBUG-FLEX-PASS] {prop_name}: flex_dormitorios=None, flex_active={flex_active}")
                            manual_data_to_pass = st.session_state.get(f'manual_preview_{prop_name}', None) if fuente_activa_saved == 'manual' else None
                            resultado = valuar_con_cache(p_obj, forzar_recalculo=forzar, consultar_infomapa=False, retro_dias=retro_dias, flex_dormitorios=flex_dormitorios, preview=preview_mode, manual_data=manual_data_to_pass)
                            print(f"[CACHE-CHECK] {prop_name}: valuar_con_cache retorno: error={resultado.get('error')}, valor={resultado.get('valor_propiedad_usd')}, n_comps={len(resultado.get('comparables_venta',[])) if resultado.get('comparables_venta') else 0}, cache_preview={resultado.get('_cache',{}).get('preview')}")
                        else:
                            # Fuente manual: recargar con preview=True para cachear resultado
                            # pero sin pisar _ultima_valuacion (preserva exclusion y datos manuales)
                            print(f"[CACHE-CHECK] {prop_name}: fuente=manual, recargando con preview=True (preserva UV/exclusion)")
                            resultado = valuar_con_cache(p_obj, forzar_recalculo=forzar, consultar_infomapa=False, retro_dias=retro_dias, flex_dormitorios=flex_dormitorios, preview=True, manual_data=None)
                    _sl.mark("after_valuar_con_cache")
                    if not usar_cache:
                        n_comps = len(resultado.get('comparables_venta', []))
                        print(f"[DEBUG] {prop_name}: post-valuacion: error={resultado.get('error')}, n_comps={n_comps}, valor_usd={resultado.get('valor_propiedad_usd')}, m2_base={resultado.get('m2_base_venta')}, m2_eq={resultado.get('m2_equivalentes')}")
                        if resultado.get('error'):
                            print(f"[DEBUG] {prop_name}: RESULTADO CON ERROR, mensaje={resultado.get('mensaje')}")

                    # ── TAREA-102: Fallback a UV snapshot si recálculo falló ──
                    if ya_valuado and (resultado.get('error') or n_comps < 3):
                        uv_snap = p_obj.get('_ultima_valuacion', {})
                        if uv_snap.get('valor_usd') and uv_snap.get('comps', 0) >= 3:
                            uv_valor = uv_snap['valor_usd']
                            uv_comps = uv_snap.get('comps', 0)
                            uv_m2_eq = uv_snap.get('m2_equivalentes', 0)
                            print(f"[DEBUG-FALLBACK-102] {prop_name}: fallback a UV snapshot. "
                                  f"error={resultado.get('error')}, n_comps={n_comps}, "
                                  f"uv_valor={uv_valor}, uv_comps={uv_comps}")
                            resultado = {
                                'valor_propiedad_usd': uv_valor,
                                'm2_base_venta': uv_m2_eq,
                                'm2_equivalentes': uv_m2_eq,
                                'm2_microzona': uv_m2_eq,
                                'resolution_metadata': {'n_propiedades': uv_comps},
                                'comparables_venta': [],
                                '_cache': {'preview': True, 'recalculado': False, 'guard_restored': False},
                                'error': None,
                                '_fallback_uv': True,
                                'valor_venta_conservador': round(uv_valor * 0.93, 0),
                                'valor_venta_optimista': round(uv_valor * 1.07, 0),
                                'valor_m2': uv_m2_eq,
                                'valor_m2_actual_usd': round(uv_valor / uv_m2_eq, 2) if uv_m2_eq > 0 else 0,
                                '_fuente_activa': uv_snap.get('fuente_activa', 'auto'),
                                'usdt_ars': uv_snap.get('usdt_ars', 1480),
                            }
                            n_comps = uv_comps

                    # ── Valuación manual paralela (siempre computada, nunca sobreescribe) ──
                    uv = p_obj.get('_ultima_valuacion', {})
                    manual_params_saved = uv.get('manual_params')
                    print(f"[DEBUG-MANUAL-RESULT] {prop_name}: manual_params_saved={'SI' if manual_params_saved else 'NO'}, "
                          f"uv_keys={list(uv.keys())}, uv_fuente={uv.get('fuente_activa', 'N/A')}, "
                          f"uv_valor_usd={uv.get('valor_usd', 'N/A')}, uv_retro={uv.get('retro_dias', 'N/A')}")
                    resultado_manual = None
                    if manual_params_saved:
                        try:
                            from parsers.mercado_inmobiliario import generar_resultado_manual
                            resultado_manual = generar_resultado_manual(p_obj, manual_params_saved, auto_result=resultado)
                            print(f"[DEBUG-MANUAL-RESULT] {prop_name}: resultado_manual GENERADO OK — valor={resultado_manual.get('valor_propiedad_usd','N/A')}, n_prop={resultado_manual.get('resolution_metadata',{}).get('n_propiedades','N/A')}")
                        except Exception as e:
                            logger.error(f"[MANUAL] Error generando resultado manual para {prop_name}: {e}")
                            resultado_manual = None
                            print(f"[DEBUG-MANUAL-RESULT] {prop_name}: resultado_manual FALLO — {e}")
                    _sl.mark("after_manual_parallel")

                    # Determinar fuente activa (default 'auto' si no hay manual)
                    fuente_activa = st.session_state.get(f'fuente_activa_{prop_name}', uv.get('fuente_activa', 'auto'))
                    if not manual_params_saved:
                        fuente_activa = 'auto'
                    print(f"[DEBUG-FUENTE] {prop_name}: fuente_activa resuelta={fuente_activa}, session_state={st.session_state.get(f'fuente_activa_{prop_name}', 'NO_SET')}, uv_disk={uv.get('fuente_activa', 'NO_UV')}")

                    # Inyectar datos paralelos para que la UI elija qué mostrar
                    resultado['_auto_result'] = resultado
                    resultado['_manual_result'] = resultado_manual
                    resultado['_manual_params'] = manual_params_saved
                    resultado['_fuente_activa'] = fuente_activa
                    print(f"[DEBUG-MANUAL-RESULT] {prop_name}: INYECTADO: _manual_params={'SI' if resultado.get('_manual_params') else 'NO'}, _manual_result={'SI' if resultado.get('_manual_result') else 'NO'}, _fuente_activa={resultado.get('_fuente_activa')}")
                    _sl.mark("after_inject_parallel")

                    # ── Restaurar exclusión desde UV si el resultado fresco no la tiene ──
                    uv_excl = p_obj.get('_ultima_valuacion', {})
                    _restore_cond1 = not resultado.get('_comp_exclusion_applied')
                    _restore_cond2 = uv_excl.get('_comp_exclusion_applied')
                    _restore_cond3 = not st.session_state.get(f'comp_excluded_{prop_name}', False)
                    if _restore_cond1 and _restore_cond2 and _restore_cond3:
                        resultado['_comp_excluded'] = uv_excl.get('_comp_excluded', [])
                        resultado['_comp_exclusion_applied'] = True
                        print(f"[DEBUG-EXCL-RESTORE] {prop_name}: RESTAURADA — {len(resultado['_comp_excluded'])} ids excluidos, from_apply={uv_excl.get('_comp_exclusion_applied')}")
                    elif uv_excl.get('_comp_exclusion_applied'):
                        print(f"[DEBUG-EXCL-RESTORE] {prop_name}: SALTADA — cond1(fresh_excl_applied)={_restore_cond1}, cond2(uv_excl_applied)={_restore_cond2}, cond3(no_pending_ss)={_restore_cond3}")

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
                            # Ya no se hace nada aquí — el botón solo actúa a nivel visual
                            pass
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
                            elif not preview_mode and p_obj.get('_ultima_valuacion', {}).get('_comp_exclusion_applied'):
                                excluded_ids = p_obj['_ultima_valuacion'].get('_comp_excluded', [])
                                from_apply = True
                                print(f"[APPLY] {prop_name}: Restaurando exclusión desde _ultima_valuacion, {len(excluded_ids)} comps excluidos, preview_mode={preview_mode}")
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
                            _guard_restored = resultado.get('_cache', {}).get('guard_restored', False)
                            print(f"[DEBUG-EXCL] {prop_name}: is_already_applied={is_already_applied}, _cache.recalculado={resultado.get('_cache', {}).get('recalculado')}, guard_restored={_guard_restored}")
                            
                            _skip_recalc = is_already_applied and not from_apply and (not resultado.get('_cache', {}).get('recalculado') or _guard_restored)
                            if _skip_recalc:
                                print(f"[DEBUG-EXCL] {prop_name}: SALTANDO recálculo (ya aplicado y coincide, guard_restored={_guard_restored})")
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
                                            # Sincronizar header con selección activa (TAREA-094)
                                            _meta['n_propiedades'] = len(comps_filtrados)
                                            resultado['m2_microzona'] = nuevo_vm2
                                            print(f"[DEBUG-SYNC-HEADER] {prop_name}: n_propiedades={len(comps_filtrados)}, m2_microzona={nuevo_vm2}")
                                            print(f"[APPLY] {prop_name}: {preview['n_sel']} comps, P{preview['percentil']}, valor=${nuevo_valor:,.0f}")
                                        elif preview is not None and preview.get('fallback'):
                                            # < 3 comps: mantener valor original del pool
                                            resultado = dict(resultado)
                                            resultado['_auto_result'] = resultado
                                            resultado['_n_excluidos'] = len(excluded_ids)
                                            # Sync header (TAREA-094): mostrar pool completo en fallback
                                            _meta['n_propiedades'] = len(comps_filtrados)
                                            print(f"[DEBUG-SYNC-HEADER] {prop_name}: fallback, n_propiedades={len(comps_filtrados)}")
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
                                        import copy
                                        st.session_state[f'_official_result_{prop_name}'] = copy.deepcopy(resultado)
                                        print(f"[DEBUG-OFFICIAL] {prop_name}: resultado oficial guardado en session_state")
                                        print(f"[APPLY] {prop_name}: Persistida exclusión de {len(excluded_ids)} comps a cache+propiedades")
                                    except Exception as e:
                                        logger.warning(f"[APPLY] {prop_name}: No se pudo persistir exclusión: {e}")
                                    finally:
                                        # Limpiar flag de forzar recalculo para evitar re-ejecuciones infinitas
                                        if f'forzar_recalculo_{prop_name}' in st.session_state:
                                            del st.session_state[f'forzar_recalculo_{prop_name}']
                                            print(f"[DEBUG-FLOW] {prop_name}: forzar_recalculo limpiado post-persist")
                                else:
                                    if preview_mode:
                                        print(f"[DEBUG-PERSIST-SKIP] {prop_name}: preview activo, NO persiste (from_apply={from_apply}, excluded={excluded_ids})")
                                    if resultado.get('_comp_exclusion_applied'):
                                        print(f"[DEBUG-EXCL-FLAG] {prop_name}: _comp_exclusion_applied ya=True, PRESERVADO (from_apply=False, guard_restored={resultado.get('_cache', {}).get('guard_restored')}, _cache.recalculado={resultado.get('_cache', {}).get('recalculado')})")
                                    else:
                                        resultado['_comp_exclusion_applied'] = False

                with profile_block("mostrar_detalle_valu_total", p_obj):
                    # ── Guardar resultado oficial si no existe (primera valuación / post-Limpiar) ──
                    if not preview_mode:
                        official_key = f'_official_result_{prop_name}'
                        if official_key not in st.session_state:
                            import copy
                            st.session_state[official_key] = copy.deepcopy(resultado)
                            print(f"[DEBUG-OFFICIAL-FIRST] {prop_name}: resultado oficial guardado por primera vez, valor=${resultado.get('valor_propiedad_usd',0):,.0f}, n_prop={resultado.get('resolution_metadata',{}).get('n_propiedades')}")
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

        # ─── Comparables Manuales ───
        st.markdown("---")
        with st.expander("📋 Comparables Manuales", expanded=False):
            from parsers.manual_comparables import load_data, save_data, get_manual_comparables, get_scraping_comparables, add_manual, update_manual, delete_manual
            _data = load_data()
            _manual_list = get_manual_comparables(_data)
            _scraping_list = get_scraping_comparables(_data)
            st.caption(f"📊 **{len(_manual_list)}** comparables manuales de **{len(_manual_list) + len(_scraping_list)}** totales en cache_scraping.json")
            if _manual_list:
                _cols = ["id_manual", "precio", "moneda", "m2", "dormitorios", "tipo", "operacion", "calle_limpia", "numero_limpio", "lat", "lon", "date_created"]
                _rows = []
                for p in _manual_list:
                    _row = {k: p.get(k, "") for k in _cols}
                    _row["_id"] = p.get("id_manual", "")
                    _rows.append(_row)
                st.data_editor(
                    _rows,
                    column_config={
                        "id_manual": st.column_config.TextColumn("ID", disabled=True, width="small"),
                        "precio": st.column_config.NumberColumn("Precio", format="$%.0f"),
                        "moneda": st.column_config.SelectboxColumn("Moneda", options=["USD", "ARS"]),
                        "m2": st.column_config.NumberColumn("m²", format="%.1f"),
                        "dormitorios": st.column_config.NumberColumn("Dorms", format="%d"),
                        "tipo": st.column_config.SelectboxColumn("Tipo", options=["Departamento", "Casa", "Cochera", "Local", "Oficina", "PH", "Terreno"]),
                        "operacion": st.column_config.SelectboxColumn("Oper.", options=["venta", "alquiler"]),
                        "calle_limpia": st.column_config.TextColumn("Calle", width="medium"),
                        "numero_limpio": st.column_config.NumberColumn("Nro", format="%d"),
                        "lat": st.column_config.NumberColumn("Lat", format="%.6f"),
                        "lon": st.column_config.NumberColumn("Lon", format="%.6f"),
                        "date_created": st.column_config.TextColumn("Creado", disabled=True, width="small"),
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="manual_comparables_editor",
                )
                for p in _manual_list:
                    _mid = p.get("id_manual", "")
                    _cols3 = st.columns([2, 1, 1])
                    with _cols3[0]:
                        st.caption(f"**{p.get('calle_limpia', '?')} {p.get('numero_limpio', '') or ''}** — ${p.get('precio', 0):,.0f} — {p.get('m2', 0):.0f}m²")
                    with _cols3[1]:
                        _edit_key = f"edit_manual_{_mid}"
                        if st.session_state.get(_edit_key, False):
                            if st.button("❌ Cerrar", key=f"close_edit_{_mid}"):
                                st.session_state[_edit_key] = False
                                st.rerun()
                        else:
                            if st.button("✏️ Editar", key=f"btn_edit_{_mid}"):
                                st.session_state[_edit_key] = True
                                st.rerun()
                    with _cols3[2]:
                        _del_key = f"delete_confirm_{_mid}"
                        if st.session_state.get(_del_key, False):
                            c1, c2 = st.columns(2)
                            with c1:
                                if st.button("🗑️ Sí", key=f"confirm_del_{_mid}", type="primary"):
                                    delete_manual(_mid)
                                    st.session_state.pop(_del_key, None)
                                    st.rerun()
                            with c2:
                                if st.button("Cancelar", key=f"cancel_del_{_mid}"):
                                    st.session_state.pop(_del_key, None)
                                    st.rerun()
                        else:
                            if st.button("🗑️ Eliminar", key=f"btn_del_{_mid}"):
                                st.session_state[_del_key] = True
                                st.rerun()
                    if st.session_state.get(_edit_key, False):
                        st.markdown("---")
                        _edit_prop = p
                        with st.form(key=f"form_edit_{_mid}"):
                            st.markdown(f"**Editando:** {_edit_prop.get('calle_limpia', '')} {_edit_prop.get('numero_limpio', '') or ''}")
                            ec1, ec2 = st.columns(2)
                            with ec1:
                                edit_precio = st.number_input("Precio ($)", value=float(_edit_prop.get("precio", 0)), min_value=0.0, step=1000.0, key=f"ep_{_mid}")
                                edit_moneda = st.selectbox("Moneda", ["USD", "ARS"], index=0 if _edit_prop.get("moneda") == "USD" else 1, key=f"em_{_mid}")
                                edit_m2 = st.number_input("m²", value=float(_edit_prop.get("m2", 0)), min_value=1.0, step=1.0, key=f"em2_{_mid}")
                                edit_dorms = st.number_input("Dormitorios", value=int(_edit_prop.get("dormitorios", 1)), min_value=0, max_value=20, step=1, key=f"ed_{_mid}")
                                edit_tipo = st.selectbox("Tipo", ["Departamento", "Casa", "Cochera", "Local", "Oficina", "PH", "Terreno"],
                                                         index=["Departamento", "Casa", "Cochera", "Local", "Oficina", "PH", "Terreno"].index(_edit_prop.get("tipo", "Departamento")), key=f"et_{_mid}")
                                edit_operacion = st.selectbox("Operación", ["venta", "alquiler"],
                                                               index=0 if _edit_prop.get("operacion") == "venta" else 1, key=f"eo_{_mid}")
                            with ec2:
                                edit_calle = st.text_input("Calle", value=_edit_prop.get("calle_limpia", ""), key=f"ec_{_mid}")
                                edit_num = st.number_input("Número", value=int(_edit_prop.get("numero_limpio", 0)) if _edit_prop.get("numero_limpio") else 0, min_value=0, step=1, key=f"en_{_mid}")
                                edit_direccion = st.text_input("Dirección (completa)", value=_edit_prop.get("direccion", ""), key=f"edir_{_mid}")
                                edit_lat = st.number_input("Latitud", value=float(_edit_prop.get("lat", -32.95)), format="%.6f", key=f"elat_{_mid}")
                                edit_lon = st.number_input("Longitud", value=float(_edit_prop.get("lon", -60.66)), format="%.6f", key=f"elon_{_mid}")
                            if st.form_submit_button("💾 Guardar Cambios", type="primary"):
                                _upd = {
                                    "precio": edit_precio, "moneda": edit_moneda, "m2": edit_m2,
                                    "dormitorios": edit_dorms, "tipo": edit_tipo, "operacion": edit_operacion,
                                    "calle_limpia": edit_calle, "numero_limpio": edit_num, "direccion": edit_direccion,
                                    "lat": edit_lat, "lon": edit_lon,
                                }
                                update_manual(_mid, _upd)
                                st.session_state[_edit_key] = False
                                st.rerun()
            else:
                st.info("No hay comparables manuales. Añade uno usando el formulario de abajo.")
            st.markdown("---")
            _show_add = st.checkbox("➕ Añadir nuevo comparable manual", key="show_add_manual")
            if _show_add:
                with st.form(key="form_add_manual"):
                    ac1, ac2 = st.columns(2)
                    with ac1:
                        add_precio = st.number_input("Precio ($)", min_value=0.0, step=1000.0, value=50000.0, key="ap")
                        add_moneda = st.selectbox("Moneda", ["USD", "ARS"], key="am")
                        add_m2 = st.number_input("m²", min_value=1.0, step=1.0, value=50.0, key="am2")
                        add_dorms = st.number_input("Dormitorios", min_value=0, max_value=20, step=1, value=2, key="ad")
                        add_tipo = st.selectbox("Tipo", ["Departamento", "Casa", "Cochera", "Local", "Oficina", "PH", "Terreno"], key="at")
                        add_operacion = st.selectbox("Operación", ["venta", "alquiler"], key="ao")
                    with ac2:
                        add_calle = st.text_input("Calle", key="acalle")
                        add_num = st.number_input("Número", min_value=0, step=1, value=0, key="anum")
                        add_direccion = st.text_input("Dirección (completa, opcional)", key="adir")
                        add_lat = st.number_input("Latitud", value=-32.95, format="%.6f", key="alat")
                        add_lon = st.number_input("Longitud", value=-60.66, format="%.6f", key="alon")
                    if st.form_submit_button("💾 Guardar Comparable", type="primary"):
                        _add_data = {
                            "precio": add_precio, "moneda": add_moneda, "m2": add_m2,
                            "dormitorios": add_dorms, "tipo": add_tipo, "operacion": add_operacion,
                            "calle_limpia": add_calle, "numero_limpio": add_num, "direccion": add_direccion,
                            "lat": add_lat, "lon": add_lon,
                        }
                        add_manual(_add_data)
                        st.success("Comparable manual guardado en cache_scraping.json")
                        st.session_state["show_add_manual"] = False
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
