import unittest
from dataclasses import replace
from unittest.mock import patch

import pandas as pd

from code_MBAL.common.inflow import PRESSURE_SQUARED
from code_sheets.Base.base_controller import (
    COND_CONTRIBUTION_COLUMNS,
    GAS_CONTRIBUTION_COLUMNS,
    _apply_well_schedule,
    _ensure_contribution_columns,
    _external_contribution_results,
    _finalize_gas_step,
    _module_output_json,
    _prepare_owned_contribution,
)
from code_sheets.Periodic.periodic_model import (
    PeriodicConfig,
    PeriodicSchedule,
    PeriodicState,
    build_periodic_plan,
    calculate_periodic_step,
)


def _config():
    return PeriodicConfig(
        inflow_model=PRESSURE_SQUARED,
        kgf_method="test",
        z_method="test",
        density_method="test",
        viscosity_method="test",
        hydraulic_resistance_method="test",
        hydraulic_resistance_coefficient=0.0,
        reservoir_temperature_c=60.0,
        wellhead_temperature_c=20.0,
        gas_relative_density=0.7,
        condensate_density_kgm3=750.0,
        tubing_diameter_mm=89.0,
        pipe_absolute_roughness_mm=0.05,
        well_md_m=3000.0,
        well_tvd_m=2800.0,
        surface_tension_nm=0.07,
    )


def _calculate(schedule, state, days=30.0, *, config=None, mobility=1.0):
    return calculate_periodic_step(
        reservoir_pressure_mpa=10.0,
        period_days=days,
        schedule=schedule,
        state=state,
        config=config or _config(),
        mobility_calculator=lambda _pressure: mobility,
        kgf_calculator=lambda _pressure: 50.0,
        wellhead_calculator=lambda pzab, _qgas: pzab - 1.0,
        velocity_calculator=lambda _temperature, qgas, _pressure: qgas / 10.0,
        minimum_lift_velocity_calculator=lambda _pzab: 1.0,
    )


