"""
Análisis de métodos de valuación usando el engine REAL.
Extrae el pool de comparables del motor actual para cada propiedad,
luego aplica los 5 métodos sobre ese mismo pool.
"""

import sys, os, json, math
from datetime import datetime, timedelta
from collections import defaultdict

# Agregar path del proyecto
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')

# Imports del engine real
from parsers.mercado_inmobiliario import obtener_mediana_cluster_v2, _precio_ajustado, _computar_vm2_core
from parsers.cluster_filters import calcular_percentil, seleccionar_percentil_por_calidad_pool, _calcular_cv

# ── Cargar datos ─────────────────────────────────────────────────────────────
print("Cargando cache_scraping.json...")
with open(r'c:\Users\Gustavo\ingresos_familiares_st\cache_scraping.json', 'r', encoding='utf-8') as f:
    CACHE = json.load(f)
print(f"Cache cargado: {len(CACHE['propiedades'])} propiedades")

with open(r'c:\Users\Gustavo\ingresos_familiares_st\propiedades.json', 'r', encoding='utf-8') as f:
    PROPS_JSON = json.load(f)

# ── Definición de propiedades a analizar ─────────────────────────────────────
SUJETOS = [
    {
        'nombre': 'Mabel',
        'zona': 'Martin',
        'dormitorios': 1,
        'lat': -32.9541101, 'lon': -60.6316406,
        'anio': 1998,
        'm2eq': 42.3035,
        'retro_dias': 60,
        'flex_dormitorios': [1,2,3,4,5],
        'manual_usd': 72974,
        'stored_usd': 50713,
    },
    {
        'nombre': 'Ayacucho',
        'zona': 'República de la Sexta',
        'dormitorios': 1,
        'lat': -32.9611391, 'lon': -60.6264443,
        'anio': 2002,
        'm2eq': 28.9265,
        'retro_dias': 60,
        'flex_dormitorios': [4,5,6],
        'manual_usd': 39514,
        'stored_usd': 30843,
    },
    {
        'nombre': 'Vera Mujica',
        'zona': 'Facultades',
        'dormitorios': 1,
        'lat': -32.9427375, 'lon': -60.6673362,
        'anio': 2009,
        'm2eq': 40.62,
        'retro_dias': 60,
        'flex_dormitorios': [1,2,3,4,5],
        'manual_usd': 54974,
        'stored_usd': 61185,
    },
    {
        'nombre': 'P1200',
        'zona': 'Centro',
        'dormitorios': 2,
        'lat': -32.9568191, 'lon': -60.6429513,
        'anio': 1977,
        'm2eq': 88.85,
        'retro_dias': 60,
        'flex_dormitorios': [1,2,3,4,5],
        'manual_usd': 118563,
        'stored_usd': 111296,
    },
    {
        'nombre': 'Entre Rios',
        'zona': 'Centro',
        'dormitorios': 1,
        'lat': -32.9412249, 'lon': -60.6397994,
        'anio': 2016,
        'm2eq': 34.0,
        'retro_dias': 0,
        'flex_dormitorios': None,
        'manual_usd': 54605,
        'stored_usd': 54203,
    },
    {
        'nombre': 'Brown 2750',
        'zona': 'Pichincha',
        'dormitorios': 2,
        'lat': -32.9331753, 'lon': -60.6575732,
        'anio': 2025,
        'm2eq': 98.7,
        'retro_dias': 0,
        'flex_dormitorios': None,
        'manual_usd': 195130,
        'stored_usd': 241344,
    },
    {
        'nombre': 'Francia 250b',
        'zona': 'Puerto Norte',
        'dormitorios': 3,
        'lat': -32.9304159, 'lon': -60.6620818,
        'anio': 2025,
        'm2eq': 160.0,
        'retro_dias': 60,
        'flex_dormitorios': [1,2,3,4,5],
        'manual_usd': 543962,
        'stored_usd': 596224,
        'activos_usd': 56000,
    },
    {
        'nombre': 'Mitre1473',
        'zona': 'Centro',
        'dormitorios': 3,
        'lat': -32.9544322, 'lon': -60.6415903,
        'anio': 1971,
        'm2eq': 222.2,
        'retro_dias': 60,
        'flex_dormitorios': [1,2,3,4,5],
        'manual_usd': 522952,
        'stored_usd': 217838,
    },
    {
        'nombre': 'Cochabamba 45',
        'zona': 'República de la Sexta',
        'dormitorios': 4,
        'lat': -32.9611391, 'lon': -60.6264443,
        'anio': 1966,
        'm2eq': 98.0,
        'retro_dias': 60,
        'flex_dormitorios': [1,2,3,4,5],
        'manual_usd': 115052,
        'stored_usd': 81803,
    },
]

