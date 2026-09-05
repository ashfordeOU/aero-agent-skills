"""Contract test for the power-analysis leaf (cross-cutting/numerics).

Exercises SKILL.md workflow steps 2 through 7 of the power-analysis leaf:
step 2 the quantile traverse (normal_quantile at 1 - alpha/2 for
z_(1-alpha/2), at the target power for z_(1-beta) = z_power, and the
normal_survival function used by the achieved-power evaluation), step 3
the two-sample sizing traverse for the minimum sample size per group from
the significance level, target power, effect size and standard deviation,
step 4 the one-sample sizing traverse, step 5 the proportion sizing
traverse from the null proportion and alternative proportion, step 6 the
achieved-power traverse at the rounded sample size, and step 7 the power
report bookkeeping dict with n_per_group, n_total and achieved_power.
Step 8 of the workflow, the verification run, is this file: it confirms
the spec worked-example anchors (63 per group for a half sigma shift at
eighty percent power, 44 for the 0.30 to 0.50 proportion comparison,
achieved power 0.8013 at 63 per group), the inverse-square effect-size
growth of the required sample size, the achieved-power-at-computed-n at
least the target power, the exact doubling relation between the two-sample
and one-sample requirements, the quantile and survival identities, and
every ValueError guard from the validation list. Run offline as a
deterministic stdlib unittest.
"""

import math
import unittest

import power_analysis_logic as pa

DELTA = 0.5      # effect size: half a sigma shift (delta = 0.5 * sigma)
SIGMA = 1.0      # population standard deviation
ALPHA = 0.05     # two-sided significance level
POWER = 0.8      # target power (type II error rate 0.2)
N_TWO = 63       # real module output, per group at the worked example


