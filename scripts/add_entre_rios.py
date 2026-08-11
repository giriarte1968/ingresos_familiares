#!/usr/bin/env python3
"""Agrega Entre Rios 1372 a propiedades.json"""
import json, uuid, os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
path = os.path.join(BASE_DIR, "propiedades.json")

with open(path, encoding="utf-8") as f:
    data = json.load(f)

new_id = "prop_" + uuid.uuid4().hex[:8]

new_prop = {
    "nombre": "Entre Rios 1372",
    "tipo_inmueble": "departamento",
    "zona": "Centro",
    "direccion": "Entre Rios 1372",
    "lat": -32.9530046,
    "lon": -60.6427417,
    "ubicacion_tipo": "calle",
    "m2_cubiertos": 73.24,
    "m2_semicubiertos": 8.88,
    "m2_descubiertos_propios": 21.47,
    "m2_descubiertos_comun_exclusivo": 0.0,
    "dormitorios": 2,
    "ambientes": 2,
    "banos": 1,
    "toilet": True,
    "banio_servicio": False,
    "anio_construccion": 1965,
    "constructora": "",
    "piso": 2,
    "total_pisos": 0,
    "vista": "frente",
    "gas_ok": "si",
    "balcon": False,
    "tipo_balcon": "terraza",
    "orientacion": "este",
    "ventilacion": "cruzada",
    "estado_detalle": "regular",
    "calidad_edificio": "media",
    "seguridad": "ninguna",
    "terminaciones_suelo": "ceramico",
    "carpinteria": "estandar",
    "terminaciones_cocina": "estandar",
    "preinstalacion_aa": False,
    "cocheras_cantidad": 0,
    "cocheras_tipo": "cubierta",
    "valor_cochera_base": 0.0,
    "valor_baulera": 0.0,
    "doble_ingreso": True,
    "lavadero_independiente": True,
    "reciclado": False,
    "reciclado_tipo": "ninguno",
    "anio_reciclado": None,
    "ventilacion_bano": "natural",
    "layout_flexible": False,
    "placares_completos": True,
    "despensa": True,
    "ascensores_edificio": 0,
    "detalles_categoria": [],
    "descripcion_libre": "Departamento tipo ph, 2do piso de escalera, construccion solida pero precisa reparaciones. Dormitorio secundario con ventilacion a aire luz, sector de guardado con bano de servicio, dos dormitorios comodos, uno a la calle living con salida al balcon y cocina con ventilacion al aire luz.",
    "valor_compra_usd": 0.0,
    "fecha_compra": "2026-01-01",
    "fecha_publicacion": "2026-08-11",
    "expensas_ars": 0,
    "id": new_id,
    "cochera": False,
    "disposicion": "frente",
}

data["propiedades"].append(new_prop)

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print(f"Added: {new_prop['nombre']} (id={new_id})")
print(f"Coords: {new_prop['lat']}, {new_prop['lon']}")
print(f"Total properties: {len(data['propiedades'])}")
