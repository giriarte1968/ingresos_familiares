import json, sys, os

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

with open('data/flex_dorm_factors.json', 'r', encoding='utf-8') as f:
    flex_data = json.load(f)

mz_dict = flex_data.get('data', flex_data)

print("Macrozonas en flex_dorm_factors.json:")
tot_samples = 0
weighted_ratios = {'1': 0.0, '2': 0.0, '3': 0.0, '4': 0.0}

for mz, data in mz_dict.items():
    if mz == '_global' or not isinstance(data, dict): continue
    n = data.get('n', data.get('n_props', 100))
    ratios = data.get('ratios_vs_2d', {})
    if not ratios: continue
    
    tot_samples += n
    print(f"  Macrozona: {mz:<18} | n_props: {n:>5} | ratios: {ratios}")
    for d_str in ['1', '2', '3', '4']:
        val = ratios.get(d_str, 1.0)
        weighted_ratios[d_str] += val * n

if tot_samples > 0:
    global_empirico = {d: round(weighted_ratios[d] / tot_samples, 4) for d in ['1', '2', '3', '4']}
    print("=" * 70)
    print(f"FALLBACK GLOBAL EMPIRICO DINAMICO (Muestras totales={tot_samples}):")
    print(json.dumps(global_empirico, indent=2))
