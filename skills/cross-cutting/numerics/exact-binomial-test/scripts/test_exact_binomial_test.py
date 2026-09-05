"""Contract test for the exact-binomial-test leaf (cross-cutting/numerics).

Exercises SKILL.md workflow steps 2 through 7 of the exact-binomial-test
leaf: step 2 the tail-mass traverse (binomial_probability for the single
outcome mass P(X = k) and binomial_cdf for the lower tail P(X <= k)), step
3 the exact-test traverse (binomial_exact_test returning the verdict dict
with p_lower_tail, p_upper_tail, p_value, direction and midp_applied under
the doubling convention for the two-sided p-value), step 4 the mid-p
traverse that relaxes the doubling by the mass of the observed count, step
5 the normal cross-check traverse (binomial_normal_approximation with the
continuity correction toward the null mean), step 6 the small-count
traverse (small_count_recommendation with min_expected and the verdict
that gates the exact tail), and step 7 the verdict bookkeeping that
compares the p_value against the significance level to record reject or
fail-to-reject. Step 8 of the workflow, the verification run, is this
file: it confirms the spec worked-example anchors (0.1110 lower tail and
0.2220 two-sided p for eight successes in forty trials against a null
proportion p zero of 0.30, 0.0355 for two in twenty, the -1.208 z
cross-check), the doubling and cap identities, the mid-p identities, the
large-sample convergence of the normal approximation, the distribution
identities (cdf at k = n is 1, the pmf sums to 1), and every ValueError
guard from the validation list. Run offline as a deterministic stdlib
unittest.
"""

import math
import unittest

import exact_binomial_test_logic as eb

CDF_40_8 = 0.11100917524979735     # real module output, P(X <= 8 | n 40, p0 0.3)
P_OBS_40_8 = 0.0557262880960546    # real module output, P(X = 8 | n 40, p0 0.3)
Z_40_8 = -1.20761472884912         # real module output, continuity-corrected z


class WorkedExampleContract(unittest.TestCase):
    """Workflow anchors from the spec worked example and verdict bookkeeping."""

    def test_step2_tail_mass_anchor_lower_tail_40_8(self):
        """Workflow step 2, the tail-mass traverse: binomial_cdf(8, 40, 0.3)
        returns the real output 0.11100917524979735, within 1e-3 of the
        0.1110 prep anchor for P(X <= 8) against the null proportion 0.30."""
        c = eb.binomial_cdf(8, 40, 0.3)
        self.assertAlmostEqual(c, CDF_40_8, places=12)
        self.assertLessEqual(abs(c - 0.1110), 1e-3)

    def test_step3_exact_test_anchor_two_sided_40_8(self):
        """Workflow step 3, the exact-test traverse: binomial_exact_test(8,
        40, 0.3) returns p_value 0.2220183504995947, within 2e-3 of the
        0.2220 anchor, with direction less and p_lower_tail the doubled
        mass, so step 7 verdict bookkeeping fails to reject at the 0.05
        significance level."""
        r = eb.binomial_exact_test(8, 40, 0.3)
        self.assertAlmostEqual(r["p_value"], 0.2220183504995947, places=12)
        self.assertLessEqual(abs(r["p_value"] - 0.2220), 2e-3)
        self.assertEqual(r["direction"], "less")
        self.assertGreater(r["p_value"], 0.05)
        self.assertFalse(r["midp_applied"])

    def test_step3_exact_test_anchor_less_20_2(self):
        """Workflow step 3, the exact-test traverse: binomial_cdf(2, 20,
        0.3) returns 0.03548313229846864, within 1e-3 of the 0.0355 anchor,
        and the less alternative p_value rejects at the 0.05 significance
        level in step 7 verdict bookkeeping."""
        c = eb.binomial_cdf(2, 20, 0.3)
        self.assertAlmostEqual(c, 0.03548313229846864, places=12)
        self.assertLessEqual(abs(c - 0.0355), 1e-3)
        r = eb.binomial_exact_test(2, 20, 0.3, alternative="less")
        self.assertAlmostEqual(r["p_value"], c, places=12)
        self.assertLess(r["p_value"], 0.05)

    def test_step5_normal_cross_check_anchor_40_8(self):
        """Workflow step 5, the normal cross-check traverse:
        binomial_normal_approximation(8, 40, 0.3) returns z
        -1.20761472884912, within 0.01 of the -1.208 anchor, and p_value
        0.22719549110006437, within 0.005 of the 0.227 anchor."""
        r = eb.binomial_normal_approximation(8, 40, 0.3)
        self.assertAlmostEqual(r["z"], Z_40_8, places=12)
        self.assertLessEqual(abs(r["z"] - (-1.208)), 0.01)
        self.assertAlmostEqual(r["p_value"], 0.22719549110006437, places=12)
        self.assertLessEqual(abs(r["p_value"] - 0.227), 0.005)


