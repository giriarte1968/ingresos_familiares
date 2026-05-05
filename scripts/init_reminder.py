# Recordatorios de Configuración - AGENTS.md

## Flujo Obligatorio Después de Cada Cambio

```
1. python scripts/auto_validate.py
   ↓
[OK] → git add . && git commit -m "..." && git push origin main
[FAIL] → Corregir errores antes de commit
```

## Archivos .MD a Mantener Sincronizados

| Archivo | Cuando Actualizar |
|---------|-------------------|
| **ALGORITMOS.md** | Cambios en lógica de valuación |
| **DICCIONARIO_DATOS.md** | Nuevos campos o fuentes de datos |
| **MEMORIA_PROYECTO.md** | Cambios en arquitectura |
| **STATUS_ACTUAL.md** | Cambios de estado del proyecto |
| **BITACORA_AGENTES.md** | Decisiones técnicas importantes |

## Validación Automática

```bash
# Ejecutar después de cada cambio de código:
python scripts/auto_validate.py

# Para actualizar docs (opcional después de validar):
python scripts/update_docs.py --auto
```

## Notas Importantes

- **Antiguo sistema de reglas**: Las Reglas de Oro están en MEMORIA_PROYECTO.md
- **No cambiar lógica de valuación** sin impactar docs correspondientes
- Todos los tests deben pasar ANTES de hacer push a GitHub

## Cambios Recientes (2026-05)

- Barreras diferenciadas: hard (weight=0.20), soft (weight=0.90)
- Fecha dinámica por defecto en valuar_propiedad_v7
- Ventana móvil de 180 días en clusters

---

*Para recordatorio: ejecutar este script al iniciar sesión*