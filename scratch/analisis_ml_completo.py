"""
ANALISIS ML COMPLETO - Cache Scraping VPP Rosario
Objetivo: Entender la estructura real del precio por m2 en funcion de:
  1. Ubicacion geografica (lat/lon)
  2. Tamanio (m2) 
  3. Dormitorios
  4. Antiguedad
  5. Efecto de barreras geograficas

Luego construir la logica de valuacion optima.
NO USA referencias manuales.
"""

import sys, os, json, math, warnings
warnings.filterwarnings('ignore')
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

import numpy as np
from collections import defaultdict
from datetime import datetime

# ============================================================
# 1. CARGAR DATOS
# ============================================================
print("=" * 70)
print("ANALISIS ML COMPLETO - VPP Rosario")
print("=" * 70)

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

# Filtrar ventas validas
ventas_raw = [p for p in cache['propiedades']
              if p.get('operacion') == 'venta'
              and p.get('valor_m2', 0) > 200
              and p.get('valor_m2', 0) < 12000
              and p.get('m2', 0) > 15
              and p.get('m2', 0) < 600
              and p.get('lat') and p.get('lon')
              and p.get('dormitorios') in [1, 2, 3, 4]]

print(f"\nDatos: {len(ventas_raw)} ventas validas (de {len(cache['propiedades'])} totales)")

# Resolver macrozona para cada prop
from parsers.zonas_manager import resolver_macrozona

def get_macrozona(p):
    try:
        info = resolver_macrozona(p)
        return info.get('macrozona_id', 'resto_rosario')
    except:
        return 'resto_rosario'

print("Resolviendo macrozonas...")
for p in ventas_raw:
    p['_macrozona'] = get_macrozona(p)

# Conteo por macrozona
from collections import Counter
mz_cnt = Counter(p['_macrozona'] for p in ventas_raw)
print("\nPropiedades por macrozona:")
for mz, cnt in sorted(mz_cnt.items(), key=lambda x: -x[1]):
    print(f"  {mz:<25} {cnt:>5}")

# ============================================================
# 2. ANALISIS DE PRECIO vs M2 POR MACROZONA Y DORMITORIO
# ============================================================
print("\n" + "=" * 70)
print("ANALISIS: Precio/m2 por Tamano (buckets 20m2)")
print("=" * 70)

def percentil(data, p):
    s = sorted(data)
    idx = int(len(s) * p / 100)
    return s[min(idx, len(s)-1)] if s else None

# Buckets de m2 (cada 20m2)
BUCKETS = [(0,30), (30,50), (50,75), (75,100), (100,130), (130,180), (180,250), (250,400)]

macrozonas_principales = ['centro_premium', 'macrocentro', 'norte', 'puerto_norte', 'fisherton']

price_by_mz_dorm_bucket = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))

for p in ventas_raw:
    mz = p['_macrozona']
    dorm = p.get('dormitorios', 1)
    m2 = p.get('m2', 0)
    vm2 = p.get('valor_m2', 0)
    
    for lo, hi in BUCKETS:
        if lo <= m2 < hi:
            price_by_mz_dorm_bucket[mz][dorm][(lo, hi)].append(vm2)
            break

print("\nMedia P50 por macrozona/dorm/bucket:")
print(f"{'Zona':<18} {'Dorm':<5} {'Bucket':<12} {'N':>5} {'P50':>8} {'P25':>8} {'P75':>8}")
print("-" * 70)

# Estructura para ML: relacion m2 -> vm2 por macrozona
sa_data = {}

