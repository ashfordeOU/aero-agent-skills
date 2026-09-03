"""Offline contract test for adhesive_bonded_joints_logic.

Runs with the stdlib only: python3 test_adhesive_bonded_joints.py
Covers the single-lap adhesive joint worked examples from the leaf
spec, boundary behaviour, ValueError rejection of non-physical inputs
and round-trip identities. Deterministic, no network, exits 0.
"""

import math
import sys
import unittest

sys.path.insert(0, "/Users/enterprisehq/AeroSkills/skills/structures/composites/adhesive-bonded-joints/scripts")
import adhesive_bonded_joints_logic as abj

# Worked example constants: aluminum adherends E 70 GPa, t 2 mm,
# adhesive G 0.5 GPa, t_a 0.2 mm, bond width 25 mm, load 10 kN.
E_ALU = 70e9
T_ADHEREND = 2e-3
G_ADHESIVE = 0.5e9
T_ADHESIVE = 0.2e-3
WIDTH = 25e-3
LOAD = 10e3
L_25 = 25e-3
L_10 = 10e-3
ALLOW_25 = 25e6
ALLOW_45 = 45e6


class TestShearLagBeta(unittest.TestCase):
    """Shear-lag parameter beta."""

    def test_worked_example_beta(self):
        beta = abj.shear_lag_beta(E_ALU, T_ADHEREND, G_ADHESIVE, T_ADHESIVE)
        self.assertAlmostEqual(beta, 188.98, delta=0.5)

    def test_beta_squared_identity(self):
        beta = abj.shear_lag_beta(E_ALU, T_ADHEREND, G_ADHESIVE, T_ADHESIVE)
        expected = (G_ADHESIVE / T_ADHESIVE) * (2.0 / (E_ALU * T_ADHEREND))
        self.assertAlmostEqual(beta * beta, expected, delta=1e-6)

    def test_beta_drops_with_stiffer_adherend(self):
        stiff = abj.shear_lag_beta(2.0 * E_ALU, T_ADHEREND, G_ADHESIVE, T_ADHESIVE)
        self.assertLess(stiff, abj.shear_lag_beta(E_ALU, T_ADHEREND, G_ADHESIVE, T_ADHESIVE))

    def test_beta_drops_with_thicker_bondline(self):
        thick = abj.shear_lag_beta(E_ALU, T_ADHEREND, G_ADHESIVE, 2.0 * T_ADHESIVE)
        self.assertLess(thick, abj.shear_lag_beta(E_ALU, T_ADHEREND, G_ADHESIVE, T_ADHESIVE))


class TestAverageShearStress(unittest.TestCase):
    """Average adhesive shear stress."""

    def test_avg_case1_25_mm(self):
        tau = abj.avg_shear_stress(LOAD, WIDTH, L_25)
        self.assertAlmostEqual(tau, 16e6, delta=1.0)

    def test_avg_case2_10_mm(self):
        tau = abj.avg_shear_stress(LOAD, WIDTH, L_10)
        self.assertAlmostEqual(tau, 40e6, delta=1.0)


class TestPeakShearStress(unittest.TestCase):
    """Peak stress with the Volkersen-style correction."""

    def test_peak_case1_within_spec(self):
        beta = abj.shear_lag_beta(E_ALU, T_ADHEREND, G_ADHESIVE, T_ADHESIVE)
        tau = abj.peak_shear_stress(LOAD, WIDTH, L_25, beta)
        self.assertAlmostEqual(tau / 1e6, 38.51, delta=0.2)

    def test_peak_case2_within_spec(self):
        beta = abj.shear_lag_beta(E_ALU, T_ADHEREND, G_ADHESIVE, T_ADHESIVE)
        tau = abj.peak_shear_stress(LOAD, WIDTH, L_10, beta)
        self.assertAlmostEqual(tau / 1e6, 51.27, delta=0.3)

    def test_shorter_overlap_raises_peak(self):
        beta = abj.shear_lag_beta(E_ALU, T_ADHEREND, G_ADHESIVE, T_ADHESIVE)
        peak_short = abj.peak_shear_stress(LOAD, WIDTH, L_10, beta)
        peak_long = abj.peak_shear_stress(LOAD, WIDTH, L_25, beta)
        self.assertGreater(peak_short, peak_long)

    def test_peak_exceeds_average(self):
        beta = abj.shear_lag_beta(E_ALU, T_ADHEREND, G_ADHESIVE, T_ADHESIVE)
        tau_avg = abj.avg_shear_stress(LOAD, WIDTH, L_25)
        tau_peak = abj.peak_shear_stress(LOAD, WIDTH, L_25, beta)
        self.assertGreater(tau_peak, tau_avg)

    def test_uniform_shear_limit_for_tiny_beta(self):
        tiny_beta = 1e-6
        tau_avg = abj.avg_shear_stress(LOAD, WIDTH, L_25)
        tau_peak = abj.peak_shear_stress(LOAD, WIDTH, L_25, tiny_beta)
        self.assertAlmostEqual(tau_peak, tau_avg, delta=1.0)


