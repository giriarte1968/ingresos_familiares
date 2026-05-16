# Rosario Real Estate Analytics - Motor VPP

Sistema avanzado de scraping y valuación de propiedades en Rosario, Argentina. Utiliza modelos matemáticos de clustering y ponderación geográfica para determinar el valor real de mercado y rentabilidad de activos inmobiliarios.

## 🚀 Componentes Principales

### 1. Aplicación Valu (Nueva Interfaz)
El punto de entrada principal para la gestión inmobiliaria es `valu.py`:
- **Zillow-inspired UI**: Interfaz de clase mundial con diseño moderno y minimalista.
- **Valuation Insights**: Razonamiento detallado de los factores que componen la valuación.
- **Inventario & Seguimiento**: Control de fechas de publicación y seguimiento de activos.

### 2. Motor de Valuación (VPP)
El núcleo del sistema reside en `parsers/mercado_inmobiliario.py`:
- **Clustering IQR**: Elimina ruido estadístico de las muestras.
- **Geoweighting (IDW)**: Da más peso a las propiedades físicamente más cercanas.
- **Dual Anchor Mode**: Combina señales del mercado en tiempo real con anclas estructurales de la zona.

### 3. Scraping Engine
Sistema de recolección de datos distribuido:
- `buscar_inmobiliarias.py`: Descubrimiento de fuentes directas.
- `cache_scraping.json`: Base de datos local de miles de muestras.

---

## 🛠️ Instalación y Uso

### Ejecución
Para iniciar la aplicación principal (**Valu**):
```bash
streamlit run valu.py
```

Para acceder a la versión anterior o gestión financiera (**Legacy**):
```bash
streamlit run app.py
```

## 📊 Documentación Detallada
Toda la documentación técnica se encuentra en el directorio [docs/](docs/):
- **[STATUS_ACTUAL.md](docs/STATUS_ACTUAL.md)**: Resumen del estado del proyecto.
- **[ALGORITMOS.md](docs/ALGORITMOS.md)**: Explicación de Clustering, IDW y fórmulas de valuación.

---
**Versión**: 3.1.0 | **Estado**: Activo / Producción | **Última actualización**: 2026-04-27