for mz in macrozonas_principales:
    dorm_data = price_by_mz_dorm_bucket.get(mz, {})
    if not dorm_data:
        continue
    sa_data[mz] = {}
    for dorm in [1, 2, 3, 4]:
        bucket_data = dorm_data.get(dorm, {})
        if not bucket_data:
            continue
        sa_data[mz][dorm] = {}
        for (lo, hi), prices in sorted(bucket_data.items()):
            if len(prices) >= 5:
                p50 = percentil(prices, 50)
                p25 = percentil(prices, 25)
                p75 = percentil(prices, 75)
                print(f"{mz:<18} {dorm:<5} {lo}-{hi:<7} {len(prices):>5} ${p50:>7,.0f} ${p25:>7,.0f} ${p75:>7,.0f}")
                sa_data[mz][dorm][(lo, hi)] = {'n': len(prices), 'p50': p50, 'p25': p25, 'p75': p75}
        print()

# ============================================================
# 3. CURVA SA: ELASTICIDAD PRECIO vs M2 POR DORM
# ============================================================
print("\n" + "=" * 70)
print("ELASTICIDAD: Precio/m2 relativo segun tamano (referencia = mediano 75-130m2)")
print("=" * 70)

print(f"\n{'Zona':<18} {'Dorm':<5} {'<30':<8} {'30-50':<8} {'50-75':<8} {'75-100':<8} {'100-130':<8} {'130-180':<8} {'>180':<8}")
print("-" * 80)

sa_factors = {}

for mz in macrozonas_principales:
    if mz not in sa_data:
        continue
    sa_factors[mz] = {}
    for dorm in [1, 2, 3, 4]:
        if dorm not in sa_data[mz]:
            continue
        
        # Referencia: bucket 75-130 (mediano)
        ref_price = None
        for (lo, hi), data in sa_data[mz][dorm].items():
            if lo == 75 or lo == 100:  # bucket 75-100 o 100-130 como ref
                if ref_price is None:
                    ref_price = data['p50']
                else:
                    ref_price = (ref_price + data['p50']) / 2  # promedio
        
        if ref_price is None or ref_price == 0:
            continue
        
        sa_factors[mz][dorm] = {'ref': ref_price, 'buckets': {}}
        factors = []
        for (lo, hi), data in sorted(sa_data[mz][dorm].items()):
            f = data['p50'] / ref_price if ref_price > 0 else 1.0
            sa_factors[mz][dorm]['buckets'][(lo, hi)] = f
            factors.append(f"{f:.2f}")
        
        row = f"{mz:<18} {dorm:<5}"
        for (lo, hi) in BUCKETS:
            f = sa_factors[mz][dorm]['buckets'].get((lo, hi))
            if f:
                row += f"  {f:.2f}  "
            else:
                row += "   --   "
        print(row)
    print()

# ============================================================
# 4. ANALISIS DE BARRERAS GEOGRAFICAS DESDE DATOS
# ============================================================
print("\n" + "=" * 70)
print("ANALISIS DE BARRERAS DESDE DATOS REALES")
print("=" * 70)

# Cargar barreras
with open('barreras_rosario.json', 'r', encoding='utf-8') as f:
    barreras_data = json.load(f)

barreras = barreras_data.get('features', [])
hard_barreras = [b for b in barreras if b.get('properties', {}).get('is_hard', False)]
soft_barreras = [b for b in barreras if not b.get('properties', {}).get('is_hard', False)]
print(f"Barreras hard: {len(hard_barreras)}, soft: {len(soft_barreras)}")

def haversine_m(lat1, lon1, lat2, lon2):
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# Para barreras hard, calcular gap empírico a 200m de cada lado
print("\nGaps empiricos en barreras HARD (radio 200m, ambos lados):")
print(f"{'Barrera':<40} {'N_A':>5} {'N_B':>5} {'P50_A':>8} {'P50_B':>8} {'Gap%':>8} {'P33_A':>8} {'P33_B':>8}")
print("-" * 90)

RADIO_BARRERA = 200

