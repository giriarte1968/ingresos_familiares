import os
import fitz
import numpy as np
import cv2
from paddleocr import PaddleOCR
import re

pdf_dir = r"C:\Users\Gustavo\.gemini\antigravity\scratch\tests\data\validation_pdfs"

# Initialize PaddleOCR
ocr = PaddleOCR(use_angle_cls=True, lang='es', show_log=False)

street_pattern = re.compile(
    r"(?:calle|avenida|av\.?|bulevar|bv\.?|pasaje|pje\.?|cortada|ctda\.?)\s+"
    r"([A-ZÁÉÍÓÚÜÑa-záéíóúüñ\s\.]+?)\s+"
    r"(?:N[o°º]?\s*)?(\d{1,5}(?:\s*bis)?)", 
    re.IGNORECASE
)

known_streets = ["BALCARCE", "BROWN", "DORREGO", "RIVADAVIA", "GÜEMES", "GUEMES", "JUJUY", "OROÑO", "ORONO"]
known_pattern = re.compile(
    r"(" + "|".join(known_streets) + r")\s+(?:N[o°º]?\s*)?(\d{1,5}(?:\s*bis)?)",
    re.IGNORECASE
)

print("Starting PaddleOCR on right-side crops (Low DPI)...")

for filename in os.listdir(pdf_dir):
    if not filename.endswith(".pdf") or "fresh" in filename:
        continue
    filepath = os.path.join(pdf_dir, filename)
    
    try:
        doc = fitz.open(filepath)
        page = doc.load_page(0)
        
        # Get page dimensions
        rect = page.rect
        # We want the right 40% of the page.
        crop_rect = fitz.Rect(rect.width * 0.60, 0, rect.width, rect.height)
        
        # Render the cropped area at 150 DPI
        matrix = fitz.Matrix(150/72, 150/72)
        pix = page.get_pixmap(matrix=matrix, clip=crop_rect)
        
        # Convert to numpy array for PaddleOCR (avoiding PNG save/load)
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_BGRA2BGR)
        elif pix.n == 1:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
            
        print(f"\n--- {filename} ---")
        
        # Run PaddleOCR
        result = ocr.ocr(img_array, cls=True)
        
        ocr_text = []
        if result and result[0]:
            for line in result[0]:
                text = line[1][0]
                ocr_text.append(text)
                
        full_text = " ".join(ocr_text)
        
        matches = street_pattern.findall(full_text)
        known_matches = known_pattern.findall(full_text)
        
        if matches:
            print(f"Addresses found (regex 1): {matches}")
        elif known_matches:
            print(f"Known streets found (regex 2): {known_matches}")
        else:
            print("NO ADDRESS FOUND.")
            print(f"Sample OCR ({len(full_text)} chars): {full_text[:300]}")
            
    except Exception as e:
        print(f"Error processing {filename}: {e}")

print("\nDone.")
