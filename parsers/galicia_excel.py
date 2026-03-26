"""
Parser de Excel para Banco Galicia.
Extrae ingresos bancarios desde archivo Excel.
"""
import pandas as pd


def convertir_monto_argentino(valor):
    """Convierte monto formato argentino a float: 260.000,00 -> 260000.00"""
    if pd.isna(valor):
        return 0.0
    if isinstance(valor, (int, float)):
        return float(valor)

    valor_str = str(valor).strip()
    if not valor_str:
        return 0.0

    valor_limpio = valor_str.replace('.', '').replace(',', '.')
    try:
        return float(valor_limpio)
    except:
        return 0.0


def detectar_categoria(descripcion):
    """Versión simple local para ingresos Excel."""
    desc_lower = descripcion.lower()

    categorias = {
        'sueldo': ['sueldo', 'haberes', 'neto', 'remuneración', 'salario', 'nómina'],
        'alquiler': ['alquiler', 'renta', 'inquilino', 'cobro alquiler'],
        'intereses': ['interés', 'rendimiento', 'ganancia', 'fondo mutuo', 'renta'],
        'inversion': ['dividendo', 'acción', 'bono', 'plazo fijo', 'valorización'],
        'transferencia': ['transferencia', 'depósito', 'entrada', 'recibido'],
        'otro': [],
    }

    for cat, palabras in categorias.items():
        for palabra in palabras:
            if palabra in desc_lower:
                return cat
    return 'otro'


def extraer_movimientos_galicia_excel(archivo):
    """Extrae movimientos de un Excel de Banco Galicia."""
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
                    fecha_val = str(row.get(col_fecha, '')) if col_fecha else ''
                    desc_val = str(row.get(col_mov, '')).strip() if col_mov else ''
                    desc_val = ' '.join(desc_val.split())

                    categoria = detectar_categoria(desc_val)

                    movimientos.append({
                        'fecha': fecha_val,
                        'descripcion': desc_val[:150],
                        'monto': monto,
                        'monto_ars': None,
                        'banco': 'galicia',
                        'categoria': categoria,
                        'tasas': None
                    })

        return movimientos

    except Exception as e:
        print(f"Error al leer Excel Galicia: {e}")
        import traceback
        traceback.print_exc()
        return []
