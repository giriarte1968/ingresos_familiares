#!/usr/bin/env python3
"""
Genera PDF con branding TTL Propiedades (script separado, no modifica la app).
Uso: python gen_pdf_ttl.py [nombre_propiedad]
"""
import json, os, sys, base64, subprocess, tempfile
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def safe_int(v, default=0):
    try:
        return int(v) if v is not None else default
    except (ValueError, TypeError):
        return default

def safe_float(v, default=0.0):
    try:
        return float(v) if v is not None else default
    except (ValueError, TypeError):
        return default


def load_property(nombre):
    with open(os.path.join(BASE_DIR, 'propiedades.json'), 'r', encoding='utf-8') as f:
        data = json.load(f)
    for p in data['propiedades']:
        if p.get('nombre') == nombre:
            return p
    return None


def load_cache(nombre):
    cache_path = os.path.join(BASE_DIR, 'data', 'valuaciones_cache.json')
    if not os.path.exists(cache_path):
        return None
    with open(cache_path, 'r', encoding='utf-8') as f:
        all_cache = json.load(f)
    entry = all_cache.get(nombre)
    if not entry:
        return None
    # The cache structure has resultado_completo inside
    return {'resultado': entry.get('resultado_completo', {}), 'cache_meta': entry}


def build_context(prop, cache_data):
    from parsers.valuacion_cache import CACHE_VERSION
    from parsers.mercado_inmobiliario import calcular_factores_display

    res = cache_data.get('resultado', {}) if cache_data else {}
    auto_result = res.get('_auto_result', res)

    # Usar UV de la propiedad si tiene manual (más reciente que cache)
    uv = prop.get('_ultima_valuacion', {}) or {}
    if uv.get('fuente') == 'manual' and uv.get('manual_valor_usd', 0) > 0:
        # La UV tiene la valuación manual guardada — usarla como fuente principal
        res['manual_params'] = uv.get('manual_params', {})
        res['valor_propiedad_usd'] = uv.get('manual_valor_usd')
        res['_fuente_activa'] = 'manual'
        res['m2_base_venta'] = uv.get('m2_base_venta', res.get('m2_base_venta'))
        res['m2_equivalentes'] = uv.get('m2_equivalentes', res.get('m2_equivalentes'))
        res['cap_rate'] = uv.get('cap_rate', res.get('cap_rate'))
        res['usdt_ars'] = uv.get('usdt_ars', res.get('usdt_ars'))
        res['comparables_venta'] = res.get('comparables_venta', [])
        auto_result = {'valor_propiedad_usd': uv.get('auto_valor_usd', 0)} if uv.get('auto_valor_usd', 0) > 0 else auto_result

    manual_params = res.get('manual_params', {}) or {}
    tiene_manual = bool(manual_params)
    tiene_auto = bool(auto_result.get('valor_propiedad_usd', 0) > 0)

    v_auto = safe_int(auto_result.get('valor_propiedad_usd'))
    v_auto_cons = safe_int(auto_result.get('valor_venta_conservador'))
    v_auto_opt = safe_int(auto_result.get('valor_venta_optimista'))
    v_auto_m2 = safe_int(auto_result.get('m2_base_venta'))
    n_comps_auto = safe_int(res.get('resolution_metadata', {}).get('n_propiedades', 0))

    v_manual = safe_int(res.get('valor_propiedad_usd'))
    v_manual_cons = safe_int(res.get('valor_venta_conservador'))
    v_manual_opt = safe_int(res.get('valor_venta_optimista'))

    fuente_activa = res.get('_fuente_activa', 'auto')
    if tiene_manual and tiene_auto:
        valor_adoptado = v_manual if fuente_activa == 'manual' else v_auto
        fuente_adoptada = "Manual (Tasador)" if fuente_activa == 'manual' else "Por Comparables"
    else:
        valor_adoptado = v_manual or v_auto
        fuente_adoptada = "Por Comparables" if tiene_auto else "Manual"

    # Alquiler — usar lógica unificada
    from valu_detail_sections import _recalcular_alquiler
    recalc = _recalcular_alquiler(prop, res, auto_result=auto_result)
    alq_ars = recalc['alq_ars']
    cap_rate = recalc['cap_rate']
    dolar = recalc['dolar']
    alq_usd = int(alq_ars / dolar) if dolar > 0 else 0

    m2_base = safe_int(res.get('m2_base_venta'))
    m2_eq = safe_float(res.get('m2_equivalentes') or prop.get('m2', 0))

    # Comparables
    comps = res.get('comparables_venta', [])
    comps_sorted = sorted(comps, key=lambda c: abs(c.get('precio_m2', 0) * c.get('time_adjustment', 1.0) - m2_base))[:76]
    comparables_list = []
    comp_coords = []
    for c in comps_sorted:
        comparables_list.append({
            'direccion': (c.get('direccion', '') or '')[:40],
            'm2': c.get('m2', ''),
            'dormitorios': c.get('dormitorios', ''),
            'precio_m2': f"${c.get('precio_m2', 0):,.0f}",
            'precio': f"${c.get('precio', 0):,.0f}",
            'distancia_m': f"{c.get('distancia_m', 0):.0f}",
            'antiguedad': c.get('antiguedad', c.get('antiquity', '')),
        })
        clat = c.get('lat') or c.get('latitud')
        clon = c.get('lon') or c.get('longitud')
        if clat and clon:
            try:
                comp_coords.append((float(clat), float(clon)))
            except (ValueError, TypeError):
                pass

    # Logo TTL como base64
    logo_b64 = ""
    logo_path = os.path.join(BASE_DIR, "logos TTL PROPIEDADES.jpg")
    if os.path.exists(logo_path):
        with open(logo_path, "rb") as f:
            logo_b64 = base64.b64encode(f.read()).decode()

    # Mapa
    map_b64 = ""
    prop_lat = safe_float(prop.get('lat'), None)
    prop_lon = safe_float(prop.get('lon'), None)
    if prop_lat and prop_lon and comp_coords:
        try:
            import folium
            _m = folium.Map(location=[prop_lat, prop_lon], zoom_start=15, tiles='cartodbpositron', width='100%', height='600px')
            folium.Marker([prop_lat, prop_lon], popup=f"<b>{prop.get('nombre', '')}</b>", icon=folium.Icon(color='red', icon='home')).add_to(_m)
            folium.Circle([prop_lat, prop_lon], radius=1000, color='#3388ff', fill=True, fill_opacity=0.05, weight=1).add_to(_m)
            for clat, clon in comp_coords:
                folium.CircleMarker([clat, clon], radius=5, color='#1a6b6b', fill=True, fill_color='#1a6b6b', fill_opacity=0.7).add_to(_m)
            with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as f:
                _m.save(f.name)
                _map_html = f.name
            with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
                _map_png = f.name
            script = (
                f"from playwright.sync_api import sync_playwright; import time; "
                f"p=sync_playwright().start(); b=p.chromium.launch(headless=True); "
                f"pg=b.new_page(); pg.set_viewport_size({{'width': 1200, 'height': 700}}); "
                f"pg.goto('file:///{_map_html.replace(os.sep, '/')}', wait_until='networkidle'); "
                f"time.sleep(3); pg.screenshot(path=r'{_map_png}', full_page=True); b.close(); p.stop()"
            )
            subprocess.run([sys.executable, '-c', script], capture_output=True, timeout=15)
            if os.path.exists(_map_png) and os.path.getsize(_map_png) > 100:
                with open(_map_png, 'rb') as f:
                    map_b64 = base64.b64encode(f.read()).decode()
            for p_path in [_map_html, _map_png]:
                try: os.unlink(p_path)
                except: pass
        except Exception:
            pass

    # Razonamiento — regenerar con alquiler fresco para consistencia
    meta = res.get('resolution_metadata', {}) or {}
    razonamiento = auto_result.get('razonamiento', '')
    if razonamiento and alq_ars > 0:
        # Actualizar alquiler en el resultado antes de regenerar
        res['alquiler_estimado_ars'] = alq_ars
        res['cap_rate'] = cap_rate
        res['usdt_ars'] = dolar
        auto_result['alquiler_estimado_ars'] = alq_ars
        auto_result['cap_rate'] = cap_rate
        auto_result['usdt_ars'] = dolar
        try:
            from parsers.mercado_inmobiliario import generar_razonamiento_valuacion
            razonamiento = generar_razonamiento_valuacion(prop, auto_result, meta)
        except Exception:
            pass

    # Subfactores hedonicos
    _fd = None
    try:
        _fd = calcular_factores_display(prop)
    except Exception:
        pass

    # Razonamiento manual
    razonamiento_manual = ''
    if tiene_manual and manual_params:
        _mp = manual_params
        _usd_m2 = _mp.get('usd_m2', 0)
        _fh = _mp.get('factor_hedonico', 1.0)
        _incert = _mp.get('incertidumbre_pct', 10.0)
        _lineas_m = []
        _lineas_m.append(
            f"Se realizó una valuación manual utilizando el <strong>punto de referencia geográfico</strong> "
            f"más cercano a la propiedad, considerando un radio de 400 metros alrededor de la sujeto. "
            f"El punto de referencia selected (ancla) tiene un valor de <strong>USD {_usd_m2}/m²</strong> "
            f"en el mercado de venta."
        )
        _lineas_m.append(
            f"El <strong>factor hedónico</strong> aplicado es de <strong>{_fh:.2f}</strong>, "
            f"lo que representa un ajuste del {((_fh - 1.0) * 100):+.1f}% sobre el valor del punto de referencia."
        )
        _lineas_m.append(
            f"El valor final se calcula multiplicando los metros cuadrados equivalentes ({m2_eq:.1f} m²) "
            f"por el valor del punto de referencia (USD {_usd_m2}/m²) y el factor hedónico ({_fh:.2f})."
        )
        razonamiento_manual = '<br><br>'.join(_lineas_m)

    # Catastro
    catastro_data = None
    catastro = prop.get('catastro', {})
    if catastro:
        catastro_data = {
            'ph': catastro.get('ph', '—'),
            'anio': catastro.get('anio_construccion', '—'),
            'seccion': catastro.get('seccion', '—'),
            'grafico': catastro.get('grafico', '—'),
        }

    # Activos
    activos_list = []
    total_activos = 0
    for a in prop.get('activos', []):
        v = safe_int(a.get('valor'))
        if v > 0:
            activos_list.append({'nombre': a.get('nombre', '?'), 'valor': f"{v:,}"})
            total_activos += v

    # CV qualitative
    cv = meta.get('cv_pool', 0)
    if cv < 0.2:
        cv_qualitative = "Alta confianza"
    elif cv < 0.3:
        cv_qualitative = "Confianza media"
    else:
        cv_qualitative = "Mayor dispersión"

    # Fecha scraping
    fecha_scraping = cache_data.get('cache_meta', {}).get('fecha', '—') if cache_data else '—'

    ctx = dict(
        nombre=prop.get('nombre', ''),
        direccion=prop.get('direccion', ''),
        zona=prop.get('zona', ''),
        fecha_generacion=datetime.now().strftime('%d/%m/%Y %H:%M'),
        cache_version=CACHE_VERSION,
        fecha_scraping=fecha_scraping,
        tiene_auto=tiene_auto,
        tiene_manual=tiene_manual,
        v_auto=f"{v_auto:,}",
        v_auto_cons=f"{v_auto_cons:,}",
        v_auto_opt=f"{v_auto_opt:,}",
        v_auto_spread=f"{v_auto_opt - v_auto_cons:,}" if v_auto and v_auto_opt and v_auto_cons else "",
        v_auto_m2=f"{v_auto_m2:,}",
        n_comps_auto=n_comps_auto,
        v_manual=f"{v_manual:,}",
        v_manual_cons=f"{v_manual_cons:,}",
        v_manual_opt=f"{v_manual_opt:,}",
        v_manual_spread=f"{v_manual_opt - v_manual_cons:,}" if v_manual and v_manual_opt and v_manual_cons else "",
        valor_adoptado=f"{valor_adoptado:,}",
        fuente_adoptada=fuente_adoptada,
        v_manual_m2=f"{int(v_manual / m2_eq):,}" if v_manual and m2_eq else "",
        m2_eq=f"{m2_eq:.1f}" if isinstance(m2_eq, (int, float)) and m2_eq else "N/D",
        m2_total=prop.get('m2', 0) or 0,
        m2_cub=prop.get('m2_cubiertos', 0) or 0,
        m2_desc=prop.get('m2_descubiertos', 0) or 0,
        dormitorios=prop.get('dormitorios', ''),
        banos=prop.get('banos', prop.get('baños', '')),
        antiguedad=prop.get('antiguedad', prop.get('antiquity', '')),
        anio_const=prop.get('anio_construccion', '?'),
        estado=prop.get('estado_detalle', 'bueno'),
        tipo_inmueble=prop.get('tipo_inmueble', ''),
        constructora=prop.get('constructora', ''),
        calidad_edificio=prop.get('calidad_edificio', 'estándar'),
        piso=prop.get('piso', ''),
        total_pisos=prop.get('total_pisos', ''),
        expensas=prop.get('expensas_ars', ''),
        ambientes=prop.get('ambientes', ''),
        orientacion=prop.get('orientacion', ''),
        ventilacion=prop.get('ventilacion', ''),
        vista=prop.get('vista', ''),
        m2_semi=prop.get('m2_semicubiertos', 0) or 0,
        toilet=prop.get('toilet', False),
        cocheras=prop.get('cocheras_cantidad', 0),
        baulera=prop.get('baulera', False),
        ascensores=prop.get('ascensores_edificio', ''),
        seguridad=prop.get('seguridad', ''),
        terminaciones=prop.get('terminaciones', ''),
        descripcion_libre=prop.get('descripcion_libre', ''),
        amenities_list=', '.join(prop.get('detalles_categoria', [])[:5]) if prop.get('detalles_categoria') else '',
        balcon=prop.get('balcon', False),
        tipo_balcon=prop.get('tipo_balcon', ''),
        m2_semi_detalle=prop.get('m2_semicubiertos_detalle', ''),
        disposicion=prop.get('disposicion', ''),
        ubicacion_tipo=prop.get('ubicacion_tipo', ''),
        reciclado=prop.get('reciclado', False),
        reciclado_tipo=prop.get('reciclado_tipo', ''),
        anio_reciclado=prop.get('anio_reciclado', ''),
        gas_ok=prop.get('gas_ok', ''),
        doble_ingreso=prop.get('doble_ingreso', False),
        despensa=prop.get('despensa', False),
        lavadero_independiente=prop.get('lavadero_independiente', False),
        placares_completos=prop.get('placares_completos', False),
        layout_flexible=prop.get('layout_flexible', False),
        cocheras_tipo=prop.get('cocheras_tipo', ''),
        valor_cochera_base=prop.get('valor_cochera_base', ''),
        carpinteria=prop.get('carpinteria', ''),
        terminaciones_suelo=prop.get('terminaciones_suelo', ''),
        terminaciones_cocina=prop.get('terminaciones_cocina', ''),
        ventilacion_bano=prop.get('ventilacion_bano', ''),
        alquiler_ars=f"{alq_ars:,}",
        alquiler_usd=f"{alq_usd:,}",
        cap_rate=f"{cap_rate*100:.1f}%",
        m2_base=f"${m2_base:,}" if m2_base else "N/D",
        comparables=comparables_list,
        razonamiento=razonamiento,
        razonamiento_manual=razonamiento_manual,
        fd_estado=f"{(_fd.get('factor_estado', 1.0) - 1.0) * 100:+.1f}%" if _fd else "+0.0%",
        fd_calidad=f"{(_fd.get('factor_calidad', 1.0) - 1.0) * 100:+.1f}%" if _fd else "+0.0%",
        fd_amenities=f"{_fd.get('delta_amenities', 0) * 100:+.1f}%" if _fd else "+0.0%",
        fd_otros=f"{_fd.get('delta_otros', 0) * 100:+.1f}%" if _fd else "+0.0%",
        fd_total=f"{_fd.get('total', 1.0):.4f}" if _fd else "1.0000",
        fd_estado_label=_fd.get('estado_label', '') if _fd else '',
        fd_calidad_label=_fd.get('calidad_label', '') if _fd else '',
        fd_amenities_detalle=_fd.get('detalle_amenities', '') if _fd else '',
        radio_m=meta.get('radio_usado', 1000),
        cv_qualitative=cv_qualitative,
        tiene_activos=total_activos > 0,
        activos=activos_list,
        total_activos=f"{total_activos:,}",
        catastro=catastro_data,
        logo_b64=logo_b64,
        map_b64=map_b64,
    )
    return ctx


