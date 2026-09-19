"""Contract tests for the clause 5.6.6 noise source identification logic."""

import unittest

from e50_noise_sources_logic import (
    COMPLIANT,
    INCOMPLETE,
    OVER_ALLOCATION,
    allocation_margin_k,
    assess_noise_budget,
    dominant_source,
    figure_of_merit_db,
    identified_categories,
    loss_factor,
    loss_noise_temperature,
    missing_categories,
    refer_through_loss,
    source_contribution_k,
    system_noise_temperature,
    validate_loss_db,
    validate_source,
    validate_temperature_k,
)

# Reference chain: sky, atmosphere and ground noise all seen through a 10 dB
# feed run at 290 K, plus the feed's own generated noise and a 120 K front
# end. Referring a source through 10 dB divides it by ten, and the feed
# generates 290 * (1 - 1/10) = 261 K, so the total at the receiver input is
# 2 + 3 + 2.5 + 261 + 120 = 388.5 K. Computed independently of the module.
CHAIN = (
    {"category": "sky-and-cosmic-background", "temperature_k": 20.0, "referred_through_loss_db": 10.0},
    {"category": "atmospheric", "temperature_k": 30.0, "referred_through_loss_db": 10.0},
    {"category": "ground-and-spillover", "temperature_k": 25.0, "referred_through_loss_db": 10.0},
    {"category": "feed-and-line-loss", "loss_db": 10.0, "physical_temperature_k": 290.0},
    {"category": "receiver-front-end", "temperature_k": 120.0},
)
CHAIN_TOTAL_K = 388.5


class ValidationTests(unittest.TestCase):
    def test_negative_temperature_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_k(-1.0)

    def test_boolean_temperature_rejected(self):
        with self.assertRaises(ValueError):
            validate_temperature_k(True)

    def test_negative_loss_rejected(self):
        with self.assertRaises(ValueError):
            validate_loss_db(-3.0)

    def test_zero_loss_accepted(self):
        self.assertAlmostEqual(validate_loss_db(0.0), 0.0, places=9)

    def test_source_without_a_category_rejected(self):
        with self.assertRaises(ValueError):
            validate_source({"temperature_k": 20.0})

    def test_source_with_neither_temperature_nor_loss_rejected(self):
        with self.assertRaises(ValueError):
            validate_source({"category": "atmospheric"})

    def test_source_with_both_temperature_and_loss_rejected(self):
        with self.assertRaises(ValueError):
            validate_source(
                {"category": "feed-and-line-loss", "temperature_k": 50.0, "loss_db": 1.0}
            )

    def test_non_mapping_source_rejected(self):
        with self.assertRaises(ValueError):
            validate_source(["atmospheric", 20.0])

    def test_empty_source_list_rejected(self):
        with self.assertRaises(ValueError):
            system_noise_temperature([])

    def test_bare_string_is_not_a_source_list(self):
        with self.assertRaises(ValueError):
            system_noise_temperature("atmospheric")


class ReferralTests(unittest.TestCase):
    def test_zero_loss_is_unity(self):
        self.assertAlmostEqual(loss_factor(0.0), 1.0, places=9)

    def test_ten_db_is_a_factor_of_ten(self):
        self.assertAlmostEqual(loss_factor(10.0), 10.0, places=9)

    def test_twenty_db_is_a_factor_of_a_hundred(self):
        self.assertAlmostEqual(loss_factor(20.0), 100.0, places=9)

    def test_referral_divides_by_the_loss(self):
        self.assertAlmostEqual(refer_through_loss(100.0, 10.0), 10.0, places=9)

    def test_referral_through_nothing_changes_nothing(self):
        self.assertAlmostEqual(refer_through_loss(100.0, 0.0), 100.0, places=9)

    def test_lossless_element_generates_no_noise(self):
        self.assertAlmostEqual(loss_noise_temperature(0.0, 290.0), 0.0, places=9)

    def test_ten_db_run_generates_most_of_its_physical_temperature(self):
        self.assertAlmostEqual(loss_noise_temperature(10.0, 290.0), 261.0, places=9)

    def test_cooled_run_generates_proportionally_less(self):
        self.assertAlmostEqual(loss_noise_temperature(10.0, 100.0), 90.0, places=9)

    def test_loss_element_contribution_uses_its_generated_noise(self):
        entry = {"category": "feed-and-line-loss", "loss_db": 10.0, "physical_temperature_k": 290.0}
        self.assertAlmostEqual(source_contribution_k(entry), 261.0, places=9)

    def test_temperature_source_contribution_is_referred(self):
        entry = {"category": "atmospheric", "temperature_k": 30.0, "referred_through_loss_db": 10.0}
        self.assertAlmostEqual(source_contribution_k(entry), 3.0, places=9)


