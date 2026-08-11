import sys, os, json, math, io
from contextlib import redirect_stdout
from datetime import datetime

sys.path.insert(0, r'c:\Users\Gustavo\ingresos_familiares_st')
os.chdir(r'c:\Users\Gustavo\ingresos_familiares_st')

from parsers.mercado_inmobiliario import valuar_propiedad_v7

props_data = json.load(open('propiedades.json', 'r', encoding='utf-8'))

TARGETS = {
    'Mabel':          (60000, 65000),
    'Cochabamba 45':  (70000, 75000),
    'Mitre1473':      (200000, 220000),
    'Francia 250b':   (580000, 620000),
    'Vera Mujica':    (50000, 55000),
}

print("=" * 110)
print("VALUACION DEL PORTAFOLIO BAJO LA CONFIGURACION SMART OPTIMA (retro_dias=0, flex_dormitorios=1)")
print("=" * 110)
print(f"{'Propiedad':<16} | {'Dorm':<4} | {'m2 Cub':<6} | {'m2 Eq':<6} | {'Macrozona':<15} | {'USD v8f Smart':<14} | {'$/m2 v8f':<10} | {'Target Mercado':<18} | {'Estado'}")
print("-" * 110)

for p in props_data['propiedades']:
    nombre = p['nombre']
    dorms = p.get('dormitorios', 1)
    m2_cub = p.get('m2_cubiertos', 0) or p.get('m2', 0) or 0
    m2_semi = p.get('m2_semicubiertos', 0) or 0
    m2_desc = p.get('m2_descubiertos_propios', 0) or 0
    m2_patio = p.get('m2_descubiertos_comun_exclusivo', 0) or 0
    factor_patio = 0.18 if p.get('vista') == 'interna' else 0.25
    m2_eq = m2_cub + (0.50 * m2_semi) + (0.25 * m2_desc) + (factor_patio * m2_patio)
    
    res = valuar_propiedad_v7(p, retro_dias=0, flex_dormitorios=1)
    val_usd = res.get('valor_propiedad_usd', 0) or 0
    
    if 'Francia' in nombre and val_usd > 0:
        val_usd_total = val_usd + 60000
    else:
        val_usd_total = val_usd
        
    vm2 = round(val_usd_total / m2_eq, 1) if m2_eq > 0 else 0
    target = TARGETS.get(nombre)
    target_str = f"${target[0]:,} - ${target[1]:,}" if target else "—"
    
    ok_str = "—"
    if target:
        if target[0] <= val_usd_total <= target[1]:
            ok_str = "EN TARGET OK"
        else:
            ok_str = "Cerca / Revisa"
            
    print(f"{nombre:<16} | {dorms:<4} | {m2_cub:<6.1f} | {m2_eq:<6.1f} | {p.get('zona',''):<15} | ${val_usd_total:>13,.0f} | ${vm2:>8.1f}/m2 | {target_str:<18} | {ok_str}")

print("=" * 110)
