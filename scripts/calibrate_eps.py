import json
import numpy as np
from datetime import datetime
from sklearn.cluster import DBSCAN
import os

def load_data():
    path = r'C:\Users\Gustavo\ingresos_familiares_st\cache_scraping.json'
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data.get('propiedades', [])

def filter_stale(props):
    now = datetime.now()
    filtered = []
    for p in props:
        date_str = p.get('date_updated') or p.get('date_created')
        if date_str:
            try:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                if dt.tzinfo is not None:
                    dt = dt.replace(tzinfo=None)
                days_diff = (now - dt).days
                if days_diff <= 180:
                    filtered.append(p)
            except Exception:
                filtered.append(p) 
        else:
            filtered.append(p)
    return filtered

def run_dbscan_test(props, eps_meters):
    eps_deg = eps_meters / 111000.0
    coords = np.array([[p['lat'], p['lon']] for p in props if p.get('lat') and p.get('lon')])
    if len(coords) == 0: return None
    db = DBSCAN(eps=eps_deg, min_samples=8).fit(coords)
    labels = db.labels_
    n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise = list(labels).count(-1)
    noise_pct = (n_noise / len(coords)) * 100
    return {'eps': eps_meters, 'n_clusters': n_clusters, 'noise_pct': noise_pct}

if __name__ == '__main__':
    props = load_data()
    filtered_props = filter_stale(props)
    print('Total props: ' + str(len(props)) + ' | Filtered (<=180d): ' + str(len(filtered_props)))
    print('\n' + '='*50)
    print('Epsilon    | Clusters   | Ruido %')
    print('-'*50)
    for eps in [100, 150, 200, 300]:
        res = run_dbscan_test(filtered_props, eps)
        if res:
            # Use format() instead of f-strings to avoid backslash issues in this specific shell
            line = '{:<10} | {:<10} | {:>8.2f}%'.format(res['eps'], res['n_clusters'], res['noise_pct'])
            print(line)
    print('='*50)
