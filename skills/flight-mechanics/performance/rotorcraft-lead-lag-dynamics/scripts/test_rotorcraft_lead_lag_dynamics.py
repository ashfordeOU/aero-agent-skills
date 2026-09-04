"""Offline contract test for rotorcraft-lead-lag-dynamics.

Deterministic stdlib unittest, no network, no RNG. Covers the worked
example magnitude bounds (lag frequency ratio nu about 0.2810 at e = 0.05
inside the published 0.2-0.4 per rev band, fixed-frame modes at Omega = 44
rad/s about 1.968 / 5.035 / 8.970 Hz, coincidence rotor speed about 43.69
rad/s for a 5.0 Hz airframe and about 30.58 rad/s for 3.5 Hz), the exact
e = 0 limit, the sqrt(1.5) closed form at e = 0.5, multiblade relations,
ValueError rejection of every non-physical input including the |1 - nu| =
0 guard, the summary input convention, and run-to-run determinism.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from rotorcraft_lead_lag_dynamics_logic import (  # noqa: E402
    PI,
    coincidence_rotor_speed,
    fixed_frame_lag_modes,
    ground_resonance_clearance,
    lag_frequency_ratio_hinge_offset,
    lead_lag_summary,
    regressing_lag_frequency,
)

NU_E005 = lag_frequency_ratio_hinge_offset(0.05)  # real module output, about 0.2810


class TestWorkedExample(unittest.TestCase):
    """Spec worked example: lag-hinge offset e = 0.05, Omega = 44 rad/s,
    airframe lateral frequencies 5.0 Hz (exposed) and 3.5 Hz (separated)."""

    def test_lag_frequency_ratio_magnitude(self):
        self.assertAlmostEqual(NU_E005, 0.2810, places=4)
        self.assertGreater(NU_E005, 0.2)
        self.assertLess(NU_E005, 0.4)

    def test_fixed_frame_mode_anchors(self):
        modes = fixed_frame_lag_modes(NU_E005, 44.0)
        self.assertAlmostEqual(modes["collective_hz"], 1.968, places=3)
        self.assertAlmostEqual(modes["regressing_hz"], 5.035, places=3)
        self.assertAlmostEqual(modes["advancing_hz"], 8.970, places=3)

    def test_regressing_per_rev_band(self):
        regressing = regressing_lag_frequency(NU_E005, 44.0)
        per_rev = regressing / (44.0 / (2.0 * PI))
        self.assertAlmostEqual(per_rev, 0.719, places=3)

    def test_coincidence_rotor_speeds(self):
        self.assertAlmostEqual(coincidence_rotor_speed(NU_E005, 5.0),
                               43.69, places=2)
        self.assertAlmostEqual(coincidence_rotor_speed(NU_E005, 3.5),
                               30.58, places=2)

    def test_clearance_verdicts(self):
        exposed = ground_resonance_clearance(NU_E005, 44.0, 5.0)
        self.assertEqual(exposed["verdict"], "resonance-adjacent")
        self.assertAlmostEqual(exposed["clearance_fraction"], -0.007, places=3)
        separated = ground_resonance_clearance(NU_E005, 44.0, 3.5)
        self.assertEqual(separated["verdict"], "clear")
        self.assertAlmostEqual(separated["clearance_fraction"], -0.305, places=3)


class TestLagFrequencyRatio(unittest.TestCase):
    """Closed-form identities and limits of the lag frequency ratio."""

    def test_zero_offset_exact_zero(self):
        self.assertEqual(lag_frequency_ratio_hinge_offset(0.0), 0.0)

    def test_half_offset_closed_form(self):
        self.assertAlmostEqual(lag_frequency_ratio_hinge_offset(0.5),
                               math.sqrt(1.5), places=9)

    def test_monotonic_increase(self):
        values = [lag_frequency_ratio_hinge_offset(e)
                  for e in (0.0, 0.02, 0.05, 0.2, 0.5, 0.8)]
        self.assertEqual(values, sorted(values))

    def test_offset_near_one_diverges(self):
        self.assertGreater(lag_frequency_ratio_hinge_offset(0.9), 3.0)


class TestFixedFrameModes(unittest.TestCase):
    """Multiblade fixed-frame identities at Omega = 44 rad/s."""

    def test_closed_form_identities(self):
        modes = fixed_frame_lag_modes(NU_E005, 44.0)
        self.assertAlmostEqual(modes["collective_hz"],
                               NU_E005 * 44.0 / (2.0 * PI), places=9)
        self.assertAlmostEqual(modes["regressing_hz"],
                               (1.0 - NU_E005) * 44.0 / (2.0 * PI), places=9)
        self.assertAlmostEqual(modes["advancing_hz"],
                               (1.0 + NU_E005) * 44.0 / (2.0 * PI), places=9)

    def test_advancing_minus_regressing(self):
        modes = fixed_frame_lag_modes(NU_E005, 44.0)
        self.assertAlmostEqual(modes["advancing_hz"] - modes["regressing_hz"],
                               2.0 * NU_E005 * 44.0 / (2.0 * PI), places=9)

    def test_mode_trends_with_nu(self):
        self.assertGreater(fixed_frame_lag_modes(0.2, 44.0)["regressing_hz"],
                           fixed_frame_lag_modes(0.4, 44.0)["regressing_hz"])
        self.assertLess(fixed_frame_lag_modes(0.2, 44.0)["advancing_hz"],
                        fixed_frame_lag_modes(0.4, 44.0)["advancing_hz"])

    def test_regressing_function_matches_modes(self):
        self.assertAlmostEqual(regressing_lag_frequency(NU_E005, 44.0),
                               fixed_frame_lag_modes(NU_E005, 44.0)["regressing_hz"],
                               places=12)

    def test_unity_nu_regressing_zero(self):
        self.assertEqual(fixed_frame_lag_modes(1.0, 44.0)["regressing_hz"], 0.0)

    def test_rotor_speed_scaling(self):
        slow = fixed_frame_lag_modes(NU_E005, 22.0)
        fast = fixed_frame_lag_modes(NU_E005, 44.0)
        self.assertAlmostEqual(fast["collective_hz"], 2.0 * slow["collective_hz"],
                               places=9)
        self.assertAlmostEqual(fast["regressing_hz"], 2.0 * slow["regressing_hz"],
                               places=9)


class TestCoincidenceAndClearance(unittest.TestCase):
    """Coleman-diagram coincidence rotor speed and clearance verdict."""

    def test_coincidence_closed_form_and_scaling(self):
        self.assertAlmostEqual(coincidence_rotor_speed(NU_E005, 5.0),
                               2.0 * PI * 5.0 / (1.0 - NU_E005), places=9)
        self.assertAlmostEqual(coincidence_rotor_speed(NU_E005, 10.0),
                               2.0 * coincidence_rotor_speed(NU_E005, 5.0),
                               places=9)

    def test_unity_nu_rejected(self):
        with self.assertRaises(ValueError):
            coincidence_rotor_speed(1.0, 5.0)

    def test_clearance_dict_keys(self):
        result = ground_resonance_clearance(NU_E005, 44.0, 5.0)
        self.assertEqual(set(result.keys()),
                         {"coincidence_omega", "operating_omega",
                          "clearance_fraction", "verdict"})

    def test_margin_changes_verdict_boundary(self):
        self.assertEqual(ground_resonance_clearance(NU_E005, 44.0, 3.5,
                                                    margin=0.20)["verdict"],
                         "clear")
        self.assertEqual(ground_resonance_clearance(NU_E005, 44.0, 3.5,
                                                    margin=0.35)["verdict"],
                         "resonance-adjacent")
        self.assertEqual(ground_resonance_clearance(NU_E005, 44.0, 3.5,
                                                    margin=0.0)["verdict"],
                         "clear")


class TestLeadLagSummary(unittest.TestCase):
    """One-call assessment dict and its documented input convention."""

    EXPECTED_KEYS = {"lag_frequency_ratio", "collective_hz", "regressing_hz",
                     "advancing_hz", "coincidence_omega", "operating_omega",
                     "clearance_fraction", "verdict"}

    def test_hinge_offset_input(self):
        result = lead_lag_summary(0.05, 44.0, 5.0)
        self.assertEqual(set(result.keys()), self.EXPECTED_KEYS)
        self.assertAlmostEqual(result["lag_frequency_ratio"], NU_E005, places=12)

    def test_matches_component_functions(self):
        result = lead_lag_summary(0.05, 44.0, 5.0)
        modes = fixed_frame_lag_modes(NU_E005, 44.0)
        self.assertEqual(result["collective_hz"], modes["collective_hz"])
        self.assertEqual(result["regressing_hz"], modes["regressing_hz"])
        self.assertEqual(result["advancing_hz"], modes["advancing_hz"])
        self.assertAlmostEqual(result["coincidence_omega"],
                               coincidence_rotor_speed(NU_E005, 5.0), places=12)
        self.assertEqual(result["verdict"], "resonance-adjacent")

    def test_nu_input_at_or_above_one(self):
        result = lead_lag_summary(1.05, 44.0, 5.0)
        self.assertEqual(result["lag_frequency_ratio"], 1.05)
        self.assertEqual(result["verdict"], "clear")
        self.assertEqual(lead_lag_summary(math.sqrt(1.5), 44.0, 5.0)
                         ["lag_frequency_ratio"],
                         lag_frequency_ratio_hinge_offset(0.5))

    def test_unity_nu_propagates_value_error(self):
        with self.assertRaises(ValueError):
            lead_lag_summary(1.0, 44.0, 5.0)


class TestValueErrors(unittest.TestCase):
    """Rejection of every non-physical input from the spec validation list."""

    def test_offset_rejections(self):
        for bad in (-0.05, 1.0, 1.5):
            with self.assertRaises(ValueError):
                lag_frequency_ratio_hinge_offset(bad)

    def test_mode_rejections(self):
        for bad_nu in (-0.1,):
            with self.assertRaises(ValueError):
                fixed_frame_lag_modes(bad_nu, 44.0)
        for bad_omega in (0.0, -5.0):
            with self.assertRaises(ValueError):
                fixed_frame_lag_modes(NU_E005, bad_omega)

    def test_regressing_rejections(self):
        with self.assertRaises(ValueError):
            regressing_lag_frequency(-0.1, 44.0)
        with self.assertRaises(ValueError):
            regressing_lag_frequency(NU_E005, 0.0)

    def test_coincidence_rejections(self):
        with self.assertRaises(ValueError):
            coincidence_rotor_speed(-0.1, 5.0)
        for bad_freq in (0.0, -3.0):
            with self.assertRaises(ValueError):
                coincidence_rotor_speed(NU_E005, bad_freq)

    def test_clearance_rejections(self):
        with self.assertRaises(ValueError):
            ground_resonance_clearance(NU_E005, 0.0, 5.0)
        with self.assertRaises(ValueError):
            ground_resonance_clearance(NU_E005, 44.0, 5.0, margin=-0.1)

    def test_summary_rejections(self):
        with self.assertRaises(ValueError):
            lead_lag_summary(-0.05, 44.0, 5.0)
        with self.assertRaises(ValueError):
            lead_lag_summary(0.05, 0.0, 5.0)
        with self.assertRaises(ValueError):
            lead_lag_summary(0.05, 44.0, 0.0)


class TestDeterminism(unittest.TestCase):
    """Identical floats run to run."""

    def test_run_to_run_identical(self):
        self.assertEqual(fixed_frame_lag_modes(NU_E005, 44.0),
                         fixed_frame_lag_modes(NU_E005, 44.0))
        self.assertEqual(ground_resonance_clearance(NU_E005, 44.0, 5.0),
                         ground_resonance_clearance(NU_E005, 44.0, 5.0))
        self.assertEqual(lead_lag_summary(0.05, 44.0, 5.0),
                         lead_lag_summary(0.05, 44.0, 5.0))


if __name__ == "__main__":
    unittest.main()
