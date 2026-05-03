
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

try:
    from parsers.mercado_inmobiliario import valuar_propiedad_v7
    print("IMPORT_OK")
except Exception as e:
    print(f"IMPORT_ERROR: {e}")
    sys.exit(1)

test_prop = {
    'id': 'test_1',
    'nombre': 'Propiedad Test',
    'zona': 'centro',
    'm2': 50,
    'm2_cubiertos': 50,
    'lat': -32.9545,
    'lon': -60.6455,
    'dormitorios': 2,
    'tipo': 'departamento',
    'estado_detalle': 'bueno',
    'calidad_edificio': 'media',
    'piso': 2,
    'total_pisos': 5
}

print("Running valuar_propiedad_v7...")
try:
    result = valuar_propiedad_v7(test_prop, '2026-01')
    print("EXEC_OK")
    
    keys_to_check = ['alquiler_estimado_ars', 'cap_rate_anual', 'fecha_mercado', 'valor_propiedad_usd', 'justificacion']
    for key in keys_to_check:
        if key in result:
            print(f"Key found: {key} = {result[key]}")
        else:
            print(f"❌ MISSING KEY: {key}")
            sys.exit(1)
            
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"EXEC_ERROR: {e}")
    sys.exit(1)
