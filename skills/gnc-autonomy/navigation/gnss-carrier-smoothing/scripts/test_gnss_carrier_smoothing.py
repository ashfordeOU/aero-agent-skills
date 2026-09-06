"""Contract test for gnss-carrier-smoothing (gnc-autonomy/navigation).

Deterministic, offline, stdlib only (math + random with fixed seeds for
the documented simulation streams).  Exercises the SKILL.md workflow:
step 1 sets the smoothing configuration (time constant tau, update
interval T, alpha = T/tau); step 2 runs the Hatch recursion traverse
over the code-carrier stream, seeding with the raw code and carrying
with the carrier delta ranges; step 3 forms the noise-reduction verdict
from the exact code-only closed form, its textbook limit and the
carrier delta-range term; step 4 runs the code-carrier divergence
monitor, fitting the trailing-window slope, predicting the steady-state
smoothed-minus-code bias and raising the alarm; step 5 gates the
smoothed range for positioning.  Asserts the spec worked-example
anchors (real module outputs) within tolerance, the closed-form
identities, boundary cases, deterministic replay and ValueError
rejection of non-physical inputs.

Run: python3 scripts/test_gnss_carrier_smoothing.py
"""

import math
import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gnss_carrier_smoothing_logic as gcs

TRUTH = 20000000.0
N_EPOCHS = 40000
SKIP = 2000


def _noisy_diffs(v, n, rng):
    """Diffs D_k = 2*v*T*k + code noise for the divergence monitor."""
    return [2.0 * v * 1.0 * k + rng.gauss(0.0, 0.3) for k in range(n)]


class TestSmoothingConfiguration(unittest.TestCase):
    """Workflow step 1: the smoothing configuration."""

    def test_alpha_default_exact_and_pole(self):
        """alpha_from_time_constant(100, 1) is 0.01 and the recursion pole
        1 - alpha sits in (0, 1) with variance relaxation about tau/2 = 50 s,
        the smoothing configuration the SKILL.md workflow fixes first."""
        alpha = gcs.alpha_from_time_constant(100.0, 1.0)
        self.assertAlmostEqual(alpha, 0.01, delta=1e-15)
        pole = 1.0 - alpha
        self.assertGreater(pole, 0.0)
        self.assertLess(pole, 1.0)
        self.assertAlmostEqual(pole, 0.99, delta=1e-15)
        self.assertAlmostEqual(100.0 / 2.0, 50.0, delta=1e-12)

    def test_alpha_scales_with_update_interval(self):
        """alpha = T/tau exactly: halving T halves alpha and doubling T
        doubles it at a fixed time constant."""
        self.assertAlmostEqual(gcs.alpha_from_time_constant(100.0, 0.5),
                               0.005, delta=1e-15)
        self.assertAlmostEqual(gcs.alpha_from_time_constant(100.0, 2.0),
                               0.02, delta=1e-15)

    def test_alpha_rejects_invalid_tau_and_T(self):
        """Non-physical configurations are rejected: tau at 0 or negative,
        T at 0 or negative, and T at or above tau where alpha >= 1 would
        mean no smoothing at all."""
        for tau in (0.0, -5.0):
            with self.assertRaises(ValueError):
                gcs.alpha_from_time_constant(tau, 1.0)
        for T in (0.0, -1.0):
            with self.assertRaises(ValueError):
                gcs.alpha_from_time_constant(100.0, T)
        with self.assertRaises(ValueError):
            gcs.alpha_from_time_constant(100.0, 100.0)
        with self.assertRaises(ValueError):
            gcs.alpha_from_time_constant(100.0, 150.0)

    def test_alpha_rejects_nonfinite_inputs(self):
        """NaN and infinite time constant or interval cannot define a
        smoothing configuration and raise ValueError."""
        for bad in (float("inf"), float("nan")):
            with self.assertRaises(ValueError):
                gcs.alpha_from_time_constant(bad, 1.0)
            with self.assertRaises(ValueError):
                gcs.alpha_from_time_constant(100.0, bad)


