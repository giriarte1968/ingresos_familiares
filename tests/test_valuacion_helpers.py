"""
Tests unitarios para parsers/valuacion_helpers.py.
NO modifican el motor de valuación. Usan datos sintéticos.
"""
import pytest
from parsers.valuacion_helpers import (
    calcular_rango_venta,
    procesar_alquiler,
    ensamblar_metadata_resolucion,
)


# ─── TESTS calcular_rango_venta ───

def test_rango_venta_basico():
    """Valor de entrada -> rango simétrico centrado en valor_estimado."""
    res = calcular_rango_venta(
        valor_estimado=100000, p25_cluster=1200,
        p50_cluster=1500, p75_cluster=1800, n_muestras=30
    )
    r = res['rango_venta']
    assert r['min'] <= r['mid'] <= r['max']
    assert r['mid'] == 100000
    assert r['spread_pct'] > 0


def test_rango_venta_margen_error():
    """Con 30 muestras, IQR=0.40, floor=0.06 cap=0.10 -> margen debe estar entre 0.06 y 0.10."""
    res = calcular_rango_venta(
        valor_estimado=100000, p25_cluster=1200,
        p50_cluster=1500, p75_cluster=1800, n_muestras=30
    )
    r = res['rango_venta']
    # IQR = (1800-1200)/1500 = 0.40, half = 0.20, raw = 0.10
    # n >= 25 -> floor=0.06, cap=0.10, so margen = 0.10
    assert 0.06 <= r['margen_error'] <= 0.12
    assert r['min'] == 90000
    assert r['max'] == 110000


def test_rango_venta_confidence_baja():
    """Confianza BAJA debe aumentar cap a 0.20."""
    res = calcular_rango_venta(
        valor_estimado=100000, p25_cluster=1200,
        p50_cluster=1500, p75_cluster=1800, n_muestras=5,
        confidence='BAJA'
    )
    r = res['rango_venta']
    # n < 10 -> floor=0.10, cap=0.18, BAJA -> cap = max(0.18, 0.20) = 0.20
    # raw_margin = 0.10 -> margen = max(0.10, min(0.10, 0.20)) = 0.10
    assert 0.10 <= r['margen_error'] <= 0.21


def test_rango_venta_sin_dispersion():
    """Sin percentiles -> half_iqr_rel=0.0 -> margen usa floor."""
    res = calcular_rango_venta(
        valor_estimado=100000, p25_cluster=0,
        p50_cluster=0, p75_cluster=0, n_muestras=30
    )
    r = res['rango_venta']
    # raw_margin = 0, floor = 0.06, cap = 0.10 -> margen = 0.06
    assert r['margen_error'] == 0.06
    assert r['min'] == 94000
    assert r['max'] == 106000


def test_rango_venta_valor_cero():
    """Valor estimado 0 debe retornar dict vacío."""
    res = calcular_rango_venta(
        valor_estimado=0, p25_cluster=1200,
        p50_cluster=1500, p75_cluster=1800, n_muestras=30
    )
    r = res['rango_venta']
    assert r['min'] == 0
    assert r['mid'] == 0
    assert r['spread_pct'] == 0


def test_rango_venta_muestras_grandes():
    """Con 60+ muestras y radio <= 300 -> floor=0.05, cap=0.08."""
    res = calcular_rango_venta(
        valor_estimado=200000, p25_cluster=1200,
        p50_cluster=1500, p75_cluster=1800, n_muestras=60,
        radio=250, confidence='ALTA'
    )
    r = res['rango_venta']
    # raw_margin = 0.10, floor=0.05, cap=0.08 -> margen = min(0.10, 0.08) = 0.08
    assert 0.05 <= r['margen_error'] <= 0.08


# ─── TESTS procesar_alquiler ───

def test_alquiler_data_driven():
    """Con cap_info local, debe usar mercado_local."""
    cap_info = {'cap_rate': 0.05, 'cap_rate_min': 0.045, 'cap_rate_max': 0.055,
                'es_fallback': False, 'confianza': 'ALTA'}
    res = procesar_alquiler(
        valor_venta=100000, m2_equiv=50, m2_base_alquiler=12000,
        factores_alquiler=1.0, gap_alquiler=0.92, usdt_ars=1480,
        zona_txt='Centro', dorms=2,
        size_discount_params={'cap_info_local': cap_info}
    )
    assert res['metodo_alquiler'] == 'mercado_local'
    assert not res['es_fallback_alquiler']
    assert res['cap_rate'] == 0.05
    # $100k * 0.05 / 12 = $416.67 * 1480 = ~$616,667 ARS
    assert 600000 <= res['alquiler_estimado_ars'] <= 630000


