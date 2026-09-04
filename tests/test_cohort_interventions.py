import unittest
from datetime import date
from unittest.mock import Mock

from code_MBAL.common.cohort_interventions import (
    CohortInterventionEngine,
    PeriodContext,
    build_intervention_plan,
)


def _event(
    event_id,
    start_period,
    *,
    wells=2,
    first_days=15,
    before=(1.0, 0.0),
    after=(0.5, 0.0),
):
    return {
        "id": event_id,
        "start_period": start_period,
        "well_count": wells,
        "first_period_work_days": first_days,
        "before": {"a": before[0], "b": before[1]},
        "after": {"a": after[0], "b": after[1]},
    }


def _payload(
    *,
    events=None,
    mode="calculated",
    enabled=True,
    include_in_balance=True,
    inflow_model="pressure_squared",
    negative_policy="error",
    drawdown=2.0,
    utilization=0.8,
    overrides=None,
    intervention_type="grp",
):
    return {
        "schema_version": 1,
        "intervention_type": intervention_type,
        "mode": mode,
        "enabled": enabled,
        "include_in_balance": include_in_balance,
        "inflow_model": inflow_model,
        "kgf_method": "gas field",
        "negative_uplift_policy": negative_policy,
        "period_controls": {
            "default_drawdown_mpa": drawdown,
            "default_utilization": utilization,
            "overrides": overrides or [],
        },
        "events": events or [],
    }


def _context(index, start, *, days=30, pressure=20.0, temperature=60.0):
    return PeriodContext(
        index=index,
        start=date.fromisoformat(start),
        days=days,
        reservoir_pressure_mpa=pressure,
        reservoir_temperature_c=temperature,
    )


def _engine(payload, *, kgf=None, density=800.0, mobility=None):
    return CohortInterventionEngine.from_payload(
        payload,
        kgf_calculator=kgf or (lambda _pressure: 50.0),
        condensate_density_kg_m3=density,
        mobility_calculator=mobility,
    )


