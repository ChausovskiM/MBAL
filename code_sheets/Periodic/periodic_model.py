"""Помесячная модель периодической эксплуатации скважин."""

import math
from dataclasses import dataclass, replace

from code_MBAL.Complementary_functions.OGR_calc import OGR_calc
from code_MBAL.Ld_MOD.Ld import Ld
from code_MBAL.Pust_MOD.Pust import Pust
from code_MBAL.Tochigin_MOD.Tochigin import Tochigin
from code_MBAL.Velosity_MOD.Velosity import Velosity
from code_MBAL.common.inflow import (
    PSEUDOPRESSURE,
    calculate_inflow_rate,
    normalize_inflow_model,
)


SCHEDULE_FIELDS = (
    "drawdown_mpa",
    "utilization",
    "wells_retired",
    "wells_transferred_from_base",
    "a_standard",
    "b_standard",
    "a_pseudo",
    "b_pseudo",
)


def _finite_number(value, field):
    if isinstance(value, bool):
        raise ValueError(f"{field} должен быть числом")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field} должен быть числом") from error
    if not math.isfinite(result):
        raise ValueError(f"{field} должен быть конечным числом")
    return result


def _validate_keys(mapping, allowed, location):
    unknown = sorted(set(mapping).difference(allowed))
    if unknown:
        raise ValueError(
            f"Неизвестные поля в {location}: {', '.join(unknown)}"
        )


@dataclass(frozen=True)
class PeriodicSchedule:
    month: int
    drawdown_mpa: float = 0.0
    utilization: float = 0.0
    wells_retired: float = 0.0
    wells_transferred_from_base: float = 0.0
    a_standard: float = 0.0
    b_standard: float = 0.0
    a_pseudo: float = 0.0
    b_pseudo: float = 0.0


@dataclass(frozen=True)
class PeriodicPlan:
    mode: str
    enabled: bool
    initial_active_wells: float
    inflow_model: str
    kgf_method: str
    strict_excel_compatibility: bool
    schedules: tuple


@dataclass(frozen=True)
class PeriodicState:
    active_wells: float = 0.0
    cumulative_gas_mm3: float = 0.0
    cumulative_condensate_kt: float = 0.0


@dataclass(frozen=True)
class PeriodicConfig:
    inflow_model: str
    kgf_method: str
    z_method: str
    density_method: str
    viscosity_method: str
    hydraulic_resistance_method: str
    hydraulic_resistance_coefficient: float
    reservoir_temperature_c: float
    wellhead_temperature_c: float
    gas_relative_density: float
    condensate_density_kgm3: float
    tubing_diameter_mm: float
    pipe_absolute_roughness_mm: float
    well_md_m: float
    well_tvd_m: float
    surface_tension_nm: float
    strict_excel_compatibility: bool = False


@dataclass(frozen=True)
class PeriodicStepResult:
    gas_mm3: float
    condensate_kt: float
    active_wells: float
    mean_active_wells: float
    active_well_days: float
    wells_retired: float
    wells_transferred_from_base: float
    drawdown_mpa: float
    bottomhole_pressure_mpa: float
    wellhead_pressure_mpa: float
    mobility_lambda: float
    kgf_g_m3: float
    gas_rate_km3_day: float
    condensate_rate_t_day: float
    condensate_rate_m3_day: float
    bottomhole_velocity_ms: float
    wellhead_velocity_ms: float
    minimum_lift_velocity_ms: float
    liquid_lift: str
    operation_status: str
    operation_reason: str
    cumulative_gas_mm3: float
    cumulative_condensate_kt: float

    def to_columns(self):
        return {
            "Qgas_periodic": self.gas_mm3,
            "Qcond_periodic": self.condensate_kt,
            "periodic_active_wells": self.active_wells,
            "periodic_mean_active_wells": self.mean_active_wells,
            "periodic_active_well_days": self.active_well_days,
            "periodic_wells_retired": self.wells_retired,
            "periodic_wells_transferred_in": self.wells_transferred_from_base,
            "periodic_dP": self.drawdown_mpa,
            "periodic_Pzab": self.bottomhole_pressure_mpa,
            "periodic_Pust": self.wellhead_pressure_mpa,
            "periodic_lambda": self.mobility_lambda,
            "periodic_KGF": self.kgf_g_m3,
            "periodic_debit_gas": self.gas_rate_km3_day,
            "periodic_debit_cond_t": self.condensate_rate_t_day,
            "periodic_debit_cond_m3": self.condensate_rate_m3_day,
            "periodic_v_bottom": self.bottomhole_velocity_ms,
            "periodic_v_head": self.wellhead_velocity_ms,
            "periodic_vmin": self.minimum_lift_velocity_ms,
            "periodic_liquid_lift": self.liquid_lift,
            "periodic_operation_status": self.operation_status,
            "periodic_operation_reason": self.operation_reason,
            "periodic_cum_gas": self.cumulative_gas_mm3,
            "periodic_cum_cond": self.cumulative_condensate_kt,
        }


