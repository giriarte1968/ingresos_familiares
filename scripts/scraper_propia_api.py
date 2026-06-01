import json
from datetime import datetime
import time
import urllib.parse
from playwright.sync_api import sync_playwright

def scrapear_propia_api(max_pages=20, limit=100, output_file=None):
    print('='*60)
    print('SCRAPING PROPIA API VIA PLAYWRIGHT (Clean)')
    print('='*60)
    
    base_url = 'https://admin.propia.com.ar/items/properties'
    operaciones = [{'id': '1', 'nombre': 'venta'}, {'id': '2', 'nombre': 'alquiler'}]
    tipos = [{'id': '2', 'nombre': 'departamento'}, {'id': '1', 'nombre': 'casa'}, {'id': '3', 'nombre': 'ph'}]
    fields = [
        'id', 'title', 'slug', 'address', 'address_to_show', 'address_summary',
        'price', 'hide_price', 'area', 'bedrooms', 'bathrooms', 'garages',
        'expenses', 'environment_amount', 'monoambiente', 'latitude', 'longitude',
        'type_id.id', 'type_id.name', 'operation_id.id', 'operation_id.name',
        'currency_id.id', 'currency_id.symbol', 'date_created', 'date_updated'
    ]
    
    all_props = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36')
        page = context.new_page()
        page.goto('https://propia.com.ar', timeout=30000)
        page.wait_for_timeout(2000)
        
        for op in operaciones:
            for tipo in tipos:
                print('Scrapeando ' + op['nombre'] + ' - ' + tipo['nombre'] + '...')
                filtro = {
                    'status': 'published', 'published_on_portal': True,
                    '_and': [{'company_id': {'enabled': {'_eq': True}}}],
                    'operation_id': op['id'], 'type_id': tipo['id'], 'location_city_id': '1'
                }
                filtro_json = json.dumps(filtro)
                for page_num in range(1, max_pages + 1):
                    params = 'limit=' + str(limit) + '&page=' + str(page_num) + '&meta=filter_count,total_count&sort=-ranking,sort&filter=' + urllib.parse.quote(filtro_json)
                    for f in fields: params += '&fields=' + urllib.parse.quote(f)
                    url = base_url + '?' + params
                    try:
                        response_text = page.evaluate('async (u) => { const res = await fetch(u); return res.text(); }', url)
                        data = json.loads(response_text)
                        items = data.get('data', [])
                        if not items: break
                        print('  Pág ' + str(page_num) + ': ' + str(len(items)) + ' propiedades')
                        for item in items:
                            precio = item.get('price')
                            area = item.get('area')
                            if precio is None or area is None or float(area) <= 0: continue
                            
                            val_m2 = float(precio) / float(area)
                            op_name = item.get('operation_id', {}).get('name', op['nombre']).lower()
                            if op_name == 'venta' and (val_m2 < 400 or val_m2 > 5000):
                                continue

                            all_props.append({
                                'precio': float(precio),
                                'm2': float(area),
                                'dormitorios': item.get('bedrooms') or 1,
                                'tipo': item.get('type_id', {}).get('name', tipo['nombre']),
                                'operacion': item.get('operation_id', {}).get('name', op['nombre']).lower(),
                                'direccion': item.get('address_to_show') or item.get('title') or '',
                                'url': 'https://propia.com.ar/propiedades/' + item.get('slug', ''),
                                'valor_m2': round(float(precio) / float(area), 2),
                                'fuente': 'propia_api_browser',
                                'id_propia': item.get('id'),
                                'date_created': item.get('date_created'),
                                'date_updated': item.get('date_updated'),
                                'latitude': item.get('latitude'),
                                'longitude': item.get('longitude')
                            })
                        if len(items) < limit: break
                        page.wait_for_timeout(500)
                    except Exception as e:
                        print('  Error en pág ' + str(page_num) + ': ' + str(e))
                        break
        browser.close()
    unique_props = {p['id_propia']: p for p in all_props}.values()
    unique_list = list(unique_props)
    output = {
        'fecha': datetime.now().isoformat(),
        'fuente': 'propia_api_browser',
        'total': len(unique_list),
        'venta': len([p for p in unique_list if p['operacion'] == 'venta']),
        'alquiler': len([p for p in unique_list if p['operacion'] == 'alquiler']),
        'propiedades': unique_list
    }
    if output_file is None:
        output_file = r'C:\Users\Gustavo\ingresos_familiares_st\propia.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print('\\n' + '='*60 + '\\nRESULTADO FINAL: ' + str(len(unique_list)) + ' propiedades\\n  Venta: ' + str(output['venta']) + '\\n  Alquiler: ' + str(output['alquiler']) + '\\nOutput: ' + output_file + '\\n' + '='*60)
    return unique_list

if __name__ == '__main__':
    scrapear_propia_api(max_pages=50, limit=100)
