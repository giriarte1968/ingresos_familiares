import json, sys, os
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7

props = json.load(open('propiedades.json', 'r', encoding='utf-8')).get('propiedades', [])
er = None
for p in props:
    if 'entre rios' in p.get('nombre', '').lower() or '1372' in p.get('nombre', '').lower():
        er = p
        break

if er:
    print("==========================================")
    print("VALUACIÓN DE ENTRE RIOS 1372:")
    print("==========================================")
    print("  piso:", er.get('piso'))
    print("  ascensores:", er.get('ascensores'))
    print("  ascensores_edificio:", er.get('ascensores_edificio'))
    
    res = valuar_propiedad_v7(er)
    val_orig = res.get('valor_propiedad_usd')
    print(f"  Valor Actual (sin factor escalera): ${val_orig:,.0f} USD")
    print(f"  Valor con castigo -15% (2° piso escalera): ${val_orig * 0.85:,.0f} USD")
    print(f"  Valor con castigo -20% (2° piso escalera): ${val_orig * 0.80:,.0f} USD")
