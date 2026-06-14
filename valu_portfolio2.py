"""Portfolio2 — vista premium y escalable del portfolio inmobiliario.

Este módulo es intencionalmente aislado de `valu.py`: no reemplaza el
Portfolio clásico y no toca el motor de valuación. Lee resultados existentes
desde `data/valuaciones_cache.json` y solo redirige al flujo clásico cuando el
usuario pide detalle o revaluación.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Callable

import pandas as pd
import streamlit as st
from parsers.profiler import profile_block


PORTFOLIO2_CSS = """
<style>
.p2-hero {
    background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 56%, #006AFF 100%);
    border-radius: 26px;
    padding: 30px;
    color: white;
    box-shadow: 0 18px 48px rgba(15, 23, 42, 0.20);
    margin-bottom: 20px;
}
.p2-hero-eyebrow {
    font-size: 12px;
    font-weight: 900;
    letter-spacing: .14em;
    text-transform: uppercase;
    color: #93C5FD;
    margin-bottom: 8px;
}
.p2-hero h1 {
    margin: 0;
    font-size: 40px;
    line-height: 1.05;
    letter-spacing: -0.04em;
}
.p2-hero p {
    margin: 8px 0 0 0;
    color: rgba(255,255,255,0.78);
    font-size: 15px;
}
.p2-hero-total-label {
    font-size: 13px;
    color: rgba(255,255,255,.70);
    text-align: right;
}
.p2-hero-total-value {
    font-size: 34px;
    line-height: 1.05;
    font-weight: 950;
    text-align: right;
    letter-spacing: -0.04em;
}
.p2-kpi-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 16px;
    margin: 18px 0 22px 0;
}
.p2-kpi-card, .p2-section-card, .p2-property-card {
    background: white;
    border: 1px solid rgba(148, 163, 184, 0.20);
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06);
}
.p2-kpi-card {
    border-radius: 18px;
    padding: 18px;
}
.p2-kpi-label {
    color: #64748B;
    font-size: 12px;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .08em;
}
.p2-kpi-value {
    color: #0F172A;
    font-size: 27px;
    font-weight: 900;
    letter-spacing: -0.035em;
    margin-top: 6px;
}
.p2-kpi-sub {
    color: #64748B;
    font-size: 13px;
    margin-top: 4px;
}
.p2-section-card {
    border-radius: 20px;
    padding: 20px;
    margin-bottom: 18px;
}
.p2-property-card {
    border-radius: 20px;
    padding: 18px;
    margin: 6px;
    min-height: 270px;
    cursor: pointer;
    transition: box-shadow 0.2s, transform 0.15s;
}
.p2-property-card:hover {
    box-shadow: 0 8px 24px rgba(0,0,0,0.12);
    transform: translateY(-2px);
}
.p2-property-title {
    font-size: 20px;
    font-weight: 900;
    color: #0F172A;
    margin: 12px 0 4px 0;
    letter-spacing: -0.025em;
}
.p2-muted {
    color: #64748B;
    font-size: 13px;
    line-height: 1.35;
}
.p2-price {
    font-size: 29px;
    color: #006AFF;
    font-weight: 950;
    letter-spacing: -0.045em;
    margin: 16px 0 4px 0;
}
.p2-card-metrics {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 8px;
    margin-top: 14px;
}
.p2-mini-metric {
    background: #F8FAFC;
    border-radius: 12px;
    padding: 10px;
}
.p2-mini-label {
    color: #64748B;
    font-size: 11px;
}
.p2-mini-value {
    color: #0F172A;
    font-weight: 850;
    font-size: 14px;
}
.p2-badge {
    display: inline-block;
    padding: 5px 9px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 850;
    margin-right: 5px;
    margin-bottom: 5px;
}
.p2-badge-green { background: #DCFCE7; color: #166534; }
.p2-badge-blue { background: #DBEAFE; color: #1D4ED8; }
.p2-badge-amber { background: #FEF3C7; color: #92400E; }
.p2-badge-red { background: #FEE2E2; color: #991B1B; }
.p2-small-note {
    color: #64748B;
    font-size: 12px;
}
@media (max-width: 1100px) {
    .p2-kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
    .p2-hero h1 { font-size: 34px; }
}
@media (max-width: 760px) {
    .p2-kpi-grid { grid-template-columns: 1fr; }
    .p2-hero-total-label, .p2-hero-total-value { text-align: left; }
}
</style>
"""


# ──────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ──────────────────────────────────────────────────────────────────────────────

def _fmt_usd(value: Any) -> str:
    try:
        v = float(value or 0)
        if v <= 0:
            return "Pendiente"
        return f"USD {v:,.0f}"
    except Exception:
        return "—"


def _fmt_ars(value: Any) -> str:
    try:
        v = float(value or 0)
        if v <= 0:
            return "—"
        return f"ARS {v:,.0f}"
    except Exception:
        return "—"


def _fmt_pct(value: Any) -> str:
    try:
        v = float(value or 0)
        if v <= 0:
            return "—"
        return f"{v * 100:.1f}%"
    except Exception:
        return "—"


def _project_root() -> str:
    return os.path.dirname(os.path.abspath(__file__))


def _badge(label: str, color: str) -> str:
    color_class = {
        "green": "p2-badge-green",
        "blue": "p2-badge-blue",
        "amber": "p2-badge-amber",
        "red": "p2-badge-red",
    }.get(color, "p2-badge-blue")
    return f'<span class="p2-badge {color_class}">{label}</span>'


# ──────────────────────────────────────────────────────────────────────────────
# Data assembly: O(n), no recalculation
# ──────────────────────────────────────────────────────────────────────────────

def _cargar_resultados_cache(propiedades: list[dict[str, Any]]) -> tuple[dict[str, dict], dict[str, dict]]:
    """Lee valuaciones cacheadas. No llama al motor ni recalcula.
    Si una propiedad no tiene entrada en el cache pero tiene
    _ultima_valuacion en el propio json, la usa como fallback.
    """
    from parsers.valuacion_cache import CACHE_VERSION, cargar_cache_valuaciones

    cache = cargar_cache_valuaciones()
    resultados: dict[str, dict] = {}
    estados: dict[str, dict] = {}

    for prop in propiedades:
        nombre = prop.get("nombre", "")
        entrada = cache.get(nombre)
        ultima = prop.get("_ultima_valuacion")
        processed = False

        if entrada:
            if entrada.get("cache_version") != CACHE_VERSION:
                estados[nombre] = {
                    "estado": "version",
                    "label": "Actualizar",
                    "badge": "blue",
                    "detalle": f"Cache {entrada.get('cache_version', '?')} → {CACHE_VERSION}",
                }
                processed = True
            else:
                resultado = entrada.get("resultado_completo", {}) or {}
                if not resultado.get('_cache', {}).get('preview', False):
                    # Cache oficial (no preview)
                    resultados[nombre] = resultado
                    processed = True
                    if resultado.get("error"):
                        estados[nombre] = {
                            "estado": "error",
                            "label": "Error",
                            "badge": "red",
                            "detalle": str(resultado.get("error"))[:120],
                        }
                    else:
                        estados[nombre] = {
                            "estado": "ok",
                            "label": "Actualizada",
                            "badge": "green",
                            "detalle": entrada.get("fecha_legible", ""),
                        }

        if not processed:
            if ultima:
                # Fallback: usar resumen guardado en propiedades.json
                resultados[nombre] = {
                    "valor_propiedad_usd": ultima.get("valor_usd"),
                    "alquiler_estimado_ars": ultima.get("alquiler_ars"),
                    "cap_rate": ultima.get("cap_rate"),
                    "m2_equivalentes": ultima.get("m2_equivalentes"),
                    "resolution_metadata": {"n_propiedades": ultima.get("comps", 0)},
                }
                estados[nombre] = {
                    "estado": "ok",
                    "label": "Actualizada",
                    "badge": "green",
                    "detalle": ultima.get("fecha", ""),
                }
            else:
                estados[nombre] = {
                    "estado": "pendiente",
                    "label": "Pendiente",
                    "badge": "amber",
                    "detalle": "Sin valuación cacheada",
                }

    return resultados, estados


def _build_rows(propiedades: list[dict[str, Any]], resultados: dict[str, dict], estados: dict[str, dict]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for prop in propiedades:
        nombre = prop.get("nombre", "")
        res = resultados.get(nombre, {}) or {}
        meta = res.get("resolution_metadata", {}) or {}
        estado = estados.get(nombre, {}) or {}

        valor = float(res.get("valor_propiedad_usd", 0) or 0)
        alquiler = float(res.get("alquiler_estimado_ars", 0) or 0)
        cap_rate = float(res.get("cap_rate", 0) or 0)
        comps = int(meta.get("n_propiedades", meta.get("n_filtradas", 0)) or 0)

        if comps >= 15:
            conf_label, conf_badge = "Alta", "green"
        elif comps >= 8:
            conf_label, conf_badge = "Media", "amber"
        elif comps > 0:
            conf_label, conf_badge = "Baja", "red"
        else:
            conf_label, conf_badge = "Sin datos", "amber"

        rows.append({
            "id": prop.get("id", f"_no_id_{nombre}"),
            "nombre": nombre,
            "zona": prop.get("zona") or "Sin zona",
            "tipo": prop.get("tipo_inmueble") or "",
            "direccion": prop.get("direccion") or "",
            "dormitorios": prop.get("dormitorios", 0),
            "m2": res.get("m2_equivalentes") or prop.get("m2_cubiertos", 0) or 0,
            "lat": prop.get("lat"),
            "lon": prop.get("lon"),
            "valor_usd": valor,
            "alquiler_ars": alquiler,
            "cap_rate": cap_rate,
            "comps": comps,
            "estado_label": estado.get("label", "Pendiente"),
            "estado_badge": estado.get("badge", "amber"),
            "estado_detalle": estado.get("detalle", ""),
            "conf_label": conf_label,
            "conf_badge": conf_badge,
        })

    return rows


def _fecha_cache_scraping() -> str | None:
    cache_path = os.path.join(_project_root(), "cache_scraping.json")
    if not os.path.exists(cache_path):
        return None
    try:
        with open(cache_path, 'r', encoding='utf-8') as _f:
            _meta = json.load(_f)
        _raw = _meta.get('fecha', '')
        return _raw[:10] if _raw else None
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Navigation actions
# ──────────────────────────────────────────────────────────────────────────────

def _force_nav(page: str) -> None:
    st.session_state["_force_nav_page"] = page


def _ir_a_detalle(nombre: str, forzar: bool = False) -> None:
    import logging
    logging.warning(f"[NAV] Click Ver detalle | prop={nombre} | vista_prev={st.session_state.get('page', '?')} | forzar={forzar}")
    with profile_block("NAV_click_detalle", None):
        from valu import _limpiar_estado_propiedad
        _limpiar_estado_propiedad(nombre)
        if forzar:
            st.session_state[f"forzar_recalculo_{nombre}"] = True
        st.session_state.prop_sel = nombre
        logging.warning(f"[NAV] Set prop_sel={nombre} → st.rerun()")
        st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# Render sections
# ──────────────────────────────────────────────────────────────────────────────

def _render_header(rows: list[dict[str, Any]], fecha_mercado: str | None) -> None:
    total_usd = sum(r["valor_usd"] for r in rows)
    valuadas = len([r for r in rows if r["valor_usd"] > 0])
    n = len(rows)

    st.markdown(f"""
    <div class="p2-hero">
      <div style="display:flex;justify-content:space-between;gap:22px;align-items:flex-start;flex-wrap:wrap;">
        <div>
          <div class="p2-hero-eyebrow">Valu Portfolio Intelligence</div>
          <h1>Portafolio</h1>
          <p>{n:,} propiedades · {valuadas:,} valuadas · Rosario, Argentina</p>
          <p>Datos de mercado: {fecha_mercado or "sin fecha disponible"}</p>
        </div>
        <div>
          <div class="p2-hero-total-label">Valor estimado</div>
          <div class="p2-hero-total-value">{_fmt_usd(total_usd)}</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def _render_kpis(rows: list[dict[str, Any]], usdt_ars: float) -> None:
    total_usd = sum(r["valor_usd"] for r in rows)
    total_ars = total_usd * usdt_ars
    alquiler_total = sum(r["alquiler_ars"] for r in rows)
    caps = [r["cap_rate"] for r in rows if r["cap_rate"] > 0]
    cap_prom = sum(caps) / len(caps) if caps else 0
    pendientes = len([r for r in rows if r["valor_usd"] <= 0])
    n = len(rows)

    st.markdown(f"""
    <div class="p2-kpi-grid">
      <div class="p2-kpi-card">
        <div class="p2-kpi-label">Valor portfolio</div>
        <div class="p2-kpi-value">{_fmt_usd(total_usd)}</div>
        <div class="p2-kpi-sub">ARS {total_ars/1_000_000:,.1f}M aprox.</div>
      </div>
      <div class="p2-kpi-card">
        <div class="p2-kpi-label">Renta mensual</div>
        <div class="p2-kpi-value">{_fmt_ars(alquiler_total)}</div>
        <div class="p2-kpi-sub">USD {alquiler_total/usdt_ars:,.0f} aprox.</div>
      </div>
      <div class="p2-kpi-card">
        <div class="p2-kpi-label">Cap Rate promedio</div>
        <div class="p2-kpi-value">{cap_prom*100:.1f}%</div>
        <div class="p2-kpi-sub">Sobre {len(caps):,} propiedades valuadas</div>
      </div>
      <div class="p2-kpi-card">
        <div class="p2-kpi-label">Estado de valuación</div>
        <div class="p2-kpi-value">{n - pendientes:,}/{n:,}</div>
        <div class="p2-kpi-sub">{pendientes:,} pendientes o sin cache vigente</div>
      </div>
    </div>
    """, unsafe_allow_html=True)


def _render_filters(rows: list[dict[str, Any]]) -> dict[str, Any]:
    zonas = sorted({r["zona"] for r in rows if r.get("zona")})
    tipos = sorted({r["tipo"] for r in rows if r.get("tipo")})
    estados = sorted({r["estado_label"] for r in rows if r.get("estado_label")})

    with st.container(border=True):
        c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
        with c1:
            q = st.text_input("Buscar", placeholder="Nombre, zona o dirección", key="p2_buscar")
        with c2:
            zona = st.multiselect("Zona", zonas, key="p2_zona")
        with c3:
            tipo = st.multiselect("Tipo", tipos, key="p2_tipo")
        with c4:
            estado = st.multiselect("Estado", estados, key="p2_estado")

        c5, c6, c7, c8 = st.columns([1, 1, 1, 1])
        with c5:
            cap_min = st.slider("Cap Rate mínimo", 0.0, 10.0, 0.0, 0.5, key="p2_cap_min")
        with c6:
            orden = st.selectbox(
                "Ordenar",
                [
                    "Valor USD ↓", "Valor USD ↑",
                    "Cap Rate ↓", "Cap Rate ↑",
                    "Alquiler ↓", "Alquiler ↑",
                    "Nombre A→Z", "Nombre Z→A",
                ],
                key="p2_orden",
            )
        with c7:
            vista = st.radio("Vista", ["Cards", "Mapa", "Tabla", "Analytics"], horizontal=True, key="p2_vista")
        with c8:
            page_size = st.selectbox("Cards/pág.", [12, 24, 48], index=1, key="p2_page_size")

    return {
        "q": q,
        "zona": zona,
        "tipo": tipo,
        "estado": estado,
        "cap_min": cap_min / 100,
        "orden": orden,
        "vista": vista,
        "page_size": int(page_size),
    }


def _apply_filters(rows: list[dict[str, Any]], filtros: dict[str, Any]) -> list[dict[str, Any]]:
    q = (filtros.get("q") or "").lower().strip()
    out: list[dict[str, Any]] = []

    for row in rows:
        if filtros["zona"] and row["zona"] not in filtros["zona"]:
            continue
        if filtros["tipo"] and row["tipo"] not in filtros["tipo"]:
            continue
        if filtros["estado"] and row["estado_label"] not in filtros["estado"]:
            continue
        if filtros["cap_min"] and row["cap_rate"] < filtros["cap_min"]:
            continue
        if q:
            blob = f"{row['nombre']} {row['zona']} {row['direccion']}".lower()
            if q not in blob:
                continue
        out.append(row)

    sorters = {
        "Valor USD ↓": ("valor_usd", True),
        "Valor USD ↑": ("valor_usd", False),
        "Cap Rate ↓": ("cap_rate", True),
        "Cap Rate ↑": ("cap_rate", False),
        "Alquiler ↓": ("alquiler_ars", True),
        "Alquiler ↑": ("alquiler_ars", False),
        "Nombre A→Z": ("nombre", False),
        "Nombre Z→A": ("nombre", True),
    }
    key, reverse = sorters.get(filtros["orden"], ("valor_usd", True))
    return sorted(out, key=lambda r: (r.get(key) or 0), reverse=reverse)


def _render_cards(rows: list[dict[str, Any]], page_size: int) -> None:
    if not rows:
        st.info("No encontramos propiedades con esos filtros.")
        return

    total_pages = max(1, (len(rows) + page_size - 1) // page_size)
    page = st.number_input("Página", min_value=1, max_value=total_pages, value=1, step=1, key="p2_cards_page")
    start = (int(page) - 1) * page_size
    page_rows = rows[start:start + page_size]
    st.caption(f"Mostrando {len(page_rows)} propiedades de {len(rows):,} · página {page}/{total_pages}")

    for idx in range(0, len(page_rows), 3):
        cols = st.columns(3)
        for col, row in zip(cols, page_rows[idx:idx + 3]):
            with col:
                import urllib.parse
                nombre_encoded = urllib.parse.quote(row['nombre'])
                badges = _badge(row["estado_label"], row["estado_badge"]) + _badge(f"Confianza {row['conf_label']}", row["conf_badge"])
                st.markdown(f"""
                <a href="?prop={nombre_encoded}" style="text-decoration:none;color:inherit;display:block;">
                <div class="p2-property-card">
                    <div>{badges}</div>
                    <div class="p2-property-title">{row['nombre']}</div>
                    <div class="p2-muted">{row['zona']} · {row['tipo']} · {row['dormitorios']} dorm.</div>
                    <div class="p2-muted">{row['direccion']}</div>
                    <div class="p2-price">{_fmt_usd(row['valor_usd'])}</div>
                    <div class="p2-muted">{row['comps']} comparables · {row['estado_detalle']}</div>
                    <div class="p2-card-metrics">
                        <div class="p2-mini-metric"><div class="p2-mini-label">Alquiler</div><div class="p2-mini-value">{_fmt_ars(row['alquiler_ars'])}</div></div>
                        <div class="p2-mini-metric"><div class="p2-mini-label">Cap Rate</div><div class="p2-mini-value">{_fmt_pct(row['cap_rate'])}</div></div>
                        <div class="p2-mini-metric"><div class="p2-mini-label">m² eq.</div><div class="p2-mini-value">{float(row['m2'] or 0):.1f}</div></div>
                    </div>
                </div>
                </a>
                """, unsafe_allow_html=True)


def _marker_color(row: dict[str, Any]) -> str:
    if row["valor_usd"] <= 0:
        return "orange"
    if row["cap_rate"] >= 0.06:
        return "green"
    if row["cap_rate"] >= 0.04:
        return "blue"
    if row["cap_rate"] > 0:
        return "red"
    return "gray"


def _render_map(rows: list[dict[str, Any]]) -> None:
    try:
        import folium
        from folium.plugins import MarkerCluster
        from streamlit.components.v1 import html
    except Exception as exc:
        st.warning(f"Mapa no disponible: {exc}")
        return

    props = [r for r in rows if r.get("lat") and r.get("lon")]
    if not props:
        st.info("No hay propiedades con coordenadas para mostrar en el mapa.")
        return

    max_options = [250, 500, 1000, 2000, 5000]
    default_idx = 1 if len(props) > 500 else 0
    max_markers = st.selectbox("Máximo de marcadores a renderizar", max_options, index=default_idx, key="p2_max_markers")
    props_to_render = props[:max_markers]

    lats = [float(r["lat"]) for r in props_to_render]
    lons = [float(r["lon"]) for r in props_to_render]
    m = folium.Map(tiles="cartodbpositron")
    cluster = MarkerCluster(name="Propiedades").add_to(m)

    for row in props_to_render:
        popup = f"""
        <b>{row['nombre']}</b><br>
        {row['zona']}<br>
        {row['direccion']}<br>
        <b>{_fmt_usd(row['valor_usd'])}</b><br>
        Cap Rate: {_fmt_pct(row['cap_rate'])}<br>
        {row['estado_label']} · Confianza {row['conf_label']}
        """
        folium.Marker(
            [float(row["lat"]), float(row["lon"])],
            popup=popup,
            tooltip=f"{row['nombre']} · {_fmt_usd(row['valor_usd'])}",
            icon=folium.Icon(color=_marker_color(row), icon="home"),
        ).add_to(cluster)

    pad_lat = max(max(lats) - min(lats), 0.012)
    pad_lon = max(max(lons) - min(lons), 0.012)
    m.fit_bounds(
        [[min(lats) - pad_lat * 0.35, min(lons) - pad_lon * 0.35],
         [max(lats) + pad_lat * 0.35, max(lons) + pad_lon * 0.35]],
        max_zoom=14,
    )

    st.markdown('<div class="p2-section-card">', unsafe_allow_html=True)
    st.subheader("Distribución geográfica del portfolio")
    html(m._repr_html_(), height=480)
    if len(props) > max_markers:
        st.caption(f"Mostrando {max_markers:,} de {len(props):,} propiedades con coordenadas para mantener fluida la vista.")
    st.caption("Colores: verde = alto Cap Rate, azul = normal, naranja = pendiente, rojo = bajo rendimiento.")
    st.markdown("</div>", unsafe_allow_html=True)


def _render_table(rows: list[dict[str, Any]]) -> None:
    if not rows:
        st.info("No hay propiedades para mostrar.")
        return

    df = pd.DataFrame(rows)
    df_display = pd.DataFrame({
        "Nombre": df["nombre"],
        "Zona": df["zona"],
        "Tipo": df["tipo"],
        "Dorm.": df["dormitorios"],
        "m²": df["m2"].map(lambda v: f"{float(v or 0):.1f}"),
        "Valor USD": df["valor_usd"].map(_fmt_usd),
        "Alquiler": df["alquiler_ars"].map(_fmt_ars),
        "Cap Rate": df["cap_rate"].map(_fmt_pct),
        "Estado": df["estado_label"],
        "Confianza": df["conf_label"],
        "Comps": df["comps"],
    })

    st.markdown('<div class="p2-section-card">', unsafe_allow_html=True)
    st.subheader("Tabla ejecutiva")
    st.dataframe(df_display, hide_index=True, width="stretch")
    st.download_button(
        "Exportar CSV",
        data=df_display.to_csv(index=False).encode("utf-8"),
        file_name=f"portfolio2_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        use_container_width=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)


def _render_alerts(rows: list[dict[str, Any]]) -> None:
    pendientes = [r for r in rows if r["valor_usd"] <= 0]
    baja_conf = [r for r in rows if r["conf_label"] == "Baja"]
    sin_coords = [r for r in rows if not r.get("lat") or not r.get("lon")]

    st.markdown('<div class="p2-section-card">', unsafe_allow_html=True)
    st.subheader("Alertas del portfolio")
    if not pendientes and not baja_conf and not sin_coords:
        st.success("Portfolio sin alertas críticas.")
    else:
        if pendientes:
            st.warning(f"{len(pendientes):,} propiedades pendientes de valuación o sin cache vigente.")
        if baja_conf:
            st.warning(f"{len(baja_conf):,} propiedades con baja confianza estadística.")
        if sin_coords:
            st.warning(f"{len(sin_coords):,} propiedades sin coordenadas.")
    st.markdown("</div>", unsafe_allow_html=True)


def _render_analytics(rows: list[dict[str, Any]]) -> None:
    if not rows:
        st.info("No hay datos para analizar.")
        return

    df = pd.DataFrame(rows)
    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="p2-section-card">', unsafe_allow_html=True)
        st.subheader("Valor por zona")
        df_zona = (
            df.groupby("zona", as_index=False)
              .agg(valor_usd=("valor_usd", "sum"), propiedades=("nombre", "count"))
              .sort_values("valor_usd", ascending=False)
        )
        df_zona["Valor"] = df_zona["valor_usd"].map(_fmt_usd)
        st.dataframe(df_zona[["zona", "propiedades", "Valor"]], hide_index=True, width="stretch")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="p2-section-card">', unsafe_allow_html=True)
        st.subheader("Top Cap Rate")
        top = sorted([r for r in rows if r["cap_rate"] > 0], key=lambda r: r["cap_rate"], reverse=True)[:10]
        if not top:
            st.info("Sin Cap Rate disponible.")
        else:
            for i, row in enumerate(top, 1):
                st.write(f"**{i}. {row['nombre']}** — {row['zona']} — {_fmt_pct(row['cap_rate'])}")
        st.markdown("</div>", unsafe_allow_html=True)

    _render_alerts(rows)


def _render_empty_state() -> None:
    st.markdown("""
    <div class="p2-hero">
        <div class="p2-hero-eyebrow">Valu Portfolio Intelligence</div>
        <h1>Portafolio</h1>
        <p>Todavía no cargaste propiedades. Agregá tu primera unidad para obtener valor estimado, alquiler esperado y Cap Rate.</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("Agregar primera propiedad", type="primary"):
        _force_nav("Configuración")
        st.rerun()


# ──────────────────────────────────────────────────────────────────────────────
# Public entrypoint
# ──────────────────────────────────────────────────────────────────────────────

def mostrar_portfolio2(
    cargar_propiedades_fn: Callable[[], list[dict[str, Any]]],
    obtener_usdt_fn: Callable[[], float],
) -> None:
    """Renderiza Portfolio2.

    La función recibe callbacks desde `valu.py` para no duplicar rutas ni lógica
    de carga de propiedades. No recalcula valuaciones.
    """
    st.markdown(PORTFOLIO2_CSS, unsafe_allow_html=True)

    propiedades = cargar_propiedades_fn()
    if not propiedades:
        _render_empty_state()
        return

    with profile_block("portfolio_cargar_cache", None):
        resultados, estados = _cargar_resultados_cache(propiedades)
    with profile_block("portfolio_build_rows", None):
        rows = _build_rows(propiedades, resultados, estados)
    usdt_ars = float(obtener_usdt_fn() or 1480.0)

    with profile_block("portfolio_header", None):
        _render_header(rows, _fecha_cache_scraping())
    with profile_block("portfolio_kpis", None):
        _render_kpis(rows, usdt_ars)

    if st.button("Agregar propiedad", type="primary", use_container_width=True):
        _force_nav("Configuración")
        st.rerun()
 
    with profile_block("portfolio_filters", None):
        filtros = _render_filters(rows)
        rows_filtradas = _apply_filters(rows, filtros)
    st.caption(f"{len(rows_filtradas):,} de {len(rows):,} propiedades visibles")

    vista = filtros["vista"]
    if vista == "Cards":
        with profile_block("portfolio_cards", None):
            _render_cards(rows_filtradas, page_size=filtros["page_size"])
    elif vista == "Mapa":
        with profile_block("portfolio_mapa", None):
            _render_map(rows_filtradas)
    elif vista == "Tabla":
        _render_table(rows_filtradas)
    elif vista == "Analytics":
        _render_analytics(rows_filtradas)
