#!/usr/bin/env python3
"""Gate 3 contract test: spin flight testing logic.

Exercises scripts/spin_testing_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3. Covers the spin test point
matrix builder (grid combinations, CG envelope flags, empty grid
rejection), the spin phase classification (entry, incipient, developed),
the spin recovery check (turn count and altitude loss against program
limits, unrecoverable verdicts), the recovery parachute requirement
decision, the FAR 25.201 spin resistance check with pro-spin controls,
and invalid-input edge cases (out-of-envelope CG, negative or
non-finite values, empty matrices).
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import spin_testing_logic as spin  # noqa: E402


class ConfigCombinationTest(unittest.TestCase):
    def test_point_dict_fields(self):
        point = spin.config_combination("clean", 30.0, 18000.0, 3000.0)
        self.assertEqual(point["config"], "clean")
        self.assertEqual(point["cg_pct_mac"], 30.0)
        self.assertEqual(point["weight_kg"], 18000.0)
        self.assertEqual(point["altitude_m"], 3000.0)

    def test_empty_config_raises(self):
        with self.assertRaises(ValueError):
            spin.config_combination("", 30.0, 18000.0, 3000.0)

    def test_non_finite_and_negative_raise(self):
        with self.assertRaises(ValueError):
            spin.config_combination("clean", float("nan"), 18000.0, 3000.0)
        with self.assertRaises(ValueError):
            spin.config_combination("clean", 30.0, -100.0, 3000.0)
        with self.assertRaises(ValueError):
            spin.config_combination("clean", 30.0, 18000.0, -5.0)


class SpinTestPointMatrixTest(unittest.TestCase):
    CONFIGS = ["clean", "takeoff-flaps"]
    CGS = [18.0, 30.0, 36.0]
    WEIGHTS = [18000.0, 21000.0]
    ALTITUDES = [3000.0, 6000.0]

    def test_grid_product_count_and_ids(self):
        points = spin.spin_test_point_matrix(
            self.CONFIGS, self.CGS, self.WEIGHTS, self.ALTITUDES
        )
        self.assertEqual(len(points), 2 * 3 * 2 * 2)  # 24 points
        self.assertEqual(points[0]["id"], "sp-01")
        self.assertEqual(points[-1]["id"], "sp-24")

    def test_out_of_envelope_cg_flagged(self):
        points = spin.spin_test_point_matrix(
            self.CONFIGS, self.CGS, self.WEIGHTS, self.ALTITUDES
        )
        for point in points:
            expected = 15.0 <= point["cg_pct_mac"] <= 35.0
            self.assertEqual(point["cg_envelope_ok"], expected, point)
        in_env = [p for p in points if p["cg_envelope_ok"]]
        out_env = [p for p in points if not p["cg_envelope_ok"]]
        self.assertEqual(len(in_env), 2 * 2 * 2 * 2)  # 18.0 and 30.0 %MAC
        self.assertEqual(len(out_env), 1 * 2 * 2 * 2)  # 36.0 %MAC only
        self.assertTrue(all(p["cg_pct_mac"] == 36.0 for p in out_env))

    def test_empty_matrix_raises(self):
        with self.assertRaises(ValueError):
            spin.spin_test_point_matrix([], self.CGS, self.WEIGHTS, self.ALTITUDES)
        with self.assertRaises(ValueError):
            spin.spin_test_point_matrix(self.CONFIGS, [], self.WEIGHTS, self.ALTITUDES)
        with self.assertRaises(ValueError):
            spin.spin_test_point_matrix(self.CONFIGS, self.CGS, [], self.ALTITUDES)
        with self.assertRaises(ValueError):
            spin.spin_test_point_matrix(self.CONFIGS, self.CGS, self.WEIGHTS, [])

    def test_inverted_envelope_raises(self):
        with self.assertRaises(ValueError):
            spin.spin_test_point_matrix(
                self.CONFIGS, self.CGS, self.WEIGHTS, self.ALTITUDES,
                cg_min_pct=35.0, cg_max_pct=15.0,
            )


class SpinPhaseClassifyTest(unittest.TestCase):
    def test_phase_boundaries(self):
        self.assertEqual(spin.spin_phase_classify(0.5, 25.0), "entry")
        self.assertEqual(spin.spin_phase_classify(1.5, 30.0), "incipient")
        self.assertEqual(spin.spin_phase_classify(2.5, 40.0), "developed")

    def test_developed_needs_stable_yaw_rate(self):
        # Two turns but a weak yaw rate is not a developed spin yet.
        self.assertEqual(spin.spin_phase_classify(2.5, 10.0), "incipient")

    def test_negative_inputs_raise(self):
        with self.assertRaises(ValueError):
            spin.spin_phase_classify(-1.0, 30.0)
        with self.assertRaises(ValueError):
            spin.spin_phase_classify(1.0, -30.0)
        with self.assertRaises(ValueError):
            spin.spin_phase_classify(float("inf"), 30.0)


class SpinRecoveryCheckTest(unittest.TestCase):
    def test_recoverable_within_limits(self):
        result = spin.spin_recovery_check(1.5, 1800.0)
        self.assertTrue(result["turns_ok"])
        self.assertTrue(result["altitude_ok"])
        self.assertTrue(result["recoverable"])
        self.assertEqual(result["verdict"], "recoverable")

    def test_unrecoverable_when_turns_exceed_limit(self):
        result = spin.spin_recovery_check(3.5, 1500.0)
        self.assertFalse(result["turns_ok"])
        self.assertFalse(result["recoverable"])
        self.assertEqual(result["verdict"], "unrecoverable")

    def test_unrecoverable_when_altitude_exceeds_limit(self):
        result = spin.spin_recovery_check(1.0, 4200.0)
        self.assertFalse(result["altitude_ok"])
        self.assertFalse(result["recoverable"])
        self.assertEqual(result["verdict"], "unrecoverable")

    def test_custom_limits(self):
        result = spin.spin_recovery_check(1.5, 1800.0, turns_limit=1.0)
        self.assertFalse(result["recoverable"])

    def test_negative_and_zero_limit_raise(self):
        with self.assertRaises(ValueError):
            spin.spin_recovery_check(-1.0, 1000.0)
        with self.assertRaises(ValueError):
            spin.spin_recovery_check(1.0, -1000.0)
        with self.assertRaises(ValueError):
            spin.spin_recovery_check(1.0, 1000.0, turns_limit=0.0)


class RecoveryParachuteRequirementTest(unittest.TestCase):
    def test_not_required_when_demonstrated_and_limited(self):
        result = spin.recovery_parachute_requirement(
            prior_recovery_demonstrated=True, developed_spin_planned=False
        )
        self.assertFalse(result["required"])
        self.assertEqual(result["reasons"], [])

    def test_required_when_no_prior_demonstration(self):
        result = spin.recovery_parachute_requirement(
            prior_recovery_demonstrated=False, developed_spin_planned=False
        )
        self.assertTrue(result["required"])
        self.assertIn("no prior recovery demonstration", result["reasons"][0])

    def test_required_when_developed_spin_planned(self):
        result = spin.recovery_parachute_requirement(
            prior_recovery_demonstrated=True, developed_spin_planned=True
        )
        self.assertTrue(result["required"])
        self.assertIn("developed spin testing planned", result["reasons"])

    def test_required_when_unrecoverable_predicted_or_first_flight(self):
        result = spin.recovery_parachute_requirement(
            prior_recovery_demonstrated=True, developed_spin_planned=False,
            unrecoverable_predicted=True, first_flight=True,
        )
        self.assertTrue(result["required"])
        self.assertEqual(len(result["reasons"]), 2)

    def test_reason_order_is_deterministic(self):
        r1 = spin.recovery_parachute_requirement(
            prior_recovery_demonstrated=False, developed_spin_planned=True
        )
        r2 = spin.recovery_parachute_requirement(
            prior_recovery_demonstrated=False, developed_spin_planned=True
        )
        self.assertEqual(r1["reasons"], r2["reasons"])


class SpinResistanceCheckTest(unittest.TestCase):
    def test_resistant_within_limits(self):
        result = spin.spin_resistance_check(0.8, 900.0)
        self.assertTrue(result["entered_spin"])
        self.assertTrue(result["resistant"])
        self.assertEqual(result["verdict"], "resistant")

    def test_no_autorotation_is_resistant(self):
        result = spin.spin_resistance_check(0.0, 0.0)
        self.assertFalse(result["entered_spin"])
        self.assertTrue(result["resistant"])

    def test_not_resistant_when_turns_exceed_limit(self):
        result = spin.spin_resistance_check(2.1, 800.0)
        self.assertFalse(result["resistant"])
        self.assertEqual(result["verdict"], "not-resistant")

    def test_not_resistant_when_altitude_exceeds_limit(self):
        result = spin.spin_resistance_check(0.5, 2600.0)
        self.assertFalse(result["resistant"])
        self.assertEqual(result["verdict"], "not-resistant")

    def test_negative_inputs_raise(self):
        with self.assertRaises(ValueError):
            spin.spin_resistance_check(-0.5, 800.0)
        with self.assertRaises(ValueError):
            spin.spin_resistance_check(0.5, -800.0)
        with self.assertRaises(ValueError):
            spin.spin_resistance_check(0.5, 800.0, max_allowed_turns=0.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
