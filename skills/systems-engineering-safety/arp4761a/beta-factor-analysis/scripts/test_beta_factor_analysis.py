"""Contract test for the beta-factor-analysis leaf (ARP4761A pack).

Exercises the numbered SKILL.md workflow for quantifying the common-cause
contribution to redundant-channel failure with the beta-factor model:
step 1 fixes the channel inputs (failure rate, beta factor, exposure
time), step 2 splits the failure rate into the independent rate and the
common-cause rate, step 3 computes the common-cause shock probability
Q_cc, step 4 computes the dual-channel CCF-inclusive failure probability
by inclusion-exclusion, step 5 computes the CCF enhancement ratio over
the independence-only assumption, step 6 checks the beta-limit
identities and monotonicity, and step 7 confirms the deterministic
checks. Fact terms exercised: beta-factor model, failure rate split,
common-cause shock probability, dual-channel CCF-inclusive probability,
enhancement ratio, redundancy credit. Procedure terms exercised: split,
compute, quantify, rate split, verify, gate.

Worked-example anchors (lambda = 1e-5 per hour, beta = 0.1, t = 1000
hours): independent rate 9e-6 per hour, common-cause rate 1e-6 per hour,
Q_cc = 9.99500e-4, Q_dual = 1.079695e-3, independence-only probability
9.90058e-5, enhancement 10.9054. Assert targets are the real module
outputs, inside the spec magnitude bounds.
"""

import math
import unittest

from beta_factor_analysis_logic import (
    BETA_MAX,
    BETA_MIN,
    ccf_enhancement,
    common_cause_probability,
    dual_channel_ccf_probability,
    split_failure_rate,
)

LAMBDA = 1e-5
BETA = 0.1
TIME = 1000.0


class TestWorkedExample(unittest.TestCase):
    """Workflow step 1 (channel inputs) and step 2 (failure rate split)."""

    def test_split_failure_rate_worked_example_independent(self):
        """Step 2 of the SKILL.md workflow, the failure rate split, gives
        the independent rate (1 - beta) * lambda = 9e-6 per hour."""
        result = split_failure_rate(LAMBDA, BETA)
        self.assertAlmostEqual(result["independent"], 9e-6, delta=1e-12)

    def test_split_failure_rate_worked_example_common_cause(self):
        """Step 2 of the SKILL.md workflow, the failure rate split, gives
        the common-cause rate beta * lambda = 1e-6 per hour."""
        result = split_failure_rate(LAMBDA, BETA)
        self.assertAlmostEqual(result["common_cause"], 1e-6, delta=1e-12)

    def test_split_failure_rate_dict_keys_exact(self):
        """The failure rate split dict keys are exactly 'independent' and
        'common_cause' as documented in the SKILL.md domain reference."""
        self.assertEqual(
            list(split_failure_rate(LAMBDA, BETA).keys()),
            ["independent", "common_cause"],
        )

    def test_split_failure_rate_rate_conservation(self):
        """The failure rate split conserves the total: independent plus
        common-cause parts sum back to the input failure rate lambda."""
        result = split_failure_rate(LAMBDA, BETA)
        self.assertAlmostEqual(
            result["independent"] + result["common_cause"], LAMBDA, delta=1e-12
        )

    def test_split_failure_rate_beta_zero_keeps_full_rate(self):
        """Workflow step 6 identity: at beta 0 the failure rate split
        assigns the whole rate to the independent part and nothing to the
        common-cause part."""
        result = split_failure_rate(LAMBDA, 0.0)
        self.assertAlmostEqual(result["independent"], LAMBDA, delta=1e-12)
        self.assertAlmostEqual(result["common_cause"], 0.0, delta=1e-12)

    def test_split_failure_rate_beta_one_moves_full_rate(self):
        """Workflow step 6 identity: at beta 1 the failure rate split
        assigns the whole rate to the common-cause part."""
        result = split_failure_rate(LAMBDA, 1.0)
        self.assertAlmostEqual(result["independent"], 0.0, delta=1e-12)
        self.assertAlmostEqual(result["common_cause"], LAMBDA, delta=1e-12)


class TestCommonCauseProbability(unittest.TestCase):
    """Workflow step 3: the common-cause shock probability Q_cc."""

    def test_common_cause_probability_worked_example(self):
        """Step 3 of the SKILL.md workflow computes the common-cause shock
        probability Q_cc = 1 - exp(-beta * lambda * t) = 9.99500e-4 for
        the worked example, within the 1e-8 spec bound."""
        value = common_cause_probability(LAMBDA, BETA, TIME)
        self.assertAlmostEqual(value, 9.99500e-4, delta=1e-8)

    def test_common_cause_probability_beta_zero_is_zero(self):
        """With beta 0 the common-cause shock probability is exactly 0:
        no shared fraction means no common-cause shock."""
        self.assertEqual(common_cause_probability(LAMBDA, 0.0, TIME), 0.0)

    def test_common_cause_probability_zero_time_is_zero(self):
        """At zero exposure time the common-cause shock probability is 0
        for any beta factor."""
        self.assertEqual(common_cause_probability(LAMBDA, BETA, 0.0), 0.0)

    def test_common_cause_probability_grows_with_time(self):
        """The common-cause shock probability grows with the exposure
        time at fixed failure rate and beta factor."""
        low = common_cause_probability(LAMBDA, BETA, 500.0)
        high = common_cause_probability(LAMBDA, BETA, 2000.0)
        self.assertGreater(high, low)


