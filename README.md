# Rosario Real Estate Analytics — Valu AVM

Sistema de valuación de propiedades en Rosario, Argentina. Utiliza modelos matemáticos de clustering, Selección Natural ($D \pm 1$), ajuste por barreras físicas y ponderación geográfica para determinar el valor de mercado.

## 🚀 Componentes Principales

### 1. Aplicación Valu (`valu.py`)
Interfaz principal del sistema:
- **UI & Dashboard**: Gestión de portafolio inmobiliario y visualización de valuación oficial.
- **Natural Selection ($D \pm 1$)**: Selección inteligente de comparables de 1, 2 y 3 dormitorios.
- **Navegación e Historial Estables**: Reingreso incondicional desde datos persistidos en disco (`propiedades.json`).
- **Exportación Dual PDF**: Descarga directa de PDF Estándar y **Reporte TTL** de 750 KB.

### 2. Motor de Valuación (`parsers/mercado_inmobiliario.py`)
Núcleo del motor AVM:
- **Factor de Escalera (`factor_escalera`)**: Ajuste físico para edificios sin ascensor (-15% en 2° piso).
- **Atributos Hedónicos & NLP**: Detección de terrazas de servicio (`terraza_servicio`), vistas y estado.
- **Geoweighting & Anclas**: Gradiente urbano por microzonas.

---

## 🛠️ Ejecución y Tests

### Ejecutar la Aplicación
```bash
streamlit run valu.py
```

### Ejecutar la Suite de Pruebas Automatizadas
```bash
pytest tests/test_regression.py tests/test_ui_state_machine.py
```

---

**Versión**: 3.4.0 | **Estado**: Estabilizado / Producción | **Última actualización**: 2026-08-14
