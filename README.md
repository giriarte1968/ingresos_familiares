# Rosario Real Estate Analytics - Motor VPP

Sistema avanzado de scraping y valuación de propiedades en Rosario, Argentina. Utiliza modelos matemáticos de clustering y ponderación geográfica para determinar el valor real de mercado y rentabilidad de activos inmobiliarios.

## 🚀 Componentes Principales

### 1. Motor de Valuación (VPP)
El núcleo del sistema reside en `parsers/mercado_inmobiliario.py` y `parsers/motor_vpp_core.py`:
- **Clustering IQR**: Elimina ruido estadístico de las muestras.
- **Geoweighting (IDW)**: Da más peso a las propiedades físicamente más cercanas.
- **Dual Anchor Mode**: Combina señales del mercado en tiempo real con anclas estructurales de la zona.

### 2. Scraping Engine
Sistema de recolección de datos distribuido:
- `buscar_inmobiliarias.py`: Descubrimiento de fuentes directas.
- `cache_scraping.json`: Base de datos local de miles de muestras del mercado de Rosario.

### 3. Analítica de Alquileres & ROI
- Estimación de renta mensual basada en mercado local y anclas algorítmicas.
- Cálculo de ROI (Cap Rate) utilizando cotización de **Dólar Binance** (USDT/ARS).

## 🛠️ Instalación y Uso

### Requisitos
- Python 3.11+
- Ver `requirements.txt` para dependencias de Python.

### Ejecución
Para iniciar la interfaz de usuario (Streamlit):
```bash
streamlit run app.py
```

## 📊 Documentación Detallada
Toda la documentación técnica se encuentra en el directorio [docs/](docs/):
- **[STATUS_ACTUAL.md](docs/STATUS_ACTUAL.md)**: Resumen del estado del proyecto.
- **[ALGORITMOS.md](docs/ALGORITMOS.md)**: Explicación de Clustering, IDW y fórmulas de valuación.

---
**Versión**: 3.1.0 | **Estado**: Activo / Producción | **Última actualización**: 2026-04-27