class TestHatchRecursionTraverse(unittest.TestCase):
    """Workflow step 2: the Hatch recursion traverse."""

    def test_hatch_update_matches_recursion_formula(self):
        """One step of the traverse: s = alpha*code + (1-alpha)*
        (previous smoothed + carrier delta range), at the worked-example
        ramp values."""
        s = gcs.hatch_update(TRUTH, TRUTH + 0.02, -0.02, 0.01)
        expected = 0.01 * (TRUTH + 0.02) + 0.99 * (TRUTH - 0.02)
        self.assertAlmostEqual(s, expected, delta=1e-9)
        self.assertAlmostEqual(s, 19999999.9804, delta=1e-6)

    def test_hatch_update_blends_code_and_carrier(self):
        """At alpha = 0.5 the step is the arithmetic blend of the code and
        the carried range, exercising the mixing weights of the recursion."""
        s = gcs.hatch_update(1.0, 2.0, 0.5, 0.5)
        self.assertAlmostEqual(s, 1.75, delta=1e-12)

    def test_hatch_update_rejects_alpha_outside_open_unit(self):
        """The recursion gain must lie strictly inside (0, 1): endpoints
        0.0 and 1.0 and out-of-range 1.5 and -0.1 all raise ValueError."""
        for alpha in (0.0, 1.0, 1.5, -0.1):
            with self.assertRaises(ValueError):
                gcs.hatch_update(1.0, 1.0, 0.0, alpha)

    def test_hatch_update_rejects_nonfinite_arguments(self):
        """NaN smoothed range, code, carrier delta range or alpha cannot
        propagate through the traverse."""
        with self.assertRaises(ValueError):
            gcs.hatch_update(float("nan"), 1.0, 0.0, 0.01)
        with self.assertRaises(ValueError):
            gcs.hatch_update(1.0, float("inf"), 0.0, 0.01)
        with self.assertRaises(ValueError):
            gcs.hatch_update(1.0, 1.0, float("nan"), 0.01)
        with self.assertRaises(ValueError):
            gcs.hatch_update(1.0, 1.0, 0.0, float("nan"))

    def test_run_smoother_shape_and_seed(self):
        """The smoothed series has one entry per epoch and the first epoch
        seeds with the raw code before the carrier delta ranges carry the
        range forward."""
        codes = [TRUTH + 0.02 * k for k in range(100)]
        phases = [TRUTH - 0.02 * k for k in range(100)]
        sm = gcs.run_hatch_smoother(codes, phases, 100.0, 1.0)
        self.assertEqual(len(sm), 100)
        self.assertEqual(sm[0], codes[0])

    def test_run_smoother_holds_constant_stream(self):
        """On a static range with a perfect carrier the traverse holds the
        range: every smoothed value stays at the raw code level."""
        codes = [TRUTH] * 500
        phases = [TRUTH] * 500
        sm = gcs.run_hatch_smoother(codes, phases, 100.0, 1.0)
        for value in sm:
            self.assertAlmostEqual(value, TRUTH, delta=1e-6)

    def test_run_smoother_noise_free_ramp_early_epochs(self):
        """On the noise-free ionospheric ramp (code climbs 0.02 m per epoch,
        carrier delta -0.02 m) the first five smoothed values match the
        spec worked example: the smoothed range sinks below the code as the
        ionosphere climbs."""
        codes = [TRUTH + 0.02 * k for k in range(5)]
        phases = [TRUTH - 0.02 * k for k in range(5)]
        sm = gcs.run_hatch_smoother(codes, phases, 100.0, 1.0)
        expected = [20000000.000000, 19999999.980400, 19999999.961196,
                    19999999.942384, 19999999.923960]
        for actual, want in zip(sm, expected):
            self.assertAlmostEqual(actual, want, delta=1e-6)

    def test_run_smoother_matches_recursion_replay(self):
        """The traverse is the closed loop of hatch_update steps: replaying
        the recursion manually reproduces run_hatch_smoother to float
        precision on a noisy deterministic stream."""
        rng = random.Random(11)
        codes = [TRUTH + rng.gauss(0.0, 0.3) for _ in range(200)]
        phases = [TRUTH + rng.gauss(0.0, 0.003) for _ in range(200)]
        sm = gcs.run_hatch_smoother(codes, phases, 100.0, 1.0)
        alpha = 0.01
        manual = [codes[0]]
        for k in range(1, len(codes)):
            manual.append(gcs.hatch_update(manual[-1], codes[k],
                                           phases[k] - phases[k - 1], alpha))
        for actual, want in zip(sm, manual):
            self.assertAlmostEqual(actual, want, delta=1e-12)

    def test_run_smoother_rejects_unequal_and_empty_lists(self):
        """The traverse needs a matched code-carrier stream: length
        mismatch and an empty epoch list raise ValueError."""
        with self.assertRaises(ValueError):
            gcs.run_hatch_smoother([TRUTH, TRUTH], [TRUTH], 100.0, 1.0)
        with self.assertRaises(ValueError):
            gcs.run_hatch_smoother([], [], 100.0, 1.0)

    def test_run_smoother_rejects_nonfinite_and_bad_tau(self):
        """Non-finite code or phase measurements and a time constant at or
        below the update interval are rejected by the traverse."""
        with self.assertRaises(ValueError):
            gcs.run_hatch_smoother([TRUTH, float("nan")], [TRUTH, TRUTH],
                                   100.0, 1.0)
        with self.assertRaises(ValueError):
            gcs.run_hatch_smoother([TRUTH, TRUTH], [TRUTH, float("inf")],
                                   100.0, 1.0)
        with self.assertRaises(ValueError):
            gcs.run_hatch_smoother([TRUTH, TRUTH], [TRUTH, TRUTH],
                                   50.0, 50.0)


