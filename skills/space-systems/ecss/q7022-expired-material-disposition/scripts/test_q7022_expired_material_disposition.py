"""Contract tests for the expired-material disposition logic."""

import datetime
import unittest

from q7022_expired_material_disposition_logic import (
    BASE_EXTENSION_FRACTION,
    MAX_EXTENSIONS,
    MAX_OVERRUN_FRACTION,
    days_past_expiry,
    decide_disposition,
    eligibility_findings,
    extension_days,
    grade_revalidation,
    is_retestable_family,
    new_expiry_date,
    overrun_fraction,
    parse_date,
)

WINDOWS = {
    "viscosity_pa_s": (40.0, 90.0),
    "lap_shear_mpa": (18.0, 40.0),
    "gel_time_min": (25.0, 55.0),
}

GOOD_MEASUREMENTS = {
    "viscosity_pa_s": 62.0,
    "lap_shear_mpa": 24.5,
    "gel_time_min": 38.0,
}


def base_lot(**overrides):
    """A 730-day epoxy lot found 60 days past expiry, stored to specification."""
    lot = {
        "material_family": "two-part-epoxy-adhesive",
        "expiry_date": "2026-06-01",
        "assessment_date": "2026-07-31",
        "original_shelf_life_days": 730,
        "storage_compliant": True,
        "prior_extensions": 0,
        "flight_critical": True,
    }
    lot.update(overrides)
    return lot


class ParseDateTests(unittest.TestCase):
    def test_iso_string_parsed(self):
        self.assertEqual(parse_date("2026-06-01"), datetime.date(2026, 6, 1))

    def test_non_iso_text_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("June 2026")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            parse_date(None)


class OverrunTests(unittest.TestCase):
    def test_days_past_expiry_counted(self):
        self.assertEqual(days_past_expiry("2026-06-01", "2026-07-31"), 60)

    def test_in_date_lot_gives_a_negative_overrun(self):
        self.assertLess(days_past_expiry("2026-06-01", "2026-05-01"), 0)

    def test_overrun_fraction_is_the_day_ratio(self):
        self.assertAlmostEqual(overrun_fraction(60, 730), 60.0 / 730.0, places=12)

    def test_zero_original_life_rejected(self):
        with self.assertRaises(ValueError):
            overrun_fraction(60, 0)

    def test_non_integer_overrun_rejected(self):
        with self.assertRaises(ValueError):
            overrun_fraction(60.5, 730)


class RetestableFamilyTests(unittest.TestCase):
    def test_epoxy_is_retestable(self):
        self.assertTrue(is_retestable_family("two-part-epoxy-adhesive"))

    def test_pyrotechnic_composition_is_not(self):
        self.assertFalse(is_retestable_family("pyrotechnic-composition"))

    def test_family_match_ignores_case_and_padding(self):
        self.assertFalse(is_retestable_family("  Solid-Propellant-Grain "))

    def test_empty_family_rejected(self):
        with self.assertRaises(ValueError):
            is_retestable_family("   ")


class EligibilityTests(unittest.TestCase):
    def test_clean_lot_is_eligible(self):
        self.assertEqual(eligibility_findings(base_lot()), [])

    def test_non_retestable_family_removes_the_option(self):
        findings = eligibility_findings(base_lot(material_family="pyrotechnic-composition"))
        self.assertTrue(any("no defined re-validation test" in f for f in findings))

    def test_storage_excursion_removes_the_option(self):
        findings = eligibility_findings(base_lot(storage_compliant=False))
        self.assertTrue(any("unquantified excursion" in f for f in findings))

    def test_spent_extension_budget_removes_the_option(self):
        findings = eligibility_findings(base_lot(prior_extensions=MAX_EXTENSIONS))
        self.assertTrue(any("exhausting its budget" in f for f in findings))

    def test_overrun_beyond_the_allowed_fraction_removes_the_option(self):
        findings = eligibility_findings(base_lot(assessment_date="2027-12-01"))
        self.assertTrue(any("beyond the" in f for f in findings))

    def test_overrun_exactly_at_the_allowed_fraction_is_still_eligible(self):
        lot = base_lot(original_shelf_life_days=120)
        self.assertAlmostEqual(
            overrun_fraction(days_past_expiry(lot["expiry_date"], lot["assessment_date"]), 120),
            MAX_OVERRUN_FRACTION,
            places=9,
        )
        self.assertEqual(eligibility_findings(lot), [])

    def test_negative_prior_extension_count_rejected(self):
        with self.assertRaises(ValueError):
            eligibility_findings(base_lot(prior_extensions=-1))

    def test_missing_required_key_rejected(self):
        lot = base_lot()
        del lot["original_shelf_life_days"]
        with self.assertRaises(ValueError):
            eligibility_findings(lot)


