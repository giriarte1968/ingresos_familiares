"""Genera anclas por grilla espacial con Ct dual (nuevo vs usado).
Lee configuracion de config/anclas_config.json.
Output: data/anclas_v7_AAAAMMDD_HHMMSS.json

CLI:
  --grid-size    override grid_size_m del config
  --min-props    override min_props_per_cell del config
  --output       ruta especifica (default: timestamped)
"""
import sys, os, json, math, collections, re, argparse
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, PROJECT_ROOT)

from parsers.motor_vpp_core import load_anclas_config
from parsers.time_adjustment import interpolar, ct_segmento, meses_desde, es_nuevo

FECHA_REF = datetime(2026, 6, 1)

def m2deg_lat(m):
    return m / 111000.0

def m2deg_lon(m, lat):
    return m / (111320.0 * math.cos(math.radians(lat)))

def build_noise_set(noise_tokens, noise_patterns):
    s = set(t.lower() for t in noise_tokens if t)
    return s, noise_patterns

def clean_calle(calle, noise_set, noise_patterns):
    if not calle: return ''
    tokens = calle.lower().split()
    cleaned = []
    for t in tokens:
        if t in noise_set: continue
        if t.isdigit(): continue
        if re.search(r'\d', t) and re.search(r'[a-z]', t):
            if not re.match(r'^\d+[a-z]', t):
                continue
        cleaned.append(t)
    return ' '.join(cleaned) if cleaned else ''

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

def macrozona(lat, lon, city_center):
    clat, clon = city_center['lat'], city_center['lon']
    dlat = lat - clat
    dlon = lon - clon
    dist_km = math.sqrt((dlat*111)**2 + (dlon*93)**2)
    dlat_km = dlat * 111
    dlon_km = dlon * 93
    if dist_km < 1.5: return 'centro'
    if dlon_km > -0.5:
        if dlat_km > 0.5: return 'norte'
        elif dlat_km < -0.5: return 'sur'
        else: return 'centro'
    else: return 'oeste'

