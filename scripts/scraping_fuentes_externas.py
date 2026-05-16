"""
Script de comparacion: Scraping VPP vs Fuentes Externas
Rosario, Mayo 2026

Fuentes:
1. zonaprop_full.html (ya descargado) - extrae listings individuales - mediana USD/m2
2. Properati API publica - intenta GET de stats
3. COCIR PDF - intenta descarga y extraccion
4. Reporte Inmobiliario - intenta descarga PDF

Genera: reports/comparacion_scraping_vs_oficiales.csv
"""

import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import json
import re
import statistics
import os
import sys
import requests
from pathlib import Path
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "data"
REPORTS_DIR = BASE / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-AR,es;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ──────────────────────────────────────────────────────────────────────────────
# 1. LECTURA DE ANCLAS V4.1 (fuente VPP scraping)
# ──────────────────────────────────────────────────────────────────────────────

def obtener_scraping_zonal():
    path = DATA_DIR / "anclas_rosario_v41_temporal.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    anclas = data.get("anclas", [])
    resultado = {}
    for a in anclas:
        nombre = a.get("id", "")
        usd = a.get("usd_m2")
        if usd:
            resultado[nombre] = {
                "usd_m2_scraping": round(usd),
                "n": a.get("n_zonal", 0),
                "ventana": a.get("ventana_dias"),
                "p25": a.get("p25"),
                "p75": a.get("p75"),
                "estado": a.get("estado_revision", ""),
            }
    print(f"[VPP]   {len(resultado)} anclas cargadas de v4.1")
    return resultado


# ──────────────────────────────────────────────────────────────────────────────
# 2. ZONAPROP — desde HTML ya guardado + scraping fresco por barrio
# ──────────────────────────────────────────────────────────────────────────────

# Mapeo: id_ancla -> término de búsqueda en Zonaprop
ZONAPROP_BARRIOS = {
    "martin_centro_residencial":    ("martin", "Rosario Norte - Güemes - Martín"),
    "pichincha_centro_aristobulo":  ("pichincha", "Pichincha"),
    "pellegrini_oroño":             ("pellegrini-oroño", "Pellegrini / Bv. Oroño"),
    "lourdes_parque_independencia": ("lourdes", "Lourdes - Parque Independencia"),
    "echesortu_plaza_costa":        ("echesortu", "Echesortu"),
    "zona_oeste_godoy":             ("godoy", "Zona Oeste / Godoy"),
    "zona_sur_tablada":             ("tablada", "Zona Sur / Tablada"),
    "fisherton_cordoba_oeste":      ("fisherton", "Fisherton"),
    "centro_mendoza_maipu":         ("centro", "Centro"),
    "macrocentro_salta_lagos":      ("macrocentro", "Macrocentro Norte"),
    "abasto_corazon_residencial":   ("abasto", "Abasto"),
    "sexta_pellegrini_sur":         ("sexta", "Sexta Sección"),
}


def parsear_zonaprop_html(filepath):
    """Extrae listings individuales del HTML guardado y calcula mediana USD/m2."""
    print(f"\n[ZP]    Parseando {filepath.name} ...")
    with open(filepath, encoding="utf-8", errors="ignore") as f:
        html = f.read()

    soup = BeautifulSoup(html, "html.parser")
    listings = soup.find_all("div", attrs={"data-id": True, "data-posting-type": "PROPERTY"})
    print(f"[ZP]    {len(listings)} listings encontrados")

    records = []
    for listing in listings:
        txt = listing.get_text(separator=" ", strip=True)

        # Precio
        pm = re.search(r"USD\s*([\d\.]+)", txt)
        precio = None
        if pm:
            try:
                precio = int(pm.group(1).replace(".", ""))
            except Exception:
                pass

        # m2 totales
        mm = re.search(r"(\d+)\s*m[²2]\s*tot", txt)
        m2 = None
        if mm:
            try:
                m2 = int(mm.group(1))
            except Exception:
                pass

        # Barrio / ubicación
        loc = listing.find(attrs={"data-qa": "POSTING_CARD_LOCATION"})
        location = loc.get_text(strip=True) if loc else ""

        usd_m2 = None
        if precio and m2 and m2 > 15 and precio > 10000:
            usd_m2 = round(precio / m2)

        records.append({
            "precio": precio,
            "m2": m2,
            "usd_m2": usd_m2,
            "location": location,
        })

    valid = [r for r in records if r["usd_m2"] and 300 < r["usd_m2"] < 6000]
    print(f"[ZP]    {len(valid)} listings con USD/m2 válido")

    if not valid:
        return None, records

    prices = [r["usd_m2"] for r in valid]
    med = statistics.median(prices)
    avg = statistics.mean(prices)
    print(f"[ZP]    Rosario general -> Mediana: {med:.0f} | Promedio: {avg:.0f} USD/m2")
    return round(med), records


