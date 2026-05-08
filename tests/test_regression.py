"""
🏠 AVM ROSARIO — SUITE DE REGRESIÓN OBLIGATORIA
Este archivo es el guardián de la lógica de negocio. 
Basado en docs/MEMORIA_PROYECTO.md - Sección 11.

⛔ LOS RANGOS DE ESTOS TESTS SON INAMOVIBLES.
Si un cambio en el código hace que estos tests fallen, el cambio está MAL.
"""
import pytest
import os
import sys

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
            'tipo_balcon': 'corrido', 'balcon': True,
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
    assert 80000 <= r['valor_propiedad_usd'] <= 82000, f"Lista {r['valor_propiedad_usd']} fuera de rango"


def test_mabel_alquiler():
    """Valida alquiler y ROI para Mabel"""
    r = valuar_propiedad_v7(ejecutar_valuacion('mabel'), fecha_ref="2026-04")
    assert 360_000 <= r['alquiler_estimado_ars'] <= 460_000, f"Alquiler {r['alquiler_estimado_ars']} fuera de rango"
    assert 3.0 <= r['cap_rate_anual'] <= 6.5, f"ROI {r['cap_rate_anual']}% fuera de rango"


def test_ayacucho_venta():
    """Valida rangos de venta para Ayacucho (6ta Pellegrini)"""
    r = valuar_propiedad_v7(ejecutar_valuacion('ayacucho'))
    assert 44000 <= r['valor_propiedad_usd'] <= 50000, f"Lista {r['valor_propiedad_usd']} fuera de rango"


def test_patio_grande_vera():
    """Verifica ajuste patio grande para Vera Mujica (m2_desc=24, piso=0).
    ALGORITMOS.md: m2_desc>=20 -> coef 0.25, PB+patio>=15 -> factor_piso 0.98
    """
    import json
    with open('propiedades.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    vera = None
    for p in data.get('propiedades', []):
        if p.get('nombre') == 'Vera Mujica':
            vera = p
            break
    
    assert vera is not None, "Vera Mujica no encontrada"
    assert vera.get('m2_descubiertos_comun_exclusivo', 0) >= 10, "Vera debe tener patio uso comun exclusivo >= 10m2"
    assert vera.get('piso') == 0, "Vera debe ser PB"
    
    r = valuar_propiedad_v7(vera, fecha_ref='2026-04')
    
# Vera: m2_equiv con 12.7m2 uso comun exclusivo (coef 35% PB) = ~40.0
    m2_equiv = r['m2_equivalentes']
    assert 35.0 <= m2_equiv <= 42.0, f"m2_equiv {m2_equiv} fuera de rango"
    
    # Valor principal dentro del rango (benchmark $42k-$55k)
    valor_principal = r.get('valor_propiedad_usd', 0)
    assert 40000 <= valor_principal <= 55000, f"Valor Vera {valor_principal} fuera de rango"


def test_ui_vs_python_no_diverge():
    """
    RO-12: El valor calculado directamente en Python
    no debe diferir de los rangos de honor.
    Si diverge, hay un problema de caché o lógica obsoleta.
    """
    from parsers.mercado_inmobiliario import valuar_propiedad_v7
    from tests.test_regression import ejecutar_valuacion
    
    r = valuar_propiedad_v7(ejecutar_valuacion('mabel'))
    # Mabel venta lista rango post-sincronizacion UI-CLI
    assert 80000 <= r['valor_propiedad_usd'] <= 82000, \
        f"DIVERGENCIA CRITICA: Mabel da {r['valor_propiedad_usd']}"


def test_normalize_year():
    """Valida normalize_year() con distintos inputs."""
    from parsers.mercado_inmobiliario import normalize_year
    
    assert normalize_year("1998") == 1998
    assert normalize_year("1998-01-01") == 1998
    assert normalize_year(1998) == 1998
    assert normalize_year(1998.0) == 1998
    assert normalize_year(None) is None
    assert normalize_year("") is None
    assert normalize_year("abcd") is None
    assert normalize_year(1800) is None
    assert normalize_year(2050) is None


def test_m2_equiv_legado_igual():
    """Propiedad legacy (solo m2_cubiertos, m2_semicubiertos) debe dar igual que antes."""
    from parsers.mercado_inmobiliario import calcular_m2_equivalentes
    
    prop = {
        'm2_cubiertos': 41.0,
        'm2_semicubiertos': 7.5,
        'm2_semicubiertos_detalle': 'medio',
        'm2_descubiertos': 0,
        'm2_comunes': 0,
    }
    m2 = calcular_m2_equivalentes(prop)
    assert 43.5 <= m2 <= 45.5, f"m2_equiv legacy changed: {m2}"


def test_m2_equiv_granular():
    """Propiedad con m2_semi_propios y m2_semi_exclusivos usa modo granular."""
    from parsers.mercado_inmobiliario import calcular_m2_equivalentes
    
    prop = {
        'm2_cubiertos': 39.50,
        'm2_semi_propios': 1.22,
        'm2_semi_exclusivos': 5.01,
        'm2_semicubiertos_detalle': 'medio',
        'tipo_balcon': 'corrido',
        'm2_descubiertos': 0,
        'm2_comunes': 28.43,
    }
    m2 = calcular_m2_equivalentes(prop)
    assert 45.5 <= m2 <= 46.5, f"m2_equiv granular: {m2}"


def test_no_usa_m2_total_escritura_como_cubierto():
    """m2_total_escritura NO debe usarse como fallback de cubiertos."""
    from parsers.mercado_inmobiliario import calcular_m2_equivalentes
    
    prop = {
        'm2_total_escritura': 74.16,
        'm2_cubiertos': 39.5,
        'm2_semicubiertos': 10.0,
        'm2_semicubiertos_detalle': 'medio',
        'm2_descubiertos': 5.0,
    }
    m2 = calcular_m2_equivalentes(prop)
    assert m2 < 60, f"m2_equiv usa m2_total_escritura como cubiertos: {m2}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])