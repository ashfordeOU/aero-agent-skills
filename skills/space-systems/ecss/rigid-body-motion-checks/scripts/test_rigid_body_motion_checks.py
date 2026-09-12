"""
Gate-3 contract tests for rigid_body_motion_checks_logic.
Stdlib unittest only. Run: python3 test_rigid_body_motion_checks.py
"""

import sys
import os
import unittest

# Allow running from any working directory
sys.path.insert(0, os.path.dirname(__file__))

from rigid_body_motion_checks_logic import (
    RB_MODE_LABELS,
    aggregate_rigid_body_check,
    check_mass_matrix,
    check_residual_force_per_mode,
    check_residual_forces_all_modes,
    check_strain_energy_all_modes,
    check_strain_energy_per_mode,
)


def _all_near_zero_energies(threshold=1e-6):
    return {lbl: 0.0 for lbl in RB_MODE_LABELS}


def _all_near_zero_residuals(threshold=1e-6):
    return {lbl: 0.0 for lbl in RB_MODE_LABELS}


class TestMassCheck(unittest.TestCase):

    def test_mass_check_pass_exact(self):
        r = check_mass_matrix(100.0, 100.0, 0.01)
        self.assertTrue(r.passed)
        self.assertAlmostEqual(r.relative_error, 0.0)

    def test_mass_check_pass_within_tolerance(self):
        r = check_mass_matrix(100.0, 100.5, 0.01)
        self.assertTrue(r.passed)
        self.assertAlmostEqual(r.relative_error, 0.005)

    def test_mass_check_fail_exceeds_tolerance(self):
        r = check_mass_matrix(100.0, 103.0, 0.01)
        self.assertFalse(r.passed)
        self.assertAlmostEqual(r.relative_error, 0.03)
        self.assertIn("FAIL", r.message)

    def test_mass_check_fail_below_expected(self):
        r = check_mass_matrix(100.0, 95.0, 0.02)
        self.assertFalse(r.passed)
        self.assertAlmostEqual(r.relative_error, 0.05)

    def test_mass_check_invalid_expected_mass_zero(self):
        with self.assertRaises(ValueError):
            check_mass_matrix(0.0, 100.0, 0.01)

    def test_mass_check_invalid_expected_mass_negative(self):
        with self.assertRaises(ValueError):
            check_mass_matrix(-5.0, 100.0, 0.01)

    def test_mass_check_invalid_tolerance_zero(self):
        with self.assertRaises(ValueError):
            check_mass_matrix(100.0, 100.0, 0.0)

    def test_mass_check_invalid_tolerance_above_one(self):
        with self.assertRaises(ValueError):
            check_mass_matrix(100.0, 100.0, 1.5)

    def test_mass_check_invalid_computed_mass_negative(self):
        with self.assertRaises(ValueError):
            check_mass_matrix(100.0, -1.0, 0.01)

    def test_mass_check_message_contains_pass(self):
        r = check_mass_matrix(200.0, 200.0, 0.005)
        self.assertIn("PASS", r.message)


class TestStrainEnergyCheck(unittest.TestCase):

    def test_strain_energy_per_mode_pass(self):
        r = check_strain_energy_per_mode("TX", 1e-10, 1e-6)
        self.assertTrue(r.passed)
        self.assertIn("PASS", r.message)

    def test_strain_energy_per_mode_fail(self):
        r = check_strain_energy_per_mode("RZ", 5e-4, 1e-6)
        self.assertFalse(r.passed)
        self.assertIn("FAIL", r.message)

    def test_strain_energy_per_mode_invalid_label(self):
        with self.assertRaises(ValueError):
            check_strain_energy_per_mode("TX1", 0.0, 1e-6)

    def test_strain_energy_per_mode_negative_energy(self):
        with self.assertRaises(ValueError):
            check_strain_energy_per_mode("TY", -1.0, 1e-6)

    def test_strain_energy_per_mode_non_positive_threshold(self):
        with self.assertRaises(ValueError):
            check_strain_energy_per_mode("TZ", 0.0, 0.0)

    def test_strain_energy_all_modes_pass(self):
        energies = {lbl: 1e-12 for lbl in RB_MODE_LABELS}
        results = check_strain_energy_all_modes(energies, 1e-6)
        self.assertEqual(len(results), 6)
        self.assertTrue(all(r.passed for r in results))

    def test_strain_energy_all_modes_some_fail(self):
        energies = {lbl: 1e-12 for lbl in RB_MODE_LABELS}
        energies["RX"] = 1e-3  # exceeds threshold
        results = check_strain_energy_all_modes(energies, 1e-6)
        failing = [r for r in results if not r.passed]
        self.assertEqual(len(failing), 1)
        self.assertEqual(failing[0].mode_label, "RX")

    def test_strain_energy_all_modes_missing_label(self):
        energies = {lbl: 0.0 for lbl in RB_MODE_LABELS if lbl != "TZ"}
        with self.assertRaises(ValueError):
            check_strain_energy_all_modes(energies, 1e-6)

    def test_strain_energy_all_modes_extra_label(self):
        energies = {lbl: 0.0 for lbl in RB_MODE_LABELS}
        energies["TX2"] = 0.0
        with self.assertRaises(ValueError):
            check_strain_energy_all_modes(energies, 1e-6)

    def test_strain_energy_label_order_preserved(self):
        energies = {lbl: float(i) * 1e-8 for i, lbl in enumerate(RB_MODE_LABELS)}
        results = check_strain_energy_all_modes(energies, 1e-6)
        for result, label in zip(results, RB_MODE_LABELS):
            self.assertEqual(result.mode_label, label)


