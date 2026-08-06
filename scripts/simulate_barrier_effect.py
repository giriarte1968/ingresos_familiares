#!/usr/bin/env python3
"""
Simulacion con efecto de barrera v9.
NUEVA FORMULA: Reemplaza alpha/blend/penalty con ajuste individual por barrera.

Flujo:
1. Llamar engine para obtener pool_final (comps filtrados por geo/dorms/CT/size)
2. RE-CLASIFICAR cada comp con barreras corrected (mismas reglas que engine)
3. Para comps cross: detectar QUE barrera cruzan, aplicar efecto individual
4. Calcular P33 de TODO el pool ajustado (same + cross-adjusted)

NO alpha, NO blend, NO penalty del 3%.
"""
import json
import math
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# --- 1. CARGAR DATOS ---
print("Cargando datos...")

with open('barreras_rosario_corrected.json', 'r', encoding='utf-8') as f:
    barreras_data = json.load(f)
barreras = barreras_data.get('features', [])
print(f"  Barreras corrected: {len(barreras)}")

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache_data = json.load(f)
props_cache = cache_data.get('propiedades', [])
print(f"  Props cache: {len(props_cache)}")

with open('propiedades.json', 'r', encoding='utf-8') as f:
    propiedades = json.load(f)['propiedades']
print(f"  Props prueba: {len(propiedades)}")


# --- FUNCIONES AUXILIARES ---
def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _intersect(p1, p2, p3, p4):
    def ccw(A, B, C):
        return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
    return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)


def check_barrier_crossing_with_name(p1, p2, barriers):
    """Igual que engine pero retorna nombre de barrera detectada."""
    for b in barriers:
        props = b.get('properties', {})
        bt = props.get('barrier_type')
        if not bt:
            continue
        coords = b.get('geometry', {}).get('coordinates', [])
        for i in range(len(coords) - 1):
            if _intersect(p1, p2, coords[i], coords[i + 1]):
                return bt, props.get('name', '')
    return False, None


def compute_percentil(pctl, values):
    if not values:
        return None
    s = sorted(values)
    idx = int(len(s) * pctl / 100)
    idx = min(idx, len(s) - 1)
    idx = max(idx, 0)
    return float(s[idx])


def get_barrier_midpoint(geometry):
    coords = geometry.get("coordinates", [])
    if not coords:
        return None, None
    mid = len(coords) // 2
    lon, lat = coords[mid]
    return lat, lon


def get_barrier_direction(geometry):
    coords = geometry.get("coordinates", [])
    if len(coords) < 2:
        return None
    start = coords[0]
    end = coords[-1]
    dx = end[0] - start[0]
    dy = end[1] - start[1]
    length = math.sqrt(dx * dx + dy * dy)
    if length == 0:
        return None
    return (dx / length, dy / length)


def assign_side(lat, lon, barrier_lat, barrier_lon, direction_vec):
    if direction_vec is None:
        return "unknown"
    vprop = (lon - barrier_lon, lat - barrier_lat)
    cross = direction_vec[0] * vprop[1] - direction_vec[1] * vprop[0]
    if cross > 0:
        return "side_A"
    elif cross < 0:
        return "side_B"
    return "on_line"


# --- 2. PRE-CALCULAR EFECTOS DE BARRERA (desde datos RAW del mercado) ---
print("\nPre-calculando efectos de barrera...")

efectos = {}
RADIO_EFECTO = 300

for barrera in barreras:
    nombre = barrera['properties']['name']
    midpoint_lat, midpoint_lon = get_barrier_midpoint(barrera['geometry'])
    if midpoint_lat is None:
        continue

    direction = get_barrier_direction(barrera['geometry'])
    if direction is None:
        continue

    lado_A = []
    lado_B = []

    for p in props_cache:
        if p.get('operacion') != 'venta':
            continue
        vm2 = p.get('valor_m2', 0)
        if not vm2 or vm2 <= 0:
            continue
        lat_p = p.get('lat')
        lon_p = p.get('lon')
        if lat_p is None or lon_p is None:
            continue
        try:
            plat, plon = float(lat_p), float(lon_p)
        except:
            continue

        dist = haversine_m(midpoint_lat, midpoint_lon, plat, plon)
        if dist > RADIO_EFECTO:
            continue

        side = assign_side(plat, plon, midpoint_lat, midpoint_lon, direction)
        if side == "side_A":
            lado_A.append(vm2)
        elif side == "side_B":
            lado_B.append(vm2)

    if len(lado_A) >= 5 and len(lado_B) >= 5:
        p33_A = compute_percentil(33, lado_A)
        p33_B = compute_percentil(33, lado_B)
        if p33_A and p33_A > 0:
            efecto = (p33_A - p33_B) / p33_A
            efectos[nombre] = {
                'efecto': efecto,
                'p33_a': p33_A,
                'p33_b': p33_B,
                'n_a': len(lado_A),
                'n_b': len(lado_B),
            }

