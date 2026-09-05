"""Contract test for fault_tree_uncertainty_analysis_logic.py (wave-40).

Deterministic, offline, stdlib unittest. Run from the repo root:

    python3 skills/systems-engineering-safety/arp4761a/fault-tree-uncertainty-analysis/scripts/test_fault_tree_uncertainty_analysis.py

The module docstring of this file exercises the SKILL.md workflow:
step 1 gathers the fault-tree top probability and the per-event lognormal
error factors, step 2 converts each error factor to a lognormal sigma
with error_factor_to_sigma, step 3 combines the per-event sigmas into
the lognormal sigma of the tree probability with combined_log_sigma
using the Fussell-Vesely fractions as weights, step 4 forms the two
sided 90 percent lognormal-confidence-band with confidence_band, step 5
computes the exceedance probability against a target probability with
exceedance_probability, and step 6 decomposes the variance of the
lognormal spread into per-event uncertainty-variance-shares with
variance_decomposition. Worked example (spec): q_top = 2.5e-6 with FV
weights [0.62, 0.31, 0.07] and error factors [3, 5, 10]. Assert targets
are the real module outputs inside the spec magnitude bounds, plus the
closed-form identities and ValueError rejection of non-physical inputs.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import fault_tree_uncertainty_analysis_logic as ftua

Q_TOP = 2.5e-6
FV_WEIGHTS = [0.62, 0.31, 0.07]
ERROR_FACTORS = [3.0, 5.0, 10.0]
SIGMAS = [0.667849, 0.978382, 1.399748]
SIGMA_LNQ = 0.522534


class ErrorFactorToSigmaTests(unittest.TestCase):
    def test_error_factor_three_anchor(self):
        """Workflow step 2 anchor: EF 3 maps to sigma 0.667849."""
        self.assertAlmostEqual(ftua.error_factor_to_sigma(3.0), 0.667849, delta=1e-6)

    def test_error_factor_five_anchor(self):
        """Workflow step 2 anchor: EF 5 maps to sigma 0.978382."""
        self.assertAlmostEqual(ftua.error_factor_to_sigma(5.0), 0.978382, delta=1e-6)

    def test_error_factor_ten_anchor(self):
        """Workflow step 2 anchor: EF 10 maps to sigma ln(10)/1.645 = 1.399748."""
        self.assertAlmostEqual(ftua.error_factor_to_sigma(10.0), 1.399748, delta=1e-6)
        self.assertAlmostEqual(
            ftua.error_factor_to_sigma(10.0), math.log(10.0) / ftua.NORMAL_QUANTILE_90
        )

    def test_error_factor_one_gives_zero_sigma(self):
        """Workflow step 2 identity: EF 1.0 gives sigma 0.0 exactly."""
        self.assertEqual(ftua.error_factor_to_sigma(1.0), 0.0)

    def test_error_factor_below_one_raises(self):
        """Workflow step 2 rejection: an error factor below 1 would reverse the band."""
        with self.assertRaises(ValueError):
            ftua.error_factor_to_sigma(0.999)
        with self.assertRaises(ValueError):
            ftua.error_factor_to_sigma(0.0)


class CombinedLogSigmaTests(unittest.TestCase):
    def test_worked_example_combined_log_sigma(self):
        """Workflow step 3 anchor: FV-weighted combination gives sigma_lnq 0.522534."""
        sigmas = [ftua.error_factor_to_sigma(ef) for ef in ERROR_FACTORS]
        self.assertAlmostEqual(
            ftua.combined_log_sigma(FV_WEIGHTS, sigmas), SIGMA_LNQ, delta=1e-6
        )

    def test_single_event_identity(self):
        """Workflow step 3 identity: one event with FV weight 1.0 keeps its sigma."""
        self.assertAlmostEqual(
            ftua.combined_log_sigma([1.0], [0.667849]), 0.667849, delta=1e-9
        )

    def test_zero_sigmas_combine_to_zero(self):
        """Workflow step 3 boundary: all-zero sigmas or weights give sigma_lnq 0."""
        self.assertEqual(ftua.combined_log_sigma([0.5, 0.5], [0.0, 0.0]), 0.0)
        self.assertEqual(ftua.combined_log_sigma([0.0, 0.0], [0.5, 0.5]), 0.0)

    def test_weights_used_as_is_never_renormalized(self):
        """Workflow step 3 convention: a partial or oversized weight set is kept as-is."""
        self.assertAlmostEqual(ftua.combined_log_sigma([2.0, 0.0], [0.5, 9.0]), 1.0, delta=1e-12)

    def test_length_mismatch_raises(self):
        """Workflow step 3 rejection: unequal weight and sigma lists raise ValueError."""
        with self.assertRaises(ValueError):
            ftua.combined_log_sigma([0.5, 0.5], [0.5])

    def test_negative_weight_raises(self):
        """Workflow step 3 rejection: a negative Fussell-Vesely fraction raises ValueError."""
        with self.assertRaises(ValueError):
            ftua.combined_log_sigma([0.5, -0.1], [0.5, 0.5])

    def test_negative_sigma_raises(self):
        """Workflow step 3 rejection: a negative per-event sigma raises ValueError."""
        with self.assertRaises(ValueError):
            ftua.combined_log_sigma([0.5, 0.5], [0.5, -0.1])


class ConfidenceBandTests(unittest.TestCase):
    def test_worked_example_band_bounds(self):
        """Workflow step 4 anchor: 90 percent band bounds 1.05836e-6 and 5.90535e-6."""
        band = ftua.confidence_band(Q_TOP, SIGMA_LNQ)
        self.assertAlmostEqual(band["lower"], 1.05836e-6, delta=1e-10)
        self.assertAlmostEqual(band["upper"], 5.90535e-6, delta=1e-10)

    def test_band_dict_keys_exactly_lower_upper(self):
        """Workflow step 4 output shape: dict keys are exactly lower and upper."""
        self.assertEqual(
            sorted(ftua.confidence_band(Q_TOP, SIGMA_LNQ).keys()), ["lower", "upper"]
        )

    def test_band_geometric_center_identity(self):
        """Workflow step 4 identity: lower * upper = q_top^2 keeps the geometric center."""
        band = ftua.confidence_band(Q_TOP, SIGMA_LNQ)
        self.assertAlmostEqual(
            band["lower"] * band["upper"], Q_TOP * Q_TOP, delta=1e-24
        )

    def test_q_top_strictly_inside_band(self):
        """Workflow step 4 property: q_top sits strictly inside the band for sigma > 0."""
        band = ftua.confidence_band(Q_TOP, SIGMA_LNQ)
        self.assertLess(band["lower"], Q_TOP)
        self.assertLess(Q_TOP, band["upper"])

    def test_zero_sigma_band_collapses(self):
        """Workflow step 4 boundary: at sigma_lnq 0 the band collapses to [q_top, q_top]."""
        band = ftua.confidence_band(Q_TOP, 0.0)
        self.assertEqual(band["lower"], Q_TOP)
        self.assertEqual(band["upper"], Q_TOP)

    def test_band_input_rejections(self):
        """Workflow step 4 rejection: q_top 0, q_top 1.5 and sigma -0.1 raise ValueError."""
        with self.assertRaises(ValueError):
            ftua.confidence_band(0.0, SIGMA_LNQ)
        with self.assertRaises(ValueError):
            ftua.confidence_band(1.5, SIGMA_LNQ)
        with self.assertRaises(ValueError):
            ftua.confidence_band(Q_TOP, -0.1)


class ExceedanceProbabilityTests(unittest.TestCase):
    def test_worked_example_target_below_estimate(self):
        """Workflow step 5 anchor: exceedance vs 1e-7 is 0.99999999964, above the 50 percent line."""
        self.assertAlmostEqual(
            ftua.exceedance_probability(Q_TOP, SIGMA_LNQ, 1e-7),
            0.99999999964,
            delta=1e-10,
        )

    def test_worked_example_target_above_estimate(self):
        """Workflow step 5 anchor: exceedance vs 1e-5 is 0.00398872, below the 50 percent line."""
        self.assertAlmostEqual(
            ftua.exceedance_probability(Q_TOP, SIGMA_LNQ, 1e-5),
            0.00398872,
            delta=1e-8,
        )

    def test_median_identity_at_target_equal_q_top(self):
        """Workflow step 5 identity: exceedance at target == q_top is exactly 0.5, the lognormal median."""
        self.assertEqual(ftua.exceedance_probability(Q_TOP, SIGMA_LNQ, Q_TOP), 0.5)

    def test_target_ordering_straddles_half(self):
        """Workflow step 5 property: targets below q_top exceed 0.5, above q_top below 0.5."""
        low = ftua.exceedance_probability(Q_TOP, SIGMA_LNQ, 1e-7)
        high = ftua.exceedance_probability(Q_TOP, SIGMA_LNQ, 1e-5)
        self.assertGreater(low, 0.5)
        self.assertLess(high, 0.5)

    def test_exceedance_monotone_in_target(self):
        """Workflow step 5 property: exceedance falls as the target rises."""
        earlier = ftua.exceedance_probability(Q_TOP, SIGMA_LNQ, 1e-6)
        later = ftua.exceedance_probability(Q_TOP, SIGMA_LNQ, 2e-6)
        self.assertGreater(earlier, later)

    def test_exceedance_zero_sigma_raises(self):
        """Workflow step 5 rejection: sigma_lnq 0 makes the exceedance undefined."""
        with self.assertRaises(ValueError):
            ftua.exceedance_probability(Q_TOP, 0.0, 1e-7)

    def test_exceedance_non_positive_target_raises(self):
        """Workflow step 5 rejection: a zero or negative target raises ValueError."""
        with self.assertRaises(ValueError):
            ftua.exceedance_probability(Q_TOP, SIGMA_LNQ, 0.0)
        with self.assertRaises(ValueError):
            ftua.exceedance_probability(Q_TOP, SIGMA_LNQ, -1.0)

    def test_exceedance_q_top_out_of_range_raises(self):
        """Workflow step 5 rejection: q_top outside (0, 1] raises ValueError."""
        with self.assertRaises(ValueError):
            ftua.exceedance_probability(0.0, SIGMA_LNQ, 1e-7)
        with self.assertRaises(ValueError):
            ftua.exceedance_probability(1.5, SIGMA_LNQ, 1e-7)


class VarianceDecompositionTests(unittest.TestCase):
    def test_worked_example_shares(self):
        """Workflow step 6 anchor: shares 0.627931, 0.336908, 0.035161 for EFs 3, 5, 10."""
        sigmas = [ftua.error_factor_to_sigma(ef) for ef in ERROR_FACTORS]
        shares = ftua.variance_decomposition(FV_WEIGHTS, sigmas)
        self.assertAlmostEqual(shares[0], 0.627931, delta=1e-6)
        self.assertAlmostEqual(shares[1], 0.336908, delta=1e-6)
        self.assertAlmostEqual(shares[2], 0.035161, delta=1e-6)

    def test_shares_sum_to_one(self):
        """Workflow step 6 property: the uncertainty-variance-shares sum to 1.0."""
        sigmas = [ftua.error_factor_to_sigma(ef) for ef in ERROR_FACTORS]
        shares = ftua.variance_decomposition(FV_WEIGHTS, sigmas)
        self.assertAlmostEqual(sum(shares), 1.0, delta=1e-12)

    def test_single_event_share_one(self):
        """Workflow step 6 identity: one contributing event takes the whole share, 1.0."""
        self.assertEqual(ftua.variance_decomposition([1.0], [0.667849]), [1.0])

    def test_equal_weights_equal_sigmas_equal_shares(self):
        """Workflow step 6 property: equal weights and sigmas split the spread evenly."""
        shares = ftua.variance_decomposition([0.5, 0.5], [0.5, 0.5])
        self.assertAlmostEqual(shares[0], 0.5, delta=1e-12)
        self.assertAlmostEqual(shares[1], 0.5, delta=1e-12)

    def test_zero_total_variance_returns_zeros(self):
        """Workflow step 6 convention: zero total variance (no spread) returns zero shares."""
        self.assertEqual(ftua.variance_decomposition([0.0, 0.0], [0.5, 0.5]), [0.0, 0.0])
        self.assertEqual(ftua.variance_decomposition([0.5, 0.5], [0.0, 0.0]), [0.0, 0.0])

    def test_shares_aligned_to_input_order(self):
        """Workflow step 6 property: shares keep input order when events are permuted."""
        sigmas = [ftua.error_factor_to_sigma(ef) for ef in ERROR_FACTORS]
        plain = ftua.variance_decomposition(FV_WEIGHTS, sigmas)
        swapped = ftua.variance_decomposition(
            [FV_WEIGHTS[1], FV_WEIGHTS[0], FV_WEIGHTS[2]],
            [sigmas[1], sigmas[0], sigmas[2]],
        )
        self.assertAlmostEqual(plain[0], swapped[1], delta=1e-12)
        self.assertAlmostEqual(plain[1], swapped[0], delta=1e-12)
        self.assertAlmostEqual(plain[2], swapped[2], delta=1e-12)

    def test_decomposition_input_rejections(self):
        """Workflow step 6 rejection: length mismatch and negative inputs raise ValueError."""
        with self.assertRaises(ValueError):
            ftua.variance_decomposition([0.5], [0.5, 0.5])
        with self.assertRaises(ValueError):
            ftua.variance_decomposition([0.5, -0.2], [0.5, 0.5])
        with self.assertRaises(ValueError):
            ftua.variance_decomposition([0.5, 0.5], [0.5, -0.2])

    def test_decomposition_not_a_birnbaum_sensitivity(self):
        """Workflow step 6 fence: shares weight EF spread and FV fractions, not raw deltas."""
        sigmas = [ftua.error_factor_to_sigma(ef) for ef in ERROR_FACTORS]
        shares = ftua.variance_decomposition(FV_WEIGHTS, sigmas)
        self.assertAlmostEqual(shares[0], 0.627931, delta=1e-6)
        # A Birnbaum-style raw delta would rank by sigma alone, not by share.
        self.assertGreater(sigmas[2], sigmas[1])
        self.assertLess(shares[2], shares[1])


class DeterminismTests(unittest.TestCase):
    def test_module_is_deterministic_across_calls(self):
        """Workflow steps 2 to 6 are deterministic: repeated calls return identical values."""
        sigmas_a = [ftua.error_factor_to_sigma(ef) for ef in ERROR_FACTORS]
        sigmas_b = [ftua.error_factor_to_sigma(ef) for ef in ERROR_FACTORS]
        self.assertEqual(sigmas_a, sigmas_b)
        band_a = ftua.confidence_band(Q_TOP, SIGMA_LNQ)
        band_b = ftua.confidence_band(Q_TOP, SIGMA_LNQ)
        self.assertEqual(band_a, band_b)
        self.assertEqual(
            ftua.variance_decomposition(FV_WEIGHTS, sigmas_a),
            ftua.variance_decomposition(FV_WEIGHTS, sigmas_b),
        )


if __name__ == "__main__":
    unittest.main()
