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

print("=" * 80)
print("TESTING COCHABAMBA 45 WITH AUTOMATIC RETRO EXPANSION FOR RARE TIPOLOGY:")
print("=" * 80)

# Check how many 4d comps exist in 180d within 800m
mediana, n, meta = obtener_mediana_cluster_v2('República de la Sexta', 4, operacion='venta', lat_ref=cochabamba['lat'], lon_ref=cochabamba['lon'], retro_dias=0, flex_dormitorios=1, m2_equiv=98.0)
print(f"Default retro=0, flex=1 -> mediana=${mediana:,.2f}/m2 (${mediana*98:,.0f} USD), comps={n}, radio={meta.get('radio_usado')}m")

# Check with retro=36 or retro=60
mediana60, n60, meta60 = obtener_mediana_cluster_v2('República de la Sexta', 4, operacion='venta', lat_ref=cochabamba['lat'], lon_ref=cochabamba['lon'], retro_dias=60, flex_dormitorios=1, m2_equiv=98.0)
print(f"Retro=60, flex=1 -> mediana=${mediana60:,.2f}/m2 (${mediana60*98:,.0f} USD), comps={n60}, radio={meta60.get('radio_usado')}m")
