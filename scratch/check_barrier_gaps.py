import json, sys, os
from collections import defaultdict
import numpy as np

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from scratch.simulate_v8f import BARRIER_VECTOR_INFO

gaps = [info['gap'] for info in BARRIER_VECTOR_INFO.values() if 'gap' in info]
print(f"Total barreras medidas en Rosario: {len(gaps)}")
print(f"Gaps medidos: {[round(g, 4) for g in gaps]}")

if gaps:
    p50_gap = np.median(gaps)
    p25_gap = np.percentile(gaps, 25)
    p75_gap = np.percentile(gaps, 75)
    print(f"Mediana empirica global del gap de barrera: {p50_gap:.4f} (P25={p25_gap:.4f}, P75={p75_gap:.4f})")
