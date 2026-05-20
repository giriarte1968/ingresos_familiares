"""
Tests para la recalibración de factores constructivos (TAREA).
Verifica:
- premium NO es estado de conservación, se normaliza a excelente+calidad premium
- factor_estado usa escala suavizada (sin premium)
- factor_calidad incluye premium
- ventilación usa simetría suavizada (0.95/1.05)
- el salto combinado no lleva la suma_cruda al clamp automáticamente
"""
import pytest
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.mercado_inmobiliario import calcular_factores


def test_premium_no_es_estado():
    """Si estado_detalle='premium', se normaliza a estado excelente y calidad pasa a premium."""
    f = calcular_factores({'estado_detalle': 'premium', 'calidad_edificio': 'media'})
    assert f['factor_estado'] == 1.05, f"Esperaba 1.05 (excelente), obtuvo {f['factor_estado']}"
    assert f['factor_calidad'] == 1.08, f"Esperaba 1.08 (premium), obtuvo {f['factor_calidad']}"


def test_premium_con_calidad_existente():
    """Si estado=premium pero calidad ya está definida, no sobreescribe calidad."""
    f = calcular_factores({'estado_detalle': 'premium', 'calidad_edificio': 'alta'})
    assert f['factor_estado'] == 1.05
    assert f['factor_calidad'] == 1.04, f"Calidad 'alta' debe seguir siendo 1.04, obtuvo {f['factor_calidad']}"


def test_estado_excelente_sin_premium():
    """estado=excelente, calidad=media → estado recibe solo el premio de excelente, calidad no se toca."""
    f = calcular_factores({'estado_detalle': 'excelente', 'calidad_edificio': 'media'})
    assert f['factor_estado'] == 1.05, f"Esperaba 1.05 (excelente), obtuvo {f['factor_estado']}"
    assert f['factor_calidad'] == 1.0, f"Esperaba 1.0 (media), obtuvo {f['factor_calidad']}"


def test_calidad_premium():
    """calidad=premium aplica 1.08 y no altera el estado."""
    f = calcular_factores({'estado_detalle': 'bueno', 'calidad_edificio': 'premium'})
    assert f['factor_estado'] == 1.0, f"Estado debe seguir siendo 1.0 (bueno), obtuvo {f['factor_estado']}"
    assert f['factor_calidad'] == 1.08, f"Calidad premium debe dar 1.08, obtuvo {f['factor_calidad']}"


def test_ventilacion_simple_cruzada_suavizada():
    """Ventilación simple=0.95, cruzada=1.05 → delta entre ambas = 0.10."""
    base = {'estado_detalle': 'bueno', 'calidad_edificio': 'media', 'anio_construccion': 2024,
            'piso': 5, 'total_pisos': 10, 'vista': 'frente', 'gas_ok': 'si',
            'tipo_balcon': 'ninguno', 'ubicacion_tipo': 'calle'}
    r_a = calcular_factores({**base, 'ventilacion': 'simple'})
    r_b = calcular_factores({**base, 'ventilacion': 'cruzada'})
    diff = r_b['suma_cruda_raw'] - r_a['suma_cruda_raw']
    assert abs(diff - 0.10) < 0.001, f"Delta simple→cruzada debería ser 0.10, es {diff:.4f}"


