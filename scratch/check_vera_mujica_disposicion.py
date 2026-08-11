import json, sys, os
sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7, calcular_factores

props = json.load(open('propiedades.json', 'r', encoding='utf-8')).get('propiedades', [])
vera = None
for p in props:
    if 'vera' in p.get('nombre', '').lower() or 'vera' in p.get('direccion', '').lower():
        vera = p
        break

if vera:
    print("==========================================")
    print("DATOS DE VERA MUJICA EN PROPIEDADES.JSON:")
    print("==========================================")
    print("  piso:", vera.get('piso'))
    print("  disposicion:", vera.get('disposicion'))
    print("  vista:", vera.get('vista'))
    print("  reciclado:", vera.get('reciclado'))
    print("  reciclado_tipo:", vera.get('reciclado_tipo'))
    
    factores = calcular_factores(vera)
    print("\nFACTORES FISICOS COMPUTADOS:")
    for k, v in factores.items():
        print(f"  {k}: {v}")
    
    res = valuar_propiedad_v7(vera)
    print("\nRESULTADO VALUACION AUTOMATICA:")
    print("  valor_propiedad_usd:", res.get('valor_propiedad_usd'))
    print("  m2_base_venta:", res.get('m2_base_venta'))
    print("  m2_equivalentes:", res.get('m2_equivalentes'))
    print("  size_discount:", res.get('size_discount'))
    print("  factor_calidad:", res.get('factor_calidad'))
