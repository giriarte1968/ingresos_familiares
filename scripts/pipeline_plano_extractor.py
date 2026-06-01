import os
import re
import fitz  # PyMuPDF
import cv2
import numpy as np
from paddleocr import PaddleOCR

class PlanoAddressExtractor:
    def __init__(self, use_gpu=False):
        """
        Inicializa el motor de extracción.
        Carga PaddleOCR en memoria para ser reutilizado en múltiples documentos.
        """
        print("[*] Iniciando motor PaddleOCR (esto puede tomar unos segundos)...")
        # lang='es' para manejar acentos como 'Güemes', 'Rivadavia'
        # use_angle_cls=True para detectar texto rotado (muy común en planos)
        self.ocr = PaddleOCR(use_angle_cls=True, lang='es', show_log=False, use_gpu=use_gpu)
        print("[*] Motor OCR listo.")

        # Patrón robusto para detectar calles, avenidas y rangos de números
        # Captura: CALLE JUJUY Nos 1845 y 1851 | B. RIVADAVIA N° 2137 / 2141
        self.pattern = re.compile(
            r"(?:CALLE|AVENIDA|AV\.?|BVAR\.?|BV\.?|PJE\.?|CORTADA)\s*:?\s*"
            r"([A-ZÁÉÍÓÚÜÑ\.\s]+?)\s+"
            r"(?:N(?:O|OS|RO|ROS|°|º|)\s*)?"
            r"(\d{1,5}(?:\s*BIS)?(?:\s*(?:/|Y|-)\s*\d{1,5}(?:\s*BIS)?)*)",
            re.IGNORECASE
        )

    def _extract_vector_text(self, page):
        """Extrae el texto incrustado nativamente en el PDF si es un plano vectorial CAD."""
        words = page.get_text("words")
        if not words:
            return ""
        
        # Ordenar palabras por posición 'Y', y luego por 'X' para mantener una lectura lógica
        words.sort(key=lambda w: (w[1], w[0]))
        vector_text = " ".join(w[4] for w in words)
        return vector_text

    def _extract_ocr_text(self, page):
        """Realiza un recorte estratégico de la Carátula y ejecuta el OCR."""
        rect = page.rect
        # Smart Cropping: Asumimos que la carátula está en el 40% derecho
        crop_rect = fitz.Rect(rect.width * 0.60, 0, rect.width, rect.height)
        
        # Renderizamos el recorte a 150 DPI (suficiente para OCR, evita colapsos de RAM)
        matrix = fitz.Matrix(150/72, 150/72)
        pix = page.get_pixmap(matrix=matrix, clip=crop_rect)
        
        # Convertimos la imagen de PyMuPDF a Numpy Array para OpenCV / PaddleOCR
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_BGRA2BGR)
        elif pix.n == 1:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)

        # Ejecutamos OCR sobre la imagen en memoria
        result = self.ocr.ocr(img_array, cls=True)
        
        ocr_text_list = []
        if result and result[0]:
            for line in result[0]:
                text = line[1][0]
                ocr_text_list.append(text)
                
        return " ".join(ocr_text_list)

    def _parse_addresses(self, raw_text):
        """Aplica las reglas de expresión regular para aislar calles y números/rangos."""
        text = raw_text.upper().replace('\n', ' ')
        matches = self.pattern.findall(text)
        
        resultados = []
        for match in matches:
            # Limpieza básica
            calle = re.sub(r'\s+', ' ', match[0].strip())
            numeros_raw = match[1].strip()
            
            # Dividir rangos (ej: "2137 / 2141" o "1845 y 1851")
            nums = [n.strip() for n in re.split(r'\s*(?:/|Y|-)\s*', numeros_raw) if n.strip()]
            
            # Filtro anti-falsos positivos (Línea de Calle o Línea Municipal)
            if "L.C." not in calle and "L. M." not in calle:
                resultados.append({
                    "calle": calle,
                    "numeros": nums
                })
        
        return resultados

    def process_pdf(self, pdf_path):
        """Método principal para procesar un PDF completo."""
        try:
            doc = fitz.open(pdf_path)
            if len(doc) == 0:
                return {"status": "error", "message": "PDF vacío"}
                
            page = doc.load_page(0) # Casi siempre la carátula está en la hoja 1
            
            # Intento 1: Texto Vectorial
            metodo = "Vectorial CAD"
            raw_text = self._extract_vector_text(page)
            
            # Intento 2: OCR Fallback
            # Si se encontraron menos de 100 caracteres, asumimos que es una imagen escaneada
            if len(raw_text.strip()) < 100:
                metodo = "OCR Recorte"
                raw_text = self._extract_ocr_text(page)
                
            doc.close()
            
            # Procesamos el texto final
            direcciones = self._parse_addresses(raw_text)
            
            return {
                "status": "success",
                "metodo": metodo,
                "direcciones_encontradas": direcciones,
                "texto_parcial": raw_text[:500] + "..." if len(raw_text) > 500 else raw_text
            }
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

# =========================================================================
# Ejemplo de Ejecución
# =========================================================================
if __name__ == "__main__":
    import glob
    
    # Directorio de los planos de prueba (ajusta la ruta según lo necesites)
    pdf_dir = r"C:\Users\Gustavo\.gemini\antigravity\scratch\tests\data\validation_pdfs"
    
    if os.path.exists(pdf_dir):
        # Instanciamos la clase una sola vez para que PaddleOCR se cargue en memoria
        extractor = PlanoAddressExtractor()
        
        print("\n--- INICIANDO EXTRACCIÓN DE DIRECCIONES ---\n")
        pdf_files = glob.glob(os.path.join(pdf_dir, "*.pdf"))
        
        for pdf in pdf_files:
            if "fresh" in pdf: 
                continue
                
            filename = os.path.basename(pdf)
            print(f"Procesando: {filename}")
            
            resultado = extractor.process_pdf(pdf)
            
            if resultado['status'] == 'success':
                print(f"  > Método Usado: {resultado['metodo']}")
                dirs = resultado['direcciones_encontradas']
                
                if dirs:
                    for d in dirs:
                        print(f"  > 🏠 Dirección: {d['calle']} - Número(s): {', '.join(d['numeros'])}")
                else:
                    print("  > ❌ No se encontraron direcciones válidas.")
            else:
                print(f"  > ❌ ERROR: {resultado['message']}")
                
            print("-" * 50)
    else:
        print(f"El directorio '{pdf_dir}' no existe. Ajusta la ruta en el bloque main.")
