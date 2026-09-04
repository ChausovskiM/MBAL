"""Cohort engine for incremental gas-well interventions.

The source workbook stores GRP, other GTM and ZBS as triangular cohort
matrices.  An intervention cohort starts with a possibly partial first
period, then remains active for every later period.  This module implements
that behaviour without reading project JSON files, so the Base controller can
inject its current pressure and the already selected physical correlations.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass
from datetime import date, datetime
from typing import Callable, Mapping

from code_MBAL.common.inflow import (
    PSEUDOPRESSURE,
    calculate_inflow_rate,
    normalize_inflow_model,
)


INTERVENTION_TYPES = {"grp", "other_gtm", "zbs"}
INTERVENTION_MODES = {"external", "calculated"}
NEGATIVE_UPLIFT_POLICIES = {"error", "allow", "clip_zero"}
OUTPUT_COLUMNS = {
    "grp": ("Qgas_frac", "Qcond_frac"),
    "other_gtm": ("Qgas_gtm", "Qcond_gtm"),
    "zbs": ("Qgas_zbs", "Qcond_zbs"),
}
_UPLIFT_TOLERANCE = 1e-12


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


def _require_keys(mapping, required, location):
    missing = sorted(set(required).difference(mapping))
    if missing:
        raise ValueError(
            f"Не заданы поля в {location}: {', '.join(missing)}"
        )


def _mapping(value, location):
    if not isinstance(value, Mapping):
        raise ValueError(f"{location} должен быть JSON-объектом")
    return value


def _date(value, field):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise ValueError(f"{field} должен быть датой YYYY-MM-DD")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{field} должен быть датой YYYY-MM-DD") from error


@dataclass(frozen=True)
class ProductivityCoefficients:
    """A/B coefficients for one inflow model."""

    a: float
    b: float


@dataclass(frozen=True)
class InterventionEvent:
    """One cohort of wells treated in the same reporting period."""

    id: str
    start_period: date
    well_count: float
    first_period_work_days: float
    before: ProductivityCoefficients
    after: ProductivityCoefficients
    comment: str = ""


@dataclass(frozen=True)
class PeriodControlOverride:
    period: date
    drawdown_mpa: float | None = None
    utilization: float | None = None


@dataclass(frozen=True)
class InterventionPlan:
    schema_version: int
    intervention_type: str
    mode: str
    enabled: bool
    include_in_balance: bool
    include_cohort_details: bool
    inflow_model: str
    kgf_method: str
    negative_uplift_policy: str
    default_drawdown_mpa: float
    default_utilization: float
    overrides: tuple[PeriodControlOverride, ...]
    events: tuple[InterventionEvent, ...]


@dataclass(frozen=True)
class PeriodContext:
    """Reservoir state known before production in the current period."""

    index: int
    start: date
    days: float
    reservoir_pressure_mpa: float
    reservoir_temperature_c: float


@dataclass(frozen=True)
class CohortContribution:
    event_id: str
    start_period: date
    wells: float
    raw_delta_rate_km3_day_per_well: float
    delta_rate_km3_day_per_well: float
    exposure_days: float
    gas_million_m3: float
    condensate_thousand_t: float


@dataclass(frozen=True)
class InterventionPeriodResult:
    intervention_type: str
    include_in_balance: bool
    period: date
    drawdown_mpa: float
    utilization: float
    reservoir_pressure_mpa: float
    bottomhole_pressure_mpa: float
    mobility_lambda: float | None
    kgf_g_m3: float
    new_wells: float
    active_wells_end: float
    mean_active_wells: float
    active_well_days: float
    gas_rate_km3_day_per_mean_well: float
    condensate_rate_t_day_per_mean_well: float
    condensate_rate_m3_day_per_mean_well: float
    gas_million_m3: float
    condensate_thousand_t: float
    cumulative_gas_million_m3: float
    cumulative_condensate_thousand_t: float
    cohorts: tuple[CohortContribution, ...]
    warnings: tuple[str, ...]

    def to_base_columns(self):
        """Map generic contribution values to the columns expected by Base."""
        gas_column, condensate_column = OUTPUT_COLUMNS[self.intervention_type]
        multiplier = 1.0 if self.include_in_balance else 0.0
        return {
            gas_column: self.gas_million_m3 * multiplier,
            condensate_column: self.condensate_thousand_t * multiplier,
        }

    def to_dict(self):
        """Return a JSON-serialisable representation of the period result."""
        payload = asdict(self)
        payload["period"] = self.period.isoformat()
        for cohort in payload["cohorts"]:
            cohort["start_period"] = cohort["start_period"].isoformat()
        payload["cohorts"] = list(payload["cohorts"])
        payload["warnings"] = list(payload["warnings"])
        return payload


def _parse_coefficients(value, location):
    value = _mapping(value, location)
    _validate_keys(value, {"a", "b"}, location)
    _require_keys(value, {"a", "b"}, location)
    a_value = _finite_number(value["a"], f"{location}.a")
    b_value = _finite_number(value["b"], f"{location}.b")
    if a_value <= 0:
        raise ValueError(f"{location}.a должен быть больше нуля")
    if b_value < 0:
        raise ValueError(f"{location}.b не может быть отрицательным")
    return ProductivityCoefficients(a=a_value, b=b_value)


def build_intervention_plan(payload):
    """Validate a sparse JSON payload and return an immutable plan."""
    payload = _mapping(payload, "GTM input")
    root_fields = {
        "schema_version", "intervention_type", "mode", "enabled",
        "include_in_balance", "include_cohort_details", "inflow_model", "kgf_method",
        "negative_uplift_policy", "period_controls", "events",
    }
    _validate_keys(payload, root_fields, "GTM input")
    _require_keys(
        payload, root_fields.difference({"include_cohort_details"}),
        "GTM input",
    )

    if (
        isinstance(payload["schema_version"], bool)
        or payload["schema_version"] != 1
    ):
        raise ValueError("Поддерживается только schema_version=1 для GTM")
    intervention_type = payload["intervention_type"]
    if (
        not isinstance(intervention_type, str)
        or intervention_type not in INTERVENTION_TYPES
    ):
        raise ValueError(
            "intervention_type должен быть grp, other_gtm или zbs"
        )
    mode = payload["mode"]
    if not isinstance(mode, str) or mode not in INTERVENTION_MODES:
        raise ValueError("mode должен быть external или calculated")
    for field in ("enabled", "include_in_balance"):
        if not isinstance(payload[field], bool):
            raise ValueError(f"{field} должен быть true или false")
    include_cohort_details = payload.get("include_cohort_details", False)
    if not isinstance(include_cohort_details, bool):
        raise ValueError("include_cohort_details должен быть true или false")

    inflow_model = payload["inflow_model"]
    if inflow_model != "inherit":
        inflow_model = normalize_inflow_model(inflow_model)
    kgf_method = payload["kgf_method"]
    if not isinstance(kgf_method, str) or not kgf_method.strip():
        raise ValueError("kgf_method должен быть inherit или непустой строкой")
    kgf_method = kgf_method.strip()
    negative_policy = payload["negative_uplift_policy"]
    if (
        not isinstance(negative_policy, str)
        or negative_policy not in NEGATIVE_UPLIFT_POLICIES
    ):
        raise ValueError(
            "negative_uplift_policy должен быть error, allow или clip_zero"
        )

    controls = _mapping(payload["period_controls"], "period_controls")
    control_fields = {
        "default_drawdown_mpa", "default_utilization", "overrides",
    }
    _validate_keys(controls, control_fields, "period_controls")
    _require_keys(controls, control_fields, "period_controls")
    default_drawdown = _finite_number(
        controls["default_drawdown_mpa"], "default_drawdown_mpa"
    )
    default_utilization = _finite_number(
        controls["default_utilization"], "default_utilization"
    )
    if default_drawdown < 0:
        raise ValueError("default_drawdown_mpa не может быть отрицательным")
    if not 0 <= default_utilization <= 1:
        raise ValueError("default_utilization должен быть от 0 до 1")

    override_items = controls["overrides"]
    if not isinstance(override_items, list):
        raise ValueError("period_controls.overrides должен быть массивом")
    overrides = []
    override_dates = set()
    for position, item in enumerate(override_items):
        location = f"period_controls.overrides[{position}]"
        item = _mapping(item, location)
        _validate_keys(item, {"period", "drawdown_mpa", "utilization"}, location)
        _require_keys(item, {"period"}, location)
        if "drawdown_mpa" not in item and "utilization" not in item:
            raise ValueError(f"{location} должен менять хотя бы одно поле")
        period = _date(item["period"], f"{location}.period")
        if period in override_dates:
            raise ValueError(f"Повторяющийся override для {period.isoformat()}")
        override_dates.add(period)
        drawdown = None
        utilization = None
        if "drawdown_mpa" in item:
            drawdown = _finite_number(
                item["drawdown_mpa"], f"{location}.drawdown_mpa"
            )
            if drawdown < 0:
                raise ValueError(f"{location}.drawdown_mpa не может быть отрицательным")
        if "utilization" in item:
            utilization = _finite_number(
                item["utilization"], f"{location}.utilization"
            )
            if not 0 <= utilization <= 1:
                raise ValueError(f"{location}.utilization должен быть от 0 до 1")
        overrides.append(PeriodControlOverride(
            period=period,
            drawdown_mpa=drawdown,
            utilization=utilization,
        ))

    event_items = payload["events"]
    if not isinstance(event_items, list):
        raise ValueError("events должен быть массивом")
    events = []
    event_ids = set()
    event_dates = set()
    event_fields = {
        "id", "start_period", "well_count", "first_period_work_days",
        "before", "after", "comment",
    }
    required_event_fields = event_fields.difference({"comment"})
    for position, item in enumerate(event_items):
        location = f"events[{position}]"
        item = _mapping(item, location)
        _validate_keys(item, event_fields, location)
        _require_keys(item, required_event_fields, location)
        event_id = item["id"]
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError(f"{location}.id должен быть непустой строкой")
        event_id = event_id.strip()
        if event_id in event_ids:
            raise ValueError(f"Повторяющийся GTM id: {event_id}")
        start_period = _date(item["start_period"], f"{location}.start_period")
        if start_period in event_dates:
            raise ValueError(
                f"В периоде {start_period.isoformat()} может быть только одна когорта одного типа"
            )
        well_count = _finite_number(item["well_count"], f"{location}.well_count")
        first_days = _finite_number(
            item["first_period_work_days"],
            f"{location}.first_period_work_days",
        )
        if well_count <= 0:
            raise ValueError(f"{location}.well_count должен быть больше нуля")
        if first_days < 0:
            raise ValueError(
                f"{location}.first_period_work_days не может быть отрицательным"
            )
        comment = item.get("comment", "")
        if not isinstance(comment, str):
            raise ValueError(f"{location}.comment должен быть строкой")
        events.append(InterventionEvent(
            id=event_id,
            start_period=start_period,
            well_count=well_count,
            first_period_work_days=first_days,
            before=_parse_coefficients(item["before"], f"{location}.before"),
            after=_parse_coefficients(item["after"], f"{location}.after"),
            comment=comment,
        ))
        event_ids.add(event_id)
        event_dates.add(start_period)

    return InterventionPlan(
        schema_version=1,
        intervention_type=intervention_type,
        mode=mode,
        enabled=payload["enabled"],
        include_in_balance=payload["include_in_balance"],
        include_cohort_details=include_cohort_details,
        inflow_model=inflow_model,
        kgf_method=kgf_method,
        negative_uplift_policy=negative_policy,
        default_drawdown_mpa=default_drawdown,
        default_utilization=default_utilization,
        overrides=tuple(sorted(overrides, key=lambda item: item.period)),
        events=tuple(sorted(events, key=lambda item: item.start_period)),
    )


class CohortInterventionEngine:
    """Stateful, period-by-period cohort calculator for GRP/other GTM/ZBS."""

    def __init__(
        self,
        plan: InterventionPlan,
        *,
        kgf_calculator: Callable[[float], float],
        condensate_density_kg_m3: float,
        base_inflow_model: str | None = None,
        mobility_calculator: Callable[[float, float], float] | None = None,
    ):
        if not isinstance(plan, InterventionPlan):
            raise TypeError("plan должен быть InterventionPlan")
        if not callable(kgf_calculator):
            raise TypeError("kgf_calculator должен быть функцией")
        if mobility_calculator is not None and not callable(mobility_calculator):
            raise TypeError("mobility_calculator должен быть функцией")
        density = _finite_number(
            condensate_density_kg_m3, "condensate_density_kg_m3"
        )
        if density <= 0:
            raise ValueError("condensate_density_kg_m3 должна быть больше нуля")

        if plan.inflow_model == "inherit":
            if base_inflow_model is None:
                raise ValueError(
                    "base_inflow_model обязателен при inflow_model='inherit'"
                )
            inflow_model = normalize_inflow_model(base_inflow_model)
        else:
            inflow_model = normalize_inflow_model(plan.inflow_model)
        if inflow_model == PSEUDOPRESSURE and mobility_calculator is None:
            raise ValueError(
                "mobility_calculator обязателен для pseudopressure"
            )

        self.plan = plan
        self.inflow_model = inflow_model
        self.kgf_calculator = kgf_calculator
        self.mobility_calculator = mobility_calculator
        self.condensate_density_kg_m3 = density
        self._events_by_date = {event.start_period: event for event in plan.events}
        self._overrides_by_date = {item.period: item for item in plan.overrides}
        self.reset()

    @classmethod
    def from_payload(cls, payload, **dependencies):
        """Build and validate an engine directly from decoded JSON."""
        return cls(build_intervention_plan(payload), **dependencies)

    def reset(self):
        """Reset active cohorts and contribution-only cumulative production."""
        self._active_events = []
        self._active_event_ids = set()
        self._last_index = None
        self._last_period = None
        self._cumulative_gas = 0.0
        self._cumulative_condensate = 0.0

    def _controls_for(self, period):
        drawdown = self.plan.default_drawdown_mpa
        utilization = self.plan.default_utilization
        override = self._overrides_by_date.get(period)
        if override is not None:
            if override.drawdown_mpa is not None:
                drawdown = override.drawdown_mpa
            if override.utilization is not None:
                utilization = override.utilization
        return drawdown, utilization

    def _validate_context(self, context):
        if not isinstance(context, PeriodContext):
            raise TypeError("context должен быть PeriodContext")
        if isinstance(context.index, bool) or not isinstance(context.index, int):
            raise ValueError("PeriodContext.index должен быть целым числом")
        if context.index < 0:
            raise ValueError("PeriodContext.index не может быть отрицательным")
        period = _date(context.start, "PeriodContext.start")
        days = _finite_number(context.days, "PeriodContext.days")
        pressure = _finite_number(
            context.reservoir_pressure_mpa,
            "PeriodContext.reservoir_pressure_mpa",
        )
        temperature = _finite_number(
            context.reservoir_temperature_c,
            "PeriodContext.reservoir_temperature_c",
        )
        if days <= 0:
            raise ValueError("PeriodContext.days должен быть больше нуля")
        if pressure < 0:
            raise ValueError("reservoir_pressure_mpa не может быть отрицательным")
        if self._last_index is not None:
            if context.index <= self._last_index or period <= self._last_period:
                raise ValueError("GTM periods должны поступать строго по возрастанию")
        return period, days, pressure, temperature

    def _apply_uplift_policy(self, event, raw_delta, period, warnings):
        if raw_delta >= -_UPLIFT_TOLERANCE:
            return max(raw_delta, 0.0)
        message = (
            f"{self.plan.intervention_type} {event.id}, {period.isoformat()}: "
            f"дебит после ГТМ ниже дебита до ГТМ "
            f"({raw_delta:g} тыс. м³/сут)"
        )
        if self.plan.negative_uplift_policy == "error":
            raise ValueError(message)
        warnings.append(message)
        if self.plan.negative_uplift_policy == "clip_zero":
            return 0.0
        return raw_delta

    def step(self, context: PeriodContext):
        """Calculate one period and advance the active-cohort state."""
        if self.plan.mode != "calculated":
            raise RuntimeError(
                "GTM mode='external': Base должен сохранить legacy "
                "Qgas/Qcond и не вызывать cohort engine"
            )
        period, days, pressure, temperature = self._validate_context(context)
        drawdown, utilization = self._controls_for(period)
        bottomhole_pressure = max(pressure - drawdown, 0.0)

        if self.plan.enabled:
            missed = [
                event.id for event in self.plan.events
                if event.start_period < period
                and event.id not in self._active_event_ids
            ]
            if missed:
                raise ValueError(
                    "Пропущен период запуска GTM: " + ", ".join(missed)
                )

        new_event = self._events_by_date.get(period) if self.plan.enabled else None
        if new_event is not None and new_event.first_period_work_days > days:
            raise ValueError(
                f"GTM {new_event.id}: first_period_work_days "
                f"({new_event.first_period_work_days:g}) больше длительности "
                f"периода ({days:g})"
            )

        active_or_new = bool(self._active_events or new_event)
        if active_or_new and drawdown > pressure:
            raise ValueError(
                f"GTM {period.isoformat()}: депрессия {drawdown:g} МПа "
                f"выше пластового давления {pressure:g} МПа"
            )

        active_events = tuple(self._active_events) + (
            (new_event,) if new_event is not None else ()
        )

        mean_pressure = (pressure + bottomhole_pressure) / 2
        mobility = None
        kgf = 0.0
        if active_events and self.inflow_model == PSEUDOPRESSURE:
            mobility = 0.0
            if mean_pressure > 0:
                mobility = _finite_number(
                    self.mobility_calculator(mean_pressure, temperature),
                    f"mobility_lambda {period.isoformat()}",
                )
            if mobility <= 0 and drawdown > 0:
                raise ValueError("mobility_lambda должна быть больше нуля")
        if active_events:
            kgf = _finite_number(
                self.kgf_calculator(mean_pressure),
                f"KGF {period.isoformat()}",
            )
            if kgf < 0:
                raise ValueError("KGF не может быть отрицательным")

        warnings = []
        cohort_results = []
        gas = 0.0
        condensate = 0.0
        for event in active_events:
            before_rate = _finite_number(
                calculate_inflow_rate(
                    self.inflow_model,
                    event.before.a,
                    event.before.b,
                    pressure,
                    bottomhole_pressure,
                    mobility or 0.0,
                ),
                f"GTM {event.id} before rate {period.isoformat()}",
            )
            after_rate = _finite_number(
                calculate_inflow_rate(
                    self.inflow_model,
                    event.after.a,
                    event.after.b,
                    pressure,
                    bottomhole_pressure,
                    mobility or 0.0,
                ),
                f"GTM {event.id} after rate {period.isoformat()}",
            )
            raw_delta = after_rate - before_rate
            delta_rate = self._apply_uplift_policy(
                event, raw_delta, period, warnings
            )
            exposure_days = (
                event.first_period_work_days
                if event.start_period == period else days
            )
            cohort_gas = (
                delta_rate * event.well_count * exposure_days
                * utilization / 1000
            )
            cohort_condensate = cohort_gas * kgf / 1000
            gas += cohort_gas
            condensate += cohort_condensate
            cohort_results.append(CohortContribution(
                event_id=event.id,
                start_period=event.start_period,
                wells=event.well_count,
                raw_delta_rate_km3_day_per_well=raw_delta,
                delta_rate_km3_day_per_well=delta_rate,
                exposure_days=exposure_days,
                gas_million_m3=cohort_gas,
                condensate_thousand_t=cohort_condensate,
            ))

        active_wells = sum(event.well_count for event in active_events)
        new_wells = new_event.well_count if new_event is not None else 0.0
        partial_new_wells = (
            new_wells * new_event.first_period_work_days / days
            if new_event is not None else 0.0
        )
        mean_active_wells = (
            active_wells - new_wells + partial_new_wells
        ) * utilization
        active_well_days = mean_active_wells * days
        gas_rate = (
            gas * 1000 / active_well_days
            if active_well_days > 0 else 0.0
        )
        condensate_rate_t = gas_rate * kgf / 1000
        condensate_rate_m3 = (
            condensate_rate_t * 1000 / self.condensate_density_kg_m3
        )
        self._cumulative_gas += gas
        self._cumulative_condensate += condensate

        result = InterventionPeriodResult(
            intervention_type=self.plan.intervention_type,
            include_in_balance=self.plan.include_in_balance,
            period=period,
            drawdown_mpa=drawdown,
            utilization=utilization,
            reservoir_pressure_mpa=pressure,
            bottomhole_pressure_mpa=bottomhole_pressure,
            mobility_lambda=mobility,
            kgf_g_m3=kgf,
            new_wells=new_wells,
            active_wells_end=active_wells,
            mean_active_wells=mean_active_wells,
            active_well_days=active_well_days,
            gas_rate_km3_day_per_mean_well=gas_rate,
            condensate_rate_t_day_per_mean_well=condensate_rate_t,
            condensate_rate_m3_day_per_mean_well=condensate_rate_m3,
            gas_million_m3=gas,
            condensate_thousand_t=condensate,
            cumulative_gas_million_m3=self._cumulative_gas,
            cumulative_condensate_thousand_t=self._cumulative_condensate,
            cohorts=tuple(cohort_results),
            warnings=tuple(warnings),
        )
        if new_event is not None:
            self._active_events.append(new_event)
            self._active_event_ids.add(new_event.id)
        self._last_index = context.index
        self._last_period = period
        return result


__all__ = [
    "CohortContribution",
    "CohortInterventionEngine",
    "InterventionEvent",
    "INTERVENTION_MODES",
    "InterventionPeriodResult",
    "InterventionPlan",
    "OUTPUT_COLUMNS",
    "PeriodContext",
    "PeriodControlOverride",
    "ProductivityCoefficients",
    "build_intervention_plan",
]
