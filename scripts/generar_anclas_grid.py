"""Genera anclas por grilla 400m con Ct dual (nuevo vs usado).
Output: data/anclas_rosario_v6_cluster.json + comparacion vs Ct unico.
"""
import json, math, collections, re
from datetime import datetime

FECHA_REF = datetime(2026, 6, 1)

# Ct base (general market)
TABLA_CT  = [(0,1.000),(3,1.011),(6,1.033),(12,1.105),(18,1.207),
             (24,1.235),(30,1.267),(36,1.254),(42,1.203),(48,1.173),
             (54,1.152),(60,1.131),(66,1.105),(72,1.067),(78,1.027),(83,1.000)]

# Ct diferenciado por segmento
# Bassini: usado +10-15% vs general, estrenar competitivo (-5%)
# Formula: Ct_segmento = 1.0 + (Ct_base - 1.0) * factor
FACTOR_USADO = 1.12  # usado aprecia 12% mas que el general
FACTOR_NUEVO = 0.95  # nuevo aprecia 5% menos que el general

def ct_segmento(meses, factor):
    ct_base = interpolar(TABLA_CT, meses)
    return 1.0 + (ct_base - 1.0) * factor

RUTA_CACHE = 'C:/Users/Gustavo/ingresos_familiares_st/cache_scraping.json'
RUTA_OUT   = 'C:/Users/Gustavo/ingresos_familiares_st/data/anclas_rosario_v6_cluster.json'
GRID_SIZE_M = 400
MIN_PROPS   = 5

CENTRO_LAT = -32.92776
CENTRO_LON = -60.69769

def interpolar(tabla, x):
    if x <= tabla[0][0]: return tabla[0][1]
    if x >= tabla[-1][0]: return 1.0
    for i in range(len(tabla)-1):
        x1,y1 = tabla[i]; x2,y2 = tabla[i+1]
        if x1 <= x <= x2:
            return y1 + (y2 - y1) * (x - x1) / (x2 - x1)
    return 1.0

def meses_desde(fecha_str):
    if not fecha_str: return None
    try:
        dt = datetime.strptime(str(fecha_str)[:10], '%Y-%m-%d')
        return max(0, (FECHA_REF - dt).days / 30.44)
    except: return None

def m2deg_lat(m):  return m / 111000.0
def m2deg_lon(m, lat): return m / (111320.0 * math.cos(math.radians(lat)))

def es_nuevo(p):
    txt = ('%s %s %s' % (p.get('direccion',''), p.get('tipo',''), p.get('zona',''))).lower()
    return any(k in txt for k in ['a estrenar', 'estrenar', 'pozo', 'obra nueva'])

PROP_NOISE = {'duplex','casa','casas','departamento','dormitorio','dormitorios',
    'cochera','monoambiente','ph','local','oficina','patio','jardin','terraza',
    'balcon','living','comedor','cocina','banio','bano','lavadero','pileta',
    'quincho','marina','co_working','con','sin','y','e','o','a','su','tu','mi',
    'al','el','un','una','para','semi','piso','planta','frente','contrafrente',
    'exclusivo','exclusiva','completo','completa','tipo','gran','gran_',
    'nuevo','nueva','usado','usada','consultar','consulte','permuta',
    'c','s','n','e','o','en','de','la','las','los','del',
    'republica','pago','largo','bajo','alto','alta','bis','pasaje','pje',
    'esquina','esq','lt','lote','manzana','mz',
    'moderno','chalet','retasado','fisherton','pasos'}

def clean_calle(calle):
    if not calle: return ''
    tokens = calle.lower().split()
    cleaned = []
    for t in tokens:
        if t in PROP_NOISE: continue
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

# Centros de referencia para validar zona comercial
# Si el centroide de la celda esta fuera del radio, cae a macrozona geografica
ZONA_CENTROIDES = {
    # Centros reales desde cache_scraping.json (media de props con esa zona)
    'martin':       {'lat': -32.9500, 'lon': -60.6525, 'radio': 1500},
    'pellegrini':   {'lat': -32.9551, 'lon': -60.6507, 'radio': 1500},
    'puerto_norte': {'lat': -32.9250, 'lon': -60.6660, 'radio': 1200},
    'pichincha':    {'lat': -32.9373, 'lon': -60.6581, 'radio': 1200},
    'abasto':       {'lat': -32.9589, 'lon': -60.6453, 'radio': 1200},
    # centro aproximado
    'centro':       {'lat': -32.940,  'lon': -60.649, 'radio': 1500},
}

