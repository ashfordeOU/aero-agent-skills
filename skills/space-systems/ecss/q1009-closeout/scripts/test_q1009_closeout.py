#!/usr/bin/env python3
"""Contract test for nonconformance close-out against criteria (offline)."""

import copy
import datetime
import unittest

from q1009_closeout_logic import (
    ACTION_RECORDS,
    BASE_CLOSURE_ROLES,
    BASE_RECORDS,
    CUSTOMER_ROLE,
    DEPARTURE_DISPOSITIONS,
    DEPARTURE_RECORDS,
    DISPOSITIONS,
    VERDICT_BLOCKED,
    VERDICT_CLOSED,
    add_years,
    close_nonconformance,
    closure_signatures,
    missing_records,
    parse_date,
    required_records,
    retention_check,
)

CASE = {
    "ncr_id": "NCR-0412",
    "severity": "major",
    "disposition": "use-as-is",
    "disposition_implemented": True,
    "disposition_verified": True,
    "has_actions": True,
    "actions_verified": True,
    "open_conditions": 0,
    "records_held": [
        "ncr-form",
        "disposition-record",
        "verification-evidence",
        "concession-approval",
        "as-built-configuration-update",
        "action-closure-evidence",
    ],
    "signed_by": ["product-assurance", "engineering", "customer-representative"],
    "closure_date": "2026-04-30",
    "retention_years": 10,
}


def _case(**overrides):
    case = copy.deepcopy(CASE)
    case.update(overrides)
    return case


class DateTests(unittest.TestCase):
    def test_iso_date_parses(self):
        self.assertEqual(parse_date("closure_date", "2026-04-30"), datetime.date(2026, 4, 30))

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("closure_date", "30 April 2026")

    def test_ten_years_on_keeps_the_day(self):
        self.assertEqual(add_years(datetime.date(2026, 4, 30), 10), datetime.date(2036, 4, 30))

    def test_leap_day_falls_back_to_the_28th(self):
        self.assertEqual(add_years(datetime.date(2028, 2, 29), 1), datetime.date(2029, 2, 28))

    def test_zero_years_is_the_same_day(self):
        self.assertEqual(add_years(datetime.date(2026, 4, 30), 0), datetime.date(2026, 4, 30))

    def test_negative_years_rejected(self):
        with self.assertRaises(ValueError):
            add_years(datetime.date(2026, 4, 30), -1)


class RecordSetTests(unittest.TestCase):
    def test_base_records_always_required(self):
        needed = required_records("rework", False)
        for record in BASE_RECORDS:
            self.assertIn(record, needed)

    def test_departure_route_adds_the_concession_records(self):
        for disposition in DEPARTURE_DISPOSITIONS:
            needed = required_records(disposition, False)
            for record in DEPARTURE_RECORDS:
                self.assertIn(record, needed)

    def test_rework_needs_no_concession_record(self):
        self.assertNotIn("concession-approval", required_records("rework", False))

    def test_actions_add_their_closure_evidence(self):
        for record in ACTION_RECORDS:
            self.assertIn(record, required_records("rework", True))

    def test_every_disposition_has_a_record_set(self):
        for disposition in DISPOSITIONS:
            self.assertTrue(required_records(disposition, True))

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            required_records("shelved", False)

    def test_full_record_set_leaves_nothing_missing(self):
        self.assertEqual(missing_records(CASE), ())

    def test_absent_record_is_named(self):
        held = [r for r in CASE["records_held"] if r != "concession-approval"]
        self.assertEqual(missing_records(_case(records_held=held)), ("concession-approval",))

    def test_records_held_must_be_a_list(self):
        with self.assertRaises(ValueError):
            missing_records(_case(records_held="ncr-form"))

    def test_blank_record_name_rejected(self):
        with self.assertRaises(ValueError):
            missing_records(_case(records_held=CASE["records_held"] + [" "]))


class SignatureTests(unittest.TestCase):
    def test_major_closure_needs_the_customer(self):
        result = closure_signatures(CASE)
        self.assertIn(CUSTOMER_ROLE, result["required_roles"])
        self.assertTrue(result["complete"])

    def test_minor_closure_does_not(self):
        result = closure_signatures(
            _case(severity="minor", signed_by=list(BASE_CLOSURE_ROLES))
        )
        self.assertNotIn(CUSTOMER_ROLE, result["required_roles"])
        self.assertTrue(result["complete"])

    def test_missing_signature_is_named(self):
        result = closure_signatures(_case(signed_by=["engineering"]))
        self.assertIn("product-assurance", result["missing_roles"])
        self.assertFalse(result["complete"])

    def test_extra_signature_does_not_break_closure(self):
        result = closure_signatures(
            _case(signed_by=CASE["signed_by"] + ["project-management"])
        )
        self.assertTrue(result["complete"])

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            closure_signatures(_case(severity="moderate"))

    def test_signature_list_must_be_a_list(self):
        with self.assertRaises(ValueError):
            closure_signatures(_case(signed_by="engineering"))