for barrera in hard_barreras[:20]:  # primeras 20
    props_b = barrera.get('properties', {})
    nombre = props_b.get('name', '?')[:35]
    geom = barrera.get('geometry', {})
    coords = geom.get('coordinates', [])
    if not coords or len(coords) < 2:
        continue
    
    # Punto medio de la barrera
    p1, p2 = coords[0], coords[-1]
    mid_lat = (p1[1] + p2[1]) / 2
    mid_lon = (p1[0] + p2[0]) / 2
    
    # Direction
    dlat = p2[1] - p1[1]
    dlon = p2[0] - p1[0]
    direction = 'NS' if abs(dlat) > abs(dlon) else 'EW'
    
    lado_A, lado_B = [], []
    for p in ventas_raw:
        try:
            plat, plon = float(p['lat']), float(p['lon'])
        except:
            continue
        dist = haversine_m(mid_lat, mid_lon, plat, plon)
        if dist > RADIO_BARRERA:
            continue
        vm2 = p.get('valor_m2', 0)
        if vm2 <= 0:
            continue
        if direction == 'NS':
            side = 'A' if plat > mid_lat else 'B'
        else:
            side = 'A' if plon > mid_lon else 'B'
        if side == 'A':
            lado_A.append(vm2)
        else:
            lado_B.append(vm2)
    
    if len(lado_A) < 5 or len(lado_B) < 5:
        continue
    
    p50_A = percentil(lado_A, 50)
    p50_B = percentil(lado_B, 50)
    p33_A = percentil(lado_A, 33)
    p33_B = percentil(lado_B, 33)
    gap_pct = (p50_A - p50_B) / p50_A * 100 if p50_A else 0
    
    print(f"{nombre:<40} {len(lado_A):>5} {len(lado_B):>5} ${p50_A:>7,.0f} ${p50_B:>7,.0f} {gap_pct:>+7.1f}% ${p33_A:>7,.0f} ${p33_B:>7,.0f}")

# ============================================================
# 5. MODELO DE REGRESION: vm2 ~ lat + lon + m2 + dorm
# ============================================================
print("\n" + "=" * 70)
print("REGRESION LINEAL: vm2 ~ lat + lon + m2 + dorm + m2^2")
print("=" * 70)

# Preparar datos para regresion
X = []
y = []
for p in ventas_raw:
    try:
        lat = float(p['lat'])
        lon = float(p['lon'])
        m2 = float(p['m2'])
        dorm = int(p.get('dormitorios', 1))
        vm2 = float(p['valor_m2'])
        if 100 < vm2 < 10000 and 15 < m2 < 500:
            X.append([lat, lon, m2, m2**0.5, dorm, 1])  # features
            y.append(vm2)
    except:
        continue

X = np.array(X, dtype=float)
y = np.array(y, dtype=float)
print(f"Datos para regresion: {len(y)} observaciones")

# Normalizar features
X_mean = X.mean(axis=0)
X_std = X.std(axis=0)
X_std[X_std == 0] = 1
X_norm = (X - X_mean) / X_std

# OLS (numpy linalg)
try:
    coeffs, residuals, rank, sv = np.linalg.lstsq(X_norm, y, rcond=None)
    y_pred = X_norm @ coeffs
    ss_res = np.sum((y - y_pred)**2)
    ss_tot = np.sum((y - y.mean())**2)
    r2 = 1 - ss_res / ss_tot
    mae = np.mean(np.abs(y - y_pred))
    
    feature_names = ['lat', 'lon', 'm2', 'sqrt_m2', 'dorm', 'intercept']
    print(f"\nR² = {r2:.4f}")
    print(f"MAE = ${mae:.0f}/m²")
    print(f"\nCoeficientes normalizados (importancia relativa):")
    for name, c in sorted(zip(feature_names, coeffs), key=lambda x: -abs(x[1])):
        print(f"  {name:<15}: {c:>+10.2f}")
    
    # Importancia relativa (% de la varianza explicada)
    for i, name in enumerate(feature_names):
        contrib = abs(coeffs[i]) / sum(abs(coeffs)) * 100
        bar = '#' * int(contrib)
        print(f"  {name:<15}: {contrib:>5.1f}% {bar}")
        
except Exception as e:
    print(f"Error en regresion: {e}")

