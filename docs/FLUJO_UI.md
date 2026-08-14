# Flujo UI & Maquina de Estados — Valu

Documentación del flujo de navegación y máquina de estados en la aplicación Valu (`valu.py`).

---

## 1. FLUJO DE NAVEGACIÓN Y REINGRESO

```
[Portfolio / Navegación]
    │ Click en Tarjeta (?prop=Nombre)
    ▼
[valu.py router]
    │ Lee propiedad desde propiedades.json
    │
    ├── ¿ya_valuado == True? (_ultima_valuacion en disco)
    │     ├── SÍ → Restaura parámetros de _ultima_valuacion (retro_dias, flex_dormitorios)
    │     │        Limpia pendientes espurios (pop pendiente_comparables_)
    │     │        Usa cache o resultado oficial grabado sin caducidad diaria
    │     │        Muestra Header Card ($82,814 USD) y 12 comparables
    │     │
    │     └── NO (Estado Post-Limpiar)
    │            → Muestra "Sin Valor / Presione Comparables para iniciar"
    │            → Al presionar "📊 Comparables" o "✅ Aplicar", genera/comitea valuación
```

---

## 2. REGLAS DE PERSISTENCIA Y CONSISTENCIA

1. **Reingreso Incondicional:**  
   Al entrar o reingresar a una propiedad previamente valuada, el motor lee de forma pasiva desde `propiedades.json`. No pierde la valuación al cambiar la fecha del sistema ni al expirar la sesión.
2. **Hashes Estables de Comparables:**  
   La casilla de exclusión de comparables genera claves estables basadas exclusivamente en atributos del comparable (`c.get('id')` o precio/m2/lat/lon). Ningún checkbox se desmarca ni se desplaza al desmarcar otro elemento de la lista.
3. **Reporte TTL:**  
   En la sección `⚡ Acciones`, se dispone del botón contiguous **🏠 Reporte TTL** que compila y ofrece la descarga directa del informe en formato PDF.