class TestConcentrationFactor(unittest.TestCase):
    """Peak to average concentration."""

    def test_concentration_case1_within_spec(self):
        beta = abj.shear_lag_beta(E_ALU, T_ADHEREND, G_ADHESIVE, T_ADHESIVE)
        self.assertAlmostEqual(abj.concentration_factor(beta, L_25), 2.407, delta=0.01)

    def test_concentration_is_peak_over_avg_roundtrip(self):
        beta = abj.shear_lag_beta(E_ALU, T_ADHEREND, G_ADHESIVE, T_ADHESIVE)
        ratio = (abj.peak_shear_stress(LOAD, WIDTH, L_25, beta) /
                 abj.avg_shear_stress(LOAD, WIDTH, L_25))
        self.assertAlmostEqual(abj.concentration_factor(beta, L_25), ratio, delta=1e-9)

    def test_concentration_grows_with_overlap(self):
        beta = abj.shear_lag_beta(E_ALU, T_ADHEREND, G_ADHESIVE, T_ADHESIVE)
        self.assertGreater(abj.concentration_factor(beta, 2.0 * L_25),
                           abj.concentration_factor(beta, L_25))


class TestJointMargin(unittest.TestCase):
    """Margin ratio and MS-style margin."""

    def test_joint_margin_case1_ratio(self):
        beta = abj.shear_lag_beta(E_ALU, T_ADHEREND, G_ADHESIVE, T_ADHESIVE)
        peak = abj.peak_shear_stress(LOAD, WIDTH, L_25, beta)
        self.assertAlmostEqual(abj.joint_margin(ALLOW_25, peak), 0.649, delta=0.01)

    def test_joint_margin_ms_is_ratio_minus_one(self):
        beta = abj.shear_lag_beta(E_ALU, T_ADHEREND, G_ADHESIVE, T_ADHESIVE)
        peak = abj.peak_shear_stress(LOAD, WIDTH, L_25, beta)
        ratio = abj.joint_margin(ALLOW_25, peak)
        self.assertAlmostEqual(ratio - 1.0, -0.351, delta=0.01)

    def test_margin_above_one_for_case3(self):
        beta = abj.shear_lag_beta(E_ALU, T_ADHEREND, G_ADHESIVE, T_ADHESIVE)
        peak = abj.peak_shear_stress(LOAD, WIDTH, L_25, beta)
        self.assertGreater(abj.joint_margin(ALLOW_45, peak), 1.0)

    def test_margin_scales_with_allowable(self):
        beta = abj.shear_lag_beta(E_ALU, T_ADHEREND, G_ADHESIVE, T_ADHESIVE)
        peak = abj.peak_shear_stress(LOAD, WIDTH, L_25, beta)
        self.assertAlmostEqual(abj.joint_margin(ALLOW_45, peak),
                               1.8 * abj.joint_margin(ALLOW_25, peak), delta=1e-9)


