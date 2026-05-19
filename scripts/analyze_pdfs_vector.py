import os
import fitz
import json

pdf_dir = r"C:\Users\Gustavo\.gemini\antigravity\scratch\tests\data\validation_pdfs"

print("Starting vector text extraction check...")
for filename in os.listdir(pdf_dir):
    if not filename.endswith(".pdf") or "fresh" in filename:
        continue
    filepath = os.path.join(pdf_dir, filename)
    doc = fitz.open(filepath)
    vector_text = ""
    for page in doc:
        # Extract text as words to preserve positioning and avoid garbled text
        words = page.get_text("words")
        # words is a list of [x0, y0, x1, y1, "word", block_no, line_no, word_no]
        words.sort(key=lambda w: (w[1], w[0])) # sort by y, then x
        vector_text += " ".join(w[4] for w in words)
        
    print(f"--- {filename} ---")
    if len(vector_text.strip()) > 20:
        print(f"VECTOR TEXT FOUND ({len(vector_text)} chars):")
        print(vector_text[:500] + "...")
        # Check if we can find street names
        streets = ["BALCARCE", "BROWN", "DORREGO", "RIVADAVIA", "GÜEMES", "JUJUY", "OROÑO"]
        found = [s for s in streets if s in vector_text.upper()]
        print(f"Streets found in vector: {found}")
    else:
        print("NO VECTOR TEXT")
    print("")

print("Done with vector check.")
