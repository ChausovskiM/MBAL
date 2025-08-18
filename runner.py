import os
import sys
import shutil
from pathlib import Path
import importlib
from PIL import Image
import matplotlib.pyplot as plt

# --- режимы и базовые пути ---
FROZEN = getattr(sys, "frozen", False)
BASE_READ = Path(getattr(sys, "_MEIPASS", Path(__file__).parent.resolve()))  # где лежат ресурсы
APP_DIR  = Path(sys.executable).parent if FROZEN else Path(__file__).parent.resolve()

# В .exe пишем в отдельную папку, исходники не трогаем
OUT_DIR  = (APP_DIR / "run_data") if FROZEN else APP_DIR

# чтобы модули импортировались из пакета
if str(BASE_READ) not in sys.path:
    sys.path.insert(0, str(BASE_READ))

MODULES = [
    "code_sheets.PVT.pvt_controller",
    "code_sheets.KGF.kgf_controller",
    "code_sheets.PZ.pz_controller",
    "code_sheets.Components.components_controller",
    "code_sheets.GDI.gdi_controller",
    "code_sheets.Productivity.prod_controller",
    "code_sheets.Temperature.temperature_controller",
    "code_sheets.Base.base_controller",
]

GRAPH_FILES = {
    "code_sheets/PVT/pvt_graph.png": "PVT",
    "code_sheets/KGF/kgf_graph.png": "КГФ",
    "code_sheets/PZ/pz_graph.png": "Pz",
    "code_sheets/Components/components_graph.png": "Состав",
    "code_sheets/GDI/gdi_graph.png": "Обработка ГДИ",
    "code_sheets/Base/base_graph.png": "База",
}

# копируем только данные (не .py), и только в .exe
DATA_EXT = {".json", ".csv", ".xlsx", ".xls", ".parquet", ".txt", ".png", ".jpg", ".jpeg"}

def prepare_workdir():
    (OUT_DIR / "code_sheets").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "plots").mkdir(exist_ok=True)
    (OUT_DIR / "outputs").mkdir(exist_ok=True)
    os.environ["MBAL_OUT_DIR"] = str(OUT_DIR)

    if not FROZEN:
        # из исходников ничего не копируем, чтобы не трогать проект
        return

    src = BASE_READ / "code_sheets"
    dst = OUT_DIR   / "code_sheets"

    if not src.exists():
        print("[warn] В пакете нет папки 'code_sheets'")
        return

    for p in src.rglob("*"):
        rel = p.relative_to(src)
        target = dst / rel
        if p.is_dir():
            target.mkdir(exist_ok=True, parents=True)
        else:
            # копируем только данные, .py не трогаем
            if p.suffix.lower() in DATA_EXT:
                target.parent.mkdir(exist_ok=True, parents=True)
                shutil.copy2(p, target)

def run_controllers():
    old_cwd = Path.cwd()
    try:
        os.chdir(OUT_DIR)  # все относительные записи пойдут в run_data
        for name in MODULES:
            try:
                print(f"Running: {name}")
                mod = importlib.import_module(name)
                if hasattr(mod, "main"):
                    mod.main()
                else:
                    print(f"[skip] {name} не содержит main()")
            except Exception as e:
                print(f"[ERR] {name}: {e}")
    finally:
        os.chdir(old_cwd)

def show_graphs():
    shown = False
    for rel, title in GRAPH_FILES.items():
        path = OUT_DIR / rel
        if path.exists():
            try:
                img = Image.open(path)
                fig = plt.figure(num=title)
                plt.imshow(img)
                plt.axis("off")
                plt.title(title)
                plt.tight_layout()
                plt.show(block=False)
                shown = True
            except Exception as e:
                print(f"[img err] {path}: {e}")
        else:
            print(f"[miss] {path}")
    if shown:
        plt.show(block=True)

def main():
    print(f"[info] BASE_READ = {BASE_READ}")
    print(f"[info] OUT_DIR   = {OUT_DIR}")
    prepare_workdir()
    run_controllers()
    
    show_graphs()
    print("Все скрипты выполнены!")

if __name__ == "__main__":
    # подтягиваем либы, чтобы PyInstaller их включил
    try:
        import openpyxl
        import pandas  # noqa: F401
        import matplotlib  # noqa: F401
        import scipy  # noqa: F401
        import tkinter  # для окон Matplotlib (TkAgg)
    except Exception:
        pass
    main()
