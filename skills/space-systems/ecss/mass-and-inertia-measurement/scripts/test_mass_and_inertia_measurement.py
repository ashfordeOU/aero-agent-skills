"""
Gate 3 contract tests for mass_and_inertia_measurement_logic.py.
stdlib unittest only — offline, deterministic.
Run: python3 test_mass_and_inertia_measurement.py
"""

import math
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from mass_and_inertia_measurement_logic import (
    TWO_PI_SQUARED,
    aggregate_report,
    calibrate_torsion_constant,
    check_inertia_tensor_symmetry,
    compute_fixture_corrected_inertia,
    compute_moment_of_inertia,
    validate_cg,
    validate_inertia,
    validate_mass,
)


# ---------------------------------------------------------------------------
# compute_moment_of_inertia
# ---------------------------------------------------------------------------

class TestComputeMomentOfInertia(unittest.TestCase):
    def test_formula_correctness(self):
        k, T = 100.0, 2.0
        expected = k * T ** 2 / TWO_PI_SQUARED
        self.assertAlmostEqual(compute_moment_of_inertia(T, k), expected, places=12)

    def test_zero_period_raises(self):
        with self.assertRaises(ValueError):
            compute_moment_of_inertia(0.0, 50.0)

    def test_negative_period_raises(self):
        with self.assertRaises(ValueError):
            compute_moment_of_inertia(-1.0, 50.0)

    def test_zero_torsion_constant_raises(self):
        with self.assertRaises(ValueError):
            compute_moment_of_inertia(1.0, 0.0)

    def test_negative_torsion_constant_raises(self):
        with self.assertRaises(ValueError):
            compute_moment_of_inertia(1.0, -10.0)

    def test_larger_period_gives_larger_inertia(self):
        k = 80.0
        i_short = compute_moment_of_inertia(1.0, k)
        i_long = compute_moment_of_inertia(2.0, k)
        self.assertLess(i_short, i_long)


# ---------------------------------------------------------------------------
# compute_fixture_corrected_inertia
# ---------------------------------------------------------------------------

class TestFixtureCorrectedInertia(unittest.TestCase):
    def test_subtraction_algebraically_correct(self):
        k, T_total, T_fix = 80.0, 3.0, 2.0
        expected = k * (T_total ** 2 - T_fix ** 2) / TWO_PI_SQUARED
        result = compute_fixture_corrected_inertia(T_total, T_fix, k)
        self.assertAlmostEqual(result, expected, places=12)

    def test_fixture_period_equal_to_total_raises(self):
        with self.assertRaises(ValueError):
            compute_fixture_corrected_inertia(2.0, 2.0, 80.0)

    def test_fixture_period_greater_than_total_raises(self):
        with self.assertRaises(ValueError):
            compute_fixture_corrected_inertia(1.0, 2.0, 80.0)

    def test_result_is_positive(self):
        result = compute_fixture_corrected_inertia(3.0, 1.0, 60.0)
        self.assertGreater(result, 0.0)


# ---------------------------------------------------------------------------
# calibrate_torsion_constant
# ---------------------------------------------------------------------------

class TestCalibrateTorsionConstant(unittest.TestCase):
    def test_round_trip_recovers_reference_inertia(self):
        I_ref, k_true, T_base = 5.0, 120.0, 1.0
        T_ref = math.sqrt(I_ref * TWO_PI_SQUARED / k_true + T_base ** 2)
        k_calc = calibrate_torsion_constant(I_ref, T_ref, T_base)
        self.assertAlmostEqual(k_calc, k_true, places=8)

    def test_reference_period_must_exceed_base(self):
        with self.assertRaises(ValueError):
            calibrate_torsion_constant(5.0, 1.0, 1.5)

    def test_equal_periods_raises(self):
        with self.assertRaises(ValueError):
            calibrate_torsion_constant(5.0, 2.0, 2.0)

    def test_zero_reference_inertia_raises(self):
        with self.assertRaises(ValueError):
            calibrate_torsion_constant(0.0, 2.0, 1.0)

    def test_negative_reference_inertia_raises(self):
        with self.assertRaises(ValueError):
            calibrate_torsion_constant(-1.0, 2.0, 1.0)

    def test_result_is_positive(self):
        k = calibrate_torsion_constant(3.0, 2.0, 1.0)
        self.assertGreater(k, 0.0)


# ---------------------------------------------------------------------------
# validate_mass
# ---------------------------------------------------------------------------

