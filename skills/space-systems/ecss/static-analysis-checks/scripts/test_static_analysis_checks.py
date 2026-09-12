#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C section 5.5 static analysis checks.

Exercises scripts/static_analysis_checks_logic.py (stdlib unittest,
offline). Contract: reaction equilibrium is PASS when the maximum relative
residual is within tolerance and FAIL when it exceeds tolerance; an empty
applied_forces list, a length mismatch, or an out-of-range tolerance yields
ERROR. Energy balance is PASS when the relative error between external work
and strain energy is within tolerance and FAIL when it exceeds tolerance;
negative inputs or an out-of-range tolerance yields ERROR; both inputs being
zero is a trivial PASS; strain energy zero with nonzero work is FAIL. Solver
convergence is PASS when the dimensionless residual norm is at or below the
threshold and FAIL when it exceeds it; a negative residual or non-positive
tolerance yields ERROR. run_static_analysis_checks returns three ordered
results when all required keys are present and a single ERROR result when
a required key is missing. all_checks_pass returns True only when every
result status is PASS.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import static_analysis_checks_logic as sa  # noqa: E402


class ReactionsEquilibriumTest(unittest.TestCase):

    def test_perfect_balance_passes(self):
        result = sa.check_reactions([100.0, 0.0, -50.0], [-100.0, 0.0, 50.0])
        self.assertEqual(result["status"], sa.PASS)

    def test_small_residual_within_one_pct_passes(self):
        # residual = 0.5 N, scale = 100 N, rel = 0.005 < 0.01
        result = sa.check_reactions([100.0], [-99.5])
        self.assertEqual(result["status"], sa.PASS)
        self.assertAlmostEqual(result["details"]["max_rel_residual"], 0.005)

    def test_large_residual_fails(self):
        # residual = 5 N, scale = 100 N, rel = 0.05 > 0.01
        result = sa.check_reactions([100.0], [-95.0])
        self.assertEqual(result["status"], sa.FAIL)

    def test_all_zero_forces_trivially_passes(self):
        result = sa.check_reactions([0.0, 0.0], [0.0, 0.0])
        self.assertEqual(result["status"], sa.PASS)
        self.assertIn("trivially", result["message"])

    def test_empty_applied_forces_is_error(self):
        result = sa.check_reactions([], [])
        self.assertEqual(result["status"], sa.ERROR)
        self.assertIn("empty", result["message"])

    def test_length_mismatch_is_error(self):
        result = sa.check_reactions([100.0, 200.0], [-100.0])
        self.assertEqual(result["status"], sa.ERROR)
        self.assertIn("mismatch", result["message"].lower())

    def test_tolerance_zero_is_error(self):
        result = sa.check_reactions([100.0], [-100.0], tolerance_pct=0.0)
        self.assertEqual(result["status"], sa.ERROR)

    def test_tolerance_100_is_error(self):
        result = sa.check_reactions([100.0], [-100.0], tolerance_pct=100.0)
        self.assertEqual(result["status"], sa.ERROR)

    def test_exact_tolerance_boundary_passes(self):
        # residual = 1 N, scale = 100 N, rel = 0.01 == tolerance 1 %
        result = sa.check_reactions([100.0], [-99.0], tolerance_pct=1.0)
        self.assertEqual(result["status"], sa.PASS)

    def test_multi_axis_largest_residual_governs(self):
        # axis 0: residual 0, axis 1: residual 3, scale=100, rel=0.03 > 0.01
        result = sa.check_reactions([100.0, 100.0], [-100.0, -97.0])
        self.assertEqual(result["status"], sa.FAIL)
        self.assertAlmostEqual(result["details"]["max_rel_residual"], 0.03)


