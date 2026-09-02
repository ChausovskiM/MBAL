import math
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

import runner
from code_MBAL.Complementary_functions.OGR_calc import OGR_calc
from code_MBAL.Pust_MOD.Pust import Pust
from code_MBAL.Q_MOD.fQ import fQ
from code_MBAL.Q_MOD.fQLd import fQLd
from code_MBAL.Velosity_MOD.Velosity import Velosity
from code_MBAL.Z_MOD.Z_calc import Z_calc
from code_MBAL.Complementary_functions.save_figure import save_figure
from code_MBAL.common.gas_mixture import load_gas_components
from code_MBAL.common.paths import get_runtime_root, runtime_path
from code_sheets.Base.base_controller import (
    _apply_well_schedule,
    _build_forecast_table,
    _calculate_base_wellhead_pressure,
    _ensure_contribution_columns,
    _ensure_numeric_columns,
    _validate_base_operation,
    condensate_tonnes_to_m3,
)
from code_sheets.Productivity.prod_controller import effective_length
from code_sheets.Summary.summary_controller import build_summary


class FlowTests(unittest.TestCase):
    def test_fq_supports_linear_inflow(self):
        self.assertAlmostEqual(fQ(2.0, 0.0, 5.0, 3.0), 8.0)

    def test_fqld_supports_linear_inflow(self):
        self.assertAlmostEqual(fQLd(2.0, 0.0, 100.0, 5.0, 3.0), 100.0)

    def test_nonpositive_pressure_drop_has_no_flow(self):
        self.assertEqual(fQ(2.0, 1.0, 3.0, 5.0), 0.0)
        self.assertEqual(fQLd(2.0, 1.0, 100.0, 3.0, 5.0), 0.0)


class SafetyTests(unittest.TestCase):
    def test_pust_rejects_nonphysical_inputs_without_calculation(self):
        args = (89.0, 5.0, 0.7, 3000.0, 20.0, 60.0, 'x', 'x', 'x', 'x', 0.0, 3000.0)
        self.assertEqual(Pust(-1.0, 100.0, *args), 0.0)
        self.assertEqual(Pust(10.0, 0.0, *args), 0.0)
        self.assertEqual(Pust(10.0, 100.0, None, *args[1:]), 0.0)

    def test_velocity_is_zero_for_stopped_well(self):
        self.assertEqual(Velosity('латонов-гуревич', 60.0, 0.0, 10.0, 89.0), 0.0)
        self.assertEqual(Velosity('латонов-гуревич', 60.0, 100.0, 0.0, 89.0), 0.0)


