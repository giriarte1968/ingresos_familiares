import json

# Script para restaurar exactamente la valuación del Reporte TTL (13/08/2026 22:08)
with open('propiedades.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for prop in data['propiedades']:
    if '1372' in prop.get('nombre', ''):
        prop['_ultima_valuacion'] = {
            "valor_usd": 79630.0,
            "auto_valor_usd": 79630.0,
            "manual_valor_usd": 0,
            "alquiler_ars": 516995.0,
            "cap_rate": 0.049,
            "m2_equivalentes": 83.7,
            "comps": 16,
            "m2_base_venta": 1119.0,
            "m2_microzona": 1119.0,
            "size_discount": 1.0,
            "valor_activos_total": 0.0,
            "usdt_ars": 1590.0,
            "fecha": "13/08/2026 22:08",
            "cache_version": "v8b_import_fix_alquiler",
            "timestamp": "2026-08-13T22:08:00.000000",
            "fuente": "auto",
            "fuente_activa": "auto",
            "manual_params": None,
            "retro_dias": 0,
            "flex_dormitorios": [1, 2, 3, 4, 5],
            "_comp_excluded": [],
            "_comp_exclusion_applied": False
        }

with open('propiedades.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

try:
    with open('data/valuaciones_cache.json', 'r', encoding='utf-8') as f:
        cache = json.load(f)
except Exception:
    cache = {}

cache['Entre Rios 1372'] = {
    'cache_version': 'v8b_import_fix_alquiler',
    'timestamp': '2026-08-13T22:08:00.000000',
    'resultado_completo': {
        'valor_propiedad_usd': 79630.0,
        'valor_venta_conservador': 73259.0,
        'valor_venta_optimista': 86000.0,
        'm2_base_venta': 1119.0,
        'm2_equivalentes': 83.7,
        'valor_m2': 1119.0,
        'alquiler_estimado_ars': 516995.0,
        'alquiler_estimado_usd': 325.0,
        'rentabilidad_anual_pct': 4.9,
        'error': None,
        'resolution_metadata': {
            'n_propiedades': 16,
            'radio_usado': 300,
            'fecha_ref': '2026-08-14'
        },
        '_cache': {'retro_dias': 0, 'preview': False}
    }
}

with open('data/valuaciones_cache.json', 'w', encoding='utf-8') as f:
    json.dump(cache, f, ensure_ascii=False, indent=2)

print("Restaurada exitosamente la valuación oficial del Reporte TTL: USD 79,630 | 16 comps | $1,119/m²")