class EnergyBalanceTest(unittest.TestCase):

    def test_perfect_balance_passes(self):
        result = sa.check_energy_balance(500.0, 500.0)
        self.assertEqual(result["status"], sa.PASS)

    def test_small_relative_error_passes(self):
        # rel error = |505 - 500| / 500 = 0.01 == 1 % tolerance
        result = sa.check_energy_balance(505.0, 500.0, tolerance_pct=1.0)
        self.assertEqual(result["status"], sa.PASS)

    def test_large_relative_error_fails(self):
        # rel error = |550 - 500| / 500 = 0.10 > 0.01
        result = sa.check_energy_balance(550.0, 500.0)
        self.assertEqual(result["status"], sa.FAIL)

    def test_both_zero_trivially_passes(self):
        result = sa.check_energy_balance(0.0, 0.0)
        self.assertEqual(result["status"], sa.PASS)
        self.assertIn("trivially", result["message"])

    def test_nonzero_work_with_zero_strain_energy_fails(self):
        result = sa.check_energy_balance(10.0, 0.0)
        self.assertEqual(result["status"], sa.FAIL)
        self.assertIn("zero", result["message"].lower())

    def test_negative_external_work_is_error(self):
        result = sa.check_energy_balance(-1.0, 500.0)
        self.assertEqual(result["status"], sa.ERROR)
        self.assertIn("external_work", result["message"])

    def test_negative_strain_energy_is_error(self):
        result = sa.check_energy_balance(500.0, -1.0)
        self.assertEqual(result["status"], sa.ERROR)
        self.assertIn("strain_energy", result["message"])

    def test_invalid_tolerance_is_error(self):
        result = sa.check_energy_balance(500.0, 500.0, tolerance_pct=0.0)
        self.assertEqual(result["status"], sa.ERROR)

    def test_details_contain_relative_error(self):
        result = sa.check_energy_balance(510.0, 500.0)
        self.assertIn("relative_error", result["details"])
        self.assertAlmostEqual(result["details"]["relative_error"], 0.02)


class SolverConvergenceTest(unittest.TestCase):

    def test_residual_below_threshold_passes(self):
        result = sa.check_solver_convergence(1e-8, tolerance=1e-6)
        self.assertEqual(result["status"], sa.PASS)

    def test_residual_at_threshold_passes(self):
        result = sa.check_solver_convergence(1e-6, tolerance=1e-6)
        self.assertEqual(result["status"], sa.PASS)

    def test_residual_above_threshold_fails(self):
        result = sa.check_solver_convergence(1e-4, tolerance=1e-6)
        self.assertEqual(result["status"], sa.FAIL)

    def test_negative_residual_is_error(self):
        result = sa.check_solver_convergence(-1e-8)
        self.assertEqual(result["status"], sa.ERROR)
        self.assertIn("residual_norm", result["message"])

    def test_zero_tolerance_is_error(self):
        result = sa.check_solver_convergence(1e-8, tolerance=0.0)
        self.assertEqual(result["status"], sa.ERROR)
        self.assertIn("tolerance", result["message"])

    def test_details_contain_residual_and_tolerance(self):
        result = sa.check_solver_convergence(5e-7, tolerance=1e-6)
        self.assertIn("residual_norm", result["details"])
        self.assertIn("tolerance", result["details"])
        self.assertAlmostEqual(result["details"]["residual_norm"], 5e-7)


class RunAllChecksTest(unittest.TestCase):

    def _good_model(self):
        return {
            "applied_forces": [1000.0, 0.0, -500.0],
            "reaction_forces": [-1000.0, 0.0, 500.0],
            "external_work": 250.0,
            "strain_energy": 250.0,
            "residual_norm": 1e-10,
        }

    def test_all_passing_model_returns_three_results(self):
        results = sa.run_static_analysis_checks(self._good_model())
        self.assertEqual(len(results), 3)
        statuses = [r["status"] for r in results]
        self.assertEqual(statuses, [sa.PASS, sa.PASS, sa.PASS])

    def test_all_checks_pass_helper_true_for_passing_model(self):
        results = sa.run_static_analysis_checks(self._good_model())
        self.assertTrue(sa.all_checks_pass(results))

    def test_missing_required_key_returns_single_error(self):
        data = self._good_model()
        del data["strain_energy"]
        results = sa.run_static_analysis_checks(data)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["status"], sa.ERROR)
        self.assertIn("strain_energy", results[0]["message"])

    def test_all_checks_pass_false_when_one_fails(self):
        data = self._good_model()
        data["residual_norm"] = 0.5   # far above default tolerance
        results = sa.run_static_analysis_checks(data)
        self.assertFalse(sa.all_checks_pass(results))

    def test_result_order_is_reactions_energy_convergence(self):
        results = sa.run_static_analysis_checks(self._good_model())
        self.assertEqual(results[0]["name"], "reactions")
        self.assertEqual(results[1]["name"], "energy_balance")
        self.assertEqual(results[2]["name"], "convergence")

    def test_custom_tolerances_respected(self):
        data = self._good_model()
        # Force a 2 % reaction residual; default 1 % tol fails, 5 % tol passes.
        data["applied_forces"] = [100.0]
        data["reaction_forces"] = [-98.0]   # residual = 2 N, scale = 100, rel = 0.02
        data["reaction_tol_pct"] = 5.0
        results = sa.run_static_analysis_checks(data)
        self.assertEqual(results[0]["status"], sa.PASS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