def macrozona(lat, lon):
    dlat = lat - CENTRO_LAT
    dlon = lon - CENTRO_LON
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

        # Three versions of lista_hoy
        ct_base = interpolar(TABLA_CT, m)
        ct_usado = ct_segmento(m, FACTOR_USADO)
        ct_nuevo_val = ct_segmento(m, FACTOR_NUEVO)

        # Use the appropriate Ct based on segment
        ct = ct_nuevo_val if is_new else ct_usado

        props.append({
            'lat': lat, 'lon': lon,
            'valor_m2': vm2,
            'lista_hoy_unico': round(vm2 * ct_base, 2),      # Ct unico (original)
            'lista_hoy_dual':  round(vm2 * ct, 2),            # Ct dual (segmento)
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

    # Asignar props a celdas (misma grilla para ambas versiones)
    celdas = collections.defaultdict(list)
    for p in props:
        ix = int(math.floor((p['lon'] - lon0) / dlon))
        iy = int(math.floor((p['lat'] - lat0) / dlat))
        celdas[(ix, iy)].append(p)

    # Nombrar y valorar celdas (con Ct dual)
    usado = set()
    anclas = []
    for (ix, iy), miembros in celdas.items():
        n = len(miembros)
        if n < MIN_PROPS: continue
        lat_c = sum(p['lat'] for p in miembros) / n
        lon_c = sum(p['lon'] for p in miembros) / n

        # Mediana con Ct unico
        vals_u = sorted(p['lista_hoy_unico'] for p in miembros)
        med_u = vals_u[n//2] if n%2 else (vals_u[n//2-1]+vals_u[n//2])/2

        # Mediana con Ct dual
        vals_d = sorted(p['lista_hoy_dual'] for p in miembros)
        med_d = vals_d[n//2] if n%2 else (vals_d[n//2-1]+vals_d[n//2])/2

        # Naming: zona + calle principal (top 1, no 2 — mas estable)
        calles_raw = [clean_calle(p['calle']) for p in miembros if p['calle']]
        calles = [c for c in calles_raw if c]
        top1 = ''
        if calles:
            top1 = collections.Counter(calles).most_common(1)[0][0].replace(' ', '_')
            name_base = top1
        else:
            name_base = 'microzona'

        # Zona comercial: la mas comun no-Otro en la celda
        # Solo se asigna si el centroide esta dentro del radio de referencia
        zonas_en_celda = collections.Counter(
            p['zona'] for p in miembros if p['zona'] and p['zona'] != 'Otro')
        if zonas_en_celda:
            cand_zone = zonas_en_celda.most_common(1)[0][0].lower().replace(' ', '_')
            ref = ZONA_CENTROIDES.get(cand_zone)
            if ref and haversine(lat_c, lon_c, ref['lat'], ref['lon']) <= ref['radio']:
                zona_label = cand_zone
            else:
                zona_label = macrozona(lat_c, lon_c)
        else:
            zona_label = macrozona(lat_c, lon_c)
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
            'usd_m2': round(med_d, 0),         # Valor con Ct dual
            'usd_m2_ct_unico': round(med_u, 0), # Valor con Ct unico (ref)
            'diff_pct': round((med_d - med_u) / med_u * 100, 1) if med_u else 0,
            'fecha_calibracion': '2026-06-01',
            'fuente': 'grid_v6_dual',
            'n_zonal': n,
            'calle_principal': top1 if calles else '',
            'macrozona': zona_label,
        })

    anclas.sort(key=lambda a: a['id'])
    print("Total anclas: %d" % len(anclas))

    doc = {
        'version': 'v6_grid_dual',
        'fecha_generacion': '2026-06-01',
        'algoritmo': 'grid_400m',
        'parametros': {
            'ct_usado_factor': FACTOR_USADO,
            'ct_nuevo_factor': FACTOR_NUEVO,
        },
        'total_props': len(props),
        'anclas': anclas,
    }
    with open(RUTA_OUT, 'w', encoding='utf-8') as f:
        json.dump(doc, f, indent=2, ensure_ascii=False)
    print("Guardado:", RUTA_OUT)

    # Stats comparativas
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
