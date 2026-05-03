import json
with open('C:/Users/Gustavo/ingresos_familiares_st/new_anchors_20260422_0852.json') as f:
    new_anchors = json.load(f)
medium = [a for a in new_anchors if a['_meta']['confidence'] == 'MEDIUM']
print('Anclas MEDIUM:', len(medium))
for a in medium:
    print(f"{a['id']}: {a['lat']}, {a['lon']} -> {a['usd_m2']}")