class TwoSidedConventionContract(unittest.TestCase):
    """Doubling convention, cap at one, and direction semantics."""

    def test_two_sided_most_central_count_p_value_one(self):
        """Workflow step 3 doubling cap: at the most central count k = 5 of
        n = 10 with p0 = 0.5 both tail masses are 0.623046875, above one
        half, so the doubled two-sided p_value is exactly 1.0."""
        r = eb.binomial_exact_test(5, 10, 0.5)
        self.assertEqual(r["p_value"], 1.0)
        self.assertEqual(r["p_lower_tail"], 0.623046875)
        self.assertEqual(r["p_upper_tail"], 0.623046875)

    def test_two_sided_doubling_below_cap_visible(self):
        """Workflow step 3 doubling below the cap: with n = 10, p0 = 0.5,
        k = 3 the lower tail 0.171875 doubles to p_value 0.34375, the raw
        doubling visible before the cap at one applies."""
        r = eb.binomial_exact_test(3, 10, 0.5)
        self.assertEqual(r["p_value"], 2.0 * 0.171875)
        self.assertLess(r["p_value"], 1.0)

    def test_two_sided_greater_direction_doubles_upper_tail(self):
        """Workflow step 3 direction: with k = 16 above the null mean 12 of
        n = 40, p0 = 0.3 the observed direction is greater, the one-sided
        p_value is the upper tail 0.11514665058139029, and the doubled
        two-sided p_value is 0.23029330116278057."""
        r = eb.binomial_exact_test(16, 40, 0.3)
        self.assertEqual(r["direction"], "greater")
        self.assertAlmostEqual(r["p_upper_tail"], 0.11514665058139029, places=12)
        self.assertAlmostEqual(r["p_value"], 2.0 * r["p_upper_tail"], places=12)
        self.assertAlmostEqual(r["p_value"], 0.23029330116278057, places=12)

    def test_two_sided_equals_capped_doubled_smaller_tail(self):
        """Workflow step 3 identity: the two-sided p_value equals
        min(1, 2 * min(p_lower_tail, p_upper_tail)) for the worked example,
        the smaller tail being the observed-direction lower tail 0.1110."""
        r = eb.binomial_exact_test(8, 40, 0.3)
        self.assertAlmostEqual(
            r["p_value"], min(1.0, 2.0 * min(r["p_lower_tail"], r["p_upper_tail"])),
            places=12)
        self.assertLess(r["p_lower_tail"], r["p_upper_tail"])

    def test_one_sided_less_returns_lower_tail(self):
        """Workflow step 3 alternative less: binomial_exact_test(16, 40,
        0.3, alternative="less") returns the lower tail 0.9366871245215924
        and fails to reject at 0.05 even though the count sits above the
        null mean."""
        r = eb.binomial_exact_test(16, 40, 0.3, alternative="less")
        self.assertAlmostEqual(r["p_value"], r["p_lower_tail"], places=12)
        self.assertAlmostEqual(r["p_lower_tail"], 0.9366871245215924, places=12)
        self.assertGreater(r["p_value"], 0.05)

    def test_one_sided_greater_returns_upper_tail(self):
        """Workflow step 3 alternative greater: binomial_exact_test(8, 40,
        0.3, alternative="greater") returns the upper tail
        0.9447171128462573 and fails to reject at 0.05."""
        r = eb.binomial_exact_test(8, 40, 0.3, alternative="greater")
        self.assertAlmostEqual(r["p_value"], r["p_upper_tail"], places=12)
        self.assertAlmostEqual(r["p_upper_tail"], 0.9447171128462573, places=12)

    def test_lower_and_upper_tail_overlap_identity(self):
        """Distribution identity behind the doubling: p_lower_tail plus
        p_upper_tail equals 1 plus the probability of the observed count,
        because the observed count sits in both tails."""
        r = eb.binomial_exact_test(8, 40, 0.3)
        self.assertAlmostEqual(
            r["p_lower_tail"] + r["p_upper_tail"], 1.0 + P_OBS_40_8, places=12)