def build_periodic_plan(payload, horizon_months):
    """Проверяет JSON и разворачивает разреженный график на весь горизонт."""
    if not isinstance(payload, dict):
        raise ValueError("Periodic input должен быть JSON-объектом")
    _validate_keys(payload, {
        "schema_version", "mode", "enabled", "initial_active_wells",
        "inflow_model", "kgf_method", "strict_excel_compatibility",
        "defaults", "schedule",
    }, "Periodic")
    schema_version = payload.get("schema_version", 1)
    if isinstance(schema_version, bool) or schema_version != 1:
        raise ValueError("Поддерживается только schema_version=1 для Periodic")

    mode = payload.get("mode", "external")
    if mode not in {"external", "calculated"}:
        raise ValueError("Periodic.mode должен быть external или calculated")
    enabled = payload.get("enabled", False)
    if not isinstance(enabled, bool):
        raise ValueError("Periodic.enabled должен быть true или false")
    initial_active_wells = _finite_number(
        payload.get("initial_active_wells", 0.0), "initial_active_wells"
    )
    if initial_active_wells < 0:
        raise ValueError("initial_active_wells не может быть отрицательным")

    inflow_model = payload.get("inflow_model", "inherit")
    if inflow_model != "inherit":
        normalize_inflow_model(inflow_model)
    kgf_method = payload.get("kgf_method", "inherit")
    if not isinstance(kgf_method, str) or not kgf_method.strip():
        raise ValueError("Periodic.kgf_method должен быть непустой строкой")
    strict_excel_compatibility = payload.get(
        "strict_excel_compatibility", False
    )
    if not isinstance(strict_excel_compatibility, bool):
        raise ValueError(
            "Periodic.strict_excel_compatibility должен быть true или false"
        )

    defaults = payload.get("defaults", {})
    if not isinstance(defaults, dict):
        raise ValueError("Periodic.defaults должен быть JSON-объектом")
    _validate_keys(defaults, set(SCHEDULE_FIELDS), "Periodic.defaults")
    default_values = {
        field: _finite_number(defaults.get(field, 0.0), f"defaults.{field}")
        for field in SCHEDULE_FIELDS
    }
    default_schedule = PeriodicSchedule(month=0, **default_values)

    entries = payload.get("schedule", [])
    if not isinstance(entries, list):
        raise ValueError("Periodic.schedule должен быть массивом")
    schedules = [
        replace(default_schedule, month=month)
        for month in range(1, horizon_months + 1)
    ]
    seen_months = set()
    for position, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(f"Periodic.schedule[{position}] должен быть объектом")
        _validate_keys(
            entry, {"month", *SCHEDULE_FIELDS},
            f"Periodic.schedule[{position}]",
        )
        month_value = _finite_number(
            entry.get("month"), f"Periodic.schedule[{position}].month"
        )
        if not month_value.is_integer():
            raise ValueError("Periodic month должен быть целым числом")
        month = int(month_value)
        if month < 1 or month > horizon_months:
            raise ValueError(f"Periodic month должен быть от 1 до {horizon_months}")
        if month in seen_months:
            raise ValueError(f"Повторяющийся Periodic month: {month}")
        seen_months.add(month)
        overrides = {
            field: _finite_number(entry[field], f"month {month}.{field}")
            for field in SCHEDULE_FIELDS if field in entry
        }
        schedules[month - 1] = replace(schedules[month - 1], **overrides)

    for schedule in schedules:
        if not 0 <= schedule.utilization <= 1:
            raise ValueError(
                f"Periodic utilization месяца {schedule.month} должен быть от 0 до 1"
            )
        if schedule.drawdown_mpa < 0:
            raise ValueError("Periodic drawdown_mpa не может быть отрицательным")
        if schedule.wells_retired < 0 or schedule.wells_transferred_from_base < 0:
            raise ValueError("Движение периодического фонда не может быть отрицательным")
        for field in ("a_standard", "a_pseudo"):
            if getattr(schedule, field) < 0:
                raise ValueError(f"Periodic {field} не может быть отрицательным")
        for field in ("b_standard", "b_pseudo"):
            if getattr(schedule, field) < 0:
                raise ValueError(f"Periodic {field} не может быть отрицательным")

    return PeriodicPlan(
        mode=mode,
        enabled=enabled,
        initial_active_wells=initial_active_wells,
        inflow_model=inflow_model,
        kgf_method=kgf_method,
        strict_excel_compatibility=strict_excel_compatibility,
        schedules=tuple(schedules),
    )


