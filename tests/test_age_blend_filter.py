"""Tests para TAREA-009: conectar P33_age_blend para 5-7 comparables."""


def test_filtrar_por_ventana_edad_activa_blend_con_6_comparables():
    """6 comparables dentro de +/-30 activan age_filter y devuelven P33_age_blend."""
    from parsers.mercado_inmobiliario import _filtrar_por_ventana_edad
    from parsers.cluster_filters import seleccionar_percentil_por_edad

    pool = [
        {'anio_estimado': 2011, 'valor_m2': 1000},
        {'anio_estimado': 1981, 'valor_m2': 1100},
        {'anio_estimado': 1981, 'valor_m2': 1200},
        {'anio_estimado': 1992, 'valor_m2': 1300},
        {'anio_estimado': 2006, 'valor_m2': 1400},
        {'anio_estimado': 2022, 'valor_m2': 1500},
        {'anio_estimado': 1975, 'valor_m2': 2000},  # fuera +/-30
        {'anio_estimado': 1968, 'valor_m2': 2100},  # fuera +/-30
    ]

    pool_final, applied, n_age, a_min, a_max = _filtrar_por_ventana_edad(
        pool, anio_sujeto=2010, ventana=15
    )

    assert applied is True
    assert n_age == 6
    assert a_min == 1980
    assert a_max == 2040

    years = {p['anio_estimado'] for p in pool_final}
    assert 1975 not in years
    assert 1968 not in years

    percentil, label = seleccionar_percentil_por_edad(applied, n_age)
    assert percentil == 33
    assert label == 'P33_age_blend'


def test_filtrar_por_ventana_edad_5_en_ventana_15():
    """5 comparables dentro de +/-15 activan directamente."""
    from parsers.mercado_inmobiliario import _filtrar_por_ventana_edad
    from parsers.cluster_filters import seleccionar_percentil_por_edad

    pool = [
        {'anio_estimado': 2005, 'valor_m2': 1000},
        {'anio_estimado': 2008, 'valor_m2': 1100},
        {'anio_estimado': 2012, 'valor_m2': 1200},
        {'anio_estimado': 2015, 'valor_m2': 1300},
        {'anio_estimado': 2018, 'valor_m2': 1400},
        {'anio_estimado': 1990, 'valor_m2': 2000},
    ]

    pool_final, applied, n_age, a_min, a_max = _filtrar_por_ventana_edad(
        pool, anio_sujeto=2010, ventana=15
    )

    assert applied is True
    assert n_age == 5
    assert a_min == 1995
    assert a_max == 2025

    percentil, label = seleccionar_percentil_por_edad(applied, n_age)
    assert percentil == 33
    assert label == 'P33_age_blend'


def test_filtrar_por_ventana_edad_sin_anio_sujeto():
    """Sin anio_sujeto, no aplica filtro."""
    from parsers.mercado_inmobiliario import _filtrar_por_ventana_edad

    pool = [{'anio_estimado': 2010, 'valor_m2': 1000}]
    pool_final, applied, n_age, _, _ = _filtrar_por_ventana_edad(pool, anio_sujeto=None)
    assert applied is False
    assert n_age == 0


def test_filtrar_por_ventana_edad_menos_de_5_total():
    """Menos de 5 comparables con anio -> no activa filtro, n_age = len(pool_con_anio)."""
    from parsers.mercado_inmobiliario import _filtrar_por_ventana_edad

    pool = [{'anio_estimado': 2010, 'valor_m2': 1000}]
    pool_final, applied, n_age, _, _ = _filtrar_por_ventana_edad(pool, anio_sujeto=2010)
    assert applied is False
    assert n_age == 1


def test_filtrar_por_ventana_edad_5_total_4_en_30_sin_activar():
    """5 con anio, solo 4 en +/-30 -> no activa filtro, n_age = 5."""
    from parsers.mercado_inmobiliario import _filtrar_por_ventana_edad

    pool = [
        {'anio_estimado': 2008, 'valor_m2': 1000},
        {'anio_estimado': 2009, 'valor_m2': 1100},
        {'anio_estimado': 2011, 'valor_m2': 1200},
        {'anio_estimado': 2012, 'valor_m2': 1300},
        {'anio_estimado': 1970, 'valor_m2': 2000},  # fuera de +/-30
    ]
    pool_final, applied, n_age, _, _ = _filtrar_por_ventana_edad(pool, anio_sujeto=2010)
    assert applied is False
    assert n_age == 5