class MidPContract(unittest.TestCase):
    """Workflow step 4, the mid-p traverse that relaxes the doubling."""

    def test_step4_midp_two_sided_subtracts_observed_mass(self):
        """Workflow step 4, the mid-p traverse: with midp True the two-sided
        p_value becomes 0.1662920624035401, the conservative doubled value
        0.2220183504995947 minus the observed mass 0.0557262880960546."""
        plain = eb.binomial_exact_test(8, 40, 0.3)
        r = eb.binomial_exact_test(8, 40, 0.3, midp=True)
        self.assertTrue(r["midp_applied"])
        self.assertAlmostEqual(r["p_value"], 0.1662920624035401, places=12)
        self.assertAlmostEqual(r["p_value"], plain["p_value"] - P_OBS_40_8, places=12)
        self.assertLess(r["p_value"], plain["p_value"])

    def test_step4_midp_one_sided_drops_half_observed_mass(self):
        """Workflow step 4, the mid-p traverse on a one-sided alternative:
        the less p_value 0.08314603120177005 is the lower tail 0.1110 minus
        half of the observed mass 0.0557262880960546."""
        r = eb.binomial_exact_test(8, 40, 0.3, alternative="less", midp=True)
        self.assertTrue(r["midp_applied"])
        self.assertAlmostEqual(
            r["p_value"], CDF_40_8 - 0.5 * P_OBS_40_8, places=12)
        self.assertAlmostEqual(r["p_value"], 0.08314603120177005, places=12)

    def test_midp_applied_flag_default_false(self):
        """Workflow step 4 flag: midp_applied is False without the mid-p
        request and True with it, on identical inputs otherwise."""
        self.assertFalse(eb.binomial_exact_test(8, 40, 0.3)["midp_applied"])
        self.assertTrue(eb.binomial_exact_test(8, 40, 0.3, midp=True)["midp_applied"])

    def test_midp_most_central_count(self):
        """Workflow step 4 at the most central count: mid-p of
        binomial_exact_test(5, 10, 0.5) is 0.75390625, the capped 1.0 minus
        the observed mass 0.24609375."""
        r = eb.binomial_exact_test(5, 10, 0.5, midp=True)
        self.assertAlmostEqual(r["p_value"], 0.75390625, places=12)
        self.assertAlmostEqual(r["p_value"], 1.0 - 0.24609375, places=12)


class NormalApproximationContract(unittest.TestCase):
    """Workflow step 5, the normal cross-check traverse."""

    def test_step5_z_formula_continuity_correction_toward_mean(self):
        """Workflow step 5 continuity correction: for k = 8 below the null
        mean 12 of n = 40, p0 = 0.3 the count moves half a step toward the
        mean, z = (8 - 12 + 0.5) / sqrt(8.4) = -1.20761472884912 exactly."""
        r = eb.binomial_normal_approximation(8, 40, 0.3)
        expected = (8 - 12 + 0.5) / math.sqrt(8.4)
        self.assertAlmostEqual(r["z"], expected, places=12)
        self.assertLess(r["z"], 0.0)

    def test_step5_z_sign_flips_above_mean(self):
        """Workflow step 5 above the null mean: for k = 16 of n = 40, p0 =
        0.3 the correction subtracts half a step, z = (15.5 - 12) /
        sqrt(8.4) = +1.20761472884912, and the two-sided p_value is the
        same 0.22719549110006437 by symmetry."""
        r = eb.binomial_normal_approximation(16, 40, 0.3)
        expected = (16 - 12 - 0.5) / math.sqrt(8.4)
        self.assertAlmostEqual(r["z"], expected, places=12)
        self.assertAlmostEqual(r["z"], -Z_40_8, places=12)
        self.assertAlmostEqual(r["p_value"], 0.22719549110006437, places=12)

    def test_normal_p_value_two_sided_tail_identity(self):
        """Workflow step 5 tail identity: p_value equals twice the standard
        normal upper tail 1 - Phi(abs(z)), evaluated with math.erfc as the
        two-sided normal tail of the continuity-corrected z statistic."""
        r = eb.binomial_normal_approximation(8, 40, 0.3)
        upper_tail = 0.5 * math.erfc(abs(r["z"]) / math.sqrt(2.0))
        self.assertAlmostEqual(r["p_value"], 2.0 * upper_tail, places=12)

    def test_step5_approximation_converges_as_n_grows(self):
        """Workflow step 5 large-sample convergence: the gap between the
        exact two-sided p_value and the normal approximation at n = 400
        with k = 100 is 0.002304, below half of the 0.012713 gap at n = 40
        with k = 10, so the approximation approaches the exact tail as the
        trial count grows."""
        e_small = eb.binomial_exact_test(10, 40, 0.3)["p_value"]
        a_small = eb.binomial_normal_approximation(10, 40, 0.3)["p_value"]
        e_large = eb.binomial_exact_test(100, 400, 0.3)["p_value"]
        a_large = eb.binomial_normal_approximation(100, 400, 0.3)["p_value"]
        err_small = abs(e_small - a_small)
        err_large = abs(e_large - a_large)
        self.assertAlmostEqual(err_small, 0.012713, places=3)
        self.assertAlmostEqual(err_large, 0.002304, places=3)
        self.assertLess(err_large, 0.5 * err_small)