class TestNoiseReductionVerdict(unittest.TestCase):
    """Workflow step 3: the noise-reduction verdict closed forms."""

    def test_code_only_std_exact_default_and_scaling(self):
        """code_noise_std_smoothed(0.01, 0.3) is the exact closed form
        sigma_code*sqrt(alpha/(2-alpha)) = 0.021266 m and scales linearly
        with the raw code noise sigma."""
        exact = gcs.code_noise_std_smoothed(0.01, 0.3)
        self.assertAlmostEqual(exact, 0.021266, delta=1e-6)
        doubled = gcs.code_noise_std_smoothed(0.01, 0.6)
        self.assertAlmostEqual(doubled, 2.0 * exact, delta=1e-12)

    def test_code_only_std_rejects_bad_alpha(self):
        """The closed form needs alpha strictly inside (0, 1): 0.0, 1.0 and
        1.5 all raise ValueError."""
        for alpha in (0.0, 1.0, 1.5):
            with self.assertRaises(ValueError):
                gcs.code_noise_std_smoothed(alpha, 0.3)

    def test_code_only_std_rejects_bad_sigma(self):
        """A non-positive or non-finite raw code noise sigma cannot feed
        the noise-reduction verdict."""
        for sigma in (0.0, -0.3, float("nan")):
            with self.assertRaises(ValueError):
                gcs.code_noise_std_smoothed(0.01, sigma)

    def test_verdict_code_only_and_limit_identity(self):
        """The verdict pairs the exact code-only std 0.021266 m with the
        textbook limit sigma_code/sqrt(2*tau/T) = 0.021213 m, and the
        identity approx = exact*sqrt((2-alpha)/2) holds to 1e-12."""
        verdict = gcs.noise_reduction_verdict(100.0, 1.0, 0.3, 0.003)
        self.assertAlmostEqual(verdict["alpha"], 0.01, delta=1e-15)
        self.assertAlmostEqual(verdict["code_only_std"], 0.021266,
                               delta=1e-6)
        self.assertAlmostEqual(verdict["approx_std"], 0.021213, delta=1e-6)
        approx_from_exact = verdict["code_only_std"] * math.sqrt(
            (2.0 - verdict["alpha"]) / 2.0)
        self.assertAlmostEqual(verdict["approx_std"], approx_from_exact,
                               delta=1e-12)

    def test_verdict_carrier_total_and_improvement(self):
        """The verdict closes with the carrier delta-range term 0.021054 m,
        the total smoothed std 0.029925 m whose variance is the exact sum
        of the code and carrier term variances, and the improvement factor
        sigma_code/total_std = 10.025 over the raw code."""
        verdict = gcs.noise_reduction_verdict(100.0, 1.0, 0.3, 0.003)
        self.assertAlmostEqual(verdict["carrier_term_std"], 0.021054,
                               delta=1e-6)
        self.assertAlmostEqual(verdict["total_std"], 0.029925, delta=1e-6)
        var_sum = (verdict["code_only_std"] ** 2
                   + verdict["carrier_term_std"] ** 2)
        self.assertAlmostEqual(verdict["total_std"] ** 2, var_sum,
                               delta=1e-15)
        self.assertAlmostEqual(verdict["improvement_factor"], 10.025,
                               delta=1e-3)
        self.assertAlmostEqual(verdict["improvement_factor"],
                               0.3 / verdict["total_std"], delta=1e-12)

    def test_verdict_relative_gap_expansion(self):
        """The relative gap (exact - approx)/exact = 0.002503 matches the
        small-alpha expansion alpha/4 + alpha^2/32 + alpha^3/128 to 1e-8."""
        verdict = gcs.noise_reduction_verdict(100.0, 1.0, 0.3, 0.003)
        gap = ((verdict["code_only_std"] - verdict["approx_std"])
               / verdict["code_only_std"])
        alpha = verdict["alpha"]
        expansion = (alpha / 4.0 + alpha ** 2 / 32.0 + alpha ** 3 / 128.0)
        self.assertAlmostEqual(gap, 0.002503, delta=1e-6)
        self.assertAlmostEqual(gap, expansion, delta=1e-8)

    def test_verdict_small_alpha_tightens_limit(self):
        """At a much longer time constant the textbook limit tightens onto
        the exact closed form: the relative gap follows alpha/4 toward
        zero."""
        verdict = gcs.noise_reduction_verdict(10000.0, 1.0, 0.3, 0.003)
        gap = ((verdict["code_only_std"] - verdict["approx_std"])
               / verdict["code_only_std"])
        self.assertAlmostEqual(gap, 2.5e-5, delta=1e-6)
        self.assertAlmostEqual(gap, verdict["alpha"] / 4.0, delta=1e-6)

    def test_verdict_rejects_invalid_inputs(self):
        """Non-positive code or carrier sigmas and an invalid time constant
        are rejected when the verdict is formed."""
        for sigma in (0.0, -0.3):
            with self.assertRaises(ValueError):
                gcs.noise_reduction_verdict(100.0, 1.0, sigma, 0.003)
        with self.assertRaises(ValueError):
            gcs.noise_reduction_verdict(100.0, 1.0, 0.3, 0.0)
        with self.assertRaises(ValueError):
            gcs.noise_reduction_verdict(1.0, 1.0, 0.3, 0.003)


