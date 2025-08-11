import os
import sys
import subprocess
from pathlib import Path
import platform

SCRIPTS_ORDER = [
    "code_sheets/PVT/pvt_controller.py",
    "code_sheets/KGF/kgf_controller.py",
    "code_sheets/PZ/pz_controller.py",
    "code_sheets/Components/components_controller.py",
    "code_sheets/GDI/gdi_controller.py",
    "code_sheets/Productivity/prod_controller.py",
    "code_sheets/Temperature/temperature_controller.py",
    "code_sheets/Base/base_controller.py",
]

def run_scripts():
    project_root = Path(__file__).parent.absolute()
    procs = []

    # Для Windows удобнее отвязать дочерние процессы от родителя,
    # чтобы GUI не закрывался при завершении лаунчера.
    creationflags = 0
    if platform.system() == "Windows":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP  # не блокируем консоль

    for script_path in SCRIPTS_ORDER:
        full_script_path = project_root / script_path
        if not full_script_path.exists():
            print(f"Error: file {full_script_path} not found!")
            continue

        print(f"Run script: {script_path}")
        try:
            # Не захватываем stdout/stderr, чтобы не забивать буферы
            p = subprocess.Popen(
                [sys.executable, str(full_script_path)],
                cwd=project_root,
                creationflags=creationflags,
                close_fds=False
            )
            procs.append((script_path, p.pid))
            print(f"  -> started PID {p.pid}")
        except Exception as e:
            print(f"Error when starting {script_path}: {e}")

    print("\nAll scripts started. You can switch between their figure windows.")
    print("PIDs:", procs)

if __name__ == "__main__":
    run_scripts()
