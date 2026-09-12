"""
Offline deterministic unit tests for limit_load_to_dll_cascade_logic.py.
Run: python3 test_limit_load_to_dll_cascade.py
Must print OK with no external dependencies.
"""

import math
import sys
import os
import unittest

# Allow running from any working directory.
sys.path.insert(0, os.path.dirname(__file__))

from limit_load_to_dll_cascade_logic import (
    LimitLoadCascadeError,
    validate_luf,
    compute_dll,
    propagate_level,
    cascade,
    combine_loads,
    build_dll_table,
)


class TestValidateLuf(unittest.TestCase):

    def test_luf_unity_accepted(self):
        self.assertEqual(validate_luf(1.0), 1.0)

    def test_luf_above_unity_accepted(self):
        self.assertAlmostEqual(validate_luf(1.25), 1.25)

    def test_luf_below_unity_raises(self):
        with self.assertRaises(LimitLoadCascadeError):
            validate_luf(0.99)

    def test_luf_zero_raises(self):
        with self.assertRaises(LimitLoadCascadeError):
            validate_luf(0.0)

    def test_luf_negative_raises(self):
        with self.assertRaises(LimitLoadCascadeError):
            validate_luf(-1.5)

    def test_luf_non_numeric_raises(self):
        with self.assertRaises(TypeError):
            validate_luf("1.2")


class TestComputeDll(unittest.TestCase):

    def test_basic_multiplication(self):
        # DLL = LL x LUF
        self.assertAlmostEqual(compute_dll(1000.0, 1.25), 1250.0)

    def test_unity_luf_gives_dll_equal_to_ll(self):
        self.assertAlmostEqual(compute_dll(800.0, 1.0), 800.0)

    def test_negative_ll_preserves_sign(self):
        # Negative load (direction) x positive LUF stays negative.
        self.assertAlmostEqual(compute_dll(-500.0, 1.1), -550.0)

    def test_zero_ll_gives_zero_dll(self):
        self.assertAlmostEqual(compute_dll(0.0, 1.5), 0.0)

    def test_luf_below_unity_raises(self):
        with self.assertRaises(LimitLoadCascadeError):
            compute_dll(1000.0, 0.9)

    def test_non_numeric_ll_raises(self):
        with self.assertRaises(TypeError):
            compute_dll("1000", 1.1)

    def test_integer_inputs_accepted(self):
        result = compute_dll(200, 2)
        self.assertAlmostEqual(result, 400.0)


class TestPropagateLevel(unittest.TestCase):

    def test_pass_through_transfer(self):
        # transfer_factor=1.0 means child LL equals parent LL.
        result = propagate_level(500.0, 1.0, 1.2)
        self.assertAlmostEqual(result["ll"], 500.0)
        self.assertAlmostEqual(result["dll"], 600.0)

    def test_amplification_transfer(self):
        # Dynamic amplification: transfer_factor > 1.0 increases child LL.
        result = propagate_level(400.0, 1.5, 1.25)
        self.assertAlmostEqual(result["ll"], 600.0)
        self.assertAlmostEqual(result["dll"], 750.0)

    def test_attenuation_transfer(self):
        # Attenuation: transfer_factor < 1.0 reduces child LL.
        result = propagate_level(1000.0, 0.6, 1.1)
        self.assertAlmostEqual(result["ll"], 600.0)
        self.assertAlmostEqual(result["dll"], 660.0)

    def test_zero_transfer_gives_zero_loads(self):
        result = propagate_level(1000.0, 0.0, 1.3)
        self.assertAlmostEqual(result["ll"], 0.0)
        self.assertAlmostEqual(result["dll"], 0.0)

    def test_negative_transfer_factor_raises(self):
        with self.assertRaises(LimitLoadCascadeError):
            propagate_level(500.0, -0.5, 1.2)

    def test_keys_present_in_result(self):
        result = propagate_level(300.0, 1.0, 1.0)
        self.assertIn("ll", result)
        self.assertIn("dll", result)