class RetentionTests(unittest.TestCase):
    def test_sufficient_retention_is_compliant(self):
        result = retention_check("2026-04-30", 10, 10)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["retained_until"], "2036-04-30")

    def test_short_retention_reports_the_shortfall(self):
        result = retention_check("2026-04-30", 5, 10)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["shortfall_years"], 5)

    def test_longer_retention_has_no_shortfall(self):
        self.assertEqual(retention_check("2026-04-30", 15, 10)["shortfall_years"], 0)

    def test_zero_required_years_rejected(self):
        with self.assertRaises(ValueError):
            retention_check("2026-04-30", 10, 0)

    def test_negative_retention_rejected(self):
        with self.assertRaises(ValueError):
            retention_check("2026-04-30", -1, 10)

    def test_boolean_retention_rejected(self):
        with self.assertRaises(ValueError):
            retention_check("2026-04-30", True, 10)


class CloseoutTests(unittest.TestCase):
    def test_complete_case_closes(self):
        result = close_nonconformance(CASE)
        self.assertEqual(result["verdict"], VERDICT_CLOSED)
        self.assertTrue(result["closed"])
        self.assertEqual(result["unmet_criteria"], ())

    def test_disposition_not_carried_out_blocks_closure(self):
        result = close_nonconformance(_case(disposition_implemented=False))
        self.assertEqual(result["verdict"], VERDICT_BLOCKED)
        self.assertTrue(any("carried out" in c for c in result["unmet_criteria"]))

    def test_disposition_unchecked_blocks_closure(self):
        result = close_nonconformance(_case(disposition_verified=False))
        self.assertTrue(any("never checked" in c for c in result["unmet_criteria"]))

    def test_open_condition_blocks_closure(self):
        result = close_nonconformance(_case(open_conditions=2))
        self.assertFalse(result["closed"])
        self.assertTrue(any("still open" in c for c in result["unmet_criteria"]))

    def test_unverified_actions_block_closure(self):
        result = close_nonconformance(_case(actions_verified=False))
        self.assertTrue(any("verified effective" in c for c in result["unmet_criteria"]))

    def test_verified_actions_without_any_action_is_inconsistent(self):
        result = close_nonconformance(_case(has_actions=False))
        self.assertFalse(result["closed"])

    def test_missing_record_blocks_closure(self):
        held = [r for r in CASE["records_held"] if r != "verification-evidence"]
        result = close_nonconformance(_case(records_held=held))
        self.assertIn("verification-evidence", result["missing_records"])
        self.assertFalse(result["closed"])

    def test_missing_signature_blocks_closure(self):
        result = close_nonconformance(_case(signed_by=["engineering"]))
        self.assertTrue(any("not signed by" in c for c in result["unmet_criteria"]))

    def test_short_retention_blocks_closure(self):
        result = close_nonconformance(_case(retention_years=3))
        self.assertTrue(any("retention" in c for c in result["unmet_criteria"]))

    def test_programme_retention_period_is_configurable(self):
        result = close_nonconformance(_case(retention_years=3), required_retention_years=3)
        self.assertTrue(result["closed"])

    def test_rework_closes_without_a_concession_record(self):
        held = [
            "ncr-form",
            "disposition-record",
            "verification-evidence",
            "action-closure-evidence",
        ]
        result = close_nonconformance(_case(disposition="rework", records_held=held))
        self.assertTrue(result["closed"])

    def test_several_unmet_criteria_are_all_reported(self):
        result = close_nonconformance(
            _case(disposition_implemented=False, signed_by=[], retention_years=1)
        )
        self.assertGreaterEqual(len(result["unmet_criteria"]), 3)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            close_nonconformance("NCR-0412")

    def test_missing_ncr_id_rejected(self):
        case = _case()
        del case["ncr_id"]
        with self.assertRaises(ValueError):
            close_nonconformance(case)

    def test_non_boolean_flag_rejected(self):
        with self.assertRaises(ValueError):
            close_nonconformance(_case(disposition_verified="yes"))


if __name__ == "__main__":
    unittest.main()
