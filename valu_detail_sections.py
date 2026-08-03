"""
Secciones del detalle de propiedad. Funciones de renderizado UI puras.
Cada funcion recibe datos y renderiza una seccion especifica.
Son llamadas desde mostrar_detalle_valu() en valu.py.
"""
import streamlit as st
import pandas as pd
import json, os, sys, logging

logger = logging.getLogger(__name__)
from datetime import datetime
from valu_design import kpi_card, metric_card, range_bar, insights_card, property_card
from streamlit.components.v1 import html
from parsers.mercado_inmobiliario import calcular_vm2_por_seleccion
from parsers.location_engine import obtener_precio_oficial, cargar_precios_oficiales
from parsers.debug_logger import log as _file_log

def _safe_key(name):
    """Sanitiza nombre de propiedad para usar como key de widget Streamlit."""
    return name.replace(" ", "_").replace(".", "").replace(",", "").replace("'", "").replace('"', "").replace("/", "_").replace("\\", "_").replace("(", "").replace(")", "").replace("-", "_")

_orig_print = print
def _dbg_print(*args, **kwargs):
    _orig_print(*args, **kwargs)
    msg = ' '.join(str(a) for a in args)
    if msg.startswith(('[DEBUG', '[CACHE')):
        _file_log(msg)
print = _dbg_print


def render_actions(prop, guardar_fn):
    """Barra de acciones: Volver, Editar, Eliminar."""
    nombre = prop.get('nombre', '')
    prop_id = prop.get('id', nombre)
    col_back, col_edit, col_delete = st.columns([1.5, 1, 1.5])
    with col_back:
        if st.button("← Volver al Portafolio", type="primary", use_container_width=True,
                     key=f"action_volver_{prop_id}"):
            from valu import _limpiar_estado_propiedad
            _limpiar_estado_propiedad(nombre)
            st.session_state.prop_sel = None
            st.session_state['_force_nav_page'] = 'Portfolio'
            if 'prop' in st.query_params:
                st.query_params.clear()
            st.rerun()
    with col_edit:
        if st.button("Editar", type="primary", use_container_width=True,
                     key=f"action_editar_{prop_id}"):
            st.session_state[f"edit_{prop_id}"] = True
    with col_delete:
        if st.button("Eliminar", type="primary", use_container_width=True,
                     key=f"action_eliminar_{prop_id}"):
            st.session_state[f"delete_confirm_{prop_id}"] = True

    # Confirmacion de eliminacion
    if st.session_state.get(f"delete_confirm_{prop_id}", False):
        st.warning(f"Confirma que desea eliminar la propiedad **{nombre}**?")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Si, eliminar", type="primary", use_container_width=True,
                         key=f"action_confirm_delete_{prop_id}"):
                props = cargar_propiedades()
                props = [p for p in props if p.get('id') != prop_id]
                guardar_propiedades(props)
                # Invalidar cache de valuación
                try:
                    from parsers.valuacion_cache import cargar_cache_valuaciones, guardar_cache_valuaciones
                    cache_v = cargar_cache_valuaciones()
                    cache_v.pop(nombre, None)
                    guardar_cache_valuaciones(cache_v)
                except Exception:
                    pass
                st.session_state.pop(f"delete_confirm_{prop_id}", None)
                st.session_state.prop_sel = None
                st.rerun()
        with c2:
            if st.button("Cancelar", use_container_width=True,
                         key=f"action_cancel_delete_{prop_id}"):
                st.session_state.pop(f"delete_confirm_{prop_id}", None)
                st.rerun()

    if st.session_state.get(f"edit_{prop_id}", False):
        from valu_forms import ui_formulario_propiedad
        # Usamos un key_suffix único para evitar colisiones y habilitamos el geocoding automático reactivo
        new_data = ui_formulario_propiedad(prop_inicial=prop, key_suffix=f"edit_{prop_id}", show_geocode=True)
        
        col_b1, col_b2 = st.columns(2)
        with col_b1:
            if st.button("Guardar Cambios", type="primary", key=f"save_edit_{prop_id}", use_container_width=True):
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
                keys_to_clear = [k for k in st.session_state.keys() if k.endswith(f"_edit_{prop_id}")]
                for k in keys_to_clear:
                    st.session_state.pop(k, None)
                st.session_state[f"edit_{prop_id}"] = False
                st.rerun()
                
        with col_b2:
            if st.button("Cancelar", key=f"cancel_edit_{prop_id}", use_container_width=True):
                # Limpiar el estado de edición al cancelar
                keys_to_clear = [k for k in st.session_state.keys() if k.endswith(f"_edit_{prop_id}")]
                for k in keys_to_clear:
                    st.session_state.pop(k, None)
                st.session_state[f"edit_{prop_id}"] = False
                st.rerun()


def _set_fuente_activa(nombre, fuente):
    """Persiste la fuente activa (auto/manual) en _ultima_valuacion."""
    props = cargar_propiedades()
    for p in props:
        if p.get('nombre') == nombre:
            uv = p.setdefault('_ultima_valuacion', {})
            print(f"[DEBUG-FUENTE] {nombre}: UV antes de cambiar fuente_activa a {fuente}: valor_usd={uv.get('valor_usd')}, comps={uv.get('comps')}, tiene_fuente={'fuente_activa' in uv}, previa_fuente={uv.get('fuente_activa')}")
            uv['fuente_activa'] = fuente
            break
    guardar_propiedades(props)
    st.session_state[f'fuente_activa_{nombre}'] = fuente
    print(f"[DEBUG-FUENTE] {nombre}: fuente_activa={fuente} persistida en propiedades.json + session_state")


