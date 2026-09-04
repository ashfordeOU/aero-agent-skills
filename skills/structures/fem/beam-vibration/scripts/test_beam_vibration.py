#!/usr/bin/env python3
"""Contract test for the continuous Euler-Bernoulli beam vibration logic.

Offline, deterministic, stdlib unittest. Covers the worked aluminum
beam (E = 73.1 GPa, rho = 2780 kg/m3, 50 x 100 mm, L = 2 m: EI =
3.04583333e5 N m^2, m = 13.9 kg/m), the published characteristic
roots, the pinned-pinned closed form and its exact n^2 ratios, the
Rayleigh upper bound (about 1.272x the exact fundamental), the
free-free elastic mode identity with clamped-clamped, mode-list
behavior, determinism, bisection tolerance, and ValueError rejection
of non-positive ei/mass/length, mode_n < 1, non-integer modes and
invalid boundary-condition names.

Run: python3 test_beam_vibration.py
"""

import math
import unittest

from beam_vibration_logic import (
    BC_CANTILEVER, BC_CLAMPED_CLAMPED, BC_FREE_FREE, BC_PINNED_PINNED,
    CANTILEVER_ROOTS, CLAMPED_FREE_FREE_ROOTS,
    beam_frequency, beam_mode_frequencies, cantilever_frequency,
    characteristic_root, clamped_clamped_frequency, free_free_frequency,
    pinned_pinned_frequency, rayleigh_fundamental,
)

# Worked aluminum beam: E = 73.1 GPa, rho = 2780 kg/m3, 50 x 100 mm,
# L = 2 m. EI = E b h^3 / 12 = 3.04583333e5 N m^2, m = rho b h = 13.9.
E = 73.1e9
RHO = 2780.0
B = 0.05
H = 0.10
LENGTH = 2.0
EI = E * B * H ** 3 / 12.0
MASS = RHO * B * H

# Real module outputs for the worked beam (assert targets).
CANT_F1 = 20.708878
CANT_F2 = 129.780320
CANT_F3 = 363.388655
PINNED_F1 = 58.130700
CLAMPED_F1 = 131.775773
RAYLEIGH_F = 26.340305

# Published roots beyond the first three cantilever / first two
# clamped values held as module constants (Blevins, 5th edition).
CANT_ROOT_4 = 10.99554073
CANT_ROOT_5 = 14.13716839
CLAMP_ROOT_3 = 10.99560784
CLAMP_ROOT_4 = 14.13716549


class BeamVibrationKnownRoots(unittest.TestCase):
    """Characteristic roots re-derived by bisection match published."""

    def test_cantilever_first_three_roots_match_published(self):
        for n, published in enumerate(CANTILEVER_ROOTS, start=1):
            self.assertAlmostEqual(
                characteristic_root(n, BC_CANTILEVER), published, delta=1e-5)

    def test_cantilever_roots_4_and_5_match_published(self):
        self.assertAlmostEqual(
            characteristic_root(4, BC_CANTILEVER), CANT_ROOT_4, delta=1e-5)
        self.assertAlmostEqual(
            characteristic_root(5, BC_CANTILEVER), CANT_ROOT_5, delta=1e-5)

    def test_clamped_first_two_roots_match_published(self):
        for n, published in enumerate(CLAMPED_FREE_FREE_ROOTS, start=1):
            self.assertAlmostEqual(
                characteristic_root(n, BC_CLAMPED_CLAMPED), published,
                delta=1e-5)

    def test_clamped_roots_3_and_4_match_published(self):
        self.assertAlmostEqual(
            characteristic_root(3, BC_CLAMPED_CLAMPED), CLAMP_ROOT_3,
            delta=1e-5)
        self.assertAlmostEqual(
            characteristic_root(4, BC_CLAMPED_CLAMPED), CLAMP_ROOT_4,
            delta=1e-5)

    def test_free_free_roots_equal_clamped_roots(self):
        for n in range(1, 7):
            self.assertEqual(
                characteristic_root(n, BC_FREE_FREE),
                characteristic_root(n, BC_CLAMPED_CLAMPED))

    def test_default_tolerance_beats_published_contract(self):
        # Contract requires 1e-5; the default 1e-12 bisection lands
        # well inside 1e-6 of every published value.
        for n, published in enumerate(CANTILEVER_ROOTS, start=1):
            self.assertLess(
                abs(characteristic_root(n, BC_CANTILEVER) - published), 1e-6)
        for n, published in enumerate(CLAMPED_FREE_FREE_ROOTS, start=1):
            self.assertLess(
                abs(characteristic_root(n, BC_CLAMPED_CLAMPED)
                    - published), 1e-6)


