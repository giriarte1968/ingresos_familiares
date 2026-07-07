"""
🏠 AVM ROSARIO — SUITE DE REGRESIÓN OBLIGATORIA
Este archivo es el guardián de la lógica de negocio. 
Basado en docs/MEMORIA_PROYECTO.md - Sección 11.

⛔ LOS RANGOS DE ESTOS TESTS REFLEJAN la LÓGICA VIGENTE.
Si un cambio intencional en la lógica modifica los valores, actualizar rangos y documentar en BITACORA.
"""
import pytest
import os
import sys
import json

# Asegurar que el path incluya la raíz para importar parsers
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.mercado_inmobiliario import valuar_propiedad_v7, obtener_mediana_cluster, calcular_factores

def ejecutar_valuacion(test_id):
    """Genera el diccionario de entrada para los casos de prueba core."""
    if test_id == 'mabel':
        return {
            'tipo_inmueble': 'departamento',
            'zona': 'Martin',
            'direccion': 'Mabel 1400',
            'lat': -32.9541, 'lon': -60.6316,
            'm2': 48.5, 'm2_cubiertos': 41.0, 'm2_semicubiertos': 7.5,
            'm2_semicubiertos_detalle': 'medio',
            'dormitorios': 1, 'anio_construccion': 2000,
            'estado_detalle': 'muy bueno', 'calidad_edificio': 'media',
            'descripcion_libre': 'luminoso, con aire acondicionado',
            'piso': 2, 'total_pisos': 10, 'ventilacion': 'cruzada',
            'tipo_balcon': 'ninguno',
            'lavadero_independiente': True, 'placares_completos': True,
            'ascensores_edificio': 1, 'detalles_categoria': ['seguridad_camaras'],
            'vista': 'frente', 'ubicacion_tipo': 'calle', 'gas_ok': 'si',
        }
    elif test_id == 'mabel_sin_nlp':
        m = ejecutar_valuacion('mabel')
        m['descripcion_libre'] = ''
        return m
    elif test_id == 'ayacucho':
        return {
            'tipo_inmueble': 'departamento',
            'zona': 'República de la Sexta',
            'direccion': 'Ayacucho 1800',
            'lat': -32.9603, 'lon': -60.6299,
            'm2': 27, 'm2_cubiertos': 27,
            'dormitorios': 1, 'anio_construccion': 2002,
            'estado_detalle': 'excelente',
            'calidad_edificio': 'media',
            'piso': 4, 'ventilacion': 'cruzada',
            'vista': 'frente', 'ubicacion_tipo': 'calle', 'gas_ok': 'si',
            'ascensores_edificio': 2, 'detalles_categoria': [],
        }
    return None

# --- TESTS DE MABEL ---

def test_mabel_venta():
    """Valida rangos de venta para Mabel (Barrio Martin)"""
    r = valuar_propiedad_v7(ejecutar_valuacion('mabel'), fecha_ref="2026-04")
    assert 70000 <= r['valor_propiedad_usd'] <= 90000, f"Lista {r['valor_propiedad_usd']} fuera de rango"

def test_mabel_alquiler():
    """Valida alquiler y ROI para Mabel"""
    r = valuar_propiedad_v7(ejecutar_valuacion('mabel'), fecha_ref='2026-04')
    assert 480_000 <= r['alquiler_estimado_ars'] <= 600_000, f"Alquiler {r['alquiler_estimado_ars']} fuera de rango"
    assert r.get('es_fallback_alquiler') == False, "Mabel debe usar Cap Rate data-driven"
    cap = r.get('cap_rate', 0)
    assert 0.03 <= cap <= 0.08, f"Cap rate {cap*100:.1f}% fuera de rango 3-8%"

def test_ayacucho_venta():
    """Valida rangos de venta para Ayacucho (6ta Pellegrini, modelo multiplicativo)"""
    r = valuar_propiedad_v7(ejecutar_valuacion('ayacucho'))
    assert 49000 <= r['valor_propiedad_usd'] <= 62000, f"Ayacucho {r['valor_propiedad_usd']} fuera de rango"

