
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
    'nombre': 'Mabel',
    'zona': 'Martin',
    'lat': -32.9541101,
    'lon': -60.6316406,
    'm2': 41,
    'm2_cubiertos': 41,
    'dormitorios': 1,
    'tipo': 'departamento',
}

try:
    res = valuar_propiedad_v7(test_prop, '2026-01')
    print(f"Resolution: {res['resolution_metadata']['resolution']}")
    print(f"Nodes found: {len(res['resolution_metadata']['nodes'])}")
    if len(res['resolution_metadata']['nodes']) > 0:
        print(f"First node ID: {res['resolution_metadata']['nodes'][0]['id']}")
    print("EXEC_OK")
except Exception as e:
    import traceback
    traceback.print_exc()
    print(f"ERROR: {e}")
