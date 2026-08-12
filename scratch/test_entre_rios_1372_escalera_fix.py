import json, sys, os
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7

props = json.load(open('propiedades.json', 'r', encoding='utf-8')).get('propiedades', [])
er = None
for p in props:
    if '1372' in p.get('nombre', '') or '1372' in p.get('direccion', ''):
        er = p
        break

if er:
    print("==========================================")
    print("TEST VALUACIÓN DE ENTRE RIOS 1372:")
    print("==========================================")
    print("  piso:", er.get('piso'))
    print("  ascensores_edificio:", er.get('ascensores_edificio'))
    
    # 1. Sin factor escalera
    res_no_esc = valuar_propiedad_v7(er, retro_dias=0, flex_dormitorios=1)
    print("  Valor Sin Escalera:", res_no_esc.get('valor_propiedad_usd'))
    
    # 2. Con factor escalera (-15% para 2° piso)
    val_con_esc = res_no_esc.get('valor_propiedad_usd') * 0.85
    print("  Valor Con Escalera 2° Piso (-15%):", round(val_con_esc))
