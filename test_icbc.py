import paddleocr, re, json, numpy as np
from PIL import Image

comercios = json.load(open(r'C:\Users\Gustavo\ingresos_familiares_st\comercios_conocidos.json', encoding='utf-8'))

def test_icbc(path, mes_sel):
    reader = paddleocr.PaddleOCR(use_angle_cls=True, lang='es', show_log=False)
    img = Image.open(path).convert('RGB')
    img_array = np.array(img)
    result = reader.ocr(img_array, cls=True)

    items = []
    if result and result[0]:
        for line in result[0]:
            if not line: continue
            bbox = line[0]
            x_center = (bbox[0][0] + bbox[2][0]) / 2
            y_center = (bbox[0][1] + bbox[2][1]) / 2
            text = line[1][0]
            items.append((y_center, x_center, text))
    items.sort()

    def parsear_monto(s):
        s = s.strip()
        negativo = s.startswith('$-')
        s = s.replace('$-', '').replace('$', '')
        if ',' in s:
            s = s.replace('.', '')
            s = s.replace(',', '.')
        else:
            parts = s.rsplit('.', 1)
            if len(parts) == 2 and len(parts[1]) == 2:
                s = parts[0].replace('.', '') + '.' + parts[1]
            else:
                s = s.replace('.', '')
        try:
            v = float(s)
        except:
            return 0.0
        return -abs(v) if negativo else abs(v)

    def parsear_fecha(s):
        m = re.match(r'(\d{1,2})-([A-Za-z]{3})-(\d{4})', s.strip())
        if not m:
            return ''
        dia = int(m.group(1))
        mes_str = m.group(2)
        anio = int(m.group(3))
        mm = {'Jan':'01','Feb':'02','Mar':'03','Abr':'04','May':'05','Jun':'06',
              'Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12',
              'Ene':'01','Ago':'08','Dic':'12'}
        mes_num = mm.get(mes_str.title()[:3].capitalize())
        if mes_num is None:
            return ''
        if not (1 <= dia <= 31 and 1900 <= anio <= 2100):
            return ''
        return f"{anio}-{mes_num}-{dia:02d}"

    gastos = []

    for i, (y_curr, x_curr, t_curr) in enumerate(items):
        if y_curr < 50:
            continue

        monto = parsear_monto(t_curr)
        if monto == 0.0:
            continue

        if monto > 0 and ('reintegro' in t_curr.lower() or 'liquidacion' in t_curr.lower() or 'credito' in t_curr.lower()):
            continue

        # Buscar descripcion: misma fila (x<200) o fila anterior
        desc_parts = []
        
        # Misma fila, x<200 (para icbc2 donde desc y monto mismo y)
        for y2, x2, t2 in items:
            if abs(y2 - y_curr) < 5 and x2 < 200 and t2 and not re.match(r'^\d[\d\-]+$', t2):
                desc_parts.append(t2)
        
        # Fila anterior (para icbc1)
        if not desc_parts:
            for y2, x2, t2 in items:
                if 0 < y_curr - y2 < 25 and x2 < 200 and t2 and not re.match(r'^\d[\d\-]+$', t2):
                    desc_parts.append(t2)

        # Buscar fecha: fila siguiente (diferencia ~17)
        fecha_gasto = ''
        for y2, x2, t2 in items:
            if 0 < y2 - y_curr < 25 and re.match(r'^\d{1,2}-[A-Za-z]{3}-\d{4}$', t2.strip()):
                fecha_gasto = parsear_fecha(t2)
                break

        if not desc_parts:
            continue

        desc = ' '.join(desc_parts)
        dlow = desc.lower()
        if not dlow.strip():
            continue
        if 'cuenta' in dlow or 'banco' in dlow or 'saldo' in dlow:
            continue
        if 'liquidacion' in dlow:
            continue
        if 'reintegro' in dlow:
            continue

        if 'spotify' in dlow or 'dlocal spotify' in dlow:
            monto = 981.49
            cat, sub, g = 'servicios', 'suscripciones', 'Spotify'
        elif 'arca' in dlow or 'pago arca' in dlow:
            cat, sub, g = 'impuestos', 'impuestos', 'Monotributo'
        elif 'iva' in dlow or ('impuesto' in dlow and 'valor' in dlow):
            cat, sub, g = 'impuestos', 'impuestos', 'IVA'
        elif 'operaciones banel' in dlow:
            cat, sub, g = 'otros', 'otros', 'Operaciones Bancarias'
        elif 'debito inmediato' in dlow:
            cat, sub, g = 'otros', 'otros', 'Debito Inmediato'
        elif 'com rechazo' in dlow or 'rechazo deb' in dlow:
            cat, sub, g = 'otros', 'otros', 'Comision Rechazo Debito'
        elif 'transf mobil' in dlow or 'transf mobile' in dlow:
            cat, sub, g = 'otros', 'otros', 'Transferencia Mobil'
        elif 'sancor' in dlow:
            cat, sub, g = 'servicios', 'seguros', 'Sancor'
        elif 'polibot' in dlow:
            cat, sub, g = 'comercios', 'indumentaria', 'Polibot'
        elif 'havanna' in dlow:
            cat, sub, g = 'comercios', 'restaurant', 'Havanna'
        else:
            mk = next((k for k in comercios if k.lower() in dlow), None)
            if mk:
                cat, sub, g = comercios[mk]['categoria'], comercios[mk]['subcategoria'], comercios[mk]['gasto']
            else:
                cat, sub, g = 'otros', 'otros', desc

        gastos.append({'fecha': fecha_gasto, 'gasto': g, 'cat': cat, 'sub': sub, 'monto': abs(monto)})

    return gastos

for fname, mes in [('icbc1.jpg', '2026-02'), ('icbc2.jpg', '2026-03')]:
    print(f'\n=== {fname} (mes={mes}) ===')
    path = fr'C:\Users\Gustavo\ingresos_familiares\documentos\{fname}'
    gastos = test_icbc(path, mes)
    print(f'  {len(gastos)} gastos detectados')
    for g in gastos:
        print(f'  {g["fecha"]} | {g["gasto"]} | {g["sub"]} | {g["cat"]} | ${g["monto"]:,.2f}')