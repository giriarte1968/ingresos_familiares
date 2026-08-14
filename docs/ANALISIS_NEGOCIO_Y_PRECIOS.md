# 📊 Análisis de Negocio, Mercado y Estrategia de Precios — Valu

**Fecha de actualización:** 14 de Agosto, 2026  
**Mercado Objetivo:** Rosario, Santa Fe (y expansión Argentina / LATAM)  
**Producto:** Valu / Reporte TTL — Engine AVM (Automated Valuation Model) Data-Driven  

---

## 1. Resumen Ejecutivo

El presente documento analiza la oportunidad de mercado, la estructura de costos tradicionales y la estrategia de precios óptima para monetizar la plataforma **Valu**.

Valu es una solución AVM (*Automated Valuation Model*) que procesa datos de oferta del mercado inmobiliario, aplica algoritmos de clustering espacial (microzonas a 300m), ajustes hedónicos físicos (piso, escalera, orientación, tipo de balcón/terraza) y ventanas de ajuste temporal (*Retro*), produciendo reportes ejecutivos en PDF de 6 páginas en 2 minutos.

---

## 2. Marco de Referencia: Tasaciones Tradicionales (Rosario y Argentina)

En la provincia de Santa Fe (Rosario), las tasaciones físicas/presenciales realizadas por corredores inmobiliarios matriculados en **COCIR** se arancelan según el **1/000 (uno por mil)** del valor del inmueble, con aranceles mínimos fijados en unidades **JUS** (Corte Suprema de Justicia de Santa Fe):

| Tipo de Tasación | Arancel Sugerido (COCIR) | Importe Estimado (ARS) | Importe Estimado (USD) |
| :--- | :---: | :---: | :---: |
| **Tasación Informativa de Vivienda** | **1 JUS** | ~$139.000 ARS | **USD 85 - USD 90** |
| **Tasación Técnica Formal / Pericial** | **2 JUS** | ~$278.000 ARS | **USD 175 - USD 180** |
| **Tasación Comercial / Campos** | **4 JUS** | ~$556.000 ARS | **USD 350 - USD 360** |
| **Tasación de Captación Inmobiliaria** | "Sin Cargo" (sujeta a contrato de exclusiva) | $0 ARS | $0 USD |

---

## 3. Benchmarks de Mercado (Nacional e Internacional)

### A. Argentina (B2C & B2B)
* **Portales Mass Market (Gratis):** ZonaProp, Mercado Libre, Properati. Ofrecen valuaciones automáticas orientativas gratuitas a cambio del lead (datos de contacto) del propietario para derivarlo a inmobiliarias sponsors.
* **Reporte Inmobiliario (Market Valuation):** Suscripciones profesionales de **$35.000 a $90.000 ARS/mes** (~USD 25 a USD 60/mes) para acceso a mapas de m² y datos de mercado. Consultas individuales vía API: **USD 5 a USD 15 por reporte**.
* **Informes Periciales Digitales:** Empresas especializadas cobran entre **$40.000 y $80.000 ARS** (~USD 25 a USD 50) por tasaciones digitales firmadas por martilleros.

### B. Internacional (EE. UU., Europa y LATAM)
* **Estados Unidos (HouseCanary / Zillow / Bowery):**
  * Reporte AVM individual descargable en PDF (B2C): **$29 a $49 USD**.
  * Suscripción SaaS para Brokers/Agentes (B2B): **$150 a $500 USD/mes**.
  * Tasación Física Bancaria (*Appraisal*): **$450 a $650 USD**.
* **España (Tinsa / ValoracionOnline):**
  * Pre-tasación AVM digital en PDF: **12 € a 25 €**.
  * Tasación oficial regulada ECO para hipotecas: **250 € a 450 €**.

---

## 4. Estrategia de Precios y Modelos de Monetización para **Valu**

Se recomienda estructurar la oferta comercial de Valu en **3 Líneas de Monetización**:

