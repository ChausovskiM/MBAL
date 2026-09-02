"""Помесячный и годовой сводный отчёт по результатам листа «База»."""

import json
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from code_MBAL.Complementary_functions.save_figure import save_figure
from code_MBAL.common.paths import runtime_path


CONTRIBUTIONS = {
    "vns": "ВНС",
    "frac": "ГРП",
    "gtm": "Прочие ГТМ",
    "zbs": "ЗБС",
    "pvlg": "ПВЛГ",
    "rs": "РС",
    "vbd": "ВБД",
    "periodic": "Периодическая эксплуатация",
}

REQUIRED_COLUMNS = {
    "date", "len_report_period", "Qgas_base_fond", "Qcond_base_fond",
    "Qgas_all", "Qcond_all", "rab_fond_on_end_period", "leave_base_fond",
    "dP", "Pust", "Ppl_on_start_period", "Ppl_on_end_period", "Pzab",
    "Qcum_gas_end_period", "Qcum_cond_end_period", "oiz_gas", "oiz_cond",
    "SPBT_t_t", "SPBT_m_m3",
}


def _dates(values):
    """Читает как ISO-даты, так и миллисекунды pandas JSON."""
    numeric = pd.to_numeric(values, errors="coerce")
    if numeric.notna().all():
        return pd.to_datetime(numeric, unit="ms")
    return pd.to_datetime(values, errors="raise")


def _safe_ratio(numerator, denominator):
    numerator = np.asarray(numerator, dtype=float)
    denominator = np.asarray(denominator, dtype=float)
    return np.divide(
        numerator,
        denominator,
        out=np.zeros_like(numerator, dtype=float),
        where=denominator != 0,
    )


