"""Contract tests for the board repair operator qualification logic."""

import datetime
import unittest

from q7028_repair_operator_qualification_logic import (
    CERTIFICATE_VALIDITY_MONTHS,
    CURRENCY_MONTHS,
    REPAIR_CLASS_REQUIREMENTS,
    VISION_VALIDITY_MONTHS,
    add_months,
    certificate_expiry,
    currency_findings,
    parse_date,
    qualify_operator,
    requirements_for,
    sample_verdict,
    vision_findings,
)

ASSESSED = "2026-09-19"


def base_record(**overrides):
    """An operator current on the land-repair class with a full sample set."""
    record = {
        "training_hours": 24.0,
        "samples_made": 6,
        "samples_accepted": 6,
        "vision_check_date": "2026-03-01",
        "certified_on": "2025-10-01",
        "last_worked_date": "2026-08-01",
    }
    record.update(overrides)
    return record


class DateArithmeticTests(unittest.TestCase):
    def test_adding_months_stays_in_the_year(self):
        self.assertEqual(add_months(datetime.date(2026, 1, 15), 3), datetime.date(2026, 4, 15))

    def test_adding_months_rolls_the_year(self):
        self.assertEqual(add_months(datetime.date(2026, 11, 10), 4), datetime.date(2027, 3, 10))

    def test_a_short_month_clamps_the_day(self):
        self.assertEqual(add_months(datetime.date(2026, 1, 31), 1), datetime.date(2026, 2, 28))

    def test_december_end_resolves(self):
        self.assertEqual(add_months(datetime.date(2026, 12, 31), 1), datetime.date(2027, 1, 31))

    def test_non_date_rejected_by_add_months(self):
        with self.assertRaises(ValueError):
            add_months("2026-01-15", 3)

    def test_iso_string_parses(self):
        self.assertEqual(parse_date("2026-09-19"), datetime.date(2026, 9, 19))

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("19-09-2026")


class RequirementTests(unittest.TestCase):
    def test_every_class_declares_hours_and_samples(self):
        for name in REPAIR_CLASS_REQUIREMENTS:
            requirements = requirements_for(name)
            self.assertGreater(requirements["training_hours"], 0.0)
            self.assertGreaterEqual(
                requirements["samples_required"], requirements["samples_to_accept"]
            )

    def test_component_replacement_costs_more_than_coating(self):
        self.assertGreater(
            requirements_for("component-replacement")["training_hours"],
            requirements_for("coating")["training_hours"],
        )

    def test_class_match_ignores_case_and_spacing(self):
        self.assertEqual(requirements_for(" Plated Hole ")["repair_class"], "plated-hole")

    def test_unknown_class_rejected(self):
        with self.assertRaises(ValueError):
            requirements_for("firmware")


class SampleTests(unittest.TestCase):
    def test_a_full_accepted_set_passes(self):
        verdict = sample_verdict("conductor", 4, 4)
        self.assertTrue(verdict["passed"])
        self.assertAlmostEqual(verdict["first_pass_yield"], 1.0, places=9)

    def test_a_class_that_tolerates_one_reject_passes_with_one(self):
        verdict = sample_verdict("land", 6, 5)
        self.assertTrue(verdict["passed"])

    def test_too_few_samples_made_is_flagged(self):
        verdict = sample_verdict("land", 3, 3)
        self.assertFalse(verdict["passed"])
        self.assertTrue(any("practical samples were made" in f for f in verdict["findings"]))

    def test_too_few_samples_accepted_is_flagged(self):
        verdict = sample_verdict("plated-hole", 6, 4)
        self.assertFalse(verdict["passed"])

    def test_yield_is_reported(self):
        self.assertAlmostEqual(sample_verdict("land", 6, 3)["first_pass_yield"], 0.5, places=9)

    def test_more_accepted_than_made_rejected(self):
        with self.assertRaises(ValueError):
            sample_verdict("land", 4, 6)

    def test_negative_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            sample_verdict("land", -1, 0)


