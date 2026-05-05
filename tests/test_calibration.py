"""Test all properties after calibration"""
import sys
import os
sys.path.insert(0, 'C:/Users/Gustavo/ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7

# Mabel
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

# Ayacucho
ayacucho = {
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

# Vera (patio grande)
vera = {
    'tipo_inmueble': 'departamento',
    'zona': 'Martin',
    'direccion': 'Vera Mujica 2400',
    'lat': -32.9511, 'lon': -60.6289,
    'm2': 88, 'm2_cubiertos': 64, 'm2_descubiertos': 24,
    'dormitorios': 2, 'anio_construccion': 2015,
    'estado_detalle': 'muy bueno', 'calidad_edificio': 'media',
    'piso': 0, 'total_pisos': 4,
    'ventilacion': 'simple',
    'vista': 'frente', 'ubicacion_tipo': 'calle', 'gas_ok': 'si',
    'ascensores_edificio': 2, 'detalles_categoria': [],
}

# P1200
p1200 = {
    'tipo_inmueble': 'departamento',
    'zona': 'Pellegrini 1200',
    'direccion': 'Pellegrini 1200',
    'lat': -32.9516, 'lon': -60.6302,
    'm2': 88.85, 'm2_cubiertos': 88.85,
    'dormitorios': 2, 'anio_construccion': 2018,
    'estado_detalle': 'excelente',
    'calidad_edificio': 'alta',
    'piso': 3, 'total_pisos': 12,
    'ventilacion': 'cruzada',
    'vista': 'despejada', 'ubicacion_tipo': 'avenida', 'gas_ok': 'si',
    'ascensores_edificio': 3, 'detalles_categoria': ['seguridad_24hs', 'gimnasio'],
}

print("=== CALIBRATION RESULTS ===")
for name, prop in [("Mabel", mabel), ("Ayacucho", ayacucho), ("Vera", vera), ("P1200", p1200)]:
    result = valuar_propiedad_v7(prop, fecha_ref="2026-04")
    print(f"{name}: ${result.get('valor_propiedad_usd', 0):,.0f} | m2_base: {result.get('m2_base_venta', 0):.0f}")