class TestAnalyze(unittest.TestCase):
    """Full joint analysis dict and verdicts."""

    def test_analyze_case1_fail_25_mpa(self):
        res = abj.analyze(LOAD, WIDTH, L_25, E_ALU, T_ADHEREND,
                          G_ADHESIVE, T_ADHESIVE, ALLOW_25)
        self.assertFalse(res["pass"])
        self.assertAlmostEqual(res["margin_ratio"], 0.649, delta=0.01)
        self.assertAlmostEqual(res["margin_ms"], -0.351, delta=0.01)

    def test_analyze_case2_fail_short_overlap(self):
        res = abj.analyze(LOAD, WIDTH, L_10, E_ALU, T_ADHEREND,
                          G_ADHESIVE, T_ADHESIVE, ALLOW_25)
        self.assertFalse(res["pass"])
        self.assertAlmostEqual(res["tau_avg"] / 1e6, 40.0, delta=1e-6)
        self.assertAlmostEqual(res["tau_max"] / 1e6, 51.27, delta=0.3)

    def test_analyze_case2_peak_higher_than_case1(self):
        r1 = abj.analyze(LOAD, WIDTH, L_25, E_ALU, T_ADHEREND,
                         G_ADHESIVE, T_ADHESIVE, ALLOW_25)
        r2 = abj.analyze(LOAD, WIDTH, L_10, E_ALU, T_ADHEREND,
                         G_ADHESIVE, T_ADHESIVE, ALLOW_25)
        self.assertGreater(r2["tau_max"], r1["tau_max"])

    def test_analyze_case3_pass_45_mpa(self):
        res = abj.analyze(LOAD, WIDTH, L_25, E_ALU, T_ADHEREND,
                          G_ADHESIVE, T_ADHESIVE, ALLOW_45)
        self.assertTrue(res["pass"])
        self.assertAlmostEqual(res["margin_ratio"], 1.169, delta=0.005)

    def test_analyze_returns_all_keys(self):
        res = abj.analyze(LOAD, WIDTH, L_25, E_ALU, T_ADHEREND,
                          G_ADHESIVE, T_ADHESIVE, ALLOW_25)
        for key in ("beta", "tau_avg", "tau_max", "concentration",
                    "margin_ratio", "margin_ms", "pass"):
            self.assertIn(key, res)

    def test_analyze_concentration_matches_peak_over_avg(self):
        res = abj.analyze(LOAD, WIDTH, L_25, E_ALU, T_ADHEREND,
                          G_ADHESIVE, T_ADHESIVE, ALLOW_25)
        self.assertAlmostEqual(res["concentration"],
                               res["tau_max"] / res["tau_avg"], delta=1e-9)

    def test_analyze_zero_load_passes(self):
        res = abj.analyze(0.0, WIDTH, L_25, E_ALU, T_ADHEREND,
                          G_ADHESIVE, T_ADHESIVE, ALLOW_25)
        self.assertEqual(res["tau_avg"], 0.0)
        self.assertEqual(res["tau_max"], 0.0)
        self.assertTrue(res["pass"])

    def test_analyze_doubled_load_halves_margin(self):
        r1 = abj.analyze(LOAD, WIDTH, L_25, E_ALU, T_ADHEREND,
                         G_ADHESIVE, T_ADHESIVE, ALLOW_25)
        r2 = abj.analyze(2.0 * LOAD, WIDTH, L_25, E_ALU, T_ADHEREND,
                         G_ADHESIVE, T_ADHESIVE, ALLOW_25)
        self.assertAlmostEqual(r1["tau_max"] * 2.0, r2["tau_max"], delta=1e-6)
        self.assertAlmostEqual(r1["margin_ratio"] / 2.0,
                               r2["margin_ratio"], delta=1e-9)
        self.assertFalse(r2["pass"])


class TestValueErrors(unittest.TestCase):
    """Non-physical inputs raise ValueError."""

    def test_negative_load_rejected(self):
        with self.assertRaises(ValueError):
            abj.avg_shear_stress(-1.0, WIDTH, L_25)
        with self.assertRaises(ValueError):
            abj.analyze(-1.0, WIDTH, L_25, E_ALU, T_ADHEREND,
                        G_ADHESIVE, T_ADHESIVE, ALLOW_25)

    def test_zero_overlap_rejected(self):
        with self.assertRaises(ValueError):
            abj.avg_shear_stress(LOAD, WIDTH, 0.0)
        with self.assertRaises(ValueError):
            abj.concentration_factor(100.0, 0.0)

    def test_zero_width_rejected(self):
        with self.assertRaises(ValueError):
            abj.avg_shear_stress(LOAD, 0.0, L_25)

    def test_zero_adherend_modulus_rejected(self):
        with self.assertRaises(ValueError):
            abj.shear_lag_beta(0.0, T_ADHEREND, G_ADHESIVE, T_ADHESIVE)

    def test_zero_adhesive_modulus_rejected(self):
        with self.assertRaises(ValueError):
            abj.shear_lag_beta(E_ALU, T_ADHEREND, 0.0, T_ADHESIVE)

    def test_zero_thicknesses_rejected(self):
        with self.assertRaises(ValueError):
            abj.shear_lag_beta(E_ALU, 0.0, G_ADHESIVE, T_ADHESIVE)
        with self.assertRaises(ValueError):
            abj.shear_lag_beta(E_ALU, T_ADHEREND, G_ADHESIVE, 0.0)

    def test_nonpositive_allowable_rejected(self):
        beta = abj.shear_lag_beta(E_ALU, T_ADHEREND, G_ADHESIVE, T_ADHESIVE)
        peak = abj.peak_shear_stress(LOAD, WIDTH, L_25, beta)
        with self.assertRaises(ValueError):
            abj.joint_margin(0.0, peak)
        with self.assertRaises(ValueError):
            abj.analyze(LOAD, WIDTH, L_25, E_ALU, T_ADHEREND,
                        G_ADHESIVE, T_ADHESIVE, 0.0)

class TestNumericalSafety(unittest.TestCase):
    """Stability of the hyperbolic correction."""

    def test_concentration_finite_for_long_overlap(self):
        beta = abj.shear_lag_beta(E_ALU, T_ADHEREND, G_ADHESIVE, T_ADHESIVE)
        self.assertTrue(math.isfinite(abj.concentration_factor(beta, 1.0)))


if __name__ == "__main__":
    unittest.main()