class PowerAnalysisContract(unittest.TestCase):
    """Worked-example anchors, identities, monotonicity and ValueError
    guards for the sample-size and power planning workflow."""

    # ---- workflow step 2: quantile traverse ----

    def test_step2_quantile_anchor_0975(self):
        """Workflow step 2, the quantile traverse: normal_quantile(0.975)
        returns 1.9599639845400538, within 1e-3 of the 1.9600 anchor for
        the 95 percent two-sided significance level."""
        z = pa.normal_quantile(0.975)
        self.assertAlmostEqual(z, 1.9599639845400538, places=9)
        self.assertLessEqual(abs(z - 1.9600), 1e-3)

    def test_step2_quantile_anchor_080(self):
        """Workflow step 2, the quantile traverse: normal_quantile(0.8)
        returns 0.8416212335729144, within 1e-3 of the 0.8416 anchor for
        z_(1-beta) at eighty percent power."""
        z = pa.normal_quantile(0.8)
        self.assertAlmostEqual(z, 0.8416212335729144, places=9)
        self.assertLessEqual(abs(z - 0.8416), 1e-3)

    def test_step2_quantile_tail_anchor(self):
        """Workflow step 2, the quantile traverse: normal_quantile(0.995)
        returns 2.575829303548903, the z_(1-alpha/2) value that sizes the
        alpha 0.01 plan, guarding the Acklam upper tail."""
        self.assertAlmostEqual(pa.normal_quantile(0.995), 2.575829303548903,
                               places=9)

    def test_step2_quantile_antisymmetry(self):
        """Workflow step 2 identity: normal_quantile(q) equals the negative
        of normal_quantile(1 - q) for q on both sides of the median."""
        for q in (0.001, 0.025, 0.1, 0.9, 0.975):
            self.assertAlmostEqual(pa.normal_quantile(q),
                                   -pa.normal_quantile(1.0 - q), places=12)

    def test_step2_quantile_median_zero(self):
        """Workflow step 2 boundary: normal_quantile(0.5) is exactly 0.0."""
        self.assertEqual(pa.normal_quantile(0.5), 0.0)

    def test_step2_quantile_rejects_out_of_unit(self):
        """Workflow step 2 guard: normal_quantile raises ValueError at and
        beyond the unit interval endpoints 0 and 1."""
        for bad in (0.0, 1.0, -0.5, 1.5):
            with self.assertRaises(ValueError):
                pa.normal_quantile(bad)

    def test_step2_survival_median_and_shift(self):
        """Workflow step 2, the survival side: normal_survival(0) is 0.5
        and normal_survival(-z) recovers the CDF value at z, so
        normal_survival(-1.9599639845400538) equals 0.975."""
        self.assertEqual(pa.normal_survival(0.0), 0.5)
        self.assertAlmostEqual(pa.normal_survival(-1.9599639845400538),
                               0.975, places=7)

    def test_step2_survival_reflection_identity(self):
        """Workflow step 2 identity: normal_survival(-z) plus
        normal_survival(z) sums to 1 for any z."""
        for z in (0.5, 1.5, -2.0, 2.575829303548903):
            self.assertAlmostEqual(
                pa.normal_survival(-z) + pa.normal_survival(z), 1.0, places=12)

    # ---- workflow step 3: two-sample sizing traverse ----

    def test_step3_two_sample_anchor(self):
        """Workflow step 3, the two-sample sizing traverse: a half sigma
        shift at eighty percent power and alpha 0.05 needs 63 per group,
        the real module output for the 62.79 continuous anchor, with 126
        total."""
        n = pa.sample_size_two_sample_pooled(DELTA, SIGMA, ALPHA, POWER)
        self.assertEqual(n, N_TWO)
        self.assertEqual(2 * n, 126)

    def test_step3_two_sample_sigma_ratio_equivariance(self):
        """Workflow step 3 scaling: only the effect-to-spread ratio
        matters, so delta 0.5 with sigma 1 and delta 1.0 with sigma 2 both
        give 63 per group."""
        self.assertEqual(pa.sample_size_two_sample_pooled(0.5, 1.0), 63)
        self.assertEqual(pa.sample_size_two_sample_pooled(1.0, 2.0), 63)

    def test_step3_effect_inverse_square_growth(self):
        """Workflow step 3 identity: the required sample size grows as the
        effect size shrinks with n ~ 1/delta^2, so halving the effect size
        from 0.5 sigma to 0.25 sigma quadruples 63 per group to 252."""
        n_half = pa.sample_size_two_sample_pooled(DELTA, SIGMA)
        n_quarter = pa.sample_size_two_sample_pooled(0.25 * SIGMA, SIGMA)
        self.assertEqual(n_quarter, 252)
        self.assertEqual(n_quarter, 4 * n_half)

    def test_step3_monotone_effect_size(self):
        """Workflow step 3 monotonicity: n at 0.25 sigma (252) exceeds n at
        0.5 sigma (63) for the same significance level and target power."""
        self.assertGreater(
            pa.sample_size_two_sample_pooled(0.25 * SIGMA, SIGMA),
            pa.sample_size_two_sample_pooled(DELTA, SIGMA))

    def test_step3_monotone_target_power(self):
        """Workflow step 3 monotonicity: n at ninety percent target power
        (85) exceeds n at eighty percent (63) for the same effect size."""
        n_p90 = pa.sample_size_two_sample_pooled(DELTA, SIGMA, ALPHA, 0.9)
        n_p80 = pa.sample_size_two_sample_pooled(DELTA, SIGMA, ALPHA, 0.8)
        self.assertEqual(n_p90, 85)
        self.assertGreater(n_p90, n_p80)

    def test_step3_alpha_tightening_raises_n(self):
        """Workflow step 3 trend: the required sample size rises as the
        significance level tightens, so alpha 0.01 (94 per group, quantile
        2.5758) exceeds alpha 0.05 (63 per group) at the same power."""
        n_a01 = pa.sample_size_two_sample_pooled(DELTA, SIGMA, 0.01, POWER)
        n_a05 = pa.sample_size_two_sample_pooled(DELTA, SIGMA, ALPHA, POWER)
        self.assertEqual(n_a01, 94)
        self.assertGreater(n_a01, n_a05)

    def test_step3_alpha_relaxed_lowers_n(self):
        """Workflow step 3 trend: alpha 0.10 relaxes the requirement to 50
        per group, below the 63 of alpha 0.05."""
        self.assertEqual(pa.sample_size_two_sample_pooled(
            DELTA, SIGMA, 0.10, POWER), 50)

    def test_step3_valueerror_delta_nonpositive(self):
        """Workflow step 3 guard: a zero or negative effect size delta
        raises ValueError."""
        for bad in (0.0, -0.25):
            with self.assertRaises(ValueError):
                pa.sample_size_two_sample_pooled(bad, SIGMA)

    def test_step3_valueerror_sigma_nonpositive(self):
        """Workflow step 3 guard: a zero or negative standard deviation
        sigma raises ValueError."""
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                pa.sample_size_two_sample_pooled(DELTA, bad)

    def test_step3_valueerror_alpha_endpoints(self):
        """Workflow step 3 guard: significance level alpha at 0 or 1
        raises ValueError."""
        for bad in (0.0, 1.0):
            with self.assertRaises(ValueError):
                pa.sample_size_two_sample_pooled(DELTA, SIGMA, alpha=bad)

    def test_step3_valueerror_power_endpoints(self):
        """Workflow step 3 guard: target power at 0 or 1 raises
        ValueError."""
        for bad in (0.0, 1.0):
            with self.assertRaises(ValueError):
                pa.sample_size_two_sample_pooled(DELTA, SIGMA, power=bad)

    def test_step3_valueerror_power_at_one_minus_alpha(self):
        """Workflow step 3 guard: target power at or above 1 - alpha (0.95
        with alpha 0.05) raises ValueError, while 0.9 stays valid."""
        with self.assertRaises(ValueError):
            pa.sample_size_two_sample_pooled(DELTA, SIGMA, power=0.95)
        self.assertEqual(
            pa.sample_size_two_sample_pooled(DELTA, SIGMA, power=0.9), 85)

    # ---- workflow step 4: one-sample sizing traverse ----

    def test_step4_one_sample_anchor(self):
        """Workflow step 4, the one-sample sizing traverse: the same half
        sigma shift at eighty percent power needs 32 observations, the
        real module output for the 31.3955 continuous anchor."""
        self.assertEqual(pa.sample_size_one_sample(DELTA, SIGMA), 32)

    def test_step4_one_sample_half_of_two_sample_exact(self):
        """Workflow step 4 identity: the one-sample requirement is exactly
        half the two-sample requirement, so at 0.25 sigma the 126
        one-sample observations equal half of the 252 two-sample total."""
        n_one = pa.sample_size_one_sample(0.25 * SIGMA, SIGMA)
        n_two = pa.sample_size_two_sample_pooled(0.25 * SIGMA, SIGMA)
        self.assertEqual(n_one, 126)
        self.assertEqual(2 * n_one, n_two)

    def test_step4_one_sample_close_to_half_two_sample(self):
        """Workflow step 4 identity, rounding aside: the two-sample 63 per
        group at 0.5 sigma sits within one of twice the one-sample 32."""
        n_one = pa.sample_size_one_sample(DELTA, SIGMA)
        n_two = pa.sample_size_two_sample_pooled(DELTA, SIGMA)
        self.assertLessEqual(abs(2 * n_one - n_two), 1)

    def test_step4_valueerror_guards(self):
        """Workflow step 4 guard: delta 0, sigma 0, alpha 1 and power 1
        each raise ValueError on the one-sample sizing traverse."""
        with self.assertRaises(ValueError):
            pa.sample_size_one_sample(0.0, SIGMA)
        with self.assertRaises(ValueError):
            pa.sample_size_one_sample(DELTA, 0.0)
        with self.assertRaises(ValueError):
            pa.sample_size_one_sample(DELTA, SIGMA, alpha=1.0)
        with self.assertRaises(ValueError):
            pa.sample_size_one_sample(DELTA, SIGMA, power=1.0)

    # ---- workflow step 5: proportion sizing traverse ----

    def test_step5_proportion_anchor(self):
        """Workflow step 5, the proportion sizing traverse: detecting a
        null proportion 0.30 against an alternative proportion 0.50 at
        eighty percent power needs 44, the real module output for the 43.5
        continuous anchor."""
        self.assertEqual(
            pa.sample_size_one_sample_proportion(0.30, 0.50), 44)

    def test_step5_proportion_smaller_gap_larger_n(self):
        """Workflow step 5 monotonicity: a 0.10 proportion gap (0.30 to
        0.40) needs 172, more than the 44 of the 0.20 gap."""
        n_wide = pa.sample_size_one_sample_proportion(0.30, 0.50)
        n_narrow = pa.sample_size_one_sample_proportion(0.30, 0.40)
        self.assertEqual(n_narrow, 172)
        self.assertGreater(n_narrow, n_wide)

    def test_step5_proportion_equal_rejected(self):
        """Workflow step 5 guard: an alternative proportion equal to the
        null proportion raises ValueError."""
        with self.assertRaises(ValueError):
            pa.sample_size_one_sample_proportion(0.30, 0.30)

    def test_step5_proportion_outside_unit_rejected(self):
        """Workflow step 5 guard: a null or alternative proportion at or
        outside the unit interval endpoints raises ValueError."""
        for bad in (0.0, 1.0):
            with self.assertRaises(ValueError):
                pa.sample_size_one_sample_proportion(bad, 0.50)
            with self.assertRaises(ValueError):
                pa.sample_size_one_sample_proportion(0.30, bad)

    # ---- workflow step 6: achieved-power traverse ----

    def test_step6_achieved_power_anchor(self):
        """Workflow step 6, the achieved-power traverse: 63 per group at a
        half sigma shift achieves 0.801301455473719, within 0.002 of the
        0.8013 anchor and at least the 0.80 target power."""
        p_achieved = pa.achieved_power_two_sample_pooled(N_TWO, DELTA, SIGMA)
        self.assertAlmostEqual(p_achieved, 0.801301455473719, places=9)
        self.assertLessEqual(abs(p_achieved - 0.8013), 0.002)
        self.assertGreaterEqual(p_achieved, POWER)

    def test_step6_achieved_power_survival_closed_form(self):
        """Workflow step 6 identity: the achieved power equals the
        normal_survival of the shifted critical value, 1 - Phi(z_(1-alpha/
        2) - delta * sqrt(n / (2 * sigma^2))), tying the quantile traverse
        and the achieved-power traverse."""
        expected = pa.normal_survival(
            pa.normal_quantile(1.0 - ALPHA / 2.0)
            - DELTA * math.sqrt(N_TWO / (2.0 * SIGMA * SIGMA)))
        self.assertAlmostEqual(
            pa.achieved_power_two_sample_pooled(N_TWO, DELTA, SIGMA),
            expected, places=12)

    def test_step6_achieved_power_grows_with_n(self):
        """Workflow step 6 monotonicity: the achieved power rises with the
        per-group sample size, from 0.8013 at 63 to 0.8854 at 80 and
        0.99987 at 252."""
        p63 = pa.achieved_power_two_sample_pooled(63, DELTA, SIGMA)
        p80 = pa.achieved_power_two_sample_pooled(80, DELTA, SIGMA)
        p252 = pa.achieved_power_two_sample_pooled(252, DELTA, SIGMA)
        self.assertAlmostEqual(p80, 0.8853789898000417, places=9)
        self.assertAlmostEqual(p252, 0.9998701613779752, places=9)
        self.assertGreater(p80, p63)
        self.assertGreater(p252, p80)

    def test_step6_achieved_power_smallest_group_ok(self):
        """Workflow step 6 boundary: n = 2 is the smallest valid per-group
        sample size and returns a finite achieved power below 0.1."""
        p2 = pa.achieved_power_two_sample_pooled(2, DELTA, SIGMA)
        self.assertGreater(p2, 0.0)
        self.assertLess(p2, 0.1)

    def test_step6_valueerror_n_below_two(self):
        """Workflow step 6 guard: a per-group sample size below 2 raises
        ValueError."""
        for bad in (1, 0, -3):
            with self.assertRaises(ValueError):
                pa.achieved_power_two_sample_pooled(bad, DELTA, SIGMA)

    def test_step6_valueerror_parameters(self):
        """Workflow step 6 guard: delta 0, sigma 0 and alpha at 1 raise
        ValueError on the achieved-power traverse."""
        with self.assertRaises(ValueError):
            pa.achieved_power_two_sample_pooled(N_TWO, 0.0, SIGMA)
        with self.assertRaises(ValueError):
            pa.achieved_power_two_sample_pooled(N_TWO, DELTA, 0.0)
        with self.assertRaises(ValueError):
            pa.achieved_power_two_sample_pooled(N_TWO, DELTA, SIGMA,
                                                alpha=1.0)

    # ---- workflow step 7: power report bookkeeping ----

    def test_step7_report_keys(self):
        """Workflow step 7, the power report bookkeeping: power_report
        returns exactly the documented keys n_per_group, n_total and
        achieved_power."""
        report = pa.power_report(DELTA, SIGMA)
        self.assertEqual(set(report.keys()),
                         {"n_per_group", "n_total", "achieved_power"})

    def test_step7_report_anchor(self):
        """Workflow step 7 bookkeeping anchor: the report for a half sigma
        shift at eighty percent power carries n_per_group 63, n_total 126
        and achieved_power 0.801301455473719, with n_total twice the
        per-group value."""
        report = pa.power_report(DELTA, SIGMA)
        self.assertEqual(report["n_per_group"], N_TWO)
        self.assertEqual(report["n_total"], 2 * N_TWO)
        self.assertAlmostEqual(report["achieved_power"],
                               0.801301455473719, places=9)
        self.assertEqual(report["n_total"], 2 * report["n_per_group"])

    def test_step7_report_deterministic(self):
        """Workflow step 7 bookkeeping: two identical power_report calls
        return identical dicts, the determinism check of the workflow."""
        self.assertEqual(pa.power_report(DELTA, SIGMA),
                         pa.power_report(DELTA, SIGMA))

    # ---- workflow step 8: verification run ----

    def test_step8_verification_full_chain_repeatable(self):
        """Workflow step 8, the verification run: sizing and achieved-power
        evaluation reproduce the 63 per group and 0.8013 achieved power
        anchors on a second pass, confirming the deterministic chain."""
        n = pa.sample_size_two_sample_pooled(DELTA, SIGMA, ALPHA, POWER)
        p = pa.achieved_power_two_sample_pooled(n, DELTA, SIGMA, ALPHA)
        self.assertEqual(n, N_TWO)
        self.assertAlmostEqual(p, 0.801301455473719, places=9)


if __name__ == "__main__":
    unittest.main()
