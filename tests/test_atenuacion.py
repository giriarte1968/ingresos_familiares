import json
from parsers.mercado_inmobiliario import valuar_propiedad_v7, calcular_factores

with open('C:/Users/Gustavo/ingresos_familiares_st/propiedades.json') as f:
    d = json.load(f)
    props = d['propiedades']

print('Propiedad    | Edad | Delta Raw | Delta Efect | Valor')
print('-' * 60)

for nombre in ['Mabel', 'Ayacucho', 'Vera Mujica', 'P1200']:
    prop = [p for p in props if p.get('nombre') == nombre][0]
    f_dict = calcular_factores(prop)
    r = valuar_propiedad_v7(prop, fecha_ref='2026-04')
    
    anio = prop.get('anio_construccion', 2026)
    anti = 2026 - anio
    delta_raw = max(-0.60, -(anti * 0.006))
    dep = f_dict.get('depreciacion', 1.0)
    delta_ef = 1.0 - dep
    valor = r.get('valor_propiedad_usd', 0)
    
    print(f'{nombre:12} | {anti:4} | {delta_raw:8.3f} | {delta_ef:9.3f} | ${valor:,.0f}')