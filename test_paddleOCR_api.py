from paddleocr import PaddleOCR
import numpy as np

# Instantiate
print("Instantiating...")
ocr = PaddleOCR(use_textline_orientation=True, lang='es')

# Create dummy image
img = np.zeros((100, 100, 3), dtype=np.uint8)

print("Testing ocr() without cls...")
try:
    res1 = ocr.ocr(img)
    print("Success without cls!")
except Exception as e:
    print(f"Error without cls: {e}")

print("Testing ocr() with cls=True...")
try:
    res2 = ocr.ocr(img, cls=True)
    print("Success with cls!")
except Exception as e:
    print(f"Error with cls: {e}")

print("Testing ocr() with cls argument explicitly disabled in init...")
try:
    ocr2 = PaddleOCR(use_angle_cls=False, lang='es')
    res3 = ocr2.ocr(img, cls=False)
except Exception as e:
    print(f"Error ocr2: {e}")
