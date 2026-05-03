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

print('=== FULL RESULT KEYS ===')
for k, v in r.items():
    if isinstance(v, dict):
        print(f"{k}:")
        for k2, v2 in v.items():
            print(f"  {k2}: {v2}")
    else:
        print(f"{k}: {v}")