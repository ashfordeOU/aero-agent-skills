#!/usr/bin/env python3
"""Contract test for the sears-function-gust-lift SKILL.md workflow.

Exercises the complete workflow of the leaf, step by step, against the
real prep anchors of the wave-45 spec (stdlib math, deterministic, exit
0): step 1 gathers the gust encounter inputs (density, speed, semi-chord,
gust amplitude, reduced frequency k and the gust frequency and wavelength
derived from it), step 2 confirms the Bessel machinery (the J0/J1/Y0/Y1
series against the published Abramowitz and Stegun constants at x = 0.5,
1.0 and 2.0), step 3 evaluates the complex sears function S(k) through
the Theodorsen lift-deficiency function C(k), step 4 sweeps the gust gain
and the phase lag over the reduced-frequency sweep and checks the
monotone gain roll-off and phase-lag growth, step 5 computes the
gust-load amplitudes against the quasi-steady 2*pi*rho*V*b*w_g
reference, step 6 locates the half-amplitude reduced frequency where
|S(k)| = 0.5 by deterministic bisection, and step 7 verifies the
Wronskian gain identity |S(k)| = (2/(pi*k))/|H1^(2)(k) + i*H0^(2)(k)|
built from the public Bessel functions. Also asserts the ValueError
rejection of non-physical inputs, determinism (two identical sweeps
return identical bits), and that the logic module imports nothing beyond
the stdlib math module and carries no RNG. Tolerances follow the kit
lesson: no exact-float equality on computed sums, math.isclose and
assertAlmostEqual everywhere.
"""

import math
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sears_function_gust_lift_logic as sfg

PI = math.pi

# Published constants (Abramowitz and Stegun 9.1 tables) and the wave-45
# spec anchor digits. All asserts are tolerance-based (kit exact-float
# lesson); the REAL anchor worst Bessel error is 9.44e-16.
J0_REF = {0.5: 0.938469807240813, 1.0: 0.7651976865579666,
          2.0: 0.2238907791412356}
J1_REF = {0.5: 0.2422684576748739, 1.0: 0.4400505857449336,
          2.0: 0.5767248077568736}
Y0_REF = {0.5: -0.4445187335067066, 1.0: 0.088256964215677,
          2.0: 0.5103756726497453}
Y1_REF = {0.5: -1.471472392670243, 1.0: -0.7812128213002887,
          2.0: -0.1070324315409374}


class TestWorkflowStep2BesselMachinery(unittest.TestCase):
    """Workflow step 2 (confirm the Bessel machinery)."""

    def test_bessel_j0_reference_constants(self):
        """J0 series matches the published constants at x = 0.5, 1, 2."""
        for x, ref in J0_REF.items():
            self.assertTrue(math.isclose(sfg.bessel_j0(x), ref, abs_tol=1e-12),
                            "J0(%s) = %r vs %r" % (x, sfg.bessel_j0(x), ref))

    def test_bessel_j1_reference_constants(self):
        """J1 series matches the published constants at x = 0.5, 1, 2."""
        for x, ref in J1_REF.items():
            self.assertTrue(math.isclose(sfg.bessel_j1(x), ref, abs_tol=1e-12),
                            "J1(%s) = %r vs %r" % (x, sfg.bessel_j1(x), ref))

    def test_bessel_y0_reference_constants(self):
        """Y0 log-harmonic series matches the published constants."""
        for x, ref in Y0_REF.items():
            self.assertTrue(math.isclose(sfg.bessel_y0(x), ref, abs_tol=1e-12),
                            "Y0(%s) = %r vs %r" % (x, sfg.bessel_y0(x), ref))

    def test_bessel_y1_reference_constants(self):
        """Y1 log-harmonic series matches the published constants."""
        for x, ref in Y1_REF.items():
            self.assertTrue(math.isclose(sfg.bessel_y1(x), ref, abs_tol=1e-12),
                            "Y1(%s) = %r vs %r" % (x, sfg.bessel_y1(x), ref))

    def test_bessel_series_worst_error_bound(self):
        """Worst absolute error over the 12 Bessel constants stays small."""
        worst = 0.0
        for x in (0.5, 1.0, 2.0):
            worst = max(worst, abs(sfg.bessel_j0(x) - J0_REF[x]),
                        abs(sfg.bessel_j1(x) - J1_REF[x]),
                        abs(sfg.bessel_y0(x) - Y0_REF[x]),
                        abs(sfg.bessel_y1(x) - Y1_REF[x]))
        self.assertLess(worst, 1e-12)  # real anchor worst error 9.44e-16


