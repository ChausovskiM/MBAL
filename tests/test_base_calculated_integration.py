import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from code_sheets.Base import base_controller


class CalculatedContributionIntegrationTests(unittest.TestCase):
    def test_periodic_and_grp_feed_same_period_material_balance(self):
        project_root = Path(__file__).resolve().parents[1]
        periodic_payload = {
            'schema_version': 1,
            'mode': 'calculated',
            'enabled': True,
            'initial_active_wells': 0,
            'inflow_model': 'pressure_squared',
            'kgf_method': 'gas field',
            'strict_excel_compatibility': False,
            'defaults': {
                'drawdown_mpa': 0.1,
                'utilization': 0.5,
                'a_standard': 1000,
                'b_standard': 0,
                'a_pseudo': 1000,
                'b_pseudo': 0,
            },
            'schedule': [
                {'month': 1, 'wells_transferred_from_base': 1},
            ],
        }
        grp_payload = {
            'schema_version': 1,
            'intervention_type': 'grp',
            'mode': 'calculated',
            'enabled': True,
            'include_in_balance': True,
            'include_cohort_details': False,
            'inflow_model': 'pressure_squared',
            'kgf_method': 'gas field',
            'negative_uplift_policy': 'error',
            'period_controls': {
                'default_drawdown_mpa': 0.1,
                'default_utilization': 0.5,
                'overrides': [],
            },
            'events': [{
                'id': 'grp-2024-01',
                'start_period': '2024-01-01',
                'well_count': 1,
                'first_period_work_days': 15,
                'before': {'a': 1000, 'b': 0},
                'after': {'a': 900, 'b': 0},
            }],
        }
        original_forecast_builder = base_controller._build_forecast_table
        original_periodic_builder = base_controller.build_periodic_plan

        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)

            def runtime_path(*parts):
                if parts[-1] in {
                    'base_output.json', 'base_graph.png',
                    'periodic_output.json', 'grp_output.json',
                }:
                    return output_root.joinpath(*parts)
                return project_root.joinpath(*parts)

            def module_input(parts, _fallback):
                return (
                    periodic_payload if 'Periodic' in parts else grp_payload
                )

            def short_forecast(table_data, _horizon, coefficient, drawdown):
                first_two_months = [
                    row for row in table_data if row['month'] <= 2
                ]
                return original_forecast_builder(
                    first_two_months, 2, coefficient, drawdown
                )

            def short_periodic_plan(payload, _horizon):
                return original_periodic_builder(payload, 2)

            with patch.object(
                base_controller, 'runtime_path', side_effect=runtime_path
            ), patch.object(
                base_controller, '_load_optional_json', side_effect=module_input
            ), patch.object(
                base_controller, '_build_forecast_table',
                side_effect=short_forecast,
            ), patch.object(
                base_controller, 'build_periodic_plan',
                side_effect=short_periodic_plan,
            ), patch.object(base_controller, 'save_figure'):
                base_controller.main()

            base_rows = json.loads(
                (output_root / 'code_sheets/Base/base_output.json')
                .read_text(encoding='utf-8')
            )
            periodic_output = json.loads(
                (output_root / 'code_sheets/Periodic/periodic_output.json')
                .read_text(encoding='utf-8')
            )
            grp_output = json.loads(
                (output_root / 'code_sheets/GRP/grp_output.json')
                .read_text(encoding='utf-8')
            )

        first, second = base_rows
        self.assertEqual(first['rab_fond_on_end_period'], 0)
        self.assertEqual(first['periodic_active_wells'], 1)
        self.assertGreater(first['Qgas_periodic'], 0)
        self.assertGreater(first['Qgas_frac'], 0)
        self.assertAlmostEqual(
            first['Qgas_all'],
            first['Qgas_base_fond']
            + first['Qgas_periodic'] + first['Qgas_frac'],
            places=9,
        )
        self.assertEqual(
            second['Ppl_on_start_period'], first['Ppl_on_end_period']
        )
        self.assertEqual(len(periodic_output['results_table']), 2)
        self.assertEqual(len(grp_output['results_table']), 2)
        self.assertFalse(grp_output['include_cohort_details'])
        self.assertNotIn('cohorts', grp_output['results_table'][0])


if __name__ == '__main__':
    unittest.main()
