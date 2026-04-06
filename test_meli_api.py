import requests
url = 'https://api.mercadolibre.com/sites/MLA/search'
# State TU = Santa Fe. City TUxBQ1JPUzkyMmFk = Rosario
params = {
    'estado': 'TUxBU0NBUGw3M2E1',
    'ciudad': 'TUxBQ1JPUzkyMmFk',
    'category': 'MLA1459',
    'q': 'departamento venta rosario pichincha',
    'limit': 10
}
response = requests.get(url, params=params)
data = response.json()
print('Total results:', data.get('paging', {}).get('total', 0))
for i, item in enumerate(data.get('results', [])):
    print(f"{item.get('id')} - {item.get('title')} - {item.get('price')} {item.get('currency_id')}")
    for attr in item.get('attributes', []):
        if attr.get('id') in ['COVERED_AREA', 'TOTAL_AREA']:
            print(f"  {attr.get('id')}: {attr.get('value_name')}")
