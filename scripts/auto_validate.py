#!/usr/bin/env python3
"""
Script de Validación Automática post-commit
Ejecutar después de cada cambio de código:
    python scripts/auto_validate.py

atau agregar como git hook:
    cp scripts/post-commit-hook .git/hooks/post-commit
    chmod +x .git/hooks/post-commit
"""
import subprocess
import sys
import os
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
os.chdir(REPO_ROOT)

def run_command(result, description):
    """Ejecuta comando y retorna success."""
    success = result.returncode == 0
    status = 'OK' if success else 'FAIL'
    print(f"\n[{status}] {description}")
    if not success:
        stderr = result.stderr.decode() if result.stderr else 'Sin output'
        print(f"  Error: {stderr[:200]}")
    return success

def main():
    print("=" * 60)
    print("VALIDACIÓN AUTOMÁTICA - Post Commit")
    print("=" * 60)

    all_passed = True

    # 1. Regression Tests
    print("\n[1] Ejecutando Regression Tests...")
    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_regression.py", "-v", "--tb=short"],
        capture_output=True
    )
    all_passed &= run_command(result, "Regression Tests")

    # 2. Verificar sintaxis Python
    print("\n[2] Verificando sintaxis Python...")
    for py_file in ["parsers/mercado_inmobiliario.py", "parsers/location_engine.py", "parsers/motor_vpp_core.py"]:
        result = subprocess.run([sys.executable, "-m", "py_compile", py_file])
        all_passed &= run_command(result, f"Sintaxis {py_file}")

    # 3. Verificar imports
    print("\n[3] Verificando imports...")
    result = subprocess.run([
        sys.executable, "-c",
        "from parsers.mercado_inmobiliario import valuar_propiedad_v7; from parsers.location_engine import check_barrier_crossing; print('OK')"
    ])
    all_passed &= run_command(result, "Imports principales")

    # Resumen
    print("\n" + "=" * 60)
    if all_passed:
        print("[OK] TODAS LAS VALIDACIONES PASARON")
        print("\nPara hacer push automatico a GitHub:")
        print("  git push origin main")
    else:
        print("[FAIL] HAY ERRORES - CORRIGE ANTES DE HACER PUSH")
    print("=" * 60)

    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())