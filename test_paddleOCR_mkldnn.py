import os
import numpy as np

# Desactivar OneDNN (suele romper PaddlePaddle en ciertos procesadores Windows)
os.environ['FLAGS_use_mkldnn'] = 'false'
os.environ['PADDLE_DISABLE_MKLDNN'] = '1'

from paddleocr import PaddleOCR

print("Instantiating with cpu math only...")
ocr = PaddleOCR(use_textline_orientation=True, lang='es', use_mkldnn=False, use_gpu=False)

img = np.zeros((100, 100, 3), dtype=np.uint8)

print("Testing ocr() directly...")
try:
    # No pasar cls=True
    res1 = ocr.ocr(img)
    print("Success without mkldnn!")
except Exception as e:
    print(f"Error: {e}")
