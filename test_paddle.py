from paddleocr import PaddleOCR
import logging

logging.getLogger('ppocr').setLevel(logging.ERROR)

ocr = PaddleOCR(use_textline_orientation=True, lang='es')
img_path = 'recibo_santa_fe_servicios.jpeg'

if not __import__('os').path.exists(img_path):
    print("No esta la imagen.")
else:
    result = ocr.ocr(img_path, cls=True)
    if result and result[0]:
        for line in result[0]:
            # bbox = [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
            bbox = line[0]
            txt = line[1][0]
            score = line[1][1]
            print(f"y_mean: {sum(pt[1] for pt in bbox)/4:.1f} x_mean: {sum(pt[0] for pt in bbox)/4:.1f} | TXT: '{txt}'")
