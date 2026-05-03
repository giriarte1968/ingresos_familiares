from parsers.location_engine import distancia

p1 = (-32.9541, -60.6316) # Mabel
p2 = (-32.9603, -60.6299) # Ayacucho

d = distancia(p1[0], p1[1], p2[0], p2[1])
print(f"Distance Mabel to Ayacucho: {d:.4f} km")

p3 = (-32.93869, -60.660698) # Property 1 from cache
d2 = distancia(p1[0], p1[1], p3[0], p3[1])
print(f"Distance Mabel to Prop1: {d2:.4f} km")
