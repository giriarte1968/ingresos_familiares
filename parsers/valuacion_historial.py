import json
import os
import shutil
import hashlib
from datetime import datetime

HISTORIAL_PATH = "data/valuaciones_historial.jsonl"
SCRAPING_HISTORY_DIR = "data/scraping_history"
SCRAPING_ACTUAL_PATH = "cache_scraping.json"

def _generar_id_evento(nombre: str) -> str:
    """Genera un ID único para cada evento de valuación."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"val_{ts}_{nombre.replace(' ', '_')}"

def _hash_archivo(filepath: str) -> str:
    """Hash MD5 del contenido de un archivo."""
    try:
        if not os.path.exists(filepath):
            return "not_found"
        with open(filepath, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()[:12]
    except:
        return "unknown"

def _guardar_snapshot_scraping(hash_scraping: str) -> str:
    """
    Si el scraping actual no tiene snapshot guardado,
    lo copia a scraping_history/ con el hash como identificador.
    Retorna el nombre del archivo.
    """
    os.makedirs(SCRAPING_HISTORY_DIR, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_archivo = f"scraping_{timestamp}_{hash_scraping}.json"
    destino = os.path.join(SCRAPING_HISTORY_DIR, nombre_archivo)

    # Buscar si ya existe un snapshot de este hash
    if os.path.exists(SCRAPING_HISTORY_DIR):
        for archivo in os.listdir(SCRAPING_HISTORY_DIR):
            if hash_scraping in archivo:
                return archivo  # Ya existe, no duplicar

    # Guardar nuevo snapshot
    try:
        if os.path.exists(SCRAPING_ACTUAL_PATH):
            shutil.copy2(SCRAPING_ACTUAL_PATH, destino)
            return nombre_archivo
        return "no_cache_scraping"
    except Exception as e:
        return f"error_{e}"

def registrar_valuacion(
    nombre: str,
    prop: dict,
    resultado: dict,
    razon: str,
    fecha_ref: str = None
):
    """
    Registra una valuación en el historial de forma append-only.
    Cada llamada agrega UNA línea al archivo JSONL.
    NUNCA sobreescribe registros anteriores.
    """
    data_dir = os.path.dirname(HISTORIAL_PATH)
    if data_dir:
        os.makedirs(data_dir, exist_ok=True)

    # Snapshot del scraping actual
    hash_scraping = _hash_archivo(SCRAPING_ACTUAL_PATH)
    archivo_scraping = _guardar_snapshot_scraping(hash_scraping)

    # Construir registro
    meta = resultado.get('resolution_metadata', {})
    rango = resultado.get('rango_venta', {})
    
    # Ensure nested dicts exist
    if not isinstance(meta, dict): meta = {}
    if not isinstance(rango, dict): rango = {}

    registro = {
        "id": _generar_id_evento(nombre),
        "timestamp": datetime.now().isoformat(),
        "fecha_ref": fecha_ref or datetime.now().strftime("%Y-%m"),
        "propiedad": nombre,
        "razon_recalculo": razon,

        "snapshot_propiedad": {
            k: prop.get(k) for k in [
                'nombre', 'zona', 'tipo_inmueble', 'direccion',
                'lat', 'lon', 'm2_cubiertos', 'm2_semicubiertos',
                'm2_descubiertos_propios', 'm2_descubiertos_comun_exclusivo',
                'm2_comunes', 'dormitorios', 'banos', 'piso', 'total_pisos',
                'anio_construccion', 'estado_detalle', 'calidad_edificio',
                'ventilacion', 'tipo_balcon', 'ubicacion_tipo', 'vista',
                'orientacion', 'descripcion_libre', 'valor_compra_usd',
                'fecha_compra'
            ]
        },

        "snapshot_mercado": {
            "dolar_binance": resultado.get('dolar_binance', 0),
            "fecha_ref": fecha_ref,
            "hash_scraping": hash_scraping,
            "archivo_scraping": archivo_scraping,
            "n_comparables_venta": meta.get('n_propiedades', 0),
            "n_comparables_alquiler": resultado.get(
                'cap_rate_info', {}
            ).get('n_alquiler', 0),
            "radio_usado": meta.get('radio_usado', 300),
            "m2_base_venta": resultado.get('m2_base_venta', 0),
            "percentil_usado": meta.get('percentil_usado', 'P33'),
            "alpha_soft": meta.get('alpha_soft', 0.7),
            "es_fallback_alquiler": resultado.get('es_fallback_alquiler', False)
        },

        "resultado": {
            "valor_venta": resultado.get('valor_propiedad_usd', 0),
            "valor_conservador": resultado.get('valor_venta_conservador', 0),
            "valor_mercado": resultado.get('valor_venta_mercado', resultado.get('valor_propiedad_usd', 0)),
            "valor_optimista": resultado.get('valor_venta_optimista', 0),
            "spread_pct": rango.get('spread_pct', 0),
            "valor_realizable": resultado.get('valor_realizable_usd', 0),
            "alquiler_mensual_ars": resultado.get('alquiler_estimado_ars', 0),
            "cap_rate": resultado.get('cap_rate', 0),
            "m2_equiv": resultado.get('m2_equivalentes', 0),
            "factor_total": resultado.get('factor_total', 0),
            "delta_anti": resultado.get('delta_anti', 0),
            "f_nlp": resultado.get('f_nlp', resultado.get('ajuste_nlp', 0) + 1.0),
            "suma_cruda": resultado.get('suma_cruda', 0),
            "size_discount_alquiler": resultado.get('size_discount_alquiler', 1.0)
        }
    }

    # Append al archivo JSONL (una línea por registro)
    with open(HISTORIAL_PATH, 'a', encoding='utf-8') as f:
        f.write(json.dumps(registro, ensure_ascii=False, default=str) + '\n')

def cargar_historial(propiedad: str = None, 
                     desde: str = None,
                     hasta: str = None,
                     limite: int = None) -> list:
    """
    Lee el historial de valuaciones.
    
    Args:
        propiedad: filtrar por nombre (None = todas)
        desde: timestamp ISO mínimo
        hasta: timestamp ISO máximo
        limite: máximo de registros (últimos N)
    
    Returns:
        Lista de registros ordenada por timestamp DESC
    """
    if not os.path.exists(HISTORIAL_PATH):
        return []

    registros = []
    with open(HISTORIAL_PATH, 'r', encoding='utf-8') as f:
        for linea in f:
            linea = linea.strip()
            if not linea:
                continue
            try:
                reg = json.loads(linea)
                if propiedad and reg.get('propiedad') != propiedad:
                    continue
                if desde and reg.get('timestamp', '') < desde:
                    continue
                if hasta and reg.get('timestamp', '') > hasta:
                    continue
                registros.append(reg)
            except json.JSONDecodeError:
                continue

    # Ordenar por timestamp DESC (más reciente primero)
    registros.sort(key=lambda r: r.get('timestamp', ''), reverse=True)

    if limite:
        return registros[:limite]

    return registros

def obtener_ultima_valuacion(propiedad: str) -> dict | None:
    """Retorna la valuación más reciente de una propiedad."""
    historial = cargar_historial(propiedad=propiedad, limite=1)
    return historial[0] if historial else None

def comparar_valuaciones(propiedad: str, id1: str, id2: str) -> dict:
    """
    Compara dos valuaciones de la misma propiedad.
    Retorna diferencias en los campos principales.
    """
    historial = cargar_historial(propiedad=propiedad)
    reg1 = next((r for r in historial if r['id'] == id1), None)
    reg2 = next((r for r in historial if r['id'] == id2), None)

    if not reg1 or not reg2:
        return {}

    campos = ['valor_venta', 'cap_rate', 'alquiler_mensual_ars',
              'm2_base_venta', 'dolar_binance']

    diferencias = {}
    for campo in campos:
        v1 = reg1.get('resultado', {}).get(campo) or reg1.get('snapshot_mercado', {}).get(campo)
        v2 = reg2.get('resultado', {}).get(campo) or reg2.get('snapshot_mercado', {}).get(campo)
        if v1 is not None and v2 is not None:
            try:
                v1_f = float(v1)
                v2_f = float(v2)
                diferencias[campo] = {
                    'antes': v1_f,
                    'despues': v2_f,
                    'variacion': v2_f - v1_f,
                    'pct': ((v2_f - v1_f) / v1_f * 100) if v1_f else 0
                }
            except:
                continue

    return {
        'id1': id1,
        'id2': id2,
        'ts1': reg1.get('timestamp'),
        'ts2': reg2.get('timestamp'),
        'diferencias': diferencias
    }

def listar_snapshots_scraping() -> list:
    """Lista todos los snapshots de scraping disponibles."""
    if not os.path.exists(SCRAPING_HISTORY_DIR):
        return []
    archivos = sorted([f for f in os.listdir(SCRAPING_HISTORY_DIR) if f.endswith('.json')], reverse=True)
    return [
        {
            'archivo': f,
            'fecha': f.split('_')[1] if '_' in f else '?',
            'hash': f.split('_')[-1].replace('.json', '') if '_' in f else '?',
            'tamanio_kb': round(
                os.path.getsize(os.path.join(SCRAPING_HISTORY_DIR, f)) / 1024, 1
            )
        }
        for f in archivos
    ]
