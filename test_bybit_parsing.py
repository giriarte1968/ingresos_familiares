import re

def test_parsing(texto):
    lineas = texto.split('\n')
    
    amount_ars_pattern1 = re.compile(r'(-?\s*[\d.,]+)\s*ARS\s*(.+)', re.IGNORECASE)
    amount_ars_pattern2a = re.compile(r'(.+)\s+(-?\s*[\d.,]+)\s+ARS$', re.IGNORECASE)
    amount_ars_pattern2b = re.compile(r'^(-?\s*[\d.,]+)\s+ARS$', re.IGNORECASE)
    fecha_pattern = re.compile(r'(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}|\d{2}-\d{2}-\d{4})')
    
    ignorados = ['historial', 'correcto', 'pago con', 'fecha', 'todos los', 
                 'tipos', 'estados', 'qr', 'con qr', 'sin', 'pago']
    
    gastos = []
    i = 0
    while i < len(lineas):
        linea = lineas[i].strip()
        if not linea:
            i += 1
            continue
            
        debe_ignorar = any(ig.lower() in linea.lower() for ig in ignorados)
        # Exception for merchant names that might contain "pago"
        if "merpago" in linea.lower():
            debe_ignorar = False

        if debe_ignorar:
            i += 1
            continue
            
        ars_match = None
        matched_pattern = None
        
        # PATTERN 1: Amount at start
        match = amount_ars_pattern1.search(linea)
        if match:
            ars_match = match
            matched_pattern = amount_ars_pattern1
            
        # PATTERN 2a: Amount at end
        if not ars_match:
            match = amount_ars_pattern2a.search(linea)
            if match:
                ars_match = match
                matched_pattern = amount_ars_pattern2a
                
        # PATTERN 2b/3: ONLY Amount ARS
        if not ars_match and 'ARS' in linea.upper():
            # Flexible solo monto - allow leading - with optional space
            solo_monto = re.match(r'^-?\s*[\d.,\s]+ARS$', linea.strip(), re.IGNORECASE)
            # Capture the whole amount including possible minus and space
            monto_match = re.search(r'(-?\s*[\d.,]+)', linea)
            if solo_monto and monto_match:
                partes_desc = []
                for k in range(i-1, -1, -1):
                    prev = lineas[k].strip()
                    if not prev: continue
                    if any(ig.lower() in prev.lower() for ig in ignorados):
                        if partes_desc: break
                        continue
                    if 'ars' in prev.lower(): break
                    if re.match(r'^[\d.,\s-]+$', prev): break # Added space here
                    # Filter out helper lines like "con ****"
                    if "****" in prev: continue
                    # Filter out date lines
                    if fecha_pattern.search(prev): continue
                    
                    partes_desc.append(prev)
                
                if partes_desc:
                    partes_desc.reverse()
                    descripcion = ' '.join(partes_desc)
                    ars_match = monto_match
                    matched_pattern = 'solo_ars'
                    print(f"DEBUG: Found solo_ars with desc: {descripcion}")
                else:
                    # Fallback for debug
                    print(f"DEBUG: Found solo_ars but NO desc for line: {linea}")

        if ars_match:
            # print(f"MATCH: {linea}")
            monto_raw = ars_match.group(1 if matched_pattern != amount_ars_pattern2a else 2)
            # Remove spaces between minus and digits
            monto_str = monto_raw.replace(' ', '')
            
            try:
                # Basic normalization for test
                m_clean = monto_str.replace('.', '') # Remove thousand sep
                if ',' in m_clean:
                    m_clean = m_clean.replace(',', '.')
                
                monto = abs(float(m_clean))
                if matched_pattern == 'solo_ars':
                     print(f"MATCH: {monto} ARS at {descripcion}")
                elif matched_pattern == amount_ars_pattern2a:
                     print(f"MATCH: {monto} ARS at {ars_match.group(1)}")
            except Exception as e:
                print(f"  Error parsing monto '{monto_raw}': {e}")
        
        i += 1


texto_prueba = """
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

test_parsing(texto_prueba)
