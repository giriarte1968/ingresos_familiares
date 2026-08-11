import os, sys

sys_path = r'c:\Users\Gustavo\ingresos_familiares_st'
files = ['results_v9.txt', 'results_v7.txt', 'results_v6.txt', 'results_v5.txt', 'results_v4.txt']

for fname in files:
    fpath = os.path.join(sys_path, fname)
    if os.path.exists(fpath):
        print(f"=== {fname} ===")
        try:
            content = open(fpath, 'r', encoding='utf-16').read()
        except:
            content = open(fpath, 'r', encoding='latin-1').read()
        sys.stdout.buffer.write(content[:2500].encode('utf-8'))
        print("\n\n" + "="*50 + "\n")