def _validate_config(config):
    positive_fields = {
        "condensate_density_kgm3": config.condensate_density_kgm3,
        "tubing_diameter_mm": config.tubing_diameter_mm,
        "well_md_m": config.well_md_m,
        "well_tvd_m": config.well_tvd_m,
        "gas_relative_density": config.gas_relative_density,
    }
    for field, value in positive_fields.items():
        if _finite_number(value, field) <= 0:
            raise ValueError(f"{field} должен быть больше нуля")
    if _finite_number(
        config.pipe_absolute_roughness_mm, "pipe_absolute_roughness_mm"
    ) < 0:
        raise ValueError("pipe_absolute_roughness_mm не может быть отрицательным")
    hydraulic_coefficient = _finite_number(
        config.hydraulic_resistance_coefficient,
        "hydraulic_resistance_coefficient",
    )
    if hydraulic_coefficient < 0:
        raise ValueError("hydraulic_resistance_coefficient не может быть отрицательным")
    for field in ("reservoir_temperature_c", "wellhead_temperature_c"):
        if _finite_number(getattr(config, field), field) <= -273.15:
            raise ValueError(f"{field} должен быть выше абсолютного нуля")
    if _finite_number(config.surface_tension_nm, "surface_tension_nm") < 0:
        raise ValueError("surface_tension_nm не может быть отрицательным")
    if not isinstance(config.strict_excel_compatibility, bool):
        raise ValueError("strict_excel_compatibility должен быть true или false")
    return normalize_inflow_model(config.inflow_model)


def _validate_schedule_and_state(schedule, state):
    month = _finite_number(schedule.month, "schedule.month")
    if not month.is_integer() or month < 1:
        raise ValueError("schedule.month должен быть положительным целым числом")
    values = {
        field: _finite_number(getattr(schedule, field), f"schedule.{field}")
        for field in SCHEDULE_FIELDS
    }
    if not 0 <= values["utilization"] <= 1:
        raise ValueError("schedule.utilization должен быть от 0 до 1")
    nonnegative = set(SCHEDULE_FIELDS).difference({"utilization"})
    for field in nonnegative:
        if values[field] < 0:
            raise ValueError(f"schedule.{field} не может быть отрицательным")

    state_values = {
        "active_wells": _finite_number(state.active_wells, "state.active_wells"),
        "cumulative_gas_mm3": _finite_number(
            state.cumulative_gas_mm3, "state.cumulative_gas_mm3"
        ),
        "cumulative_condensate_kt": _finite_number(
            state.cumulative_condensate_kt,
            "state.cumulative_condensate_kt",
        ),
    }
    for field, value in state_values.items():
        if value < 0:
            raise ValueError(f"state.{field} не может быть отрицательным")
    return values, state_values


