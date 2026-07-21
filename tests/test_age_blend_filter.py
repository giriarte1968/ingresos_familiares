"""Tests para TAREA-138: filtro ±10 años fijo para comparables."""

import pytest
from parsers.mercado_inmobiliario import _filtrar_por_ventana_edad


ANIO_ACTUAL = 2026


def test_filtrar_por_ventana_edad_12_comps_en_rango():
    """12 comparables con ant 14-34, sujeto ant=24 → filtro activado, 12 comps."""
    pool = [
        {'antiquity': 14, 'valor_m2': 1000},   # 2012
        {'antiquity': 15, 'valor_m2': 1100},   # 2011
        {'antiquity': 18, 'valor_m2': 1200},   # 2008
        {'antiquity': 20, 'valor_m2': 1300},   # 2006
        {'antiquity': 22, 'valor_m2': 1400},   # 2004
        {'antiquity': 24, 'valor_m2': 1500},   # 2002
        {'antiquity': 26, 'valor_m2': 1600},   # 2000
        {'antiquity': 28, 'valor_m2': 1700},   # 1998
        {'antiquity': 30, 'valor_m2': 1800},   # 1996
        {'antiquity': 32, 'valor_m2': 1900},   # 1994
        {'antiquity': 34, 'valor_m2': 2000},   # 1992
        {'antiquity': 16, 'valor_m2': 2100},   # 2010
    ]

    pool_final, applied, n_age, a_min, a_max = _filtrar_por_ventana_edad(
        pool, anio_sujeto=2002, ventana=10
    )

    assert applied is True
    assert n_age == 12
    assert a_min == 1992
    assert a_max == 2012


def test_filtrar_por_ventana_edad_8_en_rango():
    """8 comps en rango → filtro ACTIVA (min_con_anio=1,只要有≥1 comp en rango)."""
    pool = [
        {'antiquity': 14, 'valor_m2': 1000},   # 2012
        {'antiquity': 15, 'valor_m2': 1100},   # 2011
        {'antiquity': 18, 'valor_m2': 1200},   # 2008
        {'antiquity': 20, 'valor_m2': 1300},   # 2006
        {'antiquity': 22, 'valor_m2': 1400},   # 2004
        {'antiquity': 24, 'valor_m2': 1500},   # 2002
        {'antiquity': 30, 'valor_m2': 1800},   # 1996
        {'antiquity': 34, 'valor_m2': 2000},   # 1992
        {'antiquity': 50, 'valor_m2': 2500},   # 1976 (fuera)
        {'antiquity': 55, 'valor_m2': 2600},   # 1971 (fuera)
    ]

    pool_final, applied, n_age, a_min, a_max = _filtrar_por_ventana_edad(
        pool, anio_sujeto=2002, ventana=10
    )

    assert applied is True
    assert n_age == 8  # los 8 en rango 1992-2012


def test_filtrar_por_ventana_edad_sin_anio_sujeto():
    """Sin anio_sujeto, no aplica filtro."""
    pool = [{'antiquity': 10, 'valor_m2': 1000}]
    pool_final, applied, n_age, _, _ = _filtrar_por_ventana_edad(pool, anio_sujeto=None)
    assert applied is False
    assert n_age == 0


def test_filtrar_por_ventana_edad_usa_antiquity():
    """12 comps con antigüidades variadas, sujeto=2006 → verifica que usa antiquity."""
    pool = [
        {'antiquity': 10, 'valor_m2': 1000},   # 2016
        {'antiquity': 12, 'valor_m2': 1100},   # 2014
        {'antiquity': 14, 'valor_m2': 1200},   # 2012
        {'antiquity': 16, 'valor_m2': 1300},   # 2010
        {'antiquity': 18, 'valor_m2': 1400},   # 2008
        {'antiquity': 20, 'valor_m2': 1500},   # 2006
        {'antiquity': 22, 'valor_m2': 1600},   # 2004
        {'antiquity': 24, 'valor_m2': 1700},   # 2002
        {'antiquity': 26, 'valor_m2': 1800},   # 2000
        {'antiquity': 28, 'valor_m2': 1900},   # 1998
        {'antiquity': 30, 'valor_m2': 2000},   # 1996
        {'antiquity': 32, 'valor_m2': 2100},   # 1994 (OUTSIDE: 1994 < 1996)
    ]

    # anio_sujeto=2006, ventana ±10: [1996, 2016]
    pool_final, applied, n_age, a_min, a_max = _filtrar_por_ventana_edad(
        pool, anio_sujeto=2006, ventana=10
    )

    assert applied is True
    assert n_age == 11  # ant 32 (1994) queda fuera


