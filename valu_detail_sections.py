"""
Secciones del detalle de propiedad. Funciones de renderizado UI puras.
Cada funcion recibe datos y renderiza una seccion especifica.
Son llamadas desde mostrar_detalle_valu() en valu.py.
"""
import streamlit as st
import pandas as pd
import json, os, logging

logger = logging.getLogger(__name__)
from datetime import datetime
from valu_design import kpi_card, metric_card, hero_price, range_bar, insights_card, property_card
from streamlit.components.v1 import html
from parsers.mercado_inmobiliario import calcular_vm2_por_seleccion


def render_actions(prop, guardar_fn):
    """Barra de acciones: Volver, Editar, Limpiar, Eliminar."""
    nombre = prop.get('nombre', '')
    prop_id = prop.get('id', nombre)
    col_back, col_edit, col_clean, col_delete = st.columns([1.5, 1, 1.5, 1])
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
    with col_clean:
        if st.button("🗑️ Limpiar Valuación", type="secondary", use_container_width=True,
                     key=f"action_limpiar_{prop_id}"):
            st.session_state[f"clean_valuacion_{nombre}"] = True
            st.rerun()
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
            uv['fuente_activa'] = fuente
            break
    guardar_propiedades(props)
    st.session_state[f'fuente_activa_{nombre}'] = fuente


