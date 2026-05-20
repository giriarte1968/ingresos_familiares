"""
Tests para el módulo de auditoría técnica.
Verifica que audit_log se genere correctamente y sea consistente.
"""
import pytest
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.audit_logger import generar_audit_log, guardar_audit_log, cargar_audit_logs, obtener_ultimo_audit_log
from parsers.mercado_inmobiliario import valuar_propiedad_v7, calcular_factores


def test_valuacion_retiene_audit_log():
    """valuar_propiedad_v7() debe retornar audit_log en el resultado."""
    prop = {
        'nombre': 'Audit Test', 'tipo_inmueble': 'departamento',
        'zona': 'Martin', 'direccion': 'Test 123',
        'lat': -32.9541, 'lon': -60.6316,
        'm2': 48, 'm2_cubiertos': 41, 'm2_semicubiertos': 7,
        'dormitorios': 1, 'anio_construccion': 2000,
        'estado_detalle': 'bueno', 'calidad_edificio': 'media',
        'ventilacion': 'simple', 'piso': 5, 'total_pisos': 10,
        'vista': 'frente', 'ubicacion_tipo': 'calle', 'gas_ok': 'si',
    }
    r = valuar_propiedad_v7(prop, fecha_ref='2026-04')
    assert 'audit_log' in r, "El resultado debe contener audit_log"
    assert isinstance(r['audit_log'], dict), "audit_log debe ser un dict"


def test_audit_log_campos_minimos():
    """El audit_log debe contener las secciones principales."""
    prop = {
        'nombre': 'Audit Fields Test', 'tipo_inmueble': 'departamento',
        'zona': 'Martin', 'direccion': 'Test 456',
        'lat': -32.9541, 'lon': -60.6316,
        'm2': 50, 'm2_cubiertos': 45,
        'dormitorios': 2, 'anio_construccion': 2005,
        'estado_detalle': 'bueno', 'calidad_edificio': 'media',
        'ventilacion': 'cruzada', 'piso': 3, 'total_pisos': 8,
        'vista': 'frente', 'ubicacion_tipo': 'calle', 'gas_ok': 'si',
    }
    r = valuar_propiedad_v7(prop, fecha_ref='2026-04')
    audit = r['audit_log']
    
    secciones = ['propiedad', 'superficies', 'cluster_venta', 'factores', 'venta', 'alquiler', 'final']
    for seccion in secciones:
        assert seccion in audit, f"Falta sección {seccion} en audit_log"
        assert isinstance(audit[seccion], dict), f"Sección {seccion} debe ser un dict"
    
    # Campos clave dentro de cada sección
    assert 'nombre' in audit['propiedad']
    assert 'm2_equiv' in audit['superficies']
    assert 'n_total_cluster' in audit['cluster_venta']
    assert 'estado' in audit['factores']
    assert 'valor_principal' in audit['venta']
    assert 'cap_rate' in audit['alquiler']
    assert 'valor_venta' in audit['final']


def test_audit_log_valores_consistentes():
    """
    Los valores del audit_log deben ser consistentes con el resultado principal.
    - valor_venta del resultado = final.valor_venta del audit_log
    - m2_equiv del resultado = superficies.m2_equiv
    - etc.
    """
    prop = {
        'nombre': 'Consistency Test', 'tipo_inmueble': 'departamento',
        'zona': 'Martin', 'direccion': 'Consist 789',
        'lat': -32.9541, 'lon': -60.6316,
        'm2': 48, 'm2_cubiertos': 41, 'm2_semicubiertos': 7,
        'dormitorios': 1, 'anio_construccion': 2000,
        'estado_detalle': 'bueno', 'calidad_edificio': 'media',
        'ventilacion': 'simple', 'piso': 5, 'total_pisos': 10,
        'vista': 'frente', 'ubicacion_tipo': 'calle', 'gas_ok': 'si',
    }
    r = valuar_propiedad_v7(prop, fecha_ref='2026-04')
    audit = r['audit_log']
    
    assert r['valor_propiedad_usd'] == audit['final']['valor_venta'], \
        f"valor_venta inconsistente: {r['valor_propiedad_usd']} vs {audit['final']['valor_venta']}"
    assert r['m2_equivalentes'] == audit['superficies']['m2_equiv'], \
        f"m2_equiv inconsistente: {r['m2_equivalentes']} vs {audit['superficies']['m2_equiv']}"
    assert r['alquiler_estimado_ars'] == audit['final']['alquiler_mensual_ars'], \
        f"alquiler inconsistente: {r['alquiler_estimado_ars']} vs {audit['final']['alquiler_mensual_ars']}"