class TestWorkflowStep3TheodorsenAndSears(unittest.TestCase):
    """Workflow step 3 (evaluate the complex sears function)."""

    def test_theodorsen_c_zero_exact(self):
        """C(0) is exactly 1 + 0j, the steady-flow limit of step 3."""
        self.assertEqual(sfg.theodorsen_c(0.0), 1.0 + 0.0j)

    def test_theodorsen_c_half(self):
        """C(0.5) = 0.597936064250132 - 0.1507095031626353i within 1e-9."""
        c = sfg.theodorsen_c(0.5)
        self.assertTrue(math.isclose(c.real, 0.597936064250132, abs_tol=1e-9))
        self.assertTrue(math.isclose(c.imag, -0.1507095031626353, abs_tol=1e-9))
        self.assertTrue(math.isclose(abs(c), 0.6166367579657139, abs_tol=1e-9))

    def test_theodorsen_c_one(self):
        """C(1.0) = 0.5394348710777939 - 0.1002729028641078i within 1e-9."""
        c = sfg.theodorsen_c(1.0)
        self.assertTrue(math.isclose(c.real, 0.5394348710777939, abs_tol=1e-9))
        self.assertTrue(math.isclose(c.imag, -0.1002729028641078, abs_tol=1e-9))
        self.assertTrue(math.isclose(abs(c), 0.5486753458863547, abs_tol=1e-9))

    def test_theodorsen_c_two_toward_half_limit(self):
        """C(2.0) sits above the documented high-k limit |C| = 1/2."""
        c = sfg.theodorsen_c(2.0)
        self.assertTrue(math.isclose(c.real, 0.5129548124291317, abs_tol=1e-9))
        self.assertTrue(math.isclose(c.imag, -0.05769128342167992, abs_tol=1e-9))
        self.assertTrue(math.isclose(abs(c), 0.5161888450722721, abs_tol=1e-9))
        self.assertGreater(abs(c), 0.5)

    def test_sears_function_zero_quasi_steady_limit(self):
        """S(0) is exactly 1 + 0j: gain 1, zero phase lag, the
        quasi-steady limit of the gust-load reference."""
        s = sfg.sears_function(0.0)
        self.assertEqual(s, 1.0 + 0.0j)
        self.assertEqual(sfg.sears_gain(0.0), 1.0)
        self.assertEqual(sfg.sears_phase_lag(0.0), 0.0)

    def test_sears_function_complex_reference_values(self):
        """S(k) complex values match the spec Identities within 1e-9 per
        part (relative to max(1, |part|)) at k = 0.1, 0.25, 0.5, 1, 2."""
        refs = {
            0.1: (0.800817849647392, -0.244649056217272),
            0.25: (0.6026337749688766, -0.3027386944162097),
            0.5: (0.4392999993899336, -0.2901613576384412),
            1.0: (0.3051596787128952, -0.2421600879532278),
            2.0: (0.2097218163963314, -0.1856916381211891),
        }
        for k, (re_ref, im_ref) in refs.items():
            s = sfg.sears_function(k)
            tol = 1e-9 * max(1.0, abs(re_ref), abs(im_ref))
            self.assertTrue(math.isclose(s.real, re_ref, abs_tol=tol))
            self.assertTrue(math.isclose(s.imag, im_ref, abs_tol=tol))