def scraping_zonaprop_barrio(barrio_slug, timeout=12):
    """Intenta obtener precio mediano de un barrio específico en Zonaprop."""
    url = (
        f"https://www.zonaprop.com.ar/propiedades/venta/rosario/"
        f"{barrio_slug}/departamento.html"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        if resp.status_code != 200:
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        listings = soup.find_all("div", attrs={"data-id": True, "data-posting-type": "PROPERTY"})
        prices = []
        for l in listings:
            txt = l.get_text(separator=" ", strip=True)
            pm = re.search(r"USD\s*([\d\.]+)", txt)
            mm = re.search(r"(\d+)\s*m[²2]\s*tot", txt)
            if pm and mm:
                try:
                    precio = int(pm.group(1).replace(".", ""))
                    m2 = int(mm.group(1))
                    if precio > 10000 and m2 > 15:
                        prices.append(round(precio / m2))
                except Exception:
                    pass

        valid = [p for p in prices if 300 < p < 6000]
        if valid:
            return round(statistics.median(valid))
    except Exception as e:
        print(f"[ZP]      Error en {barrio_slug}: {e}")
    return None


# ──────────────────────────────────────────────────────────────────────────────
# 3. PROPERATI — API pública de estadísticas
# ──────────────────────────────────────────────────────────────────────────────

PROPERATI_URLS = [
    "https://www.properati.com.ar/stats/ar/rosario/departamentos/venta/",
    "https://www.properati.com.ar/stats/",
    "https://api.properati.com.ar/api/v2/listings/stats/?location=rosario&property_type=apartment&operation=sell",
]

def obtener_properati():
    print("\n[PRP]   Intentando Properati ...")
    for url in PROPERATI_URLS:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            print(f"[PRP]   {url} -> HTTP {resp.status_code}")
            if resp.status_code == 200:
                ct = resp.headers.get("Content-Type", "")
                if "json" in ct:
                    data = resp.json()
                    print(f"[PRP]   JSON keys: {list(data.keys())[:8]}")
                    # Buscar precio mediano
                    for key in ["median_price_m2", "price_m2", "median", "price"]:
                        if key in data:
                            return {"general": data[key]}
                else:
                    # Buscar en HTML
                    soup = BeautifulSoup(resp.text, "html.parser")
                    txt = soup.get_text()
                    m = re.search(r"USD[\s]*([\d\.,]+)[\s]*/[\s]*m[²2]", txt)
                    if m:
                        val = m.group(1).replace(".", "").replace(",", "")
                        return {"general": int(val)}
        except Exception as e:
            print(f"[PRP]   Error: {e}")
    print("[PRP]   No disponible (requiere JS o autenticación)")
    return {}


# ──────────────────────────────────────────────────────────────────────────────
# 4. COCIR — PDF desde cocir.com.ar
# ──────────────────────────────────────────────────────────────────────────────

COCIR_URLS = [
    "https://www.cocir.com.ar/",
    "https://www.cocir.com.ar/informes/",
    "https://www.cocir.com.ar/estadisticas/",
]

def obtener_cocir():
    print("\n[COC]   Intentando COCIR ...")
    
    # Primero intentar encontrar el PDF
    for url in COCIR_URLS:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            print(f"[COC]   {url} -> HTTP {resp.status_code}")
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")
            # Buscar links a PDF
            pdf_links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if ".pdf" in href.lower() or "informe" in href.lower() or "estadistica" in href.lower():
                    pdf_links.append(href)

            print(f"[COC]   PDF/informe links: {pdf_links[:5]}")

            # Buscar precios directamente en la página
            txt = soup.get_text(separator=" ")
            # Buscar patrón de precio por m2
            matches = re.findall(
                r"(?:rosario|precio|m2|departamento)[\s\S]{0,100}?\$?\s*([\d\.,]+)\s*(?:USD|u\$s|dolar)",
                txt, re.IGNORECASE
            )
            if matches:
                print(f"[COC]   Valores encontrados en página: {matches[:5]}")

            # Si hay PDF, intentar descargarlo
            for pdf_url in pdf_links[:3]:
                if not pdf_url.startswith("http"):
                    from urllib.parse import urljoin
                    pdf_url = urljoin(url, pdf_url)
                try:
                    result = extraer_pdf_precios(pdf_url, "COCIR")
                    if result:
                        return result
                except Exception as e:
                    print(f"[COC]   Error PDF: {e}")

        except Exception as e:
            print(f"[COC]   Error: {e}")

    print("[COC]   No disponible automáticamente")
    return {}


# ──────────────────────────────────────────────────────────────────────────────
# 5. REPORTE INMOBILIARIO — PDF
# ──────────────────────────────────────────────────────────────────────────────

REPORTE_INM_URLS = [
    "https://www.reporteinmobiliario.com/",
    "https://www.reporteinmobiliario.com/reportes/",
    "https://www.reporteinmobiliario.com/nuke/article5070-informe-mensual-mercado-inmobiliario.html",
]

def obtener_reporte_inmobiliario():
    print("\n[RI]    Intentando Reporte Inmobiliario ...")
    for url in REPORTE_INM_URLS:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            print(f"[RI]    {url} -> HTTP {resp.status_code}")
            if resp.status_code != 200:
                continue

            soup = BeautifulSoup(resp.text, "html.parser")

            # Buscar PDF links
            pdf_links = [
                a["href"] for a in soup.find_all("a", href=True)
                if ".pdf" in a["href"].lower()
            ]
            print(f"[RI]    PDFs encontrados: {pdf_links[:5]}")

            # Buscar precios en texto
            txt = soup.get_text(separator=" ")
            # Rosario
            rosario_idx = txt.lower().find("rosario")
            if rosario_idx > 0:
                snippet = txt[rosario_idx:rosario_idx+500]
                nums = re.findall(r"[\d]{3,4}", snippet)
                print(f"[RI]    Texto cerca de 'rosario': {snippet[:300]}")

            for pdf_url in pdf_links[:3]:
                if not pdf_url.startswith("http"):
                    from urllib.parse import urljoin
                    pdf_url = urljoin(url, pdf_url)
                try:
                    result = extraer_pdf_precios(pdf_url, "RI")
                    if result:
                        return result
                except Exception as e:
                    print(f"[RI]    Error PDF: {e}")

        except Exception as e:
            print(f"[RI]    Error: {e}")

    print("[RI]    No disponible automáticamente")
    return {}


def extraer_pdf_precios(pdf_url, fuente=""):
    """Intenta descargar y parsear PDF buscando precios de Rosario."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print(f"[{fuente}]   PyMuPDF no instalado, skip PDF")
        return {}

    try:
        print(f"[{fuente}]   Descargando PDF: {pdf_url}")
        resp = requests.get(pdf_url, headers=HEADERS, timeout=30)
        if resp.status_code != 200:
            return {}

        doc = fitz.open("pdf", resp.content)
        texto = ""
        for page in doc:
            texto += page.get_text()

        print(f"[{fuente}]   PDF: {len(texto)} chars extraídos")

        # Buscar Rosario
        idx = texto.lower().find("rosario")
        if idx > 0:
            snippet = texto[max(0, idx-50):idx+300]
            print(f"[{fuente}]   Rosario en PDF: {snippet[:300]}")
            # Buscar precio mediano en el contexto
            nums = re.findall(r"(?:USD|u\$s|\$)?\s*([\d]{3,4})", snippet)
            if nums:
                vals = [int(n) for n in nums if 500 < int(n) < 5000]
                if vals:
                    return {"general_pdf": vals[0]}
        return {}
    except Exception as e:
        print(f"[{fuente}]   Error PDF: {e}")
        return {}


# ──────────────────────────────────────────────────────────────────────────────
# 6. ZONAPROP INDEX PAGE — buscar dato agregado de Rosario
# ──────────────────────────────────────────────────────────────────────────────

def obtener_zonaprop_indice():
    """Intenta obtener el índice/precio promedio de Rosario desde la página de noticias/indice."""
    urls = [
        "https://www.zonaprop.com.ar/noticias/mercado-inmobiliario/",
        "https://www.zonaprop.com.ar/noticias/mercado-inmobiliario/informe-precios-departamentos-rosario.html",
    ]
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=12)
            print(f"[ZP-IDX] {url} -> HTTP {resp.status_code}")
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                txt = soup.get_text(separator=" ")
                # Buscar mención de Rosario + precio
                idx = txt.lower().find("rosario")
                while idx != -1:
                    snippet = txt[max(0, idx-30):idx+200]
                    m = re.search(r"([\d]{3,4})\s*(?:USD|u\$s|dólar|dolar)?[\s]*/[\s]*m[²2]", snippet)
                    if m:
                        val = int(m.group(1))
                        if 500 < val < 4000:
                            print(f"[ZP-IDX] Precio encontrado: {val} USD/m2")
                            return val
                    idx = txt.lower().find("rosario", idx + 1)
                    if idx > 100000:
                        break
        except Exception as e:
            print(f"[ZP-IDX] Error: {e}")
    return None


# ──────────────────────────────────────────────────────────────────────────────
# 7. TABLA COMPARATIVA
# ──────────────────────────────────────────────────────────────────────────────

# Zonas clave a comparar (id de ancla v4.1)
ZONAS_CLAVE = [
    "martin_centro_residencial",
    "martin_plaza_lopez",
    "pichincha_centro_aristobulo",
    "pichincha_norte_brown",
    "pellegrini_oroño",
    "pellegrini_paraguay",
    "pellegrini_libertad",
    "peatonal_cordoba_centro",
    "centro_mendoza_maipu",
    "lourdes_parque_independencia",
    "lourdes_core_santiago",
    "echesortu_plaza_costa",
    "echesortu_mendoza_avellaneda",
    "abasto_corazon_residencial",
    "sexta_pellegrini_sur",
    "sexta_unr_cur",
    "zona_oeste_godoy",
    "zona_oeste_felipe_more",
    "zona_sur_tablada",
    "zona_sur_hospitales",
    "fisherton_cordoba_oeste",
]


def comparar_fuentes(scraping, zp_general, zp_barrios, properati, cocir, ri):
    rows = []
    for zona in ZONAS_CLAVE:
        scr = scraping.get(zona, {})
        usd_scr = scr.get("usd_m2_scraping")

        usd_zp = zp_barrios.get(zona) or zp_general
        usd_prop = properati.get("general")
        usd_coc = cocir.get("general") or cocir.get("general_pdf")
        usd_ri = ri.get("general") or ri.get("general_pdf")

        externos = [v for v in [usd_zp, usd_prop, usd_coc, usd_ri] if v]
        prom_ext = round(statistics.mean(externos)) if externos else None

        desvio = None
        if usd_scr and prom_ext:
            desvio = round((usd_scr - prom_ext) / prom_ext * 100, 1)

        # Semáforo
        if desvio is None:
            flag = "⬛ N/D"
        elif abs(desvio) <= 10:
            flag = "✅ OK"
        elif abs(desvio) <= 20:
            flag = "🟡 MOD"
        else:
            flag = "🔴 ALTO"

        rows.append({
            "zona": zona,
            "usd_m2_scraping_p50": usd_scr,
            "n_scraping": scr.get("n"),
            "p25": scr.get("p25"),
            "p75": scr.get("p75"),
            "estado_revision": scr.get("estado"),
            "usd_m2_zonaprop": usd_zp,
            "usd_m2_properati": usd_prop,
            "usd_m2_cocir": usd_coc,
            "usd_m2_reporte_inm": usd_ri,
            "promedio_fuentes_externas": prom_ext,
            "desvio_scraping_vs_externos_pct": desvio,
            "flag": flag,
        })
    return pd.DataFrame(rows)


# ──────────────────────────────────────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("COMPARACIÓN VPP SCRAPING vs FUENTES EXTERNAS")
    print(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # 1. Anclas VPP
    scraping = obtener_scraping_zonal()

    # 2. Zonaprop — HTML guardado
    zp_html = BASE / "zonaprop_full.html"
    zp_general = None
    zp_records = []
    if zp_html.exists():
        zp_general, zp_records = parsear_zonaprop_html(zp_html)

    # 2b. Zonaprop — índice/noticias
    if not zp_general:
        zp_general = obtener_zonaprop_indice()

    # 2c. Zonaprop — scraping por barrio (con el HTML general tenemos la mediana global)
    # Intentamos también scraping fresco por barrio
    zp_barrios = {}
    print("\n[ZP]    Intentando scraping por barrio ...")
    for zona, (slug, label) in ZONAPROP_BARRIOS.items():
        val = scraping_zonaprop_barrio(slug)
        if val:
            zp_barrios[zona] = val
            print(f"[ZP]      {label}: {val} USD/m2")
        else:
            print(f"[ZP]      {label}: no disponible")

    # 3. Properati
    properati = obtener_properati()

    # 4. COCIR
    cocir = obtener_cocir()

    # 5. Reporte Inmobiliario
    ri = obtener_reporte_inmobiliario()

    # 6. Tabla comparativa
    print("\n" + "=" * 60)
    print("GENERANDO TABLA COMPARATIVA")
    print("=" * 60)

    # Usar zp_general como fallback de zonaprop por zona
    df = comparar_fuentes(scraping, zp_general, zp_barrios, properati, cocir, ri)

    # Guardar CSV
    out_path = REPORTS_DIR / "comparacion_scraping_vs_oficiales.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"\n✅ CSV guardado: {out_path}")

    # Mostrar tabla
    pd.set_option("display.max_columns", 20)
    pd.set_option("display.width", 160)
    pd.set_option("display.max_rows", 50)
    print("\n" + df.to_string(index=False))

    # Resumen de sesgo
    with_desvio = df.dropna(subset=["desvio_scraping_vs_externos_pct"])
    if not with_desvio.empty:
        sesgo = with_desvio["desvio_scraping_vs_externos_pct"].mean()
        print(f"\n{'='*60}")
        print(f"SESGO SISTEMÁTICO PROMEDIO: {sesgo:+.1f}%")
        if sesgo < -15:
            print("-> Escenario B: Scraping sistemáticamente BAJO")
            print(f"  Factor de corrección sugerido: {1/(1+sesgo/100):.3f}")
        elif sesgo > 15:
            print("-> Escenario C: Scraping sistemáticamente ALTO")
        else:
            print("-> Escenario A: Scraping ALINEADO con fuentes externas (±15%)")
        print("="*60)

    # Metadata de la corrida
    meta = {
        "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "fuente_zonaprop": "zonaprop_full.html (local) + scraping barrios",
        "zonaprop_general_usd_m2": zp_general,
        "zonaprop_barrios_disponibles": list(zp_barrios.keys()),
        "properati_disponible": bool(properati),
        "cocir_disponible": bool(cocir),
        "reporte_inm_disponible": bool(ri),
        "n_zonas_comparadas": len(df),
        "n_con_externo": int(df["promedio_fuentes_externas"].notna().sum()),
        "sesgo_promedio_pct": round(with_desvio["desvio_scraping_vs_externos_pct"].mean(), 1) if not with_desvio.empty else None,
    }
    meta_path = REPORTS_DIR / "comparacion_metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    print(f"✅ Metadata: {meta_path}")

    return df, meta


if __name__ == "__main__":
    df, meta = main()
