import sys, os, math, json
from collections import defaultdict

sys_path = r'c:\Users\Gustavo\ingresos_familiares_st'
os.chdir(sys_path)
sys.path.insert(0, sys_path)

m_path = r'c:\Users\Gustavo\ingresos_familiares_st\scratch\resultados_metodos.json'
if os.path.exists(m_path):
    resultados = json.load(open(m_path, 'r', encoding='utf-8'))
    
    metodos = ['static', 'dyna_p', 'dyna', 'idw2', 'idw15', 'idw1', 'hybrid']
    totales = defaultdict(float)
    for r in resultados:
        for m in metodos + ['stored', 'manual']:
            v = r['usd'].get(m)
            if v: totales[m] += v

    print(f"=== METRICAS COMPARATIVAS SOBRE PROPIEDADES DE MUESTRA (vs MANUAL y STORED) ===")
    print(f"{'Método':<14} {'MAE (vs Manual)':>16} {'RMSE (vs Manual)':>18} {'Bias (vs Manual)':>18} {'MAE (vs Stored)':>16} {'RMSE (vs Stored)':>18} {'Bias (vs Stored)':>18}")
    print("-" * 110)
    for m in metodos:
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
            nm = {'static':'STATIC (S1)','dyna_p':'DynA+P (v8f)','dyna':'DynA','idw2':'IDW-p2','idw15':'IDW-p1.5','idw1':'IDW-p1','hybrid':'HYBRID'}
            print(f"{nm[m]:<14} {mae_m:>15.2f}% {rmse_m:>17.2f}% {bias_m:>+17.2f}% {mae_s:>15.2f}% {rmse_s:>17.2f}% {bias_s:>+17.2f}%")
