import sys, os, json
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import _computar_vm2_core, obtener_mediana_cluster_v2

props_data = json.load(open('propiedades.json', 'r', encoding='utf-8'))
cochabamba = None
for p in props_data.get('propiedades', []):
    if 'cochabamba' in p.get('nombre', '').lower() or 'cochabamba' in p.get('direccion', '').lower():
        cochabamba = p
        break

print("=" * 80)
print("TESTING _computar_vm2_core FOR COCHABAMBA 45 (retro=0, flex=1):")
print("=" * 80)

# Run obtener_mediana_cluster_v2 with retro=0, flex=1
mediana, n, meta = obtener_mediana_cluster_v2('República de la Sexta', 4, operacion='venta', lat_ref=cochabamba['lat'], lon_ref=cochabamba['lon'], retro_dias=0, flex_dormitorios=1, m2_equiv=98.0)
print("Mediana devuelta por obtener_mediana_cluster_v2:", mediana)
