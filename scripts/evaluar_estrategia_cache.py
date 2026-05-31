"""
Evalua estrategia de matching espacial por centroide PH.
Usa la misma clasificacion que corregir_coords_cache.py.
"""
import json, os, math, sys, time, glob, re
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parsers.mercado_inmobiliario import extraer_calle_numero, _filtrar_calle_diccionario, _token_contenido, _extraer_interseccion

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_PATH = os.path.join(PROJECT, 'cache_scraping.json')
GEOMETRY_DIR = os.path.join(PROJECT, 'data', 'geometry')
CATASTRO_PATH = os.path.join(PROJECT, 'data', 'rosario_avm_full.csv')

def distancia(lat1, lon1, lat2, lon2):
    R = 6371000
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)
    dlat, dlon = lat2_r - lat1_r, lon2_r - lon1_r
    a = math.sin(dlat/2)**2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

def cargar_centroides():
    centroid_index = {}
    errors = 0
    pattern = os.path.join(GEOMETRY_DIR, 'parcelas_seccion*_json.csv')
    files = sorted(glob.glob(pattern))
    for fpath in files:
        try:
            df = pd.read_csv(fpath)
        except Exception as e:
            errors += 1
            continue
        for _, row in df.iterrows():
            try:
                geojson = json.loads(row['GEOJSON'])
                coords = geojson['geometry']['coordinates'][0]
                n = len(coords)
                lat = sum(c[1] for c in coords) / n
                lon = sum(c[0] for c in coords) / n
                key = (int(row['SECCION']), int(row['MANZANA']), int(row['GRAFICO']), int(row['CARPETA']))
                centroid_index[key] = (lat, lon)
            except:
                errors += 1
    return centroid_index

