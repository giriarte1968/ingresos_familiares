import sys, os, json
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7, obtener_mediana_cluster_v2

props_data = json.load(open('propiedades.json', 'r', encoding='utf-8'))
cochabamba = None
for p in props_data.get('propiedades', []):
    if 'cochabamba' in p.get('nombre', '').lower():
        cochabamba = p
        break

mediana, n, meta = obtener_mediana_cluster_v2('República de la Sexta', 4, operacion='venta', lat_ref=cochabamba['lat'], lon_ref=cochabamba['lon'], retro_dias=0, flex_dormitorios=1, m2_equiv=98.0)
print(f"mediana={mediana}, n={n}, radio={meta.get('radio_usado')}m")
comps = meta.get('comparables_reales', [])
for i, c in enumerate(comps, 1):
    precio = c.get('precio', 0)
    m2 = c.get('m2', 0)
    pm2 = c.get('precio_m2', 0)
    dc = c.get('date_created', '')[:10]
    print(f" #{i:<2} | {c.get('direccion','?'):<45} | {c.get('dormitorios')}d | {m2}m2 | ${precio:>8,.0f} USD | ${pm2:>6.1f}/m2 | fecha={dc}")
