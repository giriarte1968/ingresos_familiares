import json, sys, os
sys.path.insert(0, r'C:\Users\Gustavo\ingresos_familiares_st')

with open('cache_scraping.json', encoding='utf-8') as f:
    data = json.load(f)
props = data.get('propiedades', [])

ayacucho = None
for p in props:
    if isinstance(p, dict) and 'Ayacucho' in p.get('nombre', ''):
        ayacucho = p
        break

if not ayacucho:
    print('No Ayacucho found, using first prop')
    for p in props:
        if isinstance(p, dict):
            ayacucho = p
            break

from jinja2 import Environment, FileSystemLoader
from xhtml2pdf import pisa

env = Environment(loader=FileSystemLoader(r'C:\Users\Gustavo\ingresos_familiares_st\templates'))
template = env.get_template('reporte_valuacion.html')

# Mock data for test
ctx = {
    'nombre': ayacucho.get('nombre', 'Test'),
    'direccion': ayacucho.get('direccion', 'Test 123'),
    'zona': ayacucho.get('zona', 'Centro'),
    'tipo_operacion': 'Venta',
    'tipo_inmueble': 'Departamento',
    'm2_eq': ayacucho.get('m2', 80),
    'dormitorios': ayacucho.get('dormitorios', 3),
    'anio_const': ayacucho.get('anio_construccion', 2010),
    'antiguedad': 15,
    'valor_total': '145,000',
    'v_cons': '130,000',
    'v_opt': '160,000',
    'vm2': '1,813',
    'vm2_cons': '1,625',
    'vm2_opt': '2,000',
    'n_comps': 9,
    'radio_m': 1000,
    'ventana_meses': 6,
    'm2_base': '1,813',
    'alquiler_ars': '450,000',
    'alquiler_usd': '450',
    'cap_rate': '3.7%',
    'factor_total': '1.03',
    'depreciacion': '0.90',
    'nlp_ajuste': '1.00',
    'calidad_edificio': '1.00',
    'cv_pool': '0.18',
    'percentil': '45',
    'razonamiento': 'Se compararon 9 departamentos de 2-3 dormitorios en un radio de 1000m. El valor mediano ajustado es de USD 1,813/m2. La zona presenta disponibilidad moderada de unidades similares.',
    'catastro': {'ph': '5555-A', 'anio': '2010', 'seccion': '01', 'grafico': '1234'},
    'tiene_activos': False,
    'activos': [],
    'total_activos': 0,
    'comparables': [
        {'direccion': 'Cordoba 1234', 'm2': 75, 'dormitorios': 3, 'precio_m2': 1850, 'precio': 138750, 'distancia_m': 350},
        {'direccion': 'Entre Rios 567', 'm2': 82, 'dormitorios': 3, 'precio_m2': 1780, 'precio': 145960, 'distancia_m': 520},
        {'direccion': 'Corrientes 890', 'm2': 70, 'dormitorios': 2, 'precio_m2': 1920, 'precio': 134400, 'distancia_m': 280},
    ],
    'fecha_generacion': '2026-07-27 16:00',
    'cache_version': 'anclas_v7_20260727',
}

html = template.render(**ctx)

# Save HTML for inspection
with open('test_report.html', 'w', encoding='utf-8') as f:
    f.write(html)

# Generate PDF
with open('test_report.pdf', 'wb') as out_f:
    pisa_status = pisa.CreatePDF(html, dest=out_f, encoding='utf-8')

if pisa_status.err:
    print(f'PDF generation errors: {pisa_status.err}')
else:
    print('PDF generated successfully: test_report.pdf')
    print(f'Size: {os.path.getsize("test_report.pdf")} bytes')