class TestCascade(unittest.TestCase):

    def test_single_level_cascade(self):
        levels = [{"name": "panel", "transfer_factor": 1.0, "luf": 1.25}]
        results = cascade(1000.0, levels)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "panel")
        self.assertAlmostEqual(results[0]["ll"], 1000.0)
        self.assertAlmostEqual(results[0]["dll"], 1250.0)

    def test_three_level_cascade_values(self):
        levels = [
            {"name": "subsystem", "transfer_factor": 1.0, "luf": 1.2},
            {"name": "assembly",  "transfer_factor": 0.8, "luf": 1.25},
            {"name": "component", "transfer_factor": 0.9, "luf": 1.3},
        ]
        results = cascade(1000.0, levels)
        self.assertEqual(len(results), 3)
        # Level 0: ll=1000, dll=1200
        self.assertAlmostEqual(results[0]["ll"],  1000.0)
        self.assertAlmostEqual(results[0]["dll"], 1200.0)
        # Level 1: parent_ll=1000 → child_ll=800, dll=1000
        self.assertAlmostEqual(results[1]["ll"],   800.0)
        self.assertAlmostEqual(results[1]["dll"],  1000.0)
        # Level 2: parent_ll=800 → child_ll=720, dll=936
        self.assertAlmostEqual(results[2]["ll"],   720.0)
        self.assertAlmostEqual(results[2]["dll"],  936.0)

    def test_cascade_feeds_child_ll_not_dll(self):
        # The cascade must use child LL (not child DLL) as the next parent LL.
        levels = [
            {"name": "A", "transfer_factor": 1.0, "luf": 1.5},
            {"name": "B", "transfer_factor": 1.0, "luf": 1.0},
        ]
        results = cascade(100.0, levels)
        # Level A: ll=100, dll=150. Level B parent input must be 100, not 150.
        self.assertAlmostEqual(results[1]["ll"],  100.0)
        self.assertAlmostEqual(results[1]["dll"], 100.0)

    def test_empty_levels_raises(self):
        with self.assertRaises(LimitLoadCascadeError):
            cascade(1000.0, [])

    def test_non_list_levels_raises(self):
        with self.assertRaises(TypeError):
            cascade(1000.0, "not_a_list")

    def test_missing_key_raises(self):
        levels = [{"name": "X", "transfer_factor": 1.0}]  # missing 'luf'
        with self.assertRaises(KeyError):
            cascade(1000.0, levels)

    def test_luf_violation_inside_cascade_raises(self):
        levels = [{"name": "bad", "transfer_factor": 1.0, "luf": 0.8}]
        with self.assertRaises(LimitLoadCascadeError):
            cascade(1000.0, levels)


class TestCombineLoads(unittest.TestCase):

    def test_srss_three_components(self):
        # sqrt(3^2 + 4^2) = 5
        result = combine_loads([3.0, 4.0], method="SRSS")
        self.assertAlmostEqual(result, 5.0)

    def test_srss_single_component(self):
        result = combine_loads([7.0], method="SRSS")
        self.assertAlmostEqual(result, 7.0)

    def test_abs_combination(self):
        result = combine_loads([3.0, -4.0, 2.0], method="ABS")
        self.assertAlmostEqual(result, 9.0)

    def test_abs_handles_negatives(self):
        result = combine_loads([-5.0, -5.0], method="ABS")
        self.assertAlmostEqual(result, 10.0)

    def test_unknown_method_raises(self):
        with self.assertRaises(LimitLoadCascadeError):
            combine_loads([1.0, 2.0], method="RSS")

    def test_empty_components_raises(self):
        with self.assertRaises(LimitLoadCascadeError):
            combine_loads([])

    def test_non_numeric_component_raises(self):
        with self.assertRaises(TypeError):
            combine_loads([1.0, "bad"])

    def test_srss_three_equal_components(self):
        # sqrt(1^2 + 1^2 + 1^2) = sqrt(3)
        result = combine_loads([1.0, 1.0, 1.0], method="SRSS")
        self.assertAlmostEqual(result, math.sqrt(3.0))


class TestBuildDllTable(unittest.TestCase):

    def test_table_includes_root_row(self):
        levels = [{"name": "panel", "transfer_factor": 1.0, "luf": 1.25}]
        table = build_dll_table(500.0, levels)
        self.assertEqual(table[0]["name"], "root")
        self.assertAlmostEqual(table[0]["ll"], 500.0)
        self.assertIsNone(table[0]["dll"])

    def test_table_length_equals_levels_plus_one(self):
        levels = [
            {"name": "A", "transfer_factor": 0.9, "luf": 1.2},
            {"name": "B", "transfer_factor": 0.8, "luf": 1.25},
        ]
        table = build_dll_table(1000.0, levels)
        self.assertEqual(len(table), 3)

    def test_table_dll_values_correct(self):
        levels = [{"name": "bracket", "transfer_factor": 1.0, "luf": 1.1}]
        table = build_dll_table(200.0, levels)
        self.assertAlmostEqual(table[1]["dll"], 220.0)

    def test_empty_levels_raises(self):
        with self.assertRaises(LimitLoadCascadeError):
            build_dll_table(500.0, [])


if __name__ == "__main__":
    unittest.main()
