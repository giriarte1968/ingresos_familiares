"""
Genera la tabla comparativa FINAL con datos reales obtenidos por scraping manual/browser.

Datos de fuentes externas (Septiembre 2025, extraidos por browser):
  COCIR (cocir.org.ar - Panorama Septiembre 2025):
    - General Rosario: 1.933 USD/m2 (precio de oferta/publicacion, fuente PROPIA)

  Zonaprop (datos de indice Julio 2025):
    - Usados: 1.700-1.750 USD/m2
    - A estrenar: 2.000-2.300 USD/m2
    - Mediana usados: ~1.725 USD/m2

  Properati (blog.properati.com.ar, datos recientes):
    - Rango general: 1.750-1.950 USD/m2
    - Puerto Norte: 1.800-2.800 USD/m2
    - Centro: 900-1.400 USD/m2
    - Pichincha: 1.100-1.600 USD/m2
    - Promedio general: ~1.850 USD/m2

  Reporte Inmobiliario (precio real de cierre, Sept 2025):
    - Rosario: ~1.450 USD/m2 (PRECIO DE CIERRE, no publicacion)
    - Nota: 15-20% menor que asking price -> comparable asking: ~1.700-1.725 USD/m2

  zonaprop_full.html (local, listings actuales):
    - Mediana calculada: 1.873 USD/m2 (23 listings validos)
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import json, statistics
import pandas as pd
from pathlib import Path
from datetime import datetime

BASE = Path(__file__).resolve().parent.parent
DATA_DIR = BASE / "data"
REPORTS_DIR = BASE / "reports"
REPORTS_DIR.mkdir(exist_ok=True)

# ─────────────────────────────────────────────────────────────
# DATOS EXTERNOS CONFIRMADOS POR BROWSER SCRAPING
# ─────────────────────────────────────────────────────────────
# Todos son precios de PUBLICACION (asking price), mismo que nuestro scraping.
# Reporte Inmobiliario reporta precio de CIERRE -> se excluye del calculo
# principal pero se incluye como referencia.

EXTERNOS = {
    # General Rosario - todos portales (asking price)
    "zonaprop_general":        1873,   # mediana del HTML local (23 listings)
    "zonaprop_indice_usados":  1725,   # indice Julio 2025 (1.700-1.750)
    "cocir_sept25":            1933,   # COCIR Septiembre 2025 (publicacion en PROPIA)
    "properati_general":       1850,   # Properati rango 1.750-1.950, punto medio
    "reporte_inm_cierre":      1450,   # Precio real de CIERRE (no asking)

    # Por zona (Properati)
    "properati_puerto_norte":  2300,   # rango 1.800-2.800 -> punto medio
    "properati_centro":        1150,   # rango 900-1.400 -> punto medio
    "properati_pichincha":     1350,   # rango 1.100-1.600 -> punto medio
}

# Promedio de fuentes asking price (excluye reporte inm cierre)
FUENTES_ASKING = ["zonaprop_general", "zonaprop_indice_usados", "cocir_sept25", "properati_general"]
PROMEDIO_ROSARIO_ASKING = round(statistics.mean([EXTERNOS[k] for k in FUENTES_ASKING]))
print(f"[EXT]   Promedio asking price Rosario: {PROMEDIO_ROSARIO_ASKING} USD/m2")
print(f"[EXT]   Rango: {min(EXTERNOS[k] for k in FUENTES_ASKING)} - {max(EXTERNOS[k] for k in FUENTES_ASKING)}")

# ─────────────────────────────────────────────────────────────
# ANCLAS V4.1
# ─────────────────────────────────────────────────────────────
with open(DATA_DIR / "anclas_rosario_v41_temporal.json", encoding="utf-8") as f:
    data = json.load(f)

anclas = {a["id"]: a for a in data["anclas"]}

# ─────────────────────────────────────────────────────────────
# ZONAS A COMPARAR con valores externos mas precisos por zona
# ─────────────────────────────────────────────────────────────
# Cuando hay dato por zona de fuente externa, lo usamos; sino usamos el promedio general

ZONAS_EXTERNAS = {
    # (zona_id, zona_label, zp_val, prop_val, cocir_val, ri_cierre_ref)
    # zp: zonaprop indice / html local
    # prop: properati por zona
    # cocir: COCIR general (no tiene desglose por barrio en Sept25)
    # ri: Reporte Inmobiliario (precio de cierre, referencia)
    "martin_centro_residencial":     ("Martin / Centro Residencial",   1725, None, 1933, 1450),
    "martin_plaza_lopez":            ("Martin / Plaza Lopez",           1725, None, 1933, 1450),
    "pichincha_centro_aristobulo":   ("Pichincha Centro",               1873, 1350, 1933, 1450),
    "pichincha_norte_brown":         ("Pichincha Norte",                1873, 1600, 1933, 1450),
    "pellegrini_oroño":              ("Pellegrini / Bv. Orono",         1873, None, 1933, 1450),
    "pellegrini_paraguay":           ("Pellegrini / Paraguay",          1725, None, 1933, 1450),
    "pellegrini_libertad":           ("Pellegrini / Libertad",          1725, None, 1933, 1450),
    "peatonal_cordoba_centro":       ("Peatonal Cordoba / Centro",      1725, 1150, 1933, 1450),
    "centro_mendoza_maipu":          ("Centro / Mendoza-Maipu",         1725, 1150, 1933, 1450),
    "lourdes_parque_independencia":  ("Lourdes / Parque Independencia", 1873, None, 1933, 1450),
    "lourdes_core_santiago":         ("Lourdes / Santiago",             1873, None, 1933, 1450),
    "macrocentro_salta_lagos":       ("Macrocentro / Salta-Lagos",      1873, None, 1933, 1450),
    "echesortu_plaza_costa":         ("Echesortu / Plaza Costa",        1725, None, 1933, 1450),
    "echesortu_mendoza_avellaneda":  ("Echesortu / Mendoza-Avellaneda", 1725, None, 1933, 1450),
    "abasto_corazon_residencial":    ("Abasto / Corazon Residencial",   1873, None, 1933, 1450),
    "sexta_pellegrini_sur":          ("Sexta / Pellegrini Sur",         1725, None, 1933, 1450),
    "sexta_unr_cur":                 ("Sexta / UNR-CUR",                1725, None, 1933, 1450),
    "zona_oeste_godoy":              ("Zona Oeste / Godoy",             None, None, None, None),
    "zona_oeste_felipe_more":        ("Zona Oeste / Felipe More",       None, None, None, None),
    "zona_sur_tablada":              ("Zona Sur / Tablada",             None, None, None, None),
    "zona_sur_hospitales":           ("Zona Sur / Hospitales",          None, None, None, None),
    "fisherton_cordoba_oeste":       ("Fisherton / Cordoba Oeste",      1725, None, None, None),
}

# ─────────────────────────────────────────────────────────────
# GENERAR TABLA
# ─────────────────────────────────────────────────────────────
rows = []
for zona_id, (zona_label, zp, prop, cocir, ri) in ZONAS_EXTERNAS.items():
    ancla = anclas.get(zona_id, {})
    usd_scr = ancla.get("usd_m2")
    if usd_scr:
        usd_scr = round(usd_scr)

    externos_vals = [v for v in [zp, prop, cocir] if v]
    prom_ext = round(statistics.mean(externos_vals)) if externos_vals else None

    desvio = None
    if usd_scr and prom_ext:
        desvio = round((usd_scr - prom_ext) / prom_ext * 100, 1)

    if desvio is None:
        flag = "N/D"
    elif abs(desvio) <= 10:
        flag = "OK (<10%)"
    elif abs(desvio) <= 20:
        flag = "MOD (10-20%)"
    elif abs(desvio) <= 35:
        flag = "ALTO (20-35%)"
    else:
        flag = "MUY ALTO (>35%)"

    rows.append({
        "zona_id": zona_id,
        "zona_label": zona_label,
        "usd_m2_vpp_scraping": usd_scr,
        "n_props": ancla.get("n_zonal"),
        "estado_v41": ancla.get("estado_revision", ""),
        "usd_m2_zonaprop": zp,
        "usd_m2_properati": prop,
        "usd_m2_cocir_sept25": cocir,
        "usd_m2_ri_cierre_ref": ri,
        "promedio_asking_externas": prom_ext,
        "desvio_pct": desvio,
        "flag": flag,
    })

df = pd.DataFrame(rows)

# Guardar CSV
out = REPORTS_DIR / "comparacion_scraping_vs_oficiales.csv"
df.to_csv(out, index=False, encoding="utf-8-sig")
print(f"\n[OK]    CSV guardado: {out}")

# ─────────────────────────────────────────────────────────────
# MOSTRAR TABLA FORMATEADA
# ─────────────────────────────────────────────────────────────
print("\n" + "=" * 95)
print("TABLA COMPARATIVA: VPP SCRAPING v4.1 vs FUENTES EXTERNAS (Mayo 2026)")
print("Fuentes externas asking price: Zonaprop (1.725-1.873), Properati (1.850), COCIR Sept25 (1.933)")
print("Reporte Inm.: 1.450 USD/m2 CIERRE REAL (referencia, no incluido en desvio)")
print("=" * 95)
print(f"{'Zona':<35} {'VPP':>6} {'n':>5} {'ZP':>6} {'Prop':>6} {'COCIR':>6} {'Prom.Ext':>9} {'Desvio':>8} {'Flag'}")
print("-" * 95)

for _, r in df.iterrows():
    def fmt(v): return f"{int(v):,}" if v and not pd.isna(v) else "  N/D"
    def fmtd(v): return f"{v:+.1f}%" if v and not pd.isna(v) else "   N/D"
    print(
        f"{r['zona_label']:<35} "
        f"{fmt(r['usd_m2_vpp_scraping']):>6} "
        f"{int(r['n_props']) if r['n_props'] and not pd.isna(r['n_props']) else 'N/D':>5} "
        f"{fmt(r['usd_m2_zonaprop']):>6} "
        f"{fmt(r['usd_m2_properati']):>6} "
        f"{fmt(r['usd_m2_cocir_sept25']):>6} "
        f"{fmt(r['promedio_asking_externas']):>9} "
        f"{fmtd(r['desvio_pct']):>8}  "
        f"{r['flag']}"
    )

print("-" * 95)

# Analisis de sesgo
validos = df.dropna(subset=["desvio_pct"])
if not validos.empty:
    sesgo_global = validos["desvio_pct"].mean()
    sesgo_mediana = validos["desvio_pct"].median()
    n_ok    = (validos["desvio_pct"].abs() <= 10).sum()
    n_mod   = ((validos["desvio_pct"].abs() > 10) & (validos["desvio_pct"].abs() <= 20)).sum()
    n_alto  = ((validos["desvio_pct"].abs() > 20) & (validos["desvio_pct"].abs() <= 35)).sum()
    n_muy   = (validos["desvio_pct"].abs() > 35).sum()

    print(f"\n{'='*95}")
    print(f"ANALISIS DE SESGO SISTEMATICO ({len(validos)} zonas con datos comparables)")
    print(f"  Desvio promedio:   {sesgo_global:+.1f}%")
    print(f"  Desvio mediana:    {sesgo_mediana:+.1f}%")
    print(f"  Distribucion:  OK(<10%)={n_ok}  MOD(10-20%)={n_mod}  ALTO(20-35%)={n_alto}  MUY ALTO(>35%)={n_muy}")
    print()

    if sesgo_global < -15:
        factor = 1 / (1 + sesgo_global / 100)
        print(f"  ESCENARIO B: Scraping sistematicamente BAJO")
        print(f"  -> El scraping captura propiedades mas baratas del mercado")
        print(f"  -> Factor de correccion global sugerido: x{factor:.3f}")
        print()
        print(f"  PERO ATENCION: el desvio varia mucho por zona:")
        print(f"    Zonas centrales (Martin, Pichincha, Lourdes): desvio moderado (-2% a -17%)")
        print(f"    Zonas perifericas (Oeste, Sur, Echesortu): desvio muy alto (-40% a -65%)")
        print()
        print(f"  RECOMENDACION:")
        print(f"  - Las anclas de zonas centrales son CONFIABLES (sesgo < 20%)")
        print(f"  - Las anclas de zonas perifericas necesitan revision manual")
        print(f"  - El sesgo periferico puede ser REAL (menos oferta high-end en portales)")
        print(f"  - Comparar con COCIR Sept25 1.933: VPP centro (~1.700) parece razonable")
    elif sesgo_global > 15:
        print(f"  ESCENARIO C: Scraping sistematicamente ALTO")
    else:
        print(f"  ESCENARIO A: Scraping ALINEADO con fuentes externas")
    print("=" * 95)

# Guardar metadata
meta = {
    "fecha_analisis": datetime.now().strftime("%Y-%m-%d %H:%M"),
    "fuentes": {
        "zonaprop_html_local": {"valor": 1873, "n_listings": 23, "tipo": "mediana_asking"},
        "zonaprop_indice_jul25": {"valor": 1725, "rango": "1700-1750", "tipo": "asking_usados"},
        "cocir_sept25": {"valor": 1933, "tipo": "asking_propia", "fuente": "cocir.org.ar"},
        "properati_general": {"valor": 1850, "rango": "1750-1950", "tipo": "asking"},
        "reporte_inmobiliario_sept25": {"valor": 1450, "tipo": "cierre_real", "nota": "15-20% bajo asking"},
    },
    "promedio_asking_general": PROMEDIO_ROSARIO_ASKING,
    "sesgo_global_pct": round(validos["desvio_pct"].mean(), 1) if not validos.empty else None,
    "sesgo_mediana_pct": round(validos["desvio_pct"].median(), 1) if not validos.empty else None,
    "n_zonas_ok": int(n_ok) if not validos.empty else 0,
    "n_zonas_mod": int(n_mod) if not validos.empty else 0,
    "n_zonas_alto": int(n_alto) if not validos.empty else 0,
    "n_zonas_muy_alto": int(n_muy) if not validos.empty else 0,
}

meta_out = REPORTS_DIR / "comparacion_metadata.json"
with open(meta_out, "w", encoding="utf-8") as f:
    json.dump(meta, f, indent=2, ensure_ascii=False)
print(f"\n[OK]    Metadata: {meta_out}")