def test_audit_log_valores_positivos():
    """Verifica que los valores principales sean > 0."""
    prop = {
        'nombre': 'Positive Test', 'tipo_inmueble': 'departamento',
        'zona': 'Martin', 'direccion': 'Positive 111',
        'lat': -32.9541, 'lon': -60.6316,
        'm2': 48, 'm2_cubiertos': 41,
        'dormitorios': 1, 'anio_construccion': 2000,
        'estado_detalle': 'bueno', 'calidad_edificio': 'media',
        'ventilacion': 'simple', 'piso': 5, 'total_pisos': 10,
        'vista': 'frente', 'ubicacion_tipo': 'calle', 'gas_ok': 'si',
    }
    r = valuar_propiedad_v7(prop, fecha_ref='2026-04')
    audit = r['audit_log']
    assert audit['final']['valor_venta'] > 0
    assert audit['final']['valor_realizable'] > 0
    assert audit['superficies']['m2_equiv'] > 0
    assert audit['venta']['valor_principal'] > 0


def test_generar_audit_log_directo():
    """Llama a generar_audit_log directamente con un f_dict mínimo."""
    prop = {'nombre': 'Direct Test', 'zona': 'Centro'}
    resultado = {
        'm2_equivalentes': 40.0,
        'valor_propiedad_usd': 50000,
        'nlp_ajuste_pct': 2.0,
        'alquiler_estimado_ars': 150000,
        'valor_realizable_usd': 46000,
        'plusvalia_ciclo_usd': 5000,
        'plusvalia_ciclo_pct': 10.0,
        'plusvalia_tipo': 'Real',
        'cap_rate_anual': 5.0,
        'cap_rate_bruto': 6.0,
        'usdt_ars': 1200,
        'rango_venta': {'min': 45000, 'mid': 50000, 'max': 55000, 'spread_pct': 10.0},
        'metodo_alquiler': 'mercado_local',
        'cap_rate': 0.05,
        'es_fallback_alquiler': False,
        'size_discount_alquiler': 1.0,
        'confianza_alquiler': 'ALTA',
        'mantenimiento_mensual_ars': 5000,
        'expensas_ars': 3000,
        'cap_rate_info': {'cap_rate_min': 0.04, 'cap_rate_max': 0.06, 'n_alquiler': 10},
        'alquiler_rango': {'min': 130000, 'mid': 150000, 'max': 170000},
        'm2_base_venta': 1250.0,
    }
    f_dict = {
        'factor_estado': 1.0, 'factor_calidad': 1.0,
        'depreciacion': 0.95, 'suma_cruda': 0.05,
        'suma_cruda_raw': 0.05, 'f_estructural': 1.05,
        'tasa_zonal': 0.006,
    }
    meta_venta = {
        'n_con_anio_alta': 10, 'n_con_anio_media': 5,
        'pct_con_anio': 75.0, 'age_filter_applied': False,
        'n_age_filtered': 0, 'percentil_usado': 'P33',
        'p33_same': 1200, 'p33_cross': 1300,
        'base_principal': 1250, 'radio_usado': 300,
        'n_same_side': 20, 'n_cross_soft': 5,
    }
    audit = generar_audit_log(
        propiedad=prop, resultado=resultado,
        f_dict=f_dict, meta_venta=meta_venta, n_v=25,
        m2_base_venta_raw=1250, meta_alq={}, n_a=10,
        es_ventana3=False, m2_equiv_alquiler=36.0,
        factores_alquiler=1.05, m2_base_alquiler=12000,
        ajuste_nlp=0.02, nlp_cap=0.03,
        resolution_metadata={}, rango_venta=resultado['rango_venta'],
        comparables_venta=[],
    )
    assert audit['final']['valor_venta'] == 50000
    assert audit['superficies']['m2_equiv'] == 40.0
    assert audit['cluster_venta']['n_total_cluster'] == 25
    assert audit['factores']['estado'] == 1.0


def test_audit_log_no_altera_resultado():
    """El audit_log no debe cambiar los valores del resultado."""
    prop = {
        'nombre': 'NoChange Test', 'tipo_inmueble': 'departamento',
        'zona': 'Martin', 'direccion': 'NoChange 222',
        'lat': -32.9541, 'lon': -60.6316,
        'm2': 48, 'm2_cubiertos': 41,
        'dormitorios': 1, 'anio_construccion': 2000,
        'estado_detalle': 'bueno', 'calidad_edificio': 'media',
        'ventilacion': 'simple', 'piso': 5, 'total_pisos': 10,
        'vista': 'frente', 'ubicacion_tipo': 'calle', 'gas_ok': 'si',
    }
    r = valuar_propiedad_v7(prop, fecha_ref='2026-04')
    # Verificar que los campos existentes sigan siendo del mismo tipo
    assert isinstance(r['valor_propiedad_usd'], (int, float))
    assert isinstance(r['m2_base_venta'], (int, float))
    assert isinstance(r['alquiler_estimado_ars'], (int, float))
    assert 'audit_log' in r
    # El audit_log no debe tener secciones vacías
    for sec in ['propiedad', 'superficies', 'cluster_venta', 'factores', 'venta', 'alquiler', 'final']:
        assert r['audit_log'][sec] is not None, f"Sección {sec} no debe ser None"