```
                               ┌────────────────────────────────────────┐
                               │   Estructura de Monetización Valu     │
                               └───────────────────┬────────────────────┘
                                                   │
         ┌─────────────────────────────────────────┼─────────────────────────────────────────┐
         │                                         │                                         │
┌────────┴────────┐                       ┌────────┴────────┐                       ┌────────┴────────┐
│  1. B2C Pay-Per-│                       │  2. B2B Suscrip-│                       │ 3. B2B Enterprise│
│     Report      │                       │     ción SaaS   │                       │      / API      │
├─────────────────┤                       ├─────────────────┤                       ├─────────────────┤
│ USD 12 - 18 /   │                       │ USD 25 - 100 /  │                       │ USD 1.0 - 2.5 / │
│ informe PDF     │                       │ mes (Plan Pro)  │                       │ consulta API    │
└─────────────────┘                       └─────────────────┘                       └─────────────────┘
```

### Alternativa 1: Pago por Informe Individual (B2C)
* **Público:** Propietarios particulares (FSBO), compradores/inversores evaluando contraofertas, familias dividiendo bienes.
* **Precio:** **$20.000 a $30.000 ARS** (~**USD 12 a USD 18**) por reporte descargable.
* **Ventaja:** Cuesta menos del 20% de una tasación presencial de 1 JUS (~$139.000 ARS), pero entrega un informe en PDF de 6 páginas con aval de datos de microzona.

### Alternativa 2: Suscripción Mensual B2B para Inmobiliarias y Corredores
* **Público:** Corredores inmobiliarios matriculados (COCIR Rosario / CUCICBA).
* **Esquema de Planes:**
  * **Plan Starter (5 tasaciones/mes):** **$35.000 ARS/mes** (~USD 22/mes).
  * **Plan Inmobiliaria Pro (25 tasaciones/mes + Logo/Branding de la Inmobiliaria):** **$85.000 ARS/mes** (~USD 55/mes).
  * **Plan Brokerage Ilimitado:** **$160.000 ARS/mes** (~USD 100/mes).

### Alternativa 3: API Enterprise (Bancos, Fintechs, Fondos de Inversión)
* **Público:** Bancos otorgando créditos hipotecarios, desarrolladoras analizando factibilidad de suelos y fondos de inversión.
* **Precio:** **USD 1.0 a USD 2.5 por llamada a la API** (o abonos anuales de USD 1.200 a USD 3.000).

---

## 5. Análisis del ROI para la Inmobiliaria (Workflow & Eficiencia)

### El Proceso Profesional Real
1. **Visita Física (15-20 min):** El corredor matriculado acude al inmueble a verificar estado de conservación, distribución y documentación (la firma y responsabilidad legal siguen siendo 100% del corredor).
2. **Carga en Valu (2 min):** Al retornar a la oficina, el corredor ingresa los datos constatados en Valu.
3. **Generación Instantánea:** Valu procesa los 16 comparables de la microzona, los coeficientes de piso/escalera/balcón y produce el Reporte PDF membretado.

### Retorno de Inversión (ROI)
* **Ahorro de Tiempo:** Pasa de 3 horas de trabajo administrativo manual en Excel/Word a **2 minutos**.
* **Retorno Financiero:** Cobrando una sola tasación por escrito a 0.5 JUS (~$70.000 ARS), el corredor **paga el 100% de la suscripción mensual de Valu** y libera su agenda para captar clientes y cerrar ventas.
* **Efecto Captación (Win Rate):** Presentar un informe de 6 páginas sustentado con datos científicos le permite a la inmobiliaria **ganar contratos de venta en exclusiva** frente a competidores que tasan "a ojo".

---

## 6. Funcionalidades Clave de Diferenciación (Roadmap de Producto)

1. **Evolución Histórica de Precios y Plusvalía:** Inclusión de gráficos SVG vectoriales en el PDF con la serie temporal del $/m² en la microzona de los últimos 36 meses.
2. **Personalización de Marca Blanca:** Inclusión automática del logo, datos de matrícula y color institucional de la inmobiliaria en la portada del PDF.
3. **Métricas de Inversión Integradas:** Cálculo automático de Alquiler Estimado (ARS / USD) y *Cap Rate* anual (%), clave para inversores de renta.