# ── Funciones de los métodos alternativos ─────────────────────────────────────

def calcular_distancia_m(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    return R * 2 * math.asin(math.sqrt(a))


def idw_percentil(comparables, percentil, lat_ref, lon_ref, power=2.0, macrozona_id=None, ancla_id=None, dormitorios_sujeto=None):
    weighted = []
    for c in comparables:
        lat = c.get('lat')
        lon = c.get('lon')
        if lat is None or lon is None:
            continue
        dist = calcular_distancia_m(lat_ref, lon_ref, float(lat), float(lon))
        dist = max(dist, 1.0)
        peso = 1.0 / (dist ** power)
        precio_norm = _precio_ajustado(c, macrozona_id=macrozona_id, ancla_id=ancla_id, dormitorios_sujeto=dormitorios_sujeto)
        weighted.append((precio_norm, peso))
    
    if not weighted:
        return None
    
    weighted.sort(key=lambda x: x[0])
    total_peso = sum(w for _, w in weighted)
    target = (percentil / 100.0) * total_peso
    acum = 0.0
    for precio, peso in weighted:
        acum += peso
        if acum >= target:
            return precio
    return weighted[-1][0]


def dyna_blend(comparables, percentil, macrozona_id=None, ancla_id=None, dormitorios_sujeto=None, apply_penalty=True):
    same = [c for c in comparables if not c.get('_cross_soft', False)]
    cross = [c for c in comparables if c.get('_cross_soft', False)]
    
    precios_same = sorted([_precio_ajustado(c, macrozona_id=macrozona_id, ancla_id=ancla_id, dormitorios_sujeto=dormitorios_sujeto) for c in same])
    precios_cross = sorted([_precio_ajustado(c, macrozona_id=macrozona_id, ancla_id=ancla_id, dormitorios_sujeto=dormitorios_sujeto) for c in cross])
    
    pct_same = calcular_percentil(precios_same, percentil) if precios_same else None
    pct_cross = calcular_percentil(precios_cross, percentil) if precios_cross else None
    
    if pct_same is None and pct_cross is None:
        return None, None, None
    if pct_same is None:
        return pct_cross, 0.0, 0.0
    if pct_cross is None:
        return pct_same, 0.0, 0.0
    
    gap = (pct_same - pct_cross) / pct_same if pct_same > 0 else 0.0
    
    n_same = len(precios_same)
    if n_same >= 15: alpha_base = 0.70
    elif n_same >= 8: alpha_base = 0.60
    elif n_same >= 5: alpha_base = 0.55
    else: alpha_base = 0.50
    
    if gap > 0.05:
        dyn_alpha = min(alpha_base + gap * 0.5, 0.85)
    elif gap < -0.05:
        dyn_alpha = max(alpha_base + gap * 0.5, 0.40)
    else:
        dyn_alpha = alpha_base
    
    dyn_blend_val = dyn_alpha * pct_same + (1 - dyn_alpha) * pct_cross
    
    if apply_penalty and gap > 0:
        n_cross = len(precios_cross)
        n_total = len(precios_cross) + len(precios_same)
        dyn_penalty = min(gap * 0.5, 0.15) * (n_cross / n_total) if n_total > 0 else 0
        dyn_blend_val *= (1 - dyn_penalty)
    
    return round(dyn_blend_val, 2), gap, dyn_alpha


# ── Loop principal ─────────────────────────────────────────────────────────────

FECHA_REF = datetime.now().strftime('%Y-%m-%d')

print(f"\n{'='*80}")
print(f"ANÁLISIS DE MÉTODOS DE VALUACIÓN — {FECHA_REF}")
print(f"{'='*80}\n")

resultados = []

for sujeto in SUJETOS:
    nombre = sujeto['nombre']
    print(f"\n{'─'*60}")
    print(f"Procesando: {nombre}")
    
    vm2_engine, n_comps, meta = obtener_mediana_cluster_v2(
        zona=sujeto['zona'],
        dormitorios=sujeto['dormitorios'],
        operacion='venta',
        lat_ref=sujeto['lat'],
        lon_ref=sujeto['lon'],
        fecha_ref=FECHA_REF,
        anio_sujeto=sujeto.get('anio'),
        tipo_inmueble='departamento',
        cache_scraping=CACHE,
        retro_dias=sujeto['retro_dias'],
        flex_dormitorios=sujeto.get('flex_dormitorios'),
        m2_equiv=sujeto['m2eq'],
    )
    
    pool = meta.get('_pool_final', [])
    n_pool = len(pool)
    radio_usado = meta.get('radio_usado', 'N/A')
    percentil_str = meta.get('percentil_usado', 'P33')
    percentil_num = int(str(percentil_str).replace('P', '')) if percentil_str else 33
    
    n_same = sum(1 for c in pool if not c.get('_cross_soft', False))
    n_cross = sum(1 for c in pool if c.get('_cross_soft', False))
    n_mismos_dorm = sum(1 for c in pool if c.get('dormitorios') == sujeto['dormitorios'])
    
    macrozona_id = meta.get('macrozona_id')
    ancla_id = meta.get('ancla_id')
    
    print(f"  Pool: {n_pool} comps | Radio: {radio_usado}m | {percentil_str} | Same:{n_same} Cross:{n_cross}")
    print(f"  m2_base engine: ${vm2_engine:,.2f}")
    
    if n_pool < 2:
        print(f"  SKIP: pool insuficiente")
        continue
    
    m2eq = sujeto['m2eq']
    activos = sujeto.get('activos_usd', 0)
    
    static_vm2 = vm2_engine
    static_usd = round(static_vm2 * m2eq + activos, 0)
    
    dyna_vm2, gap, dyn_alpha = dyna_blend(pool, percentil_num, macrozona_id=macrozona_id, ancla_id=ancla_id, dormitorios_sujeto=sujeto['dormitorios'], apply_penalty=True)
    dyna_usd = round((dyna_vm2 or 0) * m2eq + activos, 0) if dyna_vm2 else None
    
    dyna_nop_vm2, _, _ = dyna_blend(pool, percentil_num, macrozona_id=macrozona_id, ancla_id=ancla_id, dormitorios_sujeto=sujeto['dormitorios'], apply_penalty=False)
    dyna_nop_usd = round((dyna_nop_vm2 or 0) * m2eq + activos, 0) if dyna_nop_vm2 else None
    
    idw2_vm2 = idw_percentil(pool, percentil_num, sujeto['lat'], sujeto['lon'], power=2.0, macrozona_id=macrozona_id, ancla_id=ancla_id, dormitorios_sujeto=sujeto['dormitorios'])
    idw2_usd = round((idw2_vm2 or 0) * m2eq + activos, 0) if idw2_vm2 else None
    
    idw15_vm2 = idw_percentil(pool, percentil_num, sujeto['lat'], sujeto['lon'], power=1.5, macrozona_id=macrozona_id, ancla_id=ancla_id, dormitorios_sujeto=sujeto['dormitorios'])
    idw15_usd = round((idw15_vm2 or 0) * m2eq + activos, 0) if idw15_vm2 else None
    
    idw1_vm2 = idw_percentil(pool, percentil_num, sujeto['lat'], sujeto['lon'], power=1.0, macrozona_id=macrozona_id, ancla_id=ancla_id, dormitorios_sujeto=sujeto['dormitorios'])
    idw1_usd = round((idw1_vm2 or 0) * m2eq + activos, 0) if idw1_vm2 else None
    
    # Hybrid: same con percentil estatico, cross con IDW
    same_pool = [c for c in pool if not c.get('_cross_soft', False)]
    cross_pool = [c for c in pool if c.get('_cross_soft', False)]
    hybrid_vm2 = None
    if same_pool:
        precios_same_h = sorted([_precio_ajustado(c, macrozona_id=macrozona_id, ancla_id=ancla_id, dormitorios_sujeto=sujeto['dormitorios']) for c in same_pool])
        pct_same_h = calcular_percentil(precios_same_h, percentil_num)
        if cross_pool:
            idw_cross = idw_percentil(cross_pool, percentil_num, sujeto['lat'], sujeto['lon'], power=2.0, macrozona_id=macrozona_id, ancla_id=ancla_id, dormitorios_sujeto=sujeto['dormitorios'])
            n_same_h = len(same_pool)
            if n_same_h >= 15: alpha_h = 0.70
            elif n_same_h >= 8: alpha_h = 0.60
            elif n_same_h >= 5: alpha_h = 0.55
            else: alpha_h = 0.50
            hybrid_vm2 = alpha_h * pct_same_h + (1 - alpha_h) * (idw_cross or pct_same_h)
            n_cross_h = len(cross_pool)
            barrier_pct = (n_cross_h / (n_cross_h + n_same_h)) * 0.03
            hybrid_vm2 *= (1 - barrier_pct)
        else:
            hybrid_vm2 = pct_same_h
    hybrid_usd = round((hybrid_vm2 or 0) * m2eq + activos, 0) if hybrid_vm2 else None
    
    precios_norm_all = sorted([_precio_ajustado(c, macrozona_id=macrozona_id, ancla_id=ancla_id, dormitorios_sujeto=sujeto['dormitorios']) for c in pool])
    cv = _calcular_cv(precios_norm_all) if len(precios_norm_all) >= 3 else None
    
    dists = [calcular_distancia_m(sujeto['lat'], sujeto['lon'], float(c['lat']), float(c['lon'])) for c in pool if c.get('lat') and c.get('lon')]
    
    res = {
        'nombre': nombre,
        'n_pool': n_pool,
        'n_same': n_same,
        'n_cross': n_cross,
        'n_mismos_dorm': n_mismos_dorm,
        'radio_m': radio_usado,
        'percentil': percentil_str,
        'cv': cv,
        'gap': gap,
        'dyn_alpha': dyn_alpha,
        'dist_min_m': round(min(dists), 0) if dists else None,
        'dist_median_m': round(sorted(dists)[len(dists)//2], 0) if dists else None,
        'm2eq': m2eq,
        'activos_usd': activos,
        'vm2': {'static': static_vm2, 'dyna_p': dyna_vm2, 'dyna': dyna_nop_vm2, 'idw2': idw2_vm2, 'idw15': idw15_vm2, 'idw1': idw1_vm2, 'hybrid': hybrid_vm2},
        'usd': {'static': static_usd, 'dyna_p': dyna_usd, 'dyna': dyna_nop_usd, 'idw2': idw2_usd, 'idw15': idw15_usd, 'idw1': idw1_usd, 'hybrid': hybrid_usd, 'stored': sujeto['stored_usd'], 'manual': sujeto['manual_usd']},
    }
    resultados.append(res)
    
    stored_usd = sujeto['stored_usd']
    manual_usd = sujeto['manual_usd']
    print(f"\n  {'Método':<12} {'$/m²':>9} {'USD':>11} {'vs Stored':>10} {'vs Manual':>10}")
    for m_name, vm2_v, usd_v in [('STATIC', static_vm2, static_usd), ('DynA+P', dyna_vm2, dyna_usd), ('DynA', dyna_nop_vm2, dyna_nop_usd), ('IDW-p2', idw2_vm2, idw2_usd), ('IDW-p1.5', idw15_vm2, idw15_usd), ('IDW-p1', idw1_vm2, idw1_usd), ('HYBRID', hybrid_vm2, hybrid_usd)]:
        if vm2_v is None: continue
        ds = f"{(usd_v - stored_usd)/stored_usd*100:+.1f}%" if stored_usd else ""
        dm = f"{(usd_v - manual_usd)/manual_usd*100:+.1f}%" if manual_usd else ""
        print(f"  {m_name:<12} ${vm2_v:>8,.1f} ${usd_v:>10,.0f} {ds:>10} {dm:>10}")
    print(f"  {'STORED':<12} {'':>9} ${stored_usd:>10,.0f}")
    print(f"  {'MANUAL':<12} {'':>9} ${manual_usd:>10,.0f}")

# ── Tabla resumen ─────────────────────────────────────────────────────────────
print(f"\n\n{'='*80}")
print("TABLA RESUMEN")
print(f"{'='*80}")
metodos = ['static', 'dyna_p', 'dyna', 'idw2', 'idw15', 'idw1', 'hybrid', 'stored', 'manual']
totales = defaultdict(float)
for r in resultados:
    for m in metodos:
        v = r['usd'].get(m)
        if v: totales[m] += v

print(f"\n{'Propiedad':<15} {'STATIC':>10} {'DynA+P':>10} {'IDW-p2':>10} {'IDW-p1.5':>10} {'HYBRID':>10} {'STORED':>10} {'MANUAL':>10}")
print("─"*80)
for r in resultados:
    u = r['usd']
    f = lambda v: f"${v:,.0f}" if v else "N/A"
    print(f"{r['nombre']:<15} {f(u['static']):>10} {f(u['dyna_p']):>10} {f(u['idw2']):>10} {f(u['idw15']):>10} {f(u['hybrid']):>10} {f(u['stored']):>10} {f(u['manual']):>10}")
print("─"*80)
f2 = lambda m: f"${totales[m]:,.0f}" if totales[m] else "N/A"
print(f"{'TOTAL':<15} {f2('static'):>10} {f2('dyna_p'):>10} {f2('idw2'):>10} {f2('idw15'):>10} {f2('hybrid'):>10} {f2('stored'):>10} {f2('manual'):>10}")

# ── RMSE/MAE ─────────────────────────────────────────────────────────────────
print(f"\n{'='*60}")
print("MÉTRICAS DE ERROR (vs MANUAL y vs STORED)")
print(f"{'─'*60}")
print(f"{'Método':<14} {'MAE_m':>8} {'RMSE_m':>8} {'Bias_m':>8} {'MAE_s':>8} {'RMSE_s':>8} {'Bias_s':>8}")
print(f"{'─'*60}")
for m in ['static', 'dyna_p', 'dyna', 'idw2', 'idw15', 'idw1', 'hybrid']:
    em, es = [], []
    for r in resultados:
        v = r['usd'].get(m)
        manual = r['usd']['manual']
        stored = r['usd']['stored']
        if v and manual: em.append((v - manual) / manual)
        if v and stored: es.append((v - stored) / stored)
    if em:
        mae_m = sum(abs(e) for e in em)/len(em)*100
        rmse_m = math.sqrt(sum(e**2 for e in em)/len(em))*100
        bias_m = sum(em)/len(em)*100
        mae_s = sum(abs(e) for e in es)/len(es)*100 if es else 0
        rmse_s = math.sqrt(sum(e**2 for e in es)/len(es))*100 if es else 0
        bias_s = sum(es)/len(es)*100 if es else 0
        nm = {'static':'STATIC','dyna_p':'DynA+P','dyna':'DynA','idw2':'IDW-p2','idw15':'IDW-p1.5','idw1':'IDW-p1','hybrid':'HYBRID'}
        print(f"{nm[m]:<14} {mae_m:>7.1f}% {rmse_m:>7.1f}% {bias_m:>+7.1f}% {mae_s:>7.1f}% {rmse_s:>7.1f}% {bias_s:>+7.1f}%")

# ── Guardar JSON ──────────────────────────────────────────────────────────────
output_path = r'c:\Users\Gustavo\ingresos_familiares_st\scratch\resultados_metodos.json'
os.makedirs(os.path.dirname(output_path), exist_ok=True)
with open(output_path, 'w', encoding='utf-8') as f:
    json.dump(resultados, f, ensure_ascii=False, indent=2, default=str)
print(f"\nResultados guardados: {output_path}")
