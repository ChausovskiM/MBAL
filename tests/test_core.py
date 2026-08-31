import math
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
from code_sheets.Base.base_controller import (
    _ensure_contribution_columns,
    _validate_base_operation,
    condensate_tonnes_to_m3,
)
from code_sheets.Productivity.prod_controller import effective_length


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

    def test_table_kgf_requires_data(self):
        with self.assertRaises(ValueError):
            OGR_calc('table data', 1.5)
        self.assertAlmostEqual(
            OGR_calc('table data', 1.5, [1.0, 2.0], [10.0, 20.0]), 15.0
        )

    def test_table_z_requires_data(self):
        with self.assertRaises(ValueError):
            Z_calc('таблица', 1.5, 60.0)
        self.assertAlmostEqual(
            Z_calc('таблица', 1.5, 60.0, [1.0, 2.0], [0.9, 1.0]), 0.95
        )


class RunnerTests(unittest.TestCase):
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

            with patch.multiple(runner, FROZEN=True, BASE_READ=source, OUT_DIR=output):
                runner.prepare_workdir()

            self.assertEqual(output_file.read_text(encoding='utf-8'), 'user value')


class OutputTests(unittest.TestCase):
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
