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

if __name__ == '__main__':
    pytest.main([__file__])
