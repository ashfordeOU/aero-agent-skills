"""Contract tests for the clause 5.3.10 Class 2 stock relifing logic."""

import unittest

from q60_class_2_stock_relifing_logic import (
    DEFAULT_ACCEPT_NUMBER,
    MAXIMUM_RELIFING_SAMPLE,
    MAX_RELIFING_ROUNDS,
    MINIMUM_RELIFING_SAMPLE,
    MINIMUM_REGRANT_MONTHS,
    PACKAGE_BASELINE_MONTHS,
    REGRANT_DECAY,
    STORE_MULTIPLIER,
    assess_relifing,
    baseline_storage_months,
    evaluate_relifing_results,
    granted_storage_months,
    regranted_period_months,
    relifing_round_ceiling_reached,
    relifing_sample_size,
    relifing_test_set,
    storage_expired,
    store_multiplier,
)


class BaselinePeriodTests(unittest.TestCase):
    def test_hermetic_family_carries_the_long_baseline(self):
        self.assertAlmostEqual(baseline_storage_months("hermetic-ceramic"), 60.0, places=9)

    def test_plastic_family_carries_the_short_baseline(self):
        self.assertAlmostEqual(
            baseline_storage_months("plastic-encapsulated"), 24.0, places=9
        )

    def test_family_token_is_normalized(self):
        self.assertAlmostEqual(
            baseline_storage_months(" Passive-Chip "), 36.0, places=9
        )

    def test_unlisted_family_refused(self):
        with self.assertRaises(ValueError):
            baseline_storage_months("moulded-module")

    def test_blank_family_refused(self):
        with self.assertRaises(ValueError):
            baseline_storage_months("   ")

    def test_register_carries_the_common_families(self):
        self.assertIn("hermetic-metal", PACKAGE_BASELINE_MONTHS)
        self.assertIn("plastic-encapsulated", PACKAGE_BASELINE_MONTHS)


class StoreMultiplierTests(unittest.TestCase):
    def test_dry_nitrogen_extends_the_period(self):
        self.assertAlmostEqual(store_multiplier("dry-nitrogen"), 1.5, places=9)

    def test_controlled_store_leaves_the_period_alone(self):
        self.assertAlmostEqual(store_multiplier("controlled"), 1.0, places=9)

    def test_uncontrolled_store_halves_the_period(self):
        self.assertAlmostEqual(store_multiplier("uncontrolled"), 0.5, places=9)

    def test_ungraded_store_refused(self):
        with self.assertRaises(ValueError):
            store_multiplier("the-back-room")

    def test_store_register_carries_three_grades(self):
        self.assertEqual(len(STORE_MULTIPLIER), 3)

    def test_granted_period_combines_package_and_store(self):
        self.assertAlmostEqual(
            granted_storage_months("hermetic-ceramic", "dry-nitrogen"), 90.0, places=9
        )

    def test_uncontrolled_store_shortens_a_passive_period(self):
        self.assertAlmostEqual(
            granted_storage_months("passive-chip", "uncontrolled"), 18.0, places=9
        )


class ExpiryTests(unittest.TestCase):
    def test_stock_inside_the_period_has_not_expired(self):
        self.assertFalse(storage_expired(10.0, 24.0))

    def test_stock_exactly_on_the_period_has_not_expired(self):
        self.assertFalse(storage_expired(24.0, 24.0))

    def test_stock_past_the_period_has_expired(self):
        self.assertTrue(storage_expired(30.0, 24.0))

    def test_negative_elapsed_refused(self):
        with self.assertRaises(ValueError):
            storage_expired(-1.0, 24.0)

    def test_zero_granted_period_refused(self):
        with self.assertRaises(ValueError):
            storage_expired(10.0, 0.0)


class RoundCeilingTests(unittest.TestCase):
    def test_first_relifing_is_under_the_ceiling(self):
        self.assertFalse(relifing_round_ceiling_reached(0))

    def test_ceiling_reached_at_the_permitted_number(self):
        self.assertTrue(relifing_round_ceiling_reached(MAX_RELIFING_ROUNDS))

    def test_ceiling_is_three_rounds_by_default(self):
        self.assertEqual(MAX_RELIFING_ROUNDS, 3)

    def test_negative_round_count_refused(self):
        with self.assertRaises(ValueError):
            relifing_round_ceiling_reached(-1)

    def test_zero_ceiling_refused(self):
        with self.assertRaises(ValueError):
            relifing_round_ceiling_reached(1, 0)


