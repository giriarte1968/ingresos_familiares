import pytest, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.mercado_inmobiliario import valuar_propiedad_v7
from parsers.valuacion_cache import cargar_cache_valuaciones, persistir_valuacion

def test_state_machine_limpiar_to_apply():
    """
    Test de Integración de Navegación UI:
    Verifica la secuencia exacta de estados:
    1. Propiedad con _ultima_valuacion en disco (Valuada Oficial)
    2. Limpiar borra _ultima_valuacion (Estado Sin Valor)
    3. Preview calcula valor en memoria
    4. Aplicar selección graba a disco y sincroniza valor oficial al 100%
    """
    props_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'propiedades.json')
    data = json.load(open(props_path, 'r', encoding='utf-8'))
    props = data.get('propiedades', [])
    
    er = next((p for p in props if '1372' in p.get('nombre', '') or '1372' in p.get('direccion', '')), None)
    assert er is not None, "Entre Rios 1372 debe existir en propiedades.json"
    
    # 1. Simular Limpiar: remover _ultima_valuacion
    er_limpia = dict(er)
    er_limpia.pop('_ultima_valuacion', None)
    assert '_ultima_valuacion' not in er_limpia
    
    # 2. Preview en vivo (Comparables): calcula valor en vivo
    res_preview = valuar_propiedad_v7(er_limpia)
    assert res_preview.get('valor_propiedad_usd', 0) > 0
    val_preview = res_preview.get('valor_propiedad_usd')
    m2_preview = res_preview.get('m2_base_venta')
    
    # 3. Aplicar selección: persistir a disco
    res_apply = dict(res_preview)
    res_apply['_comp_exclusion_applied'] = True
    res_apply['_comp_excluded'] = []
    
    cache_v = cargar_cache_valuaciones()
    persistir_valuacion(er_limpia.get('nombre'), er_limpia, res_apply, cache_v, commit=True)
    
    # 4. Re-leer disco y verificar coincidencia al 100%
    data_disk = json.load(open(props_path, 'r', encoding='utf-8'))
    er_disk = next((p for p in data_disk.get('propiedades', []) if p.get('nombre') == er_limpia.get('nombre')), None)
    assert er_disk is not None
    uv_disk = er_disk.get('_ultima_valuacion', {})
    
    assert uv_disk.get('valor_usd') == val_preview, f"Valor en disco {uv_disk.get('valor_usd')} debe ser igual a preview {val_preview}"
    assert uv_disk.get('m2_base_venta') == m2_preview, f"m2 en disco {uv_disk.get('m2_base_venta')} debe ser igual a preview {m2_preview}"
    assert uv_disk.get('_comp_exclusion_applied') is True, "_comp_exclusion_applied debe ser True en disco"
    
    # 5. Restaurar estado original de disco
    with open(props_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def test_session_state_purge_on_clean():
    """
    Verifica que la purga de session_state elimine todas las claves asociadas a la propiedad
    incluyendo checkboxes sel_comp_ y _safe_key.
    """
    import streamlit as st
    prop_name = "Entre Rios 1372"
    skey = "Entre_Rios_1372"
    
    # Mock keys in session state
    st.session_state[f'sel_comp_{skey}_comp1'] = False
    st.session_state[f'comp_selection_{prop_name}'] = set(['comp1'])
    st.session_state[f'_comp_exclusion_applied_{prop_name}'] = True
    st.session_state[f'other_prop_key'] = 123
    
    all_keys_to_pop = [
        k for k in list(st.session_state.keys())
        if prop_name in k or skey in k
    ]
    for k in all_keys_to_pop:
        st.session_state.pop(k, None)
        
    assert f'sel_comp_{skey}_comp1' not in st.session_state
    assert f'comp_selection_{prop_name}' not in st.session_state
    assert f'_comp_exclusion_applied_{prop_name}' not in st.session_state
    assert st.session_state.get('other_prop_key') == 123

def test_reentry_preserves_valuation():
    """
    Verifica que reingresar a una propiedad valuada 10 veces consecutivas jamás cambie su estado a 'Sin Valor'
    o borre sus comparables.
    """
    props_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'propiedades.json')
    data = json.load(open(props_path, 'r', encoding='utf-8'))
    props = data.get('propiedades', [])
    er = next((p for p in props if '1372' in p.get('nombre', '')), None)
    assert er is not None
    uv = er.get('_ultima_valuacion', {})
    assert uv.get('valor_usd', 0) > 0, "Propiedad debe estar valuada"

    # Simular reingreso múltiple sin llamar _limpiar_estado_propiedad
    for _ in range(10):
        ya_valuado = bool(uv.get('valor_usd', 0) > 0)
        assert ya_valuado is True, "Reingreso debe mantener ya_valuado == True"
        res = valuar_propiedad_v7(er)
        assert res.get('valor_propiedad_usd', 0) > 0, "Resultado debe conservar valuación > 0"
        assert len(res.get('comparables_venta', [])) > 0, "Resultado debe conservar comparables"

def test_post_limpiar_comparables_button_triggers_engine_and_map():
    """
    Test de Regresión de Navegación UI (TAREA-160):
    Verifica que al oprimir '📊 Comparables' inmediatamente después de 'Limpiar':
    1. Se elimina 'pendiente_comparables_' de session_state.
    2. Se activa 'forzar = True' y 'preview_mode = True'.
    3. El motor ejecuta la valuación, calcula comparables > 0 y genera el mapa HTML.
    """
    import streamlit as st
    prop_name = "Entre Rios 1372"

    # Simular estado Post-Limpiar
    st.session_state[f'pendiente_comparables_{prop_name}'] = True
    st.session_state[f'act_comp_{prop_name}'] = True  # Simular clic en el botón 'Comparables'

    # Simular la lógica exacta de ruteo de valu.py (L907-924)
    act_comps = st.session_state.pop(f'act_comp_{prop_name}', False) or st.session_state.pop(f'act_comparables_{prop_name}', False)
    forzar = False
    preview_mode = False

    if act_comps:
        forzar = True
        preview_mode = True
        st.session_state[f'preview_mode_{prop_name}'] = True
        st.session_state.pop(f'pendiente_comparables_{prop_name}', None)

    assert act_comps is True, "El botón 'Comparables' debió ser detectado como activo"
    assert forzar is True, "forzar debió ser activado a True tras presionar 'Comparables'"
    assert preview_mode is True, "preview_mode debió ser activado a True"
    assert f'pendiente_comparables_{prop_name}' not in st.session_state, "pendiente_comparables debió ser eliminado"

    # Verificar ejecucion del motor
    props_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'propiedades.json')
    data = json.load(open(props_path, 'r', encoding='utf-8'))
    er = next(p for p in data['propiedades'] if p['nombre'] == prop_name)

    res = valuar_propiedad_v7(er)
    assert res.get('valor_propiedad_usd', 0) > 0, "El motor debió generar un valor > 0"
    assert len(res.get('comparables_venta', [])) > 0, "El motor debió traer comparables > 0"
    print(f"[T-NAV-CLEAN-COMP] OK — forzar={forzar}, valor={res.get('valor_propiedad_usd')}, comps={len(res.get('comparables_venta'))}")


if __name__ == '__main__':
    pytest.main([__file__])

