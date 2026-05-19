import os
import fitz

pdf_dir = r"C:\Users\Gustavo\.gemini\antigravity\scratch\tests\data\validation_pdfs"
output_dir = r"C:\Users\Gustavo\.gemini\antigravity\scratch\tests\data\caratulas"
os.makedirs(output_dir, exist_ok=True)

for filename in os.listdir(pdf_dir):
    if not filename.endswith(".pdf") or "fresh" in filename:
        continue
    filepath = os.path.join(pdf_dir, filename)
    doc = fitz.open(filepath)
    page = doc.load_page(0)
    
    # We assume the caratula is on the right side of the page
    # Let's crop the right 40% and bottom 60% which usually contains the title block
    rect = page.rect
    crop_rect = fitz.Rect(rect.width * 0.5, rect.height * 0.4, rect.width, rect.height)
    
    # Render at a good resolution (150 DPI)
    matrix = fitz.Matrix(150/72, 150/72)
    pix = page.get_pixmap(matrix=matrix, clip=crop_rect)
    
    out_path = os.path.join(output_dir, f"{filename.replace('.pdf', '')}.jpg")
    pix.save(out_path)
    print(f"Saved {out_path}")

print("Done extracting caratulas.")
