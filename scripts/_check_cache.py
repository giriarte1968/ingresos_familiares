import json
cache = json.load(open('data/valuaciones_cache.json', 'r', encoding='utf-8'))
for k in ['Ayacucho 1800', 'Mabel', 'P1200', 'Entre Rios', 'Vera Mujica', 'Ayacucho']:
    res = cache.get(k, {})
    print(f"\n{k}:")
    for field in ['m2_base_alquiler', 'n_alquileres', 'alquiler_estimado_ars', 'valor_venta', 'cap_rate', 'metodo_alquiler']:
        print(f"  {field}: {res.get(field)}")