class TestWorkflowStep4GainAndPhaseSweep(unittest.TestCase):
    """Workflow step 4 (sweep the gust gain and the phase lag)."""

    def test_sears_gain_reference_values(self):
        """Gain read-off |S(0.1)| = 0.8373543986997829, |S(0.5)| =
        0.5264770678107253, |S(1.0)| = 0.3895689126581746, |S(2.0)| =
        0.2801153775512997 within 1e-9."""
        refs = {0.1: 0.8373543986997829, 0.5: 0.5264770678107253,
                1.0: 0.3895689126581746, 2.0: 0.2801153775512997}
        for k, ref in refs.items():
            self.assertTrue(math.isclose(sfg.sears_gain(k), ref, abs_tol=1e-9))

    def test_sears_phase_lag_reference_values(self):
        """Phase lag 0.2964940866019039 (0.1), 0.5837270902719581 (0.5),
        0.6707968790189207 (1.0), 0.7247005314150557 (2.0) rad, within
        1e-9, and 33.44509866003521 deg at k = 0.5."""
        refs = {0.1: 0.2964940866019039, 0.5: 0.5837270902719581,
                1.0: 0.6707968790189207, 2.0: 0.7247005314150557}
        for k, ref in refs.items():
            self.assertTrue(math.isclose(sfg.sears_phase_lag(k), ref,
                                         abs_tol=1e-9))
        deg = 180.0 * sfg.sears_phase_lag(0.5) / PI
        self.assertTrue(math.isclose(deg, 33.44509866003521, abs_tol=1e-9))

    def test_gain_monotone_rolloff_sweep(self):
        """Gain strictly decreasing at every 0.05 step of the 0.1 to 2.0
        reduced-frequency sweep (the monotone roll-off of step 4)."""
        prev = sfg.sears_gain(0.1)
        k = 0.15
        while k <= 2.0 + 1e-12:
            g = sfg.sears_gain(k)
            self.assertLess(g, prev)
            prev = g
            k += 0.05

    def test_phase_lag_monotone_sweep(self):
        """Phase lag strictly increasing at every 0.05 step of the sweep."""
        prev = sfg.sears_phase_lag(0.1)
        k = 0.15
        while k <= 2.0 + 1e-12:
            lag = sfg.sears_phase_lag(k)
            self.assertGreater(lag, prev)
            prev = lag
            k += 0.05


class TestWorkflowStep7WronskianIdentity(unittest.TestCase):
    """Workflow step 7 (Wronskian gain identity verification)."""

    def test_closed_form_gain_identity_sweep(self):
        """Step 7 identity: |S(k)| = (2/(pi*k))/|H1^(2)(k) + i*H0^(2)(k)|
        at every 0.1 step of k in [0.1, 2.0], Hankel built from the
        public Bessel functions; the Bessel Wronskian makes the identity
        exact, real anchor max residual 2.22e-16, bound 1e-12."""
        k = 0.1
        while k <= 2.0 + 1e-12:
            h0 = complex(sfg.bessel_j0(k), -sfg.bessel_y0(k))
            h1 = complex(sfg.bessel_j1(k), -sfg.bessel_y1(k))
            ident = (2.0 / (PI * k)) / abs(h1 + 1.0j * h0)
            self.assertLess(abs(sfg.sears_gain(k) - ident), 1e-12)
            k += 0.1


class TestWorkflowStep6HalfAmplitude(unittest.TestCase):
    """Workflow step 6 (locate the half-amplitude reduced frequency)."""

    def test_half_gain_reduced_frequency_value(self):
        """Bisection returns k_half = 0.5672427076304547 within 1e-9 and
        the gain there is 0.5 within 1e-9."""
        k_half = sfg.half_gain_reduced_frequency()
        self.assertTrue(math.isclose(k_half, 0.5672427076304547, abs_tol=1e-9))
        self.assertTrue(math.isclose(sfg.sears_gain(k_half), 0.5, abs_tol=1e-9))

    def test_half_gain_bracket_sanity(self):
        """Bracket sanity: gain(0.5) > 0.5 > gain(0.6), so the crossing
        sits inside the default bisection bracket [0.1, 2.0]."""
        self.assertGreater(sfg.sears_gain(0.5), 0.5)
        self.assertLess(sfg.sears_gain(0.6), 0.5)

    def test_half_gain_reversed_bracket_raises(self):
        """A reversed bracket raises ValueError (half_gain_reduced_
        frequency(2.0, 0.1), the anchor case)."""
        with self.assertRaises(ValueError):
            sfg.half_gain_reduced_frequency(2.0, 0.1)

    def test_half_gain_unbracketed_raises(self):
        """A bracket that does not straddle 0.5 raises ValueError."""
        with self.assertRaises(ValueError):
            sfg.half_gain_reduced_frequency(0.05, 0.2)  # both gains > 0.5
        with self.assertRaises(ValueError):
            sfg.half_gain_reduced_frequency(0.6, 2.0)  # both gains < 0.5


