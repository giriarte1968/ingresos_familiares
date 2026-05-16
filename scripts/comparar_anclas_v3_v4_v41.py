"""
Compara valores de anclas entre v3 (manual), v4 (cluster_v2) y v4.1 (zonal P50).
Genera reports/anclas_comparacion_v3_v4_v41.csv

Uso: python scripts/comparar_anclas_v3_v4_v41.py
"""
import json, os, sys, csv, math
import numpy as np

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

REPORTS_DIR = os.path.join(BASE, 'reports')
os.makedirs(REPORTS_DIR, exist_ok=True)

# ─── CARGAR V3 ───
with open(os.path.join(BASE, 'anclas_rosario_v3_grid.json'), 'r', encoding='utf-8') as f:
    v3_raw = json.load(f)['anclas']

# ─── CARGAR V4 (generada antes) ───
v4_path = os.path.join(BASE, 'data', 'anclas_rosario_v4_propuesta.json')
v4_dict = {}
if os.path.exists(v4_path):
    with open(v4_path, 'r', encoding='utf-8') as f:
        v4_data = json.load(f)
    for a in v4_data['anclas']:
        v4_dict[a['id']] = a['usd_m2']

# ─── CARGAR SCRAPING ───
cache_path = os.path.join(BASE, 'cache_scraping.json')
with open(cache_path, 'r', encoding='utf-8') as f:
    cache = json.load(f)
props = cache.get('propiedades', [])
print(f"Propiedades totales en cache: {len(props)}")

def dist_km(l1, n1, l2, n2):
    R = 6371
    la1, lo1, la2, lo2 = map(math.radians, [l1, n1, l2, n2])
    dlat, dlon = la2 - la1, lo2 - lo1
    a = math.sin(dlat/2)**2 + math.cos(la1)*math.cos(la2)*math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def calcular_valor_zonal(lat, lon, radio_m=500):
    """
    Calcula el P50 de precio/m² para propiedades de venta
    dentro de un radio de la ancla.
    Sin filtro de dormitorios, edad ni tipo.
    """
    cercanas = []
    for p in props:
        op = str(p.get('operacion', '')).lower()
        if 'venta' not in op:
            continue
        if not p.get('lat') or not p.get('lon'):
            continue
        try:
            d = dist_km(lat, lon, float(p['lat']), float(p['lon'])) * 1000
        except:
            continue
        if d > radio_m:
            continue
        precio = p.get('precio_usd', p.get('precio', 0))
        m2 = p.get('sup_total', p.get('m2', 0))
        try:
            precio, m2 = float(precio), float(m2)
        except:
            continue
        if precio <= 0 or m2 <= 0:
            continue
        cercanas.append(precio / m2)
    
    if len(cercanas) < 20:
        return None, len(cercanas), cercanas
    
    # IQR filter
    arr = np.array(cercanas)
    q1, q3 = np.percentile(arr, [25, 75])
    iqr = q3 - q1
    limpios = [v for v in cercanas if q1 - 1.5*iqr <= v <= q3 + 1.5*iqr]
    
    if len(limpios) < 10:
        return None, len(cercanas), cercanas
    
    return float(np.median(limpios)), len(limpios), limpios

# ─── PROCESAR CADA ANCLA ───
print(f"\nProcesando {len(v3_raw)} anclas...")
resultados = []
auto_gap_ids = {a['id'] for a in v3_raw if 'auto_gap' in a.get('id', '')}

for a in v3_raw:
    aid = a['id']
    lat, lon = a.get('lat'), a.get('lon')
    if not lat or not lon:
        continue
    
    v3_val = a.get('usd_m2', 0)
    v4_val = v4_dict.get(aid, v4_dict.get(aid.replace('auto_gap_',''), None))
    
    # Valor zonal v4.1
    zonal, n_zonal, _ = calcular_valor_zonal(float(lat), float(lon))
    
    if zonal is not None and n_zonal >= 20:
        v41_val = round(zonal, 0)
        recomendacion = 'usar v4.1'
    elif zonal is not None:
        v41_val = round(zonal, 0)
        recomendacion = 'n_insuficiente'
    else:
        v41_val = None
        recomendacion = 'mantener v3'
    
    tipo = 'auto_gap' if aid in auto_gap_ids else 'manual'
    
    resultados.append({
        'id': aid,
        'tipo': tipo,
        'v3_usd': v3_val,
        'v4_usd': v4_val if v4_val else '',
        'v41_usd': v41_val if v41_val else '',
        'n_zonal': n_zonal if zonal else 0,
        'recomendacion': recomendacion,
    })

# ─── GUARDAR CSV ───
csv_path = os.path.join(REPORTS_DIR, 'anclas_comparacion_v3_v4_v41.csv')
with open(csv_path, 'w', newline='', encoding='utf-8') as f:
    w = csv.DictWriter(f, fieldnames=['id', 'tipo', 'v3_usd', 'v4_usd', 'v41_usd', 'n_zonal', 'recomendacion'])
    w.writeheader()
    w.writerows(resultados)

print(f"\nCSV guardado: {csv_path}")

# ─── RESUMEN ───
n_total = len(resultados)
n_v41 = sum(1 for r in resultados if r['v41_usd'])
n_recalibrar = sum(1 for r in resultados if r['recomendacion'] == 'usar v4.1')
n_mantener = sum(1 for r in resultados if r['recomendacion'] == 'mantener v3')
n_insuf = sum(1 for r in resultados if r['recomendacion'] == 'n_insuficiente')

print(f"\n=== RESUMEN ===")
print(f"Total anclas procesadas: {n_total}")
print(f"Con valor zonal v4.1: {n_v41}")
print(f"Recalibrar (v4.1, n>=20): {n_recalibrar}")
print(f"Mantener v3 (sin datos): {n_mantener}")
print(f"n insuficiente (<20): {n_insuf}")

print(f"\n=== TOP 10 DIFERENCIAS v3 -> v4.1 ===")
recalibrables = [r for r in resultados if r['recomendacion'] == 'usar v4.1']
recalibrables.sort(key=lambda r: abs(r['v3_usd'] - r['v41_usd']), reverse=True)
print(f"{'Ancla':42} {'v3':>6} {'v4.1':>6} {'delta':>6} {'n':>4}")
print('-'*70)
for r in recalibrables[:10]:
    d = r['v41_usd'] - r['v3_usd']
    print(f"{r['id']:42} {r['v3_usd']:>6} {r['v41_usd']:>6} {d:>+6} {r['n_zonal']:>4}")
