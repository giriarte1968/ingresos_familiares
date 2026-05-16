import os
import sys
import json

# Añadir directorio raíz al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from parsers.motor_vpp_core import valuar_con_cache

def force_recalc(nombre_prop):
    # Cargar propiedades para encontrar la que queremos
    PROPIEDADES_FILE = "propiedades.json"
    if not os.path.exists(PROPIEDADES_FILE):
        print("Error: propiedades.json no encontrado")
        return

    with open(PROPIEDADES_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        if isinstance(data, dict):
            propiedades = data.get('propiedades', [])
        else:
            propiedades = data
    
    prop = next((p for p in propiedades if p['nombre'] == nombre_prop), None)
    if not prop:
        print(f"Error: Propiedad '{nombre_prop}' no encontrada")
        return

    print(f"Forzando recalculo para {nombre_prop}...")
    res = valuar_con_cache(prop, forzar_recalculo=True)
    
    print("Resultado:")
    print(f"  Valor Venta: ${res.get('valor_propiedad_usd', 0):,.0f}")
    print(f"  Timestamp: {res.get('_cache', {}).get('timestamp')}")
    
    HISTORIAL_PATH = "data/valuaciones_historial.jsonl"
    if os.path.exists(HISTORIAL_PATH):
        with open(HISTORIAL_PATH, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            if lines:
                last_event = json.loads(lines[-1])
                print(f"[OK] Evento registrado en historial: {last_event['id']} ({last_event['timestamp']})")
                print(f"   Propiedad: {last_event['propiedad']}")
                print(f"   Valor Mercado: ${last_event['resultado']['valor_mercado']:,.0f}")
                print(f"   Motivo: {last_event['razon_recalculo']}")
            else:
                print("[ERROR] El historial esta vacio.")
    else:
        print("[ERROR] Archivo de historial no encontrado.")

if __name__ == "__main__":
    force_recalc("Mabel")