class PeriodicFormulaTests(unittest.TestCase):
    def test_linear_inflow_matches_excel_reference_case(self):
        schedule = PeriodicSchedule(
            month=1,
            drawdown_mpa=2.0,
            utilization=0.5,
            wells_transferred_from_base=2.0,
            a_standard=2.0,
            b_standard=0.0,
        )

        result, state = _calculate(
            schedule,
            PeriodicState(),
            config=replace(_config(), condensate_density_kgm3=800.0),
        )

        self.assertEqual(result.active_wells, 2.0)
        self.assertEqual(result.mean_active_wells, 1.0)
        self.assertEqual(result.active_well_days, 30.0)
        self.assertAlmostEqual(result.gas_rate_km3_day, 18.0)
        self.assertAlmostEqual(result.condensate_rate_t_day, 0.9)
        self.assertAlmostEqual(result.condensate_rate_m3_day, 1.125)
        self.assertAlmostEqual(result.gas_mm3, 0.54)
        self.assertAlmostEqual(result.condensate_kt, 0.027)
        self.assertAlmostEqual(state.cumulative_gas_mm3, 0.54)
        self.assertAlmostEqual(state.cumulative_condensate_kt, 0.027)

    def test_nonlinear_inflow_matches_quadratic_solution(self):
        schedule = PeriodicSchedule(
            month=1,
            drawdown_mpa=2.0,
            utilization=0.5,
            wells_transferred_from_base=2.0,
            a_standard=2.0,
            b_standard=0.5,
        )

        result, _state = _calculate(schedule, PeriodicState())

        expected_rate = 6.717797887081348
        self.assertAlmostEqual(result.gas_rate_km3_day, expected_rate)
        self.assertAlmostEqual(result.gas_mm3, expected_rate * 30.0 / 1000.0)
        self.assertAlmostEqual(
            result.condensate_kt,
            expected_rate * 50.0 / 1000.0 * 30.0 / 1000.0,
        )

    def test_russian_pseudopressure_alias_selects_pseudo_coefficients(self):
        schedule = PeriodicSchedule(
            month=1,
            drawdown_mpa=2.0,
            utilization=1.0,
            wells_transferred_from_base=1.0,
            a_standard=999.0,
            b_standard=999.0,
            a_pseudo=2.0,
            b_pseudo=0.0,
        )
        config = replace(_config(), inflow_model="через псевдодавление")

        result, _state = _calculate(
            schedule,
            PeriodicState(),
            config=config,
            mobility=100.0,
        )

        self.assertAlmostEqual(result.mobility_lambda, 100.0)
        self.assertAlmostEqual(result.gas_rate_km3_day, 100.0)
        self.assertAlmostEqual(result.gas_mm3, 3.0)
        self.assertAlmostEqual(result.condensate_kt, 0.15)

    def test_zero_utilization_preserves_fund_without_production(self):
        schedule = PeriodicSchedule(
            month=1,
            drawdown_mpa=2.0,
            utilization=0.0,
            a_standard=2.0,
        )

        result, state = _calculate(
            schedule,
            PeriodicState(
                active_wells=3.0,
                cumulative_gas_mm3=1.25,
                cumulative_condensate_kt=0.05,
            ),
        )

        self.assertEqual(result.active_wells, 3.0)
        self.assertEqual(result.mean_active_wells, 0.0)
        self.assertEqual(result.active_well_days, 0.0)
        self.assertEqual(result.gas_mm3, 0.0)
        self.assertEqual(result.condensate_kt, 0.0)
        self.assertEqual(result.operation_status, "остановлена")
        self.assertEqual(
            result.operation_reason, "нулевой коэффициент эксплуатации"
        )
        self.assertEqual(state.active_wells, 3.0)
        self.assertEqual(state.cumulative_gas_mm3, 1.25)
        self.assertEqual(state.cumulative_condensate_kt, 0.05)

    def test_direct_nan_inputs_are_rejected(self):
        valid_schedule = PeriodicSchedule(
            month=1,
            drawdown_mpa=1.0,
            utilization=1.0,
            a_standard=1.0,
        )
        cases = (
            (
                "schedule",
                replace(valid_schedule, drawdown_mpa=float("nan")),
                PeriodicState(active_wells=1.0),
                10.0,
            ),
            (
                "state",
                valid_schedule,
                PeriodicState(active_wells=float("nan")),
                10.0,
            ),
            (
                "pressure",
                valid_schedule,
                PeriodicState(active_wells=1.0),
                float("nan"),
            ),
        )

        for label, schedule, state, pressure in cases:
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, "конечным числом"):
                    calculate_periodic_step(
                        reservoir_pressure_mpa=pressure,
                        period_days=30.0,
                        schedule=schedule,
                        state=state,
                        config=_config(),
                        mobility_calculator=lambda _pressure: 1.0,
                        kgf_calculator=lambda _pressure: 50.0,
                        wellhead_calculator=lambda pzab, _qgas: pzab - 1.0,
                        velocity_calculator=lambda _temperature, qgas, _pressure: (
                            qgas / 10.0
                        ),
                        minimum_lift_velocity_calculator=lambda _pzab: 1.0,
                    )

    def test_kgf_is_calculated_for_active_fund_when_drawdown_is_zero(self):
        schedule = PeriodicSchedule(
            month=1,
            drawdown_mpa=0.0,
            utilization=1.0,
            a_standard=2.0,
        )
        requested_pressures = []

        result, _state = calculate_periodic_step(
            reservoir_pressure_mpa=10.0,
            period_days=30.0,
            schedule=schedule,
            state=PeriodicState(active_wells=1.0),
            config=_config(),
            mobility_calculator=lambda _pressure: 1.0,
            kgf_calculator=lambda pressure: (
                requested_pressures.append(pressure) or 50.0
            ),
            wellhead_calculator=lambda pzab, _qgas: pzab - 1.0,
            velocity_calculator=lambda _temperature, qgas, _pressure: qgas,
            minimum_lift_velocity_calculator=lambda _pzab: 1.0,
        )

        self.assertEqual(requested_pressures, [10.0])
        self.assertEqual(result.kgf_g_m3, 50.0)
        self.assertEqual(result.gas_rate_km3_day, 0.0)
        self.assertEqual(result.gas_mm3, 0.0)
        self.assertEqual(result.condensate_kt, 0.0)
        self.assertEqual(result.operation_reason, "нет депрессии")

    def test_strict_excel_mode_reproduces_legacy_temperature_inputs(self):
        schedule = PeriodicSchedule(
            month=1,
            drawdown_mpa=2.0,
            utilization=1.0,
            a_standard=2.0,
        )

        for strict, expected_length, expected_pust_temp, expected_head_temp in (
            (False, 3000.0, 5.0, 5.0),
            (True, 2800.0, 20.0, 60.0),
        ):
            with self.subTest(strict_excel_compatibility=strict):
                config = replace(
                    _config(),
                    wellhead_temperature_c=5.0,
                    strict_excel_compatibility=strict,
                )
                with patch(
                    "code_sheets.Periodic.periodic_model.Pust",
                    return_value=7.0,
                ) as pust, patch(
                    "code_sheets.Periodic.periodic_model.Velosity",
                    side_effect=(1.2, 1.1),
                ) as velocity:
                    calculate_periodic_step(
                        reservoir_pressure_mpa=10.0,
                        period_days=30.0,
                        schedule=schedule,
                        state=PeriodicState(active_wells=1.0),
                        config=config,
                        mobility_calculator=lambda _pressure: 1.0,
                        kgf_calculator=lambda _pressure: 50.0,
                        minimum_lift_velocity_calculator=lambda _pzab: 1.0,
                    )

                pust_args = pust.call_args.args
                self.assertEqual(pust_args[5], expected_length)
                self.assertEqual(pust_args[6], expected_pust_temp)
                self.assertEqual(pust_args[7], 60.0)
                self.assertEqual(velocity.call_args_list[0].args[1], 60.0)
                self.assertEqual(
                    velocity.call_args_list[1].args[1], expected_head_temp
                )


