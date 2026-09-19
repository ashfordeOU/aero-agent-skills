"""Contract tests for the board repair authorization logic."""

import unittest

from q7028_repair_authorization_logic import (
    AUTHORITY_LADDER,
    BASE_RECORDS,
    MINIMUM_RETENTION_YEARS,
    authority_rank,
    authorize_repair,
    missing_records,
    required_authority,
    retention_findings,
)


def full_record(**overrides):
    record = {key: "%s-0001" % key for key in BASE_RECORDS}
    record.update(overrides)
    return record


def base_request(**overrides):
    """A listed-method repair on a level 3 flight board, signed off by QA."""
    request = {
        "work_type": "repair",
        "hardware_model": "flight",
        "criticality": 3,
        "approved_by": "quality-assurance",
        "listed_method": True,
        "record": full_record(),
        "retention_years": MINIMUM_RETENTION_YEARS,
    }
    request.update(overrides)
    return request


class LadderTests(unittest.TestCase):
    def test_ladder_is_ordered_weakest_first(self):
        self.assertLess(authority_rank("inspector"), authority_rank("customer"))

    def test_every_rung_resolves(self):
        ranks = [authority_rank(a) for a in AUTHORITY_LADDER]
        self.assertEqual(ranks, sorted(ranks))

    def test_authority_match_ignores_case_and_spacing(self):
        self.assertEqual(authority_rank(" Design Authority "), authority_rank("design-authority"))

    def test_unknown_authority_rejected(self):
        with self.assertRaises(ValueError):
            authority_rank("project-manager")


class RequiredAuthorityTests(unittest.TestCase):
    def test_flight_repair_reaches_quality_assurance(self):
        self.assertEqual(required_authority("repair", "flight", 3), "quality-assurance")

    def test_breadboard_repair_stays_with_the_inspector(self):
        self.assertEqual(required_authority("repair", "breadboard", 4), "inspector")

    def test_modification_reaches_the_design_authority(self):
        self.assertEqual(
            required_authority("modification", "engineering-model", 4), "design-authority"
        )

    def test_top_criticality_reaches_the_customer(self):
        self.assertEqual(required_authority("repair", "flight", 1), "customer")

    def test_unlisted_method_reaches_the_customer(self):
        self.assertEqual(
            required_authority("repair", "engineering-model", 4, listed_method=False),
            "customer",
        )

    def test_the_highest_of_the_drivers_wins(self):
        self.assertEqual(required_authority("modification", "flight", 1), "customer")

    def test_unknown_work_type_rejected(self):
        with self.assertRaises(ValueError):
            required_authority("refurbishment", "flight", 3)

    def test_unknown_hardware_model_rejected(self):
        with self.assertRaises(ValueError):
            required_authority("repair", "prototype", 3)

    def test_out_of_range_criticality_rejected(self):
        with self.assertRaises(ValueError):
            required_authority("repair", "flight", 9)

    def test_non_boolean_listed_method_rejected(self):
        with self.assertRaises(ValueError):
            required_authority("repair", "flight", 3, listed_method="yes")


class RecordTests(unittest.TestCase):
    def test_a_complete_repair_file_owes_nothing(self):
        self.assertEqual(missing_records(full_record()), [])

    def test_an_empty_file_owes_every_base_entry(self):
        self.assertEqual(missing_records({}), list(BASE_RECORDS))

    def test_a_blank_string_counts_as_missing(self):
        self.assertIn("operator-id", missing_records(full_record(**{"operator-id": "   "})))

    def test_a_modification_owes_the_drawing_entries(self):
        missing = missing_records(full_record(), work_type="modification")
        self.assertIn("drawing-change-ref", missing)
        self.assertIn("as-built-update-ref", missing)

    def test_customer_level_approval_owes_its_reference(self):
        missing = missing_records(full_record(), approving_authority="customer")
        self.assertEqual(missing, ["customer-approval-ref"])

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            missing_records("repair-request-id")


class RetentionTests(unittest.TestCase):
    def test_the_minimum_retention_is_clean(self):
        self.assertEqual(retention_findings(MINIMUM_RETENTION_YEARS), [])

    def test_a_longer_retention_is_clean(self):
        self.assertEqual(retention_findings(MINIMUM_RETENTION_YEARS + 5), [])

    def test_a_short_retention_is_flagged(self):
        self.assertTrue(retention_findings(2))

    def test_negative_retention_rejected(self):
        with self.assertRaises(ValueError):
            retention_findings(-1)


class AuthorizeTests(unittest.TestCase):
    def test_a_correctly_approved_flight_repair_is_authorized(self):
        verdict = authorize_repair(base_request())
        self.assertTrue(verdict["authorized"])
        self.assertEqual(verdict["findings"], [])

    def test_an_under_signed_repair_is_refused(self):
        verdict = authorize_repair(base_request(approved_by="inspector"))
        self.assertFalse(verdict["authorized"])
        self.assertEqual(verdict["rungs_short"], 1)

    def test_an_over_signed_repair_is_still_authorized(self):
        verdict = authorize_repair(base_request(approved_by="customer"))
        self.assertTrue(verdict["authorized"])
        self.assertEqual(verdict["rungs_short"], 0)

    def test_a_modification_signed_by_qa_is_refused(self):
        verdict = authorize_repair(
            base_request(work_type="modification", approved_by="quality-assurance")
        )
        self.assertFalse(verdict["authorized"])
        self.assertEqual(verdict["required_authority"], "design-authority")

    def test_an_unlisted_method_is_always_a_finding(self):
        verdict = authorize_repair(base_request(listed_method=False, approved_by="customer"))
        self.assertFalse(verdict["authorized"])
        self.assertTrue(any("listed catalogue" in f for f in verdict["findings"]))

    def test_missing_file_entries_reach_the_findings(self):
        record = full_record()
        del record["inspection-result"]
        verdict = authorize_repair(base_request(record=record))
        self.assertIn("inspection-result", verdict["missing_records"])
        self.assertFalse(verdict["authorized"])

    def test_short_retention_reaches_the_findings(self):
        verdict = authorize_repair(base_request(retention_years=1))
        self.assertTrue(any("retention" in f for f in verdict["findings"]))

    def test_missing_request_key_rejected(self):
        request = base_request()
        del request["approved_by"]
        with self.assertRaises(ValueError):
            authorize_repair(request)

    def test_non_mapping_request_rejected(self):
        with self.assertRaises(ValueError):
            authorize_repair("repair")


if __name__ == "__main__":
    unittest.main()
