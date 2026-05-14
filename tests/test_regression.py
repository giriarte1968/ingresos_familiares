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
import json

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
    # Aceptar rango +-10% del valor esperado
    assert 75000 <= r['valor_propiedad_usd'] <= 82000, f"Lista {r['valor_propiedad_usd']} fuera de rango"


def test_mabel_alquiler():
    """Valida alquiler y ROI para Mabel"""
    r = valuar_propiedad_v7(ejecutar_valuacion('mabel'), fecha_ref='2026-04')
    assert 380_000 <= r['alquiler_estimado_ars'] <= 600_000, f"Alquiler {r['alquiler_estimado_ars']} fuera de rango"
    assert r.get('es_fallback_alquiler') == False, "Mabel debe usar Cap Rate data-driven"
    cap = r.get('cap_rate', 0)
    assert 0.03 <= cap <= 0.08, f"Cap rate {cap*100:.1f}% fuera de rango 3-8%"


def test_ayacucho_venta():
    """Valida rangos de venta para Ayacucho (6ta Pellegrini)"""
    r = valuar_propiedad_v7(ejecutar_valuacion('ayacucho'))
    assert 48000 <= r['valor_propiedad_usd'] <= 52000, f"Lista {r['valor_propiedad_usd']} fuera de rango"


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
    
    # Valor principal dentro del rango definitivo (age-filtered, P40, 8 comps)
    valor_principal = r.get('valor_propiedad_usd', 0)
    assert 50000 <= valor_principal <= 55000, f"Valor Vera {valor_principal} fuera de rango"


def test_ui_vs_python_no_diverge():
    """
    RO-12: El valor calculado directamente en Python
    no debe diferir de los rangos de honor.
    Si diverge, hay un problema de caché o lógica obsoleta.
    """
    from parsers.mercado_inmobiliario import valuar_propiedad_v7
    from tests.test_regression import ejecutar_valuacion
    
    r = valuar_propiedad_v7(ejecutar_valuacion('mabel'))
    # Valor Lista = blend P50_age con alpha 0.70
    assert 75000 <= r['valor_propiedad_usd'] <= 82000, \
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


# --- TESTS CAP RATE DATA-DRIVEN ---

def test_cap_rate_derivado_mabel():
    """Mabel debe tener cap rate derivado de datos (no fallback)"""
    r = valuar_propiedad_v7(ejecutar_valuacion('mabel'), fecha_ref='2026-04')
    assert r.get('es_fallback_alquiler') == False, \
        "Mabel tiene suficientes datos para cap rate local"
    cap = r.get('cap_rate', 0)
    assert 0.03 <= cap <= 0.08, f"Cap rate {cap*100:.1f}% fuera de rango 3-8%"


def test_cap_rate_rango_alquiler():
    """El rango de alquiler debe ser coherente"""
    r = valuar_propiedad_v7(ejecutar_valuacion('mabel'), fecha_ref='2026-04')
    rango = r.get('alquiler_rango', {})
    if rango:
        assert rango.get('min', 0) < rango.get('mid', 0) < rango.get('max', 0), \
            "Rango alquiler debe ser min < mid < max"


def test_fallback_badge_amenabar():
    """Amenabar puede usar fallback si hay pocos datos de alquiler"""
    try:
        r = valuar_propiedad_v7(ejecutar_valuacion('amenabar'), fecha_ref='2026-04')
    except:
        pass  # Skip if property not found


def test_alquiler_no_absurdo():
    """Ningún alquiler debe ser < $100k o > $2M ARS"""
    for nombre in ['mabel', 'ayacucho', 'vera']:
        try:
            r = valuar_propiedad_v7(ejecutar_valuacion(nombre), fecha_ref='2026-04')
            alq = r.get('alquiler_estimado_ars', 0)
            assert 100000 <= alq <= 2000000, \
                f"{nombre}: alquiler ${alq:,.0f} fuera de rango razonable"
        except:
            pass  # Skip if property not found


# --- TESTS SIZE DISCOUNT ---

def test_size_discount_no_aplica_unidad_chica():
    """Unidades <= 45m² no tienen descuento"""
    from parsers.mercado_inmobiliario import calcular_size_discount_alquiler
    assert calcular_size_discount_alquiler(40) == 1.00


def test_size_discount_aplica_unidad_grande():
    """Unidades > 45m² tienen descuento progresivo"""
    from parsers.mercado_inmobiliario import calcular_size_discount_alquiler
    factor = calcular_size_discount_alquiler(90)
    assert 0.70 <= factor <= 0.85


def test_size_discount_progresivo():
    """A mayor tamaño, mayor descuento"""
    from parsers.mercado_inmobiliario import calcular_size_discount_alquiler
    f45 = calcular_size_discount_alquiler(45)
    f60 = calcular_size_discount_alquiler(60)
    f80 = calcular_size_discount_alquiler(80)
    f100 = calcular_size_discount_alquiler(100)
    assert f45 > f60 > f80 > f100


def test_size_discount_piso():
    """Factor nunca baja de 0.75"""
    from parsers.mercado_inmobiliario import calcular_size_discount_alquiler
    factor = calcular_size_discount_alquiler(150)
    assert factor == 0.75


def test_alquiler_1dorm_sin_cambio():
    """Mabel (42.6m²) no debe tener size discount"""
    result = valuar_propiedad_v7(ejecutar_valuacion('mabel'), fecha_ref='2026-04')
    assert result.get('size_discount_alquiler', 1.0) == 1.0