class VisionAndCurrencyTests(unittest.TestCase):
    def test_a_recent_vision_check_is_clean(self):
        self.assertEqual(vision_findings("2026-03-01", ASSESSED), [])

    def test_a_vision_check_expiring_on_the_day_is_still_valid(self):
        checked = datetime.date(2025, 9, 19)
        expiry = add_months(checked, VISION_VALIDITY_MONTHS)
        self.assertEqual(vision_findings(checked, expiry), [])

    def test_a_lapsed_vision_check_is_flagged(self):
        self.assertTrue(vision_findings("2024-01-01", ASSESSED))

    def test_recent_work_keeps_the_operator_current(self):
        self.assertEqual(currency_findings("2026-08-01", ASSESSED), [])

    def test_work_exactly_on_the_currency_edge_is_current(self):
        worked = datetime.date(2026, 3, 19)
        self.assertEqual(currency_findings(worked, add_months(worked, CURRENCY_MONTHS)), [])

    def test_stale_work_is_flagged(self):
        self.assertTrue(currency_findings("2025-01-01", ASSESSED))

    def test_no_recorded_work_is_flagged(self):
        self.assertTrue(currency_findings(None, ASSESSED))

    def test_certificate_expiry_follows_the_validity_period(self):
        issued = datetime.date(2025, 10, 1)
        self.assertEqual(
            certificate_expiry(issued), add_months(issued, CERTIFICATE_VALIDITY_MONTHS)
        )


class QualificationTests(unittest.TestCase):
    def test_a_complete_current_operator_is_qualified(self):
        verdict = qualify_operator(base_record(), "land", ASSESSED)
        self.assertTrue(verdict["qualified"])
        self.assertEqual(verdict["action_required"], "none")

    def test_short_training_hours_demand_full_training(self):
        verdict = qualify_operator(base_record(training_hours=8.0), "land", ASSESSED)
        self.assertEqual(verdict["action_required"], "full-training")
        self.assertFalse(verdict["qualified"])

    def test_a_failed_sample_set_demands_practical_samples_only(self):
        verdict = qualify_operator(base_record(samples_accepted=2), "land", ASSESSED)
        self.assertEqual(verdict["action_required"], "practical-samples")

    def test_lost_currency_demands_practical_samples_not_the_course(self):
        verdict = qualify_operator(base_record(last_worked_date="2024-01-01"), "land", ASSESSED)
        self.assertEqual(verdict["action_required"], "practical-samples")

    def test_missing_training_outranks_lost_currency(self):
        verdict = qualify_operator(
            base_record(training_hours=1.0, last_worked_date="2024-01-01"), "land", ASSESSED
        )
        self.assertEqual(verdict["action_required"], "full-training")

    def test_a_lapsed_vision_check_reaches_the_findings(self):
        verdict = qualify_operator(base_record(vision_check_date="2023-01-01"), "land", ASSESSED)
        self.assertTrue(any("near-vision" in f for f in verdict["findings"]))

    def test_a_lapsed_certificate_reaches_the_findings(self):
        verdict = qualify_operator(base_record(certified_on="2020-01-01"), "land", ASSESSED)
        self.assertTrue(any("lapsed on" in f for f in verdict["findings"]))

    def test_the_same_record_can_fail_a_harder_class(self):
        self.assertTrue(qualify_operator(base_record(), "land", ASSESSED)["qualified"])
        self.assertFalse(
            qualify_operator(base_record(), "component-replacement", ASSESSED)["qualified"]
        )

    def test_the_certificate_expiry_is_reported(self):
        verdict = qualify_operator(base_record(), "land", ASSESSED)
        self.assertEqual(verdict["certificate_expiry"], "2027-10-01")

    def test_missing_record_key_rejected(self):
        record = base_record()
        del record["vision_check_date"]
        with self.assertRaises(ValueError):
            qualify_operator(record, "land", ASSESSED)

    def test_negative_training_hours_rejected(self):
        with self.assertRaises(ValueError):
            qualify_operator(base_record(training_hours=-2.0), "land", ASSESSED)

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            qualify_operator("land", "land", ASSESSED)


if __name__ == "__main__":
    unittest.main()
