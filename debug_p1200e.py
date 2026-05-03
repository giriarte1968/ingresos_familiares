import json

# Simular lo que hace valuar_propiedad_v7
data = json.load(open('propiedades.json', 'r', encoding='utf-8'))
p1200 = [p for p in data['propiedades'] if p.get('id') == 'prop_b8ec28ba'][0]

# Valores conocidos
m2_equiv = 88.85
m2_base_v7 = 1435.14  # Lo que retorna v7
factor_v7 = 1.4027  # Lo que usa v7

# Cálculo v7
valor_v7 = m2_equiv * m2_base_v7 * factor_v7
print(f"v7: {m2_equiv} × {m2_base_v7} × {factor_v7} = {valor_v7:.0f}")

# Pero mi cálculo manual usa:
m2_base_manual = 1514.21
factor_manual = 0.9903  # incluye depreciación

valor_manual = m2_equiv * m2_base_manual * factor_manual
print(f"manual: {m2_equiv} × {m2_base_manual} × {factor_manual} = {valor_manual:.0f}")

# El problema: m2_base_v7 * factor_v7 vs m2_base_manual * factor_manual
# 1435.14 * 1.4027 = 2013  
# 1514.21 * 0.9903 = 1499

print(f"\nDifferential:")
print(f"v7: {m2_base_v7 * factor_v7:.2f}")
print(f"manual: {m2_base_manual * factor_manual:.2f}")