import subprocess

out = subprocess.check_output(['git', 'show', 'a645023:valu.py'], text=True, encoding='utf-8')
lines = out.splitlines()

for i, line in enumerate(lines):
    if 'def mostrar_dashboard' in line:
        print(f"mostrar_dashboard starts at line {i+1}")
        for j in range(i, min(i+150, len(lines))):
            print(f"{j+1}: {lines[j].encode('ascii', 'replace').decode('ascii')}")
