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
    st.markdown('<div class="page-header"><div><h1 style="margin:0;color:#1A2B5C;">🏘️ Propiedades</h1><p style="margin:0;color:#6B7280;">Portfolio Inmobiliario · Rosario, Argentina</p></div></div>', unsafe_allow_html=True)
    
    total_usd = sum(r.get('valor_propiedad_usd', 0) for r in resultados.values())
    n_props = len(propiedades)
    cap_prom = sum(r.get('cap_rate', 0) for r in resultados.values()) / n_props if n_props else 0
    usdt_ars = obtener_usdt_ars_binance()

    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(kpi_card("💼", "Portfolio Total", f"${total_usd:,.0f} USD", f"${total_usd*usdt_ars/1e6:.1f}M ARS"), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card("🏘️", "Propiedades", f"{n_props}", "unidades activas"), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card("📈", "Cap Rate Promedio", f"{cap_prom*100:.1f}%", "rendimiento neto", border_color="#16A34A"), unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    
    cols = st.columns(3)
    for i, prop in enumerate(propiedades):
        nombre = prop.get('nombre', '')
        res = resultados.get(nombre, {})
        cache_info = res.get('_cache', {})
        
        # Get cache date for display
        cache_fecha = ''
        if cache_info.get('recalculado'):
            cache_fecha = '🆕'
        else:
            fecha = cache_info.get('fecha_calculo', '')
            if fecha:
                cache_fecha = f"📅 {fecha}"
        
        with cols[i % 3]:
            st.markdown(property_card(
                nombre, prop.get('zona', 'Oeste'), res.get('m2_equivalentes', 0),
                prop.get('dormitorios', 0), prop.get('tipo_inmueble', 'Depto'),
                res.get('valor_propiedad_usd', 0), res.get('cap_rate', 0),
                res.get('alquiler_estimado_ars', 0), 
                res.get('resolution_metadata', {}).get('n_propiedades', 0),
                cache_info=cache_fecha
            ), unsafe_allow_html=True)
            if st.button(f"Ver detalle de {nombre} →", key=f"btn_{nombre}", width='stretch'):
                st.session_state.prop_sel = nombre
                st.rerun()

def mostrar_detalle_valu(prop, res, guardar_fn):
    # Cache indicator and recalculate button
    cache_info = res.get('_cache', {})
    col_cache, col_back, col_recalc, col_edit = st.columns([2, 3, 1, 1])
    
    with col_cache:
        if cache_info.get('recalculado'):
            razon = cache_info.get('razon', '')
            razones_texto = {
                'primera_vez': 'calculado por primera vez',
                'propiedad_modificada': 'recalculado por cambio en datos',
                'scraping_actualizado': 'recalculado por nuevo scraping',
                'ttl_expirado': 'recalculado (24h expiradas)',
                'forzado_por_usuario': 'recalculado manualmente'
            }
            st.success(f"✅ {razones_texto.get(razon, razon)}")
        else:
            fecha_calc = cache_info.get('fecha_calculo', '?')
            st.caption(f"📅 Valuación del {fecha_calc} · Desde caché")
    
    with col_back:
        if st.button("← Volver al Portfolio"):
            st.session_state.prop_sel = None
            st.rerun()
    
    with col_recalc:
        nombre = prop.get('nombre', '')
        if st.button("🔄", key=f"recalc_{nombre}", help="Forzar recálculo"):
            st.session_state[f'forzar_recalculo_{nombre}'] = True
            st.rerun()
    
    with col_edit:
        if st.button("✏️ Editar Propiedad", width='stretch'):
            st.session_state[f"edit_{prop['id']}"] = True

    if st.session_state.get(f"edit_{prop['id']}", False):
        with st.form(f"f_edit_{prop['id']}"):
            new_data = ui_formulario_propiedad(prop_inicial=prop, key_suffix="edit")
            if st.form_submit_button("Guardar Cambios", type="primary"):
                guardar_fn(new_data)
                st.session_state[f"edit_{prop['id']}"] = False
                st.rerun()
            if st.form_submit_button("Cancelar"):
                st.session_state[f"edit_{prop['id']}"] = False
                st.rerun()

    nombre = prop.get('nombre', '')
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
    cap = res.get('cap_rate', 0)
    with m1: st.markdown(metric_card("💰", "Alquiler Estimado", f"${alq_ars:,.0f} ARS", f"${alq_ars/dolar:,.0f} USD/mes"), unsafe_allow_html=True)
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
    if razonamiento:
        with st.expander("📋 Informe de Valuación", expanded=True):
            st.markdown(razonamiento)
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

# --- MAIN APP ---
def main():
    if 'page' not in st.session_state: st.session_state.page = "Splash"
    if 'prop_sel' not in st.session_state: st.session_state.prop_sel = None

    # Sidebar Navigation
    with st.sidebar:
        st.markdown('<div style="padding:10px 0;"><h2 style="color:white;margin:0;">🏠 Valu</h2><p style="color:#006AFF;font-size:11px;margin:0;font-weight:700;text-transform:uppercase;letter-spacing:1px;">Valuador de Propiedades</p></div>', unsafe_allow_html=True)
        st.markdown("---")
        
        st.session_state.page = st.radio("NAVEGACIÓN", ["Splash", "Portfolio", "Inventario", "Cargar Mercado", "Configuración"])
        
        st.markdown("---")
        datos = cargar_datos()
        meses = sorted(datos.get('meses', {}).keys(), reverse=True) or ["2026-05"]
        mes_sel = st.selectbox("PERÍODO", meses)
        
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        st.markdown('<p style="color:rgba(255,255,255,0.3);font-size:10px;text-align:center;">v2.5 · Powered by VPP Engine</p>', unsafe_allow_html=True)

    if st.session_state.page == "Splash":
        st.markdown(LANDING_HTML, unsafe_allow_html=True)
        if st.button("Comenzar →", type="primary"):
            st.session_state.page = "Portfolio"
            st.rerun()

    elif st.session_state.page == "Portfolio":
        propiedades = cargar_propiedades()
        if not propiedades:
            st.info("No hay propiedades registradas. Agregá una en Configuración.")
        else:
            from parsers.motor_vpp_core import valuar_con_cache
            
            # Botón global para recalcular todo
            col_global, _ = st.columns([1, 4])
            with col_global:
                if st.button("🔄 Recalcular todo", help="Recalcula todas las propiedades ignorando el caché"):
                    st.session_state['forzar_recalculo_global'] = True
                    st.rerun()
            
            resultados = {}
            forzar_global = st.session_state.get('forzar_recalculo_global', False)
            if forzar_global:
                st.session_state['forzar_recalculo_global'] = False
            
            with st.spinner("Valuando portfolio..."):
                for p in propiedades:
                    forzar = forzar_global or st.session_state.get(f'forzar_recalculo_{p.get("nombre", "")}', False)
                    if forzar:
                        st.session_state[f'forzar_recalculo_{p.get("nombre", "")}'] = False
                    resultados[p['nombre']] = valuar_con_cache(p, fecha_ref=mes_sel, forzar_recalculo=forzar)
            
            if st.session_state.prop_sel:
                p_obj = next(p for p in propiedades if p['nombre'] == st.session_state.prop_sel)
                mostrar_detalle_valu(p_obj, resultados[p_obj['nombre']], lambda d: st.info("Guardado demo"))
            else:
                mostrar_dashboard_valu(propiedades, resultados)

    elif st.session_state.page == "Inventario":
        st.markdown('<div class="page-header"><div><h1 style="margin:0;color:#1A2B5C;">📋 Inventario & Seguimiento</h1><p style="margin:0;color:#6B7280;">Listado detallado de propiedades y fechas de publicación</p></div></div>', unsafe_allow_html=True)
        
        propiedades = cargar_propiedades()
        if not propiedades:
            st.info("No hay propiedades registradas.")
        else:
            df = pd.DataFrame(propiedades)
            
            # Formatear para visualización
            display_cols = {
                'nombre': 'Nombre',
                'tipo_inmueble': 'Tipo',
                'zona': 'Zona',
                'm2_cubiertos': 'm² Cub.',
                'dormitorios': 'Dorm.',
                'baños': 'Baños',
                'fecha_publicacion': 'Publicado el',
                'estado_detalle': 'Estado'
            }
            
            # Asegurar que existan todas las columnas
            for col in display_cols.keys():
                if col not in df.columns:
                    df[col] = "—"
            
            df_display = df[list(display_cols.keys())].rename(columns=display_cols)
            
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

if __name__ == "__main__":
    main()
