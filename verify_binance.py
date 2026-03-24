import re

def test_binance_logic(texto):
    lineas = texto.split('\n')
    
    # EXACT patterns from app.py after my changes
    amount_ars_pattern1 = re.compile(r'(-?\s*[\d.,]+)\s*ARS\s*(.*)', re.IGNORECASE)
    amount_ars_pattern2a = re.compile(r'(.+)\s+(-?\s*[\d.,]+)\s*ARS$', re.IGNORECASE)
    amount_ars_pattern2b = re.compile(r'^(-?\s*[\d.,]+)\s*ARS$', re.IGNORECASE)
    fecha_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})')
    
    ignorados = ['historial', 'correcto', 'pago con', 'fecha', 'todos los', 
                 'tipos', 'estados', 'qr', 'con qr', 'sin', 'con ****', '****', 
                 'completado', 'descontado']
    
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
        
        if not ars_match:
             match = amount_ars_pattern2b.search(linea)
             if match:
                 ars_match = match
                 matched_pattern = amount_ars_pattern2b

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
                # Normalización logic
                monto_str_norm = monto_str.strip()
                if monto_str_norm.startswith('-'):
                    monto_str_norm = '-' + monto_str_norm[1:].strip()
                
                cleaned_monto = ''.join(c for c in monto_str_norm if c.isdigit() or c in ',.-')
                
                s = ''.join(c for c in cleaned_monto if c.isdigit() or c in ',.')
                if not s: monto = 0.0
                else:
                    if ',' in s and '.' in s:
                        if s.rfind(',') > s.rfind('.'): s = s.replace('.', '').replace(',', '.')
                        else: s = s.replace(',', '')
                    else:
                        sep = ',' if ',' in s else ('.' if '.' in s else None)
                        if sep:
                            partes = s.split(sep)
                            if len(partes[-1]) == 2: s = s.replace(sep, '.')
                            elif len(partes[-1]) == 3: s = s.replace(sep, '')
                            else: s = s.replace(',', '.') if sep == ',' else s.replace('.', '')
                    monto = abs(float(s))
                
                gasto_desc = descripcion
                if not gasto_desc or len(gasto_desc) < 8 or gasto_desc.upper() in ['SOCIAL', 'PAGO', 'PAGO CON', 'CON QR']:
                    if i > 0:
                        partes_desc = []
                        for k in range(i-1, -1, -1):
                            prev_linea = lineas[k].strip()
                            if not prev_linea: continue
                            prev_ignore = any(ig.lower() in prev_linea.lower() for ig in ignorados)
                            prev_has_ars = 'ars' in prev_linea.lower()
                            prev_is_solo_monto = re.match(r'^-?\s*[\d.,\s]*ARS$', prev_linea, re.IGNORECASE)
                            
                            is_card_mask = "***" in prev_linea or re.search(r'\d{4}', prev_linea)
                            is_date = (fecha_pattern.search(prev_linea) and len(prev_linea) < 30)
                            is_solo_numero = re.match(r'^[\d. ,-]+$', prev_linea)
                            skip_line = is_card_mask or is_date or is_solo_numero
                            
                            if prev_has_ars or prev_is_solo_monto: break
                            if not prev_ignore and not skip_line and len(prev_linea) > 1:
                                partes_desc.append(prev_linea)
                            else:
                                if partes_desc: break
                        if partes_desc:
                            gasto_desc = ' '.join(reversed(partes_desc)) + (' ' + descripcion if descripcion else '')
                
                # Forward look-ahead for fragments like SOCIAL
                if i < len(lineas) - 1:
                    next_linea = lineas[i+1].strip()
                    next_ignore = any(ig.lower() in next_linea.lower() for ig in ignorados)
                    if next_linea and not next_ignore and 'ARS' not in next_linea.upper() and len(next_linea) > 2:
                        if not gasto_desc or next_linea.upper() in ['SOCIAL', 'S.A.', 'S.R.L.']:
                            gasto_desc = (gasto_desc + ' ' + next_linea).strip()

                gasto_desc = gasto_desc.replace('MERPAGO*', '').strip()
                
                categoria, subcategoria, gasto_final = "otros", "otros", gasto_desc.title()
                if 'CAJA DE PREVISION' in gasto_desc.upper() and 'SOCIAL' in gasto_desc.upper():
                    if monto > 500000:
                        categoria, subcategoria, gasto_final = 'servicios', 'salud', 'Salud (Caja Ingenieros)'
                    else:
                        categoria, subcategoria, gasto_final = 'servicios', 'jubilacion', 'Jubilación Mensual (Caja Ingenieros)'
                
                print(f"RESULT: Gasto: '{gasto_final}', Monto: {monto}, Cat/Sub: {categoria}/{subcategoria}")
                gastos.append({'gasto': gasto_final, 'monto': monto})
            except Exception as e:
                print(f"ERROR: {e} | monto_str: '{monto_str}'")
        
        i += 1
    return gastos

binance_ocr_text = """
CAJA DE PREVISION
-713,314ARS
SOCIAL
 Completado
Descantado
2026-03-0916:35:11
CAJA DE PREVISION
-158,883.63ARS
SOCIAL
Completado
Descontado
2026-03-0916:32:40
AMALFITANA SAS 065
-33.524ARS
2026-02-0412:17:24
Completado
API
-754,950.5ARS
2026-01-2916:55:15
@Completado
SUCCOTO096
-153,970.28ARS
"""

print("--- Test Binance OCR Format (v2) ---")
test_binance_logic(binance_ocr_text)
