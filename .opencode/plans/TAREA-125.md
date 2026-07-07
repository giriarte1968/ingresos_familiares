# TAREA-125: Fix portfolio muestra manual duplicado + Guardrail RU-HEADER-03 + RU-PORTFOLIO-01 — Riesgo ALTO

## CONTEXTO

### Problema 1: Portfolio muestra valor manual dos veces
Tras el fix TAREA-122 (que setea `auto_valor_usd=0` al guardar manual) y TAREA-124, al ir a Portfolio las cards muestran el valor manual duplicado como si fuera "Comparables" y "Manual".

**Causa raíz:** `valu_portfolio2.py:_build_rows()` línea 361-362:
```python
if not auto_valor_usd:
    auto_valor_usd = valor  # fallback: main value is auto
```
TAREA-122 setea `auto_valor_usd=0` en UV. En `_cargar_resultados_cache` (línea 279), `valor_propiedad_usd` se sobreescribe con el valor manual. El fallback copia ese valor manual a `auto_valor_usd`. En `_render_cards` se muestran ambos con el mismo número.

### Problema 2: Falta guardrail RU-HEADER-03
No existe `_verificar_invariante_*` para el RU-HEADER-03 (header manual independiente de comparables).

## REGLA DE ORO

- `pytest` pasa después de cada paso
- Portfolio card NO muestra valor manual duplicado
- Cuando `fuente_activa='manual'` y no hay auto_valor, la card solo muestra Manual
- Guardrail detecta si `auto_valor_usd` fue contaminado con valor manual
- DEBUG flags rastrean decisiones

## ALCANCE

| Archivo | Cambio |
|---|---|
| `valu_portfolio2.py:361-362` | No fallback `auto_valor_usd = valor` si `fuente_activa='manual'` |
| `valu_portfolio2.py:595-599` | Si `auto_val==0` y hay manual, mostrar solo manual |
| `valu_portfolio2.py` | Nueva función `_verificar_invariante_portfolio_manual()` + llamado en `_build_rows` |
| `tests/test_regression.py` | Test guardrail + test portfolio manual único |
| `docs/BITACORA_AGENTES.md` | Nueva entrada |
| `.opencode/plans/TAREAS_INDEX.md` | Nueva entrada |

---

### PASO 1: Fix `_build_rows` — no contaminar auto_valor_usd con valor manual

**Archivo:** `valu_portfolio2.py` — función `_build_rows` (líneas 361-362)

**1.1** Cambiar la lógica de fallback para respetar `fuente_activa`:

```python
# ANTES:
        if not auto_valor_usd:
            auto_valor_usd = valor  # fallback: main value is auto

# DESPUES:
        if not auto_valor_usd:
            fuente_activa = ultima.get('fuente_activa', 'auto')
            if fuente_activa != 'manual':
                auto_valor_usd = valor  # fallback: main value is auto
            print(f"[DEBUG-PORTFOLIO-BUILD] {nombre}: auto_valor_usd={auto_valor_usd}, "
                  f"manual_valor_usd={manual_valor_usd}, fuente_activa={ultima.get('fuente_activa', 'auto')}, "
                  f"valor_base={valor}")
```

**COMMIT:** `"TAREA-125/paso1: _build_rows — no fallback auto_valor_usd desde valor cuando fuente_activa=manual"`

**VERIFICAR:** `pytest tests/test_regression.py`

---

### PASO 2: Fix `_render_cards` — no mostrar $0 cuando auto_val=0 y hay manual

**Archivo:** `valu_portfolio2.py` — función `_render_cards` (líneas 592-599)

**2.1** Cuando `auto_val==0` y `has_manual`, mostrar solo el valor manual:

