# TAREA-153: Hacer barreras editables en UI

## Problema

Las barreras geográficas (`barreras_rosario.json`) están hardcodeadas. No hay forma de editarlas desde la UI sin modificar el archivo JSON directamente. Esto dificulta:
- Agregar/quitar barreras para zonas específicas
- Ajustar barreras para nuevas zonas
- Gestionar exclusiones por zona

## Solución

Crear un sistema de configuración de barreras que sea editable desde la UI.

## Archivos a Modificar

| Archivo | Cambio |
|---------|--------|
| `data/barreras_config.json` | **NUEVO** - Configuración de barreras por zona |
| `parsers/location_engine.py` | Leer exclusiones de config |
| `valu_forms.py` | Agregar UI para gestionar barreras |
| `valu_design.py` | Agregar sección de configuración de barreras |

## Diseño

### `data/barreras_config.json`
```json
{
  "barreras_excluidas_por_zona": {
    "Puerto Norte": {
      "Av. Francia": [115883685, 115883689, 256732599, ...],
      "Ferrocarril": []
    },
    "Pichincha": {
      "Av. del Valle": []
    }
  },
  "barreras_globales_excluidas": []
}
```

### `parsers/location_engine.py`
```python
def cargar_barreras(path=None, zona=None):
    barreras = _load_barreras(path)
    config = _load_barreras_config()
    
    if zona and zona in config.get('barreras_excluidas_por_zona', {}):
        excluded_ids = set()
        for barrier_name, ids in config['barreras_excluidas_por_zona'][zona].items():
            excluded_ids.update(ids)
        barreras = [b for b in barreras if b['properties']['id'] not in excluded_ids]
    
    return barreras
```

### UI (valu_forms.py)
- Agregar sección "Configuración de Barreras" en el sidebar
- Mostrar barreras activas por zona
- Permitir agregar/quitar IDs de barreras
- Botón "Guardar" que actualiza `barreras_config.json`

## Validación

1. `python scripts/auto_validate.py` → OK
2. `pytest tests/ -v` → 94+ tests pasan
3. UI muestra barreras configurables
4. Cambios en config afectan la valuación

## Commits

- Crear `data/barreras_config.json`
- Modificar `parsers/location_engine.py`
- Agregar UI en `valu_forms.py` y `valu_design.py`
- Tests y validación
