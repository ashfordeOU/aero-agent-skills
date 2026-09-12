#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-32C clause 5.5 acceptance proof and
leak test programme.

Exercises scripts/acceptance_test_programme_logic.py (stdlib unittest,
offline). Contract: a test type is accepted when it is "proof" or "leak"
and raises for any other value; proof pressure is MDP times proof factor
and raises for non-positive inputs; a proof test passes when the applied
pressure meets the requirement and the hold duration meets the minimum,
and each shortfall is a separate violation; a leak test passes when the
measured rate is within the allowable, a missing allowable is itself a
finding, and a negative rate raises; the programme passes only when
every individual test item passes.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import acceptance_test_programme_logic as atp  # noqa: E402


class ValidateTestTypeTest(unittest.TestCase):
    def test_proof_is_valid(self):
        self.assertEqual(atp.validate_test_type("proof"), "proof")

    def test_leak_is_valid(self):
        self.assertEqual(atp.validate_test_type("leak"), "leak")

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            atp.validate_test_type("burst")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            atp.validate_test_type("")


class ComputeProofPressureTest(unittest.TestCase):
    def test_nominal_computation(self):
        self.assertAlmostEqual(atp.compute_proof_pressure(200.0, 1.0), 200.0)

    def test_non_unity_factor(self):
        self.assertAlmostEqual(atp.compute_proof_pressure(200.0, 1.25), 250.0)

    def test_zero_mdp_raises(self):
        with self.assertRaises(ValueError):
            atp.compute_proof_pressure(0.0, 1.0)

    def test_negative_mdp_raises(self):
        with self.assertRaises(ValueError):
            atp.compute_proof_pressure(-50.0, 1.0)

    def test_zero_factor_raises(self):
        with self.assertRaises(ValueError):
            atp.compute_proof_pressure(200.0, 0.0)

    def test_negative_factor_raises(self):
        with self.assertRaises(ValueError):
            atp.compute_proof_pressure(200.0, -1.0)


class CheckProofTestTest(unittest.TestCase):
    def test_passes_when_all_conditions_met(self):
        violations = atp.check_proof_test(
            "tank-1",
            applied_pressure_kpa=210.0,
            required_proof_pressure_kpa=200.0,
            hold_duration_s=360.0,
        )
        self.assertEqual(violations, [])

    def test_passes_at_exact_required_pressure(self):
        violations = atp.check_proof_test(
            "tank-2",
            applied_pressure_kpa=200.0,
            required_proof_pressure_kpa=200.0,
            hold_duration_s=300.0,
        )
        self.assertEqual(violations, [])

    def test_fails_when_pressure_not_reached(self):
        violations = atp.check_proof_test(
            "tank-3",
            applied_pressure_kpa=180.0,
            required_proof_pressure_kpa=200.0,
            hold_duration_s=300.0,
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "proof_pressure_not_reached")
        self.assertEqual(violations[0]["test_id"], "tank-3")

    def test_fails_when_hold_duration_short(self):
        violations = atp.check_proof_test(
            "tank-4",
            applied_pressure_kpa=200.0,
            required_proof_pressure_kpa=200.0,
            hold_duration_s=120.0,
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "hold_duration_insufficient")

    def test_two_violations_when_both_conditions_fail(self):
        violations = atp.check_proof_test(
            "tank-5",
            applied_pressure_kpa=150.0,
            required_proof_pressure_kpa=200.0,
            hold_duration_s=60.0,
        )
        issues = {v["issue"] for v in violations}
        self.assertIn("proof_pressure_not_reached", issues)
        self.assertIn("hold_duration_insufficient", issues)

    def test_custom_min_hold_duration_applied(self):
        violations = atp.check_proof_test(
            "tank-6",
            applied_pressure_kpa=200.0,
            required_proof_pressure_kpa=200.0,
            hold_duration_s=300.0,
            min_hold_duration_s=600,
        )
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "hold_duration_insufficient")
        self.assertEqual(violations[0]["required_s"], 600)