class TestDivergenceMonitor(unittest.TestCase):
    """Workflow step 4: the code-carrier divergence monitor."""

    def test_iono_bias_formula(self):
        """smoothed_iono_bias(0.04, 100, 1) = -3.96 m: the steady-state
        smoothed-minus-code bias under divergence rate dD/dt = 0.04 m/s is
        -rate*(tau - T), the classic code-carrier divergence error."""
        bias = gcs.smoothed_iono_bias(0.04, 100.0, 1.0)
        self.assertAlmostEqual(bias, -3.96, delta=1e-9)
        self.assertAlmostEqual(bias, -0.04 * (100.0 - 1.0), delta=1e-9)
        longer = gcs.smoothed_iono_bias(0.04, 199.0, 1.0)
        self.assertAlmostEqual(longer, -0.04 * 198.0, delta=1e-9)

    def test_iono_bias_rejects_bad_rate_and_tau(self):
        """A non-finite divergence rate or an invalid time constant pair
        cannot predict the smoothed-minus-code bias."""
        for rate in (float("nan"), float("inf")):
            with self.assertRaises(ValueError):
                gcs.smoothed_iono_bias(rate, 100.0, 1.0)
        with self.assertRaises(ValueError):
            gcs.smoothed_iono_bias(0.04, 0.0, 1.0)

    def test_iono_rate_noise_free_ramp(self):
        """On noise-free diffs D_k = 0.04*k the trailing-window slope fit
        recovers the divergence rate 0.04 m/s exactly, for both the 60
        epoch default window and the full 4000 epoch record."""
        diffs = [0.04 * k for k in range(4000)]
        self.assertAlmostEqual(gcs.iono_divergence_rate(diffs, 100.0, 1.0,
                                                        60), 0.04, delta=1e-9)
        self.assertAlmostEqual(gcs.iono_divergence_rate(diffs, 100.0, 1.0,
                                                        4000), 0.04,
                               delta=1e-9)

    def test_iono_rate_rejects_bad_window(self):
        """The slope fit window must be an int of at least 2 and fit inside
        the epoch record: 1, 0, 4001 on 4000 diffs, a float window and a
        boolean all raise ValueError."""
        diffs = [0.04 * k for k in range(4000)]
        for window in (1, 0, 4001, 2.0, True):
            with self.assertRaises(ValueError):
                gcs.iono_divergence_rate(diffs, 100.0, 1.0, window)

    def test_iono_rate_rejects_bad_diffs_and_tau(self):
        """Non-finite code-carrier differences and an invalid time constant
        are rejected by the divergence rate fit."""
        with self.assertRaises(ValueError):
            gcs.iono_divergence_rate([0.0, float("nan")], 100.0, 1.0, 60)
        with self.assertRaises(ValueError):
            gcs.iono_divergence_rate([0.0, 0.04], 0.0, 1.0, 60)

    def test_divergence_quiet_case_no_alarm(self):
        """On noisy diffs (Random(123), code noise 0.3 m) with a quiet
        ionosphere at v = 0.001 m/s the monitor estimates a near-zero rate
        (-0.0001 m/s), predicts a +0.0075 m smoothed bias and stays far
        below the 1.0 m alarm threshold: no alarm."""
        rng = random.Random(123)
        quiet_diffs = _noisy_diffs(0.001, 4000, rng)
        quiet = gcs.divergence_check(quiet_diffs, 100.0, 1.0, 60, 1.0)
        self.assertAlmostEqual(quiet["rate"], -0.0001, delta=0.001)
        self.assertAlmostEqual(quiet["predicted_bias"], 0.0075, delta=0.005)
        self.assertEqual(quiet["threshold"], 1.0)
        self.assertFalse(quiet["alarm"])

    def test_divergence_ramp_case_alarms(self):
        """On the same noisy diffs with a real ramp at v = 0.02 m/s (rate
        2*v = 0.04 m/s) the fitted rate is 0.0427 m/s, the predicted
        smoothed-minus-code bias -4.2256 m exceeds the 1.0 m threshold and
        the monitor alarms, gating the range before positioning."""
        rng = random.Random(123)
        _noisy_diffs(0.001, 4000, rng)      # consume the quiet draws
        ramp_diffs = _noisy_diffs(0.02, 4000, rng)
        ramp = gcs.divergence_check(ramp_diffs, 100.0, 1.0, 60, 1.0)
        self.assertAlmostEqual(ramp["rate"], 0.04, delta=0.005)
        self.assertAlmostEqual(ramp["predicted_bias"], -4.2256, delta=0.05)
        self.assertTrue(ramp["alarm"])

    def test_divergence_rejects_bad_threshold(self):
        """A non-positive or non-finite alarm threshold is rejected."""
        for threshold in (0.0, -1.0, float("nan")):
            with self.assertRaises(ValueError):
                gcs.divergence_check([0.0, 0.04], 100.0, 1.0, 60, threshold)


