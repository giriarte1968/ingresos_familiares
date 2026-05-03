import json
import os

# Load cache
cache_path = "C:/Users/Gustavo/ingresos_familiares_st/cache_scraping.json"
with open(cache_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

props = data.get('propiedades', [])
print(f"Total props before cleaning: {len(props)}")

# Absolute filter: remove properties with valor_m2 outside [400, 5000]
props_filtrados = [p for p in props if 400 <= p.get('valor_m2', 0) <= 5000]
print(f"Props after absolute filter: {len(props_filtrados)}")
print(f"Removed {len(props) - len(props_filtrados)} outliers")

# Update cache
data['propiedades'] = props_filtrados
with open(cache_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Cache cleaned and saved!")
