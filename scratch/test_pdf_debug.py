import sys, os, json, traceback
sys.path.insert(0, r'C:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'C:\Users\Gustavo\ingresos_familiares_st')

with open('propiedades.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
props = data.get('propiedades', [])
print(f'Total propiedades: {len(props)}')
for p in props[:3]:
    print(f'  - {p.get("nombre", "?")}')

if props:
    p = props[0]
    nombre = p.get("nombre", "?")
    print(f'Generando PDF para: {nombre}')
    from valu_detail_sections import generar_reporte_pdf
    res = {
        'valor_propiedad_usd': 120000,
        'manual_params': {},
        'alquiler_estimado_ars': 500000,
        'usdt_ars': 1480,
        'cap_rate': 0.05,
        'm2_base_venta': 1500,
        'comparables_venta': [
            {'direccion': 'Test St 123', 'm2': 80, 'dormitorios': 2, 'precio_m2': 1500,
             'precio': 120000, 'distancia_m': 300, 'fuente': 'ZP'},
        ] * 10,
        'resolution_metadata': {'n_propiedades': 10, 'radio_usado': 1000},
        'valor_venta_conservador': 108000,
        'valor_venta_optimista': 132000,
        'factor_total': 1.05,
        'delta_anti': 0.97,
        'nlp_ajuste': 0.02,
    }
    try:
        pdf = generar_reporte_pdf(p, res)
        with open('test_report_debug.pdf', 'wb') as f:
            f.write(pdf)
        print(f'PDF generado: {len(pdf)} bytes -> test_report_debug.pdf')
    except Exception as e:
        traceback.print_exc()
