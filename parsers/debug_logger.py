import os
from datetime import datetime

_log_path = None
_initialized = False

def _ensure_path():
    global _log_path, _initialized
    if _initialized:
        return _log_path
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)
    _log_path = os.path.join(log_dir, f'debug_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
    with open(_log_path, 'w', encoding='utf-8') as f:
        f.write(f"=== DEBUG LOG START {datetime.now().isoformat()} ===\n")
    _initialized = True
    return _log_path

def log(msg):
    """Write tagged debug message to physical log file on disk.
       Call alongside print() to persist output for post-execution analysis."""
    try:
        with open(_ensure_path(), 'a', encoding='utf-8') as f:
            f.write(f"{datetime.now().strftime('%H:%M:%S.%f')[:-3]} {msg}\n")
    except Exception:
        pass
