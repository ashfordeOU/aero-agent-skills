import unittest
import math
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lbb_by_analysis_logic import (
    compute_hoop_stress,
    compute_stress_intensity,
    compute_critical_crack_length,
    compute_margin_of_safety,
    integrate_paris_growth,
    check_lbb_size_criterion,
    check_life_criterion,
    check_residual_strength,
    assess_lbb,
    LbbInputs,
)


class TestHoopStress(unittest.TestCase):
    def test_basic_thin_wall(self):
        # P=1e6 Pa, R=0.5 m, t=0.01 m -> sigma = 50e6 Pa
        self.assertAlmostEqual(compute_hoop_stress(1e6, 0.5, 0.01), 50e6, places=0)

    def test_zero_pressure_gives_zero_stress(self):
        self.assertEqual(compute_hoop_stress(0.0, 0.5, 0.01), 0.0)

    def test_negative_thickness_raises(self):
        with self.assertRaises(ValueError):
            compute_hoop_stress(1e6, 0.5, -0.01)

    def test_negative_pressure_raises(self):
        with self.assertRaises(ValueError):
            compute_hoop_stress(-1e6, 0.5, 0.01)


class TestStressIntensity(unittest.TestCase):
    def test_known_value(self):
        expected = 100e6 * math.sqrt(math.pi * 0.01)
        self.assertAlmostEqual(
            compute_stress_intensity(100e6, 0.01, 1.0), expected, places=0
        )

    def test_geometry_factor_scales_linearly(self):
        k1 = compute_stress_intensity(100e6, 0.01, 1.0)
        k2 = compute_stress_intensity(100e6, 0.01, 2.0)
        self.assertAlmostEqual(k2, 2.0 * k1, places=5)

    def test_negative_half_crack_length_raises(self):
        with self.assertRaises(ValueError):
            compute_stress_intensity(100e6, -0.01, 1.0)

    def test_zero_stress_gives_zero(self):
        self.assertEqual(compute_stress_intensity(0.0, 0.01, 1.0), 0.0)


class TestCriticalCrackLength(unittest.TestCase):
    def test_inverse_of_stress_intensity(self):
        K_Ic = 50e6
        sigma = 100e6
        Y = 1.0
        a_c = compute_critical_crack_length(K_Ic, sigma, Y)
        self.assertAlmostEqual(
            compute_stress_intensity(sigma, a_c, Y), K_Ic, places=1
        )

    def test_higher_stress_gives_shorter_critical_crack(self):
        K_Ic = 50e6
        a_c_low = compute_critical_crack_length(K_Ic, 50e6, 1.0)
        a_c_high = compute_critical_crack_length(K_Ic, 100e6, 1.0)
        self.assertGreater(a_c_low, a_c_high)

    def test_zero_stress_raises(self):
        with self.assertRaises(ValueError):
            compute_critical_crack_length(50e6, 0.0, 1.0)


class TestMarginOfSafety(unittest.TestCase):
    def test_no_margin_when_equal(self):
        self.assertAlmostEqual(compute_margin_of_safety(10.0, 10.0), 0.0, places=10)

    def test_positive_margin(self):
        self.assertAlmostEqual(compute_margin_of_safety(10.0, 5.0), 1.0, places=10)

    def test_negative_margin(self):
        self.assertAlmostEqual(compute_margin_of_safety(5.0, 10.0), -0.5, places=10)

    def test_zero_actual_raises(self):
        with self.assertRaises(ValueError):
            compute_margin_of_safety(10.0, 0.0)


class TestParisGrowthIntegration(unittest.TestCase):
    def test_more_cycles_for_smaller_initial_crack(self):
        cycles_small, _ = integrate_paris_growth(
            0.001, 0.01, 4e-29, 3.0, 50e6, 1.0
        )
        cycles_large, _ = integrate_paris_growth(
            0.005, 0.01, 4e-29, 3.0, 50e6, 1.0
        )
        self.assertGreater(cycles_small, cycles_large)

    def test_initial_depth_equal_thickness_raises(self):
        with self.assertRaises(ValueError):
            integrate_paris_growth(0.01, 0.01, 4e-29, 3.0, 50e6, 1.0)

    def test_returns_positive_cycles(self):
        cycles, _ = integrate_paris_growth(0.001, 0.01, 4e-29, 3.0, 50e6, 1.0)
        self.assertGreater(cycles, 0)

    def test_final_depth_reaches_wall_thickness(self):
        _, final_depth = integrate_paris_growth(
            0.001, 0.01, 4e-29, 3.0, 50e6, 1.0, n_steps=100
        )
        self.assertAlmostEqual(final_depth, 0.01, places=8)


