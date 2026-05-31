"""
TAREA-020: Corregir coordenadas de cache_scraping.json vía centroide catastral.

Para cada propiedad con (calle, num) válido:
  1. Buscar PH mas cercano en catastro
  2. Obtener centroide de la parcela (geometria oficial)
  3. Si distancia cache vs centroide >60m, reemplazar con centroide
"""
import json, os, math, sys, time, glob, re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parsers.mercado_inmobiliario import extraer_calle_numero, _filtrar_calle_diccionario, _token_contenido

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
    """Carga todas las geometrias y precomputa centroides."""
    import pandas as pd
    centroid_index = {}  # (seccion, manzana, grafico, carpeta) -> (lat, lon)
    errors = 0
    pattern = os.path.join(GEOMETRY_DIR, 'parcelas_seccion*_json.csv')
    files = sorted(glob.glob(pattern))
    print('  Archivos geometria: %d' % len(files))
    for fpath in files:
        sec_name = os.path.basename(fpath).replace('parcelas_seccion', '').replace('_json.csv', '')
        try:
            df = pd.read_csv(fpath)
        except Exception as e:
            print('  Error cargando %s: %s' % (fpath, e))
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
    print('  Centroides computados: %d' % len(centroid_index))
    if errors:
        print('  Errores: %d' % errors)
    return centroid_index