def cargar_indice_catastro():
    df = pd.read_csv(CATASTRO_PATH)
    exact_idx = {}
    block_idx = {}
    calle_tokens = {}
    for _, row in df.iterrows():
        cn, num = extraer_calle_numero(str(row.get('direccion_nominatim', '')))
        if cn and num is not None:
            key = (cn, num)
            if key not in exact_idx:
                exact_idx[key] = row
            if cn not in calle_tokens:
                calle_tokens[cn] = cn.split()
            block = (num // 100) * 100
            if cn not in block_idx:
                block_idx[cn] = {}
            if block not in block_idx[cn]:
                block_idx[cn][block] = []
            block_idx[cn][block].append((
                num,
                int(row['seccion']) if not math.isnan(row['seccion']) else None,
                int(row['manzana']) if not math.isnan(row['manzana']) else None,
                int(row['grafico']) if not math.isnan(row['grafico']) else None,
                int(row['ph']),
                row['latitud'],
                row['longitud']
            ))
    return exact_idx, block_idx, calle_tokens

def buscar_ph(cn, num, exact_idx, block_idx, calle_tokens):
    def buscar_en_calle(calle, num, block_idx):
        block = (num // 100) * 100
        best = None
        best_diff = float('inf')
        if calle in block_idx:
            if block in block_idx[calle]:
                for n, sec, man, graf, ph, lat, lon in block_idx[calle][block]:
                    if sec is not None and man is not None and graf is not None:
                        diff = abs(n - num)
                        if diff < best_diff:
                            best_diff = diff
                            best = (sec, man, graf, ph, lat, lon)
            if best is None:
                for b in [block-100, block+100]:
                    if b in block_idx[calle]:
                        for n, sec, man, graf, ph, lat, lon in block_idx[calle][b]:
                            if sec is not None and man is not None and graf is not None:
                                diff = abs(n - num)
                                if diff < best_diff:
                                    best_diff = diff
                                    best = (sec, man, graf, ph, lat, lon)
        return best

    key = (cn, num)
    if key in exact_idx:
        r = exact_idx[key]
        sec = int(r['seccion']) if not math.isnan(r['seccion']) else None
        man = int(r['manzana']) if not math.isnan(r['manzana']) else None
        graf = int(r['grafico']) if not math.isnan(r['grafico']) else None
        if sec is not None and man is not None and graf is not None:
            return (sec, man, graf, int(r['ph']), r['latitud'], r['longitud'])

    cn_clean = _filtrar_calle_diccionario(cn)
    if cn_clean and cn_clean != cn:
        result = buscar_en_calle(cn_clean, num, block_idx)
        if result:
            return result

    comp_tokens = (cn_clean or cn).split()
    best = None
    best_score = 0.0
    for cat_cn, tokens in calle_tokens.items():
        if _token_contenido(comp_tokens, tokens):
            result = buscar_en_calle(cat_cn, num, block_idx)
            if result:
                cat_tokens = set(tokens)
                overlap = len(set(comp_tokens) & cat_tokens)
                token_score = overlap / max(len(comp_tokens), len(cat_tokens))
                block = (num // 100) * 100
                has_block = 0
                if cat_cn in block_idx:
                    for b in [block, block-100, block+100]:
                        if b in block_idx[cat_cn]:
                            has_block = 0.5
                            break
                score = token_score + has_block
                if score > best_score:
                    best_score = score
                    best = result
    return best

def main():
    print('=' * 70)
    print('EVALUACION: Matching espacial por centroide PH')
    print('=' * 70)

    # 1. Cargar centroides
    print('\n[1] Centroides...')
    centroides = cargar_centroides()
    print('  Centroides: %d' % len(centroides))

    # 2. Cargar catastro
    print('\n[2] Indice catastro...')
    exact_idx, block_idx, calle_tokens = cargar_indice_catastro()
    print('  PHs exactos: %d, Calles: %d' % (len(exact_idx), len(block_idx)))

    # 3. Cargar cache
    print('\n[3] Cache...')
    with open(CACHE_PATH, encoding='utf-8') as f:
        cache = json.load(f)
    props = cache['propiedades']
    print('  Propiedades: %d' % len(props))

    # 4. Clasificar como corregir_coords_cache.py
    sin_calle_num = []
    sin_calle_num_interseccion = []
    con_calle_num_sin_ph = []
    con_calle_num_con_ph = []
    sin_coords = 0

    # Pattern for intersection detection
    _re_interseccion = re.compile(r'\b(y|esq|esquina|e/)\b|/', re.IGNORECASE)

    for p in props:
        addr = p.get('direccion', '')
        lat = p.get('lat')
        lon = p.get('lon')
        if lat is None or lon is None:
            sin_coords += 1
            continue
        cn, num = extraer_calle_numero(addr)
        if not cn or num is None:
            sin_calle_num.append(p)
            # Check if this is a true intersection address
            if _re_interseccion.search(addr) and len(_extraer_interseccion(addr)) >= 2:
                sin_calle_num_interseccion.append(p)
            continue
        ph_info = buscar_ph(cn, num, exact_idx, block_idx, calle_tokens)
        if not ph_info:
            con_calle_num_sin_ph.append(p)
        else:
            con_calle_num_con_ph.append(p)

    print('\nClasificacion:')
    print('  Sin coords:                %d' % sin_coords)
    print('  Part A (sin calle+num):    %d' % len(sin_calle_num))
    print('    De los cuales intersecciones: %d' % len(sin_calle_num_interseccion))
    print('  Part B (calle+num sin PH): %d' % len(con_calle_num_sin_ph))
    print('  Con PH encontrado:         %d' % len(con_calle_num_con_ph))
    print('  Total c/coords:            %d' % (len(sin_calle_num) + len(con_calle_num_sin_ph) + len(con_calle_num_con_ph)))

    # Build PH coord list (catastro coords + centroide if available)
    df = pd.read_csv(CATASTRO_PATH)
    ph_coords = []
    for _, row in df.iterrows():
        seccion = int(row['seccion']) if not math.isnan(row['seccion']) else None
        manzana = int(row['manzana']) if not math.isnan(row['manzana']) else None
        grafico = int(row['grafico']) if not math.isnan(row['grafico']) else None
        lat = row['latitud']
        lon = row['longitud']
        cn, num = extraer_calle_numero(str(row.get('direccion_nominatim', '')))
        if seccion is not None and manzana is not None and grafico is not None and lat and lon:
            centroid = centroides.get((seccion, manzana, grafico, int(row['ph'])))
            ph_coords.append({
                'cn': cn,
                'num': num,
                'catastro_lat': lat,
                'catastro_lon': lon,
                'centroid_lat': centroid[0] if centroid else lat,
                'centroid_lon': centroid[1] if centroid else lon,
                'direccion_raw': str(row.get('direccion_nominatim', '')),
            })
    print('  PHs con coordenadas: %d' % len(ph_coords))

    # ============================================================
    # PART A: sin calle+num
    # ============================================================
    print('\n' + '=' * 70)
    print('PART A: SIN CALLE+NUM (%d entradas)' % len(sin_calle_num))
    print('=' * 70)

    def evaluar_batch(entries, label):
        r_0ph = 0
        r_1ph = 0
        r_2ph = 0
        r_2ph_reduced = 0
        ex_0ph = []
        ex_1ph = []
        ex_2ph = []
        ex_2ph_reduced = []

        for p in entries:
            addr = p.get('direccion', '')
            lat = p.get('lat')
            lon = p.get('lon')

            nearby = []
            for ph in ph_coords:
                d = distancia(lat, lon, ph['centroid_lat'], ph['centroid_lon'])
                if d <= 60:
                    nearby.append((d, ph))
            nearby.sort(key=lambda x: x[0])

            if len(nearby) == 0:
                r_0ph += 1
                if len(ex_0ph) < 5:
                    ex_0ph.append((addr, lat, lon))
            elif len(nearby) == 1:
                r_1ph += 1
                if len(ex_1ph) < 5:
                    d, ph = nearby[0]
                    ex_1ph.append((addr, ph['direccion_raw'], round(d, 1)))
            else:
                # Try street name filter
                calles = _extraer_interseccion(addr)
                streets = [cn for cn, num in calles if cn]

                filtered = []
                for d, ph in nearby:
                    if streets and ph['cn']:
                        ph_tokens = ph['cn'].split()
                        for s in streets:
                            s_tokens = s.split()
                            if _token_contenido(s_tokens, ph_tokens) or _token_contenido(ph_tokens, s_tokens):
                                filtered.append((d, ph))
                                break
                    else:
                        filtered.append((d, ph))

                if len(filtered) == 1:
                    r_2ph_reduced += 1
                    if len(ex_2ph_reduced) < 5:
                        d, ph = filtered[0]
                        ex_2ph_reduced.append((addr, [p[1]['direccion_raw'] for p in nearby[:3]], ph['direccion_raw'], round(d, 1)))
                else:
                    r_2ph += 1
                    if len(ex_2ph) < 5:
                        ex_2ph.append((addr, [(p[1]['direccion_raw'], round(p[0], 1)) for p in nearby[:3]]))

        print('\nResultados %s:' % label)
        print('  0 PHs dentro de 60m:              %d' % r_0ph)
        print('  Exactamente 1 PH dentro de 60m:   %d' % r_1ph)
        print('  2+ PHs dentro de 60m:             %d' % (r_2ph + r_2ph_reduced))
        print('    -> Reducido a 1 por calle:       %d' % r_2ph_reduced)
        print('    -> Sigue siendo ambiguo:         %d' % r_2ph)

        print('\n--- Ejemplos: 0 PHs ---')
        for addr, lat, lon in ex_0ph:
            print('  "%s"' % addr[:70])
        print('\n--- Ejemplos: 1 PH exacto ---')
        for addr, ph_dir, d in ex_1ph:
            print('  "%s" -> %s (%.1fm)' % (addr[:60], ph_dir, d))
        print('\n--- Ejemplos: 2+ PHs, reducido a 1 por calle ---')
        for addr, nearby_dirs, match_dir, d in ex_2ph_reduced:
            print('  "%s"' % addr[:60])
            print('    Near: %s' % '; '.join(nearby_dirs))
            print('    Match: %s (%.1fm)' % (match_dir, d))
        print('\n--- Ejemplos: 2+ PHs, ambiguo ---')
        for addr, nearby_list in ex_2ph:
            print('  "%s"' % addr[:60])
            for ph_dir, d in nearby_list:
                print('    - %s (%.1fm)' % (ph_dir, d))

        return r_0ph, r_1ph, r_2ph, r_2ph_reduced

    a_0ph, a_1ph, a_2ph, a_2ph_reduced = evaluar_batch(sin_calle_num, 'Part A (todos sin calle+num)')
    a_int_0ph, a_int_1ph, a_int_2ph, a_int_2ph_reduced = evaluar_batch(sin_calle_num_interseccion, 'Part A (solo intersecciones)')
    b_0ph, b_1ph, b_2ph, b_2ph_reduced = evaluar_batch(con_calle_num_sin_ph, 'Part B')

    # Summary
    total_a = len(sin_calle_num)
    total_a_int = len(sin_calle_num_interseccion)
    total_b = len(con_calle_num_sin_ph)

    print('\n' + '=' * 70)
    print('RESUMEN FINAL')
    print('=' * 70)
    print()
    print('Part A (todos sin calle+num):')
    print('  Total:                     %d' % total_a)
    print('  0 PHs dentro 60m:          %d (%.1f%%)' % (a_0ph, 100*a_0ph/total_a))
    print('  1 PH exacto:               %d (%.1f%%)' % (a_1ph, 100*a_1ph/total_a))
    print('  2+ PHs:                    %d (%.1f%%)' % (a_2ph+a_2ph_reduced, 100*(a_2ph+a_2ph_reduced)/total_a))
    print('    -> Recuperables (1 tras filtro calle): %d' % a_2ph_reduced)
    print('    -> Irrecuperables:                     %d' % a_2ph)
    print('  Total match potencial:     %d (%.1f%%)' % (a_1ph + a_2ph_reduced, 100*(a_1ph + a_2ph_reduced)/total_a))
    print()
    print('Part A-intersection (solo intersecciones reales):')
    print('  Total:                     %d' % total_a_int)
    if total_a_int:
        print('  0 PHs dentro 60m:          %d (%.1f%%)' % (a_int_0ph, 100*a_int_0ph/total_a_int))
        print('  1 PH exacto:               %d (%.1f%%)' % (a_int_1ph, 100*a_int_1ph/total_a_int))
        print('  2+ PHs:                    %d (%.1f%%)' % (a_int_2ph+a_int_2ph_reduced, 100*(a_int_2ph+a_int_2ph_reduced)/total_a_int))
        print('    -> Recuperables (1 tras filtro calle): %d' % a_int_2ph_reduced)
        print('    -> Irrecuperables:                     %d' % a_int_2ph)
        print('  Total match potencial:     %d (%.1f%%)' % (a_int_1ph + a_int_2ph_reduced, 100*(a_int_1ph + a_int_2ph_reduced)/total_a_int))
    print()
    print('Part B (Calle+num sin PH en catastro):')
    print('  Total:                     %d' % total_b)
    print('  0 PHs dentro 60m:          %d (%.1f%%)' % (b_0ph, 100*b_0ph/total_b))
    print('  1 PH exacto:               %d (%.1f%%)' % (b_1ph, 100*b_1ph/total_b))
    print('  2+ PHs:                    %d (%.1f%%)' % (b_2ph+b_2ph_reduced, 100*(b_2ph+b_2ph_reduced)/total_b))
    print('    -> Recuperables (1 tras filtro calle): %d' % b_2ph_reduced)
    print('    -> Irrecuperables:                     %d' % b_2ph)
    print('  Total match potencial:     %d (%.1f%%)' % (b_1ph + b_2ph_reduced, 100*(b_1ph + b_2ph_reduced)/total_b))

if __name__ == '__main__':
    main()
