import json, time, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.motor_vpp_core import valuar_con_cache

d = json.load(open("propiedades.json", encoding="utf-8"))
prop = [p for p in d["propiedades"] if p.get("nombre") == "Cochabamba 45"][0]

print(f"Property: Cochabamba 45")
print(f"  Lat: {prop.get('lat')}, Lon: {prop.get('lon')}")
print(f"  Type: {prop.get('type_property')}, Dorms: {prop.get('dormitorios')}, m2: {prop.get('m2')}")
print(f"  Year/Antiquity: {prop.get('antiquity')}")
print()

t0 = time.time()
try:
    result = valuar_con_cache(
        prop=prop,
        forzar_recalculo=True,
        retro_dias=60,
        flex_dormitorios=[4, 5, 6],
    )
    elapsed = time.time() - t0
    print(f"Time: {elapsed:.1f}s")
    print(f"n_comps: {result.get('n_comps')}")
    print(f"vm2: {result.get('vm2')}")
    print(f"valor: {result.get('valor')}")
    print(f"fuente: {result.get('fuente')}")
    print(f"cluster: {result.get('cluster_name', result.get('cluster', '?'))}")
    print(f"barreras: {result.get('tiene_barreras')}")
    print(f"zona: {result.get('zona')}")
    print(f"ancla: {result.get('ancla_usada', result.get('ancla', '?'))}")
    if "selected_comps" in result:
        print(f"selected_comps: {len(result['selected_comps'])}")
        for c in result['selected_comps'][:5]:
            print(f"  {c.get('address', c.get('fuente', '?'))} - ${c.get('precio_m2', c.get('usd_m2', '?'))}/m2")
    if "error" in result:
        print(f"ERROR: {result['error']}")
except Exception as e:
    import traceback
    print(f"EXCEPTION: {e}")
    traceback.print_exc()
