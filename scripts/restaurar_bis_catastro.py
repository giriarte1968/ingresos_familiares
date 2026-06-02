"""
Restaura los sufijos "bis" que fueron incorrectamente removidos
de rosario_avm_full.csv durante procesamiento previo.

Metodo: compara el backup (que conserva los "bis") contra la version main.
Para cada PH que tenia "bis" en backup y lo perdio en main, restaura la direccion original.

Uso: python scripts/restaurar_bis_catastro.py
"""

import pandas as pd
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
MAIN_CSV = os.path.join(DATA_DIR, "rosario_avm_full.csv")
BACKUP_CSV = os.path.join(DATA_DIR, "rosario_avm_full.csv.backup_20260530_antes_interpolacion")


def main():
    main = pd.read_csv(MAIN_CSV, encoding="utf-8")
    bk = pd.read_csv(BACKUP_CSV, encoding="utf-8")

    mb = bk["direccion_nominatim"].astype(str).str.lower().str.contains("bis", na=False)
    mm = main["direccion_nominatim"].astype(str).str.lower().str.contains("bis", na=False)

    bk_bis_phs = set(bk[mb]["ph"].tolist())
    main_bis_phs = set(main[mm]["ph"].tolist())
    lost_phs = bk_bis_phs - main_bis_phs

    print(f"Bis en backup: {len(bk_bis_phs)}")
    print(f"Bis en main:   {len(main_bis_phs)}")
    print(f"Perdidos:      {len(lost_phs)}")

    # Backup del main antes de modificar
    backup_main = MAIN_CSV.replace(".csv", ".csv.bak_antes_restaurar_bis")
    if not os.path.exists(backup_main):
        main.to_csv(backup_main, index=False, encoding="utf-8")
        print(f"Backup de main guardado: {backup_main}")

    restaurados = []
    for ph in lost_phs:
        addr_bk = bk.loc[bk["ph"] == ph, "direccion_nominatim"].values[0]
        idx = main[main["ph"] == ph].index
        if len(idx) > 0:
            old_addr = main.at[idx[0], "direccion_nominatim"]
            main.at[idx[0], "direccion_nominatim"] = addr_bk
            restaurados.append((ph, old_addr, addr_bk))

    main.to_csv(MAIN_CSV, index=False, encoding="utf-8")
    print(f"Restaurados: {len(restaurados)}")
    for ph, old, new in restaurados[:10]:
        print(f"  PH {ph}: '{old}' -> '{new}'")
    if len(restaurados) > 10:
        print(f"  ... y {len(restaurados) - 10} mas")

    # Verificar
    mm2 = main["direccion_nominatim"].astype(str).str.lower().str.contains("bis", na=False)
    print(f"\nBis en main post-restauracion: {mm2.sum()}")
    print("OK")


if __name__ == "__main__":
    main()
