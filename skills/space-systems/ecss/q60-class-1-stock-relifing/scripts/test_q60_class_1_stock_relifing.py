"""Contract tests for the clause 4.3.10 Class 1 stock relifing logic."""

import datetime
import math
import unittest

from q60_class_1_stock_relifing_logic import (
    BASE_RELIFING_TESTS,
    DEFAULT_FLOOR_MONTHS,
    DEFAULT_STEP_MONTHS,
    HERMETIC_PACKAGE_FAMILIES,
    MSL_FLOOR_LIFE_HOURS,
    add_months,
    assess_stock_relifing,
    bake_duration_hours,
    bake_required,
    evaluate_relifing_sample,
    floor_life_hours,
    floor_time_fraction,
    full_months_between,
    granted_storage_months,
    parse_date,
    relifing_sample_size,
    required_relifing_tests,
)


def clean(*names, tested=8):
    return {n: {"units_tested": tested, "units_failed": 0} for n in names}


class DateHelperTests(unittest.TestCase):
    def test_iso_string_parsed(self):
        self.assertEqual(parse_date("2024-03-01"), datetime.date(2024, 3, 1))

    def test_date_object_passed_through(self):
        day = datetime.date(2024, 3, 1)
        self.assertEqual(parse_date(day), day)

    def test_datetime_reduced_to_its_day(self):
        self.assertEqual(
            parse_date(datetime.datetime(2024, 3, 1, 9, 5)), datetime.date(2024, 3, 1)
        )

    def test_malformed_date_refused(self):
        with self.assertRaises(ValueError):
            parse_date("01/03/2024")

    def test_impossible_day_refused(self):
        with self.assertRaises(ValueError):
            parse_date("2023-02-30")

    def test_months_added(self):
        self.assertEqual(add_months("2024-01-15", 12), datetime.date(2025, 1, 15))

    def test_day_clamped_into_a_shorter_month(self):
        self.assertEqual(add_months("2023-01-31", 1), datetime.date(2023, 2, 28))

    def test_leap_day_clamp(self):
        self.assertEqual(add_months("2024-01-31", 1), datetime.date(2024, 2, 29))

    def test_negative_months_refused(self):
        with self.assertRaises(ValueError):
            add_months("2024-01-31", -1)

    def test_whole_months_counted(self):
        self.assertEqual(full_months_between("2024-01-15", "2024-07-15"), 6)

    def test_partial_month_not_counted(self):
        self.assertEqual(full_months_between("2024-01-15", "2024-07-14"), 5)

    def test_reversed_interval_refused(self):
        with self.assertRaises(ValueError):
            full_months_between("2024-07-15", "2024-01-15")


class FloorLifeTests(unittest.TestCase):
    def test_unlimited_level_has_no_floor_life(self):
        self.assertIsNone(floor_life_hours("1"))

    def test_mid_level_floor_life(self):
        self.assertEqual(floor_life_hours("3"), 168)

    def test_level_name_is_case_insensitive(self):
        self.assertEqual(floor_life_hours(" 5A "), 24)

    def test_unlisted_level_refused(self):
        with self.assertRaises(ValueError):
            floor_life_hours("7")

    def test_blank_level_refused(self):
        with self.assertRaises(ValueError):
            floor_life_hours("  ")

    def test_unlimited_level_consumes_nothing(self):
        self.assertAlmostEqual(floor_time_fraction(5000.0, "1"), 0.0, places=9)

    def test_half_the_budget_consumed(self):
        self.assertAlmostEqual(floor_time_fraction(84.0, "3"), 0.5, places=9)

    def test_budget_consumed_exactly(self):
        self.assertAlmostEqual(floor_time_fraction(168.0, "3"), 1.0, places=9)

    def test_zero_floor_life_level_always_owes_a_bake(self):
        self.assertTrue(math.isinf(floor_time_fraction(0.0, "6")))

    def test_negative_exposure_refused(self):
        with self.assertRaises(ValueError):
            floor_time_fraction(-1.0, "3")

    def test_register_carries_the_standard_levels(self):
        self.assertIn("2a", MSL_FLOOR_LIFE_HOURS)
        self.assertIn("5a", MSL_FLOOR_LIFE_HOURS)