class TestDualChannelProbability(unittest.TestCase):
    """Workflow step 4: the dual-channel CCF-inclusive probability."""

    def test_dual_channel_worked_example(self):
        """Step 4 of the SKILL.md workflow computes the dual-channel
        CCF-inclusive failure probability by inclusion-exclusion:
        1.079695e-3 for the worked example, within the 1e-8 spec bound."""
        value = dual_channel_ccf_probability(LAMBDA, BETA, TIME)
        self.assertAlmostEqual(value, 1.079695e-3, delta=1e-8)

    def test_dual_channel_beta_zero_reduces_to_pure_parallel(self):
        """Workflow step 6 identity: beta 0 reduces Q_dual to the pure
        parallel probability (1 - exp(-lambda * t))^2."""
        q_dual = dual_channel_ccf_probability(LAMBDA, 0.0, TIME)
        pure_parallel = (1.0 - math.exp(-LAMBDA * TIME)) ** 2
        self.assertAlmostEqual(q_dual, pure_parallel, delta=1e-12)

    def test_dual_channel_beta_one_reduces_to_single_channel(self):
        """Workflow step 6 identity: beta 1 reduces Q_dual to the
        single-channel failure probability 1 - exp(-lambda * t)."""
        q_dual = dual_channel_ccf_probability(LAMBDA, 1.0, TIME)
        single = 1.0 - math.exp(-LAMBDA * TIME)
        self.assertAlmostEqual(q_dual, single, delta=1e-12)

    def test_dual_channel_zero_time_is_zero(self):
        """At zero exposure time the dual-channel CCF-inclusive
        probability is 0 for every beta factor."""
        self.assertEqual(dual_channel_ccf_probability(LAMBDA, BETA, 0.0), 0.0)

    def test_dual_channel_monotone_in_beta(self):
        """Workflow step 6 monotonicity: Q_dual at beta 0.05 is below
        Q_dual at beta 0.2 at the fixed worked-example time."""
        low = dual_channel_ccf_probability(LAMBDA, 0.05, TIME)
        high = dual_channel_ccf_probability(LAMBDA, 0.2, TIME)
        self.assertLess(low, high)

    def test_dual_channel_monotone_in_time(self):
        """Q_dual is monotone increasing in the exposure time at fixed
        beta factor: a later horizon accumulates more dual-channel risk."""
        low = dual_channel_ccf_probability(LAMBDA, BETA, 100.0)
        high = dual_channel_ccf_probability(LAMBDA, BETA, 5000.0)
        self.assertGreater(high, low)

    def test_dual_channel_bounded_by_one(self):
        """Q_dual is a probability, so it stays at or below 1 across beta
        factors and exposure times."""
        for b in (0.0, 0.3, 0.7, 1.0):
            for t in (10.0, 1e4, 1e6):
                self.assertLessEqual(dual_channel_ccf_probability(LAMBDA, b, t), 1.0)

    def test_dual_channel_inclusion_exclusion_bounds(self):
        """The inclusion-exclusion union Q_dual = q_i^2 + q_c -
        q_i^2 * q_c lies between each term and the plain sum of terms."""
        q_dual = dual_channel_ccf_probability(LAMBDA, BETA, TIME)
        q_i = 1.0 - math.exp(-(1.0 - BETA) * LAMBDA * TIME)
        q_c = common_cause_probability(LAMBDA, BETA, TIME)
        self.assertGreaterEqual(q_dual, q_i * q_i)
        self.assertGreaterEqual(q_dual, q_c)
        self.assertLessEqual(q_dual, q_i * q_i + q_c)


