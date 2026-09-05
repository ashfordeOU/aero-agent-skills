"""Contract test for the chi-square-goodness-of-fit leaf
(cross-cutting/numerics).

Exercises SKILL.md workflow steps 2 through 8 of the
chi-square-goodness-of-fit leaf: step 2 the expected-count traverse
(merging categories whose expected count falls below 1), step 3 the
statistic traverse, step 4 the degrees-of-freedom bookkeeping
(df = k - 1 - m), step 5 the p-value traverse through the module's own
regularized lower incomplete gamma (series branch and continued-fraction
branch), step 6 the verdict bookkeeping and the fit report dict, and
step 7 the uniform-model check. Step 8 of the workflow, the verification
run, is this file: it confirms the spec worked-example anchors (uniform
defect counts statistic 2.073 with p-value 0.913, skewed counts statistic
61.81 with a survival probability below 1e-9, the two-bin statistic 3.6
with p-value 0.0578), the observed-counts-versus-expected-counts
identities, the significance level verdicts, and every ValueError guard
from the validation list. Run offline as a deterministic stdlib unittest.
"""

import math
import unittest

import chi_square_goodness_of_fit_logic as csgof

UNIFORM_OBS = [50, 42, 38, 45, 43, 40, 42]   # defect counts over 7 days
UNIFORM_TOTAL = 300.0
UNIFORM_EXP = [UNIFORM_TOTAL / 7.0] * 7      # uniform model expected counts
SKEWED_OBS = [60, 30, 25, 20, 18, 15, 12]
SKEWED_TOTAL = 180.0
SKEWED_EXP = [SKEWED_TOTAL / 7.0] * 7


