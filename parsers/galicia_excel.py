"""
Parser de Excel para Banco Galicia.
Extrae ingresos o egresos desde archivo Excel.
"""
import re
import pandas as pd


def normalizar_fecha_galicia(fecha_raw):
    """Normaliza fecha a formato YYYY-MM-DD"""
    if not fecha_raw:
        return ''
    
    fecha_str = str(fecha_raw).strip()
    
    # Formato DD/MM/YYYY o DD-MM-YYYY
    m = re.match(r'(\d{2})[/-](\d{2})[/-](\d{4})', fecha_str)
    if m:
        return f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
    
    # Formato YYYY-MM-DD (ya normalizado)
    if re.match(r'\d{4}-\d{2}-\d{2}', fecha_str):
        return fecha_str[:10]
    
    # Pandas Timestamp
    if hasattr(fecha_raw, 'strftime'):
        return fecha_raw.strftime('%Y-%m-%d')
    
    return fecha_str[:10]


def convertir_monto_argentino(valor):
    """Convierte monto formato argentino a float: 260.000,00 -> 260000.00"""
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)

    valor_str = str(valor).strip()
    if not valor_str:
        return 0.0

    valor_str = valor_str.replace(' ', '')
    valor_limpio = valor_str.replace('.', '').replace(',', '.')
    try:
        return float(valor_limpio)
    except:
        return 0.0


def detectar_categoria_ingreso(descripcion):
    desc_lower = descripcion.lower()

    categorias = {
        'sueldo': ['sueldo', 'haberes', 'neto', 'remuneración', 'salario', 'nómina'],
        'alquiler': ['alquiler', 'renta', 'inquilino', 'cobro alquiler'],
        'intereses': ['interés', 'interes', 'rendimiento', 'ganancia', 'fondo mutuo', 'capitalizado'],
        'inversion': ['dividendo', 'acción', 'bono', 'plazo fijo', 'valorización'],
        'transferencia': ['transferencia', 'depósito', 'deposito', 'entrada', 'recibido'],
        'otro': [],
    }

    for cat, palabras in categorias.items():
        for palabra in palabras:
            if palabra in desc_lower:
                return cat
    return 'otro'


def extraer_movimientos_galicia_excel(archivo):
    """Extrae INGRESOS desde un Excel de Banco Galicia."""
    movimientos = []

    try:
        df = pd.read_excel(archivo, sheet_name=0, header=5)
        columnas = df.columns.tolist()

        col_fecha = None
        col_mov = None
        col_credito = None

        for col in columnas:
            col_lower = col.lower() if isinstance(col, str) else ''
            if 'fecha' in col_lower:
                col_fecha = col
            elif 'movimiento' in col_lower:
                col_mov = col
            elif 'crédito' in col_lower or 'credito' in col_lower:
                col_credito = col

        if col_credito:
            for _, row in df.iterrows():
                monto = convertir_monto_argentino(row.get(col_credito, 0))

                if monto > 0:
                    fecha_raw = row.get(col_fecha, '') if col_fecha else ''
                    fecha_val = normalizar_fecha_galicia(fecha_raw)
                    desc_val = str(row.get(col_mov, '')).strip() if col_mov else ''
                    desc_val = ' '.join(desc_val.split())

                    categoria = detectar_categoria_ingreso(desc_val)

                    movimientos.append({
                        'fecha': fecha_val,
                        'descripcion': desc_val[:200],
                        'monto': monto,
                        'monto_ars': None,
                        'banco': 'galicia',
                        'categoria': categoria,
                        'tasas': None
                    })

        return movimientos

    except Exception as e:
        print(f"Error al leer Excel Galicia (ingresos): {e}")
        import traceback
        traceback.print_exc()
        return []


def extraer_egresos_galicia_excel(archivo, categorizar_gasto_fn=None, datos=None,
                                  owner='Gustavo', medio_pago='Banco Galicia', generar_id_fn=None):
    """Extrae EGRESOS desde un Excel de Banco Galicia."""
    egresos = []

    try:
        df = pd.read_excel(archivo, sheet_name=0, header=5)
        columnas = df.columns.tolist()

        col_fecha = None
        col_mov = None
        col_debito = None

        for col in columnas:
            col_lower = col.lower() if isinstance(col, str) else ''
            if 'fecha' in col_lower:
                col_fecha = col
            elif 'movimiento' in col_lower:
                col_mov = col
            elif 'débito' in col_lower or 'debito' in col_lower:
                col_debito = col

        if not col_debito:
            return []

        for _, row in df.iterrows():
            monto = convertir_monto_argentino(row.get(col_debito, 0))

            if monto >= 0:
                continue

            fecha_raw = row.get(col_fecha, '') if col_fecha else ''
            fecha_val = normalizar_fecha_galicia(fecha_raw)
            desc_val = str(row.get(col_mov, '')).strip() if col_mov else ''
            desc_val = ' '.join(desc_val.split())

            if not desc_val:
                continue

            monto_abs = abs(monto)

            if categorizar_gasto_fn:
                categoria, subcategoria, gasto_final = categorizar_gasto_fn(desc_val, datos)
            else:
                categoria, subcategoria, gasto_final = 'otros', 'otros', desc_val[:200]

            egreso = {
                'fecha': fecha_val if fecha_val else '',
                'gasto': gasto_final,
                'monto': monto_abs,
                'moneda': 'ARS',
                'fuente': 'Galicia Excel',
                'categoria': categoria,
                'subcategoria': subcategoria,
                'owner': owner,
                'medio_pago': medio_pago,
                'u_id': generar_id_fn() if generar_id_fn else None
            }

            egresos.append(egreso)

        return egresos

    except Exception as e:
        print(f"Error al leer Excel Galicia (egresos): {e}")
        import traceback
        traceback.print_exc()
        return []