print(f"  Efectos calculados: {len(efectos)} barreras")

print("\nEFECTOS POR BARRERA:")
print("  %-40s %8s %8s %6s %6s" % ("Barrera", "Efecto%", "P33_A", "N_A", "N_B"))
for nombre, data in sorted(efectos.items(), key=lambda x: x[1]['efecto']):
    print("  %-40s %+7.1f%% $%6.0f %6d %6d" % (
        nombre[:40], data['efecto'] * 100, data['p33_a'], data['n_a'], data['n_b']))


# --- 3. SIMULACION: NUEVA FORMULA ---
print("\n" + "=" * 140)
print("SIMULACION v9 - NUEVA FORMULA (sin alpha/blend/penalty)")
print("=" * 140)
print("Date:", datetime.now().strftime('%Y-%m-%d %H:%M'))
print()
print("%-18s %10s %10s %10s %8s %7s %7s %10s" % (
    "Property", "Stored", "Engine", "NewFormula", "Delta%", "n_s", "n_c", "Barriers"))
print("-" * 140)

from parsers.mercado_inmobiliario import (
    obtener_mediana_cluster_v2, _precio_ajustado,
)
from parsers.cluster_filters import calcular_percentil

for prop in propiedades:
    nombre = prop['nombre']
    uv = prop.get('_ultima_valuacion', {})
    stored = uv.get('auto_valor_usd', 0)

    try:
        lat = prop.get('lat')
        lon = prop.get('lon')
        dorms = prop.get('dormitorios')
        m2 = prop.get('m2_cubiertos', 0) or prop.get('m2', 0) or 0

        if not lat or not lon or not dorms:
            print("%-18s SKIP: missing lat/lon/dorms" % nombre)
            continue

        # 1. Llamar engine para obtener pool_final (con anio_sujeto para age filter)
        anio_const = prop.get('anio_construccion', 2020)
        vm2_engine, n_pool, meta = obtener_mediana_cluster_v2(
            zona=prop.get('zona', ''),
            dormitorios=dorms, operacion='venta',
            lat_ref=lat, lon_ref=lon,
            fecha_ref='2026-04',
            anio_sujeto=anio_const,
            tipo_inmueble=prop.get('tipo_inmueble') or prop.get('tipo') or 'departamento',
            retro_dias=uv.get('retro_dias', 0),
            flex_dormitorios=uv.get('flex_dormitorios', None),
        )

        engine_value = round(vm2_engine * m2) if vm2_engine and m2 else 0

        pool_final = meta.get('_pool_final', [])
        macrozona_id = meta.get('macrozona_id')
        percentil = meta.get('percentil_usado', 'P33')
        pctl_num = int(''.join(filter(str.isdigit, percentil))) if percentil else 33

        # 2. RE-CLASIFICAR con barreras corrected (mismas reglas que engine)
        zona_ref = prop.get('zona', '')
        misma_zona_count = 0

        precios_same = []
        precios_cross = []
        barreras_detectadas = []
        comps_detalle = []

        for comp in pool_final:
            precio = _precio_ajustado(comp, macrozona_id, dormitorios_sujeto=dorms)
            if not precio or precio <= 0:
                continue

            comp_lat = comp.get('lat')
            comp_lon = comp.get('lon')
            if not comp_lat or not comp_lon:
                precios_same.append(precio)
                comps_detalle.append({'nombre': comp.get('direccion', '?'), 'tipo': 'same', 'precio': precio, 'razon': 'sin_coords'})
                continue

            try:
                comp_lat, comp_lon = float(comp_lat), float(comp_lon)
            except:
                precios_same.append(precio)
                comps_detalle.append({'nombre': comp.get('direccion', '?'), 'tipo': 'same', 'precio': precio, 'razon': 'coords_invalid'})
                continue

            # Misma zona exception (como en engine)
            comp_zona = comp.get('zona', '')
            if zona_ref and comp_zona and zona_ref == comp_zona:
                precios_same.append(precio)
                misma_zona_count += 1
                comps_detalle.append({'nombre': comp.get('direccion', '?'), 'tipo': 'same', 'precio': precio, 'razon': f'misma_zona={zona_ref}'})
                continue

            # Detectar cruce de barrera
            bt, barrier_name = check_barrier_crossing_with_name(
                (lon, lat), (comp_lon, comp_lat), barreras
            )

            if bt == 'hard':
                # Hard barrier: excluir del pool (como en engine)
                comps_detalle.append({'nombre': comp.get('direccion', '?'), 'tipo': 'excluded', 'precio': precio, 'razon': f'hard:{barrier_name}'})
                continue
            elif bt == 'soft':
                # Soft barrier: clasificar como cross
                efecto_data = efectos.get(barrier_name, None)
                if efecto_data:
                    efecto = efecto_data['efecto']
                    precio_aj = precio / (1 - efecto) if efecto != 1.0 else precio
                else:
                    # Sin efecto calculado: mantener precio original (cross pero sin ajuste)
                    efecto = 0.0
                    precio_aj = precio

                precios_cross.append(precio_aj)
                barreras_detectadas.append(barrier_name or f'soft_{bt}')
                comps_detalle.append({
                    'nombre': comp.get('direccion', '?'), 'tipo': 'cross', 'precio': precio,
                    'precio_aj': precio_aj, 'barrera': barrier_name, 'efecto': efecto
                })
            else:
                # No barrier: same-side
                precios_same.append(precio)
                comps_detalle.append({'nombre': comp.get('direccion', '?'), 'tipo': 'same', 'precio': precio, 'razon': 'sin_barrera'})

        # 3. NUEVA FORMULA: P33 de TODO el pool ajustado
        all_prices = sorted(precios_same + precios_cross)
        if all_prices:
            vm2_new = calcular_percentil(all_prices, pctl_num)
        else:
            vm2_new = 0

        new_value = round(vm2_new * m2) if vm2_new and m2 else 0

        # 4. Estadisticas
        p33_same = calcular_percentil(precios_same, pctl_num) if precios_same else None
        p33_cross = calcular_percentil(precios_cross, pctl_num) if precios_cross else None

        unique_barriers = list(set(barreras_detectadas))

        delta_stored = ((new_value - stored) / stored * 100) if stored else 0

        print("%-18s $%9s $%9s $%9s %+7.1f%% %5d %5d" % (
            nombre,
            "${:,}".format(stored),
            "${:,}".format(round(engine_value)),
            "${:,}".format(new_value),
            delta_stored,
            len(precios_same),
            len(precios_cross),
        ))
        if unique_barriers:
            print("  ^ Barreras: %s" % ", ".join(unique_barriers))

        # 5. Detalle de ajustes (solo si hay cross comps)
        if precios_cross:
            print(f"    P33_same=${p33_same:.0f} P33_cross_aj=${p33_cross:.0f}" if p33_same and p33_cross else "")
            for d in comps_detalle:
                if d['tipo'] == 'cross' and d.get('efecto', 0) != 0:
                    pct = d['efecto'] * 100
                    print(f"    -> {d['nombre']}: ${d['precio']:.0f} -> ${d['precio_aj']:.0f} ({pct:+.1f}% por {d['barrera']})")

    except Exception as e:
        import traceback
        print("%-18s ERROR: %s" % (nombre, str(e)[:80]))
        traceback.print_exc()


# --- RESUMEN ---
print()
print("=" * 140)
print("RESUMEN")
print("=" * 140)
print()
print("Stored    = valor en propiedades.json (_ultima_valuacion.auto_valor_usd)")
print("Engine    = valor con logica ACTUAL (alpha/blend/penalty 3%)")
print("NewFormula= valor con NUEVA formula (P33 de pool ajustado por barrera)")
print("Delta%    = cambio NewFormula vs. Stored")
print()
print("NUEVA FORMULA:")
print("  1. Llamar engine para obtener pool_final (comps filtrados)")
print("  2. Re-clasificar con barreras corrected (same/cross/excluded)")
print("  3. Para cross: precio_aj = precio / (1 - efecto_barrera)")
print("  4. vm2 = P33 de TODOS los precios ajustados (same + cross)")
print("  5. Sin alpha, sin blend, sin penalty del 3%")
