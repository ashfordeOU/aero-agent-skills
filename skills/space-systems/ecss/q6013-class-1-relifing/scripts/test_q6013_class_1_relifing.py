"""Contract tests for the clause 4.3.10 commercial-lot relifing logic."""

import datetime
import unittest

from q6013_class_1_relifing_logic import (
    BASE_RELIFING_TESTS,
    DEFAULT_MIN_SAMPLE,
    DEFAULT_SAMPLE_FRACTION,
    HERMETIC_PACKAGE_FAMILIES,
    add_months,
    assess_relifing,
    evaluate_relifing_tests,
    expiry_date,
    full_months_between,
    is_expired,
    parse_date,
    permitted_storage_months,
    relifing_sample_size,
    required_relifing_tests,
)

REGISTER = {
    "ceramic-hermetic": {"dry-nitrogen": 60, "controlled-ambient": 24},
    "plastic-encapsulated": {"dry-nitrogen": 24, "controlled-ambient": 12},
}


def passes(*names, tested=6):
    return {n: {"units_tested": tested, "units_passed": tested} for n in names}


class DateParsingTests(unittest.TestCase):
    def test_iso_string_parsed(self):
        self.assertEqual(parse_date("2024-03-01"), datetime.date(2024, 3, 1))

    def test_date_object_passed_through(self):
        d = datetime.date(2024, 3, 1)
        self.assertEqual(parse_date(d), d)

    def test_datetime_reduced_to_its_day(self):
        self.assertEqual(
            parse_date(datetime.datetime(2024, 3, 1, 14, 30)), datetime.date(2024, 3, 1)
        )

    def test_malformed_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("01/03/2024")

    def test_impossible_day_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("2023-02-30")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_date(20240301)


class MonthArithmeticTests(unittest.TestCase):
    def test_simple_addition(self):
        self.assertEqual(add_months("2024-01-15", 3), datetime.date(2024, 4, 15))

    def test_year_rollover(self):
        self.assertEqual(add_months("2024-11-10", 4), datetime.date(2025, 3, 10))

    def test_day_clamped_into_a_shorter_month(self):
        self.assertEqual(add_months("2024-01-31", 1), datetime.date(2024, 2, 29))

    def test_day_clamped_in_a_common_year(self):
        self.assertEqual(add_months("2023-01-31", 1), datetime.date(2023, 2, 28))

    def test_zero_months_is_the_same_day(self):
        self.assertEqual(add_months("2024-05-05", 0), datetime.date(2024, 5, 5))

    def test_negative_months_rejected(self):
        with self.assertRaises(ValueError):
            add_months("2024-05-05", -1)

    def test_float_months_rejected(self):
        with self.assertRaises(ValueError):
            add_months("2024-05-05", 1.5)

    def test_whole_months_counted(self):
        self.assertEqual(full_months_between("2024-01-15", "2024-04-15"), 3)

    def test_partial_month_not_counted(self):
        self.assertEqual(full_months_between("2024-01-15", "2024-04-14"), 2)

    def test_same_day_is_zero_months(self):
        self.assertEqual(full_months_between("2024-01-15", "2024-01-15"), 0)

    def test_end_before_start_rejected(self):
        with self.assertRaises(ValueError):
            full_months_between("2024-04-15", "2024-01-15")


class StorageRegisterTests(unittest.TestCase):
    def test_period_looked_up(self):
        self.assertEqual(
            permitted_storage_months(REGISTER, "ceramic-hermetic", "dry-nitrogen"), 60
        )

    def test_environment_changes_the_period(self):
        self.assertEqual(
            permitted_storage_months(REGISTER, "ceramic-hermetic", "controlled-ambient"),
            24,
        )

    def test_case_and_padding_tolerated(self):
        self.assertEqual(
            permitted_storage_months(REGISTER, " Plastic-Encapsulated ", "DRY-NITROGEN"),
            24,
        )

    def test_unlisted_family_rejected(self):
        with self.assertRaises(ValueError):
            permitted_storage_months(REGISTER, "moulded-module", "dry-nitrogen")

    def test_ungranted_environment_rejected(self):
        with self.assertRaises(ValueError):
            permitted_storage_months(REGISTER, "ceramic-hermetic", "open-warehouse")

    def test_non_positive_period_rejected(self):
        with self.assertRaises(ValueError):
            permitted_storage_months({"x": {"dry-nitrogen": 0}}, "x", "dry-nitrogen")

    def test_empty_register_rejected(self):
        with self.assertRaises(ValueError):
            permitted_storage_months({}, "ceramic-hermetic", "dry-nitrogen")


