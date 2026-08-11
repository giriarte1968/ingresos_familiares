import json, os

m_path = r'c:\Users\Gustavo\ingresos_familiares_st\scratch\resultados_metodos.json'
if os.path.exists(m_path):
    data = json.load(open(m_path, 'r', encoding='utf-8'))
    print("Found resultados_metodos.json with", len(data), "entries")
    print(json.dumps(data[:2], indent=2))
else:
    print("resultados_metodos.json does not exist yet")
