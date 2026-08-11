import json

with open('data/valuaciones_cache.json', encoding='utf-8') as f:
    cache = json.load(f)

# Check full result_completo for detailed alquiler info
for prop_name in ['Ayacucho', 'Mabel', 'Vera Mujica']:
    data = cache.get(prop_name)
    if data:
        r = data.get('resultado_completo', {})
        print(f'=== {prop_name} ===')
        print(f'  alquiler_estimado_ars: {r.get("alquiler_estimado_ars", "N/A")}')
        print(f'  alquiler_min_ars: {r.get("alquiler_min_ars", "N/A")}')
        print(f'  alquiler_max_ars: {r.get("alquiler_max_ars", "N/A")}')
        print(f'  metodo_alquiler: {r.get("metodo_alquiler", "N/A")}')
        print(f'  cap_rate: {r.get("cap_rate", "N/A")}')
        print(f'  n_alquileres: {r.get("n_alquileres", "N/A")}')
        print(f'  confianza_alquiler: {r.get("confianza_alquiler", r.get("confianza_alq", "N/A"))}')
        print(f'  m2_base_alquiler: {r.get("m2_base_alquiler", "N/A")}')
        print(f'  m2_base_alq_raw: {r.get("m2_base_alq_raw", "N/A")}')
        print(f'  m2_base_venta: {r.get("m2_base_venta", "N/A")}')
        print(f'  m2_equiv: {r.get("m2_equiv", "N/A")}')
        print(f'  valor_venta: {r.get("valor_venta", "N/A")}')
        print(f'  valor_propiedad_usd: {r.get("valor_propiedad_usd", "N/A")}')
        print(f'  n_propiedades: {r.get("n_propiedades", "N/A")}')
        print(f'  resolution: {r.get("resolution", "N/A")}')
        print(f'  confidence: {r.get("confidence", "N/A")}')
        print(f'  percentil_usado: {r.get("percentil_usado", "N/A")}')
        print(f'  factores_alquiler: {r.get("factores_alquiler", "N/A")}')
        print(f'  GAP_ALQUILER: {r.get("GAP_ALQUILER", "N/A")}')
        print()