class TestWorkflowStep1And5GustLoads(unittest.TestCase):
    """Workflow steps 1 and 5 (inputs, quasi-steady reference, loads)."""

    def test_quasi_steady_gust_lift_worked_example(self):
        """Step 5 reference: L_qs = 2*pi*rho*V*b*w_g = 3078.760800517998
        N/m at rho = 1.225, V = 80, b = 1, w_g = 5, within 1e-6 relative."""
        l_qs = sfg.quasi_steady_gust_lift(1.225, 80.0, 1.0, 5.0)
        self.assertTrue(math.isclose(l_qs, 3078.760800517998,
                                     rel_tol=1e-6))

    def test_unsteady_gust_load_worked_example_and_ratio(self):
        """Step 5 load: L_hat = 1620.896958747317 N/m at k = 0.5 within
        1e-6 relative, and L_hat/L_qs equals sears_gain(0.5) within
        1e-12 (the load is L_qs times the gain by construction)."""
        l_qs = sfg.quasi_steady_gust_lift(1.225, 80.0, 1.0, 5.0)
        l_hat = sfg.unsteady_gust_load(1.225, 80.0, 1.0, 5.0, 0.5)
        self.assertTrue(math.isclose(l_hat, 1620.896958747317,
                                     rel_tol=1e-6))
        self.assertTrue(math.isclose(l_hat / l_qs, sfg.sears_gain(0.5),
                                     abs_tol=1e-12))

    def test_reduced_frequency_round_trip(self):
        """Step 1 conversion: reduced_frequency(6.366197723675814 Hz, 80
        m/s, 1 m) = 0.5 within 1e-12 (k = 2*pi*f*b/V)."""
        k = sfg.reduced_frequency(6.366197723675814, 80.0, 1.0)
        self.assertTrue(math.isclose(k, 0.5, abs_tol=1e-12))

    def test_gust_frequency_and_wavelength_worked(self):
        """Step 1 geometry: f = k*V/(2*pi*b) = 6.366197723675814 Hz and
        lambda = V/f = 12.56637061435917 m = 6.283185307179586 chord
        lengths at the worked k = 0.5, b = 1 m point."""
        f = 0.5 * 80.0 / (2.0 * PI * 1.0)
        self.assertTrue(math.isclose(f, 6.366197723675814, abs_tol=1e-12))
        lam = 80.0 / f
        self.assertTrue(math.isclose(lam, 12.56637061435917, abs_tol=1e-12))
        self.assertTrue(math.isclose(lam / 2.0, 6.283185307179586,
                                     abs_tol=1e-12))

    def test_half_amplitude_gust_load_worked(self):
        """Step 6 load: at k_half the unsteady load is
        1539.380400258999 N/m within 1e-6 relative and the ratio to L_qs
        is 0.5000000000000001 within 1e-9 (half the quasi-steady value)."""
        l_qs = sfg.quasi_steady_gust_lift(1.225, 80.0, 1.0, 5.0)
        k_half = sfg.half_gain_reduced_frequency()
        l_half = sfg.unsteady_gust_load(1.225, 80.0, 1.0, 5.0, k_half)
        self.assertTrue(math.isclose(l_half, 1539.380400258999,
                                     rel_tol=1e-6))
        self.assertTrue(math.isclose(l_half / l_qs, 0.5000000000000001,
                                     abs_tol=1e-9))

    def test_zero_gust_amplitude_allowed(self):
        """A zero gust amplitude is physical: L_qs = 0 and L_hat = 0."""
        self.assertEqual(sfg.quasi_steady_gust_lift(1.225, 80.0, 1.0, 0.0),
                         0.0)
        self.assertEqual(sfg.unsteady_gust_load(1.225, 80.0, 1.0, 0.0, 0.5),
                         0.0)