class CheckLeakTestTest(unittest.TestCase):
    def test_passes_when_measured_below_allowable(self):
        self.assertEqual(atp.check_leak_test("valve-1", 0.005, 0.01), [])

    def test_passes_when_measured_equals_allowable(self):
        self.assertEqual(atp.check_leak_test("valve-2", 0.01, 0.01), [])

    def test_fails_when_rate_exceeded(self):
        violations = atp.check_leak_test("valve-3", 0.02, 0.01)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "leak_rate_exceeded")
        self.assertEqual(violations[0]["test_id"], "valve-3")
        self.assertAlmostEqual(violations[0]["measured"], 0.02)
        self.assertAlmostEqual(violations[0]["allowable"], 0.01)

    def test_missing_allowable_is_finding(self):
        violations = atp.check_leak_test("valve-4", 0.005, None)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_allowable_leak_rate")

    def test_negative_measured_rate_raises(self):
        with self.assertRaises(ValueError):
            atp.check_leak_test("valve-5", -0.001, 0.01)

    def test_zero_allowable_raises(self):
        with self.assertRaises(ValueError):
            atp.check_leak_test("valve-6", 0.0, 0.0)


class AcceptanceTestResultTest(unittest.TestCase):
    def test_proof_item_passes(self):
        item = {
            "test_id": "tank-A",
            "test_type": "proof",
            "applied_pressure_kpa": 205.0,
            "required_proof_pressure_kpa": 200.0,
            "hold_duration_s": 310.0,
        }
        result = atp.acceptance_test_result(item)
        self.assertTrue(result["passed"])
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["test_type"], "proof")

    def test_leak_item_passes(self):
        item = {
            "test_id": "seal-A",
            "test_type": "leak",
            "measured_leak_rate": 0.003,
            "allowable_leak_rate": 0.01,
        }
        result = atp.acceptance_test_result(item)
        self.assertTrue(result["passed"])

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            atp.acceptance_test_result(
                {
                    "test_id": "x",
                    "test_type": "vibration",
                    "applied_pressure_kpa": 100.0,
                    "required_proof_pressure_kpa": 100.0,
                    "hold_duration_s": 300.0,
                }
            )


class AcceptanceProgrammeResultTest(unittest.TestCase):
    def _proof_pass(self, tid):
        return {
            "test_id": tid,
            "test_type": "proof",
            "applied_pressure_kpa": 200.0,
            "required_proof_pressure_kpa": 200.0,
            "hold_duration_s": 300.0,
        }

    def _leak_pass(self, tid):
        return {
            "test_id": tid,
            "test_type": "leak",
            "measured_leak_rate": 0.005,
            "allowable_leak_rate": 0.01,
        }

    def _leak_fail(self, tid):
        return {
            "test_id": tid,
            "test_type": "leak",
            "measured_leak_rate": 0.02,
            "allowable_leak_rate": 0.01,
        }

    def test_all_pass_programme_passes(self):
        result = atp.acceptance_programme_result(
            [self._proof_pass("t1"), self._leak_pass("t2")]
        )
        self.assertTrue(result["programme_passed"])
        self.assertEqual(len(result["results"]), 2)

    def test_one_failure_fails_programme(self):
        result = atp.acceptance_programme_result(
            [self._proof_pass("t1"), self._leak_fail("t2")]
        )
        self.assertFalse(result["programme_passed"])

    def test_empty_programme_passes(self):
        result = atp.acceptance_programme_result([])
        self.assertTrue(result["programme_passed"])
        self.assertEqual(result["results"], [])

    def test_results_list_length_matches_items(self):
        items = [self._proof_pass("t%d" % i) for i in range(4)]
        result = atp.acceptance_programme_result(items)
        self.assertEqual(len(result["results"]), 4)

    def test_individual_results_carry_test_ids(self):
        items = [self._proof_pass("alpha"), self._leak_pass("beta")]
        result = atp.acceptance_programme_result(items)
        ids = [r["test_id"] for r in result["results"]]
        self.assertEqual(ids, ["alpha", "beta"])


if __name__ == "__main__":
    unittest.main()
