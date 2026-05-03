from geopy.geocoders import Nominatim
import time

g = Nominatim(user_agent='test')

# Test 3 de Febrero 520
r = g.geocode('3 de Febrero 520, Rosario, Santa Fe, Argentina')
print(f"3 de Febrero 520:")
print(f"  lat: {r.latitude}, lon: {r.longitude}")
print(f"  address: {r.address}")

time.sleep(0.5)

# Test "3 de Febrero 520" vs "520 3 de Febrero"
r2 = g.geocode('520 3 de Febrero, Rosario, Santa Fe, Argentina')
print(f"\n520 3 de Febrero:")
print(f"  lat: {r2.latitude}, lon: {r2.longitude}")