def test_alquiler_fallback():
    """Sin cap_info, debe usar ROI zonal."""
    res = procesar_alquiler(
        valor_venta=100000, m2_equiv=50, m2_base_alquiler=12000,
        factores_alquiler=1.0, gap_alquiler=0.92, usdt_ars=1480,
        zona_txt='Centro', dorms=2,
    )
    assert res['metodo_alquiler'] == 'roi_zonal_fallback'
    assert res['es_fallback_alquiler']
    assert res['confianza_alquiler'] == 'BAJA'


def test_alquiler_con_size_discount():
    """Size discount debe aplicarse cuando m2 > 45."""
    def mock_size_discount(m2):
        return 0.80 if m2 > 80 else 1.0

    res = procesar_alquiler(
        valor_venta=100000, m2_equiv=90, m2_base_alquiler=12000,
        factores_alquiler=1.0, gap_alquiler=0.92, usdt_ars=1480,
        zona_txt='Centro', dorms=2,
        size_discount_fn=mock_size_discount,
    )
    assert res['size_discount'] > 0


def test_alquiler_roi_por_zona():
    """ROI debe variar según zona."""
    res_centro = procesar_alquiler(
        100000, 50, 12000, 1.0, 0.92, 1480, 'Centro', 2)
    res_oeste = procesar_alquiler(
        100000, 50, 12000, 1.0, 0.92, 1480, 'Oeste', 2)
    assert res_centro['cap_rate'] != res_oeste['cap_rate']
    assert res_centro['cap_rate'] < res_oeste['cap_rate']  # Centro más barato


# ─── TESTS ensamblar_metadata_resolucion ───

def test_metadata_confianza_alta():
    """Con n=20 y radio, debe dar ALTA."""
    meta = {'radio_usado': 300, 'percentil_usado': 'P50_age', 'zona_resolucion': 'Centro'}
    res = ensamblar_metadata_resolucion(meta, n_v=20, zona_txt='Centro')
    assert res['confidence'] == 'ALTA'
    assert res['resolution'] == 'GEO'


def test_metadata_confianza_baja():
    """Con n=5, debe dar BAJA."""
    meta = {'radio_usado': 300, 'percentil_usado': 'P33', 'zona_resolucion': 'Martin'}
    res = ensamblar_metadata_resolucion(meta, n_v=5, zona_txt='Martin')
    assert res['confidence'] == 'BAJA'


def test_metadata_sin_radio():
    """Sin radio_usado, debe dar ZONAL."""
    meta = {'percentil_usado': 'P33'}
    res = ensamblar_metadata_resolucion(meta, n_v=10, zona_txt='Centro')
    assert res['resolution'] == 'ZONAL'


def test_metadata_sin_datos():
    """Sin n_v ni radio, debe dar GLOBAL/BAJA."""
    meta = {}
    res = ensamblar_metadata_resolucion(meta, n_v=0, zona_txt='')
    assert res['resolution'] == 'GLOBAL'
    assert res['confidence'] == 'BAJA'


def test_metadata_campos_completos():
    """Debe incluir todos los campos requeridos."""
    meta = {'radio_usado': 500, 'percentil_usado': 'P45_age',
            'zona_resolucion': 'Sexta', 'n_comparables_total': 30,
            'n_con_anio_alta': 25, 'pct_con_anio': 83.3,
            'age_filter_applied': True, 'n_age_filtered': 16,
            'age_window': '+/-15 years', 'rango_anio_usado': '1987-2017',
            'comparables_reales': [], 'fuente_rango': 'cluster_v2'}
    res = ensamblar_metadata_resolucion(meta, n_v=16, zona_txt='Sexta')
    assert res['n_propiedades'] == 16
    assert res['percentil_usado'] == 'P45_age'
    assert res['n_con_anio_alta'] == 25
    assert res['age_filter_applied'] is True
    assert res['n_age_filtered'] == 16
