"""
Recalibración temporal de anclas con ventanas progresivas (90d/180d/365d + decay).
Genera data/anclas_rosario_v41_temporal.json + reports/anclas_recalibracion_temporal.csv

Uso: python scripts/recalibrar_anclas_v41_temporal.py
NO modifica el motor ni toca v3.
"""
import json, math, os, sys
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)

FECHA_REF = datetime.now()
RADIO_M = 500
MIN_MUESTRAS = 20


def dist_m(lat1, lon1, lat2, lon2):
    R = 6371000
    la1, lo1, la2, lo2 = map(math.radians, [float(lat1), float(lon1), float(lat2), float(lon2)])
    dl, do = la2 - la1, lo2 - lo1
    a = math.sin(dl/2)**2 + math.cos(la1)*math.cos(la2)*math.sin(do/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def peso_temporal(fecha_str, fecha_ref, lam=0.005):
    """Peso exponencial por antigüedad. lam=0.005 -> 90d=64%, 180d=41%, 365d=16%"""
    try:
        if isinstance(fecha_str, str):
            f = datetime.fromisoformat(fecha_str.replace('Z', ''))
        else:
            f = fecha_str
        dias = max(0, (fecha_ref - f).days)
        return math.exp(-lam * dias)
    except:
        return 0.1


def limpiar_iqr(vals):
    if len(vals) < 4:
        return vals
    q1, q3 = np.percentile(vals, [25, 75])
    iqr = q3 - q1
    lo, hi = q1 - 1.5*iqr, q3 + 1.5*iqr
    return [v for v in vals if lo <= v <= hi]


def p50_pond(vals, pesos):
    pares = sorted(zip(vals, pesos), key=lambda x: x[0])
    vo, po = [p[0] for p in pares], [p[1] for p in pares]
    pt = sum(po)
    ac = 0
    for v, p in zip(vo, po):
        ac += p
        if ac >= pt / 2:
            return v
    return vo[-1]


def recalibrar(lat, lon, props):
    """Ventana progresiva 90d→180d→365d con decay."""
    ventanas = [(90, False, 'rolling_90d'), (180, False, 'rolling_180d'),
                (365, True, 'rolling_365d_decay')]

    for max_dias, usar_decay, metodo in ventanas:
        inicio = FECHA_REF - timedelta(days=max_dias)
        vals, pesos, fechas = [], [], []

        for p in props:
            pl = p.get('lat') or p.get('latitud')
            pn = p.get('lon') or p.get('longitud')
            if not pl or not pn:
                continue
            if 'venta' not in str(p.get('operacion', '')).lower():
                continue

            try:
                if dist_m(lat, lon, float(pl), float(pn)) > RADIO_M:
                    continue
            except:
                continue

            fs = p.get('date_updated', '')
            if not fs:
                continue
            try:
                fp = datetime.fromisoformat(fs.replace('Z', ''))
            except:
                try:
                    fp = datetime.strptime(fs[:10], '%Y-%m-%d')
                except:
                    continue

            if fp < inicio or fp > FECHA_REF:
                continue

            pr = p.get('precio', p.get('precio_usd', 0))
            m2 = p.get('m2', p.get('sup_total', 0))
            if pr > 0 and m2 > 0:
                vals.append(pr / m2)
                pesos.append(peso_temporal(fp, FECHA_REF) if usar_decay else 1.0)
                fechas.append(fp)

        if len(vals) >= 4:
            limpios = limpiar_iqr(vals)
            pesos_l = [pesos[i] for i, v in enumerate(vals) if v in limpios][:len(limpios)]
        else:
            limpios, pesos_l = vals, pesos

        if len(limpios) >= MIN_MUESTRAS:
            v = p50_pond(limpios, pesos_l) if usar_decay else float(np.median(limpios))
            return {
                'usd_m2': round(v, 2), 'n': len(limpios), 'ventana': max_dias,
                'metodo': metodo, 'f_min': min(fechas).strftime('%Y-%m-%d') if fechas else '',
                'f_max': max(fechas).strftime('%Y-%m-%d') if fechas else '',
                'p25': round(float(np.percentile(limpios, 25)), 2),
                'p75': round(float(np.percentile(limpios, 75)), 2),
            }
    return None


# ─── CARGAR DATOS ───
print("Cargando anclas v3...")
with open('anclas_rosario_v3_grid.json', 'r', encoding='utf-8') as f:
    raw = json.load(f)
anclas_v3 = raw['anclas'] if isinstance(raw, dict) else raw
meta = {k: v for k, v in raw.items() if k != 'anclas'} if isinstance(raw, dict) else {}

print(f"Cargando cache_scraping.json...")
with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)
props = cache.get('propiedades', [])
print(f"  {len(props)} propiedades de venta en cache")