class TestResidualForceCheck(unittest.TestCase):

    def test_residual_force_per_mode_pass(self):
        r = check_residual_force_per_mode("TX", 1e-9, 1e-5)
        self.assertTrue(r.passed)
        self.assertIn("PASS", r.message)

    def test_residual_force_per_mode_fail(self):
        r = check_residual_force_per_mode("RY", 0.5, 1e-5)
        self.assertFalse(r.passed)
        self.assertIn("FAIL", r.message)

    def test_residual_force_per_mode_invalid_label(self):
        with self.assertRaises(ValueError):
            check_residual_force_per_mode("T4", 0.0, 1e-5)

    def test_residual_force_per_mode_negative_residual(self):
        with self.assertRaises(ValueError):
            check_residual_force_per_mode("TZ", -0.1, 1e-5)

    def test_residual_force_per_mode_non_positive_threshold(self):
        with self.assertRaises(ValueError):
            check_residual_force_per_mode("RZ", 0.0, -1.0)

    def test_residual_force_all_modes_pass(self):
        residuals = {lbl: 1e-10 for lbl in RB_MODE_LABELS}
        results = check_residual_forces_all_modes(residuals, 1e-5)
        self.assertEqual(len(results), 6)
        self.assertTrue(all(r.passed for r in results))

    def test_residual_force_all_modes_two_fail(self):
        residuals = {lbl: 1e-10 for lbl in RB_MODE_LABELS}
        residuals["TY"] = 1.0
        residuals["RZ"] = 2.0
        results = check_residual_forces_all_modes(residuals, 1e-5)
        failing = [r for r in results if not r.passed]
        self.assertEqual(len(failing), 2)
        failing_labels = {r.mode_label for r in failing}
        self.assertEqual(failing_labels, {"TY", "RZ"})

    def test_residual_force_all_modes_missing_label(self):
        residuals = {lbl: 0.0 for lbl in RB_MODE_LABELS if lbl != "RX"}
        with self.assertRaises(ValueError):
            check_residual_forces_all_modes(residuals, 1e-5)


class TestAggregateRigidBodyCheck(unittest.TestCase):

    def _passing_mass(self):
        return check_mass_matrix(100.0, 100.0, 0.01)

    def _failing_mass(self):
        return check_mass_matrix(100.0, 115.0, 0.01)

    def _all_passing_se(self):
        return check_strain_energy_all_modes(
            {lbl: 1e-12 for lbl in RB_MODE_LABELS}, 1e-6
        )

    def _all_passing_rf(self):
        return check_residual_forces_all_modes(
            {lbl: 1e-12 for lbl in RB_MODE_LABELS}, 1e-5
        )

    def test_aggregate_all_pass(self):
        summary = aggregate_rigid_body_check(
            self._passing_mass(), self._all_passing_se(), self._all_passing_rf()
        )
        self.assertTrue(summary.overall_passed)
        self.assertEqual(len(summary.findings), 0)

    def test_aggregate_mass_fail_propagates(self):
        summary = aggregate_rigid_body_check(
            self._failing_mass(), self._all_passing_se(), self._all_passing_rf()
        )
        self.assertFalse(summary.overall_passed)
        self.assertEqual(len(summary.findings), 1)
        self.assertIn("FAIL", summary.findings[0])

    def test_aggregate_strain_energy_fail_propagates(self):
        energies = {lbl: 1e-12 for lbl in RB_MODE_LABELS}
        energies["RX"] = 9.9  # well above threshold
        se_results = check_strain_energy_all_modes(energies, 1e-6)
        summary = aggregate_rigid_body_check(
            self._passing_mass(), se_results, self._all_passing_rf()
        )
        self.assertFalse(summary.overall_passed)
        self.assertEqual(len(summary.findings), 1)

    def test_aggregate_residual_force_fail_propagates(self):
        residuals = {lbl: 1e-12 for lbl in RB_MODE_LABELS}
        residuals["TZ"] = 9.9
        rf_results = check_residual_forces_all_modes(residuals, 1e-5)
        summary = aggregate_rigid_body_check(
            self._passing_mass(), self._all_passing_se(), rf_results
        )
        self.assertFalse(summary.overall_passed)
        self.assertEqual(len(summary.findings), 1)

    def test_aggregate_multiple_failures_all_collected(self):
        energies = {lbl: 1e-12 for lbl in RB_MODE_LABELS}
        energies["TY"] = 1.0
        energies["RZ"] = 1.0
        se_results = check_strain_energy_all_modes(energies, 1e-6)
        summary = aggregate_rigid_body_check(
            self._failing_mass(), se_results, self._all_passing_rf()
        )
        self.assertFalse(summary.overall_passed)
        # 1 mass finding + 2 strain energy findings
        self.assertEqual(len(summary.findings), 3)

    def test_aggregate_result_counts_match_six_modes(self):
        summary = aggregate_rigid_body_check(
            self._passing_mass(), self._all_passing_se(), self._all_passing_rf()
        )
        self.assertEqual(len(summary.strain_energy_results), 6)
        self.assertEqual(len(summary.residual_force_results), 6)


if __name__ == "__main__":
    unittest.main()