def test_filtrar_por_ventana_edad_antiquity_zero():
    """ant=0 (año actual) se incluye correctamente en la ventana."""
    pool = [
        {'antiquity': 0, 'valor_m2': 3000},    # 2026
        {'antiquity': 2, 'valor_m2': 2500},    # 2024
        {'antiquity': 4, 'valor_m2': 2200},    # 2022
        {'antiquity': 6, 'valor_m2': 2000},    # 2020
        {'antiquity': 8, 'valor_m2': 1800},    # 2018
        {'antiquity': 10, 'valor_m2': 1600},   # 2016
        {'antiquity': 12, 'valor_m2': 1500},   # 2014
        {'antiquity': 14, 'valor_m2': 1400},   # 2012
        {'antiquity': 15, 'valor_m2': 1350},   # 2011
        {'antiquity': 15, 'valor_m2': 1350},   # 2011 (otra)
        {'antiquity': 18, 'valor_m2': 1200},   # 2008 (fuera: < 2011)
        {'antiquity': 20, 'valor_m2': 1100},   # 2006 (fuera)
    ]

    # anio_sujeto=2021, ventana ±10: [2011, 2031]
    # ant 0→2026✓, 2→2024✓, 4→2022✓, 6→2020✓, 8→2018✓, 10→2016✓, 12→2014✓, 14→2012✓, 15→2011✓, 15→2011✓
    pool_final, applied, n_age, a_min, a_max = _filtrar_por_ventana_edad(
        pool, anio_sujeto=2021, ventana=10
    )

    assert applied is True
    assert n_age == 10  # ant 0,2,4,6,8,10,12,14,15,15


def test_filtrar_por_ventana_edad_sin_antiquity():
    """Sin antiquity válido → no aplica filtro, retorna pool completo."""
    pool = [
        {'valor_m2': 1000},
        {'valor_m2': 1100},
        {'valor_m2': 1200},
    ]

    pool_final, applied, n_age, a_min, a_max = _filtrar_por_ventana_edad(
        pool, anio_sujeto=2016, ventana=10
    )

    assert applied is False
    assert len(pool_final) == 3


def test_filtrar_por_ventana_edad_pool_vacio():
    """Pool vacío → no aplica filtro."""
    pool_final, applied, n_age, _, _ = _filtrar_por_ventana_edad([], anio_sujeto=2010)
    assert applied is False
    assert n_age == 0


def test_filtrar_por_ventana_edad_un_solo_comp_en_rango():
    """2 comps en rango → fallback (min_con_anio=3, necesita≥3 para activar)."""
    pool = [
        {'antiquity': 5, 'valor_m2': 1500},    # 2021 (dentro de 2011-2031)
        {'antiquity': 8, 'valor_m2': 1400},    # 2018 (dentro)
        {'antiquity': 50, 'valor_m2': 1000},   # 1976 (fuera)
        {'antiquity': 55, 'valor_m2': 900},    # 1971 (fuera)
    ]

    pool_final, applied, n_age, a_min, a_max = _filtrar_por_ventana_edad(
        pool, anio_sujeto=2021, ventana=10
    )

    # 2 en rango < 3 → filtro SIEMPRE retorna pool filtrado (sin fallback)
    assert applied is True
    assert n_age == 2  # solo los 2 en rango


def test_filtrar_por_ventana_edad_tres_comps_en_rango():
    """3 comps en rango → filtro ACTIVA (min_con_anio=3)."""
    pool = [
        {'antiquity': 5, 'valor_m2': 1500},    # 2021
        {'antiquity': 8, 'valor_m2': 1400},    # 2018
        {'antiquity': 10, 'valor_m2': 1300},   # 2016
        {'antiquity': 50, 'valor_m2': 1000},   # 1976 (fuera)
        {'antiquity': 55, 'valor_m2': 900},    # 1971 (fuera)
    ]

    pool_final, applied, n_age, a_min, a_max = _filtrar_por_ventana_edad(
        pool, anio_sujeto=2021, ventana=10
    )

    assert applied is True
    assert n_age == 3  # ant 5,8,10