class ChiSquareGoodnessOfFitContract(unittest.TestCase):
    """Worked-example anchors, count identities, gamma closed forms,
    verdicts and ValueError guards for the goodness-of-fit workflow."""

    # ---- workflow step 3: statistic traverse ----

    def test_step3_uniform_statistic_anchor(self):
        """Workflow step 3, the statistic traverse: uniform model defect
        counts over seven days give a chi-square goodness-of-fit statistic
        of 2.0734 within 0.01 against the uniform expected counts."""
        stat = csgof.chi_square_gof_statistic(UNIFORM_OBS, UNIFORM_EXP)
        self.assertAlmostEqual(stat, 2.0734, delta=0.01)

    def test_step3_skewed_statistic_anchor(self):
        """Workflow step 3, the statistic traverse: the skewed observed
        counts give a statistic of 61.81 within 0.3 against the uniform
        expected counts."""
        stat = csgof.chi_square_gof_statistic(SKEWED_OBS, SKEWED_EXP)
        self.assertAlmostEqual(stat, 61.81, delta=0.3)

    def test_step3_two_bin_statistic_anchor(self):
        """Workflow step 3, the statistic traverse: the two-bin observed
        counts [8, 2] against the expected counts [5, 5] give a statistic
        of exactly 3.6."""
        stat = csgof.chi_square_gof_statistic([8, 2], [5, 5])
        self.assertAlmostEqual(stat, 3.6, delta=1e-9)

    def test_step3_perfect_fit_zero_statistic_unit_p(self):
        """Workflow step 3 identity, carried through step 5: observed
        counts equal to the expected counts give statistic 0 and a
        p-value of exactly 1.0 from the p-value traverse."""
        stat = csgof.chi_square_gof_statistic([4, 6, 5], [4, 6, 5])
        self.assertEqual(stat, 0.0)
        report = csgof.chi_square_goodness_of_fit([4, 6, 5], [4, 6, 5])
        self.assertEqual(report["p_value"], 1.0)

    def test_step3_uniform_statistic_hand_recomputation(self):
        """Workflow step 3 closed form: the statistic traverse equals a
        hand recomputation of the sum of squared gaps over the expected
        counts for the uniform model defect counts."""
        hand = 0.0
        for obs, exp in zip(UNIFORM_OBS, UNIFORM_EXP):
            hand += (obs - exp) ** 2 / exp
        stat = csgof.chi_square_gof_statistic(UNIFORM_OBS, UNIFORM_EXP)
        self.assertAlmostEqual(stat, hand, delta=1e-9)

    def test_step3_doubling_counts_doubles_statistic(self):
        """Workflow step 3 scaling identity: doubling all the observed
        counts and the expected counts doubles the statistic at a fixed
        relative deviation."""
        doubled_obs = [2 * v for v in UNIFORM_OBS]
        doubled_exp = [2 * v for v in UNIFORM_EXP]
        stat = csgof.chi_square_gof_statistic(UNIFORM_OBS, UNIFORM_EXP)
        doubled = csgof.chi_square_gof_statistic(doubled_obs, doubled_exp)
        self.assertAlmostEqual(doubled, 2.0 * stat, delta=1e-9)

    def test_step3_common_scaling_multiplies_statistic(self):
        """Workflow step 3 relative-fit scaling law: scaling the observed
        counts and the expected counts by one positive constant multiplies
        the statistic by that constant, so the per-category relative gaps
        survive unchanged."""
        scaled_obs = [3 * v for v in UNIFORM_OBS]
        scaled_exp = [3 * v for v in UNIFORM_EXP]
        stat = csgof.chi_square_gof_statistic(UNIFORM_OBS, UNIFORM_EXP)
        scaled = csgof.chi_square_gof_statistic(scaled_obs, scaled_exp)
        self.assertAlmostEqual(scaled, 3.0 * stat, delta=1e-9)

    # ---- workflow step 2: expected-count traverse ----

    def test_step2_merge_folds_deficient_into_next(self):
        """Workflow step 2, the expected-count traverse: a category whose
        expected count is below 1 folds into the next category, summing the
        observed counts and the expected counts."""
        obs, exp = csgof.merge_small_expected_categories(
            [1, 9, 6], [0.5, 10.0, 5.0])
        self.assertEqual(obs, [10, 6])
        self.assertAlmostEqual(exp[0], 10.5, delta=1e-12)
        self.assertAlmostEqual(exp[1], 5.0, delta=1e-12)

    def test_step2_merge_final_category_into_previous(self):
        """Workflow step 2, the expected-count traverse: the final
        category with an expected count below 1 folds into the previous
        category instead of the next one."""
        obs, exp = csgof.merge_small_expected_categories(
            [5, 5, 1], [4.0, 5.0, 0.4])
        self.assertEqual(obs, [5, 6])
        self.assertAlmostEqual(exp[0], 4.0, delta=1e-12)
        self.assertAlmostEqual(exp[1], 5.4, delta=1e-12)

    def test_step2_merge_reduces_df_in_fit_report(self):
        """Workflow step 2 through step 4: merging a small expected count
        into its neighbor drops the degrees-of-freedom bookkeeping from
        k - 1 = 2 to 1 in the fit report dict."""
        plain = csgof.chi_square_goodness_of_fit([1, 9, 6], [0.5, 10.0, 5.0])
        merged = csgof.chi_square_goodness_of_fit(
            [1, 9, 6], [0.5, 10.0, 5.0], merge_small_expected=True)
        self.assertEqual(plain["df"], 2)
        self.assertEqual(merged["df"], 1)
        self.assertAlmostEqual(merged["statistic"], 0.2238, delta=1e-3)

    # ---- workflow step 4: degrees-of-freedom bookkeeping ----

    def test_step4_df_equals_k_minus_one(self):
        """Workflow step 4, the degrees-of-freedom bookkeeping: the seven
        uniform-model categories give df = 7 - 1 - 0 = 6 in the fit report
        dict."""
        report = csgof.chi_square_goodness_of_fit(UNIFORM_OBS, UNIFORM_EXP)
        self.assertEqual(report["df"], 6)

    def test_step4_df_with_estimated_parameters(self):
        """Workflow step 4 bookkeeping with a parameter estimated from the
        data: five Poisson count categories with one estimated mean give
        df = 5 - 1 - 1 = 3."""
        report = csgof.chi_square_goodness_of_fit(
            [12, 9, 11, 8, 10], [10, 10, 10, 10, 10], estimated_parameters=1)
        self.assertEqual(report["df"], 3)

    def test_step4_df_below_one_valueerror(self):
        """Workflow step 4 guard: subtracting one estimated parameter from
        two categories leaves df = 0, and the degrees-of-freedom
        bookkeeping raises ValueError instead of reporting a p-value."""
        with self.assertRaises(ValueError):
            csgof.chi_square_goodness_of_fit(
                [40, 60], [50, 50], estimated_parameters=1)

    # ---- workflow step 5: p-value traverse ----

    def test_step5_uniform_p_value_anchor(self):
        """Workflow step 5, the p-value traverse: the uniform-model
        statistic 2.0734 at df 6 gives a survival probability of 0.913
        within 0.005."""
        stat = csgof.chi_square_gof_statistic(UNIFORM_OBS, UNIFORM_EXP)
        p = csgof.goodness_of_fit_p_value(stat, 6)
        self.assertAlmostEqual(p, 0.913, delta=0.005)

    def test_step5_skewed_p_value_below_1e9(self):
        """Workflow step 5, the p-value traverse: the skewed observed
        counts at df 6 give a survival probability below 1e-9, so the fit
        fails the uniform model."""
        stat = csgof.chi_square_gof_statistic(SKEWED_OBS, SKEWED_EXP)
        p = csgof.goodness_of_fit_p_value(stat, 6)
        self.assertLess(p, 1e-9)

    def test_step5_two_bin_p_value_anchor(self):
        """Workflow step 5, the p-value traverse: the two-bin statistic
        3.6 at df 1 gives a p-value of 0.0578 within 1e-3."""
        p = csgof.goodness_of_fit_p_value(3.6, 1)
        self.assertAlmostEqual(p, 0.0578, delta=1e-3)

    def test_step5_p_value_decreases_with_statistic(self):
        """Workflow step 5 trend: at a fixed df of 1 the survival
        probability decreases as the statistic grows from 3.6 to 7.2."""
        p_small = csgof.goodness_of_fit_p_value(3.6, 1)
        p_large = csgof.goodness_of_fit_p_value(7.2, 1)
        self.assertGreater(p_small, p_large)

    def test_step5_gamma_series_branch_erf_identity(self):
        """Workflow step 5, the p-value traverse series branch: the
        regularized lower incomplete gamma P(0.5, 0.5) equals
        erf(sqrt(0.5))."""
        gamma = csgof.regularized_lower_incomplete_gamma(0.5, 0.5)
        self.assertAlmostEqual(gamma, math.erf(math.sqrt(0.5)), delta=1e-8)

    def test_step5_gamma_continued_fraction_erf_identity(self):
        """Workflow step 5, the p-value traverse continued-fraction
        branch: the regularized lower incomplete gamma P(0.5, 3.0) equals
        erf(sqrt(3.0))."""
        gamma = csgof.regularized_lower_incomplete_gamma(0.5, 3.0)
        self.assertAlmostEqual(gamma, math.erf(math.sqrt(3.0)), delta=1e-8)

    def test_step5_gamma_lower_tail_closed_form(self):
        """Workflow step 5 gamma anchor: the regularized lower incomplete
        gamma P(1, 1) equals 1 - 1/e."""
        gamma = csgof.regularized_lower_incomplete_gamma(1.0, 1.0)
        self.assertAlmostEqual(gamma, 1.0 - 1.0 / math.e, delta=1e-10)

    def test_step5_two_bin_erfc_closed_form(self):
        """Workflow step 5 closed form: the df 1 survival probability at
        statistic 3.6 equals erfc(sqrt(1.8)), the exact upper tail of the
        half-normal law behind the chi-square distribution."""
        p = csgof.goodness_of_fit_p_value(3.6, 1)
        self.assertAlmostEqual(p, math.erfc(math.sqrt(1.8)), delta=1e-8)

    def test_step5_branch_boundary_continuity(self):
        """Workflow step 5 branch continuity: the p-value traverse crosses
        its x = a + 1 series-to-continued-fraction split near statistic
        3.0 at df 1 with no visible jump against erfc(sqrt(1.5))."""
        below = csgof.goodness_of_fit_p_value(2.999999, 1)
        above = csgof.goodness_of_fit_p_value(3.000001, 1)
        anchor = math.erfc(math.sqrt(1.5))
        self.assertLess(abs(below - anchor), 1e-6)
        self.assertLess(abs(above - anchor), 1e-6)

    # ---- workflow step 6: verdict bookkeeping ----

    def test_step6_uniform_verdict_fail_to_reject(self):
        """Workflow step 6, the verdict bookkeeping: at the 0.05
        significance level the uniform-model defect counts fail to reject
        the uniform expected counts."""
        report = csgof.chi_square_goodness_of_fit(UNIFORM_OBS, UNIFORM_EXP)
        self.assertEqual(report["verdict"], "fail-to-reject")

    def test_step6_skewed_verdict_reject(self):
        """Workflow step 6, the verdict bookkeeping: at the 0.05
        significance level the skewed observed counts reject the uniform
        model."""
        report = csgof.chi_square_goodness_of_fit(SKEWED_OBS, SKEWED_EXP)
        self.assertEqual(report["verdict"], "reject")

    def test_step6_two_bin_fail_to_reject_at_005(self):
        """Workflow step 6 verdict: the two-bin p-value 0.0578 sits above
        the 0.05 significance level, so the verdict is fail-to-reject."""
        report = csgof.chi_square_goodness_of_fit([8, 2], [5, 5], alpha=0.05)
        self.assertEqual(report["verdict"], "fail-to-reject")

    def test_step6_two_bin_reject_at_010_boundary(self):
        """Workflow step 6 verdict boundary: the same two-bin p-value
        0.0578 sits at or below a 0.10 significance level, so the verdict
        flips to reject, documenting the 0.05 to 0.10 boundary."""
        report = csgof.chi_square_goodness_of_fit([8, 2], [5, 5], alpha=0.10)
        self.assertEqual(report["verdict"], "reject")

    def test_step6_report_dict_keys_and_determinism(self):
        """Workflow step 6 fit report: chi_square_goodness_of_fit returns
        exactly the statistic, df, p_value and verdict keys, and identical
        calls give an identical report dict."""
        first = csgof.chi_square_goodness_of_fit(UNIFORM_OBS, UNIFORM_EXP)
        second = csgof.chi_square_goodness_of_fit(UNIFORM_OBS, UNIFORM_EXP)
        self.assertEqual(sorted(first.keys()),
                         ["df", "p_value", "statistic", "verdict"])
        self.assertEqual(first, second)

    def test_step6_alpha_out_of_range_valueerror(self):
        """Workflow step 6 guard: significance levels of 0, 1, -0.05 and
        1.5 all raise ValueError from the verdict bookkeeping."""
        for alpha in (0.0, 1.0, -0.05, 1.5):
            with self.assertRaises(ValueError):
                csgof.chi_square_goodness_of_fit([8, 2], [5, 5], alpha=alpha)

    # ---- workflow step 7 guards and validation list ----

    def test_step7_length_mismatch_valueerror(self):
        """Workflow step 7 guard: observed counts and expected counts of
        different lengths raise ValueError."""
        with self.assertRaises(ValueError):
            csgof.chi_square_gof_statistic([8, 2], [5, 5, 5])

    def test_step7_negative_observed_valueerror(self):
        """Workflow step 7 guard: a negative observed count raises
        ValueError."""
        with self.assertRaises(ValueError):
            csgof.chi_square_gof_statistic([8, -2], [5, 5])

    def test_step7_nonpositive_expected_valueerror(self):
        """Workflow step 7 guard: a zero or negative expected count raises
        ValueError."""
        with self.assertRaises(ValueError):
            csgof.chi_square_gof_statistic([8, 2], [5, 0])
        with self.assertRaises(ValueError):
            csgof.chi_square_gof_statistic([8, 2], [5, -1])

    def test_step7_single_category_valueerror(self):
        """Workflow step 7 guard: fewer than two categories raises
        ValueError."""
        with self.assertRaises(ValueError):
            csgof.chi_square_gof_statistic([10], [10])

    def test_step7_non_finite_counts_valueerror(self):
        """Workflow step 7 guard: infinite observed counts and non-finite
        expected counts raise ValueError."""
        with self.assertRaises(ValueError):
            csgof.chi_square_gof_statistic([8, float("inf")], [5, 5])
        with self.assertRaises(ValueError):
            csgof.chi_square_gof_statistic([8, 2], [5, float("nan")])

    def test_step7_p_value_invalid_inputs_valueerror(self):
        """Workflow step 7 guard: the p-value traverse raises ValueError
        for a negative statistic, a non-finite statistic or degrees of
        freedom below 1."""
        with self.assertRaises(ValueError):
            csgof.goodness_of_fit_p_value(-0.1, 1)
        with self.assertRaises(ValueError):
            csgof.goodness_of_fit_p_value(float("nan"), 1)
        with self.assertRaises(ValueError):
            csgof.goodness_of_fit_p_value(2.0, 0.5)
        with self.assertRaises(ValueError):
            csgof.goodness_of_fit_p_value(2.0, 0.0)

    def test_step7_gamma_invalid_shape_valueerror(self):
        """Workflow step 7 guard: the regularized lower incomplete gamma
        raises ValueError for a non-positive shape a or a negative
        argument x."""
        with self.assertRaises(ValueError):
            csgof.regularized_lower_incomplete_gamma(0.0, 1.0)
        with self.assertRaises(ValueError):
            csgof.regularized_lower_incomplete_gamma(1.0, -0.5)


if __name__ == "__main__":
    unittest.main()