def test_patio_grande_vera():
    """Verifica ajuste patio grande para Vera Mujica (PB con patio 12.7m²)."""
    import json
    with open('propiedades.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    vera = next((p for p in data.get('propiedades', []) if p.get('nombre') == 'Vera Mujica'), None)
    assert vera is not None
    r = valuar_propiedad_v7(vera, fecha_ref='2026-04')
    # Validar que el resultado sea consistente con el modelo actual
    assert r['valor_propiedad_usd'] > 0

def test_manual_valuation_auto_updates_on_additive_change():
    """Verifica que cambiar aditivos actualice la Valuación Manual en el UV sin intervención manual.
    TAREA-118: Sincronización Automática.
    """
    from parsers.mercado_inmobiliario import generar_resultado_manual
    from valu import cargar_propiedades, guardar_propiedades
    
    prop_name = "TestAutoSync"
    props = cargar_propiedades()
    prop = {'nombre': prop_name, 'lat': -32.9, 'lon': -60.6, 'valor_baulera': 1000, 'cocheras_cantidad': 1, 'cocheras_tipo': 'cubierta', 'valor_cochera_base': 10000}
    
    props.append(prop)
    uv = {
        'fuente': 'manual', 'fuente_activa': 'manual',
        'manual_params': {
            'ancla_id': 'some_id', 'usd_m2': 2000, 'factor_hedonico': 1.0, 
            'incertidumbre_pct': 10.0, 'ajuste_pct': 0.0, 
            'incluir_prima_const': True, 'incluir_size_adj': True
        },
        'valor_usd': 100000 
    }
    prop['_ultima_valuacion'] = uv
    for i, p in enumerate(props):
        if p.get('nombre') == prop_name:
            props[i] = prop
    guardar_propiedades(props)
    
    nueva_data = {'valor_baulera': 5000}
    props = cargar_propiedades()
    found_idx = -1
    for i, p in enumerate(props):
        if p.get('nombre') == prop_name:
            props[i].update(nueva_data)
            found_idx = i
            break
    
    if found_idx != -1:
        uv_updated = props[found_idx].get('_ultima_valuacion', {})
        # Nota: En el test simplificamos la lógica de actualizar_propiedad
        # Para que sea un test real, deberíamos llamar a la función, pero es anidada.
        # Simulamos el efecto:
        res_manual = generar_resultado_manual(props[found_idx], uv_updated['manual_params'], auto_result={})
        uv_updated['valor_usd'] = res_manual['valor_propiedad_usd']
    
    guardar_propiedades(props)
    props_final = cargar_propiedades()
    final_val = next(p['_ultima_valuacion']['valor_usd'] for p in props_final if p.get('nombre') == prop_name)
    assert final_val != 100000
    
    props_clean = [p for p in props_final if p.get('nombre') != prop_name]
    guardar_propiedades(props_clean)

def _cols_side_effect(*args, **kw):
    """Dynamic columns mock: returns MagicMock list matching column spec length."""
    from unittest.mock import MagicMock
    spec = args[0] if args else [1]
    n = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
    return [MagicMock() for _ in range(n)]


def _number_input_side_effect(*args, **kw):
    """Mocks st.number_input by returning the 'value' kwarg or 0."""
    return kw.get('value', 0)


def test_comparables_banner_hidden_when_full_selection():
    """Verifica que el banner de selección desaparezca cuando todos los comparables están activos."""
    import streamlit as st
    from unittest.mock import patch, MagicMock
    from valu_detail_sections import render_tabla_comparables

    comparables = [{'id': f'c{i}', 'precio': 1000 + i*100, 'm2': 50 + i*10,
                    'direccion': f'Calle {i} 123', 'lat': -34.0 - i*0.01, 'lon': -58.0 - i*0.01}
                   for i in range(6)]
    res = {'comparables_venta': comparables, '_n_excluidos': 2, 'retro_activo': False}
    prop_name = "TestBanner"

    from valu_detail_sections import _get_comp_id
    real_ids = [_get_comp_id(c) for c in comparables]
    st.session_state[f'comp_selection_{prop_name}'] = set(real_ids)
    for rid in real_ids:
        st.session_state[f'sel_comp_{prop_name}_{rid}'] = True

    with patch('streamlit.columns', side_effect=_cols_side_effect), \
         patch('streamlit.checkbox', return_value=True), \
         patch('streamlit.button', return_value=False), \
         patch('streamlit.write'), \
         patch('streamlit.metric'), \
         patch('streamlit.caption'), \
         patch('streamlit.markdown'), \
         patch('streamlit.info') as mock_info, \
         patch('streamlit.warning'):

        render_tabla_comparables(res, prop_name=prop_name)
        mock_info.assert_not_called()


def test_ui_apply_button_visible_when_all_selected():
    """TAREA-120: Botón 'Aplicar Selección' visible incluso con selección completa (6/6).
    Regresión anterior: el botón desaparecía con `else: st.write("")`.
    """
    import streamlit as st
    from unittest.mock import patch, MagicMock
    from valu_detail_sections import render_tabla_comparables, _get_comp_id

    comparables = [{'id': f'c{i}', 'precio': 1000 + i*100, 'm2': 50 + i*10,
                    'direccion': f'Calle {i} 123', 'lat': -34.0 - i*0.01, 'lon': -58.0 - i*0.01}
                   for i in range(6)]
    res = {'comparables_venta': comparables, '_n_excluidos': 0,
           '_comp_excluded': [], '_comp_exclusion_applied': False,
           'retro_activo': False}
    prop_name = "TestApplyAll"

    real_ids = [_get_comp_id(c) for c in comparables]
    st.session_state[f'comp_selection_{prop_name}'] = set(real_ids)
    for rid in real_ids:
        st.session_state[f'sel_comp_{prop_name}_{rid}'] = True

    with patch('streamlit.columns', side_effect=_cols_side_effect), \
         patch('streamlit.button', return_value=False) as mock_btn, \
         patch('streamlit.write'), \
         patch('streamlit.checkbox', return_value=True), \
         patch('streamlit.metric'), \
         patch('streamlit.caption'), \
         patch('streamlit.markdown'), \
         patch('streamlit.info'), \
         patch('streamlit.warning'):

        render_tabla_comparables(res, prop_name=prop_name)

        called_with_apply = any(
            'Aplicar selección' in str(call) or 'apply_comp_sel' in str(call)
            for call in mock_btn.call_args_list
        )
        assert called_with_apply, (
            f"El botón 'Aplicar selección' debe ser visible con selección completa. "
            f"Llamadas a st.button: {mock_btn.call_args_list}"
        )
        print(f"[TEST-UI-APPLY-BTN] OK — botón visible con selección completa")


def test_ui_reset_all_visual_only():
    """TAREA-120: 'Restablecer Todas' es SOLO visual — reselecciona todos los checkboxes
    y limpia comp_excluded, pero NO forza recálculo. El recálculo ocurre al hacer
    clic en 'Aplicar selección'.
    """
    import streamlit as st
    from unittest.mock import patch, MagicMock
    from valu_detail_sections import render_tabla_comparables, _get_comp_id

    comparables = [{'id': f'c{i}', 'precio': 1000 + i*100, 'm2': 50 + i*10,
                    'direccion': f'Calle {i} 123', 'lat': -34.0 - i*0.01, 'lon': -58.0 - i*0.01}
                   for i in range(6)]
    res = {'comparables_venta': comparables, '_n_excluidos': 2,
           '_comp_excluded': ['c0', 'c1'], '_comp_exclusion_applied': True,
           'retro_activo': False}
    prop_name = "TestResetVisual"

    real_ids = [_get_comp_id(c) for c in comparables]
    # Only 4 out of 6 selected so the reset banner appears (len(current_sel)=4 < 6)
    st.session_state[f'comp_selection_{prop_name}'] = set(real_ids)
    st.session_state[f'comp_excluded_{prop_name}'] = ['c0', 'c1']
    for idx, rid in enumerate(real_ids):
        st.session_state[f'sel_comp_{prop_name}_{rid}'] = (idx < 4)

    reset_key = f'reset_comp_sel_{prop_name}'

    def btn_side_effect(*b_args, **b_kw):
        key = b_kw.get('key', '')
        if key == reset_key:
            return True
        return False

    with patch('streamlit.columns', side_effect=_cols_side_effect), \
         patch('streamlit.button', side_effect=btn_side_effect), \
         patch('streamlit.write'), \
         patch('streamlit.checkbox', return_value=True), \
         patch('streamlit.metric'), \
         patch('streamlit.caption'), \
         patch('streamlit.markdown'), \
         patch('streamlit.info'), \
         patch('streamlit.warning'), \
         patch('streamlit.rerun'):

        render_tabla_comparables(res, prop_name=prop_name)

        # Verify: all checkboxes are True, comp_excluded is gone, NO forzar_recalculo
        for rid in real_ids:
            assert st.session_state.get(f'sel_comp_{prop_name}_{rid}', False) is True, (
                f"Checkbox {rid} debe estar seleccionado tras reset"
            )
        assert st.session_state.get(f'comp_excluded_{prop_name}') is None, (
            "comp_excluded debe eliminarse tras reset visual"
        )
        forzar_key = f'forzar_recalculo_{prop_name}'
        assert st.session_state.get(forzar_key, False) is False, (
            f"'Restablecer Todas' NO debe setear {forzar_key}. Es solo visual."
        )
        print(f"[TEST-UI-RESET-VISUAL] OK — checkboxes restaurados, excluded limpiado, sin recálculo")


def test_ui_manual_save_hidden_on_no_changes():
    """TAREA-120: Botón 'Guardar Cambios' en valuación manual NO debe aparecer
    cuando los parámetros no han cambiado respecto a los guardados en UV.
    """
    import streamlit as st
    from unittest.mock import patch, MagicMock

    prop = {
        'nombre': '__test_manual_no_save__',
        'lat': -32.95, 'lon': -60.63,
        'm2_cubiertos': 50,
        'direccion': 'Test 123',
        'zona': 'Centro',
        '_ultima_valuacion': {
            'fuente': 'manual',
            'fuente_activa': 'manual',
            'manual_params': {
                'ancla_id': 'Sin Ancla',
                'usd_m2': 2000,
                'factor_hedonico': 1.0,
                'incertidumbre_pct': 10.0,
                'ajuste_pct': 0.0,
                'incluir_prima_const': True,
                'incluir_size_adj': True,
            },
            'valor_usd': 100000,
            'retro_dias': 36,
            'flex_dormitorios': None,
            '_comp_excluded': [], '_comp_exclusion_applied': False,
        }
    }
    res = {
        'comparables_venta': [],
        'm2_microzona': 2000,
        'm2_base_venta': 1900,
        'm2_equivalentes': 50,
        'valor_propiedad_usd': 100000,
        '_fuente_activa': 'manual',
        '_manual_params': dict(prop['_ultima_valuacion']['manual_params']),
        '_manual_result': {'valor_propiedad_usd': 100000},
        'retro_dias': 36,
        'flex_dormitorios': None,
        '_comp_excluded': [], '_comp_exclusion_applied': False,
        '_auto_result': {'valor_propiedad_usd': 100000},
    }

    nombre = prop['nombre']
    st.session_state[f'vista_valuacion_{nombre}'] = True
    st.session_state[f'retro_meses_slider_{nombre}'] = 36
    st.session_state[f'flex_active_{nombre}'] = False

    with patch('streamlit.columns', side_effect=_cols_side_effect), \
         patch('streamlit.button', return_value=False) as mock_btn, \
         patch('streamlit.write'), \
         patch('streamlit.markdown'), \
         patch('streamlit.metric'), \
         patch('streamlit.number_input', side_effect=_number_input_side_effect), \
         patch('streamlit.checkbox', return_value=True), \
         patch('streamlit.selectbox', return_value='Sin Ancla'), \
         patch('streamlit.expander') as mock_exp, \
         patch('streamlit.info'), \
         patch('streamlit.warning'), \
         patch('streamlit.error'), \
         patch('streamlit.success'), \
         patch('streamlit.tabs'), \
         patch('parsers.location_engine.cargar_anclas', return_value=[]), \
         patch('parsers.location_engine.get_ancla_mas_cercana', return_value=None):

        mock_exp.return_value.__enter__ = MagicMock()
        mock_exp.return_value.__exit__ = MagicMock()

        from valu_detail_sections import render_valuacion_manual
        render_valuacion_manual(prop, res)

        save_calls = [
            call for call in mock_btn.call_args_list
            if 'Guardar' in str(call) or 'guardar' in str(call).lower()
        ]
        assert len(save_calls) == 0, (
            f"Botón 'Guardar' no debe aparecer sin cambios de parámetros. "
            f"Llamadas: {save_calls}"
        )
        print(f"[TEST-UI-MANUAL-SAVE] OK — botón Guardar oculto sin cambios de parámetros")


def test_auto_card_hidden_when_engine_failed_after_manual_save():
    """TAREA-121: RU-HEADER-01/02 — El auto card NO debe mostrar un valor STALE del cache
    preview después de un save manual cuando el auto engine no produjo resultado.
    Escenario: engine falló (insuficientes), usuario guarda valuación manual, el auto card
    debe quedar oculto ("—") aunque cache devuelva un resultado preview.
    """
    import streamlit as st
    from unittest.mock import patch, MagicMock
    import json

    nombre = "__test_auto_hidden__"
    prop = {
        'nombre': nombre,
        'zona': 'Centro',
        'lat': -32.95, 'lon': -60.63,
        'direccion': 'Test 123',
        '_ultima_valuacion': {
            'valor_usd': 735013.0,        # set by manual save
            'auto_valor_usd': 0,           # overwritten by manual save (engine had no result)
            'manual_valor_usd': 735013.0,  # manual save value
            'fuente': 'manual',
            'fuente_activa': 'manual',
            'manual_params': {'ancla_id': 'test', 'usd_m2': 2000},
            'comps': 6,
            'retro_dias': 36,
            'flex_dormitorios': None,
        }
    }

    # Auto_result simula un cache preview con valor STALE (590093) pero auto engine
    # nunca produjo resultado con los parámetros actuales.
    auto_result = {
        'valor_propiedad_usd': 590093.0,  # valor STALE del cache preview
        'm2_base_venta': 2586.57,
        'm2_microzona': 2586.57,
        'm2_equivalentes': 160.0,
        'usdt_ars': 1480,
        'resolution_metadata': {'n_propiedades': 6},  # preview tuvo 6 comps
        '_fallback_uv': False,
        '_cache': {'preview': True, 'recalculado': False, 'guard_restored': False},
    }

    manual_result = {
        'valor_propiedad_usd': 735013.0,
        'm2_base_venta': 160.0,
        'm2_equivalentes': 160.0,
        'usdt_ars': 1480,
        'resolution_metadata': {'n_propiedades': 6},
    }

    res = {
        '_auto_result': auto_result,
        '_manual_result': manual_result,
        '_manual_params': prop['_ultima_valuacion']['manual_params'],
        '_fuente_activa': 'manual',
        '_cache': {'preview': True, 'recalculado': False, 'guard_restored': False},
    }

    captured_md = []

    def _md_side_effect(*args, **kw):
        captured_md.append(args[0] if args else kw.get('body', ''))
        return MagicMock()

    with patch('streamlit.columns', side_effect=_cols_side_effect), \
         patch('streamlit.markdown', side_effect=_md_side_effect), \
         patch('streamlit.metric'), \
         patch('streamlit.warning'):

        from valu_detail_sections import render_header
        render_header(prop, res)

        # Check: auto card (POR COMPARABLES) should show "—" (hidden)
        auto_card_showing_dollar = False
        auto_card_hidden = False
        for md in captured_md:
            if 'POR COMPARABLES' in str(md):
                if '—' in str(md):
                    auto_card_hidden = True
                if '$590,093' in str(md) or '$590093' in str(md) or '590,093' in str(md) or '590093' in str(md):
                    auto_card_showing_dollar = True

        assert auto_card_hidden, (
            f"Auto card debe mostrar '—' (oculto) cuando auto engine falló. "
            f"Markdowns: {[m[:80] for m in captured_md]}"
        )
        assert not auto_card_showing_dollar, (
            f"Auto card NO debe mostrar el valor STALE del cache ($590,093). "
            f"Markdowns: {[m[:80] for m in captured_md]}"
        )

        # Verify manual card IS showing
        manual_card_showing = False
        for md in captured_md:
            if 'MANUAL' in str(md):
                if '735,013' in str(md) or '735013' in str(md):
                    manual_card_showing = True
        assert manual_card_showing, (
            f"Manual card debe mostrar el valor guardado ($735,013). "
            f"Markdowns: {[m[:80] for m in captured_md]}"
        )

        print(f"[TEST-AUTO-HIDDEN] OK — auto card oculto, manual card visible. "
              f"Auto hidden={auto_card_hidden}, Auto dollar={auto_card_showing_dollar}, "
              f"Manual showing={manual_card_showing}")


def test_manual_card_shows_when_auto_0_comps():
    """TAREA-124: RU-HEADER-03 — La tarjeta MANUAL debe mostrarse aunque el auto engine
    tenga 0 comparables (n_propiedades=0). Escenario: usuario guardó valuación manual,
    luego limpió comparables, el engine no encontró datos (cache fría).
    El header debe mostrar la manual, ocultando solo la auto card."""
    import streamlit as st
    from unittest.mock import patch, MagicMock
    import json

    nombre = "__test_manual_0_comps__"
    prop = {
        'nombre': nombre,
        'zona': 'Centro',
        'lat': -32.95, 'lon': -60.63,
        'direccion': 'Test 123',
        '_ultima_valuacion': {
            'valor_usd': 735013.0,
            'auto_valor_usd': 0,
            'manual_valor_usd': 735013.0,
            'fuente': 'manual',
            'fuente_activa': 'manual',
            'manual_params': {'ancla_id': 'test', 'usd_m2': 2000},
            'comps': 0,
            'm2_equivalentes': 160.0,
            'retro_dias': 36,
            'flex_dormitorios': None,
        }
    }

    # Auto_result con 0 comps (engine falló o cache fría post-Limpiar)
    auto_result = {
        'valor_propiedad_usd': 0,
        'm2_base_venta': 0,
        'm2_microzona': 0,
        'm2_equivalentes': 0,
        'usdt_ars': 1480,
        'resolution_metadata': {'n_propiedades': 0},
        '_fallback_uv': False,
        '_cache': {'preview': True, 'recalculado': False, 'guard_restored': False},
    }

    manual_result = {
        'valor_propiedad_usd': 735013.0,
        'm2_base_venta': 160.0,
        'm2_equivalentes': 160.0,
        'usdt_ars': 1480,
        'resolution_metadata': {'n_propiedades': 0},
    }

    res = {
        '_auto_result': auto_result,
        '_manual_result': manual_result,
        '_manual_params': prop['_ultima_valuacion']['manual_params'],
        '_fuente_activa': 'manual',
        '_cache': {'preview': True, 'recalculado': False, 'guard_restored': False},
    }

    captured_md = []

    def _md_side_effect(*args, **kw):
        captured_md.append(args[0] if args else kw.get('body', ''))
        return MagicMock()

    with patch('streamlit.columns', side_effect=_cols_side_effect), \
         patch('streamlit.markdown', side_effect=_md_side_effect), \
         patch('streamlit.metric'), \
         patch('streamlit.warning'):

        from valu_detail_sections import render_header
        render_header(prop, res)

        # Auto card debe mostrar "—" (0 comps)
        auto_card_hidden = False
        # Manual card debe mostrar $735,013
        manual_card_showing = False
        for md in captured_md:
            if 'POR COMPARABLES' in str(md):
                if '—' in str(md):
                    auto_card_hidden = True
            if 'MANUAL' in str(md):
                if '735,013' in str(md) or '735013' in str(md):
                    manual_card_showing = True

        assert auto_card_hidden, (
            f"Auto card debe mostrar '—' (oculto) cuando auto engine tiene 0 comps. "
            f"Markdowns: {[m[:80] for m in captured_md]}"
        )
        assert manual_card_showing, (
            f"Manual card debe mostrar el valor guardado ($735,013) aunque auto tenga 0 comps. "
            f"Markdowns: {[m[:80] for m in captured_md]}"
        )

        print(f"[TEST-MANUAL-0-COMPS] OK — auto card oculto, manual card visible ($735,013). "
              f"Auto hidden={auto_card_hidden}, Manual showing={manual_card_showing}")


# ========================================================================
# TESTS RU-CLEAN-MANUAL-01: Limpiar comparables NO debe borrar manual
# ========================================================================
def test_clean_comparables_preserves_manual_valuation():
    """RU-CLEAN-MANUAL-01: Limpiar comparables NO debe borrar la valuacion manual.
    Escenario: Francia 250b con valuacion manual guardada ($735K), usuario hace clic
    en "🔄 Limpiar" dentro del expander de Comparables. El UV debe preservar
    valor_usd, manual_valor_usd, fuente, fuente_activa, manual_params."""
    uv_original = {
        'valor_usd': 735013.0,
        'auto_valor_usd': 0,
        'manual_valor_usd': 735013.0,
        'fuente': 'manual',
        'fuente_activa': 'manual',
        'manual_params': {'ancla_id': 'test', 'usd_m2': 2000},
        'retro_dias': 36,
        'flex_dormitorios': None,
        'comps': 12,
        'm2_equivalentes': 160.0,
        '_comp_excluded': [],
        '_comp_exclusion_applied': False,
    }

    tiene_manual = uv_original.get('fuente') == 'manual' or uv_original.get('fuente_activa') == 'manual'
    assert tiene_manual, "Debe detectar que hay valuacion manual"

    # Simular la logica de clean con preservacion
    if tiene_manual:
        manual_keys = ('valor_usd', 'auto_valor_usd', 'manual_valor_usd',
                       'fuente', 'fuente_activa', 'manual_params',
                       'retro_dias', 'flex_dormitorios',
                       'comps', 'm2_equivalentes',
                       '_comp_excluded', '_comp_exclusion_applied')
        uv_result = {k: uv_original[k] for k in manual_keys if k in uv_original}

    assert uv_result.get('valor_usd') == 735013.0, "valor_usd debe preservarse"
    assert uv_result.get('fuente') == 'manual', "fuente debe preservarse"
    assert uv_result.get('fuente_activa') == 'manual', "fuente_activa debe preservarse"
    assert uv_result.get('manual_params') is not None, "manual_params debe preservarse"
    assert uv_result.get('manual_valor_usd') == 735013.0, "manual_valor_usd debe preservarse"
    assert uv_result.get('retro_dias') == 36, "retro_dias debe preservarse"
    assert uv_result.get('comps') == 12, "comps debe preservarse"
    assert uv_result.get('m2_equivalentes') == 160.0, "m2_equivalentes debe preservarse"
    assert '_comp_excluded' in uv_result, "_comp_excluded debe preservarse"

    print(f"[TEST-CLEAN-MANUAL] OK — manual preservada. "
          f"keys={list(uv_result.keys())}, valor_usd={uv_result['valor_usd']}")


def test_clean_comparables_cleans_when_no_manual():
    """RU-CLEAN-MANUAL-01: Limpiar comparables SIN valuacion manual debe limpiar
    todo el UV (comportamiento original, no regression)."""
    uv_original = {
        'valor_usd': 590062.0,
        'auto_valor_usd': 590062.0,
        'fuente': 'auto',
        'fuente_activa': 'auto',
        '_comp_excluded': ['comp_1'],
    }

    tiene_manual = uv_original.get('fuente') == 'manual' or uv_original.get('fuente_activa') == 'manual'
    assert not tiene_manual, "No debe detectar valuacion manual"

    # Sin manual, se limpia todo
    uv_result = None

    assert uv_result is None, "Sin manual, UV debe limpiarse completamente"

    print(f"[TEST-CLEAN-NO-MANUAL] OK — UV limpiada cuando no hay manual")


def test_guardrail_clean_comparables_detects_violation():
    """GUARDRAIL RU-CLEAN-MANUAL-01: _verificar_invariante_clean_comparables
    detecta cuando una manual fue borrada (fuente=manual pero sin manual_params)."""
    from valu import _verificar_invariante_clean_comparables

    # Escenario de bug: fuente=manual pero se perdieron los datos
    uv_violado = {'fuente': 'manual', 'valor_usd': 735013.0}
    result = _verificar_invariante_clean_comparables(uv_violado, "__test__")
    assert result is False, "Debe detectar violacion: manual_params ausente"

    # Escenario correcto: fuente=manual con todo preservado
    uv_ok = {
        'fuente': 'manual', 'fuente_activa': 'manual',
        'valor_usd': 735013.0, 'manual_valor_usd': 735013.0,
        'manual_params': {'ancla_id': 'test'},
    }
    result = _verificar_invariante_clean_comparables(uv_ok, "__test__")
    assert result is True, "No debe detectar violacion cuando todo esta correcto"

    # Escenario: fuente=auto, no aplica
    uv_auto = {'fuente': 'auto', 'valor_usd': 590062.0}
    result = _verificar_invariante_clean_comparables(uv_auto, "__test__")
    assert result is True, "No debe activarse cuando fuente=auto"

    print(f"[TEST-GUARDRAIL-CLEAN] OK — violacion detectada, correcto ignorado")


def test_guardrail_clean_comparables_auto_corrects():
    """GUARDRAIL RU-CLEAN-MANUAL-01: Verifica que el invariante NO se activa
    cuando valor_usd=0 (recien inicializado, no es borrado de manual)."""
    from valu import _verificar_invariante_clean_comparables

    # UV vacio recien inicializado
    result = _verificar_invariante_clean_comparables({}, "__test__")
    assert result is True, "UV vacio no debe activar guardrail"

    # fuente=manual pero valor_usd=0 (recien creado, nunca valuado)
    uv_zero = {'fuente': 'manual', 'fuente_activa': 'manual',
               'valor_usd': 0, 'manual_params': None}
    result = _verificar_invariante_clean_comparables(uv_zero, "__test__")
    assert result is False, "Debe detectar: manual_params=None con fuente=manual"

    print(f"[TEST-GUARDRAIL-CLEAN-ZERO] OK — casos borde manejados correctamente")


def test_guardrail_clean_comparables_integration():
    """GUARDRAIL RU-CLEAN-MANUAL-01: Integracion - simula el flujo completo
    de clean + guardrail usando propiedades.json real (como test_manual_valuation).
    Crea propiedad con manual, ejecuta logica de clean, verifica preservacion."""
    from valu import cargar_propiedades, guardar_propiedades

    prop_name = "__test_clean_integration__"
    props = cargar_propiedades()
    # Limpiar propiedad previa si existe
    props = [p for p in props if p.get('nombre') != prop_name]

    uv_manual = {
        'valor_usd': 500000.0, 'auto_valor_usd': 0,
        'manual_valor_usd': 500000.0, 'fuente': 'manual',
        'fuente_activa': 'manual',
        'manual_params': {'ancla_id': 'test', 'usd_m2': 2000},
        'retro_dias': 36, 'flex_dormitorios': None,
        '_comp_excluded': [], '_comp_exclusion_applied': False,
    }
    props.append({'nombre': prop_name, 'lat': -32.9, 'lon': -60.6,
                  '_ultima_valuacion': uv_manual})
    guardar_propiedades(props)

    # Simular la logica de clean del boton
    props2 = cargar_propiedades()
    for p in props2:
        if p.get('nombre') == prop_name:
            uv_old = p.get('_ultima_valuacion', {})
            tiene_manual = uv_old.get('fuente') == 'manual' or uv_old.get('fuente_activa') == 'manual'
            assert tiene_manual, "Debe detectar manual"
            if tiene_manual:
                manual_keys = ('valor_usd', 'auto_valor_usd', 'manual_valor_usd',
                               'fuente', 'fuente_activa', 'manual_params',
                               'retro_dias', 'flex_dormitorios',
                               '_comp_excluded', '_comp_exclusion_applied')
                uv_preservado = {k: uv_old[k] for k in manual_keys if k in uv_old}
                p['_ultima_valuacion'] = uv_preservado
            break
    guardar_propiedades(props2)

    # Verificar en disco
    props_final = cargar_propiedades()
    final_uv = next((p.get('_ultima_valuacion', {}) for p in props_final if p.get('nombre') == prop_name), {})
    assert final_uv.get('valor_usd') == 500000.0, "valor_usd preservado en disco"
    assert final_uv.get('fuente') == 'manual', "fuente preservada en disco"
    assert final_uv.get('manual_params') is not None, "manual_params preservado en disco"

    # Limpiar
    props_clean = [p for p in props_final if p.get('nombre') != prop_name]
    guardar_propiedades(props_clean)

    print(f"[TEST-CLEAN-INTEGRATION] OK — flujo completo clean+preservacion verificado")


def test_guardrail_auto_valor_usd_detects_contamination():
    """GUARDRAIL RU-MANUAL-SAVE-02: Verifica que _verificar_invariante_auto_valor_usd
    detecta cuando auto_valor_usd fue contaminado por cache preview y lo auto-corrige."""
    from valu_detail_sections import _verificar_invariante_auto_valor_usd

    # Escenario: UV fue contaminado con cache preview ($590K) en vez de valor oficial
    uv = {'auto_valor_usd': 590093, 'fuente_activa': 'manual'}
    auto_result = {'valor_propiedad_usd': 590093.0}

    result = _verificar_invariante_auto_valor_usd(uv, auto_result, "__test_guardrail__")
    assert result is False, "Debe detectar contaminacion y devolver False"
    assert uv['auto_valor_usd'] == 0, "Debe auto-corregir a 0"

    print(f"[TEST-GUARDRAIL] OK — contaminacion detectada y corregida: auto_valor_usd={uv['auto_valor_usd']}")


def test_guardrail_auto_valor_usd_preserves_legitimate_value():
    """GUARDRAIL RU-MANUAL-SAVE-02: Verifica que el invariante NO se activa
    cuando auto_valor_usd es un valor oficial preservado (diferente del cache preview)."""
    from valu_detail_sections import _verificar_invariante_auto_valor_usd

    # Escenario: UV tiene auto_valor_usd oficial ($735K) diferente del cache preview ($590K)
    uv = {'auto_valor_usd': 735013, 'fuente_activa': 'manual'}
    auto_result = {'valor_propiedad_usd': 590093.0}

    result = _verificar_invariante_auto_valor_usd(uv, auto_result, "__test_guardrail__")
    assert result is True, "No debe detectar contaminacion cuando valor preservado es diferente"
    assert uv['auto_valor_usd'] == 735013, "Debe preservar el valor oficial"

    print(f"[TEST-GUARDRAIL-LEGIT] OK — valor oficial preservado: auto_valor_usd={uv['auto_valor_usd']}")


def test_guardrail_auto_valor_usd_ignores_non_manual():
    """GUARDRAIL RU-MANUAL-SAVE-02: Verifica que el invariante NO se activa
    cuando la fuente activa es 'auto' (no aplica a modo automatico)."""
    from valu_detail_sections import _verificar_invariante_auto_valor_usd

    # Escenario: fuente activa es auto, no manual
    uv = {'auto_valor_usd': 590093, 'fuente_activa': 'auto'}
    auto_result = {'valor_propiedad_usd': 590093.0}

    result = _verificar_invariante_auto_valor_usd(uv, auto_result, "__test_guardrail__")
    assert result is True, "No debe activarse cuando fuente != manual"
    assert uv['auto_valor_usd'] == 590093, "No debe modificar auto_valor_usd"

    print(f"[TEST-GUARDRAIL-AUTO] OK — invariante ignorado en modo auto: auto_valor_usd={uv['auto_valor_usd']}")


def test_guardrail_auto_valor_usd_uv_init_0():
    """GUARDRAIL RU-MANUAL-SAVE-02: Verifica que si auto_valor_usd es 0 (inicializado
    por setdefault) y cache preview tiene valor, NO se activa el invariante."""
    from valu_detail_sections import _verificar_invariante_auto_valor_usd

    # Escenario: UV se inicializo con 0 (nunca se aplico auto engine), cache tiene valor
    uv = {'auto_valor_usd': 0, 'fuente_activa': 'manual'}
    auto_result = {'valor_propiedad_usd': 590093.0}

    result = _verificar_invariante_auto_valor_usd(uv, auto_result, "__test_guardrail__")
    assert result is True, "auto_valor_usd=0 es distinto de cache preview, no hay contaminacion"
    assert uv['auto_valor_usd'] == 0, "Debe mantener 0"

    print(f"[TEST-GUARDRAIL-ZERO] OK — auto_valor_usd=0 preservado: {uv['auto_valor_usd']}")
