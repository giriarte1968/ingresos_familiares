from geopy.geocoders import Nominatim
import time

geolocator = Nominatim(user_agent="rosario_test")

direcciones = [
    "Amenabar 5358, Rosario, Santa Fe, Argentina",
    "Avenida Amenabar 5358, Rosario, Santa Fe, Argentina",
    "Amenabar y Mendoza, Rosario, Santa Fe, Argentina",
    "Amenabar 5300, Rosario, Santa Fe, Argentina",
    "Bulevar Amenabar 5358, Rosario, Santa Fe, Argentina",
]

for direccion in direcciones:
    print(f"\n{direccion}")
    try:
        result = geolocator.geocode(direccion)
        if result:
            print(f"  -> lat: {result.latitude}, lon: {result.longitude}")
        else:
            print(f"  -> No encontrado")
    except Exception as e:
        print(f"  Error: {e}")
    time.sleep(0.5)