def render_header(prop, res):
    """Hero con badges, titulo, confianza, precio y toggle Automática/Manual."""
    from datetime import datetime
    nombre = prop.get('nombre', '')

    # Leer datos paralelos
    auto_result = res.get('_auto_result', res)
    manual_result = res.get('_manual_result')
    manual_params = res.get('_manual_params') or {}
    fuente_activa = res.get('_fuente_activa', 'auto')

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
    m2_puro = meta.get('_m2_puro', m2_base)
    barrier_pct = meta.get('barrier_pct', 0)
    n_comps = meta.get('n_propiedades', 0)

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

    # ─── Toggle Pills ───
    tiene_auto = auto_result.get('m2_base_venta', 0) > 0
    tiene_manual = manual_result is not None

    pill_key = f'fuente_activa_{nombre}'
    col_toggle = st.columns([1, 1, 4])
    with col_toggle[0]:
        if st.button("● Por Comparables", type="primary",
                     use_container_width=True, disabled=not tiene_auto,
                     key=f"{pill_key}_auto"):
            _set_fuente_activa(nombre, 'auto')
            st.rerun()
    with col_toggle[1]:
        if st.button("○ Manual", type="primary",
                     use_container_width=True, disabled=not tiene_manual,
                     key=f"{pill_key}_manual"):
            _set_fuente_activa(nombre, 'manual')
            st.rerun()

    # ─── Alertas de divergencia ───
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

    # ─── Hero card ───
    c_h1, c_h2 = st.columns([3, 2])
    # Label de fuente activa
    fuente_label = "MANUAL" if es_manual else "POR COMPARABLES"
    fuente_color = "#7C3AED" if es_manual else "#16A34A"
    fuente_badge_color = "#7C3AED15" if es_manual else "#16A34A15"
    with c_h1:
        fuente_badge = f"<span class='badge' style='background:{fuente_badge_color};color:{fuente_color};margin-left:5px;'>{fuente_label}</span>"

        dot = '#16A34A' if n_comps >= 15 else '#F59E0B' if n_comps >= 8 else '#DC2626'
        conf = 'Alta confianza' if n_comps >= 15 else 'Confianza media' if n_comps >= 8 else 'Confianza baja'
        st.markdown(f"""
        <div style="background:white;border-radius:16px;padding:28px;box-shadow:0 4px 12px rgba(0,0,0,0.08);height:100%;">
            <div style="margin-bottom:12px;">
                <span class="badge" style="background:#006AFF15;color:#006AFF;">{prop.get('tipo_inmueble','').upper()}</span>
                <span class="badge" style="background:#0D948815;color:#0D9488;margin-left:5px;">{zona.upper()}</span>
                <span class="badge" style="background:#F4F6FB;color:#6B7280;margin-left:5px;">ANO {prop.get('anio_construccion','?')}</span>
                {fuente_badge}
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
    fuente_subtitle = "VALUACIÓN MANUAL" if es_manual else "VALUACIÓN POR COMPARABLES"
    with c_h2:
        if m2_base == 0:
            st.markdown("""
            <div style="background:#F4F6FB;border-radius:16px;padding:28px;text-align:center;height:100%;display:flex;flex-direction:column;justify-content:center;font-family:'Inter',sans-serif;">
                <div style="font-size:14px;color:#6B7280;margin-bottom:8px;">""" + fuente_subtitle + """</div>
                <div style="font-size:24px;font-weight:700;color:#9CA3AF;">Sin selección</div>
                <div style="font-size:13px;color:#9CA3AF;margin-top:8px;">Seleccioná al menos 2 comparables</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(hero_price(valor_usd, valor_usd*dolar, dolar, m2_base, n_comps, zona,
                                  m2_puro=m2_puro, barrier_pct=barrier_pct, fuente_label=fuente_subtitle), unsafe_allow_html=True)


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
            html(mapa_html, height=350)
    else:
        st.caption("Mapa no disponible")


def _get_comp_id(c):
    """Genera un ID único y estable para un comparable basado en sus datos."""
    import hashlib
    # Usamos datos que no cambian entre renders para crear un hash estable
    seed = f"{c.get('precio')}_{c.get('m2')}_{c.get('direccion_limpia') or c.get('direccion')}_{c.get('lat')}_{c.get('lon')}"
    return hashlib.md5(seed.encode()).hexdigest()[:12]

def render_tabla_comparables(res, prop_name=None):
    """Tabla de propiedades comparables utilizadas con checkbox de selección.
    Muestra el recálculo P33/P50 según los comps seleccionados.
    """
    if not prop_name:
        prop_name = 'default'
    if res.get('retro_activo'):
        st.caption(f"🔙 Retro activo: ventana de {res.get('total_dias_ventana', 180)} días")
    comparables = res.get('comparables_venta', [])
    if not comparables:
        st.caption("Sin comparables disponibles")
        return

    # 1. Determinar estado de selección actual para controlar visibilidad de botones
    sel_key = f'comp_selection_{prop_name}'
    comp_ids = [_get_comp_id(c) for c in comparables]
    stored_sel = st.session_state.get(sel_key, None)
    if stored_sel is None:
        excluded = res.get('_comp_excluded')
        if excluded:
            stored_sel = set(cid for cid in comp_ids if cid not in excluded)
        else:
            stored_sel = set(comp_ids)
        st.session_state[sel_key] = stored_sel
    if not isinstance(stored_sel, set):
        stored_sel = set(stored_sel)

    # Obtener selección actual desde los checkboxes en session_state (en vivo)
    current_sel = set()
    for cid in comp_ids:
        chk_key = f'sel_comp_{prop_name}_{cid}'
        if chk_key in st.session_state:
            if st.session_state[chk_key]:
                current_sel.add(cid)
        elif cid in stored_sel:
            current_sel.add(cid)

    # Banner de info + botón Restablecer (también visible si hay comps desmarcados en UI)
    n_excluidos = res.get('_n_excluidos', 0)
    if n_excluidos or len(current_sel) < len(comparables):
        col_info, col_reset = st.columns([3, 1])
        with col_info:
            n_desel = len(comparables) - len(current_sel)
            if n_excluidos:
                st.info(f"⚡ {len(current_sel)}/{len(comparables)} comparables activos ({n_excluidos} excluidos por el usuario).")
            else:
                st.info(f"⚡ {n_desel} comparable(s) desmarcado(s) — Aplicar selección para recalcular.")
        with col_reset:
            if st.button("↩️ Restablecer todos", key=f'reset_comp_sel_{prop_name}', use_container_width=True):
                # 1. Setear todas las keys de checkbox a True
                for cid in comp_ids:
                    st.session_state[f'sel_comp_{prop_name}_{cid}'] = True
                # 2. Sincronizar estado global de selección
                st.session_state[f'comp_selection_{prop_name}'] = set(comp_ids)
                # 3. Setear flag _reset_all para que valu.py persista estado limpio
                st.session_state[f'_reset_all_{prop_name}'] = True
                # 4. Limpiar exclusión y forzar recálculo
                st.session_state.pop(f'comp_excluded_{prop_name}', None)
                st.session_state.pop(f'_comp_interacted_{prop_name}', None)
                st.session_state[f'forzar_recalculo_{prop_name}'] = True
                st.rerun()

    # Cabecera de la tabla
    hdr = st.columns([0.4, 0.5, 1.5, 0.8, 1.5, 0.6, 0.9, 2, 0.7, 0.6])
    hdr_labels = ['', '#', 'Precio USD', 'm²', 'Precio/m²', 'Dorm', 'Publicado', 'Dirección', 'Año', 'Dist']
    for col, label in zip(hdr, hdr_labels):
        col.markdown(f"**{label}**")

    selected_ids = set()
    for i, c in enumerate(comparables):
        comp_id = comp_ids[i]
        cols = st.columns([0.4, 0.5, 1.5, 0.8, 1.5, 0.6, 0.9, 2, 0.7, 0.6])

        # Sincronizar checkbox con stored_sel antes de crear widget
        chk_key = f'sel_comp_{prop_name}_{comp_id}'
        if chk_key not in st.session_state:
            st.session_state[chk_key] = comp_id in stored_sel
        checked = cols[0].checkbox("", key=chk_key)

        if checked:
            selected_ids.add(comp_id)
        else:
            # Si el usuario desmarca, removemos el ID del set en session_state inmediatamente
            if comp_id in stored_sel:
                stored_sel.remove(comp_id)

        cols[1].write(str(i+1))
        cols[2].write(f"${c.get('precio', 0):,.0f}")
        cols[3].write(f"{c.get('m2', 0):.0f}")
        # Precio/m2 con badges
        ta = c.get('time_adjustment', 1.0)
        bp = c.get('barrier_penalty', 1.0)
        vm2_orig = c.get('precio_m2', 0)
        vm2_ajust = c.get('precio_m2_ajustado', vm2_orig * ta)
        badges = ""
        if ta != 1.0:
            badges += " <span style='background:#ff6b35;color:white;font-size:9px;padding:1px 4px;border-radius:6px;font-weight:bold;'>RETRO</span>"
        if badges:
            cols[4].markdown(f"<span style='font-weight:bold'>${vm2_ajust:,.0f}</span>{badges}", unsafe_allow_html=True)
        else:
            cols[4].markdown(f"<span style='color:#2ecc71;font-weight:bold'>${vm2_orig:,.0f}</span>", unsafe_allow_html=True)
        cols[5].write(str(c.get('dormitorios', '?')))
        cols[6].write(str((c.get('date_created') or '')[:10]) if c.get('date_created') else '')
        cols[7].write(((c.get('direccion_limpia') or c.get('direccion','')) or '')[:35])
        cols[8].write(str(c.get('anio_estimado', '')) if c.get('anio_estimado') else '')
        cols[9].write(f"{c.get('distancia_m', 0):.0f}m" if c.get('distancia_m') else '')


    # Guardar selección actual
    st.session_state[sel_key] = selected_ids

    # Vista previa en vivo usando misma lógica que "Aplicar selección" (percentil por CV)
    if selected_ids:
        n_sel = len(selected_ids)
        selected_comps = [c for c in comparables if _get_comp_id(c) in selected_ids]
        preview = calcular_vm2_por_seleccion(selected_comps, res) if len(selected_comps) >= 2 else None

        all_ids = [_get_comp_id(c) for c in comparables]
        excluded_ids = [cid for cid in all_ids if cid not in selected_ids]
        is_applied = set(res.get('_comp_excluded', [])) == set(excluded_ids) and res.get('_comp_exclusion_applied', False)

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
                    st.caption(f"{preview['percentil_label']} de selección • CV={preview['cv']:.2f} • {preview['n_sel']} comps selec. de {len(comparables)} totales")
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
                # Botón visible incluso si no hay exclusiones (todos seleccionados)
                if st.button(
                    f"✅ Aplicar selección ({n_sel}/{len(comparables)})",
                    key=f'apply_comp_sel_{prop_name}',
                    type='primary',
                    use_container_width=True,
                ):
                    from datetime import datetime
                    logger.info(f"[DEBUG-APPLY] ===== INICIO Aplicar selección {prop_name} =====")
                    logger.info(f"[DEBUG-APPLY] {prop_name}: n_sel={n_sel}, n_total={len(comparables)}, n_excluded={len(excluded)}")
                    logger.info(f"[DEBUG-APPLY] {prop_name}: retro_active={st.session_state.get('retro_active_' + prop_name, False)}, flex_active={st.session_state.get('flex_active_' + prop_name, False)}")
                    
                    # Sync slider value before applying selection
                    slider_val = st.session_state.get(f'retro_meses_slider_{prop_name}', 36)
                    st.session_state[f'retro_meses_{prop_name}'] = slider_val
                    logger.info(f"[DEBUG-APPLY] {prop_name}: slider_val={slider_val}")
                    
                    st.session_state[f'comp_excluded_{prop_name}'] = excluded
                    st.session_state[f'forzar_recalculo_{prop_name}'] = True
                    logger.info(f"[DEBUG-APPLY] {prop_name}: Set forzar_recalculo=True, excluded={excluded}")
                    logger.info(f"[DEBUG-APPLY] {prop_name} ===== FIN Aplicar selección =====, calling st.rerun()")
                    st.rerun()
    elif not selected_ids:
        st.warning("⚠️ Seleccioná al menos un comparable para calcular el valor.")
        if st.button("Seleccionar todos", key=f'sel_all_{prop_name}'):
            st.session_state[sel_key] = set([_get_comp_id(c) for c in comparables])
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


# ─── REPORTE PDF ───
from io import BytesIO
from fpdf import FPDF

def generar_reporte_pdf(prop: dict, res: dict, auto_result: dict = None) -> bytes:
    from datetime import datetime
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=18)

    w = pdf.w - 20

    # Header
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(w, 10, "VALU - Reporte de Valuacion", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(w, 6, f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Propiedad
    pdf.set_fill_color(248, 250, 252)
    pdf.rect(10, pdf.get_y(), w, 40, "F")
    y_start = pdf.get_y() + 4
    pdf.set_xy(14, y_start)
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(50, 5, "PROPIEDAD")
    pdf.set_xy(14, y_start + 7)
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(90, 7, prop.get("nombre", ""))
    pdf.set_xy(14, y_start + 15)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(100, 116, 139)
    direccion = prop.get("direccion", "Rosario, Argentina")
    tipo = prop.get("tipo_inmueble", "")
    zona = prop.get("zona", "")
    pdf.cell(90, 5, f"{direccion}  |  {tipo}  |  {zona}")
    m2 = prop.get("m2_cubiertos", 0)
    dorm = prop.get("dormitorios", 0)
    anio = prop.get("anio_construccion", "?")
    pdf.set_xy(110, y_start + 7)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(30, 6, f"{m2} m2")
    pdf.set_xy(140, y_start + 7)
    pdf.cell(30, 6, f"{dorm} dorm")
    pdf.set_xy(170, y_start + 7)
    pdf.cell(30, 6, f"Ano {anio}")
    pdf.set_y(y_start + 44)
    pdf.ln(4)

    # ─── Opción B: Ambos valores (Auto + Manual) ───
    manual_params = res.get('manual_params', {}) or {}
    if not manual_params and auto_result:
        manual_params = auto_result.get('_manual_params', {}) or {}
    tiene_manual = bool(manual_params)

    if tiene_manual and auto_result:
        # Valor Automático
        v_auto = auto_result.get("valor_propiedad_usd", 0)
        v_auto_cons = auto_result.get("valor_venta_conservador", 0)
        v_auto_opt = auto_result.get("valor_venta_optimista", 0)
        v_auto_m2 = auto_result.get("m2_base_venta", 0)
        v_auto_n = auto_result.get("resolution_metadata", {}).get("n_propiedades", 0)

        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(16, 185, 129)
        pdf.cell(w, 5, "VALOR DE MERCADO ESTADÍSTICO", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(0, 106, 255)
        pdf.cell(w, 8, f"USD {v_auto:,.0f}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(w, 4, f"Conservador: USD {v_auto_cons:,.0f}  |  Optimista: USD {v_auto_opt:,.0f}", new_x="LMARGIN", new_y="NEXT")
        pdf.cell(w, 4, f"{v_auto_n} comparables  ·  ${v_auto_m2:,.0f}/m² base", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        # Valor Manual
        v_manual = res.get("valor_propiedad_usd", 0)
        v_manual_cons = res.get("valor_venta_conservador", 0)
        v_manual_opt = res.get("valor_venta_optimista", 0)
        delta = ((v_manual - v_auto) / v_auto * 100) if v_auto > 0 else 0

        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(124, 58, 237)  # purple for manual
        pdf.cell(w, 5, "VALOR SEGÚN CRITERIO DEL TASADOR", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "B", 14)
        pdf.set_text_color(124, 58, 237)
        pdf.cell(w, 8, f"USD {v_manual:,.0f}  (Dif. {delta:+.1f}%)", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(w, 4, f"Conservador: USD {v_manual_cons:,.0f}  |  Optimista: USD {v_manual_opt:,.0f}", new_x="LMARGIN", new_y="NEXT")

        motivo = manual_params.get('motivo', '')
        if motivo:
            pdf.ln(2)
            pdf.set_font("Helvetica", "I", 8)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(w, 4, f"Motivo del ajuste: {motivo}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        # Hard block: divergencia > 5% sin motivo
        from io import BytesIO
        if abs(delta) > 5 and not manual_params.get('motivo', '').strip():
            pdf.set_font("Helvetica", "B", 10)
            pdf.set_text_color(220, 38, 38)
            pdf.cell(w, 6, "(!) DOCUMENTE EL MOTIVO DEL AJUSTE PARA EXPORTAR ESTE INFORME", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(2)

        pdf.set_draw_color(226, 232, 240)
        pdf.line(10, pdf.get_y(), w + 10, pdf.get_y())
        pdf.ln(4)

        # Valor adoptado (fuente activa)
        fuente_activa = res.get('_fuente_activa', 'auto')
        if fuente_activa == 'manual':
            adoptado = v_manual
            label_fuente = "Manual (Tasador)"
        else:
            adoptado = v_auto
            label_fuente = "Automática (Mercado)"
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(w, 5, f"Valor adoptado: USD {adoptado:,.0f}  |  Fuente: {label_fuente}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

        # Metricas clave (usar el res principal que ya incluye el resultado activo)
        alq = res.get("alquiler_estimado_ars", 0)
        cap = res.get("cap_rate", 0)
        m2_base = res.get("m2_base_venta", 0)
        m2_eq = res.get("m2_equivalentes", 0)
        dolar = res.get("usdt_ars", 1480)
    else:
        # Solo automático: sección simple (comportamiento original)
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(16, 185, 129)
        pdf.cell(w, 5, "VALOR ESTIMADO", new_x="LMARGIN", new_y="NEXT")
        valor_usd = res.get("valor_propiedad_usd", 0)
        v_cons = res.get("valor_venta_conservador", 0)
        v_opt = res.get("valor_venta_optimista", 0)
        pdf.set_font("Helvetica", "B", 24)
        pdf.set_text_color(0, 106, 255)
        pdf.cell(w, 12, f"USD {valor_usd:,.0f}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(w, 5, f"Conservador: USD {v_cons:,.0f}  |  Optimista: USD {v_opt:,.0f}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(6)
        alq = res.get("alquiler_estimado_ars", 0)
        cap = res.get("cap_rate", 0)
        m2_base = res.get("m2_base_venta", 0)
        m2_eq = res.get("m2_equivalentes", 0)
        dolar = res.get("usdt_ars", 1480)

    pdf.set_fill_color(248, 250, 252)
    pdf.rect(10, pdf.get_y(), w, 28, "F")
    y_met = pdf.get_y() + 4
    labels_met = [
        ("Alquiler estimado", f"ARS {alq:,.0f} / USD {alq/dolar:,.0f}"),
        ("Cap Rate", f"{cap*100:.1f}%"),
        ("Base m2", f"USD {m2_base:,.0f}"),
        ("m2 equivalentes", f"{m2_eq:.1f}"),
    ]
    for i, (lbl, val) in enumerate(labels_met):
        x = 14 + (i % 4) * 46
        pdf.set_xy(x, y_met)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(42, 4, lbl)
        pdf.set_xy(x, y_met + 5)
        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(42, 6, val)
    pdf.set_y(y_met + 32)

    # Factores de ajuste
    meta = res.get("resolution_metadata", {}) or {}
    factor = res.get("factor_total", 1.0)
    dep = res.get("delta_anti", 1.0)
    nlp = res.get("nlp_ajuste", 0)
    calidad = prop.get("calidad_edificio", "Estandar")

    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(w, 5, "FACTORES DE AJUSTE", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    for lbl, val in [
        ("Factor total", f"{(factor-1)*100:+.1f}%"),
        ("Depreciacion", f"{(dep-1)*100:+.1f}%"),
        ("Ajuste NLP", f"{nlp*100:+.1f}%"),
        ("Calidad", calidad),
    ]:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(50, 5, lbl)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(30, 5, val, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Activos adicionales (cocheras + baulera)
    val_activos = res.get("valor_activos", {}) or {}
    if val_activos.get("total", 0) > 0:
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(16, 185, 129)
        pdf.cell(w, 5, "ACTIVOS ADICIONALES", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        for lbl, val in [
            ("Cocheras", f"USD {val_activos.get('cocheras', 0):,.0f}"),
            ("Baulera", f"USD {val_activos.get('baulera', 0):,.0f}"),
            ("Total activos", f"USD {val_activos['total']:,.0f}"),
        ]:
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(50, 5, lbl)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(30, 5, val, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # Comparables
    comps = res.get("comparables_venta", [])
    n_comps = meta.get("n_propiedades", meta.get("n_filtradas", len(comps)))
    precio_m2_prom = 0
    dist_prom = 0
    if comps:
        precio_m2_prom = sum(c.get("precio_m2", 0) or 0 for c in comps) / len(comps)
        dist_prom = sum(c.get("distancia_m", 0) or 0 for c in comps) / len(comps)

    if n_comps >= 15:
        conf = "Alta"
    elif n_comps >= 8:
        conf = "Media"
    else:
        conf = "Baja"

    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(16, 185, 129)
    pdf.cell(w, 5, "COMPARABLES", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    for lbl, val in [
        ("Cantidad", str(n_comps)),
        ("Precio/m2 prom.", f"USD {precio_m2_prom:,.0f}"),
        ("Distancia prom.", f"{dist_prom:.0f} m"),
        ("Confianza", conf),
    ]:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(100, 116, 139)
        pdf.cell(50, 5, lbl)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(30, 5, val, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Catastro
    catastro = res.get("catastro_detalle", None)
    candidatos = catastro.get("candidatos", []) if catastro else []
    if candidatos:
        sel = next((c for c in candidatos if c.get("recomendado")), candidatos[0])
        pdf.set_font("Helvetica", "B", 7)
        pdf.set_text_color(16, 185, 129)
        pdf.cell(w, 5, "CATASTRO", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        ph = sel.get("ph", "")
        anio_cat = int(float(sel["year"])) if sel.get("year") else "N/A"
        secc = int(float(sel["seccion"])) if sel.get("seccion") else "-"
        mza = int(float(sel["manzana"])) if sel.get("manzana") else "-"
        graf = int(float(sel["grafico"])) if sel.get("grafico") else "-"
        for lbl, val in [
            ("PH", str(ph)),
            ("Ano const.", str(anio_cat)),
            ("Seccion", str(secc)),
            ("Manzana", str(mza)),
            ("Grafico", str(graf)),
        ]:
            pdf.set_font("Helvetica", "", 9)
            pdf.set_text_color(100, 116, 139)
            pdf.cell(30, 5, lbl)
            pdf.set_font("Helvetica", "B", 9)
            pdf.set_text_color(15, 23, 42)
            pdf.cell(20, 5, val, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # Footer metadata
    from parsers.valuacion_cache import CACHE_VERSION
    cache_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache_scraping.json")
    fecha_scraping = ""
    if os.path.exists(cache_path):
        mtime = os.path.getmtime(cache_path)
        fecha_scraping = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")

    pdf.ln(4)
    pdf.set_draw_color(226, 232, 240)
    pdf.line(10, pdf.get_y(), w + 10, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(148, 163, 184)
    pdf.cell(w, 4, f"Version: {CACHE_VERSION}  |  Mercado: {fecha_scraping}", new_x="LMARGIN", new_y="NEXT")
    if meta.get("age_blend_applied"):
        alpha = meta.get("alpha_age_blend", 0)
        n_age = meta.get("n_age_filtered", 0)
        pdf.cell(w, 4, f"Age blend aplicado: alpha={alpha:.2f}, n_edad={n_age}", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())


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

    # ─── Carga de anclas ───
    anclas = cargar_anclas()
    ancla_options = {a.get('id', a.get('nombre', '')): a for a in anclas}
    ancla_display_map = {}
    for a in anclas:
        aid = a.get('id', a.get('nombre', ''))
        v = a.get('usd_m2', 0)
        ancla_display_map[f"{aid} (${v:,}/m2)"] = {'id': aid, 'usd_m2': v}
    ancla_display_list = sorted(ancla_display_map.keys())
    ancla_display_list = ["Sin Ancla"] + ancla_display_list

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
        default_ancla_id = ancla_por_zona.get('id', '') if ancla_por_zona else 'Sin Ancla'
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
                'incluir_size_adj': True,
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

        # Fila 1: Ancla + USD/m2
        col_a, col_b = st.columns(2)
        with col_a:
            saved_display = "Sin Ancla"
            for dk in ancla_display_list:
                if ancla_display_map.get(dk, {}).get('id') == saved.get('ancla_id', ''):
                    saved_display = dk
                    break
            if saved_display == "Sin Ancla" and saved.get('ancla_id'):
                saved_display = ancla_display_list[0]
            ancla_display_sel = st.selectbox(
                "Ancla de referencia",
                options=ancla_display_list,
                index=ancla_display_list.index(saved_display) if saved_display in ancla_display_list else 0,
                key=f"manual_ancla_{nombre}",
            )
            ancla_sel = "Sin Ancla"
            if ancla_display_sel in ancla_display_map:
                ancla_sel = ancla_display_map[ancla_display_sel]['id']
        with col_b:
            tiene_ancla = ancla_sel != "Sin Ancla"
            usd_display = saved.get('usd_m2', default_usd_m2)
            if tiene_ancla and ancla_sel in ancla_options:
                usd_display = ancla_options[ancla_sel].get('usd_m2', usd_display)
            usd_m2_input = st.number_input(
                "USD/m²",
                min_value=0.0, max_value=10000.0,
                value=float(usd_display or 0),
                step=50.0, format="%.0f",
                disabled=tiene_ancla,
                key=f"manual_usd_m2_{nombre}",
            )
            if tiene_ancla:
                st.caption("Valor determinado por el ancla. Deseleccioná el ancla para editar manualmente.")

        # Fila 2: FH + Incertidumbre
        col_c, col_d = st.columns(2)
        with col_c:
            fh = st.number_input(
                "Factor Hedonico",
                min_value=0.0, max_value=5.0,
                value=float(saved.get('factor_hedonico', default_factor_hedonico)),
                step=0.05, format="%.4f",
                key=f"manual_fh_{nombre}",
            )
        with col_d:
            inc = st.number_input(
                "Incertidumbre (±%)",
                min_value=0.0, max_value=100.0,
                value=float(saved.get('incertidumbre_pct', 10.0)),
                step=1.0, format="%.0f",
                key=f"manual_inc_{nombre}",
            )

        # Fila 3: Ajuste %
        ajuste_pct = st.number_input(
            "Ajuste porcentual (%)",
            min_value=-50.0, max_value=100.0,
            value=float(saved.get('ajuste_pct', 0.0)),
            step=1.0, format="%.1f",
            key=f"manual_aj_{nombre}",
        )

        # Fila 4: checkboxes lado a lado
        col_f, col_g = st.columns(2)
        with col_f:
            saved['incluir_size_adj'] = st.checkbox(
                f"Incluir ajuste por tamano ({_mz_name})",
                value=saved.get('incluir_size_adj', True),
                key=f"manual_incluir_size_{nombre}",
            )
        with col_g:
            if constr_label:
                saved['incluir_prima_const'] = st.checkbox(
                    f"Incluir prima de constructora ({constr_label})",
                    value=saved.get('incluir_prima_const', True),
                    key=f"manual_incluir_const_{nombre}",
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
            st.caption(f"**Activos adicionales:** {' · '.join(activos_parts)}")
        else:
            st.caption("Sin activos adicionales")

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
    if saved.get('incluir_size_adj', True):
        try:
            size_adj = calcular_size_adjustment(
                m2_eq,
                macrozona_id=_mz_info.get('macrozona_id'),
                ancla_id=ancla_sel if ancla_sel != "Sin Ancla" else None,
            )
        except Exception:
            pass

    # Calcular preview matching generar_resultado_manual
    constr_mult = factor_const if saved.get('incluir_prima_const', True) else 1.0
    pre_sub = m2_eq * usd_m2_input * size_adj * fh_eff * constr_mult

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

    # Badge color
    if motor_valor == 0:
        badge_bg = "#F3F4F6"
        badge_fg = "#4B5563"
        badge_label = "Sin referencia del motor"
        badge_display = badge_label
    elif abs(delta_pct) > 20:
        badge_bg = "#FEE2E2"
        badge_fg = "#DC2626"
        badge_label = "Diferencia significativa"
        badge_display = f"D {delta_pct:+.1f}% vs. motor · {badge_label}"
    elif abs(delta_pct) > 10:
        badge_bg = "#FEF3C7"
        badge_fg = "#D97706"
        badge_label = "Diferencia moderada"
        badge_display = f"D {delta_pct:+.1f}% vs. motor · {badge_label}"
    else:
        badge_bg = "#D1FAE5"
        badge_fg = "#059669"
        badge_label = "Diferencia aceptable"
        badge_display = f"D {delta_pct:+.1f}% vs. motor · {badge_label}"

    pre_cons = pre_final * (1 - inc / 100.0)
    pre_opt = pre_final * (1 + inc / 100.0)

    constr_display = f"{constr_label}" if constr_label and saved.get('incluir_prima_const', True) else "—"
    constr_pct_str = f"+{pct_const}%" if pct_const > 0 else ("—" if not constr_label else f"{pct_const}%")
    size_adj_str = f"{size_adj:.4f}" if saved.get('incluir_size_adj', True) else "1.0 (desactivado)"

    preview_html = f"""
    <div style="background:#ffffff;border:1px solid #d1d5db;border-radius:10px;padding:20px;margin:16px 0;">
      <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;">
        <div>
          <div style="color:#000000;font-size:12px;font-weight:600;text-transform:uppercase;letter-spacing:0.5px;">
            Valor Manual Estimado
          </div>
          <div style="font-size:30px;font-weight:700;color:#000000;margin:4px 0;font-family:system-ui,-apple-system,sans-serif;">
            ${pre_final:,.0f} USD
          </div>
          <div style="color:#333333;font-size:13px;">
            Rango: ${pre_cons:,.0f} – ${pre_opt:,.0f} USD (±{inc:.0f}%)
          </div>
        </div>
        <div style="display:flex;flex-direction:column;align-items:flex-end;gap:4px;">
          <span style="background:{badge_bg};color:{badge_fg};padding:4px 12px;border-radius:14px;font-size:13px;font-weight:600;white-space:nowrap;">
            {badge_display}
          </span>
        </div>
      </div>
      <hr style="margin:14px 0;border:none;border-top:1px solid #d1d5db;">
      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px 16px;font-size:13px;color:#333333;">
        <div><span style="color:#000000;font-weight:600;">m² eq.:</span> {m2_eq:,.0f}</div>
        <div><span style="color:#000000;font-weight:600;">USD/m²:</span> ${usd_m2_input:,.0f}</div>
        <div><span style="color:#000000;font-weight:600;">Size adj.:</span> {size_adj_str}</div>
        <div><span style="color:#000000;font-weight:600;">FH:</span> {fh_eff:.4f}</div>
        <div><span style="color:#000000;font-weight:600;">Constructora:</span> {constr_pct_str}</div>
        <div><span style="color:#000000;font-weight:600;">Ajuste %:</span> {ajuste_pct:+.1f}%</div>
        <div><span style="color:#000000;font-weight:600;">Incertidumbre:</span> ±{inc:.0f}%</div>
        <div><span style="color:#000000;font-weight:600;">Activos:</span> ${pre_act:,.0f}</div>
      </div>
      <div style="color:#333333;font-size:11px;margin-top:10px;padding-top:10px;border-top:1px solid #d1d5db;">
        m2_eq x USD/m2 x size_adj x FH x constr + activos x (1 + ajuste)
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
        can_save = usd_m2_input > 0

        if st.button("Guardar Valuacion Manual", type="primary", use_container_width=True,
                     disabled=not can_save, key=f"manual_guardar_{nombre}"):
            if usd_m2_input <= 0:
                st.error("Ingrese un valor de USD/m² valido.")
                st.rerun()

            manual_params = {
                'ancla_id': ancla_sel,
                'usd_m2': usd_m2_input,
                'factor_hedonico': fh,
                'incertidumbre_pct': inc,
                'ajuste_pct': ajuste_pct,
                'incluir_prima_const': saved.get('incluir_prima_const', True),
                'incluir_size_adj': saved.get('incluir_size_adj', True),
                'fecha_guardado': datetime.now().isoformat(),
                'valor_auto_snapshot': motor_valor,
            }
            from parsers.mercado_inmobiliario import generar_resultado_manual
            resultado_manual = generar_resultado_manual(prop, manual_params, auto_result=auto_result)

            from parsers.valuacion_cache import cargar_cache_valuaciones, guardar_cache_valuaciones
            cache = cargar_cache_valuaciones()
            cache.pop(nombre, None)
            guardar_cache_valuaciones(cache)

            props = cargar_propiedades()
            for i, p in enumerate(props):
                if p.get('nombre') == nombre:
                    uv = p.setdefault('_ultima_valuacion', {})
                    uv['valor_usd'] = resultado_manual['valor_propiedad_usd']
                    uv['fuente'] = 'manual'
                    uv['fuente_activa'] = 'manual'
                    uv['manual_params'] = manual_params
                    break
            guardar_propiedades(props)
            st.session_state.pop(ss_key, None)
            st.success(f"Valuacion manual guardada: ${resultado_manual['valor_propiedad_usd']:,.0f} USD")
            st.rerun()

    with col_btn2:
        if saved_params:
            if st.button("Eliminar Valuacion Manual", use_container_width=True,
                         key=f"manual_eliminar_{nombre}"):
                props = cargar_propiedades()
                for i, p in enumerate(props):
                    if p.get('nombre') == nombre:
                        uv = p.setdefault('_ultima_valuacion', {})
                        uv['fuente'] = 'auto'
                        uv['fuente_activa'] = 'auto'
                        uv.pop('manual_params', None)
                        break
                guardar_propiedades(props)
                st.session_state.pop(ss_key, None)
                st.rerun()
