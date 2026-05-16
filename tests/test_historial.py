import os
import json
import tempfile
import pytest
from unittest.mock import patch
from parsers.valuacion_historial import (
    registrar_valuacion, cargar_historial,
    obtener_ultima_valuacion, comparar_valuaciones,
    _generar_id_evento
)

@pytest.fixture
def tmp_historial(tmp_path):
    """Usar archivo temporal para tests."""
    historial_path = str(tmp_path / "test_historial.jsonl")
    # Patch the path in the module
    with patch('parsers.valuacion_historial.HISTORIAL_PATH', historial_path):
        yield historial_path

def test_registrar_es_append_only(tmp_historial):
    """Dos registros se acumulan, no se sobrescriben."""
    prop = {'nombre': 'Test', 'zona': 'Martin', 'm2_cubiertos': 40}
    resultado = {'valor_propiedad_usd': 70000, 'dolar_binance': 1480}

    registrar_valuacion('Test', prop, resultado, 'primera_vez')
    registrar_valuacion('Test', prop, {**resultado, 'valor_propiedad_usd': 75000}, 'scraping')

    historial = cargar_historial('Test')
    assert len(historial) == 2

def test_historial_inmutable(tmp_historial):
    """Registrar no modifica entradas anteriores."""
    prop = {'nombre': 'Test'}
    res1 = {'valor_propiedad_usd': 70000, 'dolar_binance': 1480}
    res2 = {'valor_propiedad_usd': 80000, 'dolar_binance': 1500}

    registrar_valuacion('Test', prop, res1, 'primera_vez')
    registrar_valuacion('Test', prop, res2, 'manual')

    historial = cargar_historial('Test')
    valores = [r['resultado']['valor_venta'] for r in historial]
    assert 70000 in valores
    assert 80000 in valores

def test_filtrar_por_propiedad(tmp_historial):
    """Filtrar por propiedad devuelve solo sus registros."""
    registrar_valuacion('Mabel', {}, {'valor_propiedad_usd': 77000, 'dolar_binance': 1480}, 'test')
    registrar_valuacion('P1200', {}, {'valor_propiedad_usd': 137000, 'dolar_binance': 1480}, 'test')
    registrar_valuacion('Mabel', {}, {'valor_propiedad_usd': 78000, 'dolar_binance': 1480}, 'test')

    solo_mabel = cargar_historial('Mabel')
    assert len(solo_mabel) == 2
    assert all(r['propiedad'] == 'Mabel' for r in solo_mabel)

def test_ordenado_por_mas_reciente(tmp_historial):
    """El historial debe venir del más reciente al más antiguo."""
    import time
    registrar_valuacion('Test', {}, {'valor_propiedad_usd': 70000, 'dolar_binance': 1480}, 'a')
    time.sleep(0.01)
    registrar_valuacion('Test', {}, {'valor_propiedad_usd': 80000, 'dolar_binance': 1480}, 'b')

    historial = cargar_historial('Test')
    assert historial[0]['resultado']['valor_venta'] == 80000

def test_obtener_ultima_valuacion(tmp_historial):
    """obtener_ultima_valuacion retorna solo el registro más reciente."""
    import time
    registrar_valuacion('Test', {}, {'valor_propiedad_usd': 70000, 'dolar_binance': 1480}, 'primero')
    time.sleep(0.01)
    registrar_valuacion('Test', {}, {'valor_propiedad_usd': 80000, 'dolar_binance': 1480}, 'segundo')

    ultima = obtener_ultima_valuacion('Test')
    assert ultima['resultado']['valor_venta'] == 80000

def test_sin_historial_devuelve_lista_vacia(tmp_historial):
    """Si no hay historial, devuelve lista vacía sin error."""
    with patch('parsers.valuacion_historial.HISTORIAL_PATH', tmp_historial + '_noexiste'):
        historial = cargar_historial('NoExiste')
        assert historial == []

def test_comparar_dos_valuaciones(tmp_historial):
    """comparar_valuaciones detecta diferencias correctamente."""
    prop = {'nombre': 'Test'}
    registrar_valuacion('Test', prop,
        {'valor_propiedad_usd': 70000, 'cap_rate': 0.05, 'dolar_binance': 1480, 'm2_base_venta': 1500}, 'primera')
    registrar_valuacion('Test', prop,
        {'valor_propiedad_usd': 77000, 'cap_rate': 0.055, 'dolar_binance': 1480, 'm2_base_venta': 1500}, 'segunda')

    hist = cargar_historial('Test')
    # Use IDs from the created records
    diff = comparar_valuaciones('Test', hist[0]['id'], hist[1]['id'])
    assert 'valor_venta' in diff.get('diferencias', {})