class TotalsTests(unittest.TestCase):
    def test_chain_total(self):
        self.assertAlmostEqual(system_noise_temperature(CHAIN), CHAIN_TOTAL_K, places=9)

    def test_dominant_source_is_the_feed_run(self):
        category, value = dominant_source(CHAIN)
        self.assertEqual(category, "feed-and-line-loss")
        self.assertAlmostEqual(value, 261.0, places=9)

    def test_dominance_does_not_depend_on_list_order(self):
        self.assertEqual(dominant_source(tuple(reversed(CHAIN)))[0], "feed-and-line-loss")

    def test_categories_are_reported_sorted(self):
        self.assertEqual(identified_categories(CHAIN), tuple(sorted(identified_categories(CHAIN))))

    def test_full_chain_misses_no_category(self):
        self.assertEqual(missing_categories(CHAIN), ())

    def test_absent_group_is_named(self):
        trimmed = tuple(s for s in CHAIN if s["category"] != "atmospheric")
        self.assertEqual(missing_categories(trimmed), ("atmospheric",))

    def test_figure_of_merit(self):
        self.assertAlmostEqual(figure_of_merit_db(40.0, 100.0), 20.0, places=9)

    def test_figure_of_merit_falls_as_noise_rises(self):
        self.assertAlmostEqual(
            figure_of_merit_db(40.0, 1000.0), figure_of_merit_db(40.0, 100.0) - 10.0, places=9
        )

    def test_zero_system_temperature_has_no_figure_of_merit(self):
        with self.assertRaises(ValueError):
            figure_of_merit_db(40.0, 0.0)

    def test_margin_is_the_unspent_kelvin(self):
        self.assertAlmostEqual(allocation_margin_k(388.5, 400.0), 11.5, places=9)

    def test_margin_goes_negative_when_overspent(self):
        self.assertAlmostEqual(allocation_margin_k(400.0, 388.5), -11.5, places=9)


class AssessTests(unittest.TestCase):
    def test_complete_chain_inside_allocation_is_compliant(self):
        result = assess_noise_budget(CHAIN, 400.0)
        self.assertEqual(result["verdict"], COMPLIANT)
        self.assertEqual(result["findings"], ())

    def test_total_exactly_on_the_allocation_is_inside(self):
        result = assess_noise_budget(CHAIN, CHAIN_TOTAL_K)
        self.assertAlmostEqual(result["allocation_margin_k"], 0.0, places=9)
        self.assertTrue(result["within_allocation"])
        self.assertEqual(result["verdict"], COMPLIANT)

    def test_over_allocation_is_reported_with_the_overspend(self):
        result = assess_noise_budget(CHAIN, 300.0)
        self.assertEqual(result["verdict"], OVER_ALLOCATION)
        self.assertTrue(any("exceeds" in f for f in result["findings"]))

    def test_missing_group_outranks_an_overspend(self):
        trimmed = tuple(s for s in CHAIN if s["category"] != "receiver-front-end")
        result = assess_noise_budget(trimmed, 100.0)
        self.assertEqual(result["verdict"], INCOMPLETE)

    def test_missing_group_is_named_in_the_findings(self):
        trimmed = tuple(s for s in CHAIN if s["category"] != "receiver-front-end")
        result = assess_noise_budget(trimmed, 400.0)
        self.assertTrue(any("receiver-front-end" in f for f in result["findings"]))

    def test_dominant_group_is_reported_when_something_is_wrong(self):
        result = assess_noise_budget(CHAIN, 300.0)
        self.assertTrue(any("dominates the budget" in f for f in result["findings"]))

    def test_figure_of_merit_is_carried_when_a_gain_is_given(self):
        result = assess_noise_budget(CHAIN, 400.0, gain_dbi=50.0)
        self.assertIsNotNone(result["figure_of_merit_db"])

    def test_no_figure_of_merit_without_a_gain(self):
        self.assertIsNone(assess_noise_budget(CHAIN, 400.0)["figure_of_merit_db"])

    def test_short_figure_of_merit_fails_the_budget(self):
        result = assess_noise_budget(CHAIN, 400.0, gain_dbi=30.0, required_gt_db=25.0)
        self.assertEqual(result["verdict"], OVER_ALLOCATION)
        self.assertTrue(result["figure_of_merit_short"])

    def test_sufficient_figure_of_merit_passes(self):
        result = assess_noise_budget(CHAIN, 400.0, gain_dbi=50.0, required_gt_db=20.0)
        self.assertEqual(result["verdict"], COMPLIANT)
        self.assertFalse(result["figure_of_merit_short"])

    def test_dominant_contribution_is_carried(self):
        result = assess_noise_budget(CHAIN, 400.0)
        self.assertAlmostEqual(result["dominant_contribution_k"], 261.0, places=9)

    def test_negative_allocation_rejected(self):
        with self.assertRaises(ValueError):
            assess_noise_budget(CHAIN, -1.0)


if __name__ == "__main__":
    unittest.main()
