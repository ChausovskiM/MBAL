"""Общие маршрутизация и расчёт моделей притока газа."""

import math

from code_MBAL.Q_MOD.fQ import fQ
from code_MBAL.Q_MOD.fQLd import fQLd


PRESSURE_SQUARED = "pressure_squared"
PSEUDOPRESSURE = "pseudopressure"


def normalize_inflow_model(value):
    """Приводит названия из Excel/JSON к двум поддерживаемым моделям."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Не задана методика расчёта дебита")
    normalized = value.strip().casefold().replace("ё", "е")
    if normalized in {
        PRESSURE_SQUARED,
        "typical dependence",
        "типовая зависимость",
        "давление в квадрате",
    }:
        return PRESSURE_SQUARED
    if normalized in {
        PSEUDOPRESSURE,
        "pseudo pressure",
        "pseudo-pressure",
        "псевдодавление",
        "через псевдодавление",
    }:
        return PSEUDOPRESSURE
    raise ValueError(f"Неизвестная методика расчёта дебита: {value!r}")


def calculate_inflow_rate(
    model, a, b, reservoir_pressure_mpa, bottomhole_pressure_mpa,
    mobility_lambda=0.0,
):
    """Возвращает дебит одной скважины, тыс. м³/сут."""
    normalized = normalize_inflow_model(model)
    values = {
        "a": a,
        "b": b,
        "reservoir_pressure_mpa": reservoir_pressure_mpa,
        "bottomhole_pressure_mpa": bottomhole_pressure_mpa,
        "mobility_lambda": mobility_lambda,
    }
    normalized_values = {}
    for field, value in values.items():
        if isinstance(value, bool):
            raise ValueError(f"{field} должен быть числом")
        try:
            number = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{field} должен быть числом") from error
        if not math.isfinite(number):
            raise ValueError(f"{field} должен быть конечным числом")
        normalized_values[field] = number

    a = normalized_values["a"]
    b = normalized_values["b"]
    reservoir_pressure_mpa = normalized_values["reservoir_pressure_mpa"]
    bottomhole_pressure_mpa = normalized_values["bottomhole_pressure_mpa"]
    mobility_lambda = normalized_values["mobility_lambda"]
    if a <= 0:
        raise ValueError("a должен быть больше нуля")
    if b < 0:
        raise ValueError("b не может быть отрицательным")
    if reservoir_pressure_mpa < 0 or bottomhole_pressure_mpa < 0:
        raise ValueError("Давление не может быть отрицательным")
    if mobility_lambda < 0:
        raise ValueError("mobility_lambda не может быть отрицательной")

    if normalized == PRESSURE_SQUARED:
        result = fQ(a, b, reservoir_pressure_mpa, bottomhole_pressure_mpa)
    else:
        result = fQLd(
            a, b, mobility_lambda,
            reservoir_pressure_mpa, bottomhole_pressure_mpa,
        )
    if not math.isfinite(result) or result < 0:
        raise ValueError("Расчёт притока вернул некорректный дебит")
    return result
