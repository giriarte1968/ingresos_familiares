#!/usr/bin/env python3
"""
Actualizador Automático de Documentación v2
Detecta cambios en funciones clave y actualiza docs/ALGORITMOS.md automáticamente.

Ejemplo de uso:
    python scripts/update_docs.py --auto  # Actualiza automáticamente
    python scripts/update_docs.py      # Solo detecta cambios
"""
import subprocess
import sys
import os
import re
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).parent.parent
os.chdir(REPO_ROOT)

# Mapeo: función → qué section de docs actualizar
FUNC_UPDATE_RULES = {
    'check_barrier_crossing': {
        'doc': 'docs/ALGORITMOS.md',
        'section': '7',
        'title': 'Barreras Geográficas (Rosario)',
        'content_template': """## 7. Barreras Geográficas (Rosario)

### Tipología de Barreras
| Tipo | Ejemplos | Comportamiento | Peso en IDW |
| :--- | :--- | :--- | :--- |
| **DURA** | Ferrocarril FC Mitre, Circunvalación | Exclusión total | weight *= 0.20 (80% penalty) |
| **BLANDA** | Av. Pellegrini, Av. 27 de Febrero, Av. Oroño, Av. Francia | Fricción (no exclusión) | weight *= 0.90 (10% penalty) |

### Lógica de Implementación
- `check_barrier_crossing()` retorna: `'hard'`, `'soft'` o `False`
- **En Cluster (obtener_mediana_cluster_v2)**: Solo excluye barreras DURAS
- **En IDW (calcular_precio_m2)**: Aplica penalty según tipo

### Justificación
En Rosario, las grandes avenidas son una "fricción" pero no un "corte"."""
    },
    'obtener_mediana_cluster_v2': {
        'doc': 'docs/ALGORITMOS.md',
        'section': '2',
        'title': 'Clustering de Precio',
    },
    'valuar_propiedad_v7': {
        'doc': 'docs/ALGORITMOS.md',
        'section': '3',
        'title': 'Fórmula Unificada',
    },
    # Status y Bitácora se actualizan con cambios generales
    '_general': {
        'doc': 'docs/STATUS_ACTUAL.md',
        'auto_update': True,
    },
    '_bitacora': {
        'doc': 'docs/BITACORA_AGENTES.md',
        'auto_update': True,
    }
}
}

def get_git_diff():
    """Obtiene el diff del último commit."""
    result = subprocess.run(
        ['git', 'diff', '--name-only', 'HEAD^..HEAD'],
        capture_output=True, text=True
    )
    return result.stdout.strip().split('\n')

def get_file_diff(filepath):
    """Obtiene el diff de un archivo específico."""
    result = subprocess.run(
        ['git', 'diff', 'HEAD^..HEAD', '--', filepath],
        capture_output=True, text=True
    )
    return result.stdout

def detect_changed_functions():
    """Detecta qué funciones cambiaron en el último commit."""
    changed_files = get_git_diff()
    
    changed_funcs = set()
    for f in changed_files:
        if f.startswith('parsers/') and f.endswith('.py'):
            diff = get_file_diff(f)
            for func in FUNC_UPDATE_RULES:
                if f'def {func}' in diff or f'class {func}' in diff:
                    changed_funcs.add(func)
    
    return changed_funcs

def update_algoritmos_section(func_name, rules):
    """Actualiza una sección de ALGORITMOS.md."""
    doc_path = REPO_ROOT / rules['doc']
    if not doc_path.exists():
        print(f"[WARN] {doc_path} no existe")
        return False
    
    content = doc_path.read_text(encoding='utf-8')
    
    # Generar nueva sección
    section_num = rules['section']
    title = rules.get('title', '')
    new_content = rules.get('content_template', f'## {section_num}. {title}\n\n*(Actualizado automáticamente)')
    
    # Verificar si la sección ya existe
    section_pattern = f'## {section_num}\\.'
    if section_pattern in content:
        # Reemplazar sección existente
        # Encontrar inicio de sección
        lines = content.split('\n')
        start_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith(section_pattern):
                start_idx = i
                break
        
        if start_idx is not None:
            # Encontrar fin (próxima sección ##)
            end_idx = None
            for i in range(start_idx + 1, len(lines)):
                if lines[i].strip().startswith('## '):
                    end_idx = i
                    break
            
            if end_idx is not None:
                lines[start_idx:end_idx] = new_content.split('\n')
                new_full = '\n'.join(lines)
            else:
                new_full = content + '\n\n' + new_content
        else:
            new_full = content + '\n\n' + new_content
    else:
        # Agregar al final
        new_full = content + '\n\n' + new_content
    
    doc_path.write_text(new_full, encoding='utf-8')
    return True

def main(auto=False):
    print("=" * 60)
    print("ACTUALIZADOR DE DOCUMENTACION")
    print("=" * 60)
    
    changed_funcs = detect_changed_functions()
    
    if not changed_funcs:
        print("\nNo hay cambios detectados en funciones clave.")
        return 0
    
    print(f"\nFunciones cambiadas: {', '.join(changed_funcs)}")
    
    if not auto:
        print("\nEjecutar con --auto para actualizar docs automáticamente")
        return 0
    
    # Actualizar docs
    print("\nActualizando documentación...")
    for func in changed_funcs:
        if func in FUNC_UPDATE_RULES:
            rules = FUNC_UPDATE_RULES[func]
            if update_algoritmos_section(func, rules):
                print(f"[OK] {func} -> {rules['doc']}")
            else:
                print(f"[FAIL] {func}")
        else:
            print(f"[SKIP] {func} sin regra")
    
    # Actualizar fecha
    alg_file = REPO_ROOT / 'docs/ALGORITMOS.md'
    if alg_file.exists():
        content = alg_file.read_text(encoding='utf-8')
        new_content = re.sub(
            r'\*\*Fecha\*\*: \d{4}-\d{2}-\d{2}',
            f'**Fecha**: {datetime.now().strftime("%Y-%m-%d")}',
            content
        )
        if new_content != content:
            alg_file.write_text(new_content, encoding='utf-8')
            print("[OK] Fecha actualizada")
    
    print("\n" + "=" * 60)
    print("Documentación actualizada!")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    auto = '--auto' in sys.argv
    sys.exit(main(auto))