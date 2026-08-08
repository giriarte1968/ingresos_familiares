"""
Genera factores de Size Adjustment Categórico (chico/mediano/grande).

Categorías por dormitorio:
  1: chico <45, mediano 45-75, grande >=75
  2: chico <75, mediano 75-130, grande >=130
  3: chico <115, mediano 115-210, grande >=210
  4: chico <180, mediano 180-320, grande >=320

Metodología:
  1. Para cada macrozona/dorm: clasificar props en chico/mediano/grande
  2. Calcular mediana $/m2 por categoría
  3. Normalizar: mediano = 1.0
  4. Output: data/sa_categoricas.json

NO toca archivos de producción.
"""
import json
import os
import sys
from collections import defaultdict
from datetime import datetime

os.chdir(r'C:\Users\Gustavo\ingresos_familiares_st')
sys.path.insert(0, '.')

from parsers.mercado_inmobiliario import calcular_m2_equivalentes, normalizar_zona
from parsers.zonas_manager import resolver_macrozona

# --- Categorías por dormitorio ---
CATEGORIAS = {
    1: [(0, 45, 'chico'), (45, 75, 'mediano'), (75, 9999, 'grande')],
    2: [(0, 75, 'chico'), (75, 130, 'mediano'), (130, 9999, 'grande')],
    3: [(0, 115, 'chico'), (115, 210, 'mediano'), (210, 9999, 'grande')],
    4: [(0, 180, 'chico'), (180, 320, 'mediano'), (320, 9999, 'grande')],
}

def clasificar(m2, dorms):
    """Retorna 'chico', 'mediano' o 'grande' según m2 y dormitorios."""
    cats = CATEGORIAS.get(dorms, CATEGORIAS.get(4))
    for lo, hi, nombre in cats:
        if lo <= m2 < hi:
            return nombre
    return 'mediano'


def calcular_ct(meses):
    """Factor de corrección temporal simple."""
    tasa_mensual = 0.002
    return max(0.85, 1.0 - tasa_mensual * meses)


def main():
    print("=" * 80)
    print("GENERAR CURVAS CATEGÓRICAS — chico/mediano/grande")
    print("=" * 80)
    print("Date:", datetime.now().strftime('%Y-%m-%d %H:%M'))
    print()

    # Load data
    with open('cache_scraping.json', 'r', encoding='utf-8') as f:
        cache = json.load(f)
    props = cache.get('propiedades', [])
    venta = [p for p in props if p.get('operacion') == 'venta' and p.get('moneda', 'USD') == 'USD']
    print("Props venta USD:", len(venta))

    # Load new curves for reference
    with open('data/zonas_depreciacion_new.json', 'r', encoding='utf-8') as f:
        old_new = json.load(f).get('curves', {})

    # Group by macrozona/dorm/categoria
    data = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    now = datetime.now()

    for p in venta:
        lat = p.get('lat')
        lon = p.get('lon')
        dorms = p.get('dormitorios')
        m2 = p.get('m2') or p.get('m2_cubiertos', 0)
        valor_m2 = p.get('valor_m2', 0)
        fecha_str = p.get('fecha', '')

        if not lat or not lon or not dorms or not m2 or not valor_m2:
            continue
        if dorms not in CATEGORIAS:
            continue

        try:
            lat, lon = float(lat), float(lon)
        except:
            continue

        # Resolve macrozona
        zona = normalizar_zona(p.get('zona', '') or '')
        pseudo = {'zona': zona, 'lat': lat, 'lon': lon}
        mz_info = resolver_macrozona(pseudo)
        mz_id = mz_info.get('macrozona_id')
        if not mz_id:
            continue

        # CT adjustment
        try:
            fecha = datetime.strptime(fecha_str[:10], '%Y-%m-%d')
            meses = (now - fecha).days / 30.44
        except:
            meses = 0
        ct = calcular_ct(meses)

        # CT-adjusted $/m2
        vm2_ct = valor_m2 * ct

        cat = clasificar(m2, dorms)
        data[mz_id][dorms][cat].append(vm2_ct)

    # Compute medians and factors
    result = {}
    for mz_id in sorted(data.keys()):
        result[mz_id] = {}
        for dorms in sorted(data[mz_id].keys()):
            cats = data[mz_id][dorms]
            medians = {}
            for cat_name in ['chico', 'mediano', 'grande']:
                values = cats.get(cat_name, [])
                if values:
                    values_sorted = sorted(values)
                    n = len(values_sorted)
                    med = values_sorted[n // 2]
                    medians[cat_name] = med
                else:
                    medians[cat_name] = None

            # Normalize to mediano = 1.0
            ref = medians.get('mediano')
            factors = {}
            for cat_name in ['chico', 'mediano', 'grande']:
                m = medians.get(cat_name)
                if m and ref and ref > 0:
                    factors[cat_name] = round(m / ref, 4)
                elif cat_name == 'mediano':
                    factors[cat_name] = 1.0
                else:
                    factors[cat_name] = 1.0  # fallback

            # Stats
            stats = {}
            for cat_name in ['chico', 'mediano', 'grande']:
                values = cats.get(cat_name, [])
                stats[cat_name] = len(values)

            result[mz_id][str(dorms)] = {
                'factors': factors,
                'medians': {k: round(v, 2) if v else None for k, v in medians.items()},
                'counts': stats,
            }

    # Print summary
    print()
    print("RESULTADOS:")
    print()
    for mz_id in sorted(result.keys()):
        print("=== %s ===" % mz_id)
        for dorms in sorted(result[mz_id].keys()):
            r = result[mz_id][dorms]
            f = r['factors']
            m = r['medians']
            c = r['counts']
            print("  dorm=%s: chico=%.4f (n=%d, $/m2=%.0f) | mediano=%.4f (n=%d, $/m2=%.0f) | grande=%.4f (n=%d, $/m2=%.0f)" % (
                dorms,
                f['chico'], c['chico'], m['chico'] or 0,
                f['mediano'], c['mediano'], m['mediano'] or 0,
                f['grande'], c['grande'], m['grande'] or 0,
            ))
        print()

    # Save
    output = {
        'generated': datetime.now().isoformat(),
        'method': 'categorical',
        'categories': {str(k): [(lo, hi, n) for lo, hi, n in v] for k, v in CATEGORIAS.items()},
        'data': result,
    }
    with open('data/sa_categoricas.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print("Saved: data/sa_categoricas.json")


if __name__ == '__main__':
    main()