def _optional_numeric(frame, column, default=0.0):
    if column not in frame:
        return pd.Series(default, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce").fillna(default)


def build_summary(base_frame, condensate_density_kgm3):
    """Формирует таблицы сводного отчёта из помесячного расчёта «Базы»."""
    if condensate_density_kgm3 <= 0:
        raise ValueError("Плотность конденсата должна быть больше нуля")

    missing = sorted(REQUIRED_COLUMNS.difference(base_frame.columns))
    if missing:
        raise ValueError(f"В результате Базы отсутствуют колонки: {', '.join(missing)}")

    source = base_frame.copy()
    source["date"] = _dates(source["date"])
    source = source.sort_values("date").reset_index(drop=True)
    for column in REQUIRED_COLUMNS.difference({"date"}):
        source[column] = pd.to_numeric(source[column], errors="coerce").fillna(0.0)

    periodic_active = _optional_numeric(source, "periodic_active_wells")
    periodic_retired = _optional_numeric(source, "periodic_wells_retired")
    periodic_dp = _optional_numeric(source, "periodic_dP")
    periodic_pust = _optional_numeric(source, "periodic_Pust")
    if "operation_status" in source:
        base_operating = (
            source["operation_status"].eq("работает")
            & source["rab_fond_on_end_period"].gt(0)
        ).astype(float)
    else:
        base_operating = source["rab_fond_on_end_period"].gt(0).astype(float)
    periodic_operating = periodic_active.gt(0).astype(float)
    operating_group_count = base_operating + periodic_operating
    available_wells = source["rab_fond_on_end_period"] + periodic_active
    active_wells = source["rab_fond_on_end_period"] * base_operating + periodic_active
    if "mean_rab_basefond" in source:
        base_operating_well_days = (
            _optional_numeric(source, "mean_rab_basefond")
            * source["len_report_period"] * base_operating
        )
    else:
        base_operating_well_days = (
            source["rab_fond_on_end_period"]
            * source["len_report_period"] * base_operating
        )
    if "periodic_active_well_days" in source:
        periodic_operating_well_days = _optional_numeric(
            source, "periodic_active_well_days"
        )
    else:
        periodic_operating_well_days = periodic_active * source["len_report_period"]
    mean_reservoir_pressure = (
        source["Ppl_on_start_period"] + source["Ppl_on_end_period"]
    ) / 2
    excel_mean_drawdown = (source["dP"] + periodic_dp) / 2
    operating_mean_drawdown = _safe_ratio(
        source["dP"] * base_operating + periodic_dp * periodic_operating,
        operating_group_count,
    )
    operating_mean_wellhead_pressure = _safe_ratio(
        source["Pust"] * base_operating + periodic_pust * periodic_operating,
        operating_group_count,
    )
    operating_mean_bottomhole_pressure = np.where(
        operating_group_count > 0,
        mean_reservoir_pressure - operating_mean_drawdown,
        0.0,
    )

    monthly = pd.DataFrame({
        "date": source["date"],
        "year": source["date"].dt.year,
        "days": source["len_report_period"],
        "base_gas_production_mm3": source["Qgas_base_fond"]
            + _optional_numeric(source, "Qgas_periodic"),
        "base_condensate_production_kt": source["Qcond_base_fond"]
            + _optional_numeric(source, "Qcond_periodic"),
        "total_gas_production_mm3": source["Qgas_all"],
        "total_condensate_production_kt": source["Qcond_all"],
        "available_wells": available_wells,
        "active_wells": active_wells,
        "active_well_days": base_operating_well_days + periodic_operating_well_days,
        "wells_retired": source["leave_base_fond"] + periodic_retired,
        "wells_introduced": _optional_numeric(source, "vvod_wells_in_curr_period"),
        "reservoir_pressure_start_mpa": source["Ppl_on_start_period"],
        "reservoir_pressure_end_mpa": source["Ppl_on_end_period"],
        "bottomhole_pressure_mpa": source["Pzab"],
        # Эти два поля повторяют AVERAGE из Excel, включая нулевой
        # периодический фонд. Ниже также сохраняются физически корректные поля.
        "mean_drawdown_mpa": excel_mean_drawdown,
        "mean_wellhead_pressure_mpa": (source["Pust"] + periodic_pust) / 2,
        "operating_mean_drawdown_mpa": operating_mean_drawdown,
        "operating_mean_wellhead_pressure_mpa": operating_mean_wellhead_pressure,
        "mean_reservoir_pressure_mpa": mean_reservoir_pressure,
        "mean_bottomhole_pressure_mpa": mean_reservoir_pressure - excel_mean_drawdown,
        "operating_mean_bottomhole_pressure_mpa": operating_mean_bottomhole_pressure,
        "cumulative_gas_mm3": source["Qcum_gas_end_period"],
        "cumulative_condensate_kt": source["Qcum_cond_end_period"],
        "remaining_gas_mm3": source["oiz_gas"],
        "remaining_condensate_kt": source["oiz_cond"],
        "spbt_kt": source["SPBT_t_t"],
        "spbt_mm3": source["SPBT_m_m3"],
    })

    # Excel использует конечный доступный фонд; operating_* использует
    # фактические скважино-сутки и остаётся информативным при остановках.
    monthly["mean_gas_rate_km3_day"] = _safe_ratio(
        monthly["base_gas_production_mm3"] * 1000,
        monthly["available_wells"] * monthly["days"],
    )
    monthly["operating_mean_gas_rate_km3_day"] = _safe_ratio(
        monthly["base_gas_production_mm3"] * 1000,
        monthly["active_well_days"],
    )
    monthly["kgf_g_m3"] = _safe_ratio(
        monthly["base_condensate_production_kt"] * 1000,
        monthly["base_gas_production_mm3"],
    )
    monthly["condensate_rate_t_day"] = (
        monthly["mean_gas_rate_km3_day"] * monthly["kgf_g_m3"] / 1000
    )
    monthly["condensate_rate_m3_day"] = (
        monthly["condensate_rate_t_day"] * 1000 / condensate_density_kgm3
    )
    monthly["operating_condensate_rate_t_day"] = (
        monthly["operating_mean_gas_rate_km3_day"] * monthly["kgf_g_m3"] / 1000
    )
    monthly["operating_condensate_rate_m3_day"] = (
        monthly["operating_condensate_rate_t_day"]
        * 1000 / condensate_density_kgm3
    )

    for key in CONTRIBUTIONS:
        monthly[f"gas_{key}_mm3"] = _optional_numeric(source, f"Qgas_{key}")
        monthly[f"condensate_{key}_kt"] = _optional_numeric(source, f"Qcond_{key}")
        monthly[f"kgf_{key}_g_m3"] = _safe_ratio(
            monthly[f"condensate_{key}_kt"] * 1000,
            monthly[f"gas_{key}_mm3"],
        )

    sum_columns = [
        "days", "base_gas_production_mm3", "base_condensate_production_kt",
        "total_gas_production_mm3", "total_condensate_production_kt",
        "wells_retired", "wells_introduced", "active_well_days", "spbt_kt", "spbt_mm3",
    ]
    for key in CONTRIBUTIONS:
        sum_columns.extend([f"gas_{key}_mm3", f"condensate_{key}_kt"])

    annual = monthly.groupby("year", as_index=False)[sum_columns].sum()
    annual_last = monthly.groupby("year", as_index=False).last()[[
        "year", "available_wells", "active_wells", "reservoir_pressure_end_mpa",
        "bottomhole_pressure_mpa", "cumulative_gas_mm3",
        "cumulative_condensate_kt", "remaining_gas_mm3",
        "remaining_condensate_kt",
    ]]
    annual_last = annual_last.rename(columns={
        "bottomhole_pressure_mpa": "bottomhole_pressure_end_mpa",
    })
    annual_first = monthly.groupby("year", as_index=False).first()[[
        "year", "reservoir_pressure_start_mpa",
    ]]
    annual_mean = monthly.groupby("year", as_index=False)[[
        "mean_drawdown_mpa", "mean_wellhead_pressure_mpa",
        "mean_reservoir_pressure_mpa", "mean_bottomhole_pressure_mpa",
    ]].mean()
    operating_mean_columns = [
        "operating_mean_drawdown_mpa",
        "operating_mean_wellhead_pressure_mpa",
        "operating_mean_bottomhole_pressure_mpa",
    ]
    annual_operating_mean = (
        monthly.loc[monthly["active_wells"] > 0]
        .groupby("year", as_index=False)[operating_mean_columns]
        .mean()
    )
    annual = annual.merge(annual_first, on="year").merge(annual_last, on="year")
    annual = annual.merge(annual_mean, on="year")
    annual = annual.merge(annual_operating_mean, on="year", how="left")
    annual[operating_mean_columns] = annual[operating_mean_columns].fillna(0.0)
    annual["mean_gas_rate_km3_day"] = _safe_ratio(
        annual["base_gas_production_mm3"] * 1000,
        annual["available_wells"] * annual["days"],
    )
    annual["operating_mean_gas_rate_km3_day"] = _safe_ratio(
        annual["base_gas_production_mm3"] * 1000,
        annual["active_well_days"],
    )
    annual["kgf_g_m3"] = _safe_ratio(
        annual["base_condensate_production_kt"] * 1000,
        annual["base_gas_production_mm3"],
    )
    annual["condensate_rate_t_day"] = (
        annual["mean_gas_rate_km3_day"] * annual["kgf_g_m3"] / 1000
    )
    annual["condensate_rate_m3_day"] = (
        annual["condensate_rate_t_day"] * 1000 / condensate_density_kgm3
    )
    annual["operating_condensate_rate_t_day"] = (
        annual["operating_mean_gas_rate_km3_day"] * annual["kgf_g_m3"] / 1000
    )
    annual["operating_condensate_rate_m3_day"] = (
        annual["operating_condensate_rate_t_day"]
        * 1000 / condensate_density_kgm3
    )
    for key in CONTRIBUTIONS:
        annual[f"kgf_{key}_g_m3"] = _safe_ratio(
            annual[f"condensate_{key}_kt"] * 1000,
            annual[f"gas_{key}_mm3"],
        )

    monthly["date"] = monthly["date"].dt.strftime("%Y-%m-%d")
    return monthly, annual


def main():
    base_output = runtime_path("code_sheets", "Base", "base_output.json")
    base_input_path = runtime_path("code_sheets", "Base", "base_input.json")
    output = runtime_path("code_sheets", "Summary", "summary_output.json")
    graph = runtime_path("code_sheets", "Summary", "summary_graph.png")

    with base_output.open(encoding="utf-8") as stream:
        base_frame = pd.DataFrame(json.load(stream))
    with base_input_path.open(encoding="utf-8") as stream:
        base_input = json.load(stream)

    monthly, annual = build_summary(
        base_frame, float(base_input["condensate_density_kgm3"])
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "monthly": monthly.to_dict(orient="records"),
        "annual": annual.to_dict(orient="records"),
        "contribution_labels": CONTRIBUTIONS,
        "calculation_notes": {
            "excel_compatible": [
                "mean_drawdown_mpa",
                "mean_wellhead_pressure_mpa",
                "mean_reservoir_pressure_mpa",
                "mean_bottomhole_pressure_mpa",
                "mean_gas_rate_km3_day",
                "condensate_rate_t_day",
                "condensate_rate_m3_day",
            ],
            "operating_metrics": "Поля operating_* исключают отсутствующий или остановленный фонд.",
            "annual_pressure_aggregation": (
                "Годовые средние давления используют все месяцы календарного года. "
                "Это исправляет формулу База!Q98 исходной книги, где за 2024 год "
                "случайно усреднены только июль–декабрь."
            ),
        },
    }
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=4, allow_nan=False),
        encoding="utf-8",
    )

    fig, ax = plt.subplots(figsize=(14, 7))
    ax.plot(annual["year"], annual["base_gas_production_mm3"], label="Базовая добыча")
    ax.plot(annual["year"], annual["total_gas_production_mm3"], label="Добыча всего")
    ax.set_title("Долгосрочный прогноз добычи газа")
    ax.set_xlabel("Год")
    ax.set_ylabel("Добыча газа, млн м³")
    ax.grid(True)
    ax.legend()
    fig.tight_layout()
    save_figure(fig, graph, dpi=300, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    main()
