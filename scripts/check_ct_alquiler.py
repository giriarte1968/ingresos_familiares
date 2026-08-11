import json

with open('data/zonas_depreciacion.json', encoding='utf-8') as f:
    data = json.load(f)

print("=== CT ALQUILER RATES BY MACROZONA ===")
for mz in data.get('macrozonas', []):
    mz_id = mz.get('id', 'N/A')
    ct_rate = mz.get('ct_alquiler_rate', 'N/A')
    ct_by_dorm = mz.get('ct_alquiler_by_dormitorios', 'N/A')
    print(f"{mz_id}: ct_alquiler_rate={ct_rate}, by_dorm={ct_by_dorm}")

# Verify CT calculation for centro_premium
print()
print("=== VERIFICACIÓN CT ALQUILER PARA centro_premium ===")
ct_rate = 0.3014  # Expected rate
meses = 8.28
ct = (1.0 + ct_rate) ** (meses / 12.0)
print(f"CT rate: {ct_rate}")
print(f"Meses: {meses}")
print(f"CT calculado: {ct:.4f}")
print(f"CT esperado (del debug): 1.4109")
print(f"Diferencia: {abs(ct - 1.4109):.4f}")
