# 🏠 STATUS ACTUAL DEL PROYECTO — AVM Rosario (Valu)

*Actualizado: 14/08/2026 — Estabilización de Reingresos, Ponderación por Escalera y Reporte TTL*

---

## 1. RESUMEN EJECUTIVO

| Dimensión | Estado |
|-----------|--------|
| Motor Valuación v7 | ✅ Selección Natural ($D \pm 1$, 12 comps) / Exacto 2-Dorms (6 comps) |
| Factor Físico por Escalera | ✅ Penalización física (`factor_escalera = 0.85` en 2° piso sin ascensor) |
| Reporte TTL PDF | ✅ Generación y descarga directa Playwright de PDF 750 KB |
| Atributos Físicos Nuevos | ✅ Incorporado `tipo_balcon: "terraza_servicio"` para terrazas técnicas/tender |
| UI State Machine & Reingreso | ✅ Reingreso incondicional desde `_ultima_valuacion` (persistencia a medianoche) |
| Hashes Estables | ✅ `_get_comp_id` inmutable sin desplazamiento de checkbox por exclusión |
| Sincronización Retro/Flex | ✅ Sincronización exacta al aplicar sin desbordamiento de meses |
| Coordenadas cache scraping | ✅ Corregidas vía centroide catastral |
| Enriquecimiento años | ✅ 3-pasos (exacta ≤200m / token+bloque ≤30m / nearest+token+bloque ≤60m) |
| Tests regresión UI | ✅ **64/64 PASADOS (100% Verde)** |
| Anclas grilla 400m | ✅ 322 microzonas, 96% cobertura |

---

## 2. ESTADO DEL CACHE Y VALUACIONES

| Métrica | Cantidad / Estado |
|---------|-------------------|
| Propiedades en Portafolio | **Entre Ríos 1372 ($82,814 USD / 12 comps)**, Cochabamba 45, etc. |
| Cobertura Anclas | 322 microzonas (grilla 400m) |
| Algoritmo Selección | Natural Selection ($D \pm 1$) con fallback a exacto 2-Dorms |
| Exclusión Hedónica | Dinámica sobre array inmutable de comparables en session_state |

---

## 3. ARQUITECTURA ACTUAL

### Flujo de Valuación y Persistencia

```
propiedades.json → motor_vpp_core.valuar_con_cache()
    → necesita_recalcular() → valuar_propiedad_v7()
    → persistir_valuacion() [local]
        → atomic_write_json → data/valuaciones_cache.json
        → atomic_write_json → propiedades.json (_ultima_valuacion)
```

### Ciclo de Vida de UI y Reingreso

```
Portfolio → Click Tarjeta (?prop=Nombre)
    → valu.py detecta propiedad seleccionada
    → si _ultima_valuacion existe (ya_valuado == True):
        - Restaura incondicionalmente retro_dias, flex_dormitorios y valor USD
        - Muestra inmediatamente la Card Oficial y 12 comparables
        - Sin invalidación automática por fecha o medianoche
    → si usuario presiona "Limpiar":
        - Pasa a Estado PENDIENTE ("Sin Valor") hasta pulsar "Comparables" o "Aplicar"
```

---

## 4. COMPONENTES

| Archivo | Propósito |
|---------|-----------|
| `valu.py` | UI principal (Streamlit), router de navegación y portfolio |
| `valu_detail_sections.py` | Cards, tablas de comparables, sliders y botón "Reporte TTL" |
| `gen_pdf_ttl.py` | Generación y compilación de PDF Reporte TTL |
| `parsers/mercado_inmobiliario.py` | Motor AVM v7, cálculo de `factor_escalera` y razonamiento cualitativo |
| `valu_forms.py` | Formularios de carga con opciones de `tipo_balcon` (`terraza_servicio`) |
| `plantilla_propiedades.xlsx` | Excel maestro con los datos crudos y desplegables sincronizados |

---

## 5. VERIFICACIÓN

* **Comando:** `pytest tests/test_regression.py tests/test_ui_state_machine.py`
* **Resultado:** **64 passed, 0 failed**
