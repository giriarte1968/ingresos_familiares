"""Gestión de comparables manuales — CRUD sobre cache_scraping.json."""
import json
import os
from datetime import datetime

_SCRAPING_PATH = "cache_scraping.json"
_FUENTE_MANUAL = "manual"


def load_data():
    if not os.path.exists(_SCRAPING_PATH):
        return {"fecha": datetime.now().isoformat(), "status": "manual_only", "propiedades": [], "next_manual_id": 1}
    with open(_SCRAPING_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_data(data):
    tmp = _SCRAPING_PATH + ".tmp"
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, _SCRAPING_PATH)


def _next_id(data):
    nid = data.get("next_manual_id", 1)
    data["next_manual_id"] = nid + 1
    return f"manual_{nid:05d}"


def get_manual_comparables(data=None):
    if data is None:
        data = load_data()
    return [p for p in data.get("propiedades", []) if p.get("fuente") == _FUENTE_MANUAL]


def get_scraping_comparables(data=None):
    if data is None:
        data = load_data()
    return [p for p in data.get("propiedades", []) if p.get("fuente") != _FUENTE_MANUAL]


def add_manual(form_data):
    data = load_data()
    mid = _next_id(data)
    now_iso = datetime.now().isoformat()
    precio = float(form_data.get("precio", 0))
    m2 = float(form_data.get("m2", 0))
    entry = {
        "id_manual": mid,
        "precio": precio,
        "moneda": form_data.get("moneda", "USD"),
        "m2": m2,
        "dormitorios": int(form_data.get("dormitorios", 1)),
        "tipo": form_data.get("tipo", "Departamento"),
        "operacion": form_data.get("operacion", "venta"),
        "direccion": form_data.get("direccion", ""),
        "calle_limpia": form_data.get("calle_limpia", "").strip().lower(),
        "numero_limpio": int(form_data.get("numero_limpio", 0)) if form_data.get("numero_limpio") else None,
        "lat": float(form_data.get("lat", 0)),
        "lon": float(form_data.get("lon", 0)),
        "valor_m2": round(precio / m2, 2) if m2 > 0 else 0,
        "fuente": _FUENTE_MANUAL,
        "date_created": now_iso,
        "date_updated": now_iso,
    }
    propiedades = data.setdefault("propiedades", [])
    propiedades.append(entry)
    save_data(data)
    return mid


def update_manual(manual_id, form_data):
    data = load_data()
    propiedades = data.get("propiedades", [])
    for p in propiedades:
        if p.get("id_manual") == manual_id:
            precio = float(form_data.get("precio", p["precio"]))
            m2 = float(form_data.get("m2", p["m2"]))
            p["precio"] = precio
            p["moneda"] = form_data.get("moneda", p["moneda"])
            p["m2"] = m2
            p["dormitorios"] = int(form_data.get("dormitorios", p["dormitorios"]))
            p["tipo"] = form_data.get("tipo", p["tipo"])
            p["operacion"] = form_data.get("operacion", p["operacion"])
            p["direccion"] = form_data.get("direccion", p.get("direccion", ""))
            p["calle_limpia"] = form_data.get("calle_limpia", p.get("calle_limpia", "")).strip().lower()
            p["numero_limpio"] = int(form_data.get("numero_limpio", 0)) if form_data.get("numero_limpio") else p.get("numero_limpio")
            p["lat"] = float(form_data.get("lat", p["lat"]))
            p["lon"] = float(form_data.get("lon", p["lon"]))
            p["valor_m2"] = round(precio / m2, 2) if m2 > 0 else 0
            p["date_updated"] = datetime.now().isoformat()
            save_data(data)
            return True
    return False


def delete_manual(manual_id):
    data = load_data()
    propiedades = data.get("propiedades", [])
    antes = len(propiedades)
    data["propiedades"] = [p for p in propiedades if p.get("id_manual") != manual_id]
    if len(data["propiedades"]) < antes:
        save_data(data)
        return True
    return False