class TestSetTests(unittest.TestCase):
    def test_every_relifing_starts_with_an_external_visual(self):
        self.assertEqual(
            relifing_test_set("passive-chip", "none", "passive")[0], "external-visual"
        )

    def test_hermetic_package_owes_a_leak_test(self):
        self.assertIn(
            "fine-and-gross-leak",
            relifing_test_set("hermetic-ceramic", "tin-lead", "active"),
        )

    def test_plastic_package_owes_no_leak_test(self):
        self.assertNotIn(
            "fine-and-gross-leak",
            relifing_test_set("plastic-encapsulated", "tin-lead", "active"),
        )

    def test_finished_leads_owe_solderability(self):
        self.assertIn(
            "solderability-sample",
            relifing_test_set("plastic-encapsulated", "tin-lead", "passive"),
        )

    def test_pure_tin_finish_adds_a_whisker_review(self):
        self.assertIn(
            "whisker-risk-review",
            relifing_test_set("plastic-encapsulated", "pure-tin", "passive"),
        )

    def test_active_part_owes_electrical_at_the_extremes(self):
        self.assertIn(
            "electrical-at-temperature-extremes",
            relifing_test_set("plastic-encapsulated", "tin-lead", "active"),
        )

    def test_passive_part_owes_no_electrical_extremes(self):
        self.assertNotIn(
            "electrical-at-temperature-extremes",
            relifing_test_set("passive-chip", "none", "passive"),
        )

    def test_unknown_part_function_refused(self):
        with self.assertRaises(ValueError):
            relifing_test_set("passive-chip", "none", "structural")


class SampleSizingTests(unittest.TestCase):
    def test_proportional_sample_above_the_floor(self):
        self.assertEqual(relifing_sample_size(100), 5)

    def test_small_lot_takes_the_floor(self):
        self.assertEqual(relifing_sample_size(20), MINIMUM_RELIFING_SAMPLE)

    def test_large_lot_is_capped(self):
        self.assertEqual(relifing_sample_size(500), MAXIMUM_RELIFING_SAMPLE)

    def test_lot_under_the_floor_refused(self):
        with self.assertRaises(ValueError):
            relifing_sample_size(2)

    def test_fraction_above_one_refused(self):
        with self.assertRaises(ValueError):
            relifing_sample_size(100, 1.2)

    def test_cap_below_the_floor_refused(self):
        with self.assertRaises(ValueError):
            relifing_sample_size(100, 0.05, 12, 3)


class ResultEvaluationTests(unittest.TestCase):
    OWED = ("external-visual", "solderability-sample")

    def test_clean_results_pass(self):
        out = evaluate_relifing_results(
            self.OWED, {"external-visual": 0, "solderability-sample": 0}, 5
        )
        self.assertTrue(out["all_passed"])

    def test_a_single_failure_fails_a_zero_accept_test(self):
        out = evaluate_relifing_results(
            self.OWED, {"external-visual": 0, "solderability-sample": 1}, 5
        )
        self.assertFalse(out["all_passed"])
        self.assertEqual(out["failed_tests"], ("solderability-sample",))

    def test_default_accept_number_is_zero(self):
        self.assertEqual(DEFAULT_ACCEPT_NUMBER, 0)

    def test_a_raised_accept_number_absorbs_one_failure(self):
        out = evaluate_relifing_results(
            self.OWED, {"external-visual": 0, "solderability-sample": 1}, 5, 1
        )
        self.assertTrue(out["all_passed"])

    def test_owed_test_with_no_result_refused(self):
        with self.assertRaises(ValueError):
            evaluate_relifing_results(self.OWED, {"external-visual": 0}, 5)

    def test_result_for_an_unowed_test_refused(self):
        with self.assertRaises(ValueError):
            evaluate_relifing_results(
                self.OWED,
                {
                    "external-visual": 0,
                    "solderability-sample": 0,
                    "fine-and-gross-leak": 0,
                },
                5,
            )

    def test_more_failures_than_the_sample_refused(self):
        with self.assertRaises(ValueError):
            evaluate_relifing_results(
                self.OWED, {"external-visual": 0, "solderability-sample": 6}, 5
            )

    def test_empty_owed_set_refused(self):
        with self.assertRaises(ValueError):
            evaluate_relifing_results((), {}, 5)


