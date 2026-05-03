import json
with open('propiedades.json') as f:
    data = json.load(f)
mabel = next(p for p in data['propiedades'] if p.get('nombre') == 'Mabel')
print("estado_detalle:", mabel.get('estado_detalle'))
print("ventilacion:", mabel.get('ventilacion'))
print("descripcion_libre:", mabel.get('descripcion_libre'))
print("vista:", mabel.get('vista'))
print("piso:", mabel.get('piso'))
print("calidad_edificio:", mabel.get('calidad_edificio'))