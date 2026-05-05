"""Debug - Show detailed calculation breakdown with correct keys"""
import sys
import os
sys.path.insert(0, 'C:/Users/Gustavo/ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7, calcular_factores, calcular_m2_equivalentes

props = {
    'mabel': {
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
    },
    'ayacucho': {
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
    },
    'vera': {
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
    },
    'p1200': {
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
}

print("=" * 80)
for name, prop in props.items():
    print(f"\n### {name.upper()} ###")
    r = valuar_propiedad_v7(prop, fecha_ref="2026-04")
    
    # Factores detalle
    f = calcular_factores(prop)
    m2_equiv = calcular_m2_equivalentes(prop)
    
    print(f"m2_cubiertos: {prop.get('m2_cubiertos')}")
    print(f"m2_semicubiertos: {prop.get('m2_semicubiertos', 0)}")
    print(f"m2_descubiertos: {prop.get('m2_descubiertos', 0)}")
    print(f"m2_equiv: {m2_equiv}")
    print(f"m2_base_venta: {r.get('m2_base_venta', 0)}")
    print(f"factor_estado: {f.get('factor_estado', 0):.4f}")
    print(f"factor_calidad: {f.get('factor_calidad', 0):.4f}")
    print(f"factor_balcon: {f.get('factor_balcon', 0):.4f}")
    print(f"factor_vent: {f.get('factor_vent', 0):.4f}")
    print(f"factor_vista: {f.get('factor_vista', 0):.4f}")
    print(f"factor_piso: {f.get('factor_piso', 0):.4f}")
    print(f"factor_ubica: {f.get('factor_ubica', 0):.4f}")
    print(f"factor_gas: {f.get('factor_gas', 0):.4f}")
    print(f"factor_funcional: {f.get('factor_funcional', 0):.4f}")
    print(f"factor_seguridad: {f.get('factor_seguridad', 0):.4f}")
    print(f"factor_pasillo: {f.get('factor_pasillo', 0):.4f}")
    print(f"depreciacion: {f.get('depreciacion', 0):.4f}")
    print(f"---")
    print(f"estructural_puro: {f.get('estructural_puro', 0):.4f}")
    print(f"factores_total: {f.get('total', 0):.4f}")
    print(f"suma_cruda: {f.get('suma_cruda', 0):.4f}")
    print(f"NLP: {r.get('ajuste_nlp', 0):.4f}")
    print(f"---")
    print(f"FORMULA: {m2_equiv} x {r.get('m2_base_venta', 0):.0f} x {f.get('total', 0):.4f} x (1 + {r.get('ajuste_nlp', 0):.4f})")
    print(f"CALC: {m2_equiv} x {r.get('m2_base_venta', 0):.0f} x {f.get('total', 0):.4f} x {1 + r.get('ajuste_nlp', 0):.4f} = ${r.get('valor_propiedad_usd', 0):,.0f}")
    print("=" * 80)