class RevalidationGradingTests(unittest.TestCase):
    def test_all_properties_inside_their_windows_pass(self):
        graded = grade_revalidation(GOOD_MEASUREMENTS, WINDOWS)
        self.assertTrue(graded["passed"])
        self.assertEqual(graded["failures"], [])

    def test_property_below_its_window_fails(self):
        bad = dict(GOOD_MEASUREMENTS, lap_shear_mpa=12.0)
        graded = grade_revalidation(bad, WINDOWS)
        self.assertFalse(graded["passed"])
        self.assertTrue(any("below its acceptance low" in f for f in graded["failures"]))

    def test_property_above_its_window_fails(self):
        bad = dict(GOOD_MEASUREMENTS, viscosity_pa_s=140.0)
        graded = grade_revalidation(bad, WINDOWS)
        self.assertTrue(any("above its acceptance high" in f for f in graded["failures"]))

    def test_measurement_exactly_on_a_window_bound_passes(self):
        edge = dict(GOOD_MEASUREMENTS, gel_time_min=25.0)
        self.assertTrue(grade_revalidation(edge, WINDOWS)["passed"])

    def test_unmeasured_property_is_a_failure_not_a_pass(self):
        partial = dict(GOOD_MEASUREMENTS)
        del partial["gel_time_min"]
        graded = grade_revalidation(partial, WINDOWS)
        self.assertFalse(graded["passed"])
        self.assertEqual(graded["not_measured"], ["gel_time_min"])

    def test_empty_window_set_rejected(self):
        with self.assertRaises(ValueError):
            grade_revalidation(GOOD_MEASUREMENTS, {})

    def test_inverted_window_rejected(self):
        with self.assertRaises(ValueError):
            grade_revalidation(GOOD_MEASUREMENTS, {"viscosity_pa_s": (90.0, 40.0)})

    def test_non_numeric_measurement_rejected(self):
        with self.assertRaises(ValueError):
            grade_revalidation({"viscosity_pa_s": "62"}, {"viscosity_pa_s": (40.0, 90.0)})

    def test_non_mapping_measurements_rejected(self):
        with self.assertRaises(ValueError):
            grade_revalidation([62.0], WINDOWS)


class ExtensionSizingTests(unittest.TestCase):
    def test_first_extension_is_the_base_fraction(self):
        self.assertEqual(extension_days(730, 0), int(730 * BASE_EXTENSION_FRACTION))

    def test_second_extension_is_halved(self):
        self.assertEqual(extension_days(730, 1), int(730 * BASE_EXTENSION_FRACTION / 2.0))

    def test_extension_shrinks_with_each_grant(self):
        self.assertLess(extension_days(730, 1), extension_days(730, 0))

    def test_spent_budget_cannot_be_sized(self):
        with self.assertRaises(ValueError):
            extension_days(730, MAX_EXTENSIONS)

    def test_lot_too_short_lived_to_extend_rejected(self):
        with self.assertRaises(ValueError):
            extension_days(3, 0)

    def test_new_expiry_runs_from_the_assessment_date(self):
        self.assertEqual(new_expiry_date("2026-07-31", 182), datetime.date(2027, 1, 29))

    def test_zero_day_extension_rejected(self):
        with self.assertRaises(ValueError):
            new_expiry_date("2026-07-31", 0)


class DispositionTests(unittest.TestCase):
    def test_eligible_lot_with_no_results_goes_to_re_test(self):
        record = decide_disposition(base_lot())
        self.assertEqual(record["disposition"], "re-test")

    def test_non_retestable_family_is_scrapped(self):
        record = decide_disposition(base_lot(material_family="hydrogen-getter"))
        self.assertEqual(record["disposition"], "scrap")

    def test_storage_excursion_is_scrapped(self):
        record = decide_disposition(base_lot(storage_compliant=False))
        self.assertEqual(record["disposition"], "scrap")

    def test_clean_revalidation_extends_the_lot(self):
        record = decide_disposition(
            base_lot(acceptance_windows=WINDOWS, measurements=GOOD_MEASUREMENTS)
        )
        self.assertEqual(record["disposition"], "extend")
        self.assertEqual(record["extension_days"], int(730 * BASE_EXTENSION_FRACTION))
        self.assertEqual(record["new_expiry_date"], "2027-01-29")

    def test_failed_revalidation_on_a_flight_lot_is_scrapped(self):
        bad = dict(GOOD_MEASUREMENTS, lap_shear_mpa=9.0)
        record = decide_disposition(base_lot(acceptance_windows=WINDOWS, measurements=bad))
        self.assertEqual(record["disposition"], "scrap")

    def test_failed_revalidation_on_a_non_flight_lot_is_rejected(self):
        bad = dict(GOOD_MEASUREMENTS, lap_shear_mpa=9.0)
        record = decide_disposition(
            base_lot(acceptance_windows=WINDOWS, measurements=bad, flight_critical=False)
        )
        self.assertEqual(record["disposition"], "reject")

    def test_lot_still_in_date_is_refused_by_this_procedure(self):
        record = decide_disposition(base_lot(assessment_date="2026-05-01"))
        self.assertEqual(record["disposition"], "reject")
        self.assertTrue(any("not past its expiry" in f for f in record["findings"]))

    def test_record_carries_the_overrun(self):
        record = decide_disposition(base_lot())
        self.assertEqual(record["days_past_expiry"], 60)
        self.assertAlmostEqual(record["overrun_fraction"], 60.0 / 730.0, places=12)

    def test_second_extension_is_smaller_than_the_first(self):
        first = decide_disposition(
            base_lot(acceptance_windows=WINDOWS, measurements=GOOD_MEASUREMENTS)
        )
        second = decide_disposition(
            base_lot(
                acceptance_windows=WINDOWS,
                measurements=GOOD_MEASUREMENTS,
                prior_extensions=1,
            )
        )
        self.assertLess(second["extension_days"], first["extension_days"])

    def test_non_mapping_lot_rejected(self):
        with self.assertRaises(ValueError):
            decide_disposition("LOT-9")


if __name__ == "__main__":
    unittest.main()
