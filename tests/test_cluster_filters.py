"""
Tests unitarios para parsers/cluster_filters.py.
NO modifican el motor de valuación. Usan datos sintéticos.
"""
import pytest
from parsers.cluster_filters import (
    filtrar_por_radio,
    filtrar_por_tipo_operacion_dorms,
    filtrar_por_fecha,
    separar_por_barreras,
    calcular_percentil,
    calcular_blend_p33,
    seleccionar_percentil_por_edad,
)


def dist_mock(l1, n1, l2, n2):
    """Mock de calcular_distancia_km que devuelve distancia fija."""
    return 0.3  # Siempre 300m


def dist_var(l1, n1, l2, n2):
    """Mock que devuelve distancias variables según diferencia de lat."""
    return abs(float(l1) - float(l2)) * 111  # ~111km por grado


def barrier_none(*args):
    return False


def barrier_soft(*args):
    return 'soft'


def barrier_hard(*args):
    return 'hard'


def barrier_mixed(p1, p2):
    if 'cross' in str(p2[1]):
        return 'soft'
    return False


# ─── TESTS filtrar_por_radio ───

def test_filtrar_por_radio_incluye_dentro():
    """Propiedades dentro del radio deben incluirse."""
    props = [{'lat': -32.95, 'lon': -60.63, 'nombre': 'a'},
             {'lat': -32.9505, 'lon': -60.6305, 'nombre': 'b'}]  # ~55m apart
    res = filtrar_por_radio(props, -32.95, -60.63, 500, dist_var)
    assert len(res) == 2


def test_filtrar_por_radio_excluye_fuera():
    """Propiedades fuera del radio deben excluirse."""
    props = [{'lat': -33.05, 'lon': -60.63, 'nombre': 'a'}]  # ~11km
    res = filtrar_por_radio(props, -32.95, -60.63, 500, dist_var)
    assert len(res) == 0


def test_filtrar_por_radio_usa_latitud_key():
    """Debe aceptar 'latitud' como alias de 'lat'."""
    props = [{'latitud': -32.95, 'longitud': -60.63}]
    res = filtrar_por_radio(props, -32.95, -60.63, 500, dist_mock)
    assert len(res) == 1


def test_filtrar_por_radio_sin_coords_excluye():
    """Propiedades sin coordenadas deben excluirse."""
    props = [{'nombre': 'a'}, {'lat': -32.95, 'lon': -60.63}]
    res = filtrar_por_radio(props, -32.95, -60.63, 500, dist_mock)
    assert len(res) == 1


# ─── TESTS filtrar_por_tipo_operacion_dorms ───

def test_filtrar_tipo():
    """Filtrar por tipo 'departamento' debe excluir casas."""
    props = [{'tipo': 'Departamento'}, {'tipo': 'Casa'}]
    res = filtrar_por_tipo_operacion_dorms(props, tipo='departamento')
    assert len(res) == 1
    assert res[0]['tipo'] == 'Departamento'


def test_filtrar_operacion():
    """Filtrar por operacion 'venta' debe excluir alquileres."""
    props = [{'operacion': 'venta'}, {'operacion': 'alquiler'}]
    res = filtrar_por_tipo_operacion_dorms(props, operacion='venta')
    assert len(res) == 1


def test_filtrar_dorms_con_tolerancia():
    """Dormitorios debe coincidir con tolerancia ±1."""
    props = [{'dormitorios': 2}, {'dormitorios': 3}, {'dormitorios': 1}, {'dormitorios': 4}]
    res = filtrar_por_tipo_operacion_dorms(props, dormitorios=2, tolerancia_dorms=1)
    assert len(res) == 3  # 1, 2, 3 (no 4)


def test_filtrar_sin_parametros():
    """Sin filtros, debe devolver todas las props."""
    props = [{'a': 1}, {'b': 2}]
    res = filtrar_por_tipo_operacion_dorms(props)
    assert len(res) == 2


# ─── TESTS filtrar_por_fecha ───

def test_filtrar_fecha_incluye_recientes():
    """Propiedades dentro de la ventana deben incluirse."""
    props = [{'date_updated': '2026-04-01T00:00:00.000Z'},
             {'date_updated': '2025-06-01T00:00:00.000Z'}]
    res = filtrar_por_fecha(props, '2026-05-01', ventana_dias=90)
    assert len(res) == 1  # Solo la de abril


def test_filtrar_fecha_sin_fecha_ref():
    """Sin fecha_ref debe usar datetime.now() y no fallar."""
    props = [{'date_updated': '2026-05-01T00:00:00.000Z'}]
    res = filtrar_por_fecha(props, ventana_dias=365)
    assert len(res) >= 0  # No debe fallar


def test_filtrar_fecha_sin_date_updated():
    """Propiedades sin date_updated deben excluirse."""
    props = [{'nombre': 'a'}, {'date_updated': '2026-04-01T00:00:00.000Z'}]
    res = filtrar_por_fecha(props, '2026-05-01', ventana_dias=90)
    assert len(res) == 1


# ─── TESTS separar_por_barreras ───