class BakeTests(unittest.TestCase):
    def test_budget_exactly_spent_needs_no_bake(self):
        self.assertFalse(bake_required(1.0))

    def test_budget_under_run_needs_no_bake(self):
        self.assertFalse(bake_required(0.4))

    def test_budget_over_run_needs_a_bake(self):
        self.assertTrue(bake_required(1.2))

    def test_infinite_fraction_needs_a_bake(self):
        self.assertTrue(bake_required(math.inf))

    def test_negative_fraction_refused(self):
        with self.assertRaises(ValueError):
            bake_required(-0.1)

    def test_zero_threshold_refused(self):
        with self.assertRaises(ValueError):
            bake_required(0.5, 0.0)

    def test_thin_package_bake(self):
        self.assertEqual(bake_duration_hours(1.0, "3"), 9)

    def test_band_boundary_stays_in_the_thin_band(self):
        self.assertEqual(bake_duration_hours(1.4, "3"), 9)

    def test_mid_package_bake(self):
        self.assertEqual(bake_duration_hours(1.8, "3"), 18)

    def test_thick_package_bake(self):
        self.assertEqual(bake_duration_hours(4.0, "3"), 48)

    def test_package_above_the_widest_band_refused(self):
        with self.assertRaises(ValueError):
            bake_duration_hours(6.0, "3")

    def test_unlimited_level_has_no_bake(self):
        with self.assertRaises(ValueError):
            bake_duration_hours(1.0, "1")

    def test_zero_thickness_refused(self):
        with self.assertRaises(ValueError):
            bake_duration_hours(0.0, "3")


class GrantedPeriodTests(unittest.TestCase):
    def test_first_period_is_the_base(self):
        self.assertEqual(granted_storage_months(24, 0), 24)

    def test_each_round_shortens_the_period(self):
        self.assertEqual(granted_storage_months(24, 1), 18)
        self.assertEqual(granted_storage_months(24, 2), 12)

    def test_period_never_falls_below_the_floor(self):
        self.assertEqual(granted_storage_months(24, 9), DEFAULT_FLOOR_MONTHS)

    def test_step_is_configurable(self):
        self.assertEqual(granted_storage_months(24, 1, 12, 6), 12)

    def test_floor_above_base_refused(self):
        with self.assertRaises(ValueError):
            granted_storage_months(6, 0, 6, 12)

    def test_negative_round_refused(self):
        with self.assertRaises(ValueError):
            granted_storage_months(24, -1)

    def test_default_step_is_six_months(self):
        self.assertEqual(DEFAULT_STEP_MONTHS, 6)


class RequiredTestTests(unittest.TestCase):
    def test_plastic_package_owes_the_base_set(self):
        self.assertEqual(
            required_relifing_tests("plastic-encapsulated"), BASE_RELIFING_TESTS
        )

    def test_hermetic_package_owes_a_leak_check(self):
        self.assertIn("fine-and-gross-leak", required_relifing_tests("ceramic-hermetic"))

    def test_bake_adds_a_moisture_verification(self):
        self.assertIn(
            "post-bake-moisture-verification",
            required_relifing_tests("plastic-encapsulated", True),
        )

    def test_blank_package_family_refused(self):
        with self.assertRaises(ValueError):
            required_relifing_tests("  ")

    def test_hermetic_vocabulary_holds_metal_can(self):
        self.assertIn("metal-can", HERMETIC_PACKAGE_FAMILIES)

    def test_small_stock_takes_the_minimum_sample(self):
        self.assertEqual(relifing_sample_size(40), 5)

    def test_fraction_boundary_does_not_round_up(self):
        self.assertEqual(relifing_sample_size(100), 5)

    def test_proportional_sample_above_the_minimum(self):
        self.assertEqual(relifing_sample_size(200), 10)

    def test_large_stock_is_capped(self):
        self.assertEqual(relifing_sample_size(5000), 20)

    def test_zero_stock_refused(self):
        with self.assertRaises(ValueError):
            relifing_sample_size(0)

    def test_fraction_above_one_refused(self):
        with self.assertRaises(ValueError):
            relifing_sample_size(100, 1.4)


