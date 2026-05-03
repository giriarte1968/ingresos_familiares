import json
from parsers.mercado_inmobiliario import sanitizar_propiedad, calcular_factores

# Cargar propiedad P1200
data = json.load(open('propiedades.json', 'r', encoding='utf-8'))
p1200 = [p for p in data['propiedades'] if p.get('id') == 'prop_b8ec28ba'][0]

print("=== ANTES de sanitizar ===")
print(f"anio_construccion: {p1200.get('anio_construccion')}")
print(f"antiguedad: {p1200.get('antiguedad')}")

prop = sanitizar_propiedad(p1200)

print("\n=== DESPUÉS de sanitizar ===")
print(f"anio_construccion: {prop.get('anio_construccion')}")
print(f"antiguedad: {prop.get('antiguedad')}")

# Calcular antiguedad dinamica
anio = prop.get('anio_construccion', 2020)
antiguedad_calc = 2026 - anio
print(f"\n=== CÁLCULO ===")
print(f"anio_construccion: {anio}")
print(f"antiguedad (2026-{anio}): {antiguedad_calc}")

# Ahora setear y calcular factores
prop['antiguedad'] = antiguedad_calc
factores = calcular_factores(prop)

print(f"\n=== FACTORES ===")
for k, v in factores.items():
    print(f"  {k}: {v}")