#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C clause 4.6.2.10 buckling onset
analysis verification with HB-32-24 knockdown factor interplay.

Exercises scripts/buckling_analysis_verification_logic.py (stdlib
unittest, offline). Contract: geometry types are mapped to one of four
buckling modes (plate, shell, column, crippling) and an unrecognized
type raises; each mode carries HB-32-24 knockdown factor bounds and a
factor outside those bounds raises on validation; the critical buckling
load is the classical load multiplied by the knockdown factor; the
reserve factor is the critical load divided by the applied load times
the factor of safety; a reserve factor below 1.0 is margin-deficient;
the component review aggregates knockdown-factor and margin violations
and the component is compliant only when both lists are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import buckling_analysis_verification_logic as bav  # noqa: E402


class CategorizeGeometryTest(unittest.TestCase):
    def test_flat_plate_maps_to_plate_mode(self):
        self.assertEqual(bav.categorize_geometry("flat_plate"), "plate")

    def test_stiffened_panel_maps_to_plate_mode(self):
        self.assertEqual(bav.categorize_geometry("stiffened_panel"), "plate")

    def test_cylindrical_shell_maps_to_shell_mode(self):
        self.assertEqual(bav.categorize_geometry("cylindrical_shell"), "shell")

    def test_conical_shell_maps_to_shell_mode(self):
        self.assertEqual(bav.categorize_geometry("conical_shell"), "shell")

    def test_column_maps_to_column_mode(self):
        self.assertEqual(bav.categorize_geometry("column"), "column")

    def test_beam_column_maps_to_column_mode(self):
        self.assertEqual(bav.categorize_geometry("beam_column"), "column")

    def test_angle_section_maps_to_crippling_mode(self):
        self.assertEqual(bav.categorize_geometry("angle_section"), "crippling")

    def test_channel_section_maps_to_crippling_mode(self):
        self.assertEqual(bav.categorize_geometry("channel_section"), "crippling")

    def test_z_section_maps_to_crippling_mode(self):
        self.assertEqual(bav.categorize_geometry("z_section"), "crippling")

    def test_hat_section_maps_to_crippling_mode(self):
        self.assertEqual(bav.categorize_geometry("hat_section"), "crippling")

    def test_unknown_geometry_raises(self):
        with self.assertRaises(ValueError):
            bav.categorize_geometry("magic_truss")


class KnockdownFactorBoundsTest(unittest.TestCase):
    def test_plate_bounds(self):
        self.assertEqual(bav.knockdown_factor_bounds("plate"), (0.5, 1.0))

    def test_shell_bounds(self):
        self.assertEqual(bav.knockdown_factor_bounds("shell"), (0.1, 1.0))

    def test_column_bounds(self):
        self.assertEqual(bav.knockdown_factor_bounds("column"), (0.5, 1.0))

    def test_crippling_bounds(self):
        self.assertEqual(bav.knockdown_factor_bounds("crippling"), (0.3, 1.0))

    def test_unknown_mode_raises(self):
        with self.assertRaises(ValueError):
            bav.knockdown_factor_bounds("torsional_flutter")


class ValidateKnockdownFactorTest(unittest.TestCase):
    def test_valid_plate_factor_passes(self):
        self.assertTrue(bav.validate_knockdown_factor(0.75, "plate"))

    def test_valid_shell_factor_at_lower_bound_passes(self):
        self.assertTrue(bav.validate_knockdown_factor(0.1, "shell"))

    def test_valid_crippling_factor_passes(self):
        self.assertTrue(bav.validate_knockdown_factor(0.5, "crippling"))

    def test_factor_below_plate_lower_bound_raises(self):
        with self.assertRaises(ValueError):
            bav.validate_knockdown_factor(0.3, "plate")

    def test_factor_below_crippling_lower_bound_raises(self):
        with self.assertRaises(ValueError):
            bav.validate_knockdown_factor(0.2, "crippling")

    def test_factor_above_one_raises(self):
        with self.assertRaises(ValueError):
            bav.validate_knockdown_factor(1.1, "plate")

    def test_zero_factor_raises(self):
        with self.assertRaises(ValueError):
            bav.validate_knockdown_factor(0.0, "shell")

    def test_negative_factor_raises(self):
        with self.assertRaises(ValueError):
            bav.validate_knockdown_factor(-0.5, "column")


class CriticalBucklingLoadTest(unittest.TestCase):
    def test_critical_load_is_classical_times_knockdown(self):
        result = bav.critical_buckling_load(1000.0, 0.6)
        self.assertAlmostEqual(result, 600.0)

    def test_knockdown_of_one_leaves_load_unchanged(self):
        result = bav.critical_buckling_load(500.0, 1.0)
        self.assertAlmostEqual(result, 500.0)

    def test_zero_classical_load_raises(self):
        with self.assertRaises(ValueError):
            bav.critical_buckling_load(0.0, 0.7)

    def test_negative_classical_load_raises(self):
        with self.assertRaises(ValueError):
            bav.critical_buckling_load(-100.0, 0.7)

    def test_knockdown_above_one_raises(self):
        with self.assertRaises(ValueError):
            bav.critical_buckling_load(1000.0, 1.5)

    def test_zero_knockdown_raises(self):
        with self.assertRaises(ValueError):
            bav.critical_buckling_load(1000.0, 0.0)


