"""
Limpieza final de nombres y eliminación de anclas inválidas.
Genera data/anclas_rosario_v5_1_limpio.json

Uso: python scripts/limpiar_anclas_v5_1.py
"""
import json, os, sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

with open(os.path.join(BASE, 'data', 'anclas_rosario_v5_activo.json'), 'r', encoding='utf-8') as f:
    raw = json.load(f)
anclas = raw['anclas'] if isinstance(raw, dict) else raw

# Mapeo completo auto_gap -> nombre descriptivo
RENOMBRAR = {
    'auto_gap_alto_781': 'centro_san_luis_norte',
    'auto_gap_alto_872': 'sur_las_heras',
    'auto_gap_alto_873': 'sur_alvear',
    'auto_gap_alto_880': 'sur_san_martin',
    'auto_gap_alto_881': 'sur_domingo_matheu',
    'auto_gap_alto_890': 'sur_triangulo',
    'auto_gap_alto_892': 'sur_moderno',
    'auto_gap_medio_796': 'centro_manuel_belgrano',
    'auto_gap_medio_798': 'centro_entre_rios',
    'auto_gap_medio_799': 'sur_rueda',
    'auto_gap_medio_800': 'lourdes_francia',
    'auto_gap_medio_801': 'centro_oroño_sur',
    'auto_gap_medio_802': 'centro_catamarca',
    'auto_gap_medio_803': 'centro_pellegrini_sur',
    'auto_gap_medio_804': 'centro_mitre',
    'auto_gap_medio_805': 'centro_3febrero',
    'auto_gap_medio_806': 'martin_entre_rios',
    'auto_gap_medio_807': 'centro_jm_rosas',
    'auto_gap_medio_893': 'sur_lisandro_torre',
    'auto_gap_medio_896': 'centro_belgrano',
    'auto_gap_medio_898': 'oeste_lisandro_torre',
    'auto_gap_medio_901': 'sur_alvear_oeste',
    'auto_gap_medio_902': 'sur_belgrano',
    'auto_gap_medio_904': 'sur_antartida',
    'auto_gap_medio_906': 'sur_san_martin_oeste',
    'auto_gap_medio_907': 'sur_belgrano_sur',
    'auto_gap_medio_910': 'sur_rueda',
    'auto_gap_medio_911': 'centro_illia',
    'auto_gap_medio_912': 'sur_alvear_sur',
    'auto_gap_medio_913': 'sur_empalme_graneros',
    'auto_gap_medio_914': 'sur_alvear_este',
    'auto_gap_medio_915': 'sur_espana_hospitales',
    'auto_gap_medio_916': 'centro_3febrero_norte',
    'auto_gap_medio_917': 'echesortu_mendoza',
    'auto_gap_medio_920': 'sur_villa_urquiza',
    'auto_gap_medio_922': 'abasto_ituzaingo',
    'auto_gap_medio_924': 'sur_triangulo_oeste',
    'auto_gap_medio_925': 'centro_san_luis',
    'auto_gap_medio_926': 'sur_espana_hospitales_oeste',
    'auto_gap_medio_927': 'sur_altos_mendoza',
}

# Eliminar (fuera de Rosario o sin cobertura)
ELIMINAR = {
    'auto_gap_alto_878',   # Funes Lagos
    'auto_gap_alto_882',   # Funes Norte
    'auto_gap_medio_919',  # Funes Vida Club
    'auto_gap_medio_921',  # Victoria
    'auto_gap_medio_923',  # Funes Zona 14
}

resultado = []
stats = {'manuales': 0, 'renombradas': 0, 'eliminadas': 0}

for a in anclas:
    aid = a.get('id', a.get('nombre', ''))
    
    if aid in ELIMINAR:
        stats['eliminadas'] += 1
        continue
    
    if aid in RENOMBRAR:
        a['nombre_original'] = aid
        a['id'] = RENOMBRAR[aid]
        stats['renombradas'] += 1
    elif 'auto_gap' not in aid:
        stats['manuales'] += 1
    
    resultado.append(a)

output = {
    'version': '5.1',
    'fecha_limpieza': '2026-05-15',
    'anclas_originales_v5': len(anclas),
    'anclas_finales_v5_1': len(resultado),
    'eliminadas_fuera_rosario': 5,
    'renombradas': stats['renombradas'],
    'anclas': resultado,
}

out_path = os.path.join(BASE, 'data', 'anclas_rosario_v5_1_limpio.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(output, f, indent=2, ensure_ascii=False)

print(f'v5.1 generado: {len(resultado)} anclas')
print(f'  Manuales: {stats["manuales"]}')
print(f'  Renombradas (ex-auto_gap): {stats["renombradas"]}')
print(f'  Eliminadas (Funes/Victoria): {stats["eliminadas"]}')
print(f'  Reduccion: {len(anclas)} -> {len(resultado)} ({len(anclas)-len(resultado)} menos)')
print(f'  -> data/anclas_rosario_v5_1_limpio.json')

# Verificar que no quedan auto_gap
restantes = [a for a in resultado if 'auto_gap' in a.get('id', '')]
if restantes:
    print(f'\n⚠️ {len(restantes)} auto_gap SIN RENOMBRAR:')
    for a in restantes:
        print(f'  {a["id"]}')
else:
    print('\n✅ 0 auto_gap opacos - todos renombrados')
