import json
import math
import numpy as np
from collections import defaultdict
import sys, os

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.zonas_manager import resolver_macrozona
from parsers.mercado_inmobiliario import normalizar_zona

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

props = cache.get('propiedades', [])
print(f"Total propiedades en cache: {len(props)}")

grouped = defaultdict(list)
global_by_dorm = defaultdict(list)
all_sales = []

for p in props:
    if p.get('operacion') != 'venta':
        continue
    vm2 = p.get('valor_m2', 0)
    m2 = p.get('m2', 0)
    lat = p.get('lat')
    lon = p.get('lon')
    dorms = p.get('dormitorios', 1)
    
    if not (20 < m2 < 500 and 200 < vm2 < 10000 and lat and lon):
        continue
        
    try:
        lat_f, lon_f = float(lat), float(lon)
    except:
        continue
        
    mz_info = resolver_macrozona({'lat': lat_f, 'lon': lon_f, 'zona': normalizar_zona(p.get('zona', '')) or ''})
    mz = mz_info.get('macrozona_id') if isinstance(mz_info, dict) else mz_info
    if not mz:
        mz = '_global'
        
    d_cat = min(max(int(dorms or 1), 1), 4)
    log_m2 = math.log(m2)
    log_vm2 = math.log(vm2)
    
    grouped[(mz, d_cat)].append((log_m2, log_vm2))
    grouped[(mz, 'all')].append((log_m2, log_vm2))
    global_by_dorm[d_cat].append((log_m2, log_vm2))
    all_sales.append((log_m2, log_vm2))

def fit_beta(points):
    if len(points) < 5:
        return None, len(points)
    xs = np.array([pt[0] for pt in points])
    ys = np.array([pt[1] for pt in points])
    cov = np.cov(xs, ys)
    if cov[0, 0] == 0:
        return None, len(points)
    beta = cov[0, 1] / cov[0, 0]
    return float(beta), len(points)

beta_global_all, n_all = fit_beta(all_sales)
print(f"Beta GLOBAL all: {beta_global_all:.4f} (N={n_all})")

beta_globals_by_dorm = {}
for d in [1, 2, 3, 4]:
    b, n = fit_beta(global_by_dorm[d])
    beta_globals_by_dorm[d] = b
    print(f"Beta GLOBAL dorm={d}: {b:.4f} (N={n})")

macrozones = set(k[0] for k in grouped.keys())
beta_matrix = {}

for mz in sorted(macrozones):
    beta_matrix[mz] = {}
    b_mz_all, n_mz_all = fit_beta(grouped[(mz, 'all')])
    beta_matrix[mz]['all'] = b_mz_all if b_mz_all is not None else beta_global_all
    
    for d in [1, 2, 3, 4]:
        b_d, n_d = fit_beta(grouped[(mz, d)])
        print(f"  MZ={mz}, dorm={d}: beta={b_d if b_d else 'N/A'} (N={n_d})")
        if b_d is not None and n_d >= 15:
            beta_matrix[mz][str(d)] = b_d
        else:
            beta_matrix[mz][str(d)] = b_mz_all if b_mz_all is not None else beta_globals_by_dorm[d]

beta_matrix['_global'] = {'all': beta_global_all}
for d in [1, 2, 3, 4]:
    beta_matrix['_global'][str(d)] = beta_globals_by_dorm[d]

output = {
    'version': 'v1_continuous',
    'beta_global_all': beta_global_all,
    'beta_globals_by_dorm': beta_globals_by_dorm,
    'macrozonas': beta_matrix
}

os.makedirs('data', exist_ok=True)
with open('data/sa_continuous.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2)

print("\nGuardado exitosamente en data/sa_continuous.json")
