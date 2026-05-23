import os
import time
import json
import logging
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime

logger = logging.getLogger(__name__)

PROFILING_ENABLED = os.getenv("PROFILING_ENABLED", "false").lower() in ("true", "1", "yes")

_results = defaultdict(list)
_global_start = None

def reset():
    _results.clear()

def _get_prop_name(prop=None):
    if prop is None:
        return None
    if isinstance(prop, dict):
        return prop.get("nombre", prop.get("direccion", "?"))
    return str(prop)

@contextmanager
def profile_block(name, prop=None):
    if not PROFILING_ENABLED:
        yield
        return

    prop_name = _get_prop_name(prop)
    t0 = time.perf_counter()
    try:
        yield
    finally:
        dt = (time.perf_counter() - t0) * 1000
        prefix = f"[PROFILE][{prop_name}]" if prop_name else "[PROFILE]"
        logger.warning(f"{prefix} {name}: {dt:.1f} ms")
        _results[(prop_name or "global", name)].append({
            "t_ms": dt,
            "timestamp": datetime.now().isoformat(),
        })

def dump_results():
    if not _results:
        return {"profiling_enabled": PROFILING_ENABLED, "blocks": {}}
    aggregated = {}
    for (prop, block), entries in _results.items():
        times = [e["t_ms"] for e in entries]
        key = f"[{prop}] {block}" if prop else block
        aggregated[key] = {
            "count": len(times),
            "total_ms": round(sum(times), 1),
            "avg_ms": round(sum(times) / len(times), 1),
            "min_ms": round(min(times), 1),
            "max_ms": round(max(times), 1),
            "entries": entries[-5:],
        }
    return {
        "profiling_enabled": PROFILING_ENABLED,
        "total_blocks": len(_results),
        "blocks": aggregated,
    }

def profile_start(name, prop=None):
    """Start a manual profile timer. Returns a context dict for profile_end()."""
    if not PROFILING_ENABLED:
        return None
    return {"name": name, "prop": prop, "t0": time.perf_counter()}

def profile_end(ctx):
    """End a manual profile timer started with profile_start()."""
    if ctx is None:
        return
    dt = (time.perf_counter() - ctx["t0"]) * 1000
    prop_name = _get_prop_name(ctx.get("prop"))
    prefix = f"[PROFILE][{prop_name}]" if prop_name else "[PROFILE]"
    logger.warning(f"{prefix} {ctx['name']}: {dt:.1f} ms")
    _results[(prop_name or "global", ctx["name"])].append({
        "t_ms": dt,
        "timestamp": datetime.now().isoformat(),
    })

def save_results(path=None):
    data = dump_results()
    if path is None:
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "data",
            f"profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.warning(f"[PROFILE] Resultados guardados en {path}")
    return path
