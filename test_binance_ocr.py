import sys
import os

# Set up environment variables to avoid PaddleOCR issues
os.environ['FLAGS_use_mkldnn'] = 'false'
os.environ['PADDLE_DISABLE_MKLDNN'] = '1'

try:
    from paddleocr import PaddleOCR
    import numpy as np
    from PIL import Image
    
    # Initialize PaddleOCR
    ocr = PaddleOCR(use_angle_cls=True, lang='es', show_log=False)
    
    # Path to the image
    img_path = r'C:\Users\Gustavo\.gemini\antigravity\brain\6a7f11d0-5586-44bf-b3ab-399684ac3a79\media__1774112028694.png'
    
    # Perform OCR
    img = Image.open(img_path).convert('RGB')
    img_array = np.array(img)
    result = ocr.ocr(img_array, cls=True)
    
    # Print results
    if result and result[0]:
        for line in result[0]:
            print(line[1][0])
            
except Exception as e:
    print(f"Error: {e}")