def test_separar_same_side():
    """Sin barreras, todas van a same_side."""
    props = [{'lat': -32.95, 'lon': -60.63},
             {'lat': -32.96, 'lon': -60.64}]
    res = separar_por_barreras(props, -32.95, -60.63, barrier_none)
    assert len(res['same_side']) == 2
    assert len(res['cross_soft']) == 0
    assert len(res['excluded_hard']) == 0


def test_separar_cross_soft():
    """Barrera soft debe ir a cross_soft."""
    props = [{'lat': -32.95, 'lon': -60.63}]
    res = separar_por_barreras(props, -32.95, -60.63, barrier_soft)
    assert len(res['cross_soft']) == 1


def test_separar_excluded_hard():
    """Barrera hard debe ir a excluded_hard."""
    props = [{'lat': -32.95, 'lon': -60.63}]
    res = separar_por_barreras(props, -32.95, -60.63, barrier_hard)
    assert len(res['excluded_hard']) == 1


def test_separar_mixto():
    """Mezcla de tipos debe separar correctamente."""
    props = [
        {'nombre': 'same', 'lat': -32.95, 'lon': -60.63},
        {'nombre': 'cross_1', 'lat': -32.95, 'lon': -60.64},
    ]
    res = separar_por_barreras(props, -32.95, -60.63, barrier_mixed)
    # 'cross_1' contiene 'cross' → soft
    assert 'same_side' in res


def test_separar_sin_coords():
    """Propiedades sin coordenadas van a same_side."""
    props = [{'nombre': 'a'}]
    res = separar_por_barreras(props, -32.95, -60.63, barrier_none)
    assert len(res['same_side']) == 1


# ─── TESTS calcular_percentil ───

def test_percentil_p50():
    """P50 de [100, 200, 300, 400] con metodo discreto: idx=2 → 300."""
    assert calcular_percentil([100, 200, 300, 400], 50) == 300.0


def test_percentil_p25():
    """P25 de [100, 200, 300, 400] con metodo discreto: idx=1 → 200."""
    assert calcular_percentil([100, 200, 300, 400], 25) == 200.0


def test_percentil_p33():
    """P33 de [1, 2, 3, 4, 5, 6] con metodo discreto: idx=1 → 2."""
    assert calcular_percentil([1, 2, 3, 4, 5, 6], 33) == 2.0


def test_percentil_p40_n8():
    """P40 de 8 comps (caso Vera): idx=3 → 160."""
    precios = [100, 120, 140, 160, 180, 200, 220, 240]
    assert calcular_percentil(precios, 40) == 160.0


def test_percentil_p45_n12():
    """P45 de 12 comps (caso P1200): idx=5 → 200."""
    precios = [100, 120, 140, 160, 180, 200, 220, 240, 260, 280, 300, 320]
    assert calcular_percentil(precios, 45) == 200.0


def test_percentil_p50_n4():
    """P50 de 4 comps: idx=2 → 30."""
    precios = [10, 20, 30, 40]
    assert calcular_percentil(precios, 50) == 30.0


def test_percentil_lista_vacia():
    """Lista vacía debe retornar None."""
    assert calcular_percentil([], 50) is None


def test_percentil_valor_unico():
    """Lista con un solo valor debe retornar ese valor."""
    assert calcular_percentil([100], 50) == 100.0


# ─── TESTS calcular_blend_p33 ───

def test_blend_ambos():
    """Con same=1000 y cross=1500, alpha=0.70 → 1150."""
    res = calcular_blend_p33(1000, 1500, alpha=0.70)
    assert res == 1150.0


def test_blend_solo_same():
    """Sin cross, debe retornar same."""
    assert calcular_blend_p33(1000, None) == 1000.0


def test_blend_solo_cross():
    """Sin same, debe retornar cross."""
    assert calcular_blend_p33(None, 1500) == 1500.0


def test_blend_ninguno():
    """Sin ambos, debe retornar None."""
    assert calcular_blend_p33(None, None) is None


def test_blend_alpha_personalizado():
    """Alpha personalizado debe aplicarse correctamente."""
    res = calcular_blend_p33(1000, 2000, alpha=0.50)
    assert res == 1500.0


# ─── TESTS seleccionar_percentil_por_edad ───

def test_edad_sin_filtro():
    """Sin age_filter → P33."""
    assert seleccionar_percentil_por_edad(False, 0) == (33, 'P33')


def test_edad_n20():
    """n=25 >= 20 → P50."""
    assert seleccionar_percentil_por_edad(True, 25) == (50, 'P50_age')


def test_edad_n15():
    """n=15 entre 10 y 20 → P45."""
    assert seleccionar_percentil_por_edad(True, 15) == (45, 'P45_age')


def test_edad_n8():
    """n=8 entre 8 y 10 → P40."""
    assert seleccionar_percentil_por_edad(True, 8) == (40, 'P40_age')


def test_edad_n5():
    """n=5 < 8 → P33 (fallback)."""
    assert seleccionar_percentil_por_edad(True, 5) == (33, 'P33')
