"""
GENERAR FACTORES FLEX_DORM EMPIRICOS POR MACROZONA
==================================================
Calcula el ratio real de $/m2 entre tipologias de dormitorios
para cada macrozona, usando las 16.427 ventas validas del cache.

Guarda los resultados en data/flex_dorm_factors.json
"""

import sys, os, json
from collections import defaultdict

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

import warnings
warnings.filterwarnings('ignore')

from parsers.zonas_manager import resolver_macrozona
from parsers.mercado_inmobiliario import normalizar_zona

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

ventas = [p for p in cache['propiedades']
          if p.get('operacion') == 'venta'
          and 300 < p.get('valor_m2', 0) < 6000
          and 20 < p.get('m2', 0) < 400
          and p.get('lat') and p.get('lon')
          and p.get('dormitorios') in [1, 2, 3, 4]]

print(f"Ventas para analisis: {len(ventas)}")

# Agrupar por macrozona y dormitorios
grupos = defaultdict(lambda: defaultdict(list))

for p in ventas:
    lat, lon = p.get('lat'), p.get('lon')
    zona = p.get('zona', '') or ''
    try:
        _mz = resolver_macrozona({'zona': normalizar_zona(zona) or '', 'lat': lat, 'lon': lon})
        mz = _mz.get('macrozona_id')
    except:
        mz = None
    if not mz:
        continue
    grupos[mz][int(p['dormitorios'])].append(float(p['valor_m2']))

def p50(l):
    if not l: return None
    s = sorted(l)
    return s[int(len(s) * 0.50)]

# Min samples para considerar fiable una estimacion
MIN_N = 15

# Global como fallback
all_vm2 = defaultdict(list)
for p in ventas:
    all_vm2[int(p['dormitorios'])].append(float(p['valor_m2']))
p50_global = {d: p50(all_vm2[d]) for d in [1,2,3,4]}

# Para cada macrozona, calcular ratio_vs_2d
# ratio[d] = p50_d / p50_2d  (cuanto vale d respecto a 2d en la misma zona)
# factor_flex(suj, comp) = ratio[suj] / ratio[comp]
# -> si suj=4d y comp=2d: ratio[4] / ratio[2] = 0.75 / 1.0 = 0.75 -> comp cuesta 33% mas -> bajar comp

output = {}

for mz in sorted(grupos.keys()):
    g = grupos[mz]
    ratios = {}
    
    # Calcular p50 por dormitorio en esta zona
    p50_per_d = {}
    for d in [1, 2, 3, 4]:
        if len(g.get(d, [])) >= MIN_N:
            p50_per_d[d] = p50(g[d])
    
    # Necesitamos al menos 2d como referencia con N suficiente
    # Si no hay suficiente 2d local, usar ratio global como fallback
    ref_2d = p50_per_d.get(2)
    if not ref_2d:
        # Fallback: usar el ratio global calibrado a precio local
        # Estimamos via el mejor dorm disponible
        for d_ref in [3, 1]:
            if d_ref in p50_per_d and p50_global.get(d_ref) and p50_global.get(2):
                scale = p50_per_d[d_ref] / p50_global[d_ref]
                ref_2d = p50_global[2] * scale
                break
    
    if not ref_2d:
        continue
    
    for d in [1, 2, 3, 4]:
        local_p50 = p50_per_d.get(d)
        if local_p50 and ref_2d:
            ratios[d] = round(local_p50 / ref_2d, 4)
        elif p50_global.get(d) and p50_global.get(2):
            # Fallback al ratio global
            ratios[d] = round(p50_global[d] / p50_global[2], 4)
    
    n_total = sum(len(g.get(d, [])) for d in [1,2,3,4])
    n_per_d = {d: len(g.get(d, [])) for d in [1,2,3,4]}
    
    output[mz] = {
        'ratios_vs_2d': ratios,
        'n': n_total,
        'n_per_dorm': n_per_d,
        'p50_per_dorm': {str(d): round(p50_per_d[d]) if d in p50_per_d else None for d in [1,2,3,4]},
    }
    print(f"{mz:<22}: n={n_total:>5} ratios={ratios}")

# Agregar fallback global
global_ratios = {d: round(p50_global[d] / p50_global[2], 4) if p50_global.get(d) and p50_global.get(2) else None for d in [1,2,3,4]}
output['_global'] = {
    'ratios_vs_2d': global_ratios,
    'n': len(ventas),
    'descripcion': 'Fallback global para macrozonas sin datos suficientes',
}
print(f"\n{'_global':<22}: ratios={global_ratios}")

# Guardar
os.makedirs('data', exist_ok=True)
with open('data/flex_dorm_factors.json', 'w', encoding='utf-8') as f:
    json.dump({'version': '1.0', 'fuente': 'cache_scraping_16427_ventas', 'data': output}, f, indent=2, ensure_ascii=False)

print(f"\nGuardado en data/flex_dorm_factors.json")
print(f"Macrozonas con factores empiricos: {len([k for k in output if not k.startswith('_')])}")