class SampleEvaluationTests(unittest.TestCase):
    def test_clean_results_pass(self):
        out = evaluate_relifing_sample(
            clean("external-visual", "solderability"), BASE_RELIFING_TESTS
        )
        self.assertTrue(out["compliant"])

    def test_one_failure_against_a_zero_accept_number_fails(self):
        results = clean("external-visual", "solderability")
        results["solderability"]["units_failed"] = 1
        out = evaluate_relifing_sample(results, BASE_RELIFING_TESTS)
        self.assertFalse(out["compliant"])
        self.assertEqual(out["failed_tests"], ["solderability"])

    def test_failure_within_a_granted_accept_number_passes(self):
        results = clean("external-visual", "solderability")
        results["external-visual"]["units_failed"] = 1
        out = evaluate_relifing_sample(
            results, BASE_RELIFING_TESTS, {"external-visual": 1}
        )
        self.assertTrue(out["compliant"])

    def test_missing_required_result_refused(self):
        with self.assertRaises(ValueError):
            evaluate_relifing_sample(clean("external-visual"), BASE_RELIFING_TESTS)

    def test_failures_above_units_tested_refused(self):
        results = clean("external-visual", "solderability", tested=4)
        results["solderability"]["units_failed"] = 5
        with self.assertRaises(ValueError):
            evaluate_relifing_sample(results, BASE_RELIFING_TESTS)

    def test_zero_units_tested_refused(self):
        results = clean("external-visual", "solderability")
        results["solderability"]["units_tested"] = 0
        with self.assertRaises(ValueError):
            evaluate_relifing_sample(results, BASE_RELIFING_TESTS)

    def test_non_mapping_results_refused(self):
        with self.assertRaises(ValueError):
            evaluate_relifing_sample(["external-visual"], BASE_RELIFING_TESTS)

    def test_empty_required_set_refused(self):
        with self.assertRaises(ValueError):
            evaluate_relifing_sample(clean("external-visual"), [])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "package_family": "plastic-encapsulated",
            "moisture_sensitivity_level": "3",
            "floor_exposure_hours": 40.0,
            "package_thickness_mm": 1.2,
            "base_storage_months": 24,
            "last_operation_date": "2022-01-15",
            "as_of_date": "2024-06-15",
            "stock_quantity": 200,
            "test_results": clean("external-visual", "solderability"),
        }
        spec.update(overrides)
        return spec

    def test_stock_inside_its_period_is_in_date(self):
        out = assess_stock_relifing(self._spec(as_of_date="2023-06-15"))
        self.assertEqual(out["disposition"], "in-date")

    def test_expiry_day_itself_is_still_in_date(self):
        out = assess_stock_relifing(self._spec(as_of_date="2024-01-15"))
        self.assertEqual(out["disposition"], "in-date")

    def test_day_after_expiry_is_expired(self):
        out = assess_stock_relifing(self._spec(as_of_date="2024-01-16"))
        self.assertTrue(out["expired"])

    def test_clean_re_verification_relifes_the_stock(self):
        out = assess_stock_relifing(self._spec())
        self.assertEqual(out["disposition"], "relifed")

    def test_new_period_is_shorter_than_the_base(self):
        out = assess_stock_relifing(self._spec())
        self.assertEqual(out["new_granted_storage_months"], 18)

    def test_new_expiry_runs_from_the_assessment_date(self):
        out = assess_stock_relifing(self._spec())
        self.assertEqual(out["new_expiry_date"], "2025-12-15")

    def test_already_relifed_stock_gets_the_shortened_period(self):
        out = assess_stock_relifing(self._spec(relifing_rounds_done=1))
        self.assertEqual(out["granted_storage_months"], 18)

    def test_round_ceiling_sends_stock_to_re_screening(self):
        out = assess_stock_relifing(
            self._spec(relifing_rounds_done=2, max_relifing_rounds=2)
        )
        self.assertEqual(out["disposition"], "re-screening-required")

    def test_round_ceiling_is_read_before_any_result(self):
        results = clean("external-visual", "solderability")
        results["solderability"]["units_failed"] = 4
        out = assess_stock_relifing(
            self._spec(
                relifing_rounds_done=2, max_relifing_rounds=2, test_results=results
            )
        )
        self.assertEqual(out["disposition"], "re-screening-required")

    def test_failed_solderability_rejects_the_stock(self):
        results = clean("external-visual", "solderability")
        results["solderability"]["units_failed"] = 2
        out = assess_stock_relifing(self._spec(test_results=results))
        self.assertEqual(out["disposition"], "stock-rejected")

    def test_floor_life_over_run_obliges_a_bake(self):
        out = assess_stock_relifing(
            self._spec(
                floor_exposure_hours=400.0,
                test_results=clean(
                    "external-visual", "solderability", "post-bake-moisture-verification"
                ),
            )
        )
        self.assertTrue(out["bake_required"])
        self.assertEqual(out["bake_duration_hours"], 9)

    def test_bake_adds_a_required_test_that_must_be_evidenced(self):
        with self.assertRaises(ValueError):
            assess_stock_relifing(self._spec(floor_exposure_hours=400.0))

    def test_hermetic_package_owes_a_leak_check(self):
        out = assess_stock_relifing(
            self._spec(
                package_family="ceramic-hermetic",
                test_results=clean(
                    "external-visual", "solderability", "fine-and-gross-leak"
                ),
            )
        )
        self.assertIn("fine-and-gross-leak", out["required_tests"])

    def test_sample_size_reported(self):
        out = assess_stock_relifing(self._spec())
        self.assertEqual(out["sample_size"], 10)

    def test_assessment_before_the_last_operation_refused(self):
        with self.assertRaises(ValueError):
            assess_stock_relifing(self._spec(as_of_date="2021-01-01"))

    def test_missing_required_key_refused(self):
        spec = self._spec()
        del spec["stock_quantity"]
        with self.assertRaises(ValueError):
            assess_stock_relifing(spec)

    def test_non_mapping_spec_refused(self):
        with self.assertRaises(ValueError):
            assess_stock_relifing(["package_family"])

    def test_findings_name_the_expired_period(self):
        out = assess_stock_relifing(self._spec())
        self.assertTrue(any("storage period" in f for f in out["findings"]))


if __name__ == "__main__":
    unittest.main()