class BeamFrequencyWorkedExample(unittest.TestCase):
    """Worked aluminum beam frequencies sit inside the spec bounds."""

    def test_cantilever_first_three_frequencies_worked(self):
        # f1 about 20.709 Hz, f2 about 129.780 Hz, f3 about
        # 363.389 Hz.
        self.assertAlmostEqual(
            cantilever_frequency(1, EI, MASS, LENGTH), CANT_F1, delta=0.01)
        self.assertAlmostEqual(
            cantilever_frequency(2, EI, MASS, LENGTH), CANT_F2, delta=0.05)
        self.assertAlmostEqual(
            cantilever_frequency(3, EI, MASS, LENGTH), CANT_F3, delta=0.05)

    def test_pinned_pinned_f1_about_58_131_hz(self):
        self.assertAlmostEqual(
            pinned_pinned_frequency(1, EI, MASS, LENGTH), PINNED_F1,
            delta=0.01)

    def test_clamped_clamped_f1_about_131_776_hz(self):
        self.assertAlmostEqual(
            clamped_clamped_frequency(1, EI, MASS, LENGTH), CLAMPED_F1,
            delta=0.05)

    def test_free_free_first_elastic_equals_clamped_clamped(self):
        # Same characteristic equation and first elastic root
        # 4.73004074, so identical frequency.
        self.assertAlmostEqual(
            free_free_frequency(1, EI, MASS, LENGTH),
            clamped_clamped_frequency(1, EI, MASS, LENGTH), delta=1e-9)

    def test_rayleigh_about_26_340_hz(self):
        self.assertAlmostEqual(
            rayleigh_fundamental(EI, MASS, LENGTH), RAYLEIGH_F, delta=0.01)

    def test_rayleigh_is_upper_bound_about_1_272x_exact(self):
        rayleigh = rayleigh_fundamental(EI, MASS, LENGTH)
        exact = cantilever_frequency(1, EI, MASS, LENGTH)
        self.assertGreater(rayleigh, exact)
        self.assertAlmostEqual(rayleigh / exact, 1.2719, delta=0.001)

    def test_rayleigh_ratio_matches_sqrt20_over_3_51602(self):
        # omega_Rayleigh / omega_exact = sqrt(20) / 3.51602 for the
        # uniform cantilever parabola; verify from the actual outputs.
        rayleigh = rayleigh_fundamental(EI, MASS, LENGTH)
        exact = cantilever_frequency(1, EI, MASS, LENGTH)
        expected = math.sqrt(20.0) / 3.51602
        self.assertAlmostEqual(rayleigh / exact, expected, delta=1e-4)


