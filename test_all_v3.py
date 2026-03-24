import re

def test_logic_v3(texto):
    lineas = [l.strip() for l in texto.split('\n') if l.strip()]
    
    amount_ars_pattern1 = re.compile(r'^(-?\s*[\d.,]+)\s*ARS\s*(.*)', re.IGNORECASE)
    amount_ars_pattern2a = re.compile(r'(.+)\s+(-?\s*[\d.,]+)\s*ARS$', re.IGNORECASE)
    amount_ars_pattern2b = re.compile(r'^(-?\s*[\d.,]+)\s*ARS$', re.IGNORECASE)
    fecha_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})')
    
    ignorados = ['historial', 'correcto', 'pago con', 'fecha', 'todos los', 
                 'tipos', 'estados', 'qr', 'con qr', 'sin', 'con ****', '****', 
                 'completado', 'descontado']
    
    CASOS_ASEGURADOS = {
        'la gran argentina': {'categoria': 'comercios', 'subcategoria': 'restaurant', 'gasto': 'La Gran Argentina'},
        'alberto rey': {'categoria': 'comercios', 'subcategoria': 'limpieza', 'gasto': 'Alberto Rey'},
        'rey diego alberto': {'categoria': 'comercios', 'subcategoria': 'limpieza', 'gasto': 'Alberto Rey'},
        'tu quincho': {'categoria': 'servicios', 'subcategoria': 'eventos', 'gasto': 'Tu Quincho (Salón)'},
        'rosati damian': {'categoria': 'comercios', 'subcategoria': 'restaurant', 'gasto': 'Pizzería Rosati'},
        'transito': {'categoria': 'servicios', 'subcategoria': 'transporte', 'gasto': 'Transito Rosario'},
    }

    def categorizar(desc, monto):
        desc_upper = desc.upper()
        if 'CAJA DE PREVISION' in desc_upper and 'SOCIAL' in desc_upper:
            if monto > 500000: return 'servicios', 'salud', 'Salud (Caja Ingenieros)'
            else: return 'servicios', 'jubilacion', 'Jubilación Mensual (Caja Ingenieros)'
        
        nombre_limpio = desc.lower()
        for caso, info in CASOS_ASEGURADOS.items():
            if caso in nombre_limpio or (len(nombre_limpio) >= 4 and nombre_limpio in caso):
                return info['categoria'], info['subcategoria'], info['gasto']
        return "otros", "otros", desc.title()

    gastos = []
    i = 0
    while i < len(lineas):
        linea = lineas[i]
        ars_match = amount_ars_pattern1.search(linea) or amount_ars_pattern2a.search(linea) or amount_ars_pattern2b.search(linea)
        
        if ars_match:
            # Simple extract for test
            m_str = re.search(r'(-?\s*[\d.,]+)', ars_match.group(0)).group(1)
            # Normalización logic
            s = ''.join(c for c in m_str if c.isdigit() or c in ',.')
            if ',' in s and '.' in s:
                if s.rfind(',') > s.rfind('.'): s = s.replace('.', '').replace(',', '.')
                else: s = s.replace(',', '')
            else:
                sep = ',' if ',' in s else ('.' if '.' in s else None)
                if sep:
                    partes = s.split(sep)
                    if len(partes[-1]) == 2: s = s.replace(sep, '.')
                    elif len(partes[-1]) == 3: s = s.replace(sep, '')
                s = s.replace(',', '.') if ',' in s and '.' not in s and len(s.split(',')[-1])==2 else s
            monto = abs(float(s))
            
            # Desc
            desc_inicial = ""
            if amount_ars_pattern1.search(linea): desc_inicial = amount_ars_pattern1.search(linea).group(2)
            elif amount_ars_pattern2a.search(linea): desc_inicial = amount_ars_pattern2a.search(linea).group(1)
            
            gasto_desc = desc_inicial
            if not gasto_desc or len(gasto_desc) < 8 or gasto_desc.upper() in ['SOCIAL', 'PAGO', 'PAGO CON', 'CON QR']:
                partes_desc = []
                for k in range(i-1, -1, -1):
                    prev = lineas[k]
                    if 'ARS' in prev.upper(): break
                    if any(ig.lower() in prev.lower() for ig in ignorados): continue
                    if "***" in prev or re.search(r'\d{4}', prev) or fecha_pattern.search(prev): continue
                    partes_desc.append(prev)
                    if len(partes_desc) > 0: break # Simplified for test
                if partes_desc:
                    gasto_desc = ' '.join(reversed(partes_desc)) + (' ' + desc_inicial if desc_inicial else '')
            
            # Look ahead
            if i < len(lineas) - 1:
                nxt = lineas[i+1]
                if nxt.upper() in ['SOCIAL', 'S.A.', 'S.R.L.']:
                    gasto_desc = (gasto_desc + ' ' + nxt).strip()
            
            # Cleanup
            gasto_desc = gasto_desc.replace('MERPAGO*', '').replace('Pago', '').replace('con QR', '').strip()
            gasto_desc = re.sub(r'\.+$', '', gasto_desc).strip()
            
            cat, sub, final = categorizar(gasto_desc, monto)
            gastos.append({'gasto': final, 'monto': monto, 'cat': cat})
            print(f"[{final}] ${monto} ({cat})")
        i += 1
    return gastos

print("--- BYBIT CARD ---")
test_logic_v3("@oi0\nCoto\n- 6.999,93 ARS\n2441\n2026-03-14 14.01:05\nMERPAGO*TRAN...\n468,50 ARS")

print("\n--- BYBIT QR ---")
test_logic_v3("10,150.00 ARS GGE ALFA PARK - restaurant\nInstituto Gamma Sa 18.000 ARS")

print("\n--- BINANCE QR ---")
test_logic_v3("CAJA DE PREVISION\n-713,314ARS\nSOCIAL\nAMALFITANA SAS 065\n-33.524ARS")