class ExcelParityTests(unittest.TestCase):
    def test_t1_new_linear_cohort_uses_partial_first_period(self):
        engine = _engine(_payload(events=[_event("grp-1", "2025-01-01")]))

        result = engine.step(_context(0, "2025-01-01"))

        self.assertEqual(result.bottomhole_pressure_mpa, 18.0)
        self.assertEqual(result.new_wells, 2.0)
        self.assertEqual(result.active_wells_end, 2.0)
        self.assertEqual(result.mean_active_wells, 0.8)
        self.assertEqual(result.active_well_days, 24.0)
        self.assertAlmostEqual(result.gas_rate_km3_day_per_mean_well, 76.0)
        self.assertAlmostEqual(result.gas_million_m3, 1.824)
        self.assertAlmostEqual(result.condensate_thousand_t, 0.0912)
        self.assertAlmostEqual(result.cumulative_gas_million_m3, 1.824)
        self.assertAlmostEqual(
            result.cumulative_condensate_thousand_t, 0.0912
        )
        self.assertEqual(len(result.cohorts), 1)
        cohort = result.cohorts[0]
        self.assertEqual(cohort.event_id, "grp-1")
        self.assertEqual(cohort.exposure_days, 15.0)
        self.assertAlmostEqual(cohort.raw_delta_rate_km3_day_per_well, 76.0)
        self.assertAlmostEqual(cohort.delta_rate_km3_day_per_well, 76.0)
        self.assertEqual(
            result.to_base_columns(),
            {"Qgas_frac": 1.824, "Qcond_frac": 0.0912},
        )

    def test_t2_old_cohort_gets_full_period_and_new_cohort_partial_period(self):
        events = [
            _event("grp-1", "2025-01-01"),
            _event(
                "grp-2",
                "2025-02-01",
                wells=1,
                first_days=10,
                after=(0.8, 0.0),
            ),
        ]
        payload = _payload(
            events=events,
            overrides=[{"period": "2025-02-01", "utilization": 0.9}],
        )
        # KGF=50 at mean pressure 19 MPa and 48 at 18 MPa.
        engine = _engine(payload, kgf=lambda pressure: 2 * pressure + 12)
        engine.step(_context(0, "2025-01-01"))

        result = engine.step(
            _context(1, "2025-02-01", days=31, pressure=19.0)
        )

        self.assertEqual(result.utilization, 0.9)
        self.assertEqual(result.new_wells, 1.0)
        self.assertEqual(result.active_wells_end, 3.0)
        self.assertAlmostEqual(result.mean_active_wells, 2.0903225806451613)
        self.assertAlmostEqual(result.active_well_days, 64.8)
        self.assertAlmostEqual(result.gas_million_m3, 4.1796)
        self.assertAlmostEqual(result.condensate_thousand_t, 0.2006208)
        self.assertAlmostEqual(result.gas_rate_km3_day_per_mean_well, 64.5)
        self.assertAlmostEqual(result.condensate_rate_t_day_per_mean_well, 3.096)
        self.assertAlmostEqual(result.condensate_rate_m3_day_per_mean_well, 3.87)
        self.assertAlmostEqual(result.cumulative_gas_million_m3, 6.0036)
        self.assertAlmostEqual(
            result.cumulative_condensate_thousand_t, 0.2918208
        )
        self.assertEqual([item.exposure_days for item in result.cohorts], [31, 10])
        self.assertAlmostEqual(result.cohorts[0].gas_million_m3, 4.0176)
        self.assertAlmostEqual(result.cohorts[1].gas_million_m3, 0.162)

    def test_t3_pseudopressure_uses_one_period_mobility_for_both_rates(self):
        mobility = Mock(return_value=1000.0)
        payload = _payload(
            inflow_model="pseudopressure",
            events=[_event(
                "grp-pseudo",
                "2025-01-01",
                before=(200.0, 1.0),
                after=(100.0, 0.5),
            )],
        )
        engine = _engine(payload, density=754.0, mobility=mobility)

        result = engine.step(_context(0, "2025-01-01"))

        mobility.assert_called_once_with(19.0, 60.0)
        self.assertEqual(result.mobility_lambda, 1000.0)
        cohort = result.cohorts[0]
        self.assertAlmostEqual(
            cohort.raw_delta_rate_km3_day_per_well, 8.777084160959092
        )
        self.assertAlmostEqual(result.gas_million_m3, 0.21065001986301823)
        self.assertAlmostEqual(
            result.condensate_thousand_t, 0.01053250099315091
        )
        self.assertAlmostEqual(
            result.gas_rate_km3_day_per_mean_well, 8.777084160959092
        )
        self.assertAlmostEqual(
            result.condensate_rate_t_day_per_mean_well, 0.4388542080479546
        )
        self.assertAlmostEqual(
            result.condensate_rate_m3_day_per_mean_well, 0.582034758684290
        )

    def test_result_serialization_keeps_iso_dates_and_json_containers(self):
        result = _engine(
            _payload(events=[_event("grp-1", "2025-01-01")])
        ).step(_context(0, "2025-01-01"))

        serialized = result.to_dict()

        self.assertEqual(serialized["period"], "2025-01-01")
        self.assertEqual(serialized["cohorts"][0]["start_period"], "2025-01-01")
        self.assertIsInstance(serialized["cohorts"], list)
        self.assertIsInstance(serialized["warnings"], list)


