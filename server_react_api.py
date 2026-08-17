import json
import os
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# Catalogo de todos los caches de scraping registrados en la red inmobiliaria
DATASETS_CONFIG = {
    "rosario_principal": {
        "label": "Rosario - Cache Principal",
        "ciudad": "Rosario",
        "provincia": "Santa Fe",
        "path": r"C:\Users\Gustavo\ingresos_familiares_st\cache_scraping.json",
        "icon": "📍"
    },
    "rosario_secundario": {
        "label": "Rosario - Cache Secundario (100.000)",
        "ciudad": "Rosario",
        "provincia": "Santa Fe",
        "path": r"C:\Users\Gustavo\ingresos_familiares_st\cache_scraping_rosario_secundario.json",
        "icon": "🏢"
    },
    "rosario_terciario": {
        "label": "Rosario - Cache Terciario (100.000)",
        "ciudad": "Rosario",
        "provincia": "Santa Fe",
        "path": r"C:\Users\Gustavo\ingresos_familiares_st\cache_scraping_rosario_terciario.json",
        "icon": "🏬"
    },
    "santa_fe": {
        "label": "Santa Fe Capital (100.000)",
        "ciudad": "Santa Fe Capital",
        "provincia": "Santa Fe",
        "path": r"C:\Users\Gustavo\ingresos_familiares_st\cache_scraping_santa_fe.json",
        "icon": "🏛️"
    },
    "parana": {
        "label": "Paraná (100.000)",
        "ciudad": "Paraná",
        "provincia": "Entre Ríos",
        "path": r"C:\Users\Gustavo\ingresos_familiares_st\cache_scraping_parana.json",
        "icon": "🌊"
    },
    "rio_cuarto": {
        "label": "Río Cuarto (100.000)",
        "ciudad": "Río Cuarto",
        "provincia": "Córdoba",
        "path": r"C:\Users\Gustavo\ingresos_familiares_st\cache_scraping_rio_cuarto.json",
        "icon": "🌾"
    },
    "cordoba_part1": {
        "label": "Córdoba Capital - Vol. 1 (100.000)",
        "ciudad": "Córdoba Capital",
        "provincia": "Córdoba",
        "path": r"C:\Users\Gustavo\ingresos_familiares_st\cache_scraping_cordoba_part1.json",
        "icon": "🔔"
    },
    "cordoba_part2": {
        "label": "Córdoba Capital - Vol. 2 (100.000)",
        "ciudad": "Córdoba Capital",
        "provincia": "Córdoba",
        "path": r"C:\Users\Gustavo\ingresos_familiares_st\cache_scraping_cordoba_part2.json",
        "icon": "🔔"
    },
    "tucuman_part1": {
        "label": "San Miguel de Tucumán - Vol. 1 (100.000)",
        "ciudad": "San Miguel de Tucumán",
        "provincia": "Tucumán",
        "path": r"C:\Users\Gustavo\ingresos_familiares_st\cache_scraping_tucuman_part1.json",
        "icon": "🌲"
    },
    "tucuman_part2": {
        "label": "San Miguel de Tucumán - Vol. 2 (100.000)",
        "ciudad": "San Miguel de Tucumán",
        "provincia": "Tucumán",
        "path": r"C:\Users\Gustavo\ingresos_familiares_st\cache_scraping_tucuman_part2.json",
        "icon": "🌲"
    },
    "mendoza_part1": {
        "label": "Mendoza Capital - Vol. 1 (100.000)",
        "ciudad": "Mendoza Capital",
        "provincia": "Mendoza",
        "path": r"C:\Users\Gustavo\ingresos_familiares_st\cache_scraping_mendoza_part1.json",
        "icon": "🍷"
    },
    "mendoza_part2": {
        "label": "Mendoza Capital - Vol. 2 (100.000)",
        "ciudad": "Mendoza Capital",
        "provincia": "Mendoza",
        "path": r"C:\Users\Gustavo\ingresos_familiares_st\cache_scraping_mendoza_part2.json",
        "icon": "🍷"
    }
}

# Cache en memoria para carga ultra-rapida de archivos JSON
DATA_CACHE = {}

def get_dataset_props(key):
    if key in DATA_CACHE:
        return DATA_CACHE[key]
    
    cfg = DATASETS_CONFIG.get(key)
    if not cfg or not os.path.exists(cfg["path"]):
        return []
        
    try:
        with open(cfg["path"], 'r', encoding='utf-8') as f:
            data = json.load(f)
            props = data.get("propiedades", [])
            DATA_CACHE[key] = props
            return props
    except Exception as e:
        print(f"Error cargando dataset {key}: {e}")
        return []

class ReactAppAPIHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Silenciar logs http repetitivos
        pass

    def send_json_response(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Ruta API: /api/datasets
        if path == '/api/datasets':
            summary = []
            total_global = 0
            for k, cfg in DATASETS_CONFIG.items():
                exists = os.path.exists(cfg["path"])
                count = 0
                size_mb = 0.0
                if exists:
                    size_mb = round(os.path.getsize(cfg["path"]) / (1024 * 1024), 2)
                    props = get_dataset_props(k)
                    count = len(props)
                total_global += count
                summary.append({
                    "id": k,
                    "label": cfg["label"],
                    "ciudad": cfg["ciudad"],
                    "provincia": cfg["provincia"],
                    "icon": cfg["icon"],
                    "total": count,
                    "size_mb": size_mb,
                    "exists": exists
                })
            self.send_json_response({"datasets": summary, "total_global": total_global})
            return

        # Ruta API: /api/zones
        if path == '/api/zones':
            dataset_key = query.get('dataset', ['rosario_secundario'])[0]
            props = get_dataset_props(dataset_key)
            zonas = sorted(list(set(p.get("zona", "Otros") for p in props if p.get("zona"))))
            self.send_json_response({"dataset": dataset_key, "zonas": zonas})
            return

        # Ruta API: /api/properties
        if path == '/api/properties':
            dataset_key = query.get('dataset', ['rosario_secundario'])[0]
            page = int(query.get('page', [1])[0])
            limit = int(query.get('limit', [48])[0])
            search = query.get('search', [''])[0].strip().lower()
            tipo = query.get('tipo', ['todos'])[0].lower()
            operacion = query.get('operacion', ['todas'])[0].lower()
            zona = query.get('zona', ['todas'])[0]
            sort_by = query.get('sort_by', ['id'])[0]
            sort_order = query.get('sort_order', ['desc'])[0]

            min_precio = float(query.get('min_precio', [0])[0]) if query.get('min_precio') else None
            max_precio = float(query.get('max_precio', [0])[0]) if query.get('max_precio') else None

            props = get_dataset_props(dataset_key)

            # Filtrado de alta velocidad
            filtered = []
            for p in props:
                if tipo != 'todos' and p.get('tipo', '').lower() != tipo:
                    continue
                if operacion != 'todas' and p.get('operacion', '').lower() != operacion:
                    continue
                if zona != 'todas' and p.get('zona') != zona:
                    continue
                if min_precio is not None and min_precio > 0 and p.get('precio', 0) < min_precio:
                    continue
                if max_precio is not None and max_precio > 0 and p.get('precio', 0) > max_precio:
                    continue
                if search:
                    text = f"{p.get('direccion', '')} {p.get('zona', '')} {p.get('fuente', '')} {p.get('id_propia', '')}".lower()
                    if search not in text:
                        continue
                filtered.append(p)

            # Ordenamiento
            reverse = (sort_order == 'desc')
            if sort_by == 'precio':
                filtered.sort(key=lambda x: x.get('precio', 0), reverse=reverse)
            elif sort_by == 'valor_m2':
                filtered.sort(key=lambda x: x.get('valor_m2', 0), reverse=reverse)
            elif sort_by == 'm2':
                filtered.sort(key=lambda x: x.get('m2', 0), reverse=reverse)
            elif sort_by == 'dormitorios':
                filtered.sort(key=lambda x: x.get('dormitorios', 0), reverse=reverse)
            else:
                filtered.sort(key=lambda x: x.get('id_propia', 0), reverse=reverse)

            total_matches = len(filtered)
            start_idx = (page - 1) * limit
            end_idx = start_idx + limit
            page_items = filtered[start_idx:end_idx]

            # Estadisticas agregadas para el subset filtrado
            avg_m2_price = round(sum(p.get('valor_m2', 0) for p in filtered if p.get('moneda') == 'USD') / max(1, len([p for p in filtered if p.get('moneda') == 'USD'])), 2)
            venta_count = len([p for p in filtered if p.get('operacion') == 'venta'])
            alquiler_count = len([p for p in filtered if p.get('operacion') == 'alquiler'])

            self.send_json_response({
                "dataset": dataset_key,
                "total": total_matches,
                "page": page,
                "limit": limit,
                "total_pages": (total_matches + limit - 1) // limit if total_matches > 0 else 1,
                "stats": {
                    "avg_m2_usd": avg_m2_price,
                    "venta_count": venta_count,
                    "alquiler_count": alquiler_count
                },
                "items": page_items
            })
            return

        # Servir archivos estaticos del frontend web (index.html, app.jsx, etc)
        web_dir = r"C:\Users\Gustavo\ingresos_familiares_st\web"
        req_path = path.lstrip('/')
        if not req_path:
            req_path = 'index.html'

        file_path = os.path.join(web_dir, req_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            content_type = 'text/html; charset=utf-8'
            if file_path.endswith('.js') or file_path.endswith('.jsx'):
                content_type = 'application/javascript; charset=utf-8'
            elif file_path.endswith('.css'):
                content_type = 'text/css; charset=utf-8'
            elif file_path.endswith('.json'):
                content_type = 'application/json; charset=utf-8'

            with open(file_path, 'rb') as f:
                content = f.read()

            self.send_response(200)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            self.send_response(404)
            self.end_headers()

def run_server(port=8050):
    os.makedirs(r"C:\Users\Gustavo\ingresos_familiares_st\web", exist_ok=True)
    server_address = ('', port)
    httpd = HTTPServer(server_address, ReactAppAPIHandler)
    print("=" * 70)
    print(f"SERVIDOR API REACT NATIVO CORRIENDO EN: http://localhost:{port}")
    print("=" * 70)
    httpd.serve_forever()

if __name__ == '__main__':
    run_server(8050)
