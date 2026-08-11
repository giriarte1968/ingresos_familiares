import json

barreras_data = json.load(open('barreras_rosario.json', 'r', encoding='utf-8'))
for f in barreras_data.get('features', []):
    props = f.get('properties', {})
    geom = f.get('geometry', {})
    gtype = geom.get('type')
    coords = geom.get('coordinates', [])
    print(f"Feature name: {props.get('name')} | type: {gtype} | n_coords: {len(coords)}")