class NegativeUpliftPolicyTests(unittest.TestCase):
    def _negative_payload(self, policy, *, include_in_balance=True):
        return _payload(
            events=[_event(
                "decline",
                "2025-01-01",
                before=(0.5, 0.0),
                after=(1.0, 0.0),
            )],
            negative_policy=policy,
            include_in_balance=include_in_balance,
        )

    def test_error_policy_rejects_negative_increment(self):
        engine = _engine(self._negative_payload("error"))

        with self.assertRaisesRegex(ValueError, "дебит после ГТМ ниже"):
            engine.step(_context(0, "2025-01-01"))

    def test_allow_policy_preserves_negative_production_and_warns(self):
        result = _engine(self._negative_payload("allow")).step(
            _context(0, "2025-01-01")
        )

        self.assertAlmostEqual(result.cohorts[0].raw_delta_rate_km3_day_per_well, -76)
        self.assertAlmostEqual(result.cohorts[0].delta_rate_km3_day_per_well, -76)
        self.assertAlmostEqual(result.gas_million_m3, -1.824)
        self.assertAlmostEqual(result.condensate_thousand_t, -0.0912)
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("decline", result.warnings[0])

    def test_clip_zero_policy_keeps_diagnostics_but_removes_production(self):
        result = _engine(self._negative_payload("clip_zero")).step(
            _context(0, "2025-01-01")
        )

        self.assertAlmostEqual(result.cohorts[0].raw_delta_rate_km3_day_per_well, -76)
        self.assertEqual(result.cohorts[0].delta_rate_km3_day_per_well, 0.0)
        self.assertEqual(result.gas_million_m3, 0.0)
        self.assertEqual(result.condensate_thousand_t, 0.0)
        self.assertEqual(len(result.warnings), 1)

    def test_excluded_result_is_calculated_but_not_mapped_into_balance(self):
        result = _engine(
            self._negative_payload("allow", include_in_balance=False)
        ).step(_context(0, "2025-01-01"))

        self.assertLess(result.gas_million_m3, 0)
        self.assertEqual(
            result.to_base_columns(),
            {"Qgas_frac": 0.0, "Qcond_frac": 0.0},
        )


class EngineStateTests(unittest.TestCase):
    def test_external_plan_cannot_be_stepped(self):
        engine = _engine(_payload(mode="external"))

        with self.assertRaisesRegex(RuntimeError, "mode='external'"):
            engine.step(_context(0, "2025-01-01"))

    def test_periods_must_have_strictly_increasing_index_and_date(self):
        engine = _engine(_payload())
        engine.step(_context(0, "2025-01-01"))

        with self.assertRaisesRegex(ValueError, "строго по возрастанию"):
            engine.step(_context(0, "2025-02-01"))
        with self.assertRaisesRegex(ValueError, "строго по возрастанию"):
            engine.step(_context(1, "2024-12-01"))

    def test_reset_allows_replay_and_resets_active_cohorts_and_cumulative(self):
        engine = _engine(_payload(events=[_event("grp-1", "2025-01-01")]))
        first = engine.step(_context(0, "2025-01-01"))
        second = engine.step(_context(1, "2025-02-01", days=28))
        self.assertGreater(second.cumulative_gas_million_m3, first.gas_million_m3)

        engine.reset()
        replay = engine.step(_context(0, "2025-01-01"))

        self.assertAlmostEqual(replay.gas_million_m3, first.gas_million_m3)
        self.assertAlmostEqual(
            replay.cumulative_gas_million_m3, first.gas_million_m3
        )
        self.assertEqual(replay.new_wells, first.new_wells)
        self.assertEqual(len(replay.cohorts), 1)

    def test_skipping_an_event_start_is_rejected(self):
        engine = _engine(_payload(events=[_event("grp-1", "2025-01-01")]))

        with self.assertRaisesRegex(ValueError, "Пропущен период запуска GTM"):
            engine.step(_context(0, "2025-02-01"))

    def test_future_cohort_is_not_used_before_its_exact_start_date(self):
        engine = _engine(_payload(events=[_event("grp-1", "2025-02-01")]))

        before = engine.step(_context(0, "2025-01-01", days=31))
        started = engine.step(_context(1, "2025-02-01", days=28))

        self.assertEqual(before.active_wells_end, 0.0)
        self.assertEqual(before.gas_million_m3, 0.0)
        self.assertEqual(started.active_wells_end, 2.0)
        self.assertEqual(started.cohorts[0].exposure_days, 15.0)

    def test_disabled_plan_never_activates_scheduled_cohorts(self):
        engine = _engine(
            _payload(
                enabled=False,
                events=[_event("grp-1", "2025-01-01")],
            )
        )

        first = engine.step(_context(0, "2025-01-01"))
        later = engine.step(_context(1, "2025-02-01"))

        self.assertEqual(first.active_wells_end, 0.0)
        self.assertEqual(later.active_wells_end, 0.0)
        self.assertEqual(later.cumulative_gas_million_m3, 0.0)


