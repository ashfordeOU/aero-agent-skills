"""Offline contract test for rotorcraft-autorotative-descent logic.

Deterministic, stdlib unittest, no network. Run from the leaf directory:

    python3 scripts/test_rotorcraft_autorotative_descent.py

or from the repo root:

    python3 skills/flight-mechanics/performance/rotorcraft-autorotative-descent/scripts/test_rotorcraft_autorotative_descent.py
"""

import os
import sys
import unittest

# The logic module lives next to this test file; insert its directory.
sys.path.insert(
    0,
    os.path.dirname(os.path.abspath(__file__)),
)

from rotorcraft_autorotative_descent_logic import (  # noqa: E402
    G0,
    M0_TALBOT_MPS,
    M1_TALBOT,
    MPS_TO_FT_PER_MIN,
    VALIDITY_NOTE,
    autorotative_descent_assessment,
    energy_method_sink_rate,
    talbot_min_descent_rate_from_power,
    talbot_min_descent_rate_mps,
)

# Worked example: UH-1H-scale helicopter (NASA TM 78452 style case).
W = 42270.0        # weight, N
P = 380000.0       # minimum level-flight power, W
TIP = 208.0        # rotor tip speed OmegaR, m/s

# Real module outputs, taken as assert targets.
ENERGY_MPS = 8.989827300686066
TALBOT_MPS = 8.233286018452803
TALBOT_FT_PER_MIN = 1620.725594183623


class EnergyMethodTests(unittest.TestCase):
    """Energy-balance sink rate V = P_min / W."""

    def test_worked_example_value(self):
        self.assertAlmostEqual(
            energy_method_sink_rate(P, W), ENERGY_MPS, places=9
        )

    def test_worked_example_magnitude_bound(self):
        v = energy_method_sink_rate(P, W)
        self.assertTrue(8.5 <= v <= 9.5, "energy sink rate %r outside 8.5-9.5 m/s" % v)

    def test_simple_analytic_case(self):
        self.assertEqual(energy_method_sink_rate(100000.0, 10000.0), 10.0)

    def test_zero_weight_rejected(self):
        with self.assertRaises(ValueError):
            energy_method_sink_rate(P, 0.0)

    def test_negative_weight_rejected(self):
        with self.assertRaises(ValueError):
            energy_method_sink_rate(P, -W)

    def test_zero_power_rejected(self):
        with self.assertRaises(ValueError):
            energy_method_sink_rate(0.0, W)

    def test_negative_power_rejected(self):
        with self.assertRaises(ValueError):
            energy_method_sink_rate(-P, W)


class TalbotCorrelationTests(unittest.TestCase):
    """Empirical correlation V_est = M1 * tip * (cp_min / c_t) + M0."""

    def test_worked_example_coefficient_entry(self):
        cp_min_over_ct = P / (W * TIP)
        self.assertAlmostEqual(
            talbot_min_descent_rate_mps(cp_min_over_ct, 1.0, TIP),
            TALBOT_MPS,
            places=9,
        )

    def test_worked_example_magnitude_bound(self):
        v = talbot_min_descent_rate_mps(P / (W * TIP), 1.0, TIP)
        self.assertTrue(7.5 <= v <= 9.0, "empirical rate %r outside 7.5-9.0 m/s" % v)

    def test_empirical_below_energy_method(self):
        v_emp = talbot_min_descent_rate_mps(P / (W * TIP), 1.0, TIP)
        v_eng = energy_method_sink_rate(P, W)
        self.assertLess(v_emp, v_eng)

    def test_formula_expansion(self):
        cp, ct, tip = 0.0012, 0.0065, 200.0
        expected = M1_TALBOT * tip * (cp / ct) + M0_TALBOT_MPS
        self.assertEqual(talbot_min_descent_rate_mps(cp, ct, tip), expected)

    def test_intercept_only_when_cp_min_zero(self):
        self.assertEqual(talbot_min_descent_rate_mps(0.0, 1.0, 100.0), M0_TALBOT_MPS)

    def test_zero_ct_rejected(self):
        with self.assertRaises(ValueError):
            talbot_min_descent_rate_mps(0.001, 0.0, TIP)

    def test_zero_tip_speed_rejected(self):
        with self.assertRaises(ValueError):
            talbot_min_descent_rate_mps(0.001, 1.0, 0.0)

    def test_negative_cp_min_rejected(self):
        with self.assertRaises(ValueError):
            talbot_min_descent_rate_mps(-0.001, 1.0, TIP)