class SmallCountContract(unittest.TestCase):
    """Workflow step 6, the small-count traverse gating exact versus
    approximate tails."""

    def test_step6_small_count_adequate_20_30(self):
        """Workflow step 6, the small-count traverse:
        small_count_recommendation(20, 0.3) returns min_expected 6.0, at or
        above 5, with the verdict normal-approximation-adequate."""
        r = eb.small_count_recommendation(20, 0.3)
        self.assertEqual(r["min_expected"], 6.0)
        self.assertEqual(r["verdict"], "normal-approximation-adequate")

    def test_step6_small_count_exact_recommended_10_05(self):
        """Workflow step 6, the small-count traverse:
        small_count_recommendation(10, 0.05) returns min_expected 0.5,
        below 5, with the verdict exact-test-recommended that sends small
        attribute-data samples to the exact binomial tail."""
        r = eb.small_count_recommendation(10, 0.05)
        self.assertEqual(r["min_expected"], 0.5)
        self.assertEqual(r["verdict"], "exact-test-recommended")

    def test_small_count_boundary_five_is_adequate(self):
        """Workflow step 6 boundary: min_expected of exactly 5.0 stays on
        the adequate side of the rule, since only a minimum below 5 raises
        the exact-test-recommended verdict."""
        r = eb.small_count_recommendation(10, 0.5)
        self.assertEqual(r["min_expected"], 5.0)
        self.assertEqual(r["verdict"], "normal-approximation-adequate")


class DistributionIdentityContract(unittest.TestCase):
    """Closed-form identities of the binomial tail and edge counts."""

    def test_cdf_at_k_equals_n_is_exactly_one(self):
        """Tail-mass identity: binomial_cdf at k = n returns exactly 1.0 for
        every trial count and null proportion, the whole distribution mass
        under the lower tail."""
        self.assertEqual(eb.binomial_cdf(40, 40, 0.3), 1.0)
        self.assertEqual(eb.binomial_cdf(10, 10, 0.5), 1.0)
        self.assertEqual(eb.binomial_cdf(5, 5, 0.1), 1.0)

    def test_pmf_sums_to_one_over_k(self):
        """Tail-mass identity: the binomial_probability masses sum to 1.0
        over k = 0..n for n = 40, p = 0.3, within floating point
        tolerance."""
        total = sum(eb.binomial_probability(j, 40, 0.3) for j in range(41))
        self.assertAlmostEqual(total, 1.0, places=9)

    def test_edge_k_zero(self):
        """Edge count k = 0 with n = 10, p0 = 0.3: the lower tail is
        0.7**10 = 0.02824752489999998, the upper tail is exactly 1.0, the
        direction is less and the doubled two-sided p_value is
        0.05649504979999996."""
        r = eb.binomial_exact_test(0, 10, 0.3)
        self.assertAlmostEqual(r["p_lower_tail"], 0.7 ** 10, places=12)
        self.assertEqual(r["p_upper_tail"], 1.0)
        self.assertEqual(r["direction"], "less")
        self.assertAlmostEqual(r["p_value"], 2.0 * 0.7 ** 10, places=12)

    def test_edge_k_equals_n(self):
        """Edge count k = n with n = 10, p0 = 0.3: the lower tail is exactly
        1.0, the direction is greater and the two-sided p_value is
        1.180980000148324e-05, twice the 0.3**10 upper tail mass."""
        r = eb.binomial_exact_test(10, 10, 0.3)
        self.assertEqual(r["p_lower_tail"], 1.0)
        self.assertEqual(r["direction"], "greater")
        self.assertAlmostEqual(r["p_value"], 2.0 * 0.3 ** 10, places=12)

    def test_single_trial_counts(self):
        """Single-trial sanity: n = 1 with p0 = 0.3 gives lower tail 0.7 at
        k = 0 and lower tail 1.0 at k = 1, with the upper tails 1.0 and 0.3
        respectively."""
        r0 = eb.binomial_exact_test(0, 1, 0.3)
        r1 = eb.binomial_exact_test(1, 1, 0.3)
        self.assertAlmostEqual(r0["p_lower_tail"], 0.7, places=12)
        self.assertEqual(r0["p_upper_tail"], 1.0)
        self.assertEqual(r1["p_lower_tail"], 1.0)
        self.assertAlmostEqual(r1["p_upper_tail"], 0.3, places=12)

    def test_dict_keys_exact_and_determinism(self):
        """Determinism and the documented dict keys: the exact-test dict
        carries exactly p_lower_tail, p_upper_tail, p_value, direction and
        midp_applied, the normal dict exactly z and p_value, the small-count
        dict exactly min_expected and verdict, and repeated calls return
        identical dicts."""
        r1 = eb.binomial_exact_test(8, 40, 0.3)
        r2 = eb.binomial_exact_test(8, 40, 0.3)
        self.assertEqual(set(r1.keys()),
                         {"p_lower_tail", "p_upper_tail", "p_value",
                          "direction", "midp_applied"})
        self.assertEqual(r1, r2)
        self.assertEqual(set(eb.binomial_normal_approximation(8, 40, 0.3).keys()),
                         {"z", "p_value"})
        self.assertEqual(set(eb.small_count_recommendation(20, 0.3).keys()),
                         {"min_expected", "verdict"})


