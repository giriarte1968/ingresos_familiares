import sys, os, json
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7, obtener_mediana_cluster_v2

props_data = json.load(open('propiedades.json', 'r', encoding='utf-8'))
cochabamba = None
for p in props_data.get('propiedades', []):
    if 'cochabamba' in p.get('nombre', '').lower() or 'cochabamba' in p.get('direccion', '').lower():
        cochabamba = p
        break

def inspect_run(label, retro_dias, flex_dormitorios):
    print("=" * 90)
    print(f"DIAGNOSTICO: {label} (retro_dias={retro_dias}, flex_dormitorios={flex_dormitorios})")
    print("=" * 90)
    res = valuar_propiedad_v7(cochabamba, retro_dias=retro_dias, flex_dormitorios=flex_dormitorios)
    print(f"VALOR PROPIEDAD USD: ${res.get('valor_propiedad_usd'):,.0f} USD" if res.get('valor_propiedad_usd') else "VALOR PROPIEDAD: None")
    print(f"m2_microzona: ${res.get('m2_microzona')}" if res.get('m2_microzona') else "m2_microzona: None")
    
    meta = res.get('resolution_metadata', {})
    comps = meta.get('comparables_reales', [])
    print(f"N Comparables devueltos: {len(comps)} (radio: {meta.get('radio_usado')}m)")
    print("-" * 90)
    for i, c in enumerate(comps, 1):
        print(f" #{i:<2} | {c.get('direccion','?'):<35} | {c.get('dormitorios')}d | {c.get('m2')}m2 | ${c.get('precio',0):>8,.0f} USD | ${c.get('precio_m2',0):>6.1f}/m2 | Ct={c.get('time_adjustment',1):.3f} | dist={c.get('distancia_m')}m | {c.get('date_created','')[:10]}")

inspect_run("CASO A: UI RETRO 12 MESES + ALL FLEX (retro=12, flex=[1,2,3,4,5])", retro_dias=12, flex_dormitorios=[1,2,3,4,5])
inspect_run("CASO B: SIMULACION SIN RETRO + FLEX=1 (retro=0, flex=1)", retro_dias=0, flex_dormitorios=1)
