"""DEBUG COMPLETO - Todos los calculos para Mabel, Ayacucho y P1200"""
import sys
import os
sys.path.insert(0, 'C:/Users/Gustavo/ingresos_familiares_st')

from parsers.mercado_inmobiliario import (
    valuar_propiedad_v7, calcular_factores, calcular_m2_equivalentes,
    obtener_mediana_cluster_v2, normalizar_zona
)

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

print("=" * 100)
for name, prop in props.items():
    print(f"\n{'#' * 100}")
    print(f"### {name.upper()}")
    print(f"{'#' * 100}")
    
    # 1. METROS EQUIVALENTES
    m2_equiv = calcular_m2_equivalentes(prop)
    print(f"\n[1] METROS EQUIVALENTES:")
    print(f"  m2_cubiertos: {prop.get('m2_cubiertos')}")
    print(f"  m2_semicubiertos: {prop.get('m2_semicubiertos', 0)} (coef 0.45)")
    print(f"  m2_descubiertos: {prop.get('m2_descubiertos', 0)} (coef 0.20)")
    print(f"  m2_equiv = {m2_equiv}")
    
    # 2. CLUSTER V2 - Obtener m2_base
    zona = prop.get('zona', 'centro')
    dorms = prop.get('dormitorios', 1)
    lat = prop.get('lat', -32.9545)
    lon = prop.get('lon', -60.6455)
    zona_norm = normalizar_zona(zona)
    
    m2_base_venta, n_props, meta = obtener_mediana_cluster_v2(
        zona=zona_norm, dormitorios=dorms, operacion='venta', lat_ref=lat, lon_ref=lon, fecha_ref="2026-04"
    )
    print(f"\n[2] CLUSTER V2 (m2_base):")
    print(f"  zona_input: {zona}")
    print(f"  zona_normalizada: {zona_norm}")
    print(f"  dormitorios: {dorms}")
    print(f"  lat/lon: {lat}, {lon}")
    print(f"  m2_base_venta: {m2_base_venta}")
    print(f"  n_props_en_cluster: {n_props}")
    print(f"  radio_usado: {meta.get('radio_usado')}")
    print(f"  percentil_usado: {meta.get('percentil_usado')}")
    print(f"  zona_resol: {meta.get('zona_resolucion')}")
    
    # 3. FACTORES INDIVIDUALES
    f = calcular_factores(prop)
    print(f"\n[3] FACTORES INDIVIDUALES:")
    print(f"  antiguedad (calculada): {prop.get('antiguedad', 0)} años")
    print(f"  factor_estado ({prop.get('estado_detalle')}): {f.get('factor_estado')}")
    print(f"  factor_calidad ({prop.get('calidad_edificio')}): {f.get('factor_calidad')}")
    print(f"  factor_vent ({prop.get('ventilacion')}): {f.get('factor_vent')}")
    print(f"  factor_vista ({prop.get('vista')}): {f.get('factor_vista')}")
    print(f"  factor_piso (piso {prop.get('piso')}/{prop.get('total_pisos')}): {f.get('factor_piso')}")
    print(f"  factor_ubica ({prop.get('ubicacion_tipo')}): {f.get('factor_ubica')}")
    print(f"  factor_gas: {f.get('factor_gas')}")
    print(f"  factor_balcon: {f.get('factor_balcon')}")
    print(f"  factor_funcional: {f.get('factor_funcional')}")
    print(f"  factor_seguridad: {f.get('factor_seguridad')}")
    print(f"  factor_pasillo: {f.get('factor_pasillo')}")
    print(f"  depreciacion (anti): {f.get('depreciacion')}")
    
    # 4. PRODUCTO DE FACTORES
    print(f"\n[4] PRODUCTO DE FACTORES:")
    print(f"  estructural_puro = estado × calidad × vent × vista × piso × ubica × gas × balcon × func × seg × pasillo")
    print(f"  estructural_puro = {f.get('estructural_puro'):.4f}")
    print(f"  factores_total (con anti) = {f.get('total'):.4f}")
    print(f"  suma_cruda = {f.get('suma_cruda'):.4f}")
    
    # 5. VALOR FINAL
    r = valuar_propiedad_v7(prop, fecha_ref="2026-04")
    print(f"\n[5] CALCULO FINAL:")
    print(f"  valor_venta (before NLP): {r.get('valor_venta', 0):,.0f}")
    print(f"  ajuste_nlp: {r.get('ajuste_nlp', 0):.4f}")
    print(f"  GAP_CIERRE (0.92): {0.92}")
    print(f"  valor_propiedad_usd: {r.get('valor_propiedad_usd', 0):,.0f}")
    
    print(f"\n[6] DETALLE FORMULA:")
    print(f"  valor = m2_equiv × m2_base × factores_total × (1 + NLP) × 0.92")
    print(f"  valor = {m2_equiv} × {m2_base_venta} × {f.get('total'):.4f} × (1 + {r.get('ajuste_nlp', 0):.4f}) × 0.92")
    valor_calc = m2_equiv * m2_base_venta * f.get('total') * (1 + r.get('ajuste_nlp', 0)) * 0.92
    print(f"  valor = {valor_calc:,.0f}")
    print(f"  DIFERENCIA: {abs(valor_calc - r.get('valor_propiedad_usd', 0)):,.0f}")

print(f"\n{'=' * 100}")