class ExpiryTests(unittest.TestCase):
    def test_expiry_is_the_reference_date_plus_the_period(self):
        self.assertEqual(expiry_date("2022-06-30", 24), datetime.date(2024, 6, 30))

    def test_zero_period_rejected(self):
        with self.assertRaises(ValueError):
            expiry_date("2022-06-30", 0)

    def test_date_before_expiry_is_in_date(self):
        self.assertFalse(is_expired("2024-06-29", "2024-06-30"))

    def test_date_on_expiry_is_still_in_date(self):
        self.assertFalse(is_expired("2024-06-30", "2024-06-30"))

    def test_date_after_expiry_is_expired(self):
        self.assertTrue(is_expired("2024-07-01", "2024-06-30"))


class RequiredTestTests(unittest.TestCase):
    def test_plastic_package_gets_the_base_set(self):
        self.assertEqual(required_relifing_tests("plastic-encapsulated"), BASE_RELIFING_TESTS)

    def test_hermetic_package_adds_a_seal_check(self):
        self.assertIn("hermeticity", required_relifing_tests("ceramic-hermetic"))

    def test_hermetic_family_set_is_immutable(self):
        self.assertIsInstance(HERMETIC_PACKAGE_FAMILIES, frozenset)

    def test_empty_family_rejected(self):
        with self.assertRaises(ValueError):
            required_relifing_tests("  ")


class SampleSizeTests(unittest.TestCase):
    def test_fraction_rounds_up(self):
        self.assertEqual(relifing_sample_size(410, 0.02, 3), 9)

    def test_exact_fraction_does_not_round_up_a_whole_unit(self):
        self.assertEqual(relifing_sample_size(400, 0.02, 3), 8)

    def test_floor_applies_to_a_small_lot(self):
        self.assertEqual(relifing_sample_size(50, 0.02, 3), 3)

    def test_sample_never_exceeds_the_lot(self):
        self.assertEqual(relifing_sample_size(2, 0.02, 3), 2)

    def test_defaults_are_exposed(self):
        self.assertEqual(
            relifing_sample_size(1000),
            relifing_sample_size(1000, DEFAULT_SAMPLE_FRACTION, DEFAULT_MIN_SAMPLE),
        )

    def test_zero_lot_rejected(self):
        with self.assertRaises(ValueError):
            relifing_sample_size(0)

    def test_fraction_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            relifing_sample_size(500, 1.5, 3)


class TestEvaluationTests(unittest.TestCase):
    def test_all_tests_passing_is_compliant(self):
        out = evaluate_relifing_tests(passes(*BASE_RELIFING_TESTS), BASE_RELIFING_TESTS)
        self.assertTrue(out["compliant"])
        self.assertEqual(out["failed_tests"], [])

    def test_one_failing_unit_fails_a_full_pass_requirement(self):
        results = passes(*BASE_RELIFING_TESTS)
        results["solderability"] = {"units_tested": 6, "units_passed": 5}
        out = evaluate_relifing_tests(results, BASE_RELIFING_TESTS)
        self.assertFalse(out["compliant"])
        self.assertEqual(out["failed_tests"], ["solderability"])

    def test_pass_fraction_exactly_at_the_requirement_is_compliant(self):
        results = passes(*BASE_RELIFING_TESTS)
        results["solderability"] = {"units_tested": 8, "units_passed": 6}
        out = evaluate_relifing_tests(results, BASE_RELIFING_TESTS, 0.75)
        record = [r for r in out["results"] if r["test"] == "solderability"][0]
        self.assertAlmostEqual(record["pass_fraction"], 0.75, places=9)
        self.assertTrue(out["compliant"])

    def test_pass_fraction_below_the_requirement_fails(self):
        results = passes(*BASE_RELIFING_TESTS)
        results["solderability"] = {"units_tested": 8, "units_passed": 5}
        out = evaluate_relifing_tests(results, BASE_RELIFING_TESTS, 0.75)
        self.assertFalse(out["compliant"])

    def test_missing_required_result_rejected(self):
        results = passes("visual", "electrical")
        with self.assertRaises(ValueError):
            evaluate_relifing_tests(results, BASE_RELIFING_TESTS)

    def test_more_passed_than_tested_rejected(self):
        results = passes(*BASE_RELIFING_TESTS)
        results["visual"] = {"units_tested": 6, "units_passed": 7}
        with self.assertRaises(ValueError):
            evaluate_relifing_tests(results, BASE_RELIFING_TESTS)

    def test_zero_units_tested_rejected(self):
        results = passes(*BASE_RELIFING_TESTS)
        results["visual"] = {"units_tested": 0, "units_passed": 0}
        with self.assertRaises(ValueError):
            evaluate_relifing_tests(results, BASE_RELIFING_TESTS)

    def test_required_fraction_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_relifing_tests(passes(*BASE_RELIFING_TESTS), BASE_RELIFING_TESTS, 1.2)

    def test_empty_required_set_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_relifing_tests(passes(*BASE_RELIFING_TESTS), [])


