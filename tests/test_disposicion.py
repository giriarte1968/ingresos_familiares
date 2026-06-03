"""
Tests para factor_disposicion (TAREA-028).
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.mercado_inmobiliario import calcular_factores


def test_sin_disposicion_retorna_neutro():
    """Propiedad legacy sin campo disposicion debe tener delta 0."""
    f = calcular_factores({'anio_construccion': 1990})
    assert f['delta_disposicion'] == 0.0
    assert f['factor_disposicion'] == 1.0


def test_disposicion_frente_neutro():
    """frente debe ser neutro (delta 0)."""
    f = calcular_factores({'anio_construccion': 1990, 'disposicion': 'frente'})
    assert f['delta_disposicion'] == 0.0


def test_disposicion_lateral_neutro():
    """lateral debe ser neutro (delta 0)."""
    f = calcular_factores({'anio_construccion': 1990, 'disposicion': 'lateral'})
    assert f['delta_disposicion'] == 0.0


def test_disposicion_pasante_neutro():
    """pasante debe ser neutro (ya cubierto por ventilacion cruzada)."""
    f = calcular_factores({'anio_construccion': 1990, 'disposicion': 'pasante'})
    assert f['delta_disposicion'] == 0.0


def test_disposicion_contrafrente_penaliza():
    """contrafrente debe penalizar -0.5%."""
    f = calcular_factores({'anio_construccion': 1990, 'disposicion': 'contrafrente'})
    assert f['delta_disposicion'] == -0.005


def test_disposicion_interna_penaliza():
    """interna debe penalizar -1.0%."""
    f = calcular_factores({'anio_construccion': 1990, 'disposicion': 'interna'})
    assert f['delta_disposicion'] == -0.01


def test_disposicion_interna_con_vista_interna_reduce_castigo():
    """interna + vista interna debe reducir castigo a -0.5% (evitar doble)."""
    f = calcular_factores({
        'anio_construccion': 1990,
        'disposicion': 'interna',
        'vista': 'interna'
    })
    assert f['delta_disposicion'] == -0.005


def test_disposicion_interna_con_vista_pulmon_reduce_castigo():
    """interna + vista pulmon debe reducir castigo a -0.5%."""
    f = calcular_factores({
        'anio_construccion': 1990,
        'disposicion': 'interna',
        'vista': 'pulmon'
    })
    assert f['delta_disposicion'] == -0.005


def test_disposicion_contrafrente_con_vista_interna_no_afecta():
    """contrafrente + vista interna: contrafrente mantiene -0.5% (no se reduce, no está en penalizaciones de vista)."""
    f = calcular_factores({
        'anio_construccion': 1990,
        'disposicion': 'contrafrente',
        'vista': 'interna'
    })
    # contrafrente -0.005, vista interna no está en penalizaciones de disposicion
    assert f['delta_disposicion'] == -0.005
