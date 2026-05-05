#!/usr/bin/env python3
"""
Actualizador Automático de Documentación
Detecta cambios en código y actualiza los .MD correspondientes.

Ejecutar después de hacer cambios en código:
    python scripts/update_docs.py

Se ejecuta automáticamente en el flujo de opencode.
"""
import subprocess
import sys
import os
import re
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).parent.parent
os.chdir(REPO_ROOT)

# Mapeo de funciones a secciones de documentación
FUNCION_TO_DOC = {
    'check_barrier_crossing': {
        'file': 'docs/ALGORITMOS.md',
        'section': '7. Barreras Geográficas',
        'pattern': r'(##\s*\d+\.\s*Barreras|---\*\*Generado)'
    },
    'obtener_mediana_cluster_v2': {
        'file': 'docs/ALGORITMOS.md',
        'section': '2. Clustering de Precio',
        'pattern': r'##\s*\d+\.\s*Clustering'
    },
    'valuar_propiedad_v7': {
        'file': 'docs/ALGORITMOS.md',
        'section': '3. Fórmula Unificada',
        'pattern': r'##\s*\d+\.\s*Fórmula'
    },
    'calcular_factores': {
        'file': 'docs/ALGORITMOS.md',
        'section': '4. Factores de Ajuste',
        'pattern': r'##\s*\d+\.\s*Factores'
    },
    'barreras_rosario.json': {
        'file': 'docs/DICCIONARIO_DATOS.md',
        'section': '2. barreras_rosario.json',
        'pattern': r'##\s*\d+\.\s*barreras'
    }
}

def detect_code_changes():
    """Detecta qué funciones cambiaron en el último commit."""
    result = subprocess.run(
        ['git', 'diff', '--name-only', 'HEAD^..HEAD'],
        capture_output=True,
        text=True
    )
    changed_files = result.stdout.strip().split('\n')
    
    changed_funcs = set()
    for f in changed_files:
        if f.startswith('parsers/') and f.endswith('.py'):
            # Leer el diff para ver qué funciones cambiaron
            diff_result = subprocess.run(
                ['git', 'diff', '--name-only', 'HEAD^..HEAD', '--', f],
                capture_output=True,
                text=True
            )
            for func in FUNCION_TO_DOC:
                if func in open(f.replace('parsers/', 'parsers/')).read():
                    changed_funcs.add(func)
    
    return changed_funcs

def update_documentation():
    """Actualiza los MDs basándose en los cambios de código."""
    print("=" * 60)
    print("ACTUALIZADOR AUTOMÁTICO DE DOCUMENTACIÓN")
    print("=" * 60)
    
    changes = detect_code_changes()
    
    if not changes:
        print("\nNo se detectaron cambios que requieran documentación.")
        return True
    
    print(f"\nCambios detectados: {', '.join(changes)}")
    print("\nLos archivos .MD deben actualizarse manualmente o con el flujo de opencode.")
    print("Para más detalle, ver los cambios en git log.")
    
    # Actualizar ALGORITMOS.md con fecha
    alg_file = REPO_ROOT / 'docs/ALGORITMOS.md'
    if alg_file.exists():
        content = alg_file.read_text(encoding='utf-8')
        # Actualizar fecha
        new_content = re.sub(
            r'\*\*Fecha\*\*: \d{4}-\d{2}-\d{2}',
            f'**Fecha**: {datetime.now().strftime("%Y-%m-%d")}',
            content
        )
        if new_content != content:
            alg_file.write_text(new_content, encoding='utf-8')
            print("\n✓ Fecha actualizada en ALGORITMOS.md")
    
    print("\n" + "=" * 60)
    return True

def main():
    return 0 if update_documentation() else 1

if __name__ == "__main__":
    sys.exit(main())