def render_header(prop, res):
    """Hero con badges, titulo, confianza, precio y selector de fuente (Auto/Manual)."""
    from datetime import datetime
    nombre = prop.get('nombre', '')

    # Leer datos paralelos
    auto_result = res.get('_auto_result', res)
    manual_result = res.get('_manual_result')
    manual_params = res.get('_manual_params') or {}
    fuente_activa = res.get('_fuente_activa', 'auto')

    auto_valor_usd_raw = auto_result.get('valor_propiedad_usd', 0) if auto_result else 0
    manual_valor_usd_raw = manual_result.get('valor_propiedad_usd', 0) if manual_result else 0

    # Detectar si auto_result es real o es fallback TAREA-102
    is_fallback = auto_result.get('_fallback_uv', False) if auto_result else False
    auto_viene_de = 'motor' if not is_fallback else 'fallback-102'
    uv_dict = prop.get('_ultima_valuacion', {})
    auto_fuente_uv = uv_dict.get('fuente', 'N/A')
    auto_valor_uv = uv_dict.get('valor_usd', 'N/A')
    auto_valor_uv_auto = uv_dict.get('auto_valor_usd', 'N/A')
    auto_valor_uv_manual = uv_dict.get('manual_valor_usd', 'N/A')

    print(f"[DEBUG-HEADER] {nombre}: render_header inicio, "
          f"fuente_activa={fuente_activa}, "
          f"auto_result_from={auto_viene_de}, "
          f"auto_valor={auto_valor_usd_raw}, "
          f"manual_valor={manual_valor_usd_raw}, "
          f"UV:fuente={auto_fuente_uv}, UV:valor_usd={auto_valor_uv}, "
          f"UV:auto_valor_usd={auto_valor_uv_auto}, UV:manual_valor_usd={auto_valor_uv_manual}")

    # Valor activo según fuente
    if fuente_activa == 'manual' and manual_result:
        display = manual_result
        es_manual = True
    else:
        display = auto_result
        es_manual = False

    valor_usd = display.get('valor_propiedad_usd', 0)
    dolar = display.get('usdt_ars', 1480)
    meta = display.get('resolution_metadata', {})
    m2_base = display.get('m2_base_venta', 0)
    m2_microzona = display.get('m2_microzona', m2_base)  # anchor override if any
    size_discount = display.get('size_discount', 1.0)
    activos_total = display.get('valor_activos_total', 0)
    m2_equiv_display = display.get('m2_equivalentes', 0)
    m2_puro = meta.get('_m2_puro', m2_base)
    barrier_pct = meta.get('barrier_pct', 0)
    n_comps = (auto_result.get('resolution_metadata') or {}).get('n_propiedades', 0) if auto_result else 0

    # Calcular divergencia manual vs auto (si hay manual)
    delta_pct = 0
    if manual_result and auto_result:
        v_manual = manual_result.get('valor_propiedad_usd', 0)
        v_auto = auto_result.get('valor_propiedad_usd', 0)
        if v_auto > 0:
            delta_pct = ((v_manual - v_auto) / v_auto) * 100

    # Staleness check
    staleness_msg = ""
    if manual_params and fuente_activa == 'manual':
        fecha_guardado = manual_params.get('fecha_guardado', '')
        auto_snapshot = manual_params.get('valor_auto_snapshot', 0)
        if fecha_guardado and auto_snapshot > 0:
            try:
                dt = datetime.fromisoformat(fecha_guardado)
                dias = (datetime.now() - dt).days
                auto_nuevo = auto_result.get('valor_propiedad_usd', 0)
                drift = abs(auto_nuevo - auto_snapshot) / auto_snapshot * 100 if auto_snapshot > 0 else 0
                if dias > 30 and drift > 5:
                    staleness_msg = f"⚠️ Valuación manual guardada hace {dias} días. El mercado se movió {drift:.0f}% desde entonces."
            except:
                pass

    zona = prop.get('zona', 'Oeste')

    # ─── Dual Valuation Cards (display-only, siempre ambos activos) ───
    tiene_auto = auto_result.get('m2_base_venta', 0) > 0
    tiene_manual = manual_result is not None
    print(f"[DEBUG-HEADER-CARDS] {nombre}: tiene_auto={tiene_auto}, tiene_manual={tiene_manual}, "
          f"auto_m2_base={auto_result.get('m2_base_venta', 0) if auto_result else 0}, "
          f"fallback={auto_result.get('_fallback_uv', False) if auto_result else False}")

    v_auto = auto_result.get('valor_propiedad_usd', 0) if auto_result else 0
    v_manual = manual_result.get('valor_propiedad_usd', 0) if manual_result else 0
    n_comps_auto = (auto_result.get('resolution_metadata') or {}).get('n_propiedades', 0) if auto_result else 0
    n_total_auto = (auto_result.get('resolution_metadata') or {}).get('n_pool_total', n_comps_auto) if auto_result else n_comps_auto
    dolar_auto = auto_result.get('usdt_ars', dolar) if auto_result else dolar
    m2_micro_auto = (auto_result.get('m2_microzona', auto_result.get('m2_base_venta', 0))
                     if auto_result else 0)
    m2_line_auto = f"m²/USD en {zona}: ${m2_micro_auto:,.0f} ({n_total_auto} comp.)" if m2_micro_auto > 0 else "—"
    # Componentes de fórmula SIEMPRE desde auto_result (no display)
    auto_m2_equiv = auto_result.get("m2_equivalentes", 0) if auto_result else 0
    auto_size_discount = auto_result.get("size_discount", 1.0) if auto_result else 1.0
    auto_activos_total = auto_result.get("valor_activos_total", 0) if auto_result else 0

    print(f"[DEBUG-HEADER-FORMULA] {nombre}: formula: "
          f"m2_micro_auto={m2_micro_auto:.2f}, m2_equiv={auto_m2_equiv:.1f}, "
          f"size_discount={auto_size_discount:.3f}, activos={auto_activos_total:.0f}, "
          f"v_auto={v_auto:.0f}, display_m2_microzona={m2_microzona:.2f}")

    # ── Ocultar valuación en header si:
    # 1. Insuficientes comparables (< 3)
    # 2. Es un preview y NO existe una valuación oficial (ya_valuado=False)
    #
    # RU-HEADER-01: El auto card usa n_comps_auto (del AUTO engine), NO n_comps del display
    #   (que sigue a fuente_activa). Esto evita que el auto card muestre un valor STALE
    #   del cache preview después de un save manual que setea fuente_activa=manual.
    # RU-HEADER-02: El auto card se oculta adicionalmente si está en preview mode y
    #   no hay un auto_valor_usd oficial en UV (evita fuga de valor manual en auto card).
    ya_valuado = bool(uv_dict.get('valor_usd'))
    preview_mode = res.get('_cache', {}).get('preview', False)
    n_comps_auto_hide = (auto_result.get('resolution_metadata') or {}).get('n_propiedades', 0) if auto_result else 0
    
    ocultar_auto = n_comps_auto_hide < 3 or (fuente_activa == 'manual' and not uv_dict.get('auto_valor_usd', 0) > 0)
    if n_comps_auto_hide < 3 or (preview_mode and not ya_valuado):
        print(f"[DEBUG-INSUF-COMPS] {nombre}: n_comps_auto_hide={n_comps_auto_hide}, preview={preview_mode}, ya_valuado={ya_valuado}, "
              f"ocultando solo auto card (manual preservado). v_auto_antes={v_auto}, v_manual_antes={v_manual}, "
              f"UV:auto_valor_usd={auto_valor_uv_auto}, UV:manual_valor_usd={auto_valor_uv_manual}")
        valor_usd = 0
        m2_microzona = 0
        v_auto = 0
        m2_micro_auto = 0
        m2_line_auto = "—"
    elif ocultar_auto:
        print(f"[DEBUG-INSUF-COMPS] {nombre}: ocultando solo auto card. n_comps_auto_hide={n_comps_auto_hide}, "
              f"preview={preview_mode}, uv_auto_valor_usd={auto_valor_uv_auto}, "
              f"fuente_activa={fuente_activa}, "
              f"v_manual_ok={v_manual}, v_auto_antes={v_auto}")
        v_auto = 0
        m2_micro_auto = 0
        m2_line_auto = "—"

    dolar_manual = manual_result.get('usdt_ars', dolar) if manual_result else dolar
    m2_base_manual = manual_result.get('m2_base_venta', 0) if manual_result else 0
    n_comps_manual = (manual_result.get('resolution_metadata') or {}).get('n_propiedades', 0) if manual_result else 0
    m2_line_manual = f"m²/USD: ${m2_base_manual:,.0f} ({n_comps_manual} comp.)" if m2_base_manual > 0 else "—"

    card_key = f'fuente_cards_{nombre}'

    # ─── Spacer ───
    st.markdown("<div style='margin:12px 0;'></div>", unsafe_allow_html=True)

    # ─── Alertas de divergencia ───
    tiene_manual = manual_result is not None
    if tiene_manual and not es_manual and abs(delta_pct) > 10:
        severity = "🔴" if abs(delta_pct) > 20 else "⚠️"
        color = "#DC2626" if abs(delta_pct) > 20 else "#D97706"
        st.markdown(
            f"<span style='color:{color};font-size:13px;font-weight:600;'>"
            f"{severity} Tu valuación manual difiere {abs(delta_pct):.0f}% del motor por comparables."
            f"</span>",
            unsafe_allow_html=True
        )

    # ─── Alerta de staleness ───
    if staleness_msg:
        st.warning(staleness_msg)

    # ─── Property info card ───
    _meta = (auto_result.get('resolution_metadata') or {}) if auto_result else {}
    _percentil = _meta.get('percentil_usado', 'P33')
    dot = '#16A34A' if _percentil == 'P50' else '#F59E0B' if _percentil in ('P45', 'P40') else '#DC2626'
    conf = 'Alta confianza' if _percentil == 'P50' else 'Confianza media' if _percentil in ('P45', 'P40') else 'Confianza baja'
    n_total = (auto_result.get('resolution_metadata') or {}).get('n_pool_total', n_comps) if auto_result else n_comps
    n_mostr = (auto_result.get('resolution_metadata') or {}).get('n_mostrados', n_comps) if auto_result else n_comps
    if n_total > n_mostr:
        count_str = f"({n_total} comparables, {n_mostr} en pantalla)"
    else:
        count_str = f"({n_comps} comparables)"
    st.markdown(f"""
    <div style="background:white;border-radius:16px;padding:28px;box-shadow:0 4px 12px rgba(0,0,0,0.08);">
        <div style="margin-bottom:12px;">
            <span class="badge" style="background:#006AFF15;color:#006AFF;">{prop.get('tipo_inmueble','').upper()}</span>
            <span class="badge" style="background:#0D948815;color:#0D9488;margin-left:5px;">{zona.upper()}</span>
            <span class="badge" style="background:#F4F6FB;color:#6B7280;margin-left:5px;">Año {prop.get('anio_construccion','?')}</span>
        </div>
        <h1 style="color:#1A2B5C;margin:0;font-size:36px;"> {nombre}</h1>
        <p style="color:#6B7280;font-size:16px;">{prop.get('direccion', 'Rosario, Argentina')}</p>
        <div style="display:flex;align-items:center;margin-top:20px;">
            <span style="width:12px;height:12px;border-radius:50%;background:{dot};margin-right:8px;"></span>
            <span style="color:#1A2B5C;font-weight:600;font-size:14px;">{conf}</span>
            <span style="color:#9CA3AF;font-size:14px;margin-left:8px;">{count_str}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_disk_summary_card(prop, insuficientes=False, v_cons=0, v_opt=0, spread=0):
    """Tarjeta full-width que muestra la última valuación guardada en disco (_ultima_valuacion).
    Solo para valuación por comparables (auto). No toca session state.
    Lee directamente de propiedades.json para evitar stale data del ciclo de render.
    Si v_cons > 0 y v_opt > 0, incluye la barra de rango Conservador|Spread|Optimista dentro de la tarjeta."""
    import json, os
    nombre = prop.get('nombre', '')
    uv = {}
    try:
        props_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'propiedades.json')
        with open(props_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for p in data.get('propiedades', []):
            if p.get('nombre') == nombre:
                uv = p.get('_ultima_valuacion', {}) or {}
                break
    except Exception:
        uv = prop.get('_ultima_valuacion', {}) or {}

    auto_valor = uv.get('auto_valor_usd', 0)
    comps = uv.get('comps', 0)
    if isinstance(comps, list):
        comps = len(comps)
    m2_equiv = uv.get('m2_equivalentes', 0)
    m2_micro = uv.get('m2_microzona', 0)
    size_discount = uv.get('size_discount', 1.0)
    activos_total = uv.get('valor_activos_total', 0)
    fecha = uv.get('fecha', '')

    if insuficientes:
        meta_line = "Sin Valor"
        formula_line = "Comparables insuficientes para calcular"
    elif auto_valor > 0:
        valor_str = f"${auto_valor:,.0f}"
        comps_str = f"{comps} comp." if comps else "—"
        m2_str = f"{m2_equiv:.1f} m²" if m2_equiv else "—"
        meta_line = f"{valor_str} USD · {comps_str} · {m2_str}"
        if m2_micro > 0 and m2_equiv > 0:
            formula_line = f"${m2_micro:,.0f}/m² × {m2_equiv:.1f} m² × {size_discount:.3f} ajuste + ${activos_total:,.0f} extras = ${auto_valor:,.0f}"
        else:
            formula_line = fecha
    else:
        meta_line = "—"
        formula_line = "Sin valuación guardada"

    _range_text = ""
    if v_cons > 0 and v_opt > 0:
        _range_text = f"Conservador ${v_cons:,.0f} · Spread {spread:.1f}% · Optimista ${v_opt:,.0f}"

    grad_disk = "linear-gradient(135deg, #374151 0%, #1F2937 100%)"
    st.markdown(f"""
    <div style="border:none;border-radius:12px;padding:14px 16px;background:{grad_disk};box-shadow:0 4px 12px rgba(0,0,0,0.15);text-align:center;">
        <div style="font-size:12px;font-weight:600;color:rgba(255,255,255,0.7);margin-bottom:4px;">VALUACIÓN POR COMPARABLES</div>
        <div style="font-size:15px;font-weight:600;color:#FFFFFF;">{meta_line}</div>
        <div style="font-size:11px;color:rgba(255,255,255,0.55);margin-top:2px;">{formula_line}</div>
        <div style="font-size:11px;color:rgba(255,255,255,0.5);margin-top:6px;padding-top:6px;border-top:1px solid rgba(255,255,255,0.15);">{_range_text}</div>
    </div>
    """, unsafe_allow_html=True)


def render_manual_valuation_card(prop):
    """Tarjeta full-width que muestra la última valuación manual guardada en disco.
    Completamente independiente de la valuación por comparables.
    Lee directamente de propiedades.json para evitar stale data del ciclo de render."""
    import json, os
    nombre = prop.get('nombre', '')
    uv = {}
    try:
        props_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'propiedades.json')
        with open(props_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for p in data.get('propiedades', []):
            if p.get('nombre') == nombre:
                uv = p.get('_ultima_valuacion', {}) or {}
                break
    except Exception:
        uv = {}

    if not uv:
        uv = prop.get('_ultima_valuacion', {}) or {}

    manual_valor = uv.get('manual_valor_usd', 0)
    manual_params = uv.get('manual_params', {}) or {}
    m2_equiv = uv.get('m2_equivalentes', 0)
    usdt_ars = uv.get('usdt_ars', 0)
    fecha = uv.get('fecha', '')

    if manual_valor > 0 and manual_params:
        usd_m2 = manual_params.get('usd_m2', 0)
        fh = manual_params.get('factor_hedonico', 1.0)
        ajuste = manual_params.get('ajuste_pct', 0)
        incert = manual_params.get('incertidumbre_pct', 0)
        ancla = manual_params.get('ancla_id', '—')

        size_adj = uv.get('manual_size_adj')
        factor_const = uv.get('manual_factor_const')
        activos_total = uv.get('manual_activos_total')
        constr = uv.get('manual_constructora', '')

        if size_adj is None:
            try:
                from parsers.mercado_inmobiliario import calcular_size_adjustment
                from parsers.zonas_manager import resolver_macrozona
                _mz = resolver_macrozona(prop)
                size_adj = calcular_size_adjustment(m2_equiv, macrozona_id=_mz.get('macrozona_id'), ancla_id=ancla, dormitorios=prop.get('dormitorios'))
            except Exception:
                size_adj = 1.0
        if factor_const is None:
            factor_const = 1.0
            try:
                constr_nombre = prop.get('constructora', '')
                if constr_nombre:
                    import os, json as _json
                    constr_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'constructoras_rosario.json')
                    if os.path.exists(constr_path):
                        with open(constr_path, 'r', encoding='utf-8') as f:
                            for entry in _json.load(f):
                                if constr_nombre.lower().strip() == entry.get('descripcion', '').lower().strip():
                                    pct = entry.get('porcentaje', 0)
                                    if manual_params.get('incluir_prima_const', True):
                                        factor_const = 1.0 + pct / 100.0
                                    constr = constr_nombre
                                    break
            except Exception:
                pass
        if activos_total is None:
            try:
                from parsers.mercado_inmobiliario import calcular_valor_activos
                activos_total = calcular_valor_activos(prop, usd_m2).get('total', 0)
            except Exception:
                activos_total = 0

        valor_str = f"${manual_valor:,.0f}"
        m2_str = f"{m2_equiv:.1f} m²" if m2_equiv else "—"
        fh_str = f"FH {fh:.2f}" if fh != 1.0 else ""
        ajuste_str = f"ajuste {ajuste:+.0f}%" if ajuste != 0 else ""
        const_str = f"Const {factor_const:.2f}" if factor_const != 1.0 else ""
        size_str = f"size {size_adj:.3f}" if size_adj != 1.0 else ""
        meta_parts = [x for x in [valor_str, f"${usd_m2:,.0f}/m²", m2_str, fh_str, const_str, size_str, ajuste_str] if x]
        meta_line = " · ".join(meta_parts)

        formula_parts = [f"${usd_m2:,.0f}/m² × {m2_equiv:.1f} m²"]
        if size_adj != 1.0:
            formula_parts.append(f"× {size_adj:.3f} size")
        if fh != 1.0:
            formula_parts.append(f"× {fh:.2f} FH")
        if factor_const != 1.0:
            formula_parts.append(f"× {factor_const:.2f} const")
        if activos_total > 0:
            formula_parts.append(f"+ ${activos_total:,.0f} activos")
        formula_line = " ".join(formula_parts) + f" = ${manual_valor:,.0f}"

        conservador = manual_valor * (1 - incert / 100) if incert else 0
        optimista = manual_valor * (1 + incert / 100) if incert else 0
        if conservador > 0 and optimista > 0:
            formula_line += f" · rango ${conservador:,.0f}–${optimista:,.0f}"

        param_line = f"Ancla: {ancla}"
        if constr:
            param_line += f" · Constructora: {constr}"
        if fh != 1.0:
            param_line += f" · FH: {fh:.2f}"
        if incert:
            param_line += f" · Incertidumbre: {incert:.0f}%"

        _range_text = ""
        if conservador > 0 and optimista > 0:
            _spread_manual = ((optimista - conservador) / manual_valor * 100) if manual_valor > 0 else 0
            _range_text = f"Conservador ${conservador:,.0f} · Spread {_spread_manual:.1f}% · Optimista ${optimista:,.0f}"
    else:
        meta_line = "—"
        formula_line = "Sin valuación manual guardada"
        param_line = ""
        _range_text = ""

    grad_manual = "linear-gradient(135deg, #6B21A8 0%, #4C1D95 100%)"
    _range_div = f'<div style="font-size:11px;color:rgba(255,255,255,0.5);margin-top:6px;padding-top:6px;border-top:1px solid rgba(255,255,255,0.15);">{_range_text}</div>' if _range_text else ''
    st.markdown(f"""
    <div style="border:none;border-radius:12px;padding:14px 16px;background:{grad_manual};box-shadow:0 4px 12px rgba(0,0,0,0.15);text-align:center;">
        <div style="font-size:12px;font-weight:600;color:rgba(255,255,255,0.7);margin-bottom:4px;">VALUACIÓN MANUAL</div>
        <div style="font-size:15px;font-weight:600;color:#FFFFFF;">{meta_line}</div>
        <div style="font-size:11px;color:rgba(255,255,255,0.55);margin-top:2px;">{formula_line}</div>
        {'<div style="font-size:10px;color:rgba(255,255,255,0.4);margin-top:2px;">' + param_line + '</div>' if param_line else ''}
        {_range_div}
    </div>
    """, unsafe_allow_html=True)


def render_rango(res, valor_usd):
    """Rango de 3 escenarios con barra visual."""
    v_cons = res.get('valor_venta_conservador', valor_usd)
    v_opt = res.get('valor_venta_optimista', valor_usd)
    st.markdown(range_bar(v_cons, v_opt, res.get('rango_venta', {}).get('spread_pct', 0)), unsafe_allow_html=True)


def _recalcular_alquiler(prop, res, auto_result=None, manual_result=None):
    """Recalcula alquiler usando lógica unificada (3 casos).
    Usado tanto por render_metricas (UI) como generar_reporte_pdf (PDF).

    Returns:
        dict con keys: alq_ars, alq_min, alq_max, cap_rate, dolar
    """
    from parsers.mercado_inmobiliario import ROI_ZONAL
    from parsers.motor_vpp_core import get_binance_usdt_ars

    alq_ars = res.get('alquiler_estimado_ars', 0)
    cap = res.get('cap_rate', 0)
    dolar = res.get('usdt_ars', 1480.0)

    zona_txt = prop.get('zona', '') or ''
    zona_key = zona_txt.lower().strip() if zona_txt else 'centro'
    cap_rate_zonal = ROI_ZONAL.get(zona_key, 0.050)

    # Leer valor manual del disco si no hay manual_result en sesión
    if not manual_result:
        try:
            import json, os
            props_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'propiedades.json')
            with open(props_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            nombre = prop.get('nombre', '')
            for p in data.get('propiedades', []):
                if p.get('nombre') == nombre:
                    uv = p.get('_ultima_valuacion', {}) or {}
                    manual_v = uv.get('manual_valor_usd', 0)
                    if manual_v > 0:
                        manual_result = {'valor_propiedad_usd': manual_v}
                    break
        except Exception:
            pass

    # ─── LÓGICA DE ALQUILER SEGÚN CASO ───
    if auto_result and manual_result:
        best_valor = auto_result.get('valor_propiedad_usd', res.get('valor_propiedad_usd', 0))
        best_cap = auto_result.get('cap_rate', cap)
    elif manual_result and not auto_result:
        best_valor = manual_result.get('valor_propiedad_usd', res.get('valor_propiedad_usd', 0))
        best_cap = cap_rate_zonal
    else:
        manual_v = manual_result.get('valor_propiedad_usd', 0) if manual_result else 0
        if manual_v > 0:
            best_valor = manual_v
            best_cap = cap_rate_zonal
        else:
            best_valor = res.get('valor_propiedad_usd', 0)
            best_cap = cap_rate_zonal

    # Recalcular alquiler
    alq_min, alq_max = 0, 0
    if best_cap > 0 and best_valor > 0:
        try:
            dolar_fresh = get_binance_usdt_ars()
            if dolar_fresh > 0:
                alq_usd_calc = best_valor * best_cap / 12
                alq_ars = int(alq_usd_calc * dolar_fresh)
                alq_min = int(alq_ars * 0.85)
                alq_max = int(alq_ars * 1.15)
                dolar = dolar_fresh
                cap = best_cap
        except Exception:
            pass

    return {
        'alq_ars': alq_ars,
        'alq_min': alq_min,
        'alq_max': alq_max,
        'cap_rate': cap,
        'dolar': dolar,
    }


def render_metricas(prop, res, valor_usd, dolar, auto_result=None, manual_result=None):
    """Metricas de inversion: Alquiler, Cap Rate, Plusvalia.
    Lógica de alquiler unificada vía _recalcular_alquiler()."""
    recalc = _recalcular_alquiler(prop, res, auto_result=auto_result, manual_result=manual_result)
    alq_ars = recalc['alq_ars']
    alq_min = recalc['alq_min']
    alq_max = recalc['alq_max']
    cap = recalc['cap_rate']
    dolar = recalc['dolar']

    alq_usd = int(alq_ars / dolar) if dolar > 0 else 0
    alq_value = f"${alq_ars:,.0f} ARS / mes   USD {alq_usd:,}" if alq_usd > 0 else f"${alq_ars:,.0f} ARS / mes"
    alq_sub = f"Rango: ${alq_min:,.0f} – ${alq_max:,.0f}" if alq_min > 0 and alq_max > 0 else "Sin datos de rango"

    m1, m2, m3 = st.columns(3)
    with m1:
        st.markdown(metric_card("", "Alquiler", alq_value, alq_sub), unsafe_allow_html=True)
    with m2:
        st.markdown(metric_card("", "Rentabilidad Neta", f"{cap*100:.1f}% anual", f"Cierre est: ${valor_usd*0.92:,.0f} USD", border_color="#16A34A"), unsafe_allow_html=True)

    valor_compra = prop.get('valor_compra_usd', 0)
    with m3:
        if valor_compra > 0:
            gain = valor_usd - valor_compra
            pct = (gain/valor_compra)*100
            st.markdown(metric_card("", "Plusvalia", f"+${gain:,.0f} USD", f"{pct:+.1f}% desde compra", border_color="#F59E0B"), unsafe_allow_html=True)
        else:
            st.markdown(metric_card("", "Plusvalia", "-", "Sin datos de compra", border_color="#F59E0B"), unsafe_allow_html=True)

    # Tarjeta de Rentabilidad de la inversión
    expensas = prop.get('expensas_ars', 0)
    mantenimiento = int(alq_ars * 0.065) if alq_ars > 0 else 0
    vacancia = int(alq_ars * 0.04) if alq_ars > 0 else 0
    cap_rate_pct = cap * 100
    cap_rate_neto_pct = cap_rate_pct * 0.92

    rentabilidad_html = f"""
    <div style="background:white;border-radius:16px;padding:20px 24px;box-shadow:0 4px 12px rgba(0,0,0,0.08);margin-top:12px;">
        <div style="font-size:14px;font-weight:700;color:#1A2B5C;margin-bottom:12px;">Rentabilidad de la inversión</div>
        <div style="display:flex;gap:32px;margin-bottom:16px;">
            <div>
                <div style="color:#6B7280;font-size:12px;">Rentabilidad bruta</div>
                <div style="color:#1A2B5C;font-size:18px;font-weight:700;">{cap_rate_pct:.1f}% anual</div>
            </div>
            <div>
                <div style="color:#6B7280;font-size:12px;">Rentabilidad neta</div>
                <div style="color:#16A34A;font-size:18px;font-weight:700;">{cap_rate_neto_pct:.1f}% anual</div>
            </div>
        </div>
        <div style="border-top:1px solid #E5E7EB;padding-top:12px;">
            <div style="color:#6B7280;font-size:12px;font-weight:600;margin-bottom:8px;">Costos del propietario:</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 24px;font-size:13px;color:#374151;">
                <div>Expensas extraordinarias:</div><div style="text-align:right;">${expensas:,.0f} ARS/mes</div>
                <div>Mantenimiento estimado:</div><div style="text-align:right;">${mantenimiento:,.0f} ARS/mes</div>
                <div>Vacancia estimada (4%):</div><div style="text-align:right;">${vacancia:,.0f} ARS/mes</div>
            </div>
        </div>
    </div>
    """
    st.markdown(rentabilidad_html, unsafe_allow_html=True)


def render_razonamiento(prop, res):
    """Razonamiento narrativo en expander."""
    razonamiento = res.get('razonamiento', '')
    _old_textos = ['correcci', 'percentil P50', 'percentil seleccionado help', 'barreras geogr']
    _need_regen = ('incertidumbresignificativa' in razonamiento.replace(' ', '')) or any(t in razonamiento.lower() for t in _old_textos)
    if razonamiento and _need_regen:
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
            st.components.v1.html(mapa_html, height=500, scrolling=False)
    else:
        st.caption("Mapa no disponible")


def _get_comp_id(c, idx=0):
    """Genera un ID único y estable para un comparable basado en sus datos."""
    import hashlib
    # Usamos datos que no cambian entre renders para crear un hash estable
    # idx previene colisiones cuando dos entries tienen mismos precio/m2/direccion/lat/lon
    seed = f"{c.get('precio')}_{c.get('m2')}_{c.get('direccion_limpia') or c.get('direccion')}_{c.get('lat')}_{c.get('lon')}_{idx}"
    return hashlib.md5(seed.encode()).hexdigest()[:12]

def render_tabla_comparables(res, prop_name=None):
    """Tabla de propiedades comparables utilizadas con checkbox de selección.
    Muestra el recálculo P33/P50 según los comps seleccionados.
    """
    if not prop_name:
        prop_name = 'default'
    # Debug: dump selection state at entry
    _sel_key = f'comp_selection_{prop_name}'
    _sel_val = st.session_state.get(_sel_key, None)
    _sel_comp_keys = [k for k in st.session_state if k.startswith(f'sel_comp_{_safe_key(prop_name)}_')]
    _sel_comp_true = sum(1 for k in _sel_comp_keys if st.session_state[k])
    _comp_excl = st.session_state.get(f'comp_excluded_{prop_name}', None)
    _comp_excl_applied = st.session_state.get(f'_comp_exclusion_applied_{prop_name}', None)
    print(f"[DEBUG-SEL-ENTRY] {prop_name}: comp_selection_={'SET(' + str(len(_sel_val)) + ')' if _sel_val else 'None'}, sel_comp_keys={len(_sel_comp_keys)} (true={_sel_comp_true}), comp_excluded={_comp_excl}, _applied={_comp_excl_applied}")
    if res.get('retro_activo'):
        st.caption(f"🔙 Retro activo: ventana de {res.get('total_dias_ventana', 180)} días")
    comparables = res.get('comparables_venta', [])
    if not comparables:
        st.caption("Sin comparables disponibles")
        return

    comparables = sorted(comparables, key=lambda c: c.get('precio', 0))

    # 1. Determinar estado de selección actual para controlar visibilidad de botones
    sel_key = f'comp_selection_{prop_name}'
    comp_ids = [_get_comp_id(c, i) for i, c in enumerate(comparables)]
    stored_sel = st.session_state.get(sel_key, None)
    if stored_sel is None:
        excluded = res.get('_comp_excluded')
        if excluded:
            # Detectar si los IDs excluidos son del formato viejo (sin idx)
            # Si ningun ID excluido matchea con los comp_ids actuales, son IDs viejos
            old_format = not any(eid in comp_ids for eid in excluded)
            if old_format:
                print(f"[DEBUG-SEL-OLD-ID] {prop_name}: IDs excluidos no matchean formato actual (posible cambio de hash). Limpiando estado.")
                excluded = None
                res['_comp_excluded'] = None
                res['_comp_exclusion_applied'] = False
            stored_sel = set(cid for cid in comp_ids if cid not in excluded) if excluded else set(comp_ids)
        else:
            stored_sel = set(comp_ids)
        st.session_state[sel_key] = stored_sel
        print(f"[DEBUG-SEL-INIT] {prop_name}: stored_sel=None, reinicializado desde res._comp_excluded={excluded} → {len(stored_sel)} comps.")
    if not isinstance(stored_sel, set):
        stored_sel = set(stored_sel)

    # Obtener selección actual desde los checkboxes en session_state (en vivo)
    current_sel = set()
    for cid in comp_ids:
        chk_key = f'sel_comp_{_safe_key(prop_name)}_{cid}'
        if chk_key in st.session_state:
            if st.session_state[chk_key]:
                current_sel.add(cid)
        elif cid in stored_sel:
            current_sel.add(cid)

    # Banner de info + botón Restablecer (solo si hay comparables desmarcados en UI)
    if len(current_sel) < len(comparables):
        col_info, col_reset = st.columns([3, 1])
        with col_info:
            n_desel = len(comparables) - len(current_sel)
            st.info(f"⚡ {len(current_sel)}/{len(comparables)} comparables activos — {n_desel} desmarcado(s). Aplicar selección para recalcular.")
        with col_reset:
            if st.button("↩️ Restablecer todos", key=f'reset_comp_sel_{_safe_key(prop_name)}', use_container_width=True):
                    # Solo efecto visual: seleccionar todos los comparables
                    for cid in comp_ids:
                        st.session_state[f'sel_comp_{_safe_key(prop_name)}_{cid}'] = True
                    st.session_state[sel_key] = set(comp_ids)
                    st.session_state.pop(f'comp_excluded_{_safe_key(prop_name)}', None)
                    st.session_state.pop(f'_comp_exclusion_applied_{_safe_key(prop_name)}', None)
                    st.session_state.pop(f'_comp_interacted_{prop_name}', None)
                    # FORZAR RECALCULO: Para que el motor vuelva a calcular la mediana del pool completo
                    st.session_state[f'forzar_recalculo_{prop_name}'] = True
                    print(f"[DEBUG-RESET] {prop_name}: Selección restablecida, forzando recálculo para volver al valor natural.")
                    st.rerun()




    # Calcular mediana para highlight
    precios_m2 = [c.get('precio_m2', 0) * c.get('time_adjustment', 1.0) for c in comparables]
    precios_m2_sorted = sorted(precios_m2)
    n_p = len(precios_m2_sorted)
    if n_p % 2 == 1:
        vm2_mediana = precios_m2_sorted[n_p // 2]
    else:
        vm2_mediana = (precios_m2_sorted[n_p // 2 - 1] + precios_m2_sorted[n_p // 2]) / 2
    idx_mediana = min(range(n_p), key=lambda i: abs(precios_m2[i] - vm2_mediana))

    # Cabecera de la tabla
    hdr = st.columns([0.4, 0.5, 1.5, 0.8, 1.5, 0.6, 0.9, 2, 0.7, 0.6])
    hdr_labels = ['', '#', 'Precio USD', 'm²', 'Precio/m²', 'Dorm', 'Publicado', 'Dirección', 'Año', 'Dist']
    for col, label in zip(hdr, hdr_labels):
        col.markdown(f"**{label}**")

    selected_ids = set()
    for i, c in enumerate(comparables):
        comp_id = comp_ids[i]
        cols = st.columns([0.4, 0.5, 1.5, 0.8, 1.5, 0.6, 0.9, 2, 0.7, 0.6])

        _is_med = (i == idx_mediana)

        # Sincronizar checkbox con stored_sel antes de crear widget
        chk_key = f'sel_comp_{_safe_key(prop_name)}_{comp_id}'
        if chk_key not in st.session_state:
            st.session_state[chk_key] = comp_id in stored_sel
        checked = cols[0].checkbox("", key=chk_key)

        if checked:
            selected_ids.add(comp_id)
        else:
            if comp_id in stored_sel:
                stored_sel.remove(comp_id)

        _rc = "color:#c0392b;" if _is_med else ""
        cols[1].markdown(f"<span style='{_rc}'>{i+1}</span>", unsafe_allow_html=True)
        cols[2].markdown(f"<span style='{_rc}'>${c.get('precio', 0):,.0f}</span>", unsafe_allow_html=True)
        cols[3].markdown(f"<span style='{_rc}'>{c.get('m2', 0):.0f}</span>", unsafe_allow_html=True)
        # Precio/m2 con badges
        ta = c.get('time_adjustment', 1.0)
        vm2_orig = c.get('precio_m2', 0)
        vm2_ajust = c.get('precio_m2_ajustado', vm2_orig * ta)
        badges = ""
        if _is_med:
            badges += " <span style='background:#c0392b;color:white;font-size:9px;padding:1px 4px;border-radius:6px;font-weight:bold;'>MED</span>"
        if ta != 1.0:
            badges += " <span style='background:#ff6b35;color:white;font-size:9px;padding:1px 4px;border-radius:6px;font-weight:bold;'>RETRO</span>"
        if badges:
            _vm2_style = f"color:#c0392b;font-weight:bold" if _is_med else "font-weight:bold"
            cols[4].markdown(f"<span style='{_vm2_style}'>${vm2_ajust:,.0f}</span>{badges}", unsafe_allow_html=True)
        else:
            _vm2_style = f"color:#c0392b;font-weight:bold" if _is_med else "color:#2ecc71;font-weight:bold"
            cols[4].markdown(f"<span style='{_vm2_style}'>${vm2_orig:,.0f}</span>", unsafe_allow_html=True)
        cols[5].markdown(f"<span style='{_rc}'>{c.get('dormitorios', '?')}</span>", unsafe_allow_html=True)
        cols[6].markdown(f"<span style='{_rc}'>{str((c.get('date_created') or '')[:10]) if c.get('date_created') else ''}</span>", unsafe_allow_html=True)
        cols[7].markdown(f"<span style='{_rc}'>{((c.get('direccion_limpia') or c.get('direccion','')) or '')[:35]}</span>", unsafe_allow_html=True)
        _ant = c.get('antiquity')
        if _ant is not None and _ant >= 0:
            from datetime import datetime as _dt
            _year = _dt.now().year - _ant
        else:
            _year = None
        cols[8].markdown(f"<span style='{_rc}'>{str(_year) if _year else ''}</span>", unsafe_allow_html=True)
        cols[9].markdown(f"<span style='{_rc}'>{c.get('distancia_m', 0):.0f}m</span>" if c.get('distancia_m') else '', unsafe_allow_html=True)


    # Guardar selección actual
    st.session_state[sel_key] = selected_ids

    # Vista previa en vivo usando misma lógica que "Aplicar selección" (percentil por CV)
    if selected_ids:
        n_sel = len(selected_ids)
        n_total = len(comparables)
        selected_comps = [c for i, c in enumerate(comparables) if comp_ids[i] in selected_ids]
        if n_sel == n_total and n_sel >= 3:
            meta = res.get('resolution_metadata', {})
            _m2_puro = meta.get('_m2_puro')
            if _m2_puro and _m2_puro > 0:
                vm2_raw = _m2_puro
            else:
                raw_prices = sorted([c.get('precio_m2', 0) for c in comparables])
                n_rp = len(raw_prices)
                if n_rp % 2 == 1:
                    vm2_raw = raw_prices[n_rp // 2]
                else:
                    vm2_raw = (raw_prices[n_rp // 2 - 1] + raw_prices[n_rp // 2]) / 2
            preview = {'vm2': round(vm2_raw, 0), 'n_sel': n_sel, 'fallback': False,
                       'percentil_label': 'Motor', 'cv': meta.get('cv_pool', 0)}
        elif len(selected_comps) >= 3:
            preview = calcular_vm2_por_seleccion(selected_comps, res)
        else:
            preview = None

        all_ids = [_get_comp_id(c, i) for i, c in enumerate(comparables)]
        excluded_ids = [cid for cid in all_ids if cid not in selected_ids]
        _ss_comp_excluded = st.session_state.get(f'_comp_excluded_{prop_name}', [])
        _ss_comp_applied = st.session_state.get(f'_comp_exclusion_applied_{prop_name}', False)
        comp_excluded = res.get('_comp_excluded')
        if comp_excluded is None:
            comp_excluded = _ss_comp_excluded
        comp_applied = res.get('_comp_exclusion_applied')
        if comp_applied is None:
            comp_applied = _ss_comp_applied
        # RU-EXCL-SOURCE-01: verificar que comp_excluded no viene de session_state stale
        _res_excl = res.get('_comp_excluded')
        if _res_excl is not None and _res_excl != comp_excluded:
            print(f"[GUARDRAIL] RU-EXCL-SOURCE-01: {prop_name}: res._comp_excluded={_res_excl} "
                  f"!= comp_excluded={comp_excluded}. Stale session state leaking!")
        no_exclusions = len(excluded_ids) == 0 and len(comp_excluded) == 0
        is_applied = comp_applied and (no_exclusions or set(comp_excluded) == set(excluded_ids))
        print(f"[DEBUG-SEL-APPLIED] {prop_name}: is_applied={is_applied}, no_exclusions={no_exclusions}, excluded_ids={excluded_ids}, comp_excluded={comp_excluded}, comp_applied={comp_applied}, n_sel={len(selected_ids)}/{len(comp_ids)}, stored_sel_len={len(stored_sel)}")

        # GUARDRAIL: detectar divergencia entre preview vm2 y header m2
        if preview and is_applied:
            header_m2 = res.get("m2_microzona", res.get("m2_base_venta", 0))
            preview_m2 = preview["vm2"]
            diff_pct = abs(preview_m2 - header_m2) / max(header_m2, 1) * 100
            if diff_pct > 0.5:
                print(f"[GUARDRAIL] RU-M2-CONSISTENCY-01: {prop_name}: "
                      f"preview_vm2={preview_m2:.2f} != header_m2={header_m2:.2f} "
                      f"(diff={diff_pct:.1f}%, n_sel={n_sel}/{n_total}, is_applied={is_applied})")

        _pv = f'{preview["vm2"]:.2f}' if preview else "N/A"
        _hm = res.get("m2_microzona", res.get("m2_base_venta", 0))
        print(f"[DEBUG-EXCL-PREVIEW] {prop_name}: preview_vm2={_pv}, "
              f"n_sel={n_sel}/{n_total}, is_applied={is_applied}, header_m2={_hm:.2f}")

        col_a, col_b, col_c = st.columns([1, 2, 1.2])
        with col_a:
            if preview:
                st.metric("Valor/m² por selección", f"${preview['vm2']:,.0f}")
            else:
                st.metric("Valor/m² por selección", "—")
        with col_b:
            if preview:
                if preview.get('fallback'):
                    st.caption(f"Valor original del pool • {preview['n_sel']} comps (mín. 3 req.)")
                else:
                    cv_str = f"{preview['cv']:.2f}" if preview.get('cv') is not None else "—"
                    st.caption(f"{preview['percentil_label']} de selección • CV={cv_str} • {preview['n_sel']} comps selec. de {len(comparables)} totales")
            else:
                st.caption(f"Mínimo 2 comps • {n_sel} selec. de {len(comparables)} totales")
        with col_c:
            # Botón para re-valuar usando solo los comparables seleccionados
            excluded = [cid for cid in all_ids if cid not in selected_ids]
            
            if n_sel < 3:
                st.button("Mínimo 3 comparables", disabled=True, use_container_width=True)
            elif is_applied:
                st.button("✅ Selección Aplicada", type="secondary", disabled=True, use_container_width=True)
            else:
                # Botón visible SIEMPRE (incluye selección completa 6/6)
                    if st.button(
                        f"✅ Aplicar selección ({n_sel}/{len(comparables)})",
                        key=f'apply_comp_sel_{_safe_key(prop_name)}',
                        type='primary',
                        use_container_width=True,
                    ):
                        from datetime import datetime
                        print(f"[DEBUG-APPLY] ===== INICIO Aplicar selección {prop_name} =====")
                        print(f"[DEBUG-APPLY] {prop_name}: n_sel={n_sel}, n_total={len(comparables)}, n_excluded={len(excluded)}")
                        print(f"[DEBUG-APPLY] {prop_name}: retro_active={st.session_state.get('retro_active_' + prop_name, False)}, flex_active={st.session_state.get('flex_active_' + prop_name, False)}")
                        
                        # Sync slider value before applying selection
                        slider_val = st.session_state.get(f'retro_meses_slider_{prop_name}', 36)
                        st.session_state[f'retro_meses_{prop_name}'] = slider_val
                        print(f"[DEBUG-APPLY] {prop_name}: slider_val={slider_val}")
                        
                        st.session_state[f'comp_excluded_{prop_name}'] = excluded
                        st.session_state[f'_comp_exclusion_applied_{prop_name}'] = True
                        st.session_state[f'_comp_excluded_{prop_name}'] = excluded
                        st.session_state[f'forzar_recalculo_{prop_name}'] = True
                        print(f"[DEBUG-APPLY] {prop_name}: Set forzar_recalculo=True, _comp_exclusion_applied=True, excluded={excluded}")
                        print(f"[DEBUG-APPLY] {prop_name} ===== FIN Aplicar selección =====, calling st.rerun()")
                        st.rerun()


    elif not selected_ids:
        st.warning("⚠️ Seleccioná al menos un comparable para calcular el valor.")
        if st.button("Seleccionar todos", key=f'sel_all_{_safe_key(prop_name)}'):
            st.session_state[sel_key] = set([_get_comp_id(c, i) for i, c in enumerate(comparables)])
            # Limpiar exclusión previa
            st.session_state.pop(f'comp_excluded_{prop_name}', None)
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
                idx1 = st.selectbox("Primera valuacion", range(len(historial)), format_func=lambda i: labels[i], key=f"comp1_{_safe_key(nombre)}")
            with col2:
                idx2 = st.selectbox("Segunda valuacion", range(len(historial)), index=min(1, len(historial)-1), format_func=lambda i: labels[i], key=f"comp2_{_safe_key(nombre)}")
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
from jinja2 import Template

def generar_reporte_pdf(prop: dict, res: dict, auto_result: dict = None) -> bytes:
    """Genera reporte PDF profesional con WeasyPrint + template HTML."""
    from datetime import datetime
    from parsers.valuacion_cache import CACHE_VERSION

    # ── Preparar datos (con safety checks) ──
    def _safe_int(v, default=0):
        try:
            return int(v) if v is not None else default
        except (ValueError, TypeError):
            return default

    def _safe_float(v, default=0.0):
        try:
            return float(v) if v is not None else default
        except (ValueError, TypeError):
            return default

    manual_params = res.get('manual_params', {}) or {}
    if not manual_params and auto_result:
        manual_params = auto_result.get('_manual_params', {}) or {}
    tiene_manual = bool(manual_params)
    tiene_auto = bool(auto_result and auto_result.get('valor_propiedad_usd', 0) > 0)

    # Valores auto
    v_auto = _safe_int((auto_result or {}).get('valor_propiedad_usd'))
    v_auto_cons = _safe_int((auto_result or {}).get('valor_venta_conservador'))
    v_auto_opt = _safe_int((auto_result or {}).get('valor_venta_optimista'))
    v_auto_m2 = _safe_int((auto_result or {}).get('m2_base_venta'))
    n_comps_auto = _safe_int((auto_result or res or {}).get('resolution_metadata', {}).get('n_propiedades', 0))

    # Valores manual
    v_manual = _safe_int(res.get('valor_propiedad_usd'))
    v_manual_cons = _safe_int(res.get('valor_venta_conservador'))
    v_manual_opt = _safe_int(res.get('valor_venta_optimista'))
    v_manual_spread = f"{v_manual_opt - v_manual_cons:,}" if v_manual and v_manual_opt and v_manual_cons else "",
    delta_manual = f"{((v_manual - v_auto) / v_auto * 100):+.1f}" if v_auto > 0 else "N/A"

    # Valor adoptado
    fuente_activa = res.get('_fuente_activa', 'auto')
    if tiene_manual and tiene_auto:
        valor_adoptado = v_manual if fuente_activa == 'manual' else v_auto
        fuente_adoptada = "Manual (Tasador)" if fuente_activa == 'manual' else "Por Comparables"
    else:
        valor_adoptado = v_manual or v_auto
        fuente_adoptada = "Por Comparables" if tiene_auto else "Manual"

    # Metricas — usar lógica unificada de alquiler
    recalc = _recalcular_alquiler(prop, res, auto_result=auto_result)
    alq_ars = recalc['alq_ars']
    alq_usd = int(alq_ars / recalc['dolar']) if recalc['dolar'] > 0 else 0
    cap_rate = recalc['cap_rate']
    dolar = recalc['dolar']
    m2_base = _safe_int(res.get('m2_base_venta'))
    m2_eq = res.get('m2_equivalentes') or prop.get('m2', 0)
    m2_eq = _safe_float(m2_eq, 0.0)

    # Comparables — top 76 por relevancia para PDF
    comps = res.get('comparables_venta', [])
    comps_sorted = sorted(comps, key=lambda c: abs(c.get('precio_m2', 0) * c.get('time_adjustment', 1.0) - m2_base))[:76]
    comparables_list = []
    comp_coords = []  # lat, lon for map
    for c in comps_sorted:
        comparables_list.append({
            'direccion': (c.get('direccion', '') or '')[:40],
            'm2': c.get('m2', ''),
            'dormitorios': c.get('dormitorios', ''),
            'precio_m2': f"${c.get('precio_m2', 0):,.0f}",
            'precio': f"${c.get('precio', 0):,.0f}",
            'distancia_m': f"{c.get('distancia_m', 0):.0f}",
            'antiguedad': c.get('antiguedad', c.get('antiquity', '')),
        })
        clat = c.get('lat') or c.get('latitud')
        clon = c.get('lon') or c.get('longitud')
        if clat and clon:
            try:
                comp_coords.append((float(clat), float(clon), (c.get('direccion') or '')[:30]))
            except (ValueError, TypeError):
                pass

    # Coordenadas de la propiedad
    prop_lat = prop.get('lat') or prop.get('latitud')
    prop_lon = prop.get('lon') or prop.get('longitud')
    try:
        prop_lat = float(prop_lat) if prop_lat else None
        prop_lon = float(prop_lon) if prop_lon else None
    except (ValueError, TypeError):
        prop_lat = prop_lon = None

    # Logo como base64
    logo_b64 = ""
    try:
        import base64 as _b64mod
        logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "logovalu1.jpeg.png")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as _f:
                logo_b64 = _b64mod.b64encode(_f.read()).decode()
    except Exception:
        pass

    # Mapa de comparables como imagen (folium + Playwright screenshot)
    map_b64 = ""
    if prop_lat and prop_lon and comp_coords:
        try:
            import folium
            from folium.plugins import MarkerCluster
            _m = folium.Map(location=[prop_lat, prop_lon], zoom_start=15, tiles='cartodbpositron', width='100%', height='600px')
            folium.Marker(
                [prop_lat, prop_lon],
                popup=f"<b>{prop.get('nombre', 'Propiedad')}</b>",
                icon=folium.Icon(color='red', icon='home'),
            ).add_to(_m)
            folium.Circle(
                [prop_lat, prop_lon],
                radius=1000,
                color='#3388ff',
                fill=True,
                fill_opacity=0.05,
                weight=1,
            ).add_to(_m)
            for clat, clon, cdireccion in comp_coords:
                folium.CircleMarker(
                    [clat, clon],
                    radius=5,
                    color='#10b981',
                    fill=True,
                    fill_color='#10b981',
                    fill_opacity=0.7,
                    popup=cdireccion,
                ).add_to(_m)
            import tempfile as _tf
            with _tf.NamedTemporaryFile(suffix='.html', delete=False) as _f:
                _m.save(_f.name)
                _map_html_path = _f.name
            with _tf.NamedTemporaryFile(suffix='.png', delete=False) as _f:
                _map_png_path = _f.name
            _map_html_fwd = _map_html_path.replace(os.sep, '/')
            _map_png_fwd = _map_png_path.replace(os.sep, '/')
            _map_script = (
                "from playwright.sync_api import sync_playwright\n"
                "import time\n"
                "p = sync_playwright().start()\n"
                "b = p.chromium.launch(headless=True)\n"
                "pg = b.new_page()\n"
                "pg.set_viewport_size({'width': 1200, 'height': 700})\n"
                f"pg.goto('file:///{_map_html_fwd}', wait_until='networkidle')\n"
                "time.sleep(3)\n"
                f"pg.screenshot(path=r'{_map_png_fwd}', full_page=True)\n"
                "b.close()\n"
                "p.stop()\n"
            )
            import subprocess as _sp
            _sp.run([sys.executable, '-c', _map_script], capture_output=True, timeout=15)
            if os.path.exists(_map_png_path) and os.path.getsize(_map_png_path) > 100:
                with open(_map_png_path, 'rb') as _f:
                    map_b64 = _b64mod.b64encode(_f.read()).decode()
            for _p in [_map_html_path, _map_png_path]:
                try: os.unlink(_p)
                except: pass
        except Exception:
            pass

    # Metadata
    meta = res.get('resolution_metadata', {}) or {}
    # Use auto_result for auto razonamiento (res may be manual_result when fuente_activa=='manual')
    auto_source = auto_result or res
    razonamiento = auto_source.get('razonamiento', '')

    # Always regenerate razonamiento with fresh data (alquiler, etc.) for consistency
    if razonamiento:
        try:
            from parsers.mercado_inmobiliario import generar_razonamiento_valuacion
            _auto_meta = auto_source.get('resolution_metadata', {}) or {}
            # Inject fresh alquiler into auto_source so razonamiento uses consistent values
            auto_source['alquiler_estimado_ars'] = alq_ars
            auto_source['cap_rate'] = cap_rate
            auto_source['usdt_ars'] = dolar
            razonamiento = generar_razonamiento_valuacion(prop, auto_source, _auto_meta)
        except Exception:
            pass

    # Subfactores hedonicos reales (necesario antes del razonamiento manual)
    _fd = None
    try:
        from parsers.mercado_inmobiliario import calcular_factores_display
        _fd = calcular_factores_display(prop)
    except Exception:
        pass

    # Razonamiento manual detallado
    razonamiento_manual = ''
    if tiene_manual and manual_params:
        _mp = manual_params
        _usd_m2 = _mp.get('usd_m2', 0)
        _fh = _mp.get('factor_hedonico', 1.0)
        _incert = _mp.get('incertidumbre_pct', 10.0)
        _ajuste = _mp.get('ajuste_pct', 0.0)
        _incluir_const = _mp.get('incluir_prima_const', True)

        _lineas_m = []

        # Párrafo 1: Metodología (real — punto de referencia geográfico)
        _lineas_m.append(
            f"La valuación manual de {prop.get('nombre', 'la propiedad')} se realizó "
            f"utilizando un punto de referencia geográfico como base de precio, "
            f"considerando un radio de 400 metros alrededor de la propiedad."
        )

        # Párrafo 2: Precio base (real — ancla de zona)
        _detalles_formula = []
        _detalles_formula.append(f"{m2_eq} m2 equivalentes x USD {_usd_m2:,.0f}/m2")
        _valor_base = m2_eq * _usd_m2

        _lineas_m.append(
            f"El precio base de referencia es USD {_usd_m2:,.0f}/m2, determinado a partir "
            f"del punto geográfico más cercano a la ubicación de la propiedad. "
            f"Este valor representa el precio de referencia de la zona considerando "
            f"propiedades similares en tamaño y ubicación."
        )

        # Párrafo 3: Factor hedonico desglosado
        if _fd:
            _estado_pct = (_fd.get('factor_estado', 1.0) - 1.0) * 100
            _calidad_pct = (_fd.get('factor_calidad', 1.0) - 1.0) * 100
            _amenities_pct = _fd.get('delta_amenities', 0) * 100
            _otros_pct = _fd.get('delta_otros', 0) * 100
            _total_fh = _fd.get('total', 1.0)

            _lineas_m.append(
                f"Se aplico un factor hedonico combinado de {_total_fh:.4f}, desglosado "
                f"en subfactores de referencia:"
            )

            _subfactores = []
            if _estado_pct != 0:
                _subfactores.append(f"Estado ({_fd.get('estado_label', '')}): {_estado_pct:+.1f}%")
            else:
                _subfactores.append(f"Estado ({_fd.get('estado_label', '')}): +0.0% (estandar)")
            if _calidad_pct != 0:
                _subfactores.append(f"Calidad ({_fd.get('calidad_label', '')}): {_calidad_pct:+.1f}%")
            else:
                _subfactores.append(f"Calidad ({_fd.get('calidad_label', '')}): +0.0% (estandar)")
            if _amenities_pct != 0:
                _det_am = _fd.get('detalle_amenities', '')
                _subfactores.append(f"Amenities ({_det_am}): {_amenities_pct:+.1f}%")
            else:
                _subfactores.append(f"Amenities: +0.0% (sin amenities diferenciadoras)")
            _subfactores.append(f"Otros: {_otros_pct:+.1f}%")

            for sf in _subfactores:
                _lineas_m.append(f"  - {sf}")

            _detalles_formula.append(f"factor hedonico {_total_fh:.4f}")

        # Párrafo 4: Constructora
        if _incluir_const and prop.get('constructora', ''):
            try:
                import json as _json
                _constr_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "constructoras_rosario.json")
                if os.path.exists(_constr_path):
                    with open(_constr_path, 'r', encoding='utf-8') as _f:
                        _constr_list = _json.load(_f)
                        _constr_name = prop.get('constructora', '').lower().strip()
                        for _entry in _constr_list:
                            if _constr_name == _entry.get('descripcion', '').lower().strip():
                                _pct = _entry.get('porcentaje', 0)
                                _factor_const = 1.0 + _pct / 100.0
                                _detalles_formula.append(f"prima constructora {_factor_const:.4f} (+{_pct}%)")
                                _lineas_m.append(
                                    f"Se incluyo la prima de constructora ({prop.get('constructora')}) "
                                    f"con un factor de {_factor_const:.4f} (+{_pct}%), reconociendo "
                                    f"la valoracion de marca y calidad constructiva en el mercado."
                                )
                                break
            except Exception:
                pass

        # Párrafo 5: Ajuste manual
        if _ajuste != 0:
            _detalles_formula.append(f"ajuste manual {_ajuste:+.1f}%")
            _lineas_m.append(
                f"Se aplico un ajuste manual del {_ajuste:+.1f}% por consideraciones "
                f"especificas del analista no capturadas por los factores anteriores."
            )

        # Párrafo 6: Formula final
        _valor_calc = m2_eq * _usd_m2 * _fh
        _lineas_m.append(
            f"La formula de calculo fue: {' x '.join(_detalles_formula)}, "
            f"llegando a un valor estimado de USD {_valor_calc:,.0f}."
        )

        # Párrafo 7: Rango de incertidumbre
        _lineas_m.append(
            f"Se establecio un rango de incertidumbre de +/-{_incert:.0f}% "
            f"(conservador: USD {int(v_manual_cons):,}, optimista: USD {int(v_manual_opt):,}), "
            f"reflejando la variabilidad propia de una estimacion basada en juicio profesional."
        )

        # Párrafo 8: Comparacion con automatica
        if tiene_auto and v_auto > 0:
            _delta = ((v_manual - v_auto) / v_auto) * 100
            if abs(_delta) < 3:
                _lineas_m.append(
                    f"El resultado manual (USD {v_manual:,}) es consistente con la "
                    f"valuacion automatica (USD {v_auto:,}), con una diferencia del "
                    f"{_delta:+.1f}%, lo que indica convergencia entre ambos metodos."
                )
            elif _delta > 0:
                _lineas_m.append(
                    f"El resultado manual (USD {v_manual:,}) supera a la valuacion "
                    f"automatica (USD {v_auto:,}) en un {_delta:+.1f}%, lo que sugiere "
                    f"que el analista identifico atributos de valor no capturados por "
                    f"el algoritmo de mercado."
                )
            else:
                _lineas_m.append(
                    f"El resultado manual (USD {v_manual:,}) es inferior a la valuacion "
                    f"automatica (USD {v_auto:,}) en un {_delta:+.1f}%, lo que sugiere "
                    f"que el analista considera factores de riesgo o desgaste no reflejados "
                    f"en el comparativo de mercado."
                )

        razonamiento_manual = "\n\n".join(_lineas_m)

    # Activos
    val_activos = res.get('valor_activos', {}) or {}
    activos_list = []
    if val_activos.get('cocheras', 0) > 0:
        activos_list.append({'nombre': 'Cocheras', 'valor': f"{int(val_activos['cocheras']):,}"})
    if val_activos.get('baulera', 0) > 0:
        activos_list.append({'nombre': 'Baulera', 'valor': f"{int(val_activos['baulera']):,}"})
    total_activos = int(val_activos.get('total', 0))

    # Catastro
    catastro_data = None
    catastro = res.get('catastro_detalle')
    if catastro:
        candidatos = catastro.get('candidatos', [])
        if candidatos:
            sel = next((c for c in candidatos if c.get('recomendado')), candidatos[0])
            catastro_data = {
                'ph': sel.get('ph', 'N/A'),
                'anio': int(float(sel['year'])) if sel.get('year') else 'N/A',
                'seccion': int(float(sel['seccion'])) if sel.get('seccion') else '-',
                'grafico': int(float(sel['grafico'])) if sel.get('grafico') else '-',
            }

    # Fechas
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache_scraping.json")
    fecha_scraping = ""
    if os.path.exists(cache_path):
        fecha_scraping = datetime.fromtimestamp(os.path.getmtime(cache_path)).strftime("%Y-%m-%d")

    # CV cualitativo
    cv_qualitative = ''
    cv_pool_val = meta.get('cv_pool')
    if cv_pool_val is not None:
        if cv_pool_val < 0.10:
            cv_qualitative = 'Pool altamente homogeneo'
        elif cv_pool_val < 0.15:
            cv_qualitative = 'Homogeneidad buena'
        elif cv_pool_val < 0.20:
            cv_qualitative = 'Heterogeneidad moderada'
        else:
            cv_qualitative = 'Pool heterogeneo'

    # ── Renderizar template ──
    template_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", "reporte_valuacion.html")
    with open(template_path, 'r', encoding='utf-8') as f:
        template = Template(f.read())

    html_content = template.render(
        nombre=prop.get('nombre', ''),
        direccion=prop.get('direccion', 'Rosario, Argentina'),
        zona=prop.get('zona', ''),
        fecha_generacion=datetime.now().strftime('%d/%m/%Y %H:%M'),
        cache_version=CACHE_VERSION,
        fecha_scraping=fecha_scraping,
        tiene_auto=tiene_auto,
        tiene_manual=tiene_manual,
        v_auto=f"{v_auto:,}",
        v_auto_cons=f"{v_auto_cons:,}",
        v_auto_opt=f"{v_auto_opt:,}",
        v_auto_spread=f"{v_auto_opt - v_auto_cons:,}" if v_auto and v_auto_opt and v_auto_cons else "",
        v_auto_m2=f"{v_auto_m2:,}",
        n_comps_auto=_safe_int(n_comps_auto),
        v_manual=f"{v_manual:,}",
        v_manual_cons=f"{v_manual_cons:,}",
        v_manual_opt=f"{v_manual_opt:,}",
        v_manual_spread=f"{v_manual_opt - v_manual_cons:,}" if v_manual and v_manual_opt and v_manual_cons else "",
        delta_manual=delta_manual,
        valor_adoptado=f"{valor_adoptado:,}",
        fuente_adoptada=fuente_adoptada,
        valor_unico=f"{(v_manual or v_auto):,}",
        v_cons_unico=f"{(v_manual_cons or v_auto_cons):,}",
        v_opt_unico=f"{(v_manual_opt or v_auto_opt):,}",
        v_manual_m2=f"{int(v_manual / m2_eq):,}" if v_manual and m2_eq else "",
        m2_eq=f"{m2_eq:.1f}" if isinstance(m2_eq, (int, float)) and m2_eq else "N/D",
        m2_total=prop.get('m2', 0) or 0,
        m2_cub=prop.get('m2_cubiertos', 0) or 0,
        m2_desc=prop.get('m2_descubiertos', 0) or 0,
        dormitorios=prop.get('dormitorios', ''),
        banos=prop.get('banos', prop.get('baños', '')),
        antiguedad=prop.get('antiguedad', prop.get('antiquity', '')),
        anio_const=prop.get('anio_construccion', '?'),
        estado=prop.get('estado_detalle', 'bueno'),
        tipo_inmueble=prop.get('tipo_inmueble', ''),
        constructora=prop.get('constructora', ''),
        calidad_edificio=prop.get('calidad_edificio', 'estándar'),
        piso=prop.get('piso', ''),
        total_pisos=prop.get('total_pisos', ''),
        expensas=prop.get('expensas_ars', ''),
        ambientes=prop.get('ambientes', ''),
        orientacion=prop.get('orientacion', ''),
        ventilacion=prop.get('ventilacion', ''),
        vista=prop.get('vista', ''),
        m2_semi=prop.get('m2_semicubiertos', 0) or 0,
        toilet=prop.get('toilet', False),
        cocheras=prop.get('cocheras_cantidad', 0),
        baulera=prop.get('baulera', False),
        ascensores=prop.get('ascensores_edificio', ''),
        seguridad=prop.get('seguridad', ''),
        terminaciones=prop.get('terminaciones', ''),
        descripcion_libre=prop.get('descripcion_libre', ''),
        amenities_list=', '.join(prop.get('detalles_categoria', [])[:5]) if prop.get('detalles_categoria') else '',
        balcon=prop.get('balcon', False),
        tipo_balcon=prop.get('tipo_balcon', ''),
        m2_semi_detalle=prop.get('m2_semicubiertos_detalle', ''),
        disposicion=prop.get('disposicion', ''),
        ubicacion_tipo=prop.get('ubicacion_tipo', ''),
        reciclado=prop.get('reciclado', False),
        reciclado_tipo=prop.get('reciclado_tipo', ''),
        anio_reciclado=prop.get('anio_reciclado', ''),
        gas_ok=prop.get('gas_ok', ''),
        doble_ingreso=prop.get('doble_ingreso', False),
        despensa=prop.get('despensa', False),
        lavadero_independiente=prop.get('lavadero_independiente', False),
        placares_completos=prop.get('placares_completos', False),
        layout_flexible=prop.get('layout_flexible', False),
        cocheras_tipo=prop.get('cocheras_tipo', ''),
        valor_cochera_base=prop.get('valor_cochera_base', ''),
        carpinteria=prop.get('carpinteria', ''),
        terminaciones_suelo=prop.get('terminaciones_suelo', ''),
        terminaciones_cocina=prop.get('terminaciones_cocina', ''),
        ventilacion_bano=prop.get('ventilacion_bano', ''),
        alquiler_ars=f"{alq_ars:,}",
        alquiler_usd=f"{alq_usd:,}",
        cap_rate=f"{cap_rate*100:.1f}%",
        m2_base=f"${m2_base:,}" if m2_base else "N/D",
        comparables=comparables_list,
        razonamiento=razonamiento,
        razonamiento_manual=razonamiento_manual,
        factor_total=f"{(res.get('factor_total', 1.0)-1)*100:+.1f}%",
        depreciacion=f"{(res.get('delta_anti', 1.0)-1)*100:+.1f}%",
        nlp_ajuste=f"{res.get('nlp_ajuste', 0)*100:+.1f}%",
        cv_pool=f"{meta.get('cv_pool', 0):.3f}",
        percentil=meta.get('percentil_usado', 'P50'),
        tiene_activos=total_activos > 0,
        activos=activos_list,
        total_activos=f"{total_activos:,}",
        catastro=catastro_data,
        logo_b64=logo_b64,
        map_b64=map_b64,
        fd_estado=f"{(_fd.get('factor_estado', 1.0) - 1.0) * 100:+.1f}%" if _fd else "+0.0%",
        fd_calidad=f"{(_fd.get('factor_calidad', 1.0) - 1.0) * 100:+.1f}%" if _fd else "+0.0%",
        fd_amenities=f"{_fd.get('delta_amenities', 0) * 100:+.1f}%" if _fd else "+0.0%",
        fd_otros=f"{_fd.get('delta_otros', 0) * 100:+.1f}%" if _fd else "+0.0%",
        fd_total=f"{_fd.get('total', 1.0):.4f}" if _fd else "1.0000",
        fd_estado_label=_fd.get('estado_label', '') if _fd else '',
        fd_calidad_label=_fd.get('calidad_label', '') if _fd else '',
        fd_amenities_detalle=_fd.get('detalle_amenities', '') if _fd else '',
        radio_m=meta.get('radio_usado', 1000),
        cv_qualitative=cv_qualitative,
    )

    return html_content


def generar_reporte_html(prop: dict, res: dict, auto_result: dict = None) -> str:
    """Genera HTML del reporte (para preview en iframe)."""
    return generar_reporte_pdf(prop, res, auto_result)


def generar_reporte_pdf_bytes(prop: dict, res: dict, auto_result: dict = None) -> bytes:
    """Genera PDF a partir del HTML (Playwright subprocess)."""
    html_content = generar_reporte_pdf(prop, res, auto_result)

    # ── Generar PDF con Playwright (subprocess para evitar event loop de Streamlit) ──
    import subprocess, tempfile
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8') as f:
        f.write(html_content)
        html_path = f.name
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        pdf_path = f.name
    try:
        _html_fwd = html_path.replace(os.sep, '/')
        script = (
            f"from playwright.sync_api import sync_playwright; "
            f"p=sync_playwright().start(); b=p.chromium.launch(headless=True); "
            f"pg=b.new_page(); pg.goto('file:///{_html_fwd}', wait_until='networkidle'); "
            f"pg.pdf(path=r'{pdf_path}',format='A4',print_background=True); "
            f"b.close(); p.stop()"
        )
        result = subprocess.run(
            [sys.executable, '-c', script],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Playwright subprocess error: {result.stderr[:500]}")
        with open(pdf_path, 'rb') as f:
            pdf_bytes = f.read()
    finally:
        try: os.unlink(html_path)
        except: pass
        try: os.unlink(pdf_path)
        except: pass
    return pdf_bytes


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
    Formulario de Valuacion Manual — tres bloques:
      1. Configuracion (ancla, USD/m2, FH, incertidumbre, activos)
      2. Preview Calculator (custom HTML)
      3. Accion (motivo, guardar, eliminar)
    """
    from datetime import datetime
    from parsers.location_engine import cargar_anclas, get_ancla_mas_cercana
    from parsers.mercado_inmobiliario import (
        calcular_m2_equivalentes, calcular_factores, calcular_factores_display,
        calcular_size_adjustment,
    )
    from parsers.zonas_manager import resolver_macrozona
    
    nombre = prop.get('nombre', '')
    auto_result = res.get('_auto_result', res)
    saved_params = res.get('_manual_params') or {}
    motor_valor = auto_result.get('valor_propiedad_usd', 0)
    
    # Debugging initial values
    cant_cocheras_raw = prop.get('cocheras_cantidad', 0)
    try:
        cant_cocheras = int(cant_cocheras_raw)
    except (ValueError, TypeError):
        cant_cocheras = 0
    tipo_cochera = prop.get('cocheras_tipo', 'cubierta')
    valor_baulera = prop.get('valor_baulera', 0)
    print(f"[DEBUG-MANUAL-VAL] {nombre}: cant_cocheras={cant_cocheras} (raw={cant_cocheras_raw}), baulera={valor_baulera}")
    
    # Feedback post-guardado/eliminacion (persiste un ciclo de render)
    feedback = st.session_state.pop(f'manual_feedback_{nombre}', None)
    if feedback == 'guardado':
        st.success("Valuacion manual guardada correctamente.")
    elif feedback == 'eliminado':
        st.success("Valuacion manual eliminada correctamente.")


    # ─── Carga de anclas ───
    anclas = cargar_anclas()
    ancla_options = {a.get('id', a.get('nombre', '')): a for a in anclas}
    ancla_display_map = {}
    for a in anclas:
        aid = a.get('id', a.get('nombre', ''))
        v = a.get('usd_m2', 0)
        nombre_legible = a.get('nombre_legible', aid.replace('_', ' ').title())
        macrozona = a.get('macrozona', '')
        display_label = f"{nombre_legible} (${v:,}/m2) [{macrozona.upper()}]" if macrozona else f"{nombre_legible} (${v:,}/m2)"
        ancla_display_map[display_label] = {'id': aid, 'usd_m2': v}
    ancla_display_list = sorted(ancla_display_map.keys())

    # ─── Precio oficial ───
    zona_prop = (prop.get('zona') or '').lower().strip()
    dorm_prop = prop.get('dormitorios')
    precio_oficial = obtener_precio_oficial(zona_prop, dorm_prop)
    oficial_display = None
    if precio_oficial and precio_oficial.get('usd_m2', 0) > 0:
        oficial_display = precio_oficial

    lat = prop.get('lat')
    lon = prop.get('lon')
    ancla_cercana = get_ancla_mas_cercana(lat, lon, anclas) if lat and lon else None
    if ancla_cercana:
        default_ancla_id = ancla_cercana.get('id', '')
        default_usd_m2 = ancla_cercana.get('usd_m2', 0)
    else:
        zona_prop = (prop.get('zona') or '').lower().strip()
        zona_key = zona_prop.replace(' ', '_').replace('-', '_')
        ancla_por_zona = next((a for a in anclas if a.get('id', '').lower().startswith(zona_key)), None)
        if not ancla_por_zona:
            ancla_por_zona = next((a for a in anclas if zona_key in a.get('id', '').lower()), None)
        default_ancla_id = ancla_por_zona.get('id', '') if ancla_por_zona else ''
        default_usd_m2 = ancla_por_zona.get('usd_m2', 0) if ancla_por_zona else 0

    # Factor hedonico default
    default_factor_hedonico = 1.0
    try:
        f_dict = calcular_factores(prop)
        default_factor_hedonico = round(f_dict['total'], 4)
    except Exception:
        pass

    # Constructora
    constr_label = ""
    factor_const = 1.0
    pct_const = 0
    try:
        constr_path = "C:/Users/Gustavo/ingresos_familiares_st/constructoras_rosario.json"
        if os.path.exists(constr_path):
            with open(constr_path, "r", encoding="utf-8") as f:
                constr_list = json.load(f)
            constr_prop = prop.get('constructora', '').lower().strip()
            if constr_prop and isinstance(constr_list, list):
                for entry in constr_list:
                    if constr_prop == entry.get('descripcion', '').lower().strip():
                        pct_const = entry.get('porcentaje', 0)
                        factor_const = 1.0 + pct_const / 100.0
                        constr_label = f"{entry['descripcion']} ({pct_const:+.0f}%)"
                        break
    except Exception:
        pass
    if not constr_label and prop.get('constructora'):
        constr_label = prop.get('constructora', '')

    # Macrozona
    _mz_info = resolver_macrozona(prop)
    _mz_name = _mz_info.get('macrozona', '')

    # Activos
    cant_cocheras = prop.get('cocheras_cantidad', 0)
    tipo_cochera = prop.get('cocheras_tipo', 'cubierta')
    valor_baulera = prop.get('valor_baulera', 0)

    # ─── Session state ───
    ss_key = f"manual_params_{nombre}"
    if ss_key not in st.session_state:
        if saved_params:
            st.session_state[ss_key] = dict(saved_params)
        else:
            st.session_state[ss_key] = {
                'ancla_id': default_ancla_id,
                'usd_m2': default_usd_m2,
                'factor_hedonico': default_factor_hedonico,
                'ajuste_pct': 0.0,
                'incertidumbre_pct': 10.0,
                'incluir_prima_const': True,
            }

    saved = st.session_state[ss_key]

    if saved_params:
        fecha_guardado = saved_params.get('fecha_guardado', '')
        fecha_str = ""
        if fecha_guardado:
            try:
                dt = datetime.fromisoformat(fecha_guardado)
                fecha_str = dt.strftime("%d/%m/%Y %H:%M")
            except Exception:
                pass
        st.info(f"Valuacion manual guardada ({fecha_str}). Los campos estan pre-poblados. Edita y volve a guardar para actualizar.")

    # ========================================================================
    # BLOQUE 1: CONFIGURACION
    # ========================================================================
    with st.container(border=True):
        st.markdown("##### Parametros de Valuacion Manual")

        # Selector de fuente del valor m2
        fuentes_options = ["Ancla del cluster"]
        if oficial_display:
            fuentes_options.append("Valor oficial")

        saved_fuente = saved.get('fuente_m2', 'Ancla del cluster')
        if saved_fuente not in fuentes_options:
            saved_fuente = fuentes_options[0]

        fuente_sel = st.radio(
            "Fuente del valor m2",
            options=fuentes_options,
            index=fuentes_options.index(saved_fuente) if saved_fuente in fuentes_options else 0,
            horizontal=True,
            key=f"manual_fuente_m2_{_safe_key(nombre)}",
        )

        # Fila: Ancla (si aplica) | USD/m² | FH (%) | Inc. (±%) | Ajuste (%)
        print(f"[DEBUG-VISUAL-101] {nombre}: fuente={fuente_sel}, ancla_id={saved.get('ancla_id')}, fh_delta={(float(saved.get('factor_hedonico', 1.0))-1.0)*100:+.1f}%, inc={saved.get('incertidumbre_pct')}, ajuste={saved.get('ajuste_pct')}")

        if fuente_sel == "Ancla del cluster":
            col_a, col_b, col_c, col_d, col_e = st.columns([2, 1, 1, 1, 1])
            with col_a:
                saved_display = ancla_display_list[0] if ancla_display_list else ''
                for dk in ancla_display_list:
                    if ancla_display_map.get(dk, {}).get('id') == saved.get('ancla_id', ''):
                        saved_display = dk
                        break
                if not saved_display and saved.get('ancla_id') and ancla_display_list:
                    saved_display = ancla_display_list[0]
                ancla_display_sel = st.selectbox(
                    "Ancla",
                    options=ancla_display_list,
                    index=ancla_display_list.index(saved_display) if saved_display in ancla_display_list else 0,
                    key=f"manual_ancla_{_safe_key(nombre)}",
                )
                ancla_sel = ''
                if ancla_display_sel in ancla_display_map:
                    ancla_sel = ancla_display_map[ancla_display_sel]['id']
            with col_b:
                tiene_ancla = bool(ancla_sel)
                usd_display = saved.get('usd_m2', default_usd_m2)
                if tiene_ancla and ancla_sel in ancla_options:
                    usd_display = ancla_options[ancla_sel].get('usd_m2', usd_display)
                usd_m2_input = st.number_input(
                    "USD/m²",
                    min_value=0.0, max_value=10000.0,
                    value=float(usd_display or 0),
                    step=50.0, format="%.0f",
                    disabled=tiene_ancla,
                    key=f"manual_usd_m2_{_safe_key(nombre)}",
                )
            with col_c:
                fh_delta_saved = (float(saved.get('factor_hedonico', default_factor_hedonico)) - 1.0) * 100
                fh_delta = st.number_input(
                    "FH (Δ%)",
                    min_value=-100.0, max_value=400.0,
                    value=fh_delta_saved,
                    step=1.0, format="%.1f",
                    key=f"manual_fh_{_safe_key(nombre)}",
                )
                fh = 1.0 + (fh_delta / 100.0)
            with col_d:
                inc = st.number_input(
                    "Inc. (±%)",
                    min_value=0.0, max_value=100.0,
                    value=float(saved.get('incertidumbre_pct', 10.0)),
                    step=1.0, format="%.0f",
                    key=f"manual_inc_{_safe_key(nombre)}",
                )
            with col_e:
                ajuste_pct = st.number_input(
                    "Ajuste (%)",
                    min_value=-50.0, max_value=100.0,
                    value=float(saved.get('ajuste_pct', 0.0)),
                    step=1.0, format="%.1f",
                    key=f"manual_aj_{_safe_key(nombre)}",
                )
            if tiene_ancla:
                st.caption("Valor determinado por el ancla seleccionada.")
            ancla_sel_final = ancla_sel
            usd_m2_oficial = None

        elif fuente_sel == "Valor oficial":
            col_b, col_c, col_d, col_e = st.columns([1, 1, 1, 1])
            ancla_sel_final = "_oficial"
            usd_oficial_val = oficial_display['usd_m2']
            usd_m2_input = st.number_input(
                "USD/m² (oficial)",
                min_value=0.0, max_value=10000.0,
                value=float(usd_oficial_val),
                step=50.0, format="%.0f",
                disabled=True,
                key=f"manual_usd_m2_{_safe_key(nombre)}",
            )
            tiene_ancla = True
            with col_b:
                fh_delta_saved = (float(saved.get('factor_hedonico', default_factor_hedonico)) - 1.0) * 100
                fh_delta = st.number_input(
                    "FH (Δ%)",
                    min_value=-100.0, max_value=400.0,
                    value=fh_delta_saved,
                    step=1.0, format="%.1f",
                    key=f"manual_fh_{_safe_key(nombre)}",
                )
                fh = 1.0 + (fh_delta / 100.0)
            with col_c:
                inc = st.number_input(
                    "Inc. (±%)",
                    min_value=0.0, max_value=100.0,
                    value=float(saved.get('incertidumbre_pct', 10.0)),
                    step=1.0, format="%.0f",
                    key=f"manual_inc_{_safe_key(nombre)}",
                )
            with col_d:
                ajuste_pct = st.number_input(
                    "Ajuste (%)",
                    min_value=-50.0, max_value=100.0,
                    value=float(saved.get('ajuste_pct', 0.0)),
                    step=1.0, format="%.1f",
                    key=f"manual_aj_{_safe_key(nombre)}",
                )
            fuente_detalle = oficial_display.get('fuente', ['N/A'])
            fuente_fecha = oficial_display.get('fecha', 'N/A')
            fuente_zona = oficial_display.get('zona', zona_prop)
            st.caption(f"Fuente: {', '.join(fuente_detalle) if isinstance(fuente_detalle, list) else fuente_detalle} ({fuente_fecha}). Zona: {fuente_zona}. Precio de publicacion.")
            usd_m2_oficial = oficial_display

        else:
            # Fallback: no debería llegar aquí
            col_b, col_c, col_d, col_e = st.columns([1, 1, 1, 1])
            ancla_sel_final = ''
            usd_m2_input = st.number_input(
                "USD/m²",
                min_value=0.0, max_value=10000.0,
                value=float(saved.get('usd_m2', 0)),
                step=50.0, format="%.0f",
                key=f"manual_usd_m2_{_safe_key(nombre)}",
            )
            tiene_ancla = False
            with col_b:
                fh_delta_saved = (float(saved.get('factor_hedonico', default_factor_hedonico)) - 1.0) * 100
                fh_delta = st.number_input(
                    "FH (Δ%)",
                    min_value=-100.0, max_value=400.0,
                    value=fh_delta_saved,
                    step=1.0, format="%.1f",
                    key=f"manual_fh_{_safe_key(nombre)}",
                )
                fh = 1.0 + (fh_delta / 100.0)
            with col_c:
                inc = st.number_input(
                    "Inc. (±%)",
                    min_value=0.0, max_value=100.0,
                    value=float(saved.get('incertidumbre_pct', 10.0)),
                    step=1.0, format="%.0f",
                    key=f"manual_inc_{_safe_key(nombre)}",
                )
            with col_d:
                ajuste_pct = st.number_input(
                    "Ajuste (%)",
                    min_value=-50.0, max_value=100.0,
                    value=float(saved.get('ajuste_pct', 0.0)),
                    step=1.0, format="%.1f",
                    key=f"manual_aj_{_safe_key(nombre)}",
                )
            st.caption("Ingresá el valor USD/m² manualmente.")
            ancla_sel_final = ''
            usd_m2_oficial = None

        # Checkbox: prima de constructora
        constr_check_label = f"Prima de constructora ({constr_label})" if constr_label else "Prima de constructora"
        saved['incluir_prima_const'] = st.checkbox(
            constr_check_label,
            value=saved.get('incluir_prima_const', True),
            key=f"manual_incluir_const_{_safe_key(nombre)}",
        )

        # Activos (solo lectura, inline)
        activos_parts = []
        if cant_cocheras > 0:
            coef_tipo_act = {'cubierta': 1.0, 'semicubierta': 0.7, 'descubierta': 0.4}.get(tipo_cochera, 1.0)
            vbc = prop.get('valor_cochera_base', usd_m2_input * 12)
            for i in range(1, cant_cocheras + 1):
                fu = 1.0 if i == 1 else 0.7 if i == 2 else 0.5
                v = vbc * coef_tipo_act * fu
                activos_parts.append(f"Cochera {i}: ${v:,.0f} USD")
        if valor_baulera > 0:
            activos_parts.append(f"Baulera: ${valor_baulera:,.0f} USD")
        if activos_parts:
            # Estilo unificado para coincidir con las etiquetas de los widgets (como Ajuste por Tamaño)
            st.markdown(
                f'<div style="color:#31333F; font-size:14px; margin:4px 0; font-family: \'Inter\', sans-serif;">'
                f'<span style="font-weight:600;">Activos adicionales:</span> '
                f'{ " · ".join(activos_parts) }'
                f'</div>', 
                unsafe_allow_html=True
            )
        else:
            st.markdown('<div style="color:#9CA3AF; font-size:14px; margin:4px 0; font-family: \'Inter\', sans-serif;">Sin activos adicionales</div>', unsafe_allow_html=True)

        # Subfactores de Referencia (display only)
        try:
            fd = calcular_factores_display(prop)
            if fd:
                sub_pct_estado = (fd['factor_estado'] - 1.0) * 100
                sub_pct_calidad = (fd['factor_calidad'] - 1.0) * 100
                sub_pct_amenities = fd['delta_amenities'] * 100
                sub_pct_otros = fd['delta_otros'] * 100
                with st.container(border=True):
                    st.markdown("**Subfactores de Referencia**")
                    col_a, col_b, col_c, col_d = st.columns(4)
                    with col_a:
                        st.markdown(f"Estado: **{sub_pct_estado:+.1f}%**")
                    with col_b:
                        st.markdown(f"Calidad: **{sub_pct_calidad:+.1f}%**")
                    with col_c:
                        st.markdown(f"Amenities: **{sub_pct_amenities:+.1f}%**")
                    with col_d:
                        st.markdown(f"Otros: **{sub_pct_otros:+.1f}%**")
                    st.caption(f"Factor combinado de referencia: **{fd['total']:.4f}**")
        except Exception:
            pass

    # ========================================================================
    # BLOQUE 2: PREVIEW CALCULATOR (custom HTML)
    # ========================================================================
    m2_eq = calcular_m2_equivalentes(prop)
    fh_eff = fh if fh != 0 else 1.0

    # Size adjustment
    size_adj = 1.0
    # Calcular preview matching generar_resultado_manual
    # Size adjustment ya integrado en ancla (usd_m2 ya incluye size_adj)
    constr_mult = factor_const if saved.get('incluir_prima_const', True) else 1.0
    pre_sub = m2_eq * usd_m2_input * fh_eff * constr_mult

    pre_act = 0
    if cant_cocheras > 0:
        coef_tipo_act = {'cubierta': 1.0, 'semicubierta': 0.7, 'descubierta': 0.4}.get(tipo_cochera, 1.0)
        vbc = prop.get('valor_cochera_base', usd_m2_input * 12)
        for i in range(1, cant_cocheras + 1):
            fu = 1.0 if i == 1 else 0.7 if i == 2 else 0.5
            pre_act += vbc * coef_tipo_act * fu
    pre_act += valor_baulera

    pre_subtotal = pre_sub + pre_act
    pre_final = pre_subtotal * (1 + ajuste_pct / 100.0)

    delta_pct = ((pre_final - motor_valor) / motor_valor * 100) if motor_valor > 0 else 0

    pre_cons = pre_final * (1 - inc / 100.0)
    pre_opt = pre_final * (1 + inc / 100.0)

    constr_display = f"{constr_label}" if constr_label and saved.get('incluir_prima_const', True) else "—"
    constr_pct_str = f"+{pct_const}%" if pct_const > 0 else ("—" if not constr_label else f"{pct_const}%")

    preview_html = f"""
    <div style="background:#ffffff;border:1px solid #d1d5db;border-radius:10px;padding:20px;margin:16px 0;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;">
        <div>
          <div style="color:#000000;font-size:13px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">
            Valor Manual Estimado
          </div>
          <div style="font-size:30px;font-weight:700;color:#000000;margin:4px 0;font-family:system-ui,-apple-system,sans-serif;">
            ${pre_final:,.0f} USD
          </div>
          <div style="color:#333333;font-size:13px;">
            Rango: ${pre_cons:,.0f} – ${pre_opt:,.0f} USD (±{inc:.0f}%)
          </div>
        </div>
      </div>
      <hr style="margin:14px 0;border:none;border-top:1px solid #d1d5db;">
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px 16px;font-size:13px;color:#333333;">
        <div><span style="color:#000000;font-weight:600;">m² eq.:</span> {m2_eq:,.0f}</div>
        <div><span style="color:#000000;font-weight:600;">USD/m²:</span> ${usd_m2_input:,.0f}</div>
        <div><span style="color:#000000;font-weight:600;">FH:</span> {(fh_eff-1.0)*100:+.1f}%</div>
        <div><span style="color:#000000;font-weight:600;">Constructora:</span> {constr_pct_str}</div>
        <div><span style="color:#000000;font-weight:600;">Ajuste %:</span> {ajuste_pct:+.1f}%</div>
        <div><span style="color:#000000;font-weight:600;">Incertidumbre:</span> ±{inc:.0f}%</div>
        <div><span style="color:#000000;font-weight:600;">Activos:</span> ${pre_act:,.0f}</div>
      </div>
      <div style="color:#333333;font-size:11px;margin-top:10px;padding-top:10px;border-top:1px solid #d1d5db;">
        m2_eq x USD/m2 x FH x constr + activos x (1 + ajuste)
      </div>
    </div>
    """

    if usd_m2_input > 0:
        st.markdown(preview_html, unsafe_allow_html=True)
    else:
        with st.container(border=True):
            st.warning("Ingrese un valor de USD/m² para ver la previsualizacion.")

    # ========================================================================
    # BLOQUE 3: ACCION
    # ========================================================================
    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        # Verificar si los parámetros actuales difieren de los guardados en la UV
        params_changed = False
        if saved_params:
            # Comparar solo los parámetros editables
            checks = [
                ('ancla_id', ancla_sel_final),
                ('usd_m2', usd_m2_input),
                ('factor_hedonico', fh),
                ('incertidumbre_pct', inc),
                ('ajuste_pct', ajuste_pct),
                ('incluir_prima_const', saved.get('incluir_prima_const', True)),
            ]
            if saved_params and 'fuente_m2' in saved_params:
                checks.append(('fuente_m2', fuente_sel))
            for key, val in checks:
                if saved_params.get(key) != val:
                    params_changed = True
                    break
        else:
            params_changed = True # Si no hay nada guardado, permitimos guardar

        can_save = usd_m2_input > 0 and params_changed
        
        if st.button("✅ Aplicar Selección", type="primary", use_container_width=True,
                     key=f"manual_guardar_{_safe_key(nombre)}", disabled=not can_save):
            manual_params = {
                'ancla_id': ancla_sel_final,
                'usd_m2': usd_m2_input,
                'factor_hedonico': fh,
                'incertidumbre_pct': inc,
                'ajuste_pct': ajuste_pct,
                'incluir_prima_const': saved.get('incluir_prima_const', True),
                'fecha_guardado': datetime.now().isoformat(),
                'valor_auto_snapshot': motor_valor,
                'fuente_m2': fuente_sel,
                'fuente_m2_detalle': usd_m2_oficial if usd_m2_oficial else None,
            }
            from parsers.mercado_inmobiliario import generar_resultado_manual
            resultado_manual = generar_resultado_manual(prop, manual_params, auto_result=auto_result)
            
            manual_valor_usd = resultado_manual.get('valor_propiedad_usd', 0)
            auto_viene_de = 'fallback-102' if (auto_result and auto_result.get('_fallback_uv', False)) else 'motor'
            auto_result_valor = auto_result.get('valor_propiedad_usd', None) if auto_result else None
            print(f"[DEBUG-MANUAL-SAVE] {nombre}: GUARDANDO manual. "
                  f"manual_valor_usd={manual_valor_usd}, "
                  f"auto_viene_de={auto_viene_de}, "
                  f"auto_result_keys={list(auto_result.keys()) if auto_result else 'NONE'}, "
                  f"auto_result_valor={auto_result_valor}")
            
            props = cargar_propiedades()
            for i, p in enumerate(props):
                if p.get('nombre') == nombre:
                    uv = p.setdefault('_ultima_valuacion', {})
                    old_comp_excluded = uv.get('_comp_excluded', [])
                    old_comp_exclusion_applied = uv.get('_comp_exclusion_applied', False)
                    
                    uv_antes = {k: uv.get(k) for k in ('valor_usd', 'auto_valor_usd', 'manual_valor_usd', 'fuente', 'fuente_activa')}
                    print(f"[DEBUG-MANUAL-SAVE] {nombre}: UV ANTES del guardado: {uv_antes}")
                    
                    uv['valor_usd'] = resultado_manual['valor_propiedad_usd']
                    auto_valor_previo = uv.get('auto_valor_usd', None)
                    uv.setdefault('auto_valor_usd', 0)
                    auto_valor_origen = 'uv_preservado' if (auto_valor_previo is not None and auto_valor_previo > 0) else 'uv_init_0'
                    print(f"[DEBUG-MANUAL-SAVE-ORIGEN] {nombre}: auto_valor_usd={uv['auto_valor_usd']}, "
                          f"origen={auto_valor_origen}, previo={auto_valor_previo}, "
                          f"auto_result_cache={auto_result_valor}")
                    uv['manual_valor_usd'] = manual_valor_usd
                    uv['fuente'] = 'manual'
                    uv['fuente_activa'] = 'manual'
                    uv['manual_params'] = manual_params
                    uv['manual_size_adj'] = resultado_manual.get('size_adjustment', 1.0)
                    uv['manual_factor_const'] = resultado_manual.get('factor_const', 1.0)
                    uv['manual_activos_total'] = resultado_manual.get('valor_activos', {}).get('total', 0)
                    uv['manual_constructora'] = resultado_manual.get('constructora', '')
                    uv['retro_dias'] = st.session_state.get(f'retro_meses_{nombre}', 0)
                    flex_active = st.session_state.get(f'flex_active_{nombre}', False)
                    uv['flex_dormitorios'] = [1, 2, 3, 4, 5] if flex_active else None
                    if old_comp_exclusion_applied:
                        uv['_comp_excluded'] = old_comp_excluded
                        uv['_comp_exclusion_applied'] = True
                    else:
                        uv.setdefault('_comp_excluded', [])
                        uv.setdefault('_comp_exclusion_applied', False)
                    uv_despues = {k: uv.get(k) for k in ('valor_usd', 'auto_valor_usd', 'manual_valor_usd', 'fuente', 'fuente_activa')}
                    print(f"[DEBUG-MANUAL-SAVE] {nombre}: UV DESPUES del guardado: {uv_despues}")
                    break
            if not guardar_propiedades(props):
                st.error("Error de escritura en propiedades.json. La valuacion manual NO se guardo.")
                st.rerun()
            prop['_ultima_valuacion'] = uv
            st.session_state.pop(ss_key, None)
            st.session_state.pop(f'_official_result_{nombre}', None)
            st.session_state.pop(f'preview_mode_{nombre}', None)
            st.session_state[f'manual_feedback_{_safe_key(nombre)}'] = 'guardado'
            st.rerun()


    with col_btn2:
        if saved_params:
            if st.button("🔄 Limpiar", use_container_width=True,
                         key=f"manual_eliminar_{_safe_key(nombre)}"):
                props = cargar_propiedades()
                for i, p in enumerate(props):
                    if p.get('nombre') == nombre:
                        uv = p.setdefault('_ultima_valuacion', {})
                        auto_valor = uv.get('auto_valor_usd', 0)
                        if auto_valor > 0:
                            uv['fuente'] = 'auto'
                            uv['fuente_activa'] = 'auto'
                            uv['valor_usd'] = auto_valor
                        else:
                            uv['fuente'] = 'auto'
                            uv['fuente_activa'] = 'auto'
                            uv['valor_usd'] = 0
                        uv.pop('manual_params', None)
                        uv['manual_valor_usd'] = 0
                        uv.pop('manual_size_adj', None)
                        uv.pop('manual_factor_const', None)
                        uv.pop('manual_activos_total', None)
                        uv.pop('manual_constructora', None)
                        print(f"[DEBUG-DELETE-103] {nombre}: manual eliminado, auto_valor_usd={auto_valor}, valor_usd={uv['valor_usd']}")
                        break
                if not guardar_propiedades(props):
                    st.error("Error de escritura en propiedades.json. La valuacion manual NO se elimino.")
                    print(f"[DEBUG-MANUAL-DELETE] {nombre}: guardar_propiedades FALLO")
                    st.rerun()
                prop['_ultima_valuacion'] = uv
                st.session_state.pop(ss_key, None)
                st.session_state.pop(f'_official_result_{nombre}', None)
                st.session_state.pop(f'preview_mode_{nombre}', None)
                print(f"[DEBUG-MANUAL-DELETE] {nombre}: ELIMINACION EXITOSA — prop actualizado en memoria")
                st.session_state[f'manual_feedback_{_safe_key(nombre)}'] = 'eliminado'
                st.rerun()