class PinnedPinnedClosedForm(unittest.TestCase):
    """Closed-form frequencies and exact n^2 ratios."""

    def test_mode_ratio_is_exact_square(self):
        f1 = pinned_pinned_frequency(1, EI, MASS, LENGTH)
        for n in (2, 3, 5):
            fn = pinned_pinned_frequency(n, EI, MASS, LENGTH)
            self.assertAlmostEqual(fn / f1, float(n * n), places=9)

    def test_pinned_matches_beam_frequency_with_n_pi_root(self):
        for n in (1, 2, 3):
            self.assertAlmostEqual(
                pinned_pinned_frequency(n, EI, MASS, LENGTH),
                beam_frequency(n * math.pi, EI, MASS, LENGTH), places=9)

    def test_beam_frequency_matches_direct_formula(self):
        beta_n_L = characteristic_root(2, BC_CANTILEVER)
        direct = (beta_n_L ** 2) * math.sqrt(
            EI / (MASS * LENGTH ** 4)) / (2.0 * math.pi)
        self.assertAlmostEqual(
            beam_frequency(beta_n_L, EI, MASS, LENGTH), direct, places=12)

    def test_cantilever_round_trip_via_beam_frequency(self):
        # cantilever_frequency is beam_frequency applied to the
        # characteristic root; the round trip must be exact.
        for n in range(1, 5):
            beta = characteristic_root(n, BC_CANTILEVER)
            self.assertEqual(
                cantilever_frequency(n, EI, MASS, LENGTH),
                beam_frequency(beta, EI, MASS, LENGTH))


class BeamModeFrequenciesBehavior(unittest.TestCase):
    """Mode lists: counts, ordering, per-bc dispatch."""

    def test_cantilever_list_matches_individual_calls(self):
        modes = beam_mode_frequencies(BC_CANTILEVER, 3, EI, MASS, LENGTH)
        self.assertEqual(len(modes), 3)
        for n in (1, 2, 3):
            self.assertEqual(
                modes[n - 1], cantilever_frequency(n, EI, MASS, LENGTH))

    def test_every_bc_list_ascending_and_length(self):
        # 8 modes per bc, strictly ascending; mode 2 exceeds mode 1 for
        # every bc (pinned-pinned ratio 4, cantilever about 6.27,
        # clamped-clamped and free-free about 2.756).
        for bc in (BC_PINNED_PINNED, BC_CANTILEVER, BC_CLAMPED_CLAMPED,
                   BC_FREE_FREE):
            modes = beam_mode_frequencies(bc, 8, EI, MASS, LENGTH)
            self.assertEqual(len(modes), 8)
            for a, b in zip(modes, modes[1:]):
                self.assertGreater(b, a)
            self.assertGreater(modes[1] / modes[0], 2.5)

    def test_first_mode_is_fundamental(self):
        self.assertEqual(
            beam_mode_frequencies(BC_CANTILEVER, 1, EI, MASS, LENGTH),
            [cantilever_frequency(1, EI, MASS, LENGTH)])

    def test_free_free_elastic_modes_only(self):
        # Rigid-body (zero frequency) modes are excluded; the returned
        # elastic list matches clamped-clamped mode for mode.
        free = beam_mode_frequencies(BC_FREE_FREE, 5, EI, MASS, LENGTH)
        clamped = beam_mode_frequencies(
            BC_CLAMPED_CLAMPED, 5, EI, MASS, LENGTH)
        self.assertEqual(free, clamped)
        self.assertGreater(free[0], 0.0)


class DeterminismAndTolerance(unittest.TestCase):
    """No RNG, identical floats run to run, tol respected."""

    def test_outputs_deterministic_run_to_run(self):
        roots_a = [characteristic_root(n, BC_CANTILEVER) for n in (1, 2, 3)]
        roots_b = [characteristic_root(n, BC_CANTILEVER) for n in (1, 2, 3)]
        self.assertEqual(roots_a, roots_b)
        self.assertEqual(
            beam_mode_frequencies(BC_CLAMPED_CLAMPED, 5, EI, MASS, LENGTH),
            beam_mode_frequencies(BC_CLAMPED_CLAMPED, 5, EI, MASS, LENGTH))
        self.assertEqual(
            rayleigh_fundamental(EI, MASS, LENGTH),
            rayleigh_fundamental(EI, MASS, LENGTH))

    def test_bisection_tolerance_is_respected(self):
        # A coarse 1e-3 bisection stays within its width of the fine
        # 1e-12 result, for every root family.
        for bc in (BC_CANTILEVER, BC_CLAMPED_CLAMPED, BC_FREE_FREE):
            coarse = characteristic_root(2, bc, tol=1e-3)
            fine = characteristic_root(2, bc, tol=1e-12)
            self.assertLess(abs(coarse - fine), 2e-3)


