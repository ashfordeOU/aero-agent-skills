"""Contract tests for the clause 5.7.2.8 time-distribution accuracy logic."""

import unittest

from e50_time_distribution_logic import (
    EXCEEDED,
    WITHIN,
    assess_distribution,
    chain_error_ns,
    distribution_error_ns,
    holdover_error_ns,
    hop_error_ns,
    max_distribution_period_s,
    validate_hop,
    validate_nonnegative,
    validate_positive,
)

HOP_A = {
    "name": "bus-master-to-router",
    "delay_ns": 1000.0,
    "asymmetry_ns": 100.0,
    "quantization_ns": 20.0,
    "jitter_ns": 30.0,
}
HOP_B = {"name": "router-to-user", "delay_ns": 0.0, "jitter_ns": 40.0}
CHAIN = [HOP_A, HOP_B]


class ValidationTests(unittest.TestCase):
    def test_zero_is_a_valid_nonnegative(self):
        self.assertAlmostEqual(validate_nonnegative(0), 0.0, places=9)

    def test_negative_rejected(self):
        with self.assertRaises(ValueError):
            validate_nonnegative(-1.0)

    def test_boolean_rejected_as_a_number(self):
        with self.assertRaises(ValueError):
            validate_nonnegative(True)

    def test_text_rejected_as_a_number(self):
        with self.assertRaises(ValueError):
            validate_nonnegative("1000")

    def test_infinite_rejected(self):
        with self.assertRaises(ValueError):
            validate_nonnegative(float("inf"))

    def test_zero_period_rejected(self):
        with self.assertRaises(ValueError):
            validate_positive(0.0, "period_s")

    def test_hop_without_a_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_hop({"delay_ns": 10.0})

    def test_hop_with_an_unknown_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_hop({"name": "h", "delay_ms": 10.0})

    def test_hop_with_a_non_boolean_compensation_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_hop({"name": "h", "compensated": "yes"})

    def test_hop_that_is_not_a_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_hop(["name", "h"])

    def test_empty_chain_rejected(self):
        with self.assertRaises(ValueError):
            chain_error_ns([])


class HopBudgetTests(unittest.TestCase):
    def test_uncompensated_hop_carries_the_whole_delay(self):
        systematic, _ = hop_error_ns({"name": "h", "delay_ns": 800.0})
        self.assertAlmostEqual(systematic, 800.0, places=6)

    def test_compensated_hop_carries_only_the_residual(self):
        systematic, _ = hop_error_ns(
            {"name": "h", "delay_ns": 800.0, "compensated": True, "residual_ns": 12.0}
        )
        self.assertAlmostEqual(systematic, 12.0, places=6)

    def test_asymmetry_contributes_half_of_itself(self):
        systematic, _ = hop_error_ns({"name": "h", "asymmetry_ns": 100.0})
        self.assertAlmostEqual(systematic, 50.0, places=6)

    def test_quantization_contributes_half_a_step(self):
        systematic, _ = hop_error_ns({"name": "h", "quantization_ns": 64.0})
        self.assertAlmostEqual(systematic, 32.0, places=6)

    def test_jitter_is_reported_as_the_random_term(self):
        _, random_ns = hop_error_ns({"name": "h", "jitter_ns": 30.0})
        self.assertAlmostEqual(random_ns, 30.0, places=6)


class ChainTests(unittest.TestCase):
    def test_systematic_terms_add_linearly(self):
        self.assertAlmostEqual(chain_error_ns(CHAIN)["systematic_ns"], 1060.0, places=6)

    def test_random_terms_combine_root_sum_square(self):
        self.assertAlmostEqual(chain_error_ns(CHAIN)["random_ns"], 50.0, places=6)

    def test_total_is_systematic_plus_random(self):
        chain = chain_error_ns(CHAIN)
        self.assertAlmostEqual(
            chain["total_ns"], chain["systematic_ns"] + chain["random_ns"], places=6
        )

    def test_breakdown_names_every_hop(self):
        names = [h["name"] for h in chain_error_ns(CHAIN)["breakdown"]]
        self.assertEqual(names, ["bus-master-to-router", "router-to-user"])

    def test_random_terms_do_not_add_linearly(self):
        chain = chain_error_ns(CHAIN)
        self.assertLess(chain["random_ns"], 70.0)


class HoldoverTests(unittest.TestCase):
    def test_holdover_grows_with_the_period(self):
        self.assertAlmostEqual(holdover_error_ns(10.0, 2.0), 20000.0, places=6)

    def test_holdover_is_linear_in_drift(self):
        self.assertAlmostEqual(
            holdover_error_ns(20.0, 2.0), 2.0 * holdover_error_ns(10.0, 2.0), places=6
        )

    def test_a_perfect_oscillator_holds_over_without_error(self):
        self.assertAlmostEqual(holdover_error_ns(0.0, 60.0), 0.0, places=9)

    def test_negative_drift_rejected(self):
        with self.assertRaises(ValueError):
            holdover_error_ns(-1.0, 2.0)

    def test_zero_period_rejected_by_holdover(self):
        with self.assertRaises(ValueError):
            holdover_error_ns(10.0, 0.0)