class ValueErrorContract(unittest.TestCase):
    """Every non-physical input guard from the validation list."""

    def test_valueerror_k_outside_count_range(self):
        """Guard: k 41 against n 40 sits above the range and k -1 below it,
        and both raise ValueError in every entry point."""
        with self.assertRaises(ValueError):
            eb.binomial_cdf(41, 40, 0.3)
        with self.assertRaises(ValueError):
            eb.binomial_exact_test(41, 40, 0.3)
        with self.assertRaises(ValueError):
            eb.binomial_probability(41, 40, 0.3)
        with self.assertRaises(ValueError):
            eb.binomial_exact_test(-1, 10, 0.5)

    def test_valueerror_k_fractional(self):
        """Guard: the fractional count k 2.5 is not an integer and raises
        ValueError in the exact-test and tail-mass traverses."""
        with self.assertRaises(ValueError):
            eb.binomial_cdf(2.5, 40, 0.3)
        with self.assertRaises(ValueError):
            eb.binomial_exact_test(2.5, 40, 0.3)

    def test_valueerror_n_zero_and_fractional(self):
        """Guard: n 0 and the fractional trial count n 2.5 raise ValueError
        in every entry point."""
        with self.assertRaises(ValueError):
            eb.binomial_exact_test(0, 0, 0.3)
        with self.assertRaises(ValueError):
            eb.binomial_cdf(2, 2.5, 0.3)
        with self.assertRaises(ValueError):
            eb.small_count_recommendation(0, 0.3)

    def test_valueerror_p0_at_zero_and_one(self):
        """Guard: a hypothesized null proportion p0 of exactly 0 or exactly
        1 sits outside the open unit interval and raises ValueError."""
        with self.assertRaises(ValueError):
            eb.binomial_exact_test(8, 40, 0.0)
        with self.assertRaises(ValueError):
            eb.binomial_exact_test(8, 40, 1.0)
        with self.assertRaises(ValueError):
            eb.binomial_cdf(8, 40, 1.0)
        with self.assertRaises(ValueError):
            eb.small_count_recommendation(20, 0.0)

    def test_valueerror_p_outside_unit_interval(self):
        """Guard: a probability below 0 or above 1 raises ValueError in the
        mass and cumulative tail functions."""
        with self.assertRaises(ValueError):
            eb.binomial_probability(8, 40, -0.1)
        with self.assertRaises(ValueError):
            eb.binomial_probability(8, 40, 1.5)
        with self.assertRaises(ValueError):
            eb.binomial_cdf(8, 40, 1.0000001)

    def test_valueerror_bad_alternative(self):
        """Guard: an alternative outside two-sided, less and greater raises
        ValueError in the exact-test traverse."""
        with self.assertRaises(ValueError):
            eb.binomial_exact_test(8, 40, 0.3, alternative="middle")

    def test_valueerror_non_numeric_inputs(self):
        """Guard: non-numeric counts and proportions raise ValueError rather
        than comparing or raising TypeError."""
        with self.assertRaises(ValueError):
            eb.binomial_exact_test("8", 40, 0.3)
        with self.assertRaises(ValueError):
            eb.binomial_exact_test(8, 40, None)
        with self.assertRaises(ValueError):
            eb.binomial_cdf(8, 40, True)


if __name__ == "__main__":
    unittest.main()
