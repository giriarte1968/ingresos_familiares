import json, math, sys, os
import numpy as np

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

with open('data/sa_continuous.json', 'r', encoding='utf-8') as f:
    sa_cont_data = json.load(f)

with open('cache_scraping.json', 'r', encoding='utf-8') as f:
    cache = json.load(f)

# Calculate empirical size ratios per macrozone in cache
props = [p for p in cache['propiedades'] if p.get('operacion') == 'venta' and p.get('m2', 0) > 10 and p.get('valor_m2', 0) > 200]

mz_m2 = {}
for p in props:
    mz = p.get('zona', '_global')
    m2 = p.get('m2')
    if mz not in mz_m2: mz_m2[mz] = []
    mz_m2[mz].append(m2)

# Compute 2-sigma ratios for typical m2 variance in each macrozone
# Ratio = (m2_suj / m2_comp)^beta
# ln(ratio) = beta * (ln(m2_suj) - ln(m2_comp))
# std(ln(ratio)) = sqrt(2) * beta * std(ln(m2))

mz_bounds = {}
macrozonas_map = sa_cont_data.get('macrozonas', {})

for mz_id, mz_info in macrozonas_map.items():
    beta = mz_info.get('all', -0.18)
    if not beta or beta >= 0: beta = -0.18
    
    # Typical log-size std dev in Rosario is ~0.42
    # 2 * std(ln(ratio)) = 2 * |beta| * std(ln(m2)) * sqrt(2)
    std_ln_m2 = 0.42
    std_ln_ratio = abs(beta) * std_ln_m2 * math.sqrt(2)
    
    # 2-sigma bounds in log-space: [-2 * std, +2 * std]
    # In ratio space: [exp(-2 * std), exp(+2 * std)]
    low_bound = round(math.exp(-2.0 * std_ln_ratio), 3)
    high_bound = round(math.exp(+2.0 * std_ln_ratio), 3)
    
    mz_bounds[mz_id] = {'min': low_bound, 'max': high_bound, 'beta': beta}
    print(f"Macrozona: {mz_id:<18} | Beta: {beta:+.4f} | Dynamic 2-Sigma Bounds: [{low_bound:.3f}, {high_bound:.3f}]")

print("=" * 70)
print("JSON dict for code injection:")
print(json.dumps(mz_bounds, indent=2))
