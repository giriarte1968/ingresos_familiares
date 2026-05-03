from parsers.mercado_inmobiliario import valuar_propiedad_v7

mabel = {
    'tipo_inmueble': 'departamento',
    'zona': 'Martin',
    'direccion': 'Mabel 1400',
    'lat': -32.9541,
    'lon': -60.6316,
    'm2': 48.5,
    'm2_cubiertos': 41.0,
    'm2_semicubiertos': 7.5,
    'm2_descubiertos': 0.0,
    'dormitorios': 1,
    'anio_construccion': 2000,
    'estado_detalle': 'muy bueno',
    'calidad_edificio': 'media',
    'descripcion_libre': 'luminoso, con aire acondicionado',
    'piso': 2,
    'total_pisos': 10,
    'ventilacion': 'cruzada',
}

r = valuar_propiedad_v7(mabel)

print('=== MABEL 1400 ===')
print(f"valor_lista:     ${r.get('valor_propiedad_usd'):,.0f}")
print(f"valor_cierre:   ${r.get('valor_realizable_usd'):,.0f}")
print(f"alquiler_ars:   ${r.get('alquiler_estimado_ars'):,.0f}")
print(f"roi_anual:      {r.get('cap_rate_anual'):.2f}%")
print()
print('=== COMPONENTES ===')
print(f"m2_equiv:      {r.get('m2_equivalentes', 0):.2f}")
print(f"m2_base:       {r.get('precio_base_m2', 0):.2f}")
print(f"factor_total:   {r.get('factor_total', 0):.4f}")
print(f"metodo:        {r.get('metodo_base', 'N/A')}")
print(f"radio:         {r.get('resolution_metadata', {}).get('resolution', 'N/A')}")
print(f"ventana:       {r.get('ventana_usada', 'N/A')}")
print(f"n_comparables:{r.get('n_comparables', 0)}")