class EndToEndTests(unittest.TestCase):
    def test_total_includes_chain_and_holdover(self):
        budget = distribution_error_ns(CHAIN, 10.0, 2.0)
        self.assertAlmostEqual(budget["total_ns"], 1060.0 + 20000.0 + 50.0, places=6)

    def test_holdover_is_reported_separately(self):
        budget = distribution_error_ns(CHAIN, 10.0, 2.0)
        self.assertAlmostEqual(budget["holdover_ns"], 20000.0, places=6)

    def test_shorter_period_lowers_the_total(self):
        long_period = distribution_error_ns(CHAIN, 10.0, 4.0)["total_ns"]
        short_period = distribution_error_ns(CHAIN, 10.0, 1.0)["total_ns"]
        self.assertLess(short_period, long_period)


class PeriodSizingTests(unittest.TestCase):
    def test_longest_period_spends_exactly_the_remaining_budget(self):
        required = 21110.0
        period = max_distribution_period_s(CHAIN, 10.0, required)
        total = distribution_error_ns(CHAIN, 10.0, period)["total_ns"]
        self.assertAlmostEqual(total, required, places=6)

    def test_a_chain_that_spends_the_allowance_returns_zero(self):
        self.assertAlmostEqual(max_distribution_period_s(CHAIN, 10.0, 500.0), 0.0, places=9)

    def test_no_drift_means_the_period_is_not_the_constraint(self):
        self.assertIsNone(max_distribution_period_s(CHAIN, 0.0, 5000.0))

    def test_tighter_accuracy_shortens_the_period(self):
        loose = max_distribution_period_s(CHAIN, 10.0, 40000.0)
        tight = max_distribution_period_s(CHAIN, 10.0, 20000.0)
        self.assertLess(tight, loose)

    def test_zero_required_accuracy_rejected(self):
        with self.assertRaises(ValueError):
            max_distribution_period_s(CHAIN, 10.0, 0.0)


class AssessmentTests(unittest.TestCase):
    def _consumer(self, required, period=2.0, name="payload-timestamper"):
        return {
            "name": name,
            "hops": CHAIN,
            "drift_ppm": 10.0,
            "period_s": period,
            "required_ns": required,
        }

    def test_a_comfortable_consumer_is_within_accuracy(self):
        result = assess_distribution([self._consumer(50000.0)])
        self.assertEqual(result["verdict"], WITHIN)

    def test_a_starved_consumer_exceeds_accuracy(self):
        result = assess_distribution([self._consumer(5000.0)])
        self.assertEqual(result["verdict"], EXCEEDED)

    def test_a_budget_landing_on_the_allowance_is_within(self):
        budget = distribution_error_ns(CHAIN, 10.0, 2.0)["total_ns"]
        result = assess_distribution([self._consumer(budget)])
        self.assertEqual(result["verdict"], WITHIN)

    def test_the_worst_consumer_is_named(self):
        result = assess_distribution(
            [self._consumer(50000.0, name="housekeeping"), self._consumer(5000.0, name="ranging")]
        )
        self.assertEqual(result["worst_consumer"], "ranging")

    def test_one_failing_consumer_fails_the_set(self):
        result = assess_distribution(
            [self._consumer(50000.0, name="housekeeping"), self._consumer(5000.0, name="ranging")]
        )
        self.assertEqual(result["verdict"], EXCEEDED)

    def test_a_failing_consumer_is_given_a_period_remedy(self):
        result = assess_distribution([self._consumer(5000.0)])
        self.assertTrue(any("distribution period of at most" in f for f in result["findings"]))

    def test_a_chain_bound_consumer_is_told_the_period_cannot_help(self):
        result = assess_distribution([self._consumer(900.0)])
        self.assertTrue(any("cannot recover it" in f for f in result["findings"]))

    def test_the_stated_period_remedy_actually_holds_the_consumer(self):
        result = assess_distribution([self._consumer(5000.0)])
        period = result["consumers"][0]["max_period_s"]
        fixed = assess_distribution([self._consumer(5000.0, period=period)])
        self.assertEqual(fixed["verdict"], WITHIN)

    def test_margin_is_the_allowance_less_the_budget(self):
        result = assess_distribution([self._consumer(50000.0)])
        entry = result["consumers"][0]
        self.assertAlmostEqual(
            entry["margin_ns"], entry["required_ns"] - entry["total_ns"], places=6
        )

    def test_an_empty_consumer_set_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_distribution([])

    def test_a_consumer_without_a_required_accuracy_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_distribution([{"name": "x", "hops": CHAIN, "period_s": 2.0}])

    def test_a_consumer_without_a_name_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_distribution(
                [{"hops": CHAIN, "period_s": 2.0, "required_ns": 5000.0}]
            )


if __name__ == "__main__":
    unittest.main()