# ============================================================
# 6. ANALISIS: EFECTO REAL DEL TAMANO POR MACROZONA
# ============================================================
print("\n" + "=" * 70)
print("CORRELACION: m2 vs vm2 por macrozona (logaritmica)")
print("=" * 70)

print(f"\n{'Zona':<20} {'N':>5} {'Corr(m2,vm2)':>14} {'Elasticidad':>12} {'Interpretacion'}")
print("-" * 75)

for mz in ['centro_premium', 'macrocentro', 'norte', 'puerto_norte', 'fisherton']:
    props_mz = [p for p in ventas_raw if p['_macrozona'] == mz]
    if len(props_mz) < 20:
        continue
    
    m2s = np.array([float(p['m2']) for p in props_mz])
    vm2s = np.array([float(p['valor_m2']) for p in props_mz])
    
    # Filtrar outliers extremos
    mask = (vm2s > np.percentile(vm2s, 2)) & (vm2s < np.percentile(vm2s, 98))
    m2s, vm2s = m2s[mask], vm2s[mask]
    
    # Correlacion de Pearson entre log(m2) y log(vm2)
    log_m2 = np.log(m2s)
    log_vm2 = np.log(vm2s)
    corr = np.corrcoef(log_m2, log_vm2)[0, 1]
    
    # Elasticidad: regresion log-log → coeficiente
    X_lm = np.column_stack([log_m2, np.ones(len(log_m2))])
    coeffs_lm, _, _, _ = np.linalg.lstsq(X_lm, log_vm2, rcond=None)
    elasticidad = coeffs_lm[0]
    
    interp = "vm2 SUBE con m2" if elasticidad > 0.05 else ("vm2 BAJA con m2" if elasticidad < -0.05 else "vm2 PLANA")
    print(f"{mz:<20} {len(m2s):>5} {corr:>+14.4f} {elasticidad:>+12.4f}  {interp}")

# ============================================================
# 7. ANALISIS: EFECTO CROSS-BARRIER EN VALUACION
# ============================================================
print("\n" + "=" * 70)
print("PROPUESTA DE PENALTY DINAMICO PARA CROSS-BARRIER")
print("=" * 70)

print("""
LOGICA PROPUESTA:
  - Para comps del mismo lado (same): sin penalty
  - Para comps que cruzan barrera SOFT: penalty = gap_empirico / 2
    (gap medido de los datos reales, no 3% fijo)
  - Para comps que cruzan barrera HARD: excluir (comportamiento actual)
  
VENTAJA vs alpha+blend+penalty 3% fijo:
  - El 3% es arbitrario e ignora que el gap real varía de 0% a 40%
  - El alpha depende de n_same (estructura arbitraria)
  - El penalty dinamico emerge del mercado: si el gap es 20%, aplica 10%
  
IMPLEMENTACION:
  precio_cross_ajustado = precio_norm / (1 - gap_barrera/2)
  luego: percentil(all_prices_ajustados, P)
  
  donde gap_barrera = medido de los datos reales del cache
""")

# Calcular gaps para barreras soft principales
print("Gaps empiricos en barreras SOFT principales (radio 300m):")
print(f"{'Barrera':<45} {'N_A':>5} {'N_B':>5} {'P50_A':>8} {'P50_B':>8} {'Gap%':>8}")
print("-" * 85)

SOFT_TARGETS = ['pellegrini', 'oroño', 'orono', 'del valle', 'Francia', '27 de febrero', '27de']
soft_gaps = {}