class TestValidateMass(unittest.TestCase):
    def test_within_tolerance_passes(self):
        result = validate_mass(10.4, 10.0, 0.10)
        self.assertTrue(result["pass"])
        self.assertIsNone(result["finding"])

    def test_exceeds_tolerance_fails(self):
        result = validate_mass(11.5, 10.0, 0.10)
        self.assertFalse(result["pass"])
        self.assertIsNotNone(result["finding"])

    def test_exact_boundary_passes(self):
        result = validate_mass(10.5, 10.0, 0.05)
        self.assertTrue(result["pass"])

    def test_deviation_sign_negative(self):
        result = validate_mass(9.0, 10.0, 0.20)
        self.assertTrue(result["pass"])
        self.assertAlmostEqual(result["deviation_fraction"], -0.10, places=10)

    def test_negative_measured_raises(self):
        with self.assertRaises(ValueError):
            validate_mass(-1.0, 10.0, 0.05)

    def test_zero_predicted_raises(self):
        with self.assertRaises(ValueError):
            validate_mass(10.0, 0.0, 0.05)

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            validate_mass(10.0, 10.0, -0.01)

    def test_result_keys_present(self):
        result = validate_mass(10.0, 10.0, 0.05)
        for key in ("measured_kg", "predicted_kg", "deviation_fraction",
                    "tolerance_fraction", "pass", "finding"):
            self.assertIn(key, result)


# ---------------------------------------------------------------------------
# validate_cg
# ---------------------------------------------------------------------------