def test_no_doble_premio_premium_excelente():
    """
    El escenario antes problemático (bueno→premium, media→excelente, simple→cruzada)
    ya no debe llevar la suma_cruda al clamp de +0.40 automáticamente.
    """
    base = {
        'estado_detalle': 'bueno', 'calidad_edificio': 'media',
        'ventilacion': 'simple', 'anio_construccion': 2024,
        'vista': 'frente', 'gas_ok': 'si', 'piso': 5, 'total_pisos': 10,
        'tipo_balcon': 'ninguno', 'ubicacion_tipo': 'calle'
    }
    mejorado = {
        'estado_detalle': 'premium', 'calidad_edificio': 'excelente',
        'ventilacion': 'cruzada', 'anio_construccion': 2024,
        'vista': 'frente', 'gas_ok': 'si', 'piso': 5, 'total_pisos': 10,
        'tipo_balcon': 'ninguno', 'ubicacion_tipo': 'calle'
    }
    r_base = calcular_factores(base)
    r_mejor = calcular_factores(mejorado)
    # La suma_cruda del caso mejorado no debe alcanzar el clamp de +0.40
    assert r_mejor['suma_cruda_raw'] < 0.40, \
        f"suma_cruda_raw={r_mejor['suma_cruda_raw']:.3f} no debería alcanzar clamp 0.40"
    assert r_mejor['suma_cruda_raw'] > 0.10, \
        f"suma_cruda_raw={r_mejor['suma_cruda_raw']:.3f} debería ser positiva (mejora real)"
    # El factor estructural final debe estar muy por debajo del clamp 1.35
    assert r_mejor['f_estructural'] < 1.25, \
        f"f_estructural={r_mejor['f_estructural']:.3f} debería estar bajo 1.25"
    assert r_mejor['f_estructural'] > 1.0, \
        f"f_estructural={r_mejor['f_estructural']:.3f} debería ser >1.0 (mejora real)"


def test_factor_estado_nuevos_valores():
    """Verifica la nueva tabla de factor_estado."""
    casos = {
        'a_estrenar': 1.08, 'excelente': 1.05, 'muy_bueno': 1.03,
        'bueno': 1.0, 'regular': 0.92, 'malo': 0.85, 'a_refaccionar': 0.70
    }
    for estado, esperado in casos.items():
        f = calcular_factores({'estado_detalle': estado, 'calidad_edificio': 'media'})
        assert abs(f['factor_estado'] - esperado) < 0.001, \
            f"estado={estado}: esperado {esperado}, obtuvo {f['factor_estado']}"


def test_factor_calidad_nuevos_valores():
    """Verifica la nueva tabla de factor_calidad."""
    casos = {
        'premium': 1.08, 'excelente': 1.06, 'alta': 1.04,
        'media': 1.0, 'baja': 0.95, 'economica': 0.90
    }
    for calidad, esperado in casos.items():
        f = calcular_factores({'estado_detalle': 'bueno', 'calidad_edificio': calidad})
        assert abs(f['factor_calidad'] - esperado) < 0.001, \
            f"calidad={calidad}: esperado {esperado}, obtuvo {f['factor_calidad']}"


# ─── REGRESIÓN: RATIO DEL CASO PROBLEMÁTICO ───

def test_ratio_salto_mejorado_controlado():
    """
    Escenario A (baseline): bueno/media/simple
    Escenario B (mejorado): premium(c/e)/excelente/cruzada
    El ratio valor_mejorado/valor_base debe estar entre 1.15 y 1.25.
    """
    base = {
        'tipo_inmueble': 'departamento', 'zona': 'Martin',
        'm2': 48.5, 'm2_cubiertos': 41.0, 'm2_semicubiertos': 7.5,
        'dormitorios': 1, 'anio_construccion': 2000,
        'estado_detalle': 'bueno', 'calidad_edificio': 'media',
        'ventilacion': 'simple', 'vista': 'frente', 'gas_ok': 'si',
        'piso': 5, 'total_pisos': 10, 'tipo_balcon': 'ninguno',
        'ubicacion_tipo': 'calle', 'orientacion': 'norte',
        'lat': -32.9541, 'lon': -60.6316
    }
    mejorado = {**base,
        'estado_detalle': 'premium', 'calidad_edificio': 'excelente',
        'ventilacion': 'cruzada'
    }

    from parsers.mercado_inmobiliario import valuar_propiedad_v7
    r_base = valuar_propiedad_v7(base, fecha_ref='2026-04')
    r_mejor = valuar_propiedad_v7(mejorado, fecha_ref='2026-04')

    v_base = r_base.get('valor_propiedad_usd', 0)
    v_mejor = r_mejor.get('valor_propiedad_usd', 0)

    assert v_base > 0, "Valuación base debe ser > 0"
    assert v_mejor > 0, "Valuación mejorada debe ser > 0"

    ratio = v_mejor / v_base
    assert 1.15 <= ratio <= 1.25, \
        f"Ratio {ratio:.3f} fuera del rango esperado [1.15, 1.25]. " \
        f"Base=${v_base:,.0f}, Mejorado=${v_mejor:,.0f}"
