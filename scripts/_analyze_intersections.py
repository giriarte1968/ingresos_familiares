"""
Analyze intersection entries in cache_scraping.json.
Count PHs at each intersection using geometry centroids.
"""
import json, os, glob, math, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from parsers.mercado_inmobiliario import extraer_calle_numero, _filtrar_calle_diccionario, _token_contenido
import pandas as pd

PROJECT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def distancia(lat1, lon1, lat2, lon2):
    R = 6371000
    lat1_r, lon1_r = math.radians(lat1), math.radians(lon1)
    lat2_r, lon2_r = math.radians(lat2), math.radians(lon2)
    dlat, dlon = lat2_r - lat1_r, lon2_r - lon1_r
    a = math.sin(dlat/2)**2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

# ---- Load catastro ----
CATASTRO_PATH = os.path.join(PROJECT, 'data', 'rosario_avm_full.csv')
df_cat = pd.read_csv(CATASTRO_PATH)

catastro_phs = []
calle_tokens = {}
for _, row in df_cat.iterrows():
    cn, num = extraer_calle_numero(str(row.get('direccion_nominatim', '')))
    if cn and num is not None:
        lat, lon = row['latitud'], row['longitud']
        catastro_phs.append({
            'ph': int(row['ph']),
            'lat': lat,
            'lon': lon,
            'calle': cn,
            'seccion': int(row['seccion']) if not math.isnan(row['seccion']) else None,
            'manzana': int(row['manzana']) if not math.isnan(row['manzana']) else None,
            'grafico': int(row['grafico']) if not math.isnan(row['grafico']) else None,
        })
        if cn not in calle_tokens:
            calle_tokens[cn] = set(cn.split())

def street_matches_ph(ph_calle, target_calle):
    ph_tokens = ph_calle.split()
    target_tokens = target_calle.split()
    return _token_contenido(ph_tokens, target_tokens) or _token_contenido(target_tokens, ph_tokens)

# ---- Load cache ----
with open(os.path.join(PROJECT, 'cache_scraping.json'), encoding='utf-8') as f:
    cache = json.load(f)
props = cache['propiedades']

with open(os.path.join(PROJECT, 'data', 'calles_rosario.json'), encoding='utf-8') as f:
    CALLES_SET = set(json.load(f))

INT_SEPS = [' y ', ' esq ', ' esq. ', ' esq, ', ' esquina ', ' e/ ']
_RE_E_WORD = re.compile(r'\be\b')

def match_street_by_token(street_tokens):
    best = None
    best_score = 0.0
    for cat_cn, tokens in calle_tokens.items():
        tok_list = list(tokens)
        if _token_contenido(street_tokens, tok_list):
            cat_tokens_set = set(tokens)
            overlap = len(set(street_tokens) & cat_tokens_set)
            score = overlap / max(len(street_tokens), len(tok_list))
            if score > best_score and score >= 0.5:
                best_score = score
                best = cat_cn
    return best

def parse_street(raw_part):
    cn, num = extraer_calle_numero(raw_part)
    if not cn or len(cn) < 4:
        return None
    cn2 = _filtrar_calle_diccionario(cn)
    candidate = cn2 if cn2 and len(cn2) >= 4 else cn
    matched = match_street_by_token(candidate.split())
    if matched:
        return matched
    if candidate in CALLES_SET:
        return candidate
    return None

# Find intersection entries
intersection_entries = []
for p in props:
    addr = p.get('direccion', '')
    if not isinstance(addr, str) or not addr.strip():
        continue
    addr_lower = addr.lower().strip()
    found_sep = None
    for sep in INT_SEPS:
        if sep in addr_lower:
            found_sep = sep
            break
    if found_sep is None and _RE_E_WORD.search(addr_lower):
        found_sep = 'e-word'
    if found_sep is None:
        continue
    s = addr_lower
    if found_sep == 'e-word':
        parts = re.split(r'\be\b', s, maxsplit=1)
    else:
        parts = s.split(found_sep, 1)
    streets = []
    for part in parts:
        part = part.strip()
        if part:
            s_name = parse_street(part)
            if s_name:
                streets.append(s_name)
    if len(streets) >= 2:
        intersection_entries.append((addr, found_sep, streets[0], streets[1], p))