class AssessmentTests(unittest.TestCase):
    def _spec(self, **over):
        spec = {
            "package_family": "ceramic-hermetic",
            "storage_environment": "controlled-ambient",
            "storage_register": REGISTER,
            "last_acceptance_date": "2021-06-30",
            "as_of_date": "2024-09-14",
            "lot_size": 400,
            "test_results": passes("visual", "solderability", "electrical", "hermeticity"),
            "original_acceptance_date": "2021-06-30",
            "max_relifing_operations": 3,
            "relifing_operations_done": 1,
            "max_cumulative_storage_months": 120,
            "extension_months": 24,
        }
        spec.update(over)
        return spec

    def test_lot_inside_its_period_needs_no_action(self):
        out = assess_relifing(self._spec(as_of_date="2023-06-01"))
        self.assertEqual(out["disposition"], "in-date")
        self.assertFalse(out["expired"])
        self.assertIsNone(out["new_expiry_date"])

    def test_expiry_date_is_reported(self):
        out = assess_relifing(self._spec())
        self.assertEqual(out["expiry_date"], "2023-06-30")

    def test_expired_lot_passing_re_verification_is_relifed(self):
        out = assess_relifing(self._spec())
        self.assertEqual(out["disposition"], "relifed")
        self.assertEqual(out["new_expiry_date"], "2026-09-14")

    def test_hermetic_package_requires_a_seal_check(self):
        out = assess_relifing(self._spec())
        self.assertIn("hermeticity", out["required_tests"])

    def test_plastic_package_does_not_require_a_seal_check(self):
        out = assess_relifing(
            self._spec(
                package_family="plastic-encapsulated",
                storage_environment="dry-nitrogen",
                test_results=passes("visual", "solderability", "electrical"),
            )
        )
        self.assertNotIn("hermeticity", out["required_tests"])
        self.assertEqual(out["disposition"], "relifed")

    def test_failed_re_verification_rejects_the_lot(self):
        results = passes("visual", "solderability", "electrical", "hermeticity")
        results["hermeticity"] = {"units_tested": 6, "units_passed": 4}
        out = assess_relifing(self._spec(test_results=results))
        self.assertEqual(out["disposition"], "lot-rejected")

    def test_exhausted_extension_count_sends_the_lot_for_re_screening(self):
        out = assess_relifing(self._spec(relifing_operations_done=3))
        self.assertEqual(out["disposition"], "re-screening-required")

    def test_cumulative_ceiling_sends_the_lot_for_re_screening(self):
        out = assess_relifing(self._spec(max_cumulative_storage_months=24))
        self.assertEqual(out["disposition"], "re-screening-required")

    def test_ceiling_is_checked_before_any_test_result_is_read(self):
        out = assess_relifing(self._spec(relifing_operations_done=3, test_results={}))
        self.assertEqual(out["disposition"], "re-screening-required")
        self.assertIsNone(out["test_evaluation"])

    def test_sample_size_travels_with_the_result(self):
        out = assess_relifing(self._spec())
        self.assertEqual(out["sample_size"], 8)

    def test_cumulative_storage_counted_from_original_acceptance(self):
        out = assess_relifing(self._spec(original_acceptance_date="2019-06-30"))
        self.assertEqual(out["cumulative_storage_months"], 62)

    def test_assessment_before_acceptance_rejected(self):
        with self.assertRaises(ValueError):
            assess_relifing(self._spec(as_of_date="2020-01-01"))

    def test_last_acceptance_before_original_rejected(self):
        with self.assertRaises(ValueError):
            assess_relifing(self._spec(original_acceptance_date="2022-01-01"))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["lot_size"]
        with self.assertRaises(ValueError):
            assess_relifing(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_relifing(["package_family"])

    def test_zero_extension_rejected(self):
        with self.assertRaises(ValueError):
            assess_relifing(self._spec(extension_months=0))

    def test_findings_name_the_expired_period(self):
        out = assess_relifing(self._spec())
        self.assertTrue(any("storage period" in f for f in out["findings"]))


if __name__ == "__main__":
    unittest.main()
