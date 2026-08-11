import sys
sys.path.insert(0, '.')

from parsers.mercado_inmobiliario import valuar_propiedad_v7
from datetime import date

fecha_ref = date(2026, 7, 28)

# Test Ayacucho
prop_ay = {
    'nombre': 'Ayacucho 1234',
    'direccion': 'Ayacucho 1234',
    'lat': -32.9333,
    'lon': -60.6407,
    'dormitorios': 3,
    'm2_cubiertos': 85,
    'm2_descubiertos': 10,
    'tipo_inmueble': 'departamento',
    'descripcion_libre': 'Departamento en zona centro'
}

result_ay = valuar_propiedad_v7(prop_ay, fecha_ref)
print('=== Ayacucho 1234 ===')
print(f'  n_alquileres: {result_ay.get("n_alquileres", "N/A")}')
print(f'  m2_base_alquiler: {result_ay.get("m2_base_alquiler", "N/A")}')
print(f'  alquiler_estimado_ars: {result_ay.get("alquiler_estimado_ars", "N/A")}')
print(f'  metodo_alquiler: {result_ay.get("metodo_alquiler", "N/A")}')
print(f'  cap_rate: {result_ay.get("cap_rate", "N/A")}')
print(f'  confianza_alquiler: {result_ay.get("confianza_alquiler", "N/A")}')
print(f'  valor_venta: {result_ay.get("valor_venta", "N/A")}')
print(f'  m2_base_venta: {result_ay.get("m2_base_venta", "N/A")}')
print(f'  m2_equiv: {result_ay.get("m2_equiv", "N/A")}')
print()

# Test Mabel
prop_ma = {
    'nombre': 'Mabel',
    'direccion': 'Mabel Castellanos 3150',
    'lat': -32.9175,
    'lon': -60.6825,
    'dormitorios': 2,
    'm2_cubiertos': 60,
    'm2_descubiertos': 0,
    'tipo_inmueble': 'departamento',
    'descripcion_libre': 'Departamento en zona oeste'
}

result_ma = valuar_propiedad_v7(prop_ma, fecha_ref)
print('=== Mabel ===')
print(f'  n_alquileres: {result_ma.get("n_alquileres", "N/A")}')
print(f'  m2_base_alquiler: {result_ma.get("m2_base_alquiler", "N/A")}')
print(f'  alquiler_estimado_ars: {result_ma.get("alquiler_estimado_ars", "N/A")}')
print(f'  metodo_alquiler: {result_ma.get("metodo_alquiler", "N/A")}')
print(f'  cap_rate: {result_ma.get("cap_rate", "N/A")}')
print(f'  confianza_alquiler: {result_ma.get("confianza_alquiler", "N/A")}')
print(f'  valor_venta: {result_ma.get("valor_venta", "N/A")}')
print(f'  m2_base_venta: {result_ma.get("m2_base_venta", "N/A")}')
print(f'  m2_equiv: {result_ma.get("m2_equiv", "N/A")}')
print()

# Test Vera Mujica
prop_vm = {
    'nombre': 'Vera Mujica',
    'direccion': 'Vera Mujica 435',
    'lat': -32.9500,
    'lon': -60.6600,
    'dormitorios': 2,
    'm2_cubiertos': 70,
    'm2_descubiertos': 5,
    'tipo_inmueble': 'departamento',
    'descripcion_libre': 'Departamento en zona norte'
}

result_vm = valuar_propiedad_v7(prop_vm, fecha_ref)
print('=== Vera Mujica ===')
print(f'  n_alquileres: {result_vm.get("n_alquileres", "N/A")}')
print(f'  m2_base_alquiler: {result_vm.get("m2_base_alquiler", "N/A")}')
print(f'  alquiler_estimado_ars: {result_vm.get("alquiler_estimado_ars", "N/A")}')
print(f'  metodo_alquiler: {result_vm.get("metodo_alquiler", "N/A")}')
print(f'  cap_rate: {result_vm.get("cap_rate", "N/A")}')
print(f'  confianza_alquiler: {result_vm.get("confianza_alquiler", "N/A")}')
print(f'  valor_venta: {result_vm.get("valor_venta", "N/A")}')
print(f'  m2_base_venta: {result_vm.get("m2_base_venta", "N/A")}')
print(f'  m2_equiv: {result_vm.get("m2_equiv", "N/A")}')
