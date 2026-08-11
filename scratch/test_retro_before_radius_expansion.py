import sys, os, json
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7, obtener_mediana_cluster_v2

# Modify obtener_mediana_cluster_v2 logic locally to test:
# If n_same < 5 within 500m/800m in 180d, expand date filter to 60m before expanding radius to 1000m!

props_data = json.load(open('propiedades.json', 'r', encoding='utf-8'))
cochabamba = None
for p in props_data.get('propiedades', []):
    if 'cochabamba' in p.get('nombre', '').lower():
        cochabamba = p
        break

mediana, n, meta = obtener_mediana_cluster_v2('República de la Sexta', 4, operacion='venta', lat_ref=cochabamba['lat'], lon_ref=cochabamba['lon'], retro_dias=60, flex_dormitorios=1, m2_equiv=98.0)
print(f"Retro=60, flex=1 -> mediana=${mediana:,.2f}/m2 (${mediana*98:,.0f} USD), n_comps={n}")
