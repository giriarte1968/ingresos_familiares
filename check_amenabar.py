import json
import math

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    lat1_r, lat2_r = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(lat1_r) * math.cos(lat2_r) * math.sin(dlon/2)**2
    return 2 * R * math.asin(math.sqrt(a))

anclas = json.load(open('anclas_rosario_v2_grid.json'))['anclas']
amenabar_lat, amenabar_lon = -32.9739902, -60.6347712

print("Amenabar 5358 (lat:-32.9739902, lon:-60.6347712)")
print("-" * 50)

# Filtrar anclas oeste
oeste = [a for a in anclas if 'zona_oeste' in a['id']]
for a in oeste:
    d = haversine(amenabar_lat, amenabar_lon, a['lat'], a['lon'])
    print(f"{a['id']}: ${a['usd_m2']}/m2 a {d:.3f}km")

print("\n--- Todas las anclas ordenadas por distancia ---")
distancias = [(a['id'], a['usd_m2'], haversine(amenabar_lat, amenabar_lon, a['lat'], a['lon'])) for a in anclas]
for aid, ausd, dist in sorted(distancias, key=lambda x: x[2])[:10]:
    print(f"{aid}: ${ausd}/m2 a {dist:.3f}km")