class TestEmpiricalConfirmation(unittest.TestCase):
    """Workflow steps 2-4 verified against deterministic simulations."""

    def test_empirical_code_only_matches_closed_form(self):
        """Static-noise replay (Random(42), code-only, 40000 epochs, first
        2000 skipped past the variance relaxation): the settled empirical
        std of the smoothed range is 0.021043 m, within 0.002 m and 5% of
        the exact code-only closed form from the noise-reduction verdict."""
        rng = random.Random(42)
        codes = [TRUTH + rng.gauss(0.0, 0.3) for _ in range(N_EPOCHS)]
        phases = [TRUTH] * N_EPOCHS
        sm = gcs.run_hatch_smoother(codes, phases, 100.0, 1.0)
        errors = [sm[k] - TRUTH for k in range(SKIP, N_EPOCHS)]
        emp = math.sqrt(sum(e * e for e in errors) / len(errors))
        closed = gcs.code_noise_std_smoothed(0.01, 0.3)
        self.assertAlmostEqual(emp, 0.021043, delta=1e-6)
        self.assertAlmostEqual(emp, closed, delta=0.002)
        self.assertTrue(math.isclose(emp, closed, rel_tol=0.05))

    def test_empirical_code_carrier_within_autocorr_budget(self):
        """Code plus carrier delta noise (Random(7), 40000 epochs): the
        settled empirical std is 0.027221 m, within 15% of the total
        smoothed std because the autocorrelated output only holds about
        N/(2*tau/T) effective samples."""
        rng = random.Random(7)
        codes = [TRUTH + rng.gauss(0.0, 0.3) for _ in range(N_EPOCHS)]
        phases = [TRUTH]
        for _ in range(N_EPOCHS - 1):
            phases.append(phases[-1] + rng.gauss(0.0, 0.003))
        sm = gcs.run_hatch_smoother(codes, phases, 100.0, 1.0)
        errors = [sm[k] - TRUTH for k in range(SKIP, N_EPOCHS)]
        emp = math.sqrt(sum(e * e for e in errors) / len(errors))
        total = gcs.noise_reduction_verdict(100.0, 1.0, 0.3, 0.003)["total_std"]
        self.assertAlmostEqual(emp, 0.027221, delta=1e-6)
        self.assertTrue(math.isclose(emp, total, rel_tol=0.15))

    def test_empirical_iono_ramp_bias_matches_closed_form(self):
        """Noise-free ionospheric ramp at v = 0.02 m/s over 4000 epochs: the
        empirical mean smoothed-minus-code error over the last 2000 epochs
        is -3.9600 m, matching smoothed_iono_bias(2*v) within 0.1% and
        confirming the divergence monitor's bias prediction."""
        codes = [TRUTH + 0.02 * k for k in range(4000)]
        phases = [TRUTH - 0.02 * k for k in range(4000)]
        sm = gcs.run_hatch_smoother(codes, phases, 100.0, 1.0)
        tail = [sm[k] - codes[k] for k in range(2000, 4000)]
        emp_bias = sum(tail) / len(tail)
        closed = gcs.smoothed_iono_bias(0.04, 100.0, 1.0)
        self.assertAlmostEqual(emp_bias, -3.9600, delta=1e-3)
        self.assertTrue(math.isclose(emp_bias, closed, rel_tol=1e-3))

    def test_deterministic_replay_identical(self):
        """The module is deterministic: replaying the traverse and the
        divergence monitor on identical streams reproduces bit-identical
        results, so the gate verdict is reproducible offline."""
        rng = random.Random(42)
        codes = [TRUTH + rng.gauss(0.0, 0.3) for _ in range(2000)]
        phases = [TRUTH] * 2000
        first = gcs.run_hatch_smoother(codes, phases, 100.0, 1.0)
        second = gcs.run_hatch_smoother(codes, phases, 100.0, 1.0)
        self.assertEqual(first, second)
        diffs = [0.04 * k + 0.1 * math.sin(k) for k in range(200)]
        a = gcs.divergence_check(diffs, 100.0, 1.0, 60, 1.0)
        b = gcs.divergence_check(diffs, 100.0, 1.0, 60, 1.0)
        self.assertEqual(a, b)


if __name__ == "__main__":
    unittest.main()