def main():
    cfg = load_anclas_config(force_reload=True)
    gen_cfg = cfg.get('generator', {})
    zones_cfg = cfg.get('zones', {})
    runtime_cfg = cfg.get('runtime', {})

    parser = argparse.ArgumentParser(description='Generar anclas por grilla')
    parser.add_argument('--grid-size', type=int, default=gen_cfg.get('grid_size_m', 400))
    parser.add_argument('--min-props', type=int, default=gen_cfg.get('min_props_per_cell', 5))
    parser.add_argument('--output', type=str, default=None)
    args = parser.parse_args()

    GRID_SIZE_M = args.grid_size
    MIN_PROPS = args.min_props
    FACTOR_USADO = gen_cfg.get('ct_factors', {}).get('usado', 1.12)
    FACTOR_NUEVO = gen_cfg.get('ct_factors', {}).get('nuevo', 0.95)
    city_center = gen_cfg.get('city_center', {'lat': -32.92776, 'lon': -60.69769})
    noise_tokens = gen_cfg.get('noise_tokens', [])
    noise_patterns = gen_cfg.get('noise_patterns', [])
    noise_set, _ = build_noise_set(noise_tokens, noise_patterns)
    ct_table = gen_cfg.get('ct_table', [])

    RUTA_CACHE = os.path.join(PROJECT_ROOT, 'cache_scraping.json')

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    if args.output:
        RUTA_OUT = args.output
    else:
        prefix = gen_cfg.get('output_prefix', 'anclas_v7_')
        out_name = '%s%s.json' % (prefix, ts)
        RUTA_OUT = os.path.join(PROJECT_ROOT, gen_cfg.get('output_dir', 'data'), out_name)

    print("Grid size: %dm, min props: %d" % (GRID_SIZE_M, MIN_PROPS))
    print("Ct: usado=1.0+(Ct-1.0)*%.2f, nuevo=1.0+(Ct-1.0)*%.2f" % (FACTOR_USADO, FACTOR_NUEVO))

    with open(RUTA_CACHE, encoding='utf-8') as f:
        cache = json.load(f)
    props_raw = cache.get('propiedades', [])

    props = []
    n_nuevo = 0
    for p in props_raw:
        if p.get('operacion') != 'venta': continue
        vm2 = p.get('valor_m2', 0)
        if not vm2 or vm2 <= 0: continue
        lat, lon = p.get('lat'), p.get('lon')
        if lat is None or lon is None: continue
        m = meses_desde(p.get('date_created'))
        if m is None: continue

        is_new = es_nuevo(p)
        if is_new: n_nuevo += 1

        ct_base = interpolar(ct_table, m)
        ct_usado = ct_segmento(m, FACTOR_USADO)
        ct_nuevo_val = ct_segmento(m, FACTOR_NUEVO)
        ct = ct_nuevo_val if is_new else ct_usado

        props.append({
            'lat': lat, 'lon': lon,
            'valor_m2': vm2,
            'lista_hoy_unico': round(vm2 * ct_base, 2),
            'lista_hoy_dual':  round(vm2 * ct, 2),
            'ct_base': ct_base,
            'ct_aplicado': ct,
            'es_nuevo': is_new,
            'zona': p.get('zona', ''),
            'calle': p.get('calle_limpia', ''),
            'meses': m,
        })
    print("Props validas venta: %d (nuevo=%d, usado=%d)" % (len(props), n_nuevo, len(props)-n_nuevo))

    lats = [p['lat'] for p in props]
    lons = [p['lon'] for p in props]
    lat0, lat1 = min(lats), max(lats)
    lon0, lon1 = min(lons), max(lons)
    dlat = m2deg_lat(GRID_SIZE_M)
    dlon = m2deg_lon(GRID_SIZE_M, (lat0+lat1)/2)

    celdas = collections.defaultdict(list)
    for p in props:
        ix = int(math.floor((p['lon'] - lon0) / dlon))
        iy = int(math.floor((p['lat'] - lat0) / dlat))
        celdas[(ix, iy)].append(p)

    usado = set()
    anclas = []
    for (ix, iy), miembros in celdas.items():
        n = len(miembros)
        if n < MIN_PROPS: continue
        lat_c = sum(p['lat'] for p in miembros) / n
        lon_c = sum(p['lon'] for p in miembros) / n

        vals_u = sorted(p['lista_hoy_unico'] for p in miembros)
        med_u = vals_u[n//2] if n%2 else (vals_u[n//2-1]+vals_u[n//2])/2

        vals_d = sorted(p['lista_hoy_dual'] for p in miembros)
        med_d = vals_d[n//2] if n%2 else (vals_d[n//2-1]+vals_d[n//2])/2

        calles_raw = [clean_calle(p['calle'], noise_set, noise_patterns) for p in miembros if p['calle']]
        calles = [c for c in calles_raw if c]
        top1 = ''
        if calles:
            top1 = collections.Counter(calles).most_common(1)[0][0].replace(' ', '_')
            name_base = top1
        else:
            name_base = 'microzona'

        zonas_en_celda = collections.Counter(
            p['zona'] for p in miembros if p['zona'] and p['zona'] != 'Otro')
        if zonas_en_celda:
            cand_zone = zonas_en_celda.most_common(1)[0][0].lower().replace(' ', '_')
            ref = zones_cfg.get(cand_zone)
            if ref and haversine(lat_c, lon_c, ref['lat'], ref['lon']) <= ref['radio']:
                zona_label = cand_zone
            else:
                zona_label = macrozona(lat_c, lon_c, city_center)
        else:
            zona_label = macrozona(lat_c, lon_c, city_center)
        name = '%s_%s' % (name_base, zona_label)
        if name in usado:
            for i in range(2, 999):
                cand = '%s_%d' % (name, i)
                if cand not in usado:
                    name = cand
                    break
        usado.add(name)
        name = name.strip('_')

        anclas.append({
            'id': name,
            'lat': round(lat_c, 6),
            'lon': round(lon_c, 6),
            'usd_m2': round(med_d, 0),
            'usd_m2_ct_unico': round(med_u, 0),
            'diff_pct': round((med_d - med_u) / med_u * 100, 1) if med_u else 0,
            'fecha_calibracion': '2026-06-01',
            'fuente': 'grid_v7',
            'n_zonal': n,
            'calle_principal': top1 if calles else '',
            'macrozona': zona_label,
        })

    anclas.sort(key=lambda a: a['id'])
    print("Total anclas: %d" % len(anclas))

    # Cobertura: props a <=300m de alguna ancla
    props_con_coord = [p for p in props_raw if p.get('lat') and p.get('lon') and p.get('operacion') == 'venta']
    cubiertas = 0
    for p in props_con_coord:
        pl, pn = p['lat'], p['lon']
        for a in anclas:
            if haversine(pl, pn, a['lat'], a['lon']) <= 300:
                cubiertas += 1
                break
    cobertura = cubiertas / len(props_con_coord) * 100 if props_con_coord else 0
    n_con_zona = sum(1 for a in anclas if a['macrozona'] not in ('centro', 'norte', 'sur', 'oeste'))
    n_sin_zona = sum(1 for a in anclas if a['macrozona'] in ('centro', 'norte', 'sur', 'oeste'))

    doc = {
        'version': 'v7_grid',
        'fecha_generacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'algoritmo': 'grid_%dm' % GRID_SIZE_M,
        'parametros': {
            'grid_size_m': GRID_SIZE_M,
            'min_props': MIN_PROPS,
            'ct_usado_factor': FACTOR_USADO,
            'ct_nuevo_factor': FACTOR_NUEVO,
        },
        'total_props': len(props),
        'total_anclas': len(anclas),
        'coverage_pct': round(cobertura, 1),
        'anclas': anclas,
    }
    with open(RUTA_OUT, 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    print("Guardado: %s" % RUTA_OUT)

    print("\n=== RESUMEN GENERACION ===")
    print("Output: %s" % RUTA_OUT)
    print("Anclas generadas: %d" % len(anclas))
    print("Cobertura (props <=300m de ancla): %.1f%%" % cobertura)
    print("Anclas con zona comercial: %d (%.1f%%)" % (n_con_zona, n_con_zona/len(anclas)*100 if anclas else 0))
    print("Anclas sin zona (macrozona): %d (%.1f%%)" % (n_sin_zona, n_sin_zona/len(anclas)*100 if anclas else 0))

    vals_d = sorted(a['usd_m2'] for a in anclas)
    vals_u = sorted(a['usd_m2_ct_unico'] for a in anclas)
    print("\nDistribucion:")
    print("  %-6s %8s %8s %8s" % ("Pct", "CtUnico", "CtDual", "Diff"))
    for pct in [5,10,25,50,75,90,95]:
        idx = min(int(len(vals_d)*pct/100), len(vals_d)-1)
        print("  P%-4d %8d %8d %+7.1f%%" % (pct, vals_u[idx], vals_d[idx],
              (vals_d[idx]-vals_u[idx])/vals_u[idx]*100))

    print("\nPor macrozona (Ct dual):")
    mz_grp = collections.defaultdict(list)
    for a in anclas:
        mz_grp[a['macrozona']].append(a)
    for mz in ['centro','norte','sur','oeste']:
        ga = mz_grp.get(mz, [])
        if not ga: continue
        gd = sorted(a['usd_m2'] for a in ga)
        gu = sorted(a['usd_m2_ct_unico'] for a in ga)
        med_d = gd[len(gd)//2]
        med_u = gu[len(gu)//2]
        print("  %s: %d anc  CtUnico=$%d  CtDual=$%d  diff=%+.1f%%" % (
            mz, len(gd), med_u, med_d, (med_d-med_u)/med_u*100))

    print("\nEjemplos de cambio:")
    diffs = sorted(anclas, key=lambda a: abs(a['diff_pct']), reverse=True)
    for a in diffs[:10]:
        print("  %-45s $%5d -> $%5d (%+.1f%%)  [%d props]" % (
            a['id'], a['usd_m2_ct_unico'], a['usd_m2'], a['diff_pct'], a['n_zonal']))

if __name__ == '__main__':
    main()
