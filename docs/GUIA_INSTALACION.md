# ⚙️ GUÍA DE INSTALACIÓN Y ENTORNO — AVM ROSARIO

Instrucciones para poner en marcha el sistema desde cero y entender sus dependencias externas.

---

## 1. Requisitos de Software
- **Python**: 3.10 o superior (recomendado 3.11).
- **Tesseract OCR**: Requerido para el procesamiento de imágenes/PDFs de pagos.
    - Windows: Instalar vía `vcpkg` o descargar el binario de UB Mannheim.
- **Poppler**: Requerido por `pdf2image`.

## 2. Instalación de Dependencias
```bash
pip install -r requirements.txt
```

### Librerías Críticas
- `streamlit`: Interfaz de usuario.
- `folium` / `streamlit-folium`: Mapas interactivos.
- `pytesseract`: Motor de OCR para facturas/recibos.
- `geopandas` / `shapely`: Cálculos geométricos y de barreras.
- `scikit-learn`: Usado para clustering DBSCAN.

## 3. Variables de Entorno y APIs
Actualmente el sistema funciona principalmente con scrapers y fuentes públicas, pero requiere:
- **Conexión a Internet**: Para consultar la cotización de Binance (USDT/ARS) en tiempo real.
- **Geocodificación**: Se usa Nominatim (OpenStreetMap) por defecto. No requiere KEY pero tiene límites de velocidad (rate-limit).

## 4. Estructura de Ejecución
Para iniciar la aplicación principal:
```bash
streamlit run app.py
```

Para correr los tests de regresión (Obligatorio antes de cada commit):
```bash
pytest tests/test_regression.py
```

---

## 5. Notas de Desarrollo en Windows
Si tienes errores con `fiona` o `geopandas` al instalar:
1. Intenta instalar `pyproj` y `shapely` por separado.
2. Asegúrate de tener las herramientas de compilación de C++ para Visual Studio instaladas.