class TestLbbCriteria(unittest.TestCase):
    def test_size_criterion_passes_when_a_tw_lt_a_c(self):
        self.assertTrue(check_lbb_size_criterion(0.005, 0.010))

    def test_size_criterion_fails_when_a_tw_equals_a_c(self):
        self.assertFalse(check_lbb_size_criterion(0.010, 0.010))

    def test_size_criterion_fails_when_a_tw_exceeds_a_c(self):
        self.assertFalse(check_lbb_size_criterion(0.011, 0.010))

    def test_life_criterion_passes_when_cycles_sufficient(self):
        # 4000 cycles >= 1000 * 2.0 = 2000
        self.assertTrue(check_life_criterion(4000, 1000, 2.0))

    def test_life_criterion_fails_when_cycles_insufficient(self):
        # 1500 cycles < 1000 * 2.0 = 2000
        self.assertFalse(check_life_criterion(1500, 1000, 2.0))

    def test_residual_strength_passes_when_below_both_limits(self):
        self.assertTrue(check_residual_strength(30e6, 50e6, 200e6, 500e6))

    def test_residual_strength_fails_on_fracture(self):
        self.assertFalse(check_residual_strength(60e6, 50e6, 200e6, 500e6))

    def test_residual_strength_fails_on_net_section_collapse(self):
        self.assertFalse(check_residual_strength(30e6, 50e6, 600e6, 500e6))


class TestFullAssessment(unittest.TestCase):
    def _passing_inputs(self):
        return LbbInputs(
            wall_thickness=0.004,        # 4 mm
            vessel_radius=0.10,          # 100 mm radius
            burst_pressure=5e6,          # 5 MPa burst
            proof_pressure=3e6,          # 3 MPa proof
            fracture_toughness=80e6,     # 80 MPa*sqrt(m) K_Ic
            yield_strength=400e6,        # 400 MPa yield
            geometry_factor=1.12,
            initial_crack_depth=0.0005,  # 0.5 mm initial depth
            initial_half_length=0.0005,  # 0.5 mm half-length (circular, aspect ratio = 1)
            paris_C=4e-29,               # SI units [m/cycle / (Pa*sqrt(m))^m]
            paris_m=3.0,
            delta_stress=50e6,           # 50 MPa cyclic stress range
            required_life_cycles=1000,
            life_safety_factor=2.0,
        )

    def test_passing_assessment_returns_demonstrated(self):
        result = assess_lbb(self._passing_inputs())
        self.assertTrue(result.lbb_demonstrated)
        self.assertEqual(len(result.findings), 0)

    def test_result_has_positive_burst_stress(self):
        result = assess_lbb(self._passing_inputs())
        self.assertGreater(result.burst_stress, 0)

    def test_burst_stress_greater_than_proof_stress(self):
        result = assess_lbb(self._passing_inputs())
        self.assertGreater(result.burst_stress, result.proof_stress)

    def test_critical_crack_length_is_positive(self):
        result = assess_lbb(self._passing_inputs())
        self.assertGreater(result.critical_crack_length, 0)

    def test_failing_assessment_with_very_low_toughness(self):
        # K_Ic=1e6 makes a_c tiny -> size criterion and residual strength both fail
        bad = self._passing_inputs()._replace(fracture_toughness=1e6)
        result = assess_lbb(bad)
        self.assertFalse(result.lbb_demonstrated)
        self.assertGreater(len(result.findings), 0)

    def test_invalid_initial_depth_raises(self):
        # initial_crack_depth >= wall_thickness should raise
        bad = self._passing_inputs()._replace(initial_crack_depth=0.020)
        with self.assertRaises(ValueError):
            assess_lbb(bad)

    def test_proof_exceeds_burst_raises(self):
        bad = self._passing_inputs()._replace(proof_pressure=6e6)
        with self.assertRaises(ValueError):
            assess_lbb(bad)

    def test_deterministic_repeated_calls_agree(self):
        inp = self._passing_inputs()
        r1 = assess_lbb(inp)
        r2 = assess_lbb(inp)
        self.assertEqual(r1.lbb_demonstrated, r2.lbb_demonstrated)
        self.assertAlmostEqual(r1.critical_crack_length, r2.critical_crack_length)
        self.assertAlmostEqual(r1.growth_cycles_to_through_wall, r2.growth_cycles_to_through_wall)

    def test_life_safety_factor_below_one_raises(self):
        bad = self._passing_inputs()._replace(life_safety_factor=0.5)
        with self.assertRaises(ValueError):
            assess_lbb(bad)

    def test_through_wall_half_length_uses_initial_aspect_ratio(self):
        # aspect ratio c_0/a_0 = 2 -> a_tw = 2 * wall_thickness
        inp = self._passing_inputs()._replace(
            initial_crack_depth=0.0005,
            initial_half_length=0.0010,  # aspect ratio = 2
        )
        result = assess_lbb(inp)
        expected_a_tw = 2.0 * inp.wall_thickness
        self.assertAlmostEqual(result.through_wall_half_length, expected_a_tw, places=10)


if __name__ == "__main__":
    unittest.main()
