import subprocess

out = subprocess.check_output(['git', 'show', 'a645023:valu.py'], text=True, encoding='utf-8')
lines = out.splitlines()

print(f"Total lines in valu.py at a645023: {len(lines)}")
for i, line in enumerate(lines[:100]):
    if 'def ' in line:
        print(f"Line {i+1}: {line}")
