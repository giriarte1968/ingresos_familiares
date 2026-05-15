"""
Comparación de valores de mercado scraping VPP vs fuentes oficiales externas.
Genera reports/comparacion_scraping_vs_oficiales.csv

Uso: python scripts/comparar_scraping_vs_oficiales.py
"""
import json, os, sys, requests, re
import pandas as pd
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.chdir(BASE)

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

def obtener_scraping_zonal():
    """Lee anclas v4.1 temporal."""
    with open('data/anclas_rosario_v41_temporal.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    anclas = data['anclas'] if isinstance(data, dict) else data
    result = {}
    for a in anclas:
        nombre = a.get('id', a.get('nombre', ''))
        usd = a.get('usd_m2')
        if usd:
            result[nombre] = {
                'usd_m2_scraping': usd,
                'usd_m2_v3': a.get('usd_m2_v3', 0),
                'n': a.get('n_zonal', 0),
                'ventana': a.get('ventana_dias', 0),
                'estado': a.get('estado_revision', ''),
            }
    return result


def try_zonaprop_scraping():
    """Intenta obtener datos de Zonaprop para Rosario."""
    print("\n[ZONAPROP] Intentando obtener datos...")
    result = {'fuente': 'Zonaprop', 'fecha': datetime.now().strftime('%Y-%m-%d'), 'barrios': {}}
    
    try:
        # Intentar página de búsqueda de departamentos en Rosario
        url = 'https://www.zonaprop.com.ar/propiedades/venta/rosario/departamento.html'
        resp = requests.get(url, headers=HEADERS, timeout=20)
        if resp.status_code == 200:
            html = resp.text
            # Buscar precio promedio en el texto
            for pattern in [r'precio\s*(?:promedio|promedio.*?)\$?\s*([0-9.,]+)',
                           r'USD\s*([0-9.,]+)\s*(?:/|por)\s*m²',
                           r'([0-9.,]+)\s*USD/m²']:
                matches = re.findall(pattern, html, re.IGNORECASE)
                if matches:
                    result['raw_match'] = matches[:5]
                    print(f"  Patrones encontrados: {matches[:3]}")
            
            # Extraer precios de propiedades individuales
            prices = re.findall(r'USD\s*([0-9.,]+)', html)
            m2_vals = re.findall(r'(\d+\.?\d*)\s*m²', html)
            print(f"  Precios USD encontrados: {len(prices)}, m2 encontrados: {len(m2_vals)}")
            
            if len(prices) > 10 and len(m2_vals) > 10:
                # Intentar emparejar precios con m2
                pairs = []
                prs = [float(p.replace(',', '')) for p in prices[:50]]
                m2s = [float(m) for m in m2_vals[:50]]
                for i in range(min(len(prs), len(m2s))):
                    if prs[i] > 0 and m2s[i] > 10:
                        pairs.append(prs[i] / m2s[i])
                if pairs:
                    result['precio_promedio_calculado'] = round(sum(pairs) / len(pairs), 0)
                    result['n_propiedades_extract'] = len(pairs)
                    print(f"  Precio promedio calculado: ${result['precio_promedio_calculado']:.0f} USD/m² (n={len(pairs)})")
        else:
            print(f"  HTTP {resp.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
    
    return result


def try_properati_scraping():
    """Intenta obtener datos de Properati."""
    print("\n[PROPERATI] Intentando obtener datos...")
    result = {'fuente': 'Properati', 'fecha': datetime.now().strftime('%Y-%m-%d'), 'barrios': {}}
    
    try:
        # Properati API de estadísticas
        urls = [
            'https://www.properati.com.ar/stats/rosario/departamento/venta',
            'https://www.properati.com.ar/stats/rosario',
            'https://api.properati.com.ar/stats/rosario',
        ]
        for url in urls:
            try:
                resp = requests.get(url, headers=HEADERS, timeout=15)
                if resp.status_code == 200:
                    print(f"  OK: {url}")
                    # Intentar parsear JSON
                    try:
                        data = resp.json()
                        result['raw_data'] = data
                        print(f"  JSON keys: {list(data.keys())[:5]}")
                    except:
                        # Buscar patrones en HTML
                        html = resp.text
                        prices = re.findall(r'USD\s*([0-9.,]+)', html)
                        print(f"  Precios encontrados: {len(prices)}")
                    break
            except:
                continue
    except Exception as e:
        print(f"  Error: {e}")
    
    return result


def try_cocir():
    """Intenta obtener datos de COCIR (Colegio de Corredores Inmobiliarios de Rosario)."""
    print("\n[COCIR] Intentando obtener datos...")
    result = {'fuente': 'COCIR', 'fecha': datetime.now().strftime('%Y-%m-%d'), 'barrios': {}}
    
    try:
        resp = requests.get('https://www.cocir.com.ar/', headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            html = resp.text
            # Buscar links a informes PDF
            pdf_links = re.findall(r'(https?://[^\s"\']+\.pdf)', html)
            if pdf_links:
                result['pdfs_encontrados'] = pdf_links[:5]
                print(f"  PDFs encontrados: {len(pdf_links)}")
                for link in pdf_links[:3]:
                    print(f"    {link}")
            else:
                print(f"  No se encontraron PDFs")
        else:
            print(f"  HTTP {resp.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
    
    return result


def try_reporte_inmobiliario():
    """Intenta obtener datos de Reporte Inmobiliario."""
    print("\n[REPORTE INMOBILIARIO] Intentando obtener datos...")
    result = {'fuente': 'ReporteInmobiliario', 'fecha': datetime.now().strftime('%Y-%m-%d'), 'barrios': {}}
    
    try:
        resp = requests.get('https://www.reporteinmobiliario.com/', headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            html = resp.text
            pdf_links = re.findall(r'(https?://[^\s"\']+\.pdf)', html)
            if pdf_links:
                result['pdfs_encontrados'] = pdf_links[:5]
                print(f"  PDFs encontrados: {len(pdf_links)}")
                for link in pdf_links[:3]:
                    print(f"    {link}")
        else:
            print(f"  HTTP {resp.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
    
    return result


# ─── EJECUTAR ───
print("=" * 70)
print("COMPARACIÓN SCRAPING VPP vs FUENTES EXTERNAS")
print("=" * 70)

SCRAPING = obtener_scraping_zonal()
print(f"\nScraping v4.1: {len(SCRAPING)} zonas con valores")

zonaprop = try_zonaprop_scraping()
properati = try_properati_scraping()
cocir = try_cocir()
reporte_inm = try_reporte_inmobiliario()

# ─── GENERAR TABLA COMPARATIVA ───
# Zonas clave para comparar (mapeo entre nombres de anclas y fuentes externas)
ZONAS_COMPARACION = [
    ('rio_puerto_norte', 'Puerto Norte', 2100),
    ('rio_bv_oroño', 'Bv Oroño', 1850),
    ('parque_espana_norte', 'Parque España', 1850),
    ('martin_rio_urquiza', 'Martín (Río Uruguay)', 1850),
    ('martin_centro_residencial', 'Martín Centro', 1480),
    ('martin_av_pellegrini_bajo', 'Martín Av Pellegrini', 1650),
    ('centro_mendoza_maipu', 'Centro (Mendoza/Maipú)', 1550),
    ('peatonal_cordoba_centro', 'Peatonal Córdoba', 1700),
    ('pellegrini_oroño', 'Pellegrini/Oroño', 1750),
    ('pellegrini_paraguay', 'Pellegrini/Paraguay', 1700),
    ('abasto_corazon_residencial', 'Abasto', 1380),
    ('sexta_pellegrini_sur', 'Sexta Pellegrini', 1400),
    ('lourdes_parque_independencia', 'Lourdes', 1450),
    ('pichincha_centro_aristobulo', 'Pichincha Centro', 1680),
    ('echesortu_plaza_costa', 'Echesortu', 1420),
    ('macrocentro_catamarca_espana', 'Macrocentro', 1580),
    ('zona_oeste_godoy', 'Oeste (Godoy)', 1100),
    ('zona_sur_tablada', 'Sur (Tablada)', 1000),
    ('fisherton_golf', 'Fisherton Golf', 1700),
    ('zona_sur_grandoli', 'Sur (Grandoli)', 950),
    ('ayacucho_mendoza', 'Ayacucho/Mendoza', 1500),
]

print(f"\n{'='*100}")
print("TABLA COMPARATIVA: Scraping VPP vs Fuentes Externas")
print(f"{'='*100}")
print(f"{'Zona':45} {'Scraping':>10} {'v3':>8} {'n':>5} {'Zonaprop':>10} {'Properati':>10} {'Observaciones':>20}")
print('-'*100)

rows = []
for ancla_id, zona_nombre, v3_val in ZONAS_COMPARACION:
    s = SCRAPING.get(ancla_id, {})
    scrap_val = s.get('usd_m2_scraping', '')
    n_val = s.get('n', '')
    estado = s.get('estado', '')
    
    # Construir observaciones
    obs = []
    if scrap_val and isinstance(scrap_val, (int, float)):
        v3_num = float(v3_val)
        desvio_v3 = (scrap_val - v3_num) / v3_num * 100
        obs.append(f"vs v3: {desvio_v3:+.0f}%")
    if n_val and isinstance(n_val, (int, float)) and n_val > 0:
        obs.append(f"n={n_val}")
    if estado:
        obs.append(estado)
    
    scrap_str = f"${scrap_val:,.0f}" if scrap_val and isinstance(scrap_val, (int, float)) else 'N/D'
    v3_str = f"${v3_val:,}" if v3_val else ''
    
    print(f"{zona_nombre:45} {scrap_str:>10} {v3_str:>8} {str(n_val):>5} {'':>10} {'':>10} {' | '.join(obs):>20}")
    
    rows.append({
        'zona': zona_nombre,
        'ancla_id': ancla_id,
        'scraping_usd_m2': scrap_val if isinstance(scrap_val, (int, float)) else None,
        'v3_usd_m2': v3_val,
        'n_zonal': n_val if isinstance(n_val, (int, float)) else None,
        'estado': estado,
    })

df = pd.DataFrame(rows)
df.to_csv('reports/comparacion_scraping_vs_oficiales.csv', index=False, encoding='utf-8')
print(f"\nCSV guardado: reports/comparacion_scraping_vs_oficiales.csv")

print(f"\n{'='*70}")
print("RESUMEN FUENTES EXTERNAS")
print(f"{'='*70}")
print(f"Zonaprop: {zonaprop.get('precio_promedio_calculado', 'No disponible')}")
print(f"  URL: https://www.zonaprop.com.ar/propiedades/venta/rosario/departamento.html")
print(f"Properati: No disponible automáticamente")
print(f"  URL: https://www.properati.com.ar/stats/rosario/departamento/venta")
print(f"COCIR PDFs: {cocir.get('pdfs_encontrados', 'No encontrados')}")
print(f"  URL: https://www.cocir.com.ar/")
print(f"Reporte Inmobiliario: {reporte_inm.get('pdfs_encontrados', 'No encontrados')}")
print(f"  URL: https://www.reporteinmobiliario.com/")
