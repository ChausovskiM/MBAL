"""Единые пути к пользовательским данным для исходников и frozen-сборки."""

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_runtime_root():
    """Возвращает каталог входов/выходов текущего запуска.

    Runner задаёт ``MBAL_OUT_DIR`` перед запуском контроллеров. Значение
    читается при каждом вызове, потому что PyInstaller импортирует контроллеры
    раньше, чем создаётся пользовательский каталог ``run_data``.
    """
    configured = os.environ.get("MBAL_OUT_DIR")
    return Path(configured).resolve() if configured else PROJECT_ROOT


def runtime_path(*parts):
    """Строит путь внутри каталога данных текущего запуска."""
    return get_runtime_root().joinpath(*parts)
