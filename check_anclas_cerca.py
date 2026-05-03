import json
import math

anclas = json.load(open('anclas_rosario_v2_grid.json'))['anclas']
lat, lon = -32.9541101, -60.6316406

print(f"Coordenadas Mabel: lat={lat}, lon={lon}")
print("\nAnclas cercanas:")

for a in anclas:
    d = 2*6371*math.asin(math.sqrt(
        math.sin((a['lat']-lat)*math.pi/360)**2 + 
        math.cos(lat*math.pi/180)*math.cos(a['lat']*math.pi/180)*
        math.sin((a['lon']-lon)*math.pi/360)**2
    ))
    if d < 0.5:
        print(f"  {a['id']}: {a['usd_m2']}/m2 a {d:.3f}km")