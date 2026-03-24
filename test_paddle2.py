from paddleocr import PaddleOCR
import numpy as np

print("Instantiating PaddleOCR 2.9...")
# En 2.9.1, 'use_angle_cls' is supported, not deprecated.
ocr = PaddleOCR(use_angle_cls=True, lang='es', show_log=False)

img_path = r'C:\Users\Gustavo\ingresos_familiares\documentos\recibo_santa_fe_servicios_2.jpeg'

print(f"Testing ocr.ocr on {img_path}...")
try:
    results_raw = ocr.ocr(img_path, cls=True)
    if results_raw and results_raw[0]:
        for line in results_raw[0]:
            if not line: continue
            bbox = line[0]
            txt = line[1][0]
            score = line[1][1]
            print(f"y: {sum(pt[1] for pt in bbox)/4:.1f} x: {sum(pt[0] for pt in bbox)/4:.1f} | TXT: '{txt}'")
    else:
        print("No se encontraron resultados.")
except Exception as e:
    print(f"Error OCR: {e}")