class TestEnhancement(unittest.TestCase):
    """Workflow step 5: the CCF enhancement ratio."""

    def test_enhancement_worked_example(self):
        """Step 5 of the SKILL.md workflow computes the CCF enhancement
        ratio 10.9054 over the independence-only assumption for the
        worked example, within the 1e-3 spec bound."""
        value = ccf_enhancement(LAMBDA, BETA, TIME)
        self.assertAlmostEqual(value, 10.9054, delta=1e-3)

    def test_enhancement_matches_ratio_definition(self):
        """The CCF enhancement ratio equals Q_dual divided by the
        independence-only parallel probability."""
        ratio = ccf_enhancement(LAMBDA, BETA, TIME)
        q_dual = dual_channel_ccf_probability(LAMBDA, BETA, TIME)
        indep_only = (1.0 - math.exp(-LAMBDA * TIME)) ** 2
        self.assertAlmostEqual(ratio, q_dual / indep_only, delta=1e-12)

    def test_enhancement_beta_zero_is_one(self):
        """Workflow step 6 identity: at beta 0 the CCF enhancement ratio
        is exactly 1.0, no redundancy credit loss."""
        self.assertEqual(ccf_enhancement(LAMBDA, 0.0, TIME), 1.0)

    def test_enhancement_zero_time_beta_zero_is_one(self):
        """At zero exposure time with beta 0 the CCF enhancement ratio is
        1.0 by the beta-zero guard."""
        self.assertEqual(ccf_enhancement(LAMBDA, 0.0, 0.0), 1.0)

    def test_enhancement_zero_time_beta_positive_raises(self):
        """At zero exposure time with beta above 0 the enhancement ratio
        is undefined and must raise ValueError."""
        with self.assertRaises(ValueError):
            ccf_enhancement(LAMBDA, BETA, 0.0)

    def test_enhancement_at_least_one(self):
        """The common-cause contribution never reduces dual-channel risk:
        the CCF enhancement ratio is at least 1.0, so redundancy credit
        decisions must discount the independence-only assumption."""
        for b in (0.0, 0.1, 0.5, 1.0):
            self.assertGreaterEqual(ccf_enhancement(LAMBDA, b, TIME), 1.0)


class TestValueErrorRejection(unittest.TestCase):
    """Workflow step 1 validation: non-physical inputs raise ValueError."""

    def test_split_rejects_non_positive_failure_rate(self):
        """A zero or negative failure rate lambda is rejected by the
        failure rate split."""
        with self.assertRaises(ValueError):
            split_failure_rate(0.0, BETA)
        with self.assertRaises(ValueError):
            split_failure_rate(-1e-5, BETA)

    def test_split_rejects_beta_below_min(self):
        """A beta factor of -0.1 below BETA_MIN is rejected."""
        with self.assertRaises(ValueError):
            split_failure_rate(LAMBDA, -0.1)

    def test_split_rejects_beta_above_max(self):
        """A beta factor of 1.1 above BETA_MAX is rejected."""
        with self.assertRaises(ValueError):
            split_failure_rate(LAMBDA, 1.1)

    def test_shock_probability_rejects_zero_failure_rate(self):
        """The common-cause shock probability rejects a zero failure
        rate lambda."""
        with self.assertRaises(ValueError):
            common_cause_probability(0.0, BETA, TIME)

    def test_shock_probability_rejects_negative_time(self):
        """The common-cause shock probability rejects a negative
        exposure time."""
        with self.assertRaises(ValueError):
            common_cause_probability(LAMBDA, BETA, -1.0)

    def test_dual_channel_rejects_beta_above_max(self):
        """The dual-channel CCF-inclusive probability rejects a beta
        factor above BETA_MAX."""
        with self.assertRaises(ValueError):
            dual_channel_ccf_probability(LAMBDA, 1.1, TIME)

    def test_dual_channel_rejects_negative_time(self):
        """The dual-channel CCF-inclusive probability rejects a negative
        exposure time."""
        with self.assertRaises(ValueError):
            dual_channel_ccf_probability(LAMBDA, BETA, -5.0)

    def test_enhancement_rejects_zero_failure_rate(self):
        """The CCF enhancement ratio rejects a zero failure rate lambda."""
        with self.assertRaises(ValueError):
            ccf_enhancement(0.0, BETA, TIME)

    def test_enhancement_rejects_beta_below_min(self):
        """The CCF enhancement ratio rejects a beta factor below
        BETA_MIN."""
        with self.assertRaises(ValueError):
            ccf_enhancement(LAMBDA, -0.1, TIME)

    def test_module_constants_span_unit_interval(self):
        """The module constants BETA_MIN = 0.0 and BETA_MAX = 1.0 bound
        the beta factor to the unit interval."""
        self.assertEqual(BETA_MIN, 0.0)
        self.assertEqual(BETA_MAX, 1.0)


class TestDeterminism(unittest.TestCase):
    """Workflow step 7: the deterministic checks."""

    def test_repeated_calls_identical(self):
        """The dual-channel CCF-inclusive probability is deterministic:
        repeated calls return bit-identical results."""
        first = dual_channel_ccf_probability(LAMBDA, BETA, TIME)
        for _ in range(5):
            self.assertEqual(dual_channel_ccf_probability(LAMBDA, BETA, TIME), first)


if __name__ == "__main__":
    unittest.main()