class InputValidation(unittest.TestCase):
    """ValueError on non-positive inputs, bad modes, bad bc names."""

    def test_ei_nonpositive_raises(self):
        for fn in (cantilever_frequency, clamped_clamped_frequency,
                   pinned_pinned_frequency, free_free_frequency):
            with self.assertRaises(ValueError):
                fn(1, 0.0, MASS, LENGTH)
            with self.assertRaises(ValueError):
                fn(1, -1.0, MASS, LENGTH)

    def test_mass_nonpositive_raises(self):
        for fn in (cantilever_frequency, clamped_clamped_frequency,
                   pinned_pinned_frequency, free_free_frequency):
            with self.assertRaises(ValueError):
                fn(1, EI, 0.0, LENGTH)
            with self.assertRaises(ValueError):
                fn(1, EI, -13.9, LENGTH)

    def test_length_nonpositive_raises(self):
        for fn in (cantilever_frequency, clamped_clamped_frequency,
                   pinned_pinned_frequency, free_free_frequency):
            with self.assertRaises(ValueError):
                fn(1, EI, MASS, 0.0)
            with self.assertRaises(ValueError):
                fn(1, EI, MASS, -2.0)

    def test_mode_zero_negative_and_fractional_raise(self):
        for fn in (cantilever_frequency, clamped_clamped_frequency,
                   pinned_pinned_frequency, free_free_frequency):
            with self.assertRaises(ValueError):
                fn(0, EI, MASS, LENGTH)
        with self.assertRaises(ValueError):
            pinned_pinned_frequency(-1, EI, MASS, LENGTH)
        with self.assertRaises(ValueError):
            characteristic_root(-3, BC_CANTILEVER)
        with self.assertRaises(ValueError):
            cantilever_frequency(2.5, EI, MASS, LENGTH)
        with self.assertRaises(ValueError):
            characteristic_root(1.5, BC_CLAMPED_CLAMPED)

    def test_beam_frequency_nonpositive_beta_raises(self):
        with self.assertRaises(ValueError):
            beam_frequency(0.0, EI, MASS, LENGTH)
        with self.assertRaises(ValueError):
            beam_frequency(-1.875, EI, MASS, LENGTH)

    def test_invalid_bc_names_raise(self):
        # Neither the root solver nor the mode-list dispatcher accepts
        # off-spec bc names such as "clamped" (the valid name is
        # "clamped-clamped") or the empty string.
        for bad in ("clamped", "pinned", "", "cantilever-beam",
                    "fixed-fixed", "free"):
            with self.assertRaises(ValueError):
                characteristic_root(1, bad)
            with self.assertRaises(ValueError):
                beam_mode_frequencies(bad, 3, EI, MASS, LENGTH)

    def test_zero_modes_requested_raises(self):
        with self.assertRaises(ValueError):
            beam_mode_frequencies(BC_CANTILEVER, 0, EI, MASS, LENGTH)

    def test_rayleigh_unknown_shape_and_bad_inputs_raise(self):
        with self.assertRaises(ValueError):
            rayleigh_fundamental(EI, MASS, LENGTH, shape="x-squared")
        with self.assertRaises(ValueError):
            rayleigh_fundamental(EI, MASS, LENGTH, shape="")
        with self.assertRaises(ValueError):
            rayleigh_fundamental(0.0, MASS, LENGTH)
        with self.assertRaises(ValueError):
            rayleigh_fundamental(EI, 0.0, LENGTH)
        with self.assertRaises(ValueError):
            rayleigh_fundamental(EI, MASS, -2.0)

    def test_mode_frequencies_nonpositive_beam_inputs_raise(self):
        with self.assertRaises(ValueError):
            beam_mode_frequencies(BC_PINNED_PINNED, 3, EI, MASS, -1.0)
        with self.assertRaises(ValueError):
            beam_mode_frequencies(BC_CANTILEVER, 3, -EI, MASS, LENGTH)


if __name__ == "__main__":
    unittest.main()