class PeriodicTransferTests(unittest.TestCase):
    def test_boolean_schema_version_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'schema_version=1'):
            build_periodic_plan(
                {'schema_version': True}, horizon_months=1
            )

    def test_transfer_is_a_single_month_event_and_not_forward_filled(self):
        plan = build_periodic_plan(
            {
                "mode": "calculated",
                "enabled": True,
                "defaults": {
                    "drawdown_mpa": 2.0,
                    "utilization": 0.5,
                    "a_standard": 1.0,
                    "b_standard": 0.0,
                },
                "schedule": [
                    {"month": 1, "wells_transferred_from_base": 1.0},
                ],
            },
            horizon_months=2,
        )

        self.assertEqual(plan.schedules[0].wells_transferred_from_base, 1.0)
        self.assertEqual(plan.schedules[1].wells_transferred_from_base, 0.0)

        first, state = _calculate(
            plan.schedules[0], PeriodicState(active_wells=2.0)
        )
        second, state = _calculate(plan.schedules[1], state, days=31.0)

        # The transfer acts at the start of month 1, so all three wells
        # contribute to that month's mean fund and production.
        self.assertEqual(first.active_wells, 3.0)
        self.assertEqual(first.mean_active_wells, 1.5)
        self.assertEqual(first.active_well_days, 45.0)
        self.assertEqual(first.wells_transferred_from_base, 1.0)
        self.assertAlmostEqual(first.gas_rate_km3_day, 36.0)
        self.assertAlmostEqual(first.gas_mm3, 1.62)
        self.assertAlmostEqual(first.condensate_kt, 0.081)

        # The same schedule value must not silently transfer the well again.
        self.assertEqual(second.active_wells, 3.0)
        self.assertEqual(second.wells_transferred_from_base, 0.0)
        self.assertEqual(state.active_wells, 3.0)

    def test_retirement_above_available_periodic_fund_is_rejected(self):
        plan = build_periodic_plan(
            {
                "mode": "calculated",
                "enabled": True,
                "schedule": [{"month": 1, "wells_retired": 2.0}],
            },
            horizon_months=1,
        )

        with self.assertRaisesRegex(ValueError, "выбытие превышает доступный фонд"):
            _calculate(plan.schedules[0], PeriodicState(active_wells=1.0))

    def test_one_schedule_transfer_conserves_combined_base_and_periodic_fund(self):
        plan = build_periodic_plan(
            {
                "mode": "calculated",
                "enabled": True,
                "schedule": [
                    {"month": 1, "wells_transferred_from_base": 1.0},
                ],
            },
            horizon_months=2,
        )
        frame = pd.DataFrame(
            {
                "vvod_wells_in_curr_period": [0.0, 0.0],
                "leave_base_fond": [0.0, 0.0],
                "time_prod_leaving_wells": [0.0, 0.0],
                "len_report_period": [30.0, 31.0],
                # The only source is Periodic.schedule; Base receives its
                # internal projection rather than a second user-entered value.
                "transfer_to_periodic": [
                    schedule.wells_transferred_from_base
                    for schedule in plan.schedules
                ],
            }
        )
        _apply_well_schedule(frame, entry_wells=2.0)

        periodic_state = PeriodicState()
        combined_fund = []
        for index, schedule in enumerate(plan.schedules):
            _result, periodic_state = _calculate(
                schedule, periodic_state, days=frame.loc[index, "len_report_period"]
            )
            combined_fund.append(
                frame.loc[index, "rab_fond_on_end_period"]
                + periodic_state.active_wells
            )

        self.assertEqual(frame["rab_fond_on_end_period"].tolist(), [1, 1])
        self.assertEqual(combined_fund, [2.0, 2.0])