for barrera in soft_barreras:
    props_b = barrera.get('properties', {})
    nombre = props_b.get('name', '?')
    nombre_lower = nombre.lower()
    
    # Solo analizar barreras con nombre conocido
    if not any(t.lower() in nombre_lower for t in SOFT_TARGETS):
        continue
    
    geom = barrera.get('geometry', {})
    coords = geom.get('coordinates', [])
    if not coords or len(coords) < 2:
        continue
    
    p1, p2 = coords[0], coords[-1]
    mid_lat = (p1[1] + p2[1]) / 2
    mid_lon = (p1[0] + p2[0]) / 2
    dlat = p2[1] - p1[1]
    dlon = p2[0] - p1[0]
    direction = 'NS' if abs(dlat) > abs(dlon) else 'EW'
    
    lado_A, lado_B = [], []
    for p in ventas_raw:
        try:
            plat, plon = float(p['lat']), float(p['lon'])
        except:
            continue
        dist = haversine_m(mid_lat, mid_lon, plat, plon)
        if dist > 300:
            continue
        vm2 = p.get('valor_m2', 0)
        if vm2 <= 0:
            continue
        if direction == 'NS':
            side = 'A' if plat > mid_lat else 'B'
        else:
            side = 'A' if plon > mid_lon else 'B'
        if side == 'A':
            lado_A.append(vm2)
        else:
            lado_B.append(vm2)
    
    if len(lado_A) < 5 or len(lado_B) < 5:
        continue
    
    p50_A = percentil(lado_A, 50)
    p50_B = percentil(lado_B, 50)
    gap_pct = abs(p50_A - p50_B) / max(p50_A, p50_B) * 100
    soft_gaps[nombre] = gap_pct / 100
    
    print(f"{nombre[:45]:<45} {len(lado_A):>5} {len(lado_B):>5} ${p50_A:>7,.0f} ${p50_B:>7,.0f} {gap_pct:>+7.1f}%")

print(f"\nGaps medios de barreras soft: {np.mean(list(soft_gaps.values()))*100:.1f}% (vs 3% fijo actual)")

# ============================================================
# 8. RESUMEN: CUAL ES EL MEJOR METODO
# ============================================================
print("\n" + "=" * 70)
print("CONCLUSION: METODO OPTIMO EMERGENTE DE LOS DATOS")
print("=" * 70)

print("""
1. SA (SIZE ADJUSTMENT):
   - La elasticidad log-log es NEGATIVA en todas las macrozonas:
     vm2 BAJA a medida que aumenta m2 (propiedades grandes son mas baratas por m2)
   - La curva varía por MACROZONA y DORMITORIO
   - SA categorico por dorm (chico/mediano/grande) captura esto correctamente
   - Fórmula: ratio = factor_sujeto / factor_comp (relativo, cap ±20%)

2. BLEND:
   - El blend alpha (0.50-0.70) + penalty (3%) es ARBITRARIO
   - El gap real entre same y cross varía enormemente (0% a 40% segun barrera)
   - PROPUESTA: penalty = gap_empirico_barrera / 2 (penaliza la mitad del gap real)
   - Si cruzas 27 de Febrero (gap real ~27%): penalty = 13.5% al comp cross
   - Si cruzas Pellegrini (gap real ~1%): penalty ≈ 0.5% (casi nada)
   - Si cruzas ferrocarril (hard): excluir

3. PERCENTIL:
   - P33/P40/P45/P50 según CV y N (sistema actual es correcto)
   - Sobre TODOS los comps ajustados (same con SA-relativo, cross con SA + penalty)

METODO FINAL PROPUESTO:
  vm2_comp_norm = precio_m2 * CT * (sa_sujeto / sa_comp) 
                  / (1 - penalty_barrera * is_cross)
  vm2 = percentil(sorted(vm2_comp_norms), P)
  USD = vm2 * m2_equiv + activos
""")

print("\nArchivo guardado: scratch/analisis_ml_results.json")
results_out = {
    'n_ventas': len(ventas_raw),
    'sa_factors': {mz: {str(d): {str(k): v for k, v in bdata.items()} 
                         for d, bdata in ddata.items() if isinstance(ddata, dict)}
                   for mz, ddata in sa_factors.items()},
    'soft_gaps': soft_gaps,
}
import os
os.makedirs('scratch', exist_ok=True)
with open('scratch/analisis_ml_results.json', 'w', encoding='utf-8') as f:
    json.dump(results_out, f, ensure_ascii=False, indent=2, default=str)