def cargar_indice_catastro():
    """Carga PHs del catastro y construye indices."""
    import pandas as pd
    df = pd.read_csv(CATASTRO_PATH)
    
    exact_idx = {}
    block_idx = {}
    calle_tokens = {}  # cn -> tokens for token matching
    
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
    """Busca el PH mas cercano para (cn, num).
    
    Usa matching progresivo:
    1. Exacto por (cn, num)
    2. _filtrar_calle_diccionario para limpiar street name y probar de nuevo
    3. Token containment contra todas las calles del catastro
    """
    # Helper: busca en block_idx[calle] el mejor PH por numero
    def buscar_en_calle(calle, num, block_idx):
        block = (num // 100) * 100
        best = None
        best_diff = float('inf')
        if calle in block_idx:
            # Primero buscar en el mismo bloque
            if block in block_idx[calle]:
                for n, sec, man, graf, ph, lat, lon in block_idx[calle][block]:
                    if sec is not None and man is not None and graf is not None:
                        diff = abs(n - num)
                        if diff < best_diff:
                            best_diff = diff
                            best = (sec, man, graf, ph, lat, lon)
            # Si no hay match en el mismo bloque, buscar en bloques adyacentes
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
    
    # Paso 1: exacto
    key = (cn, num)
    if key in exact_idx:
        r = exact_idx[key]
        sec = int(r['seccion']) if not math.isnan(r['seccion']) else None
        man = int(r['manzana']) if not math.isnan(r['manzana']) else None
        graf = int(r['grafico']) if not math.isnan(r['grafico']) else None
        if sec is not None and man is not None and graf is not None:
            return (sec, man, graf, int(r['ph']), r['latitud'], r['longitud'])
    
    # Paso 2: filtrar con calles_rosario y probar
    cn_clean = _filtrar_calle_diccionario(cn)
    if cn_clean and cn_clean != cn:
        result = buscar_en_calle(cn_clean, num, block_idx)
        if result:
            return result
    
    # Paso 3: token containment contra todas las calles del catastro
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
                # Bonus: catastro street that has PHs on the comparable's block
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
    print('=' * 60)
    print('TAREA-020: Corregir coordenadas cache via centroide')
    print('=' * 60)
    print()
    
    # Paso 1: Backup
    print('[1] Haciendo backup...')
    backup_path = CACHE_PATH + '.bak'
    if not os.path.exists(backup_path):
        import shutil
        shutil.copy2(CACHE_PATH, backup_path)
        print('  Backup -> %s' % backup_path)
    else:
        print('  Backup ya existe: %s' % backup_path)
    
    # Paso 2: Cargar geometrias
    print()
    print('[2] Cargando geometria de parcelas y computando centroides...')
    t0 = time.time()
    centroid_index = cargar_centroides()
    t1 = time.time()
    print('  Tiempo: %.1fs' % (t1 - t0))
    
    # Paso 3: Cargar catastro
    print()
    print('[3] Cargando catastro...')
    exact_idx, block_idx, calle_tokens = cargar_indice_catastro()
    print('  PHs en indice exacto: %d' % len(exact_idx))
    print('  Calles en indice por bloque: %d' % len(block_idx))
    
    # Paso 4: Cargar cache
    print()
    print('[4] Cargando cache_scraping.json...')
    with open(CACHE_PATH, encoding='utf-8') as f:
        cache = json.load(f)
    props = cache['propiedades']
    print('  Propiedades: %d' % len(props))
    
    # Paso 5: Corregir coordenadas
    print()
    print('[5] Corrigiendo coordenadas...')
    stats = {
        'total': len(props),
        'con_calle_num': 0,
        'ph_encontrado': 0,
        'centroide_encontrado': 0,
        'corregido': 0,
        'sin_cambio': 0,
        'sin_ph': 0,
        'sin_centroide': 0,
        'error_acumulado': 0,
        'max_error_antes': 0,
        'max_error_despues': 0,
        'max_error_dir': '',
    }
    
    corregidos_muestra = []
    
    for p in props:
        addr = p.get('direccion', '')
        cn, num = extraer_calle_numero(addr)
        if not cn or num is None:
            continue
        stats['con_calle_num'] += 1
        
        ph_info = buscar_ph(cn, num, exact_idx, block_idx, calle_tokens)
        if not ph_info:
            stats['sin_ph'] += 1
            continue
        stats['ph_encontrado'] += 1
        
        sec, man, graf, ph_num, ph_lat, ph_lon = ph_info
        if sec is None:
            stats['sin_centroide'] += 1
            continue
        
        # Buscar centroide: preferir carpeta=ph_num, fallback a carpeta=0
        centroid = centroid_index.get((sec, man, graf, ph_num))
        if centroid is None:
            centroid = centroid_index.get((sec, man, graf, 0))
        if centroid is None:
            # Try any carpeta
            for key, val in centroid_index.items():
                if key[0] == sec and key[1] == man and key[2] == graf:
                    centroid = val
                    break
        if centroid is None:
            stats['sin_centroide'] += 1
            continue
        
        stats['centroide_encontrado'] += 1
        
        cache_lat = p.get('lat')
        cache_lon = p.get('lon')
        if cache_lat is None or cache_lon is None:
            continue
        
        d_antes = distancia(cache_lat, cache_lon, centroid[0], centroid[1])
        stats['error_acumulado'] += d_antes
        if d_antes > stats['max_error_antes']:
            stats['max_error_antes'] = d_antes
            stats['max_error_dir'] = addr[:60]
        
        if d_antes > 60:
            p['lat'] = centroid[0]
            p['lon'] = centroid[1]
            stats['corregido'] += 1
            if len(corregidos_muestra) < 20:
                corregidos_muestra.append({
                    'dir': addr[:60],
                    'ph': ph_num,
                    'd_antes': round(d_antes, 1),
                    'antiguo': (round(cache_lat, 6), round(cache_lon, 6)),
                    'nuevo': (round(centroid[0], 6), round(centroid[1], 6)),
                })
        else:
            stats['sin_cambio'] += 1
    
    # Paso 6: Guardar
    print()
    print('[6] Guardando cache corregido...')
    with open(CACHE_PATH, 'w', encoding='utf-8') as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    print('  Guardado correctamente')
    
    # Stats
    print()
    print('=' * 60)
    print('RESUMEN')
    print('=' * 60)
    print('  Total propiedades:            %d' % stats['total'])
    print('  Con (calle, num) valido:      %d' % stats['con_calle_num'])
    print('  PH encontrado en catastro:    %d' % stats['ph_encontrado'])
    print('  Centroide encontrado:         %d' % stats['centroide_encontrado'])
    print('  ---')
    print('  Corregidos (>60m):            %d' % stats['corregido'])
    print('  Sin cambio (<=60m):           %d' % stats['sin_cambio'])
    print('  Sin PH en catastro:           %d' % stats['sin_ph'])
    print('  Sin centroide en geometria:   %d' % stats['sin_centroide'])
    if stats['corregido'] > 0:
        print('  Error promedio antes:         %.0fm' % (stats['error_acumulado'] / stats['centroide_encontrado']))
        print('  Max error antes:              %.0fm (%s)' % (stats['max_error_antes'], stats['max_error_dir']))
    
    print()
    print('Muestra de correcciones (primeros %d):' % len(corregidos_muestra))
    print('  %-50s %-5s %-8s %s' % ('Direccion', 'PH', 'Dist_ant', 'Nuevo coords'))
    print('  ' + '-' * 80)
    for m in corregidos_muestra:
        print('  %-50s %-5d %-8.0f (%.6f, %.6f)' % (m['dir'][:50], m['ph'], m['d_antes'], m['nuevo'][0], m['nuevo'][1]))

if __name__ == '__main__':
    main()
