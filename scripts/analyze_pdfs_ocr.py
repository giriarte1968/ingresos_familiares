import os
import fitz
import json
from paddleocr import PaddleOCR

pdf_dir = r"C:\Users\Gustavo\.gemini\antigravity\scratch\tests\data\validation_pdfs"

# Initialize PaddleOCR
# Use lang='es' for Spanish to handle accents better (e.g. Güemes)
ocr = PaddleOCR(use_angle_cls=True, lang='es', show_log=False)

def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    
    # 1. Try vector text extraction
    vector_text = ""
    for page in doc:
        vector_text += page.get_text()
        
    # 2. Try OCR on rendered images
    ocr_text = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        # Render page to image at 300 DPI for better OCR
        pix = page.get_pixmap(matrix=fitz.Matrix(300/72, 300/72))
        img_bytes = pix.tobytes("png")
        
        # Save temporary image for PaddleOCR (it can also take numpy arrays, but file is easy)
        temp_img_path = f"temp_page_{page_num}.png"
        with open(temp_img_path, "wb") as f:
            f.write(img_bytes)
            
        result = ocr.ocr(temp_img_path, cls=True)
        if result and result[0]:
            for line in result[0]:
                text = line[1][0]
                confidence = line[1][1]
                ocr_text.append(text)
                
        os.remove(temp_img_path)
        
    return vector_text, ocr_text

results = {}
for filename in os.listdir(pdf_dir):
    if not filename.endswith(".pdf") or "fresh" in filename:
        continue
    filepath = os.path.join(pdf_dir, filename)
    print(f"Processing {filename}...")
    vector_text, ocr_text = extract_text_from_pdf(filepath)
    results[filename] = {
        "vector_len": len(vector_text.strip()),
        "vector_sample": vector_text.strip()[:200].replace('\n', ' '),
        "ocr_text": " | ".join(ocr_text)
    }

with open("ocr_analysis_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("Done!")
