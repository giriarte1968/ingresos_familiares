"""Test Mabel after factor calibration"""
import sys
import os
sys.path.insert(0, 'C:/Users/Gustavo/ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7

mabel = {
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

result = valuar_propiedad_v7(mabel, fecha_ref="2026-04")
print(f"Mabel: {result.get('valor_propiedad_usd', 0):,.0f}")
print(f"m2_base: {result.get('m2_base_venta', 0)}")
print(f"factores_total: {result.get('factores_total', 0)}")