class PeriodicContributionModeTests(unittest.TestCase):
    @staticmethod
    def _frame():
        frame = pd.DataFrame(
            {
                "Qgas_base_fond": [10.0],
                "Qcond_base_fond": [0.5],
                "Qgas_frac": [1.0],
                "Qcond_frac": [0.05],
                "Qgas_periodic": [2.0],
                "Qcond_periodic": [0.1],
                "Qcum_gas_start_period": [100.0],
                "cum_time": [0.0],
                "len_report_period": [31.0],
            }
        )
        _ensure_contribution_columns(frame, GAS_CONTRIBUTION_COLUMNS)
        _ensure_contribution_columns(frame, COND_CONTRIBUTION_COLUMNS)
        return frame

    def test_external_mode_preserves_periodic_contribution_exactly_once(self):
        frame = self._frame()

        should_calculate = _prepare_owned_contribution(
            frame,
            module_name="Periodic",
            mode="external",
            enabled=True,
            gas_column="Qgas_periodic",
            condensate_column="Qcond_periodic",
        )

        self.assertFalse(should_calculate)
        self.assertEqual(GAS_CONTRIBUTION_COLUMNS.count("Qgas_periodic"), 1)
        self.assertEqual(COND_CONTRIBUTION_COLUMNS.count("Qcond_periodic"), 1)
        self.assertEqual(frame.loc[0, "Qgas_periodic"], 2.0)
        self.assertEqual(frame.loc[0, "Qcond_periodic"], 0.1)
        with patch(
            "code_sheets.Base.base_controller._material_balance_pressure",
            return_value=9.5,
        ) as pressure:
            _finalize_gas_step(frame, 0, {}, {}, initial_z=1.0)

        self.assertEqual(frame.loc[0, "Qgas_all"], 13.0)
        self.assertEqual(frame.loc[0, "Qcum_gas_end_period"], 113.0)
        self.assertEqual(frame.loc[0, "Ppl_on_end_period"], 9.5)
        pressure.assert_called_once_with(113.0, 31.0, {}, {}, 1.0)
        self.assertAlmostEqual(
            frame.loc[0, ["Qcond_base_fond", *COND_CONTRIBUTION_COLUMNS]].sum(),
            0.65,
        )

    def test_disabled_external_mode_removes_only_periodic_contribution(self):
        frame = self._frame()

        should_calculate = _prepare_owned_contribution(
            frame,
            module_name="Periodic",
            mode="external",
            enabled=False,
            gas_column="Qgas_periodic",
            condensate_column="Qcond_periodic",
        )

        self.assertFalse(should_calculate)
        self.assertEqual(frame.loc[0, "Qgas_periodic"], 0.0)
        self.assertEqual(frame.loc[0, "Qcond_periodic"], 0.0)
        self.assertEqual(frame.loc[0, "Qgas_frac"], 1.0)
        self.assertEqual(frame.loc[0, "Qcond_frac"], 0.05)
        with patch(
            "code_sheets.Base.base_controller._material_balance_pressure",
            return_value=9.5,
        ):
            _finalize_gas_step(frame, 0, {}, {}, initial_z=1.0)
        self.assertEqual(frame.loc[0, "Qgas_all"], 11.0)
        self.assertEqual(frame.loc[0, "Qcum_gas_end_period"], 111.0)

    def test_calculated_mode_rejects_external_periodic_values(self):
        frame = self._frame()

        with self.assertRaisesRegex(ValueError, "нельзя одновременно задать"):
            _prepare_owned_contribution(
                frame,
                module_name="Periodic",
                mode="calculated",
                enabled=True,
                gas_column="Qgas_periodic",
                condensate_column="Qcond_periodic",
            )

    def test_external_module_output_contains_preserved_time_series(self):
        frame = self._frame()
        frame['month'] = [1]
        frame['date'] = pd.to_datetime(['2024-01-01'])
        frame['Ppl_on_start_period'] = [17.2]
        frame['periodic_active_wells'] = [2.0]
        frame['periodic_Pust'] = [float('nan')]

        results = _external_contribution_results(
            frame,
            frame['Qgas_periodic'].copy(),
            frame['Qcond_periodic'].copy(),
            'Qgas_periodic',
            'Qcond_periodic',
            'periodic',
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]['date'], '2024-01-01')
        self.assertEqual(results[0]['Qgas_periodic'], 2.0)
        self.assertEqual(results[0]['Qcond_periodic'], 0.1)
        self.assertEqual(results[0]['periodic_active_wells'], 2.0)
        self.assertIsNone(results[0]['periodic_Pust'])
        self.assertNotIn('NaN', _module_output_json(
            mode='external', enabled=True, results=results
        ))


if __name__ == "__main__":
    unittest.main()
