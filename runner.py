import os
import sys
import subprocess
from pathlib import Path

# Определяем порядок выполнения скриптов
SCRIPTS_ORDER = [
    "code_sheets/PVT/pvt_controller_ilya.py",
    "code_sheets/KGF/kgf_controller_ilya.py",
    "code_sheets/PZ/pz_controller_ilya.py",
    "code_sheets/Components/components_controller_ilya.py",
    "code_sheets/GDI/gdi_controller_ilya.py",
    "code_sheets/Productivity/prod_controller_ilya.py",
    "code_sheets/Temperature/temperature_controller_ilya.py",
    "code_sheets/Base/base_controller_ilya.py",
]

def run_scripts():
    # Получаем корневую директорию проекта
    project_root = Path(__file__).parent.absolute()
    
    for script_path in SCRIPTS_ORDER:
        # Формируем полный путь к скрипту
        full_script_path = project_root / script_path
        
        # Проверяем существование файла
        if not full_script_path.exists():
            print(f"Error: file {full_script_path} not found!")
            continue
        
        print(f"Runn script: {script_path}")
        
        try:
            # Запускаем скрипт с помощью subprocess
            result = subprocess.run(
                [sys.executable, str(full_script_path)],
                cwd=project_root,  # Устанавливаем рабочую директорию
                check=True,
                capture_output=True,
                text=True
            )
            
            # Выводим вывод скрипта
            if result.stdout:
                print("Script output:")
                print(result.stdout)
                
        except subprocess.CalledProcessError as e:
            print(f"Error when executing the script {script_path}:")
            print(e.stderr)
            # Можно добавить break если нужно прервать выполнение при ошибке
            # break

if __name__ == "__main__":
    run_scripts()
    print("All scripts are executed!")