```python
# ANTES:
                auto_val = float(row.get('auto_valor_usd', 0) or 0)
                manual_val = float(row.get('manual_valor_usd', 0) or 0)
                has_manual = manual_val > 0
                if has_manual:
                    price_block = f'''<div class="p2-price">{_fmt_usd(auto_val)} <span class="p2-price-label">Comparables</span></div>
<div class="p2-price" style="color:#006AFF;">{_fmt_usd(manual_val)} <span style="font-size:11px;font-weight:400;color:#006AFF;opacity:0.7;">Manual</span></div>'''
                else:
                    price_block = f'''<div class="p2-price">{_fmt_usd(auto_val)}</div>'''

# DESPUES:
                auto_val = float(row.get('auto_valor_usd', 0) or 0)
                manual_val = float(row.get('manual_valor_usd', 0) or 0)
                has_manual = manual_val > 0
                has_auto = auto_val > 0
                if has_manual and has_auto:
                    price_block = f'''<div class="p2-price">{_fmt_usd(auto_val)} <span class="p2-price-label">Comparables</span></div>
<div class="p2-price" style="color:#006AFF;">{_fmt_usd(manual_val)} <span style="font-size:11px;font-weight:400;color:#006AFF;opacity:0.7;">Manual</span></div>'''
                elif has_manual:
                    price_block = f'''<div class="p2-price" style="color:#006AFF;">{_fmt_usd(manual_val)} <span style="font-size:11px;font-weight:400;color:#006AFF;opacity:0.7;">Manual</span></div>'''
                elif has_auto:
                    price_block = f'''<div class="p2-price">{_fmt_usd(auto_val)}</div>'''
                else:
                    price_block = f'''<div class="p2-price">—</div>'''
```

**COMMIT:** `"TAREA-125/paso2: _render_cards — ocultar $0 cuando auto_val=0 y hay manual"`

**VERIFICAR:** `pytest tests/test_regression.py`

---

### PASO 3: Guardrail `_verificar_invariante_portfolio_manual` + tests

**Archivo:** `valu_portfolio2.py` — agregar función al final + llamado en `_build_rows`

**3.1** Agregar función guardrail:

```python
def _verificar_invariante_portfolio_manual(row: dict, nombre: str) -> bool:
    """
    RU-PORTFOLIO-01: Verifica que auto_valor_usd NO fue contaminado
    con el valor manual. Si fuente_activa='manual' y hay manual_params,
    auto_valor_usd debe ser 0 (no hay auto engine) o != manual_valor_usd.
    
    Returns:
        True si invariante se cumple.
        False si se detecto contaminacion.
    """
    auto_val = float(row.get('auto_valor_usd', 0) or 0)
    manual_val = float(row.get('manual_valor_usd', 0) or 0)
    valor = float(row.get('valor_usd', 0) or 0)
    fuente = row.get('fuente_activa', 'auto')
    
    if fuente == 'manual' and manual_val > 0 and auto_val > 0 and auto_val == manual_val:
        print(f"[GUARDRAIL-PORT-01] {nombre}: CONTAMINACION DETECTADA - "
              f"auto_valor_usd={auto_val} == manual_valor_usd={manual_val}. "
              f"RU-PORTFOLIO-01 violado. Valor={valor}, fuente={fuente}")
        return False
    return True
```

**3.2** Llamar guardrail al final de `_build_rows` (antes del append):

```python
                        if not _verificar_invariante_portfolio_manual(row_entry, nombre):
                            print(f"[GUARDRAIL-PORT-01] {nombre}: VIOLACION detectada en build_rows")
```

Donde `row_entry` es el dict antes de hacer append. O mejor, crear `row_entry` y verificar antes del append.

**3.3** Test del guardrail en `tests/test_regression.py`:

Test `test_portfolio_guardrail_detects_manual_contamination`: Verifica que el guardrail detecta auto_val==manual_val cuando fuente_activa='manual'.

Test `test_portfolio_guardrail_no_false_positive`: Verifica que no hay falso positivo con auto_val diferente.

**COMMIT:** `"TAREA-125/paso3: guardrail RU-PORTFOLIO-01 + tests"`

**VERIFICAR:** `pytest tests/test_regression.py`

---

### VALIDACION FINAL

```
☐ pytest tests/test_regression.py (22+ tests)
☐ python scripts/auto_validate.py
☐ Portfolio: card muestra solo "Manual" sin duplicado
☐ Portfolio: card muestra "Comparables" + "Manual" cuando ambos existen
☐ Portfolio: card muestra solo "Comparables" sin manual
☐ Guardrail detecta contaminación en tests
```

### DOCS A ACTUALIZAR

- `docs/BITACORA_AGENTES.md` — Nueva entrada TAREA-125
- `.opencode/plans/TAREAS_INDEX.md` — Agregar entrada TAREA-125
- `docs/STATUS_ACTUAL.md` — Actualizar estado

### ARCHIVO DE PLAN

Se guarda en `.opencode/plans/TAREA-125.md`. NO se elimina al ejecutar.
