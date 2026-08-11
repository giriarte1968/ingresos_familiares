import json, os

sys_path = r'c:\Users\Gustavo\ingresos_familiares_st'

print("--- OUTLIER EXCLUSION RESULTS ---")
res_md = os.path.join(sys_path, 'OUTLIER_EXCLUSION_RESULTS.md')
if os.path.exists(res_md):
    print(open(res_md, 'r', encoding='utf-8').read()[:1500])

print("\n--- RESULTS V9 ---")
v9 = os.path.join(sys_path, 'results_v9.txt')
if os.path.exists(v9):
    print(open(v9, 'r', encoding='utf-8').read()[:1500])

print("\n--- BACKTEST 1000 RESULTS JSON ---")
bt_json = os.path.join(sys_path, 'scratch', 'backtest_1000_results.json')
if os.path.exists(bt_json):
    d = json.load(open(bt_json, 'r', encoding='utf-8'))
    print("Keys in backtest json:", d.keys() if isinstance(d, dict) else len(d))
    if isinstance(d, dict) and 'metrics' in d:
        print(json.dumps(d['metrics'], indent=2))