class ConversionAndInputTests(unittest.TestCase):
    def test_condensate_mass_to_volume_matches_excel_formula(self):
        self.assertAlmostEqual(condensate_tonnes_to_m3(32.6705, 754.0), 43.3295756, places=6)

    def test_effective_length_applies_ntg_only_to_nonvertical_completion(self):
        self.assertEqual(effective_length(140.0, 0.0, 0.675), 140.0)
        self.assertAlmostEqual(
            effective_length(140.0, 10.0, 0.675), math.hypot(140.0, 10.0) * 0.675
        )

    def test_optional_gtm_columns_preserve_values_and_fill_gaps(self):
        frame = pd.DataFrame({'Qgas_vns': [1.5, None]})
        _ensure_contribution_columns(frame, ['Qgas_vns', 'Qgas_frac'])
        self.assertEqual(frame['Qgas_vns'].tolist(), [1.5, 0.0])
        self.assertEqual(frame['Qgas_frac'].tolist(), [0.0, 0.0])

    def test_well_schedule_preserves_values_and_fills_gaps(self):
        frame = pd.DataFrame({'leave_base_fond': [1, None]})
        _ensure_numeric_columns(frame, {
            'leave_base_fond': 0.0,
            'vvod_wells_in_curr_period': 0.0,
        })
        self.assertEqual(frame['leave_base_fond'].tolist(), [1.0, 0.0])
        self.assertEqual(frame['vvod_wells_in_curr_period'].tolist(), [0.0, 0.0])

    def test_well_schedule_rejects_retirement_above_available_fund(self):
        frame = pd.DataFrame({
            'vvod_wells_in_curr_period': [0],
            'leave_base_fond': [2],
            'time_prod_leaving_wells': [15],
            'len_report_period': [31],
        })
        with self.assertRaises(ValueError):
            _apply_well_schedule(frame, entry_wells=1)

    def test_forecast_preserves_user_values_after_month_13(self):
        frame = _build_forecast_table(
            [
                {'month': 1, 'exploration_coeff': 0.8, 'dP': 2.0},
                {'month': 14, 'exploration_coeff': 0.7, 'dP': 1.9,
                 'Qgas_frac': 3.5},
            ],
            horizon_months=15,
            default_exploration_coeff=0.9,
            default_dp_mpa=2.6,
        )
        self.assertEqual(frame.loc[13, 'month'], 14)
        self.assertEqual(frame.loc[13, 'exploration_coeff'], 0.7)
        self.assertEqual(frame.loc[13, 'dP'], 1.9)
        self.assertEqual(frame.loc[13, 'Qgas_frac'], 3.5)
        self.assertEqual(frame.loc[14, 'exploration_coeff'], 0.9)
        self.assertEqual(frame.loc[14, 'dP'], 2.6)

    def test_base_wellhead_pressure_uses_md_for_friction_and_tvd_for_head(self):
        base_input = {
            'd_nkt': 89, 'pipe_absolute_roughness': 5,
            'well_md': 5000, 'well_tvd': 3187, 'T_ust': 29,
            'viscosity_method': 'lee-gonzalez',
            'hydraulic_resistance_method': 'стандартная зависимость',
            'hydraulic_resistance_coefficient': 0,
        }
        with patch('code_sheets.Base.base_controller.Pust', return_value=8.5) as pust:
            result = _calculate_base_wellhead_pressure(
                14.0, 500.0, base_input,
                {'Z_method': 'пенг-робинсон', 'density_method': 'корреляция'},
                {'gas_relative_density': 0.7},
                {'T_reservor_init': 60},
            )
        self.assertEqual(result, 8.5)
        self.assertEqual(pust.call_args.args[5], 5000)
        self.assertEqual(pust.call_args.args[-1], 3187)

    def test_stopped_well_does_not_restart_without_explicit_option(self):
        row = pd.Series({
            'Ppl_on_start_period': 12.0,
            'dP': 2.0,
            'Pzab': 10.0,
            'debit_gaza_base': 300.0,
        })
        previous = pd.Series({
            'operation_status': 'остановлена',
            'operation_limit': 'минимальное устьевое давление',
        })
        result = _validate_base_operation(row, {}, {}, {}, {}, previous)
        self.assertEqual(result, (12.0, 0.0, 0.0, 'остановлена', 'минимальное устьевое давление'))

    def test_new_fund_can_start_after_period_without_active_wells(self):
        row = pd.Series({
            'Ppl_on_start_period': 12.0,
            'dP': 2.0,
            'Pzab': 10.0,
            'debit_gaza_base': 300.0,
            'mean_rab_basefond': 1.0,
            'lmbda': 100.0,
        })
        previous = pd.Series({
            'operation_status': 'остановлена',
            'operation_limit': 'нет действующего фонда',
        })
        with patch(
            'code_sheets.Base.base_controller._operating_limit_reason',
            return_value='',
        ):
            result = _validate_base_operation(row, {}, {}, {}, {}, previous)
        self.assertEqual(result, (10.0, 100.0, 300.0, 'работает', ''))

    def test_table_kgf_requires_data(self):
        with self.assertRaises(ValueError):
            OGR_calc('table data', 1.5)
        self.assertAlmostEqual(
            OGR_calc('table data', 1.5, [1.0, 2.0], [10.0, 20.0]), 15.0
        )

    def test_polynomial_kgf_uses_exact_curve_instead_of_rounded_table(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            kgf_dir = Path(temp_dir) / 'code_sheets' / 'KGF'
            kgf_dir.mkdir(parents=True)
            (kgf_dir / 'kgf_output.json').write_text(json.dumps({
                'C5_plus': 9.0,
                'coeff_experiment': [2.0, 1.0],
                'coef_type': [3.0, 2.0],
                'results_table': {
                    'P': [1.0, 4.0],
                    'KGF_experiment': [999.0, 999.0],
                    'KGF_type': [999.0, 999.0],
                },
            }), encoding='utf-8')
            (kgf_dir / 'kgf_experimental_input.json').write_text(
                json.dumps({'Pnk': 4.0}), encoding='utf-8'
            )
            (kgf_dir / 'kgf_typical_input.json').write_text(
                json.dumps({'Pnk': 4.0, 'KGF': 14.0}), encoding='utf-8'
            )

            with patch.dict(os.environ, {'MBAL_OUT_DIR': temp_dir}):
                self.assertEqual(OGR_calc('experimental data', 3.0), 7.0)
                self.assertEqual(OGR_calc('experimental data', 4.0), 9.0)
                self.assertEqual(OGR_calc('experimental data', 4.001), 9.0)
                self.assertEqual(OGR_calc('typical dependence', 3.0), 11.0)
                self.assertEqual(OGR_calc('typical dependence', 4.001), 14.0)

    def test_table_z_requires_data(self):
        with self.assertRaises(ValueError):
            Z_calc('таблица', 1.5, 60.0)
        self.assertAlmostEqual(
            Z_calc('таблица', 1.5, 60.0, [1.0, 2.0], [0.9, 1.0]), 0.95
        )


class RunnerTests(unittest.TestCase):
    def test_runtime_paths_follow_current_output_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir).resolve()
            components_path = root / 'code_sheets' / 'PVT' / 'gas_components.json'
            components_path.parent.mkdir(parents=True)
            components_path.write_text(
                json.dumps([{'formula': 'test', 'mol_fraction_pct': 100}]),
                encoding='utf-8',
            )
            with patch.dict(os.environ, {'MBAL_OUT_DIR': str(root)}):
                self.assertEqual(get_runtime_root(), root)
                self.assertEqual(
                    runtime_path('code_sheets', 'PVT', 'gas_components.json'),
                    components_path,
                )
                self.assertEqual(load_gas_components()[0]['formula'], 'test')

    def test_summary_runs_after_base(self):
        self.assertGreater(
            runner.MODULES.index('code_sheets.Summary.summary_controller'),
            runner.MODULES.index('code_sheets.Base.base_controller'),
        )

    def test_controller_error_is_propagated(self):
        with patch.object(runner, 'MODULES', ['does.not.exist']):
            with self.assertRaises(RuntimeError):
                runner.run_controllers()

    def test_frozen_startup_preserves_user_data(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / 'source'
            output = root / 'output'
            (source / 'code_sheets').mkdir(parents=True)
            (output / 'code_sheets').mkdir(parents=True)
            source_file = source / 'code_sheets' / 'input.json'
            output_file = output / 'code_sheets' / 'input.json'
            source_file.write_text('source', encoding='utf-8')
            output_file.write_text('user value', encoding='utf-8')

            with patch.dict(os.environ, {}, clear=False):
                with patch.multiple(runner, FROZEN=True, BASE_READ=source, OUT_DIR=output):
                    runner.prepare_workdir()

            self.assertEqual(output_file.read_text(encoding='utf-8'), 'user value')


class OutputTests(unittest.TestCase):
    def test_summary_aggregates_excel_report_metrics(self):
        rows = []
        for date_value, days, gas, condensate, pressure in [
            ('2024-01-01', 31, 15.0, 0.75, 17.0),
            ('2024-02-01', 29, 14.0, 0.70, 16.5),
        ]:
            rows.append({
                'date': date_value,
                'len_report_period': days,
                'Qgas_base_fond': gas,
                'Qcond_base_fond': condensate,
                'Qgas_all': gas,
                'Qcond_all': condensate,
                'rab_fond_on_end_period': 1,
                'leave_base_fond': 0,
                'dP': 2.5,
                'Pust': 9.0,
                'Ppl_on_start_period': pressure,
                'Ppl_on_end_period': pressure - 0.1,
                'Pzab': pressure - 2.5,
                'Qcum_gas_end_period': 900.0,
                'Qcum_cond_end_period': 10.0,
                'oiz_gas': 3000.0,
                'oiz_cond': 300.0,
                'SPBT_t_t': 0.3,
                'SPBT_m_m3': 0.15,
                'operation_status': 'работает',
            })

        monthly, annual = build_summary(pd.DataFrame(rows), 754.0)
        self.assertEqual(len(monthly), 2)
        self.assertAlmostEqual(annual.loc[0, 'base_gas_production_mm3'], 29.0)
        self.assertAlmostEqual(annual.loc[0, 'base_condensate_production_kt'], 1.45)
        self.assertAlmostEqual(annual.loc[0, 'kgf_g_m3'], 50.0)
        self.assertAlmostEqual(
            annual.loc[0, 'mean_gas_rate_km3_day'], 29_000 / 60
        )
        self.assertEqual(annual.loc[0, 'reservoir_pressure_start_mpa'], 17.0)
        self.assertEqual(annual.loc[0, 'reservoir_pressure_end_mpa'], 16.4)

    def test_summary_does_not_report_stopped_well_as_active(self):
        row = {
            'date': '2034-02-01',
            'len_report_period': 28,
            'Qgas_base_fond': 0.0,
            'Qcond_base_fond': 0.0,
            'Qgas_all': 0.0,
            'Qcond_all': 0.0,
            'rab_fond_on_end_period': 1,
            'leave_base_fond': 0,
            'dP': 2.6,
            'Pust': 0.0,
            'Ppl_on_start_period': 10.0,
            'Ppl_on_end_period': 10.0,
            'Pzab': 10.0,
            'Qcum_gas_end_period': 2000.0,
            'Qcum_cond_end_period': 100.0,
            'oiz_gas': 2000.0,
            'oiz_cond': 200.0,
            'SPBT_t_t': 0.0,
            'SPBT_m_m3': 0.0,
            'operation_status': 'остановлена',
        }
        monthly, annual = build_summary(pd.DataFrame([row]), 754.0)
        self.assertEqual(monthly.loc[0, 'available_wells'], 1)
        self.assertEqual(monthly.loc[0, 'active_wells'], 0)
        self.assertEqual(monthly.loc[0, 'operating_mean_drawdown_mpa'], 0)
        self.assertEqual(monthly.loc[0, 'operating_mean_wellhead_pressure_mpa'], 0)
        self.assertEqual(monthly.loc[0, 'operating_mean_bottomhole_pressure_mpa'], 0)
        self.assertEqual(annual.loc[0, 'mean_gas_rate_km3_day'], 0)
        self.assertEqual(annual.loc[0, 'operating_mean_drawdown_mpa'], 0)
        self.assertEqual(annual.loc[0, 'operating_mean_wellhead_pressure_mpa'], 0)

    def test_summary_annual_operating_pressures_exclude_stopped_months(self):
        common = {
            'len_report_period': 31,
            'Qgas_base_fond': 1.0,
            'Qcond_base_fond': 0.05,
            'Qgas_all': 1.0,
            'Qcond_all': 0.05,
            'rab_fond_on_end_period': 1,
            'leave_base_fond': 0,
            'Ppl_on_start_period': 15.0,
            'Ppl_on_end_period': 14.8,
            'Pzab': 12.5,
            'Qcum_gas_end_period': 1.0,
            'Qcum_cond_end_period': 0.05,
            'oiz_gas': 100.0,
            'oiz_cond': 5.0,
            'SPBT_t_t': 0.0,
            'SPBT_m_m3': 0.0,
        }
        working = {
            **common,
            'date': '2024-01-01',
            'dP': 2.5,
            'Pust': 10.0,
            'operation_status': 'работает',
        }
        stopped = {
            **common,
            'date': '2024-02-01',
            'len_report_period': 29,
            'Qgas_base_fond': 0.0,
            'Qcond_base_fond': 0.0,
            'Qgas_all': 0.0,
            'Qcond_all': 0.0,
            'dP': 2.6,
            'Pust': 0.0,
            'operation_status': 'остановлена',
        }

        _monthly, annual = build_summary(
            pd.DataFrame([working, stopped]), 754.0
        )
        self.assertEqual(annual.loc[0, 'operating_mean_drawdown_mpa'], 2.5)
        self.assertEqual(annual.loc[0, 'operating_mean_wellhead_pressure_mpa'], 10.0)

    def test_summary_keeps_excel_and_operating_pressure_metrics(self):
        row = {
            'date': '2024-01-01', 'len_report_period': 31,
            'Qgas_base_fond': 15.0, 'Qcond_base_fond': 0.75,
            'Qgas_all': 15.0, 'Qcond_all': 0.75,
            'rab_fond_on_end_period': 1, 'leave_base_fond': 0,
            'dP': 2.4, 'Pust': 10.0,
            'Ppl_on_start_period': 17.0, 'Ppl_on_end_period': 16.9,
            'Pzab': 14.6, 'Qcum_gas_end_period': 900.0,
            'Qcum_cond_end_period': 10.0, 'oiz_gas': 3000.0,
            'oiz_cond': 300.0, 'SPBT_t_t': 0.3, 'SPBT_m_m3': 0.15,
            'operation_status': 'работает',
        }
        monthly, _annual = build_summary(pd.DataFrame([row]), 754.0)
        self.assertEqual(monthly.loc[0, 'mean_drawdown_mpa'], 1.2)
        self.assertEqual(monthly.loc[0, 'operating_mean_drawdown_mpa'], 2.4)
        self.assertEqual(monthly.loc[0, 'mean_wellhead_pressure_mpa'], 5.0)
        self.assertEqual(monthly.loc[0, 'operating_mean_wellhead_pressure_mpa'], 10.0)
        self.assertAlmostEqual(monthly.loc[0, 'mean_bottomhole_pressure_mpa'], 15.75)
        self.assertAlmostEqual(
            monthly.loc[0, 'operating_mean_bottomhole_pressure_mpa'], 14.55
        )

    def test_figure_is_saved_through_temporary_file(self):
        class FakeFigure:
            def savefig(self, path, **kwargs):
                Path(path).write_bytes(b'graph')

        with tempfile.TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / 'graph.png'
            save_figure(FakeFigure(), target, dpi=300)
            self.assertEqual(target.read_bytes(), b'graph')


if __name__ == '__main__':
    unittest.main()