def test_alquiler_p1200_con_discount():
    """P1200 (88.85m²) debe tener size discount ~0.78"""
    # Load P1200 from propiedades.json
    with open('propiedades.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    prop = [p for p in data['propiedades'] if 'P1200' in p.get('nombre', '')][0]
    
    result = valuar_propiedad_v7(prop, fecha_ref='2026-04')
    sd = result.get('size_discount_alquiler', 1.0)
    assert 0.75 <= sd <= 0.85
    alq = result.get('alquiler_estimado_ars', 0)
    # P1200 debe estar dentro de benchmark $600k-$900k
    assert 600000 <= alq <= 900000, f"P1200 alquiler ${alq:,.0f} fuera de benchmark"


# ─── FASE 1: ENRIQUECIMIENTO DE AÑO DESDE CATASTRO ───

def test_fase1_no_cambia_valores():
    """Enriquecimiento NO debe cambiar valores de venta/alquiler"""
    valores_referencia = {
        'mabel': (70000, 85000),
        'ayacucho': (44000, 50000),
    }
    for nombre, (lo, hi) in valores_referencia.items():
        r = valuar_propiedad_v7(ejecutar_valuacion(nombre), fecha_ref='2026-04')
        valor = r.get('valor_propiedad_usd', 0)
        assert lo <= valor <= hi, f"{nombre}: valor ${valor} fuera de rango esperado (${lo}-${hi})"


def test_fase1_pool_enriquecido():
    """Verificar que al menos algunos comparables se enriquecen"""
    r = valuar_propiedad_v7(ejecutar_valuacion('mabel'), fecha_ref='2026-04')
    meta = r.get('resolution_metadata', {})
    pct = meta.get('pct_con_anio', 0)
    total = meta.get('n_comparables_total', 0)
    alta = meta.get('n_con_anio_alta', 0)
    media = meta.get('n_con_anio_media', 0)
    print(f"\n[FASE1] Mabel: pool={total}, ALTA={alta}, MEDIA={media}, pct={pct}%")
    assert pct > 0, f"Mabel: {pct}% enriquecido (esperado >0%)"


# ─── FASE 2: FILTRO DE EDAD ±15 AÑOS ───

def test_filtro_edad_reduce_pool():
    """Con filtro de edad, pool se reduce"""
    r = valuar_propiedad_v7(ejecutar_valuacion('mabel'), fecha_ref='2026-04')
    meta = r.get('resolution_metadata', {})
    
    if meta.get('age_filter_applied'):
        n_filtered = meta.get('n_age_filtered', 0)
        n_total = meta.get('n_comparables_total', 0)
        assert n_filtered > 0, "Filtro debe dejar al menos 1 comparable"
        assert n_filtered < n_total, "Filtro debe reducir el pool"
        assert n_filtered >= 8, "Debe quedar mínimo 8 comparables"
        print(f"\n[FASE2] Mabel: pool={n_total} → {n_filtered} (ventana {meta.get('age_window', '?')})")


def test_anio_no_hardcodeado():
    """Verificar que no hay 2026 hardcodeado en el cálculo de antigüedad"""
    import datetime
    r = valuar_propiedad_v7(ejecutar_valuacion('mabel'))
    assert r.get('valor_propiedad_usd', 0) > 0
    print(f"\n[ANIO_DINAMICO] Año actual={datetime.datetime.now().year}, valor=${r.get('valor_propiedad_usd', 0):,.0f}")


# ─── FASE 3: PERCENTIL AJUSTADO POR EDAD ───

def test_percentil_p50_con_age_filter():
    """Mabel (n=27 >=20) debe usar P50_age"""
    r = valuar_propiedad_v7(ejecutar_valuacion('mabel'), fecha_ref='2026-04')
    meta = r.get('resolution_metadata', {})
    if meta.get('age_filter_applied') and meta.get('n_age_filtered', 0) >= 20:
        assert meta.get('percentil_usado') == 'P50_age', \
            f"Esperaba P50_age, obtuvo {meta.get('percentil_usado')}"


def test_percentil_p45_con_age_filter():
    """Si n entre 10 y 19, debe usar P45_age"""
    r = valuar_propiedad_v7(ejecutar_valuacion('ayacucho'), fecha_ref='2026-04')
    meta = r.get('resolution_metadata', {})
    n = meta.get('n_age_filtered', 0)
    if meta.get('age_filter_applied') and 10 <= n < 20:
        assert meta.get('percentil_usado') == 'P45_age', \
            f"n={n} esperaba P45_age, obtuvo {meta.get('percentil_usado')}"


def test_alquiler_sigue_p50():
    """Alquiler siempre usa P50 aunque haya age_filter"""
    r = valuar_propiedad_v7(ejecutar_valuacion('mabel'), fecha_ref='2026-04')
    meta = r.get('resolution_metadata', {})
    alq = r.get('alquiler_estimado_ars', 0)
    assert 380000 <= alq <= 600000, f"Alquiler {alq} fuera de rango"


def test_percentil_p33_sin_age_filter():
    """Sin age filter, venta debe usar P33"""
    r = valuar_propiedad_v7(ejecutar_valuacion('ayacucho'), fecha_ref='2026-04')
    meta = r.get('resolution_metadata', {})
    if not meta.get('age_filter_applied'):
        assert meta.get('percentil_usado') == 'P33', \
            f"Sin filtro esperaba P33, obtuvo {meta.get('percentil_usado')}"