import pandas as pd

file_path = r'C:\Users\Gustavo\ingresos_familiares\documentos\Extracto_00020408903.xlsx'
try:
    # Galicia Excel usually has headers on line 6 (header=5)
    df = pd.read_excel(file_path, header=5)
    print("Columns:", df.columns.tolist())
    print("\nFirst 10 rows:")
    print(df.head(10))
    
    # Check if there is another sheet or if headers are elsewhere
    df_raw = pd.read_excel(file_path, header=None)
    print("\nRaw head (first 10 rows, no header):")
    print(df_raw.head(10))
    
except Exception as e:
    print(f"Error: {e}")