# ─── RECALIBRAR ───
print(f"\nRecalibrando {len(anclas_v3)} anclas...")
resultados = []

for i, a in enumerate(anclas_v3):
    nombre = a.get('id', a.get('nombre', f'ancla_{i}'))
    lat, lon = a.get('lat'), a.get('lon')
    usd_v3 = a.get('usd_m2', 0)

    if lat and lon:
        r = recalibrar(lat, lon, props)
    else:
        r = None

    entry = {
        'id': nombre, 'lat': lat, 'lon': lon,
        'usd_m2': r['usd_m2'] if r else usd_v3,
        'usd_m2_v3': usd_v3,
        'n_zonal': r['n'] if r else 0,
        'ventana_dias': r['ventana'] if r else None,
        'metodo_temporal': r['metodo'] if r else 'sin_datos',
        'fecha_pub_min': r['f_min'] if r else '',
        'fecha_pub_max': r['f_max'] if r else '',
        'p25': r['p25'] if r else None,
        'p75': r['p75'] if r else None,
    }

    if r:
        desvio = ((r['usd_m2'] - usd_v3) / usd_v3 * 100) if usd_v3 else 0
        entry['desvio_pct_vs_v3'] = round(desvio, 1)
        if r['n'] >= 100 and abs(desvio) <= 20:
            entry['estado_revision'] = 'auto_aprobable'
        elif r['n'] >= 20:
            entry['estado_revision'] = 'revision_manual'
        else:
            entry['estado_revision'] = 'mantener_v3'
    else:
        entry['desvio_pct_vs_v3'] = None
        entry['estado_revision'] = 'mantener_v3'

    resultados.append(entry)

# ─── GUARDAR JSON ───
output = {**meta, 'anclas_v3_originales': len(anclas_v3), 'anclas_v41': len(resultados),
          'fecha_calibracion': FECHA_REF.strftime('%Y-%m-%d'), 'anclas': resultados}

with open('data/anclas_rosario_v41_temporal.json', 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)
print(f"\n  -> data/anclas_rosario_v41_temporal.json")

# ─── GUARDAR CSV ───
os.makedirs('reports', exist_ok=True)
rows = [{
    'nombre': r['id'], 'v3_usd': r['usd_m2_v3'], 'v41_usd': r['usd_m2'],
    'desvio_pct': r['desvio_pct_vs_v3'], 'n_zonal': r['n_zonal'],
    'ventana_dias': r['ventana_dias'], 'metodo': r['metodo_temporal'],
    'estado': r['estado_revision'],
    'p25': r['p25'], 'p75': r['p75'],
} for r in resultados]
pd.DataFrame(rows).to_csv('reports/anclas_recalibracion_temporal.csv', index=False)
print(f"  -> reports/anclas_recalibracion_temporal.csv")

# ─── RESUMEN ───
n_auto = sum(1 for r in resultados if r['estado_revision'] == 'auto_aprobable')
n_rev = sum(1 for r in resultados if r['estado_revision'] == 'revision_manual')
n_man = sum(1 for r in resultados if r['estado_revision'] == 'mantener_v3')

print(f"\n{'='*70}")
print(f"RESUMEN: {len(resultados)} anclas procesadas")
print(f"{'='*70}")
print(f"  Auto-aprobables (n>=100, desvio<=20%): {n_auto}")
print(f"  Revision manual (n>=20, desvio>20% o n<100): {n_rev}")
print(f"  Mantener v3 (sin datos): {n_man}")

for d in [90, 180, 365]:
    nv = sum(1 for r in resultados if r['ventana_dias'] == d)
    print(f"  Ventana {d}d: {nv} anclas")
ns = sum(1 for r in resultados if r['ventana_dias'] is None)
print(f"  Sin datos: {ns} anclas")

print(f"\nTop 10 mayores cambios (v3 -> v4.1):")
cambios = [(r['id'], r['usd_m2_v3'], r['usd_m2'], r['desvio_pct_vs_v3'])
           for r in resultados if r['desvio_pct_vs_v3'] is not None]
cambios.sort(key=lambda x: abs(x[3]), reverse=True)
print(f"{'Ancla':45} {'v3':>8} {'v4.1':>8} {'Desvio':>8}")
print('-' * 72)
for nom, v3v, v41, dev in cambios[:10]:
    print(f"{nom:45} ${v3v:>6,.0f} ${v41:>6,.0f} {dev:>+7.1f}%")
