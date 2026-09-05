#!/usr/bin/env python3
"""Gate 3 contract test: random-vibration fatigue from a stress PSD.

Exercises scripts/random_vibration_fatigue_logic.py (stdlib unittest,
offline, deterministic). Contract per the wave-38 leaf spec: trapezoid
spectral moments of a one-sided PSD, expected peak rate, narrow-band
Rayleigh damage, Dirlik mixture damage, fatigue life, ValueError
rejection of non-physical inputs, determinism, and the worked-example
anchors (flat PSD G0 = 2.0 MPa^2/Hz over 10 to 100 Hz, A = 1e12,
m = 4). Real module outputs are the assert targets within the spec
magnitude bounds. Note: with the spec's 2**m amplitude-moment
convention the Dirlik estimate lies above the narrow-band estimate at
every bandwidth, and the two damage rates track proportionally as the
band narrows (rate ratio tends to 2**(m/2) = 4 for m = 4); the tests
assert that convergence, which is what the module actually does.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import random_vibration_fatigue_logic as rv  # noqa: E402

G0 = 2.0
F1, F2 = 10.0, 100.0
A_ANCHOR = 1e12
M_ANCHOR = 4
N_SAMPLES = 4001


def flat_psd(g0, f1, f2, n=N_SAMPLES):
    """Uniformly sampled flat one-sided PSD over [f1, f2]."""
    freqs = [f1 + (f2 - f1) * i / (n - 1) for i in range(n)]
    return freqs, [g0] * n


def anchor_result():
    """The full worked-example dict, computed fresh each call."""
    return rv.random_vibration_fatigue(*flat_psd(G0, F1, F2), A_ANCHOR, M_ANCHOR)


class PSDMomentsTest(unittest.TestCase):
    """Trapezoid spectral moments and their guards."""

    def moments(self):
        return rv.psd_moments(*flat_psd(G0, F1, F2))

    def test_flat_moments_analytic_identity(self):
        m = self.moments()
        self.assertAlmostEqual(m["m0"], 180.0, delta=0.1)
        self.assertAlmostEqual(m["m1"], 9900.0, delta=10.0)
        self.assertAlmostEqual(m["m2"], 666000.0, delta=1000.0)
        self.assertAlmostEqual(m["m4"], 3.99996e9, delta=4.0e7)

    def test_single_segment_flat_exact(self):
        moments = rv.psd_moments([10.0, 100.0], [2.0, 2.0])
        self.assertAlmostEqual(moments["m0"], 180.0, places=9)
        self.assertAlmostEqual(moments["m1"], 90.0 * 110.0, places=6)

    def test_empty_arrays_raise(self):
        with self.assertRaises(ValueError):
            rv.psd_moments([], [2.0, 2.0])
        with self.assertRaises(ValueError):
            rv.psd_moments([10.0, 100.0], [])

    def test_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            rv.psd_moments([10.0, 20.0, 30.0], [1.0, 1.0])

    def test_negative_values_raise(self):
        with self.assertRaises(ValueError):
            rv.psd_moments([-10.0, 100.0], [2.0, 2.0])
        with self.assertRaises(ValueError):
            rv.psd_moments([10.0, 100.0], [2.0, -2.0])

    def test_unsorted_frequencies_raise(self):
        with self.assertRaises(ValueError):
            rv.psd_moments([100.0, 10.0], [2.0, 2.0])

    def test_single_point_is_zero_energy(self):
        moments = rv.psd_moments([50.0], [2.0])
        self.assertEqual(moments["m0"], 0.0)
        self.assertEqual(moments["m2"], 0.0)


class AnchorWorkedExampleTest(unittest.TestCase):
    """Worked-example anchors from the wave-38 spec, within tolerances."""

    @classmethod
    def setUpClass(cls):
        cls.res = anchor_result()
        mom = cls.res["moments"]
        cls.co = rv.dirlik_coefficients(mom["m0"], mom["m1"],
                                        mom["m2"], mom["m4"])

    def test_peak_rate_anchor(self):
        self.assertAlmostEqual(self.res["peak_rate"], 77.50, delta=0.775)

    def test_nb_damage_and_life_anchors(self):
        self.assertAlmostEqual(self.res["nb_damage_rate"],
                               1.577e-5, delta=3.2e-7)
        self.assertAlmostEqual(self.res["nb_life_h"], 17.62, delta=0.36)

    def test_dirlik_damage_and_life_anchors(self):
        self.assertAlmostEqual(self.res["dirlik_damage_rate"],
                               5.281e-5, delta=2.65e-6)
        self.assertAlmostEqual(self.res["dirlik_life_h"], 5.26, delta=0.27)

    def test_dirlik_parameter_anchors(self):
        checks = (("gamma", 0.7849, 0.004), ("x_m", 0.7097, 0.004),
                  ("D1", 0.1159, 0.001), ("R", 0.5483, 0.003),
                  ("D2", 0.2494, 0.002), ("D3", 0.6347, 0.004),
                  ("Q", 0.1449, 0.002))
        for name, anchor, tol in checks:
            self.assertAlmostEqual(self.co[name], anchor, delta=tol,
                                   msg=name)

    def test_dirlik_coefficients_sum_to_one(self):
        total = self.co["D1"] + self.co["D2"] + self.co["D3"]
        self.assertAlmostEqual(total, 1.0, places=12)

    def test_dirlik_life_governs_verdict(self):
        self.assertLess(self.res["dirlik_life_h"], self.res["nb_life_h"])
        self.assertIn("dirlik", self.res["verdict"])
        self.assertIn("5.26", self.res["verdict"])


class ScalingAndConvergenceTest(unittest.TestCase):
    """Identities the module must satisfy across level and bandwidth."""

    def rates_at(self, g0, m):
        return rv.random_vibration_fatigue(
            *flat_psd(g0, F1, F2), A_ANCHOR, m)

    def test_doubling_g0_scales_damage_as_m0_power(self):
        for m, factor in ((2, 2.0), (4, 4.0)):
            low = self.rates_at(G0, m)
            high = self.rates_at(2.0 * G0, m)
            self.assertAlmostEqual(
                high["nb_damage_rate"] / low["nb_damage_rate"],
                factor, places=9, msg="m=%d" % m)
            self.assertAlmostEqual(
                high["dirlik_damage_rate"] / low["dirlik_damage_rate"],
                factor, places=9, msg="m=%d" % m)

    def test_ratio_tends_to_power_half_as_band_narrows(self):
        narrow = rv.random_vibration_fatigue(
            *flat_psd(G0, 48.0, 52.0), A_ANCHOR, M_ANCHOR)
        ratio = narrow["dirlik_damage_rate"] / narrow["nb_damage_rate"]
        self.assertAlmostEqual(ratio, 2.0 ** (M_ANCHOR / 2.0), delta=0.08)

    def test_ratio_closer_to_limit_for_narrow_than_wide_band(self):
        narrow = rv.random_vibration_fatigue(
            *flat_psd(G0, 48.0, 52.0), A_ANCHOR, M_ANCHOR)
        wide = anchor_result()
        limit = 2.0 ** (M_ANCHOR / 2.0)
        narrow_err = abs(narrow["dirlik_damage_rate"] /
                         narrow["nb_damage_rate"] - limit)
        wide_err = abs(wide["dirlik_damage_rate"] /
                       wide["nb_damage_rate"] - limit)
        self.assertLess(narrow_err, wide_err)

    def test_nb_below_dirlik_on_anchor_band(self):
        res = anchor_result()
        self.assertLess(res["nb_damage_rate"], res["dirlik_damage_rate"])


class ZeroEnergyTest(unittest.TestCase):
    """Zero-energy PSD returns zero damage, reported, no error."""

    def test_zero_energy_zero_damage(self):
        res = rv.random_vibration_fatigue([10.0, 100.0], [0.0, 0.0],
                                          A_ANCHOR, M_ANCHOR)
        self.assertEqual(res["nb_damage_rate"], 0.0)
        self.assertEqual(res["dirlik_damage_rate"], 0.0)
        self.assertEqual(res["peak_rate"], 0.0)
        for name in ("m0", "m1", "m2", "m4"):
            self.assertEqual(res["moments"][name], 0.0)

    def test_zero_energy_unbounded_life(self):
        res = rv.random_vibration_fatigue([10.0, 100.0], [0.0, 0.0],
                                          A_ANCHOR, M_ANCHOR)
        self.assertIsNone(res["nb_life_h"])
        self.assertIsNone(res["dirlik_life_h"])
        self.assertIn("unbounded", res["verdict"])


class ValueErrorTest(unittest.TestCase):
    """Non-physical inputs raise ValueError."""

    def test_nonpositive_basquin_raises(self):
        for a in (0.0, -1.0):
            with self.assertRaises(ValueError):
                rv.random_vibration_fatigue(
                    *flat_psd(G0, F1, F2), a, M_ANCHOR)
        for m in (0.0, -2.0):
            with self.assertRaises(ValueError):
                rv.random_vibration_fatigue(
                    *flat_psd(G0, F1, F2), A_ANCHOR, m)

    def test_nonpositive_life_rate_raises(self):
        with self.assertRaises(ValueError):
            rv.fatigue_life_hours(0.0)
        with self.assertRaises(ValueError):
            rv.fatigue_life_hours(-1e-9)

    def test_zero_m0_moment_models_raise(self):
        with self.assertRaises(ValueError):
            rv.expected_peak_rate(0.0, 666000.0, 3.99996e9)
        with self.assertRaises(ValueError):
            rv.narrowband_damage_rate(0.0, 666000.0, 3.99996e9,
                                      A_ANCHOR, M_ANCHOR)

    def test_zero_m2_or_m1_moment_models_raise(self):
        with self.assertRaises(ValueError):
            rv.expected_peak_rate(180.0, 0.0, 3.99996e9)
        with self.assertRaises(ValueError):
            rv.narrowband_damage_rate(180.0, 666000.0, 0.0,
                                      A_ANCHOR, M_ANCHOR)
        with self.assertRaises(ValueError):
            rv.dirlik_coefficients(180.0, 0.0, 666000.0, 3.99996e9)

    def test_bad_moments_in_dirlik_damage_raise(self):
        with self.assertRaises(ValueError):
            rv.dirlik_damage_rate(180.0, 9900.0, 0.0, 3.99996e9,
                                  A_ANCHOR, M_ANCHOR)
        with self.assertRaises(ValueError):
            rv.dirlik_damage_rate(180.0, 9900.0, 666000.0, 3.99996e9,
                                  -5.0, 4)
        with self.assertRaises(ValueError):
            rv.dirlik_damage_rate(180.0, 9900.0, 666000.0, 3.99996e9,
                                  1e12, 0.0)


class ClosedFormIdentityTest(unittest.TestCase):
    """Damage rates equal their closed-form amplitude moments over A."""

    def test_nb_amplitude_moment_closed_form(self):
        res = anchor_result()
        m0, m2, m4 = (res["moments"]["m0"], res["moments"]["m2"],
                      res["moments"]["m4"])
        nu0 = math.sqrt(m2 / m0)
        expect = (math.sqrt(2.0 * m0)) ** M_ANCHOR * math.gamma(
            1.0 + M_ANCHOR / 2.0) / A_ANCHOR
        self.assertAlmostEqual(res["nb_damage_rate"], nu0 * expect,
                               places=12)

    def test_dirlik_amplitude_moment_closed_form(self):
        res = anchor_result()
        moments = res["moments"]
        co = rv.dirlik_coefficients(
            moments["m0"], moments["m1"], moments["m2"], moments["m4"])
        ep = math.sqrt(moments["m4"] / moments["m2"])
        expect = (math.sqrt(moments["m0"])) ** M_ANCHOR * (
            co["D1"] * co["Q"] ** M_ANCHOR * math.gamma(1.0 + M_ANCHOR)
            + 2.0 ** M_ANCHOR * math.gamma(1.0 + M_ANCHOR / 2.0)
            * (co["D2"] * abs(co["R"]) ** M_ANCHOR + co["D3"]))
        self.assertAlmostEqual(res["dirlik_damage_rate"],
                               ep * expect / A_ANCHOR, places=12)

    def test_life_is_inverse_of_rate(self):
        res = anchor_result()
        self.assertAlmostEqual(res["nb_life_h"],
                               1.0 / (res["nb_damage_rate"] * 3600.0),
                               places=9)
        self.assertAlmostEqual(res["dirlik_life_h"],
                               1.0 / (res["dirlik_damage_rate"] * 3600.0),
                               places=9)


class DeterminismTest(unittest.TestCase):
    """Repeated runs produce identical results."""

    def test_two_runs_identical(self):
        first = anchor_result()
        second = anchor_result()
        for key in ("moments", "peak_rate", "nb_damage_rate",
                    "dirlik_damage_rate", "nb_life_h", "dirlik_life_h",
                    "verdict"):
            self.assertEqual(first[key], second[key])

    def test_coefficients_deterministic(self):
        a = rv.dirlik_coefficients(180.0, 9900.0, 666000.0, 3.99996e9)
        b = rv.dirlik_coefficients(180.0, 9900.0, 666000.0, 3.99996e9)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