class DateAndBoundaryValidationTests(unittest.TestCase):
    def test_invalid_iso_dates_are_rejected_for_events_and_overrides(self):
        with self.assertRaisesRegex(ValueError, "датой YYYY-MM-DD"):
            build_intervention_plan(
                _payload(events=[_event("grp-1", "01.02.2025")])
            )
        with self.assertRaisesRegex(ValueError, "датой YYYY-MM-DD"):
            build_intervention_plan(
                _payload(overrides=[{"period": "2025-13-01", "utilization": 0.5}])
            )

    def test_duplicate_event_and_override_dates_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "может быть только одна когорта"):
            build_intervention_plan(_payload(events=[
                _event("grp-1", "2025-01-01"),
                _event("grp-2", "2025-01-01"),
            ]))
        with self.assertRaisesRegex(ValueError, "Повторяющийся override"):
            build_intervention_plan(_payload(overrides=[
                {"period": "2025-01-01", "utilization": 0.5},
                {"period": "2025-01-01", "drawdown_mpa": 1.0},
            ]))

    def test_first_period_work_days_equal_period_is_allowed(self):
        engine = _engine(_payload(events=[
            _event("grp-1", "2025-01-01", first_days=30),
        ]))

        result = engine.step(_context(0, "2025-01-01", days=30))

        self.assertEqual(result.cohorts[0].exposure_days, 30.0)
        self.assertAlmostEqual(result.mean_active_wells, 1.6)

    def test_first_period_work_days_above_actual_period_is_rejected(self):
        engine = _engine(_payload(events=[
            _event("grp-1", "2025-02-01", first_days=29),
        ]))

        with self.assertRaisesRegex(ValueError, "больше длительности периода"):
            engine.step(_context(0, "2025-02-01", days=28))

    def test_drawdown_above_pressure_is_rejected_only_for_active_cohort(self):
        payload = _payload(
            drawdown=3.0,
            events=[_event("grp-1", "2025-02-01")],
        )
        engine = _engine(payload)
        empty = engine.step(_context(0, "2025-01-01", pressure=2.0))
        self.assertEqual(empty.gas_million_m3, 0.0)

        with self.assertRaisesRegex(ValueError, "выше пластового давления"):
            engine.step(_context(1, "2025-02-01", pressure=2.0))

    def test_context_rejects_nonpositive_days_and_negative_pressure(self):
        engine = _engine(_payload())
        with self.assertRaisesRegex(ValueError, "days должен быть больше нуля"):
            engine.step(_context(0, "2025-01-01", days=0))
        with self.assertRaisesRegex(ValueError, "не может быть отрицательным"):
            engine.step(_context(0, "2025-01-01", pressure=-0.01))

    def test_events_after_processed_horizon_do_not_leak_into_results(self):
        engine = _engine(_payload(events=[
            _event("after-horizon", "2025-04-01"),
        ]))

        results = [
            engine.step(_context(index, period))
            for index, period in enumerate(
                ["2025-01-01", "2025-02-01", "2025-03-01"]
            )
        ]

        self.assertTrue(all(item.active_wells_end == 0 for item in results))
        self.assertTrue(all(item.gas_million_m3 == 0 for item in results))


if __name__ == "__main__":
    unittest.main()
