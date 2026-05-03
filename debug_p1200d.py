import json
from parsers.mercado_inmobiliario import (
    sanitizar_propiedad, calcular_m2_equivalentes, calcular_factores,
    calcular_base_calibrada, obtener_mediana_cluster
)
from parsers.nlp_inmobiliario import calcular_ajuste_nlp_detallado

# Cargar propiedad P1200
data = json.load(open('propiedades.json', 'r', encoding='utf-8'))
p1200 = [p for p in data['propiedades'] if p.get('id') == 'prop_b8ec28ba'][0]

print("=== RAW ===")
print(f"anio_construccion: {p1200.get('anio_construccion')}")

# Sanitizar
prop = sanitizar_propiedad(p1200)
print(f"\n=== SANITIZADO ===")
print(f"anio_construccion: {prop.get('anio_construccion')}")

# m2 equivalentes
m2_equiv = calcular_m2_equivalentes(prop)
print(f"\nm2_equiv: {m2_equiv}")

# Antigüedad dinámica
anio_const = prop.get('anio_construccion', 2026 - prop.get('antiguedad', 0))
antiguedad = 2026 - anio_const
prop['antiguedad'] = antiguedad

print(f"anio_const: {anio_const}, antiguedad: {antiguedad}")

# Factores
f_dict = calcular_factores(prop)
print(f"\n=== FACTORES ===")
print(f"total: {f_dict['total']}")
print(f"sqrt_factor: {f_dict['sqrt_factor']}")
print(f"depreciacion: {f_dict['depreciacion']}")

# Base calibrada
zona = prop.get('zona')
dorms = prop.get('dormitorios')
lat = prop.get('lat')
lon = prop.get('lon')
valor_ancla = prop.get('ancla_usd_m2', 1580)

m2_base, metodo = calcular_base_calibrada(valor_ancla, {
    'zona': zona, 'dormitorios': dorms, 'lat': lat, 'lon': lon, 'anio_construccion': anio_const
})

print(f"\n=== BASE ===")
print(f"m2_base: {m2_base}")

# Cluster
cluster_val, n = obtener_mediana_cluster(zona, dorms, 'venta')
print(f"cluster: {cluster_val} ({n} muestras)")

# NLP
desc = prop.get('descripcion_libre', '')
ajuste_nlp, _ = calcular_ajuste_nlp_detallado(desc)
print(f"NLP: {ajuste_nlp*100:.1f}%")

# Cálculo MANUAL
print(f"\n=== MANUAL ===")
valor = m2_equiv * m2_base * f_dict['total']
print(f"{m2_equiv} × {m2_base:.2f} × {f_dict['total']:.4f} = {valor:.0f}")

# Con NLP
valor_nlp = valor * (1 + ajuste_nlp)
print(f"Con NLP: {valor_nlp:.0f}")

# GAP cierre
valor_cierre = valor_nlp * 0.92
print(f"Cierre (-8%): {valor_cierre:.0f}")