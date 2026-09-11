"""
Gate-3 contract test for e1003-el-pressure.
Stdlib unittest only -- offline, deterministic.
Run: python3 test_e1003_el_pressure.py
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1003_el_pressure_logic import (
    compute_proof_pressure,
    compute_burst_pressure,
    check_proof_test,
    check_pressure_cycling,
    check_burst_test,
    check_leak_test,
    run_pressure_test_sequence,
    PressureTestError,
    DEFAULT_PROOF_FACTOR,
    DEFAULT_BURST_FACTOR,
    DEFAULT_LEAK_RATE_LIMIT_PA_M3_S,
)


class TestComputeProofPressure(unittest.TestCase):

    def test_nominal_default_factor(self):
        self.assertAlmostEqual(compute_proof_pressure(100_000), 150_000)

    def test_custom_factor(self):
        self.assertAlmostEqual(compute_proof_pressure(200_000, 1.25), 250_000)

    def test_factor_exactly_one(self):
        self.assertAlmostEqual(compute_proof_pressure(80_000, 1.0), 80_000)

    def test_zero_meop_raises(self):
        with self.assertRaises(PressureTestError):
            compute_proof_pressure(0)

    def test_negative_meop_raises(self):
        with self.assertRaises(PressureTestError):
            compute_proof_pressure(-1_000)

    def test_proof_factor_below_one_raises(self):
        with self.assertRaises(PressureTestError):
            compute_proof_pressure(100_000, 0.9)


class TestComputeBurstPressure(unittest.TestCase):

    def test_nominal_default_factor(self):
        self.assertAlmostEqual(compute_burst_pressure(100_000), 200_000)

    def test_custom_factor(self):
        self.assertAlmostEqual(compute_burst_pressure(100_000, 2.5), 250_000)

    def test_zero_meop_raises(self):
        with self.assertRaises(PressureTestError):
            compute_burst_pressure(0)

    def test_burst_factor_below_one_raises(self):
        with self.assertRaises(PressureTestError):
            compute_burst_pressure(100_000, 0.5)


class TestCheckProofTest(unittest.TestCase):

    def _passing_kwargs(self):
        return dict(
            applied_pressure_pa=150_000,
            meop_pa=100_000,
            hold_duration_s=300,
            required_hold_s=300,
            deformation_detected=False,
            leak_detected=False,
        )

    def test_nominal_pass(self):
        r = check_proof_test(**self._passing_kwargs())
        self.assertTrue(r["passed"])
        self.assertEqual(r["findings"], [])

    def test_applied_pressure_too_low(self):
        kw = self._passing_kwargs()
        kw["applied_pressure_pa"] = 140_000  # below 150_000 required
        r = check_proof_test(**kw)
        self.assertFalse(r["passed"])
        self.assertTrue(any("proof pressure" in f for f in r["findings"]))

    def test_hold_duration_too_short(self):
        kw = self._passing_kwargs()
        kw["hold_duration_s"] = 100
        r = check_proof_test(**kw)
        self.assertFalse(r["passed"])
        self.assertTrue(any("Hold duration" in f for f in r["findings"]))

    def test_deformation_detected(self):
        kw = self._passing_kwargs()
        kw["deformation_detected"] = True
        r = check_proof_test(**kw)
        self.assertFalse(r["passed"])
        self.assertTrue(any("deformation" in f for f in r["findings"]))

    def test_leak_detected(self):
        kw = self._passing_kwargs()
        kw["leak_detected"] = True
        r = check_proof_test(**kw)
        self.assertFalse(r["passed"])
        self.assertTrue(any("Leakage" in f for f in r["findings"]))

    def test_multiple_failures_all_recorded(self):
        kw = self._passing_kwargs()
        kw["applied_pressure_pa"] = 100_000
        kw["hold_duration_s"] = 10
        kw["leak_detected"] = True
        r = check_proof_test(**kw)
        self.assertFalse(r["passed"])
        self.assertGreaterEqual(len(r["findings"]), 3)

    def test_proof_pressure_above_required_passes(self):
        kw = self._passing_kwargs()
        kw["applied_pressure_pa"] = 160_000  # above minimum
        r = check_proof_test(**kw)
        self.assertTrue(r["passed"])


class TestCheckPressureCycling(unittest.TestCase):

    def _passing_kwargs(self):
        return dict(
            cycles_completed=100,
            cycles_required=100,
            min_pressure_pa=0,
            max_pressure_pa=100_000,
            meop_pa=100_000,
            leak_detected=False,
            deformation_detected=False,
        )

    def test_nominal_pass(self):
        r = check_pressure_cycling(**self._passing_kwargs())
        self.assertTrue(r["passed"])
        self.assertEqual(r["findings"], [])

    def test_insufficient_cycles(self):
        kw = self._passing_kwargs()
        kw["cycles_completed"] = 50
        r = check_pressure_cycling(**kw)
        self.assertFalse(r["passed"])
        self.assertTrue(any("cycle count" in f for f in r["findings"]))

    def test_inverted_pressure_range(self):
        kw = self._passing_kwargs()
        kw["min_pressure_pa"] = 60_000
        kw["max_pressure_pa"] = 10_000  # max below min — truly inverted
        r = check_pressure_cycling(**kw)
        self.assertFalse(r["passed"])

    def test_negative_min_pressure(self):
        kw = self._passing_kwargs()
        kw["min_pressure_pa"] = -1_000
        r = check_pressure_cycling(**kw)
        self.assertFalse(r["passed"])
        self.assertTrue(any(">= 0" in f for f in r["findings"]))

    def test_leak_during_cycling_fails(self):
        kw = self._passing_kwargs()
        kw["leak_detected"] = True
        r = check_pressure_cycling(**kw)
        self.assertFalse(r["passed"])

    def test_deformation_after_cycling_fails(self):
        kw = self._passing_kwargs()
        kw["deformation_detected"] = True
        r = check_pressure_cycling(**kw)
        self.assertFalse(r["passed"])

    def test_excess_cycles_passes(self):
        kw = self._passing_kwargs()
        kw["cycles_completed"] = 200  # more than required
        r = check_pressure_cycling(**kw)
        self.assertTrue(r["passed"])


class TestCheckBurstTest(unittest.TestCase):

    def test_nominal_pass(self):
        r = check_burst_test(applied_pressure_pa=200_000, meop_pa=100_000)
        self.assertTrue(r["passed"])

    def test_applied_below_design_burst(self):
        r = check_burst_test(applied_pressure_pa=180_000, meop_pa=100_000)
        self.assertFalse(r["passed"])
        self.assertTrue(any("inconclusive" in f for f in r["findings"]))

    def test_burst_occurred_fails(self):
        r = check_burst_test(
            applied_pressure_pa=200_000, meop_pa=100_000, burst_occurred=True
        )
        self.assertFalse(r["passed"])
        self.assertTrue(any("ruptured" in f for f in r["findings"]))

    def test_above_design_burst_no_rupture_passes(self):
        r = check_burst_test(
            applied_pressure_pa=220_000, meop_pa=100_000, burst_occurred=False
        )
        self.assertTrue(r["passed"])

    def test_custom_burst_factor(self):
        r = check_burst_test(
            applied_pressure_pa=250_000, meop_pa=100_000, burst_factor=2.5
        )
        self.assertTrue(r["passed"])

    def test_custom_burst_factor_too_low_fails(self):
        r = check_burst_test(
            applied_pressure_pa=200_000, meop_pa=100_000, burst_factor=2.5
        )
        self.assertFalse(r["passed"])


class TestCheckLeakTest(unittest.TestCase):

    def test_nominal_pass(self):
        r = check_leak_test(1e-8, 1e-6)
        self.assertTrue(r["passed"])
        self.assertGreater(r["margin"], 0)

    def test_exceeds_allowable_fails(self):
        r = check_leak_test(1e-4, 1e-6)
        self.assertFalse(r["passed"])
        self.assertLess(r["margin"], 0)

    def test_at_limit_passes(self):
        r = check_leak_test(1e-6, 1e-6)
        self.assertTrue(r["passed"])
        self.assertAlmostEqual(r["margin"], 0.0)

    def test_zero_allowable_raises(self):
        with self.assertRaises(PressureTestError):
            check_leak_test(1e-8, 0)

    def test_negative_allowable_raises(self):
        with self.assertRaises(PressureTestError):
            check_leak_test(1e-8, -1e-6)

    def test_default_allowable_used(self):
        r = check_leak_test(DEFAULT_LEAK_RATE_LIMIT_PA_M3_S / 2)
        self.assertTrue(r["passed"])


class TestRunPressureTestSequence(unittest.TestCase):

    def _full_pass_inputs(self):
        return dict(
            meop_pa=100_000,
            test_results={
                "proof": {
                    "applied_pa": 150_000,
                    "hold_s": 300,
                    "required_hold_s": 300,
                    "deformation": False,
                    "leak": False,
                },
                "cycling": {
                    "cycles_done": 50,
                    "cycles_req": 50,
                    "min_pa": 0,
                    "max_pa": 100_000,
                    "leak": False,
                    "deformation": False,
                },
                "burst": {"applied_pa": 200_000, "burst_occurred": False},
                "leak": {"measured_pa_m3_s": 5e-8, "allowable_pa_m3_s": 1e-6},
            },
        )

    def test_full_sequence_pass(self):
        result = run_pressure_test_sequence(**self._full_pass_inputs())
        self.assertTrue(result["overall_passed"])
        self.assertSetEqual(set(result["tests"].keys()), {"proof", "cycling", "burst", "leak"})

    def test_single_failing_test_fails_overall(self):
        inp = self._full_pass_inputs()
        inp["test_results"]["burst"]["applied_pa"] = 150_000  # below design burst
        result = run_pressure_test_sequence(**inp)
        self.assertFalse(result["overall_passed"])
        self.assertFalse(result["tests"]["burst"]["passed"])

    def test_partial_sequence_leak_only_passes(self):
        result = run_pressure_test_sequence(
            meop_pa=100_000,
            test_results={"leak": {"measured_pa_m3_s": 5e-8, "allowable_pa_m3_s": 1e-6}},
        )
        self.assertTrue(result["overall_passed"])
        self.assertIn("leak", result["tests"])
        self.assertNotIn("proof", result["tests"])

    def test_empty_test_results_passes(self):
        result = run_pressure_test_sequence(meop_pa=100_000, test_results={})
        self.assertTrue(result["overall_passed"])
        self.assertEqual(result["tests"], {})

    def test_cycling_failure_reported(self):
        inp = self._full_pass_inputs()
        inp["test_results"]["cycling"]["cycles_done"] = 10  # below 50 required
        result = run_pressure_test_sequence(**inp)
        self.assertFalse(result["overall_passed"])
        self.assertFalse(result["tests"]["cycling"]["passed"])


if __name__ == "__main__":
    unittest.main()