class TestValueErrorRejection(unittest.TestCase):
    """ValueError rejection of non-physical inputs across the module."""

    def test_bessel_argument_valueerrors(self):
        """Zero or negative Bessel arguments raise ValueError: bessel_j0(0),
        bessel_j1(-1), bessel_y0(0), bessel_y1(0) and non-finite x."""
        for fn in (sfg.bessel_j0, sfg.bessel_j1, sfg.bessel_y0, sfg.bessel_y1):
            with self.assertRaises(ValueError):
                fn(0.0)
        with self.assertRaises(ValueError):
            sfg.bessel_j1(-1.0)
        with self.assertRaises(ValueError):
            sfg.bessel_j0(float("nan"))

    def test_reduced_frequency_k_valueerrors(self):
        """Negative or non-finite k raises ValueError on the Theodorsen,
        Sears, gain and phase-lag functions (workflow step 3 and 4)."""
        for fn in (sfg.theodorsen_c, sfg.sears_function, sfg.sears_gain,
                   sfg.sears_phase_lag):
            with self.assertRaises(ValueError):
                fn(-0.5)
        with self.assertRaises(ValueError):
            sfg.sears_function(float("nan"))
        with self.assertRaises(ValueError):
            sfg.sears_gain(float("inf"))

    def test_gust_load_input_valueerrors(self):
        """Non-positive density, speed or semi-chord, and negative or
        non-finite gust amplitude raise ValueError in step 5 functions."""
        with self.assertRaises(ValueError):
            sfg.quasi_steady_gust_lift(0.0, 80.0, 1.0, 5.0)
        with self.assertRaises(ValueError):
            sfg.quasi_steady_gust_lift(1.225, 80.0, 1.0, -5.0)
        with self.assertRaises(ValueError):
            sfg.quasi_steady_gust_lift(1.225, -80.0, 1.0, 5.0)
        with self.assertRaises(ValueError):
            sfg.quasi_steady_gust_lift(1.225, 80.0, 1.0, float("nan"))
        with self.assertRaises(ValueError):
            sfg.unsteady_gust_load(1.225, 80.0, 1.0, 5.0, -0.5)
        with self.assertRaises(ValueError):
            sfg.unsteady_gust_load(1.225, 80.0, 1.0, 5.0, float("nan"))

    def test_reduced_frequency_input_valueerrors(self):
        """Zero frequency or non-positive speed or semi-chord raise
        ValueError in the step 1 reduced-frequency conversion."""
        with self.assertRaises(ValueError):
            sfg.reduced_frequency(0.0, 80.0, 1.0)
        with self.assertRaises(ValueError):
            sfg.reduced_frequency(5.0, 0.0, 1.0)
        with self.assertRaises(ValueError):
            sfg.reduced_frequency(5.0, 80.0, -1.0)


class TestDeterminismAndPurity(unittest.TestCase):
    """Determinism and stdlib purity of the logic module."""

    def test_determinism_identical_sweeps(self):
        """Two identical full sweeps return identical bits (no RNG)."""
        a = [sfg.sears_function(0.1 * i) for i in range(21)]
        b = [sfg.sears_function(0.1 * i) for i in range(21)]
        self.assertEqual(a, b)

    def test_logic_module_stdlib_only(self):
        """The logic module imports nothing beyond math (no numpy, no
        random, no RNG) and pins the documented module constants."""
        with open(sfg.__file__) as fh:
            src = fh.read()
        imports = re.findall(r"^\s*(?:import|from)\s+(\w+)", src,
                             re.MULTILINE)
        self.assertEqual(imports, ["math"])
        self.assertNotIn("random", src)
        self.assertTrue(math.isclose(sfg.EULER_GAMMA,
                                     0.5772156649015329, abs_tol=1e-15))
        self.assertEqual(sfg.SERIES_TERMS_MAX, 300)
        self.assertEqual(sfg.SERIES_TOL, 1e-18)
        self.assertEqual(sfg.BISECT_LO, 0.1)
        self.assertEqual(sfg.BISECT_HI, 2.0)


if __name__ == "__main__":
    unittest.main()