unique_pairs = set()
pair_to_entries = {}
for raw, sep, s1, s2, entry in intersection_entries:
    pair = tuple(sorted([s1, s2]))
    unique_pairs.add(pair)
    if pair not in pair_to_entries:
        pair_to_entries[pair] = []
    pair_to_entries[pair].append((raw, entry))

print(f"=== INTERSECTION ANALYSIS ===")
print(f"Total cache entries: {len(props)}")
print(f"Entries with intersection format: {len(intersection_entries)}")
print(f"Unique intersection pairs: {len(unique_pairs)}")
print()

# ---- For each pair, count PHs within 60m ----
MAX_DIST = 60.0

results = {}
candidate_singles = []

for pair in sorted(unique_pairs):
    s1, s2 = pair
    phs_s1 = [ph for ph in catastro_phs if street_matches_ph(ph['calle'], s1)]
    phs_s2 = [ph for ph in catastro_phs if street_matches_ph(ph['calle'], s2)]
    if not phs_s1 or not phs_s2:
        continue
    phs_at_intersection = set()
    for ph1 in phs_s1:
        for ph2 in phs_s2:
            d = distancia(ph1['lat'], ph1['lon'], ph2['lat'], ph2['lon'])
            if d <= MAX_DIST:
                phs_at_intersection.add(ph1['ph'])
                phs_at_intersection.add(ph2['ph'])
    total = len(phs_at_intersection)
    results[pair] = {
        'total': total,
        'phs_s1': len(phs_s1),
        'phs_s2': len(phs_s2),
        'ph_ids': sorted(phs_at_intersection),
        'examples': pair_to_entries[pair][:3],
    }
    if total == 1:
        candidate_singles.append((pair, results[pair]))

# Print 3: PH counts
print("3. PH counts at each intersection (sorted by count, descending):")
print(f"   (MAX_DIST = {MAX_DIST}m)")
print()
sorted_pairs = sorted(results.items(), key=lambda x: -x[1]['total'])
for pair, info in sorted_pairs:
    if info['total'] > 0:
        s1, s2 = pair
        print(f"  {s1:35s} x {s2:35s} | PHs: {info['total']:3d} | (s1:{info['phs_s1']:3d}, s2:{info['phs_s2']:3d})")

zeros = sum(1 for v in results.values() if v['total'] == 0)
nonzeros = sum(1 for v in results.values() if v['total'] > 0)
print()
print(f"  Pairs with PHs at intersection: {nonzeros}")
print(f"  Pairs with 0 PHs: {zeros}")

# Print 4: single PHs
print()
print("4. Intersections with EXACTLY 1 PH (candidates):")
print(f"   Count: {len(candidate_singles)}")
print()
for pair, info in candidate_singles:
    s1, s2 = pair
    ph_id = info['ph_ids'][0]
    ph_info = [ph for ph in catastro_phs if ph['ph'] == ph_id]
    if ph_info:
        ph = ph_info[0]
        print(f"  {s1:30s} x {s2:30s} -> PH#{ph_id} ({ph['calle']}) at ({ph['lat']:.5f}, {ph['lon']:.5f})")
    else:
        print(f"  {s1:30s} x {s2:30s} -> PH#{ph_id}")
    for raw, _ in info['examples']:
        print(f"    e.g.: {raw[:90]}")
    print()

twos = [(p, v) for p, v in results.items() if v['total'] == 2]
print(f"  Intersections with exactly 2 PHs: {len(twos)}")
for pair, info in twos[:15]:
    s1, s2 = pair
    print(f"  {s1:30s} x {s2:30s}  PH ids: {info['ph_ids']}")

# Print 5: examples
print()
print("5. Examples: cache entry -> parsed streets -> PH mapping")
count = 0
for pair, info in candidate_singles[:5]:
    s1, s2 = pair
    for raw, entry in info['examples'][:2]:
        ph_id = info['ph_ids'][0]
        ph_info = [ph for ph in catastro_phs if ph['ph'] == ph_id]
        if ph_info:
            ph = ph_info[0]
            print(f"  Address:  {raw[:80]}")
            print(f"  Streets:  {s1} x {s2}")
            print(f"  -> PH#{ph_id} ({ph['calle']}) at ({ph['lat']:.5f}, {ph['lon']:.5f})")
            print()
            count += 1
            if count >= 5:
                break
    if count >= 5:
        break
