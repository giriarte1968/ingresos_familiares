import re

# Mocking the functions and variables from app.py to verify the logic
def mock_categorizar_gasto(desc, datos):
    return "categoria_test", "subcategoria_test", desc.title()

def test_app_logic(texto):
    lineas = texto.split('\n')
    
    # EXACT patterns from app.py after my changes
    amount_ars_pattern1 = re.compile(r'(-?\s*[\d.,]+)\s*ARS\s*(.+)', re.IGNORECASE)
    amount_ars_pattern2a = re.compile(r'(.+)\s+(-?\s*[\d.,]+)\s+ARS$', re.IGNORECASE)
    amount_ars_pattern2b = re.compile(r'^(-?\s*[\d.,]+)\s+ARS$', re.IGNORECASE)
    fecha_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})')
    
    ignorados = ['historial', 'correcto', 'pago con', 'fecha', 'todos los', 
                 'tipos', 'estados', 'qr', 'con qr', 'sin']
    
    debug_info = []
    gastos = []
    i = 0
    while i < len(lineas):
        linea = lineas[i].strip()
        if not linea:
            i += 1
            continue
            
        debe_ignorar = any(ig.lower() in linea.lower() for ig in ignorados)
        if debe_ignorar:
            i += 1
            continue
            
        ars_match = None
        matched_pattern = None
        
        match = amount_ars_pattern1.search(linea)
        if match:
            ars_match = match
            matched_pattern = amount_ars_pattern1
            
        if not ars_match:
            match = amount_ars_pattern2a.search(linea)
            if match:
                ars_match = match
                matched_pattern = amount_ars_pattern2a
                
        if not ars_match and 'ARS' in linea.upper():
            solo_monto = re.match(r'^-?\s*[\d.,\s]+ARS$', linea.strip(), re.IGNORECASE)
            monto_match = re.search(r'(-?\s*[\d.,]+)', linea)
            if solo_monto and monto_match:
                ars_match = monto_match
                matched_pattern = 'solo_ars'

        if ars_match:
            descripcion = ''
            if matched_pattern == amount_ars_pattern1:
                monto_str = ars_match.group(1)
                descripcion = ars_match.group(2).strip()
            elif matched_pattern == amount_ars_pattern2a:
                descripcion = ars_match.group(1).strip()
                monto_str = ars_match.group(2)
            else:
                monto_str = ars_match.group(1)
                descripcion = ''
            
            try:
                # Normalización logic from app.py
                monto_str_norm = monto_str.strip()
                if monto_str_norm.startswith('-'):
                    monto_str_norm = '-' + monto_str_norm[1:].strip()
                
                cleaned_monto = ''.join(c for c in monto_str_norm if c.isdigit() or c in ',.-')
                
                # Further normalization (comma vs dot)
                if cleaned_monto:
                    dot_count = cleaned_monto.count('.')
                    comma_count = cleaned_monto.count(',')
                    if dot_count > 0 and comma_count > 0:
                        last_dot = cleaned_monto.rfind('.')
                        last_comma = cleaned_monto.rfind(',')
                        if last_comma > last_dot: cleaned_monto = cleaned_monto.replace('.', '').replace(',', '.')
                        else: cleaned_monto = cleaned_monto.replace(',', '')
                    elif comma_count > 0: cleaned_monto = cleaned_monto.replace(',', '.')
                    elif dot_count > 1: cleaned_monto = cleaned_monto.replace('.', '')
                
                monto = abs(float(cleaned_monto.replace(' ', '')))
                
                gasto_desc = descripcion
                if not gasto_desc or len(gasto_desc) < 3:
                    if i > 0:
                        partes_desc = []
                        for k in range(i-1, -1, -1):
                            prev_linea = lineas[k].strip()
                            if not prev_linea: continue
                            prev_ignore = any(ig.lower() in prev_linea.lower() for ig in ignorados)
                            prev_has_ars = 'ars' in prev_linea.lower()
                            prev_is_solo_monto = re.match(r'^-?\s*[\d.,\s]+ARS$', prev_linea, re.IGNORECASE)
                            
                            # Filters added in my change
                            skip_line = "****" in prev_linea or (fecha_pattern.search(prev_linea) and len(prev_linea) < 30)
                            
                            if not prev_ignore and not prev_has_ars and not prev_is_solo_monto and not skip_line and len(prev_linea) > 1:
                                partes_desc.append(prev_linea)
                            else:
                                if partes_desc: break
                        if partes_desc:
                            gasto_desc = ' '.join(reversed(partes_desc))
                
                print(f"RESULT: Gasto: '{gasto_desc}', Monto: {monto}")
                gastos.append({'gasto': gasto_desc, 'monto': monto})
            except Exception as e:
                print(f"ERROR: {e} | monto_str: '{monto_str}'")
        
        i += 1
    return gastos

texto_input = """
Coto
con **** 2441
2026-03-14 14:01:05
- 6.999,93 ARS
Pago

MERPAGO*TRAN...
con **** 2877
2026-03-12 14:01:01
- 468,50 ARS
Pago
"""

# Test with existing QR format to ensure no regression
texto_qr = """
GGE ALFA PARK 10,150.00 ARS
Instituto Gamma Sa 18000.00 ARS
"""

print("--- Test Bybit Card ---")
test_app_logic(texto_input)
print("\n--- Test Bybit QR (No regression) ---")
test_app_logic(texto_qr)
