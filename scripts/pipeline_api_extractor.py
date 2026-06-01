import os
import re
import fitz  # PyMuPDF
import cv2
import numpy as np
from paddleocr import PaddleOCR
import time
import requests
import queue
import threading
import pandas as pd
from concurrent.futures import ThreadPoolExecutor

# ============================================================
# CONFIGURACIÓN DEL PIPELINE
# ============================================================
WORKERS = 3          # Hilos para descargas simultáneas de PDFs (I/O)
INPUT_CSV = "data/rosario_avm_full.csv"
CHECKPOINT_FILE = "data/pdf_ocr_checkpoint_v2.csv" # Archivo nuevo para no pisar el histórico

pdf_queue = queue.Queue(maxsize=20)
result_lock = threading.Lock()
results = []  
processed_phis = set()
total_pending = 0

class PlanoAddressExtractor:
    def __init__(self, use_gpu=True): # Ahora usamos GPU por defecto si está disponible
        print("[*] Iniciando motor PaddleOCR (esto puede tomar unos segundos)...")
        self.ocr = PaddleOCR(use_angle_cls=True, lang='es', show_log=False, use_gpu=use_gpu)
        print("[*] Motor OCR listo.")

        self.pattern = re.compile(
            r"(?:CALLE|AVENIDA|AV\.?|BVAR\.?|BV\.?|PJE\.?|CORTADA)\s*:?\s*"
            r"([A-ZÁÉÍÓÚÜÑ\.\s]+?)\s+"
            r"(?:N(?:O|OS|RO|ROS|°|º|)\s*)?"
            r"(\d{1,5}(?:\s*BIS)?(?:\s*(?:/|Y|-)\s*\d{1,5}(?:\s*BIS)?)*)",
            re.IGNORECASE
        )

    def _extract_vector_text(self, page):
        words = page.get_text("words")
        if not words:
            return ""
        words.sort(key=lambda w: (w[1], w[0]))
        return " ".join(w[4] for w in words)

    def _extract_ocr_text(self, page):
        rect = page.rect
        # Smart Cropping: Asumimos que la carátula está en el 40% derecho y 50% inferior
        # Ajustamos el recorte respecto a la versión anterior para ser más precisos con la carátula
        crop_rect = fitz.Rect(rect.width * 0.60, rect.height * 0.50, rect.width, rect.height)
        
        # Resolución moderada (150 DPI) para no ahogar la RAM de GPU
        matrix = fitz.Matrix(150/72, 150/72)
        pix = page.get_pixmap(matrix=matrix, clip=crop_rect)
        
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
        if pix.n == 4:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_BGRA2BGR)
        elif pix.n == 1:
            img_array = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)

        result = self.ocr.ocr(img_array, cls=True)
        
        ocr_text_list = []
        if result and result[0]:
            for line in result[0]:
                ocr_text_list.append(line[1][0])
                
        return " ".join(ocr_text_list)

    def _parse_addresses(self, raw_text):
        text = raw_text.upper().replace('\n', ' ')
        matches = self.pattern.findall(text)
        
        resultados = []
        for match in matches:
            calle = re.sub(r'\s+', ' ', match[0].strip())
            numeros_raw = match[1].strip()
            nums = [n.strip() for n in re.split(r'\s*(?:/|Y|-)\s*', numeros_raw) if n.strip()]
            
            if "L.C." not in calle and "L. M." not in calle:
                # Formatear el resultado en un solo string como lo hacía el viejo pipeline
                dir_formateada = f"{calle} {'/'.join(nums)}"
                resultados.append(dir_formateada)
        
        return list(set(resultados)) # Evitar duplicados

    def process_pdf_bytes(self, pdf_bytes):
        try:
            doc = fitz.open("pdf", pdf_bytes)
            if len(doc) == 0:
                return {"status": "error", "message": "PDF vacío"}
                
            page = doc.load_page(0)
            
            # 1. Intentar vector nativo
            metodo = "Vectorial"
            raw_text = self._extract_vector_text(page)
            
            # 2. Fallback a OCR con Recorte Inteligente
            if len(raw_text.strip()) < 100:
                metodo = "OCR Recorte"
                raw_text = self._extract_ocr_text(page)
                
            doc.close()
            
            direcciones = self._parse_addresses(raw_text)
            
            return {
                "status": "success",
                "metodo": metodo,
                "direcciones": direcciones
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

# ============================================================
# WORKERS Y FLUJO MULTITHREADING
# ============================================================
def get_pdf_url(ph):
    """Obtener URL del PDF desde API de la Municipalidad"""
    try:
        resp = requests.post(
            "https://infomapa.rosario.gov.ar/emapa/planos/mensura/buscarPorCarpeta.htm",
            data={"nroCarpeta": str(ph)},
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=15
        )
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                imagenes = data[0].get("imagenes", [])
                if imagenes:
                    return "https://infomapa.rosario.gov.ar" + imagenes[0]["ruta"]
    except Exception:
        pass
    return None

def download_worker(ph):
    """Worker CPU: Descarga los bytes del PDF y los encola"""
    try:
        pdf_url = get_pdf_url(ph)
        if not pdf_url:
            return ph, None, "no PDF URL"

        resp = requests.get(pdf_url, timeout=30)
        if resp.status_code != 200:
            return ph, None, f"HTTP {resp.status_code}"

        return ph, resp.content, None
    except Exception as e:
        return ph, None, str(e)

def ocr_consumer_worker():
    """Worker Principal (GPU/CPU): Desencola bytes de PDF y extrae direcciones"""
    global results
    extractor = PlanoAddressExtractor() # Inicializa PaddleOCR una vez en este hilo
    
    while True:
        item = pdf_queue.get()
        if item is None: # Señal de terminación
            pdf_queue.task_done()
            break

        ph, pdf_bytes = item
        if pdf_bytes is None:
            with result_lock:
                results.append({"ph": ph, "direccion": "", "status": "no_image", "metodo": ""})
            pdf_queue.task_done()
            continue

        res = extractor.process_pdf_bytes(pdf_bytes)
        
        with result_lock:
            if res["status"] == "success":
                dirs = res["direcciones"]
                # Unimos todas las direcciones detectadas (por si es esquina) con un pipe
                dir_str = " | ".join(dirs) if dirs else ""
                status = "OK" if dir_str else "no_address"
                results.append({"ph": ph, "direccion": dir_str, "status": status, "metodo": res.get("metodo", "")})
            else:
                results.append({"ph": ph, "direccion": "", "status": f"error: {res['message']}", "metodo": ""})
                
        pdf_queue.task_done()
        processed_phis.add(ph)

        # Logging de progreso
        done = len(processed_phis)
        if done % 10 == 0:
            pct = done / total_pending * 100 if total_pending else 0
            print(f"  [{done}/{total_pending} ({pct:.1f}%)] procesados...")

        # Guardado incremental de seguridad (Checkpointing)
        if done % 50 == 0:
            save_checkpoint()

def save_checkpoint():
    with result_lock:
        df_ck = pd.DataFrame(results)
        df_ck.to_csv(CHECKPOINT_FILE, index=False)

def load_checkpoint():
    if os.path.exists(CHECKPOINT_FILE):
        ck = pd.read_csv(CHECKPOINT_FILE)
        for _, row in ck.iterrows():
            ph = int(float(row["ph"]))
            processed_phis.add(ph)
            results.append({
                "ph": ph, 
                "direccion": str(row.get("direccion", "")), 
                "status": str(row.get("status", "")),
                "metodo": str(row.get("metodo", ""))
            })
        print(f"[*] Checkpoint cargado: {len(processed_phis)} PHs ya procesados (Saltando)")
        return True
    return False

def main():
    global total_pending

    print("\n=== PIPELINE DE EXTRACCIÓN AVANZADA (API + VECTOR + SMART OCR) ===")
    
    # 1. Cargar base original
    if not os.path.exists(INPUT_CSV):
        print(f"Error: No se encontró el archivo de entrada en {INPUT_CSV}")
        return
        
    df = pd.read_csv(INPUT_CSV, encoding="utf-8", dtype=str)
    has_num = df["direccion_nominatim"].apply(
        lambda x: any(c.isdigit() for c in str(x)) if pd.notna(x) else False
    )
    sin_numero = df[~has_num]
    print(f"[*] Total PHs sin número según CSV original: {len(sin_numero)}")

    # 2. Cargar Checkpoint
    load_checkpoint()

    # 3. Determinar pendientes
    pendientes = []
    for _, row in sin_numero.iterrows():
        ph = int(float(row["ph"]))
        if ph not in processed_phis:
            pendientes.append(ph)

    total_pending = len(pendientes)
    print(f"[*] Pendientes por procesar en esta corrida: {total_pending}")
    
    if not pendientes:
        print("[*] ¡Todo procesado!")
        return

    # 4. Iniciar hilo consumidor (OCR/Vector)
    consumer_thread = threading.Thread(target=ocr_consumer_worker, daemon=True)
    consumer_thread.start()

    # 5. Iniciar Pool de Descargas (I/O)
    t_start = time.time()
    print(f"[*] Lanzando descargas concurrentes (Workers: {WORKERS})...")
    
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        futures = {executor.submit(download_worker, ph): ph for ph in pendientes}

        for future in futures:
            ph, pdf_bytes, error = future.result()
            if error:
                print(f"  [!] PH {ph}: Error de descarga -> {error}")
            pdf_queue.put((ph, pdf_bytes))

    # 6. Finalización
    pdf_queue.put(None) # Señal de fin
    consumer_thread.join()

    # Guardado Final
    save_checkpoint()

    t_total = time.time() - t_start
    print(f"\n=== RESUMEN DE LA CORRIDA ===")
    print(f"Tiempo total: {t_total:.1f}s ({t_total/60:.1f} min)")
    
    ok = sum(1 for r in results if r.get("status") == "OK")
    no_addr = sum(1 for r in results if r.get("status") == "no_address")
    vectores = sum(1 for r in results if r.get("metodo") == "Vectorial")
    ocrs = sum(1 for r in results if r.get("metodo") == "OCR Recorte")
    errores = len(results) - ok - no_addr
    
    print(f"Total en resultados: {len(results)}")
    print(f"  ✅ Con dirección: {ok}")
    print(f"  🤷 Sin dirección: {no_addr}")
    print(f"  ❌ Errores: {errores}")
    print(f"  ⚡ Vectores (Rápidos): {vectores}")
    print(f"  👁️  OCR (Procesados): {ocrs}")
    
    if total_pending > 0:
        print(f"Throughput de corrida: {total_pending/t_total:.2f} PDFs/s")

if __name__ == "__main__":
    main()