class RegrantTests(unittest.TestCase):
    def test_first_relifing_regrants_half_the_period(self):
        out = regranted_period_months(24.0, 0)
        self.assertAlmostEqual(out["regranted_months"], 12.0, places=9)
        self.assertEqual(out["rounds_applied"], 1)

    def test_second_relifing_regrants_a_quarter(self):
        out = regranted_period_months(24.0, 1)
        self.assertAlmostEqual(out["regranted_months"], 6.0, places=9)

    def test_regrant_exactly_on_the_floor_is_usable(self):
        out = regranted_period_months(24.0, 2)
        self.assertAlmostEqual(out["regranted_months"], MINIMUM_REGRANT_MONTHS, places=9)
        self.assertTrue(out["usable"])

    def test_regrant_under_the_floor_is_not_usable(self):
        out = regranted_period_months(18.0, 2)
        self.assertFalse(out["usable"])

    def test_decay_above_one_refused(self):
        with self.assertRaises(ValueError):
            regranted_period_months(24.0, 0, 1.4)

    def test_default_decay_is_one_half(self):
        self.assertAlmostEqual(REGRANT_DECAY, 0.5, places=9)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "package_family": "plastic-encapsulated",
            "store_class": "controlled",
            "elapsed_months": 30.0,
            "lot_size": 100,
            "lead_finish": "tin-lead",
            "part_function": "active",
            "test_results": {
                "external-visual": 0,
                "solderability-sample": 0,
                "electrical-at-temperature-extremes": 0,
            },
        }
        spec.update(overrides)
        return spec

    def test_clean_relifing_is_granted(self):
        out = assess_relifing(self._spec())
        self.assertEqual(out["disposition"], "relifing-granted")

    def test_granted_period_is_reported(self):
        out = assess_relifing(self._spec())
        self.assertAlmostEqual(out["regrant"]["regranted_months"], 12.0, places=9)

    def test_stock_inside_its_period_owes_no_relifing(self):
        out = assess_relifing(self._spec(elapsed_months=12.0))
        self.assertEqual(out["disposition"], "relifing-not-required")

    def test_stock_exactly_on_its_period_owes_no_relifing(self):
        out = assess_relifing(self._spec(elapsed_months=24.0))
        self.assertEqual(out["disposition"], "relifing-not-required")

    def test_months_over_the_period_are_reported(self):
        out = assess_relifing(self._spec())
        self.assertAlmostEqual(out["months_over_period"], 6.0, places=9)

    def test_ceiling_reached_sends_the_stock_to_re_screening(self):
        out = assess_relifing(self._spec(completed_rounds=3))
        self.assertEqual(out["disposition"], "re-screening-required")

    def test_ceiling_is_checked_before_any_test_is_sized(self):
        out = assess_relifing(self._spec(completed_rounds=3, test_results={}))
        self.assertEqual(out["disposition"], "re-screening-required")

    def test_a_failed_test_refuses_the_relifing(self):
        out = assess_relifing(
            self._spec(
                test_results={
                    "external-visual": 0,
                    "solderability-sample": 2,
                    "electrical-at-temperature-extremes": 0,
                }
            )
        )
        self.assertEqual(out["disposition"], "relifing-refused")

    def test_regrant_under_the_floor_sends_the_stock_to_re_screening(self):
        out = assess_relifing(
            self._spec(
                package_family="passive-chip",
                store_class="uncontrolled",
                lead_finish="none",
                part_function="passive",
                completed_rounds=2,
                elapsed_months=40.0,
                test_results={"external-visual": 0},
            )
        )
        self.assertEqual(out["disposition"], "re-screening-required")

    def test_hermetic_stock_owes_its_leak_test_in_the_assessment(self):
        out = assess_relifing(
            self._spec(
                package_family="hermetic-ceramic",
                elapsed_months=70.0,
                test_results={
                    "external-visual": 0,
                    "solderability-sample": 0,
                    "fine-and-gross-leak": 0,
                    "electrical-at-temperature-extremes": 0,
                },
            )
        )
        self.assertIn("fine-and-gross-leak", out["owed_tests"])
        self.assertEqual(out["disposition"], "relifing-granted")

    def test_missing_result_for_an_owed_test_refused(self):
        with self.assertRaises(ValueError):
            assess_relifing(self._spec(test_results={"external-visual": 0}))

    def test_missing_required_key_refused(self):
        spec = self._spec()
        del spec["store_class"]
        with self.assertRaises(ValueError):
            assess_relifing(spec)

    def test_non_mapping_spec_refused(self):
        with self.assertRaises(ValueError):
            assess_relifing(["package_family"])

    def test_unlisted_family_refused_in_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_relifing(self._spec(package_family="moulded-module"))

    def test_reasons_are_reported_with_every_disposition(self):
        out = assess_relifing(self._spec())
        self.assertTrue(out["reasons"])


if __name__ == "__main__":
    unittest.main()
