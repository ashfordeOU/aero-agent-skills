"""
test_copv_metallic_liner.py — stdlib unittest for copv_metallic_liner_logic.py.

Run: python3 test_copv_metallic_liner.py
Must print OK.  No third-party dependencies.  Deterministic, offline.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from copv_metallic_liner_logic import (
    BURST_FACTOR_MIN,
    FATIGUE_SCATTER,
    PROOF_FACTOR_MIN,
    check_burst_factor,
    check_fatigue_adequacy,
    check_liner_yield_at_proof,
    check_proof_factor,
    compute_burst_pressure,
    compute_fatigue_life_cycles,
    compute_fiber_hoop_stress,
    compute_hoop_stress,
    compute_margin_of_safety,
    compute_proof_pressure,
    validate_copv_metallic_liner,
)


class TestComputeHoopStress(unittest.TestCase):

    def test_basic_value(self):
        # sigma = 10e6 * 0.2 / 0.004 = 500 MPa
        result = compute_hoop_stress(10e6, 0.2, 0.004)
        self.assertAlmostEqual(result, 500e6, delta=1.0)

    def test_proportional_to_pressure(self):
        s1 = compute_hoop_stress(5e6, 0.1, 0.002)
        s2 = compute_hoop_stress(10e6, 0.1, 0.002)
        self.assertAlmostEqual(s2, 2.0 * s1, delta=1.0)

    def test_proportional_to_radius(self):
        s1 = compute_hoop_stress(10e6, 0.1, 0.002)
        s2 = compute_hoop_stress(10e6, 0.2, 0.002)
        self.assertAlmostEqual(s2, 2.0 * s1, delta=1.0)

    def test_inversely_proportional_to_thickness(self):
        s1 = compute_hoop_stress(10e6, 0.2, 0.004)
        s2 = compute_hoop_stress(10e6, 0.2, 0.002)
        self.assertAlmostEqual(s2, 2.0 * s1, delta=1.0)

    def test_zero_pressure_raises(self):
        with self.assertRaises(ValueError):
            compute_hoop_stress(0.0, 0.1, 0.002)

    def test_negative_pressure_raises(self):
        with self.assertRaises(ValueError):
            compute_hoop_stress(-1e6, 0.1, 0.002)

    def test_zero_radius_raises(self):
        with self.assertRaises(ValueError):
            compute_hoop_stress(5e6, 0.0, 0.002)

    def test_zero_thickness_raises(self):
        with self.assertRaises(ValueError):
            compute_hoop_stress(5e6, 0.1, 0.0)


class TestMarginOfSafety(unittest.TestCase):

    def test_positive_margin(self):
        # MOS = 100/80 - 1 = 0.25
        self.assertAlmostEqual(compute_margin_of_safety(100.0, 80.0), 0.25)

    def test_zero_margin(self):
        self.assertAlmostEqual(compute_margin_of_safety(100.0, 100.0), 0.0)

    def test_negative_margin(self):
        # MOS = 80/100 - 1 = -0.20
        self.assertAlmostEqual(compute_margin_of_safety(80.0, 100.0), -0.20)

    def test_zero_actual_raises(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(100.0, 0.0)

    def test_zero_allowable_raises(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(0.0, 100.0)


class TestProofBurstPressure(unittest.TestCase):

    def test_proof_pressure_at_minimum_factor(self):
        self.assertAlmostEqual(compute_proof_pressure(10e6, 1.25), 12.5e6)

    def test_proof_pressure_above_minimum(self):
        self.assertAlmostEqual(compute_proof_pressure(10e6, 1.5), 15.0e6)

    def test_proof_pressure_below_minimum_raises(self):
        with self.assertRaises(ValueError):
            compute_proof_pressure(10e6, 1.0)

    def test_burst_pressure_at_minimum_factor(self):
        self.assertAlmostEqual(compute_burst_pressure(10e6, 2.0), 20.0e6)

    def test_burst_pressure_above_minimum(self):
        self.assertAlmostEqual(compute_burst_pressure(10e6, 2.5), 25.0e6)

    def test_burst_pressure_below_minimum_raises(self):
        with self.assertRaises(ValueError):
            compute_burst_pressure(10e6, 1.5)

    def test_check_proof_factor_valid(self):
        self.assertTrue(check_proof_factor(1.5))

    def test_check_proof_factor_at_boundary(self):
        self.assertTrue(check_proof_factor(PROOF_FACTOR_MIN))

    def test_check_proof_factor_invalid(self):
        self.assertFalse(check_proof_factor(1.0))

    def test_check_burst_factor_valid(self):
        self.assertTrue(check_burst_factor(2.5))

    def test_check_burst_factor_at_boundary(self):
        self.assertTrue(check_burst_factor(BURST_FACTOR_MIN))

    def test_check_burst_factor_invalid(self):
        self.assertFalse(check_burst_factor(1.9))


class TestFiberHoopStress(unittest.TestCase):

    def test_basic_value(self):
        # sigma_f = 10e6 * 0.2 / (0.01 * 0.6) = 333.33 MPa
        expected = 10e6 * 0.2 / (0.01 * 0.6)
        result = compute_fiber_hoop_stress(10e6, 0.2, 0.01, 0.6)
        self.assertAlmostEqual(result, expected, delta=1.0)

    def test_lower_vf_increases_stress(self):
        s_high_vf = compute_fiber_hoop_stress(10e6, 0.2, 0.01, 0.6)
        s_low_vf = compute_fiber_hoop_stress(10e6, 0.2, 0.01, 0.3)
        self.assertGreater(s_low_vf, s_high_vf)

    def test_vf_unity_matches_hoop_stress(self):
        # When Vf=1 the result equals the plain thin-wall hoop stress
        self.assertAlmostEqual(
            compute_fiber_hoop_stress(10e6, 0.2, 0.004, 1.0),
            compute_hoop_stress(10e6, 0.2, 0.004),
            delta=1.0,
        )

    def test_zero_vf_raises(self):
        with self.assertRaises(ValueError):
            compute_fiber_hoop_stress(10e6, 0.2, 0.01, 0.0)

    def test_vf_above_one_raises(self):
        with self.assertRaises(ValueError):
            compute_fiber_hoop_stress(10e6, 0.2, 0.01, 1.1)

    def test_zero_pressure_raises(self):
        with self.assertRaises(ValueError):
            compute_fiber_hoop_stress(0.0, 0.2, 0.01, 0.6)


class TestFatigueLife(unittest.TestCase):

    def test_stress_at_reference_gives_one_cycle(self):
        # At sigma_a = sigma_f, Nf = (sigma_f / sigma_f)^m = 1
        result = compute_fatigue_life_cycles(500e6, 500e6, 5.0)
        self.assertAlmostEqual(result, 1.0)

    def test_lower_stress_gives_longer_life(self):
        nf_high = compute_fatigue_life_cycles(400e6, 800e6, 4.0)
        nf_low = compute_fatigue_life_cycles(200e6, 800e6, 4.0)
        self.assertGreater(nf_low, nf_high)

    def test_power_law_correctness(self):
        # Nf = (1000/200)^4 = 5^4 = 625
        result = compute_fatigue_life_cycles(200e6, 1000e6, 4.0)
        self.assertAlmostEqual(result, 625.0, places=6)

    def test_zero_stress_amplitude_raises(self):
        with self.assertRaises(ValueError):
            compute_fatigue_life_cycles(0.0, 800e6, 4.0)

    def test_zero_slope_exponent_raises(self):
        with self.assertRaises(ValueError):
            compute_fatigue_life_cycles(200e6, 800e6, 0.0)


class TestFatigueAdequacy(unittest.TestCase):

    def test_adequate_life_passes(self):
        # Nf=1000, design=100, scatter=4 → required=400, margin=1.5 → compliant
        result = check_fatigue_adequacy(1000.0, 100, 4.0)
        self.assertTrue(result["compliant"])
        self.assertAlmostEqual(result["margin"], 1.5)

    def test_inadequate_life_fails(self):
        # Nf=300, design=100, scatter=4 → required=400, margin=-0.25
        result = check_fatigue_adequacy(300.0, 100, 4.0)
        self.assertFalse(result["compliant"])
        self.assertAlmostEqual(result["margin"], -0.25)

    def test_required_life_computed_correctly(self):
        result = check_fatigue_adequacy(500.0, 50, 4.0)
        self.assertAlmostEqual(result["required_life"], 200.0)

    def test_default_scatter_factor_applied(self):
        result = check_fatigue_adequacy(800.0, 100)
        self.assertAlmostEqual(result["required_life"], 100.0 * FATIGUE_SCATTER)

    def test_zero_design_cycles_raises(self):
        with self.assertRaises(ValueError):
            check_fatigue_adequacy(1000.0, 0, 4.0)


class TestLinerYieldAtProof(unittest.TestCase):

    def test_no_yield_compliant(self):
        result = check_liner_yield_at_proof(200e6, 276e6)
        self.assertTrue(result["compliant"])
        self.assertFalse(result["yielded"])

    def test_yielded_not_compliant(self):
        result = check_liner_yield_at_proof(300e6, 276e6)
        self.assertFalse(result["compliant"])
        self.assertTrue(result["yielded"])

    def test_mos_value(self):
        result = check_liner_yield_at_proof(200e6, 276e6)
        self.assertAlmostEqual(result["mos"], (276e6 / 200e6) - 1.0, places=8)

    def test_stress_equals_yield_is_yielded(self):
        result = check_liner_yield_at_proof(276e6, 276e6)
        self.assertTrue(result["yielded"])
        self.assertFalse(result["compliant"])

    def test_zero_stress_raises(self):
        with self.assertRaises(ValueError):
            check_liner_yield_at_proof(0.0, 276e6)


class TestValidateCopvMetallicLiner(unittest.TestCase):

    def _compliant_params(self):
        # All checks pass with these values (verified by hand):
        # - liner MEOP stress = 10e6*0.2/0.003 = 666.7 MPa < 880 MPa ✓
        # - liner proof stress = 12.5e6*0.2/0.003 = 833.3 MPa < 880 MPa ✓
        # - fiber burst stress = 20e6*0.2/(0.008*0.6) = 833.3 MPa < 3500 MPa ✓
        # - Nf = (800e6/100e6)^3.5 = 8^3.5 ≈ 1449 > 100*4=400 ✓
        return {
            "meop_pa": 10e6,
            "proof_factor": 1.25,
            "burst_factor": 2.0,
            "inner_radius_m": 0.2,
            "liner_thickness_m": 0.003,
            "liner_yield_pa": 880e6,
            "overwrap_thickness_m": 0.008,
            "fiber_volume_fraction": 0.6,
            "fiber_tensile_strength_pa": 3500e6,
            "liner_stress_amplitude_pa": 100e6,
            "fatigue_strength_ref_pa": 800e6,
            "fatigue_slope_exponent": 3.5,
            "design_cycles": 100,
            "fatigue_scatter_factor": 4.0,
        }

    def test_compliant_design_passes(self):
        result = validate_copv_metallic_liner(self._compliant_params())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_result_contains_required_keys(self):
        result = validate_copv_metallic_liner(self._compliant_params())
        for key in [
            "liner_meop_mos", "liner_proof_check", "fiber_burst_mos",
            "fatigue_check", "proof_factor_ok", "burst_factor_ok",
            "compliant", "findings",
        ]:
            self.assertIn(key, result)

    def test_low_burst_factor_not_compliant(self):
        params = self._compliant_params()
        params["burst_factor"] = 1.5
        result = validate_copv_metallic_liner(params)
        self.assertFalse(result["compliant"])
        self.assertFalse(result["burst_factor_ok"])

    def test_low_proof_factor_not_compliant(self):
        params = self._compliant_params()
        params["proof_factor"] = 1.0
        result = validate_copv_metallic_liner(params)
        self.assertFalse(result["compliant"])
        self.assertFalse(result["proof_factor_ok"])

    def test_liner_overstressed_at_meop_flagged(self):
        params = self._compliant_params()
        params["liner_yield_pa"] = 100e6  # far below MEOP stress of 666.7 MPa
        result = validate_copv_metallic_liner(params)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("MEOP" in f for f in result["findings"]))

    def test_insufficient_fatigue_life_flagged(self):
        params = self._compliant_params()
        params["liner_stress_amplitude_pa"] = 700e6  # Nf ≈ 1.6 << 400 required
        result = validate_copv_metallic_liner(params)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("Fatigue" in f for f in result["findings"]))

    def test_missing_parameter_raises(self):
        params = self._compliant_params()
        del params["meop_pa"]
        with self.assertRaises(ValueError):
            validate_copv_metallic_liner(params)

    def test_missing_fatigue_param_raises(self):
        params = self._compliant_params()
        del params["design_cycles"]
        with self.assertRaises(ValueError):
            validate_copv_metallic_liner(params)

    def test_optional_scatter_factor_defaults(self):
        params = self._compliant_params()
        del params["fatigue_scatter_factor"]
        result = validate_copv_metallic_liner(params)
        # Should still compute using FATIGUE_SCATTER default
        self.assertIn("fatigue_check", result)

    def test_liner_mos_positive_for_compliant_design(self):
        result = validate_copv_metallic_liner(self._compliant_params())
        self.assertGreater(result["liner_meop_mos"], 0.0)

    def test_fiber_burst_mos_positive_for_compliant_design(self):
        result = validate_copv_metallic_liner(self._compliant_params())
        self.assertGreater(result["fiber_burst_mos"], 0.0)


if __name__ == "__main__":
    unittest.main()