class PowerEntryAndConsistencyTests(unittest.TestCase):
    """Power-based entry and cross-entry consistency."""

    def test_from_power_worked_example(self):
        self.assertAlmostEqual(
            talbot_min_descent_rate_from_power(P, W, TIP), TALBOT_MPS, places=9
        )

    def test_cross_entry_consistency(self):
        cp_min = P / (W * TIP)  # ratio cp_min / c_t with c_t = 1.0
        via_coeff = talbot_min_descent_rate_mps(cp_min, 1.0, TIP)
        via_power = talbot_min_descent_rate_from_power(P, W, TIP)
        self.assertAlmostEqual(via_power, via_coeff, places=9)

    def test_level_flight_identity_expansion(self):
        expected = M1_TALBOT * (P / W) + M0_TALBOT_MPS
        self.assertEqual(talbot_min_descent_rate_from_power(P, W, TIP), expected)

    def test_zero_weight_rejected(self):
        with self.assertRaises(ValueError):
            talbot_min_descent_rate_from_power(P, 0.0, TIP)

    def test_negative_power_rejected(self):
        with self.assertRaises(ValueError):
            talbot_min_descent_rate_from_power(-P, W, TIP)

    def test_zero_power_rejected(self):
        with self.assertRaises(ValueError):
            talbot_min_descent_rate_from_power(0.0, W, TIP)

    def test_zero_tip_speed_rejected(self):
        with self.assertRaises(ValueError):
            talbot_min_descent_rate_from_power(P, W, 0.0)


class AssessmentDictTests(unittest.TestCase):
    """Convenience assessment dictionary."""

    def test_exact_keys(self):
        keys = set(autorotative_descent_assessment(W, P, TIP).keys())
        self.assertEqual(
            keys,
            {
                "energy_method_sink_rate_mps",
                "talbot_min_descent_rate_mps",
                "talbot_min_descent_rate_ft_per_min",
                "power_to_weight_ratio_mps",
                "validity_note",
            },
        )

    def test_energy_entry_value(self):
        a = autorotative_descent_assessment(W, P, TIP)
        self.assertAlmostEqual(a["energy_method_sink_rate_mps"], ENERGY_MPS, places=9)

    def test_talbot_entry_value(self):
        a = autorotative_descent_assessment(W, P, TIP)
        self.assertAlmostEqual(a["talbot_min_descent_rate_mps"], TALBOT_MPS, places=9)

    def test_ft_per_min_conversion_identity(self):
        a = autorotative_descent_assessment(W, P, TIP)
        self.assertEqual(
            a["talbot_min_descent_rate_ft_per_min"],
            a["talbot_min_descent_rate_mps"] * MPS_TO_FT_PER_MIN,
        )

    def test_power_to_weight_ratio_entry(self):
        a = autorotative_descent_assessment(W, P, TIP)
        self.assertEqual(a["power_to_weight_ratio_mps"], P / W)

    def test_fixed_validity_note(self):
        a = autorotative_descent_assessment(W, P, TIP)
        self.assertEqual(a["validity_note"], VALIDITY_NOTE)

    def test_valueerror_propagates_from_bad_weight(self):
        with self.assertRaises(ValueError):
            autorotative_descent_assessment(0.0, P, TIP)

class ModuleConstantsAndDeterminismTests(unittest.TestCase):
    """Pinned public-domain coefficients and determinism."""

    def test_talbot_coefficients(self):
        self.assertEqual(M0_TALBOT_MPS, 2.30)
        self.assertEqual(M1_TALBOT, 0.66)

    def test_standard_gravity(self):
        self.assertEqual(G0, 9.80665)

    def test_conversion_constant(self):
        self.assertEqual(MPS_TO_FT_PER_MIN, 60.0 / 0.3048)

    def test_reference_ft_conversion(self):
        self.assertAlmostEqual(8.233 * MPS_TO_FT_PER_MIN, 1620.67, places=1)

    def test_deterministic_talbot(self):
        a = autorotative_descent_assessment(W, P, TIP)
        b = autorotative_descent_assessment(W, P, TIP)
        self.assertEqual(a["talbot_min_descent_rate_mps"],
                         b["talbot_min_descent_rate_mps"])
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
