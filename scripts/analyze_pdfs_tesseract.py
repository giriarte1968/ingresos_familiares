import os
import cv2
import numpy as np
import fitz
import pytesseract
import re

pdf_dir = r"C:\Users\Gustavo\.gemini\antigravity\scratch\tests\data\validation_pdfs"

# Precompile regex for streets and numbers
# It looks for "Calle", "Avenida", "Bv", etc., followed by name and number
street_pattern = re.compile(
    r"(?:calle|avenida|av\.?|bulevar|bv\.?|pasaje|pje\.?|cortada|ctda\.?)\s+"
    r"([A-ZÁÉÍÓÚÜÑa-záéíóúüñ\s\.]+?)\s+"
    r"(?:N[o°º]?\s*)?(\d{1,5}(?:\s*bis)?)", 
    re.IGNORECASE
)

# Also a fallback regex for known street names
known_streets = ["BALCARCE", "BROWN", "DORREGO", "RIVADAVIA", "GÜEMES", "GUEMES", "JUJUY", "OROÑO", "ORONO"]
known_pattern = re.compile(
    r"(" + "|".join(known_streets) + r")\s+(?:N[o°º]?\s*)?(\d{1,5}(?:\s*bis)?)",
    re.IGNORECASE
)

print("Starting Tesseract OCR on right-side crops...")
for filename in os.listdir(pdf_dir):
    if not filename.endswith(".pdf") or "fresh" in filename:
        continue
    filepath = os.path.join(pdf_dir, filename)
    doc = fitz.open(filepath)
    
    # We assume the first page has the caratula
    page = doc.load_page(0)
    # Render at 150 DPI to keep size manageable but text readable
    pix = page.get_pixmap(matrix=fitz.Matrix(150/72, 150/72))
    img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n == 4:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_BGRA2BGR)
    elif pix.n == 1:
        img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)
        
    h, w = img_array.shape[:2]
    
    # Crop the right 35% of the image (caratula is usually on the right)
    crop_w = int(w * 0.35)
    img_crop = img_array[:, w - crop_w:]
    
    # Convert to grayscale
    gray = cv2.cvtColor(img_crop, cv2.COLOR_BGR2GRAY)
    
    # Thresholding to improve OCR
    # Otsu's thresholding
    _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    
    # Run Tesseract
    # config: --psm 3 (Fully automatic page segmentation)
    # lang='spa' for Spanish
    text = pytesseract.image_to_string(thresh, lang='spa', config='--psm 3')
    
    # To handle rotated text (sometimes caratulas are 90 degrees rotated)
    text_90 = ""
    if len(text.strip()) < 50: # If it didn't find much text, maybe it's rotated
        rotated = cv2.rotate(thresh, cv2.ROTATE_90_CLOCKWISE)
        text_90 = pytesseract.image_to_string(rotated, lang='spa', config='--psm 3')
        if len(text_90) > len(text):
            text = text_90
            
    # Try 270 degrees just in case
    if len(text.strip()) < 50:
        rotated270 = cv2.rotate(thresh, cv2.ROTATE_90_COUNTERCLOCKWISE)
        text_270 = pytesseract.image_to_string(rotated270, lang='spa', config='--psm 3')
        if len(text_270) > len(text):
            text = text_270

    print(f"--- {filename} ---")
    
    # Find addresses
    matches = street_pattern.findall(text)
    known_matches = known_pattern.findall(text)
    
    if matches:
        print(f"Addresses found: {matches}")
    elif known_matches:
        print(f"Known streets found: {known_matches}")
    else:
        print("NO ADDRESS FOUND.")
        # Print a snippet to see what OCR saw
        lines = [line.strip() for line in text.split('\n') if len(line.strip()) > 5]
        print(f"Sample OCR: {' | '.join(lines[:10])}")
        
    print("")

print("Done.")