def calculate_periodic_step(
    *, reservoir_pressure_mpa, period_days, schedule, state, config,
    mobility_calculator=None, kgf_calculator=None,
    wellhead_calculator=None, velocity_calculator=None,
    minimum_lift_velocity_calculator=None,
):
    """Рассчитывает один период и возвращает результат вместе с новым состоянием."""
    normalized_model = _validate_config(config)
    schedule_values, state_values = _validate_schedule_and_state(
        schedule, state
    )
    ppl = _finite_number(reservoir_pressure_mpa, "reservoir_pressure_mpa")
    days = _finite_number(period_days, "period_days")
    if ppl < 0:
        raise ValueError("reservoir_pressure_mpa не может быть отрицательным")
    if days <= 0:
        raise ValueError("period_days должен быть больше нуля")

    previous_wells = state_values["active_wells"]
    retired = schedule_values["wells_retired"]
    transferred = schedule_values["wells_transferred_from_base"]
    utilization = schedule_values["utilization"]
    drawdown = schedule_values["drawdown_mpa"]
    active_wells = (
        previous_wells - retired + transferred
    )
    if active_wells < -1e-12:
        raise ValueError(
            f"Periodic month {schedule.month}: выбытие превышает доступный фонд"
        )
    active_wells = max(active_wells, 0.0)
    mean_active_wells = active_wells * utilization
    active_well_days = mean_active_wells * days

    if mean_active_wells > 0 and drawdown > ppl:
        raise ValueError(
            f"Periodic month {schedule.month}: депрессия выше пластового давления"
        )
    bottomhole_pressure = max(ppl - drawdown, 0.0)
    mean_pressure = (ppl + bottomhole_pressure) / 2

    if mobility_calculator is None:
        mobility_calculator = lambda pressure: Ld(
            config.z_method, config.density_method, config.viscosity_method,
            pressure, config.reservoir_temperature_c,
        )
    if kgf_calculator is None:
        kgf_calculator = lambda pressure: OGR_calc(config.kgf_method, pressure)
    if wellhead_calculator is None:
        well_length = (
            config.well_tvd_m
            if config.strict_excel_compatibility else config.well_md_m
        )
        wellhead_temperature = (
            20.0
            if config.strict_excel_compatibility
            else config.wellhead_temperature_c
        )
        wellhead_calculator = lambda pzab, qgas: Pust(
            pzab, qgas, config.tubing_diameter_mm,
            config.pipe_absolute_roughness_mm, config.gas_relative_density,
            well_length, wellhead_temperature,
            config.reservoir_temperature_c, config.z_method,
            config.viscosity_method, config.density_method,
            config.hydraulic_resistance_method,
            config.hydraulic_resistance_coefficient, config.well_tvd_m,
        )
    if velocity_calculator is None:
        velocity_calculator = lambda temperature, qgas, pressure: Velosity(
            config.z_method, temperature, qgas, pressure,
            config.tubing_diameter_mm,
        )
    if minimum_lift_velocity_calculator is None:
        minimum_lift_velocity_calculator = lambda pzab: Tochigin(
            pzab, config.reservoir_temperature_c, config.surface_tension_nm,
            config.condensate_density_kgm3, config.tubing_diameter_mm,
            config.z_method, config.density_method,
            config.gas_relative_density,
        )

    mobility = float(mobility_calculator(mean_pressure)) if mean_pressure > 0 else 0.0
    if not math.isfinite(mobility) or mobility < 0:
        raise ValueError("Periodic mobility должна быть конечной и неотрицательной")
    minimum_lift_velocity = (
        float(minimum_lift_velocity_calculator(bottomhole_pressure))
        if bottomhole_pressure > 0 else 0.0
    )
    if not math.isfinite(minimum_lift_velocity) or minimum_lift_velocity < 0:
        raise ValueError(
            "Periodic minimum lift velocity должна быть конечной и неотрицательной"
        )
    gas_rate = 0.0
    kgf = 0.0
    if mean_active_wells > 0:
        kgf = float(kgf_calculator(mean_pressure))
        if not math.isfinite(kgf) or kgf < 0:
            raise ValueError("Periodic KGF должен быть конечным и неотрицательным")
    if mean_active_wells > 0 and drawdown > 0:
        if bottomhole_pressure <= 0:
            raise ValueError(
                f"Periodic month {schedule.month}: неположительное забойное давление"
            )
        if normalized_model == PSEUDOPRESSURE:
            a_value = schedule_values["a_pseudo"]
            b_value = schedule_values["b_pseudo"]
        else:
            a_value = schedule_values["a_standard"]
            b_value = schedule_values["b_standard"]
        if a_value <= 0 or b_value < 0:
            raise ValueError(
                f"Periodic month {schedule.month}: некорректные коэффициенты притока"
            )
        gas_rate = calculate_inflow_rate(
            normalized_model, a_value, b_value, ppl,
            bottomhole_pressure, mobility,
        )
        if normalized_model == PSEUDOPRESSURE and mobility <= 0:
            raise ValueError("Periodic mobility должна быть больше нуля")

    condensate_rate_t = gas_rate * kgf / 1000
    condensate_rate_m3 = (
        condensate_rate_t * 1000 / config.condensate_density_kgm3
    )
    gas = gas_rate * active_well_days / 1000
    condensate = condensate_rate_t * active_well_days / 1000
    wellhead_pressure = float(wellhead_calculator(bottomhole_pressure, gas_rate))
    if not math.isfinite(wellhead_pressure) or wellhead_pressure < 0:
        raise ValueError("Periodic Pust должно быть конечным и неотрицательным")
    bottomhole_velocity = float(velocity_calculator(
        config.reservoir_temperature_c, gas_rate, bottomhole_pressure
    ))
    head_velocity_temperature = (
        config.reservoir_temperature_c
        if config.strict_excel_compatibility
        else config.wellhead_temperature_c
    )
    wellhead_velocity = float(velocity_calculator(
        head_velocity_temperature, gas_rate, wellhead_pressure
    ))
    for field, value in {
        "bottomhole velocity": bottomhole_velocity,
        "wellhead velocity": wellhead_velocity,
    }.items():
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"Periodic {field} должна быть конечной и неотрицательной")
    liquid_lift = (
        "да" if bottomhole_velocity > minimum_lift_velocity else "нет"
    ) if gas_rate > 0 else ""

    if active_wells <= 0:
        operation_status, operation_reason = "остановлена", "нет фонда"
    elif utilization <= 0:
        operation_status, operation_reason = "остановлена", "нулевой коэффициент эксплуатации"
    elif drawdown <= 0:
        operation_status, operation_reason = "остановлена", "нет депрессии"
    elif gas_rate <= 0:
        operation_status, operation_reason = "остановлена", "нет притока"
    else:
        operation_status, operation_reason = "работает", ""

    cumulative_gas = state_values["cumulative_gas_mm3"] + gas
    cumulative_condensate = (
        state_values["cumulative_condensate_kt"] + condensate
    )
    result = PeriodicStepResult(
        gas_mm3=gas,
        condensate_kt=condensate,
        active_wells=active_wells,
        mean_active_wells=mean_active_wells,
        active_well_days=active_well_days,
        wells_retired=retired,
        wells_transferred_from_base=transferred,
        drawdown_mpa=drawdown,
        bottomhole_pressure_mpa=bottomhole_pressure,
        wellhead_pressure_mpa=wellhead_pressure,
        mobility_lambda=mobility,
        kgf_g_m3=kgf,
        gas_rate_km3_day=gas_rate,
        condensate_rate_t_day=condensate_rate_t,
        condensate_rate_m3_day=condensate_rate_m3,
        bottomhole_velocity_ms=bottomhole_velocity,
        wellhead_velocity_ms=wellhead_velocity,
        minimum_lift_velocity_ms=minimum_lift_velocity,
        liquid_lift=liquid_lift,
        operation_status=operation_status,
        operation_reason=operation_reason,
        cumulative_gas_mm3=cumulative_gas,
        cumulative_condensate_kt=cumulative_condensate,
    )
    new_state = PeriodicState(
        active_wells=active_wells,
        cumulative_gas_mm3=cumulative_gas,
        cumulative_condensate_kt=cumulative_condensate,
    )
    return result, new_state
