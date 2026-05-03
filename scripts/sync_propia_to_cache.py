import json
import os
from datetime import datetime

def normalizar_zona(texto):
    if not texto: return 'Otro'
    texto = texto.lower()
    mapping = {
        'martin': 'Martin', 'centro': 'Centro', 'pellegrini': 'Pellegrini',
        'sexta': 'Sexta', 'abasto': 'Abasto', 'facultades': 'Facultades',
        'pichincha': 'Pichincha', 'puerto norte': 'Puerto Norte'
    }
    for k, v in mapping.items():
        if k in texto: return v
    return 'Otro'

def deduplicar(props):
    best_props = {}
    for p in props:
        key = (int(p.get('precio', 0)), int(p.get('m2', 0)), p.get('zona', ''))
        
        # Priorizar registro que tenga coordenadas
        has_coords = p.get('lat') is not None and p.get('lon') is not None
        
        if key not in best_props:
            best_props[key] = p
        else:
            existing_has_coords = best_props[key].get('lat') is not None and best_props[key].get('lon') is not None
            if has_coords and not existing_has_coords:
                best_props[key] = p
                
    return list(best_props.values())

def curar_propiedad(p):
    try:
        precio = float(p.get('precio', 0))
        m2 = float(p.get('m2', 0))
        operacion = p.get('operacion', 'venta').lower()
        if m2 <= 20 or m2 >= 500: return None
        valor_m2 = precio / m2 if m2 > 0 else 0
        if operacion == 'venta':
            if precio < 10000: return None
            if not (400 <= valor_m2 <= 4000): return None
        else:
            if not (40000 <= precio <= 1000000): return None
        
        lat = p.get('latitude')
        lon = p.get('longitude')
        
        return {
            'precio': precio,
            'm2': m2,
            'dormitorios': p.get('dormitorios') or 1,
            'tipo': p.get('tipo', 'desconocido'),
            'operacion': operacion,
            'direccion': p.get('direccion', ''),
            'url': p.get('url', ''),
            'valor_m2': valor_m2,
            'fuente': p.get('fuente', 'propia'),
            'id_propia': p.get('id_propia'),
            'lat': lat,
            'lon': lon,
            'zona': normalizar_zona(p.get('direccion', ''))
        }
    except:
        return None

def sincronizar_propia_a_cache():
    path_propia = r'C:\Users\Gustavo\ingresos_familiares_st\propia.json'
    path_cache = r'C:\Users\Gustavo\ingresos_familiares_st\cache_scraping.json'
    with open(path_propia, 'r', encoding='utf-8') as f:
        data_propia = json.load(f)
    with open(path_cache, 'r', encoding='utf-8') as f:
        data_cache = json.load(f)
    props_propia = data_propia.get('propiedades', [])
    props_cache = data_cache.get('propiedades', []) if isinstance(data_cache, dict) else data_cache
    curadas = []
    for p in props_propia:
        cp = curar_propiedad(p)
        if cp: curadas.append(cp)
    
    print('Curadas: ' + str(len(curadas)))
    
    total = deduplicar(props_cache + curadas)
    resultado = {
        'fecha': datetime.now().isoformat(),
        'status': 'consolidado_propia_coords_v3',
        'propiedades': total
    }
    with open(path_cache, 'w', encoding='utf-8') as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)
    print('Sincronizacion completada. Total: ' + str(len(total)))

if __name__ == '__main__':
    sincronizar_propia_a_cache()
