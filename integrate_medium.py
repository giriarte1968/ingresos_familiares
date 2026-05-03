import json
import os

BASE_DIR = "C:/Users/Gustavo/ingresos_familiares_st"

with open(f"{BASE_DIR}/anclas_rosario_v2_grid.json") as f:
    original = json.load(f)

original_anchors = original.get("anclas", original)

with open(f"{BASE_DIR}/new_anchors_20260422_0852.json") as f:
    new_anchors = json.load(f)

medium = [a for a in new_anchors if a['_meta']['confidence'] == 'MEDIUM']

print(f"Anclas originales: {len(original_anchors)}")
print(f"Anclas MEDIUM a agregar: {len(medium)}")

new_to_add = []
for a in medium:
    new_to_add.append({
        "id": a['id'],
        "lat": a['lat'],
        "lon": a['lon'],
        "usd_m2": a['usd_m2']
    })

final_anchors = original_anchors + new_to_add
print(f"Total final: {len(final_anchors)}")

original["anclas"] = final_anchors
original["fuente"] = "anclas_rosario_v3_grid.json"
original["config"] = original.get("config", {})
original["config"]["n_anclas_originales"] = len(original_anchors)
original["config"]["n_anclas_nuevas"] = len(new_to_add)
original["config"]["n_anclas_total"] = len(final_anchors)
original["config"]["audit_date"] = "20260422"

output_file = f"{BASE_DIR}/anclas_rosario_v3_grid.json"
with open(output_file, "w", encoding="utf-8") as f:
    json.dump(original, f, ensure_ascii=False, indent=2)

print(f"Guardado en: {output_file}")
print("Hecho!")