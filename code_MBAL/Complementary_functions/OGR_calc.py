"""Расчёт конденсатогазового фактора по выбранной зависимости."""

import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from code_MBAL.Complementary_functions.OGR_tab1 import OGR_tab1
from code_MBAL.common.paths import runtime_path


@lru_cache(maxsize=16)
def _load_json(path, modified_ns):
    """Читает JSON один раз для каждой версии файла."""
    del modified_ns  # Значение входит в ключ кеша и обновляет его после перезаписи.
    with Path(path).open(encoding="utf-8") as stream:
        return json.load(stream)


def _kgf_json(filename):
    path = runtime_path("code_sheets", "KGF", filename).resolve()
    return _load_json(str(path), path.stat().st_mtime_ns)


def OGR_calc(Metod, P_MPA, pressure_data=None, ogr_data=None):
    """Возвращает КГФ, г/м³, для текущего давления в МПа."""
    pressure = float(P_MPA)
    if pressure <= 0:
        return 0.0

    metod = Metod.strip()
    if metod == "experimental data":
        outputs = _kgf_json("kgf_output.json")
        inputs = _kgf_json("kgf_experimental_input.json")
        pnk = float(inputs["Pnk"])
        if pressure > pnk:
            return float(outputs["C5_plus"])
        return float(np.polyval(outputs["coeff_experiment"], pressure))

    if metod == "typical dependence":
        outputs = _kgf_json("kgf_output.json")
        inputs = _kgf_json("kgf_typical_input.json")
        pnk = float(inputs["Pnk"])
        if pressure > pnk:
            return float(inputs["KGF"])
        return float(np.polyval(outputs["coef_type"], pressure))

    if metod == "table data":
        if pressure_data is None or ogr_data is None:
            raise ValueError("Не переданы pressure_data и ogr_data для табличного КГФ")
        return OGR_tab1(pressure, pressure_data, ogr_data)

    if metod == "gas field":
        return 0.0

    raise ValueError(f"Unknown method calculated KGF: '{Metod}'")