class TestValidateCG(unittest.TestCase):
    def test_all_axes_pass(self):
        result = validate_cg((1.001, 0.002, -0.003), (1.0, 0.0, 0.0), 0.005)
        self.assertTrue(result["overall_pass"])
        self.assertEqual(result["findings"], [])

    def test_one_axis_fail(self):
        result = validate_cg((1.01, 0.0, 0.0), (1.0, 0.0, 0.0), 0.005)
        self.assertFalse(result["overall_pass"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertIn("x", result["findings"][0])

    def test_all_axes_fail(self):
        result = validate_cg((1.1, 0.1, -0.1), (1.0, 0.0, 0.0), 0.005)
        self.assertFalse(result["overall_pass"])
        self.assertEqual(len(result["findings"]), 3)

    def test_euclidean_distance_computed(self):
        result = validate_cg((1.003, 0.004, 0.0), (1.0, 0.0, 0.0), 0.01)
        expected_euc = math.sqrt(0.003 ** 2 + 0.004 ** 2)
        self.assertAlmostEqual(result["euclidean_distance_m"], expected_euc, places=10)

    def test_wrong_dimension_raises(self):
        with self.assertRaises(ValueError):
            validate_cg((1.0, 2.0), (1.0, 2.0, 3.0), 0.01)

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            validate_cg((1.0, 0.0, 0.0), (1.0, 0.0, 0.0), -0.001)

    def test_zero_offset_passes(self):
        result = validate_cg((1.0, 0.0, 0.0), (1.0, 0.0, 0.0), 0.0)
        self.assertTrue(result["overall_pass"])


# ---------------------------------------------------------------------------
# validate_inertia
# ---------------------------------------------------------------------------

class TestValidateInertia(unittest.TestCase):
    def test_pass_within_tolerance(self):
        result = validate_inertia(10.2, 10.0, 0.05, "Ixx")
        self.assertTrue(result["pass"])
        self.assertIsNone(result["finding"])

    def test_fail_outside_tolerance(self):
        result = validate_inertia(10.6, 10.0, 0.05, "Iyy")
        self.assertFalse(result["pass"])
        self.assertIn("Iyy", result["finding"])

    def test_axis_label_in_finding(self):
        result = validate_inertia(20.0, 10.0, 0.05, "Izz")
        self.assertIn("Izz", result["finding"])

    def test_negative_measured_raises(self):
        with self.assertRaises(ValueError):
            validate_inertia(-1.0, 10.0, 0.05)

    def test_zero_predicted_raises(self):
        with self.assertRaises(ValueError):
            validate_inertia(10.0, 0.0, 0.05)

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            validate_inertia(10.0, 10.0, -0.01)

    def test_exact_boundary_passes(self):
        result = validate_inertia(10.5, 10.0, 0.05)
        self.assertTrue(result["pass"])


# ---------------------------------------------------------------------------
# check_inertia_tensor_symmetry
# ---------------------------------------------------------------------------

class TestInertiaTensorSymmetry(unittest.TestCase):
    def test_symmetric_tensor_passes(self):
        tensor = [
            [100.0, -5.0,  3.0],
            [ -5.0, 80.0, -2.0],
            [  3.0, -2.0, 60.0],
        ]
        result = check_inertia_tensor_symmetry(tensor)
        self.assertTrue(result["symmetric"])
        self.assertEqual(result["findings"], [])

    def test_asymmetric_tensor_fails(self):
        tensor = [
            [100.0, -5.0,  3.0],
            [ -6.0, 80.0, -2.0],
            [  3.0, -2.0, 60.0],
        ]
        result = check_inertia_tensor_symmetry(tensor)
        self.assertFalse(result["symmetric"])
        self.assertGreater(len(result["findings"]), 0)

    def test_wrong_shape_raises(self):
        with self.assertRaises(ValueError):
            check_inertia_tensor_symmetry([[1, 2], [3, 4]])

    def test_single_asymmetry_finding_identified(self):
        tensor = [
            [100.0, -5.0,  3.0],
            [ -5.0, 80.0, -2.0],
            [  3.0, -3.0, 60.0],  # I[1][2]=-2 vs I[2][1]=-3
        ]
        result = check_inertia_tensor_symmetry(tensor)
        self.assertFalse(result["symmetric"])
        self.assertEqual(len(result["findings"]), 1)

    def test_diagonal_only_tensor_is_symmetric(self):
        tensor = [
            [100.0, 0.0, 0.0],
            [  0.0, 80.0, 0.0],
            [  0.0,  0.0, 60.0],
        ]
        result = check_inertia_tensor_symmetry(tensor)
        self.assertTrue(result["symmetric"])


# ---------------------------------------------------------------------------
# aggregate_report
# ---------------------------------------------------------------------------

class TestAggregateReport(unittest.TestCase):
    def test_all_pass_gives_overall_pass(self):
        mass = validate_mass(10.0, 10.0, 0.05)
        cg = validate_cg((1.0, 0.0, 0.0), (1.0, 0.0, 0.0), 0.005)
        inertia = [validate_inertia(100.0, 100.0, 0.05, "Ixx")]
        report = aggregate_report(mass, cg, inertia)
        self.assertTrue(report["overall_pass"])
        self.assertEqual(report["findings"], [])

    def test_mass_failure_propagates(self):
        mass = validate_mass(12.0, 10.0, 0.05)
        cg = validate_cg((1.0, 0.0, 0.0), (1.0, 0.0, 0.0), 0.005)
        inertia = [validate_inertia(100.0, 100.0, 0.05, "Ixx")]
        report = aggregate_report(mass, cg, inertia)
        self.assertFalse(report["overall_pass"])
        self.assertGreater(len(report["findings"]), 0)

    def test_cg_failure_propagates(self):
        mass = validate_mass(10.0, 10.0, 0.05)
        cg = validate_cg((1.1, 0.0, 0.0), (1.0, 0.0, 0.0), 0.005)
        inertia = [validate_inertia(100.0, 100.0, 0.05, "Ixx")]
        report = aggregate_report(mass, cg, inertia)
        self.assertFalse(report["overall_pass"])

    def test_inertia_failure_propagates(self):
        mass = validate_mass(10.0, 10.0, 0.05)
        cg = validate_cg((1.0, 0.0, 0.0), (1.0, 0.0, 0.0), 0.005)
        inertia = [validate_inertia(120.0, 100.0, 0.05, "Iyy")]
        report = aggregate_report(mass, cg, inertia)
        self.assertFalse(report["overall_pass"])

    def test_report_structure_keys(self):
        mass = validate_mass(10.0, 10.0, 0.05)
        cg = validate_cg((1.0, 0.0, 0.0), (1.0, 0.0, 0.0), 0.005)
        inertia = []
        report = aggregate_report(mass, cg, inertia)
        for key in ("overall_pass", "findings", "mass", "cg", "inertia_axes"):
            self.assertIn(key, report)

    def test_multiple_inertia_axes_all_pass(self):
        mass = validate_mass(10.0, 10.0, 0.05)
        cg = validate_cg((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0.01)
        inertia = [
            validate_inertia(100.0, 100.0, 0.05, "Ixx"),
            validate_inertia(80.0, 80.0, 0.05, "Iyy"),
            validate_inertia(60.0, 60.0, 0.05, "Izz"),
        ]
        report = aggregate_report(mass, cg, inertia)
        self.assertTrue(report["overall_pass"])

    def test_multiple_inertia_axes_one_fails(self):
        mass = validate_mass(10.0, 10.0, 0.05)
        cg = validate_cg((0.0, 0.0, 0.0), (0.0, 0.0, 0.0), 0.01)
        inertia = [
            validate_inertia(100.0, 100.0, 0.05, "Ixx"),
            validate_inertia(90.0, 80.0, 0.05, "Iyy"),
        ]
        report = aggregate_report(mass, cg, inertia)
        self.assertFalse(report["overall_pass"])
        self.assertEqual(len(report["findings"]), 1)


if __name__ == "__main__":
    unittest.main()