def render_html(ctx):
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader(os.path.join(BASE_DIR, 'templates')))
    template = env.get_template('reporte_ttl.html')
    return template.render(**ctx)


def html_to_pdf(html_content):
    with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w', encoding='utf-8') as f:
        f.write(html_content)
        html_path = f.name
    with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
        pdf_path = f.name
    try:
        script = (
            f"from playwright.sync_api import sync_playwright; "
            f"p=sync_playwright().start(); b=p.chromium.launch(headless=True); "
            f"pg=b.new_page(); pg.goto('file:///{html_path.replace(os.sep, '/')}', wait_until='networkidle'); "
            f"pg.pdf(path=r'{pdf_path}', format='A4', print_background=True); "
            f"b.close(); p.stop()"
        )
        result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"Playwright error: {result.stderr[:500]}")
        with open(pdf_path, 'rb') as f:
            return f.read()
    finally:
        try: os.unlink(html_path)
        except: pass
        try: os.unlink(pdf_path)
        except: pass


def main():
    if len(sys.argv) < 2:
        # List available properties
        with open(os.path.join(BASE_DIR, 'propiedades.json'), 'r', encoding='utf-8') as f:
            data = json.load(f)
        print("Propiedades disponibles:")
        for p in data['propiedades']:
            print(f"  - {p.get('nombre')}")
        print(f"\nUso: python gen_pdf_ttl.py <nombre>")
        return

    nombre = sys.argv[1]
    prop = load_property(nombre)
    if not prop:
        print(f"Propiedad '{nombre}' no encontrada.")
        return

    cache_data = load_cache(nombre)
    if not cache_data:
        print(f"No hay cache de valuación para '{nombre}'. Primero ejecutá la valuación en la app.")
        return

    print(f"Generando PDF TTL para: {nombre}")
    ctx = build_context(prop, cache_data)
    html = render_html(ctx)
    pdf = html_to_pdf(html)

    output_path = os.path.join(BASE_DIR, f"reporte_ttl_{nombre.replace(' ', '_')}.pdf")
    with open(output_path, 'wb') as f:
        f.write(pdf)
    print(f"PDF generado: {output_path}")
    print(f"Tamaño: {len(pdf):,} bytes")


if __name__ == '__main__':
    main()