class ReserveFactorTest(unittest.TestCase):
    def test_reserve_factor_arithmetic(self):
        # critical=600, applied=200, fos=1.5 → RF = 600/(200*1.5) = 2.0
        rf = bav.reserve_factor(600.0, 200.0, 1.5)
        self.assertAlmostEqual(rf, 2.0)

    def test_minimum_passing_rf(self):
        # critical=150, applied=100, fos=1.5 → RF = 150/150 = 1.0
        rf = bav.reserve_factor(150.0, 100.0, 1.5)
        self.assertAlmostEqual(rf, 1.0)

    def test_failing_rf_below_one(self):
        # critical=100, applied=200, fos=1.0 → RF = 0.5
        rf = bav.reserve_factor(100.0, 200.0, 1.0)
        self.assertAlmostEqual(rf, 0.5)

    def test_zero_applied_load_raises(self):
        with self.assertRaises(ValueError):
            bav.reserve_factor(500.0, 0.0, 1.5)

    def test_negative_critical_load_raises(self):
        with self.assertRaises(ValueError):
            bav.reserve_factor(-500.0, 200.0, 1.5)

    def test_fos_below_one_raises(self):
        with self.assertRaises(ValueError):
            bav.reserve_factor(500.0, 200.0, 0.9)


class BucklingStatusTest(unittest.TestCase):
    def test_rf_at_minimum_is_adequate(self):
        self.assertEqual(bav.buckling_status(1.0), "adequate")

    def test_rf_above_minimum_is_adequate(self):
        self.assertEqual(bav.buckling_status(2.5), "adequate")

    def test_rf_below_minimum_is_margin_deficient(self):
        self.assertEqual(bav.buckling_status(0.99), "margin_deficient")

    def test_rf_well_below_minimum_is_margin_deficient(self):
        self.assertEqual(bav.buckling_status(0.5), "margin_deficient")


class BucklingComponentReviewTest(unittest.TestCase):
    def _make_component(self, geometry_type, classical_load_n, knockdown_factor,
                        applied_load_n, factor_of_safety, component_id="comp-1"):
        return {
            "component_id": component_id,
            "geometry_type": geometry_type,
            "classical_load_n": classical_load_n,
            "knockdown_factor": knockdown_factor,
            "applied_load_n": applied_load_n,
            "factor_of_safety": factor_of_safety,
        }

    def test_compliant_plate_component(self):
        # critical = 1000*0.7 = 700; RF = 700/(200*1.5) = 2.33 → adequate
        comp = self._make_component("flat_plate", 1000.0, 0.7, 200.0, 1.5)
        review = bav.buckling_component_review(comp)
        self.assertEqual(review["buckling_mode"], "plate")
        self.assertAlmostEqual(review["critical_load_n"], 700.0)
        self.assertGreater(review["reserve_factor"], 1.0)
        self.assertEqual(review["status"], "adequate")
        self.assertEqual(review["violations"], [])
        self.assertTrue(bav.is_buckling_compliant(review))

    def test_margin_deficient_shell_component(self):
        # critical = 500*0.15 = 75; RF = 75/(200*1.5) = 0.25 → deficient
        comp = self._make_component("cylindrical_shell", 500.0, 0.15, 200.0, 1.5)
        review = bav.buckling_component_review(comp)
        self.assertEqual(review["buckling_mode"], "shell")
        self.assertEqual(review["status"], "margin_deficient")
        violation_issues = [v["issue"] for v in review["violations"]]
        self.assertIn("buckling_margin_deficient", violation_issues)
        self.assertFalse(bav.is_buckling_compliant(review))

    def test_knockdown_out_of_bounds_flagged(self):
        # KDF 0.3 is below plate lower bound 0.5
        comp = self._make_component("flat_plate", 1000.0, 0.3, 100.0, 1.5)
        review = bav.buckling_component_review(comp)
        violation_issues = [v["issue"] for v in review["violations"]]
        self.assertIn("knockdown_factor_out_of_bounds", violation_issues)
        self.assertFalse(bav.is_buckling_compliant(review))

    def test_column_component_compliant(self):
        # critical = 2000*0.8 = 1600; RF = 1600/(400*1.5) = 2.67 → adequate
        comp = self._make_component("column", 2000.0, 0.8, 400.0, 1.5)
        review = bav.buckling_component_review(comp)
        self.assertEqual(review["buckling_mode"], "column")
        self.assertEqual(review["status"], "adequate")
        self.assertEqual(review["violations"], [])

    def test_crippling_component_at_exact_rf_one(self):
        # critical = 900*0.5 = 450; RF = 450/(300*1.5) = 1.0 → adequate
        comp = self._make_component("channel_section", 900.0, 0.5, 300.0, 1.5)
        review = bav.buckling_component_review(comp)
        self.assertAlmostEqual(review["reserve_factor"], 1.0)
        self.assertEqual(review["status"], "adequate")
        self.assertEqual(review["violations"], [])

    def test_unknown_geometry_raises(self):
        comp = self._make_component("mystery_tube", 1000.0, 0.7, 200.0, 1.5)
        with self.assertRaises(ValueError):
            bav.buckling_component_review(comp)

    def test_review_does_not_mutate_input(self):
        comp = self._make_component("flat_plate", 1000.0, 0.7, 200.0, 1.5)
        original_keys = set(comp.keys())
        bav.buckling_component_review(comp)
        self.assertEqual(set(comp.keys()), original_keys)


if __name__ == "__main__":
    unittest.main(verbosity=2)
