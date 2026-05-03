import json
from parsers.mercado_inmobiliario import (
    calcular_base_calibrada, calcular_m2_equivalentes, calcular_factores,
    valuar_propiedad_v7, obtener_mediana_cluster
)

# Cargar propiedad P1200
data = json.load(open('propiedades.json', 'r', encoding='utf-8'))
p1200 = [p for p in data['propiedades'] if p.get('id') == 'prop_b8ec28ba'][0]

print("=== P1200 raw ===")
print(f"m2: {p1200.get('m2')}")
print(f"m2_cubiertos: {p1200.get('m2_cubiertos')}")
print(f"m2_semicubiertos: {p1200.get('m2_semicubiertos')}")
print(f"m2_descubiertos: {p1200.get('m2_descubiertos')}")
print(f"zona: {p1200.get('zona')}")
print(f"ancla: {p1200.get('ancla_mas_cercana')}")
print(f"ancla_usd_m2: {p1200.get('ancla_usd_m2')}")
print(f"lat: {p1200.get('lat')}, lon: {p1200.get('lon')}")
print(f"estado: {p1200.get('estado_detalle')}")
print(f"calidad: {p1200.get('calidad_edificio')}")
print(f"piso: {p1200.get('piso')}, total_pisos: {p1200.get('total_pisos')}")
print(f"dormitorios: {p1200.get('dormitorios')}")
print(f"antiguedad: {2026 - p1200.get('anio_construccion', 1977)}")
print(f"balcon: {p1200.get('balcon')}, tipo_balcon: {p1200.get('tipo_balcon')}")
print(f"vista: {p1200.get('vista')}")
print(f"doble_ingreso: {p1200.get('doble_ingreso')}")
print(f"lavadero: {p1200.get('lavadero_independiente')}")
print(f"toilet: {p1200.get('toilet')}")
print(f"reciclado: {p1200.get('reciclado')}")
print(f"layout_flexible: {p1200.get('layout_flexible')}")

# Calcular m2 equivalentes
m2_equiv = calcular_m2_equivalentes(p1200)
print(f"\n=== m2 equivalentes: {m2_equiv}")

# Calcular factores
factores = calcular_factores(p1200)
print(f"=== Factores ===")
for k, v in factores.items():
    print(f"  {k}: {v}")

# Calcular base calibrada
valor_ancla = p1200.get('ancla_usd_m2', 1580)
prop_data = {
    'zona': p1200.get('zona'),
    'dormitorios': p1200.get('dormitorios'),
    'lat': p1200.get('lat'),
    'lon': p1200.get('lon'),
    'anio_construccion': p1200.get('anio_construccion')
}
m2_base, metodo = calcular_base_calibrada(valor_ancla, prop_data)
print(f"\n=== Base Calibrada ===")
print(f"  valor_ancla_input: {valor_ancla}")
print(f"  m2_base: {m2_base}")
print(f"  metodo: {metodo}")

# Ver cluster
zona = p1200.get('zona')
dorms = p1200.get('dormitorios')
cluster_val, n = obtener_mediana_cluster(zona, dorms, 'venta')
print(f"\n=== Cluster {zona} {dorms} dorm ===")
print(f"  mediana cluster: {cluster_val}, muestras: {n}")

# Resultado final
result = valuar_propiedad_v7(p1200)
print(f"\n=== Resultado v7 ===")
print(f"  valor_lista: {result['valor_propiedad_usd']}")
print(f"  valor_cierre: {result['valor_realizable_usd']}")
print(f"  m2_base_venta: {result.get('m2_base_venta')}")
print(f"  m2_equiv: {result.get('m2_equivalentes')}")
print(f"  m2_efectivo: {result.get('valor_m2_actual_usd')}")
print(f"  nlp: {result.get('nlp_ajuste_pct')}%")

print(f"\n=== Cálculo manual ===")
print(f"  {m2_equiv} * {m2_base} * {factores['total']:.4f} = {m2_equiv * m2_base * factores['total']:.0f}")
