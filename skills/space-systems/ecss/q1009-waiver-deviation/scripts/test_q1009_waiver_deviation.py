#!/usr/bin/env python3
"""Contract test for deviation and waiver request handling (offline)."""

import copy
import datetime
import unittest

from q1009_waiver_deviation_logic import (
    CUSTOMER_AUTHORITY,
    DURATIONS,
    IMPACT_KEYS,
    REQUIRED_FIELDS,
    SUPPLIER_AUTHORITY,
    VERDICT_APPROVED,
    VERDICT_EXPIRED,
    VERDICT_INCOMPLETE,
    VERDICT_PENDING,
    VERDICT_READY,
    VERDICT_REJECTED,
    VERDICT_VIOLATION,
    approval_authority,
    authorisation_remaining,
    check_impact_assessment,
    check_request_completeness,
    determine_request_type,
    parse_date,
    prepare_waiver_request,
    request_identifier_ok,
)

CLEAN_IMPACT = {
    "safety": False,
    "reliability": False,
    "interfaces": False,
    "lifetime": False,
    "verification": True,
}

REQUEST = {
    "request_id": "WVR-2031",
    "configuration_item": "CI-3020 harness assembly",
    "requirement_id": "REQ-EL-0440",
    "departure_description": "two backshell screws torqued below the drawing value",
    "justification": "retorque campaign shows joint retention above the design load",
    "affected_items": ["SN-014", "SN-015"],
    "duration": "limited-effectivity",
    "impact_assessment": dict(CLEAN_IMPACT),
    "requirement_in_customer_baseline": False,
    "departure_already_incurred": True,
    "approval_state": "approved",
    "items_used_before_approval": False,
    "units_authorised": 2,
    "units_used": 0,
    "expiry_date": "2026-06-30",
}

AS_OF = "2026-01-15"


def _req(**overrides):
    request = copy.deepcopy(REQUEST)
    request.update(overrides)
    return request


class RequestTypeTests(unittest.TestCase):
    def test_departure_not_yet_incurred_is_a_deviation(self):
        self.assertEqual(determine_request_type(False), "deviation")

    def test_departure_already_incurred_is_a_waiver(self):
        self.assertEqual(determine_request_type(True), "waiver")

    def test_non_boolean_timing_rejected(self):
        with self.assertRaises(ValueError):
            determine_request_type("later")

    def test_prepare_reports_the_type_from_the_timing(self):
        self.assertEqual(
            prepare_waiver_request(_req(departure_already_incurred=False), AS_OF)[
                "request_type"
            ],
            "deviation",
        )


class IdentifierAndDateTests(unittest.TestCase):
    def test_register_identifier_accepted(self):
        self.assertTrue(request_identifier_ok("WVR-2031"))

    def test_lowercase_identifier_refused(self):
        self.assertFalse(request_identifier_ok("wvr-2031"))

    def test_non_string_identifier_refused(self):
        self.assertFalse(request_identifier_ok(2031))

    def test_iso_date_parses(self):
        self.assertEqual(parse_date("as_of", "2026-06-30"), datetime.date(2026, 6, 30))

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("expiry_date", "30-06-2026")

    def test_empty_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_date("expiry_date", "")


class CompletenessTests(unittest.TestCase):
    def test_full_request_is_complete(self):
        self.assertTrue(check_request_completeness(REQUEST)["complete"])

    def test_every_required_field_is_detected_when_absent(self):
        for field in REQUIRED_FIELDS:
            request = _req()
            del request[field]
            self.assertIn(field, check_request_completeness(request)["missing_fields"])

    def test_empty_effectivity_list_counts_as_missing(self):
        self.assertIn(
            "affected_items",
            check_request_completeness(_req(affected_items=[]))["missing_fields"],
        )

    def test_bad_identifier_is_a_finding_not_a_missing_field(self):
        result = check_request_completeness(_req(request_id="wvr 2031"))
        self.assertEqual(result["missing_fields"], ())
        self.assertFalse(result["complete"])

    def test_unknown_duration_rejected(self):
        with self.assertRaises(ValueError):
            check_request_completeness(_req(duration="forever-ish"))

    def test_every_declared_duration_is_accepted(self):
        for duration in DURATIONS:
            self.assertTrue(check_request_completeness(_req(duration=duration))["complete"])

    def test_non_mapping_request_rejected(self):
        with self.assertRaises(ValueError):
            check_request_completeness("WVR-2031")


class ImpactTests(unittest.TestCase):
    def test_complete_impact_assessment(self):
        self.assertTrue(check_impact_assessment(CLEAN_IMPACT)["complete"])

    def test_missing_heading_is_reported(self):
        impact = dict(CLEAN_IMPACT)
        del impact["lifetime"]
        result = check_impact_assessment(impact)
        self.assertFalse(result["complete"])
        self.assertIn("lifetime", result["missing_headings"])

    def test_every_heading_is_checked(self):
        for key in IMPACT_KEYS:
            impact = dict(CLEAN_IMPACT)
            del impact[key]
            self.assertIn(key, check_impact_assessment(impact)["missing_headings"])

    def test_non_boolean_answer_rejected(self):
        with self.assertRaises(ValueError):
            check_impact_assessment(dict(CLEAN_IMPACT, safety="maybe"))

    def test_affected_areas_are_listed(self):
        result = check_impact_assessment(dict(CLEAN_IMPACT, interfaces=True))
        self.assertIn("interfaces", result["affected_areas"])

    def test_incomplete_impact_blocks_the_request(self):
        impact = dict(CLEAN_IMPACT)
        del impact["safety"]
        result = prepare_waiver_request(_req(impact_assessment=impact), AS_OF)
        self.assertEqual(result["verdict"], VERDICT_INCOMPLETE)


class AuthorityTests(unittest.TestCase):
    def test_supplier_requirement_stays_with_the_supplier_board(self):
        self.assertEqual(approval_authority(REQUEST)["authority"], SUPPLIER_AUTHORITY)

    def test_baseline_requirement_goes_to_the_customer(self):
        self.assertEqual(
            approval_authority(_req(requirement_in_customer_baseline=True))["authority"],
            CUSTOMER_AUTHORITY,
        )

    def test_safety_impact_escalates_to_the_customer(self):
        impact = dict(CLEAN_IMPACT, safety=True)
        self.assertEqual(
            approval_authority(_req(impact_assessment=impact))["authority"],
            CUSTOMER_AUTHORITY,
        )

    def test_interface_impact_escalates_to_the_customer(self):
        impact = dict(CLEAN_IMPACT, interfaces=True)
        self.assertEqual(
            approval_authority(_req(impact_assessment=impact))["authority"],
            CUSTOMER_AUTHORITY,
        )

    def test_reliability_alone_does_not_escalate(self):
        impact = dict(CLEAN_IMPACT, reliability=True)
        self.assertEqual(
            approval_authority(_req(impact_assessment=impact))["authority"],
            SUPPLIER_AUTHORITY,
        )

    def test_missing_baseline_flag_rejected(self):
        request = _req()
        del request["requirement_in_customer_baseline"]
        with self.assertRaises(ValueError):
            approval_authority(request)


class AuthorisationTests(unittest.TestCase):
    def test_unused_authorisation_has_units_left(self):
        self.assertEqual(authorisation_remaining(REQUEST, AS_OF)["units_remaining"], 2)

    def test_spent_units_close_the_authorisation(self):
        result = authorisation_remaining(_req(units_used=2), AS_OF)
        self.assertTrue(result["spent"])
        self.assertEqual(result["units_remaining"], 0)

    def test_overrun_is_counted(self):
        self.assertEqual(authorisation_remaining(_req(units_used=3), AS_OF)["units_overrun"], 1)

    def test_expired_approval_is_spent(self):
        result = authorisation_remaining(_req(expiry_date="2026-01-14"), AS_OF)
        self.assertTrue(result["expired"])
        self.assertEqual(result["days_left"], -1)

    def test_expiry_on_the_day_itself_is_still_live(self):
        result = authorisation_remaining(_req(expiry_date=AS_OF), AS_OF)
        self.assertFalse(result["expired"])
        self.assertEqual(result["days_left"], 0)

    def test_open_ended_approval_has_no_expiry(self):
        request = _req()
        del request["expiry_date"]
        self.assertIsNone(authorisation_remaining(request, AS_OF)["days_left"])

    def test_zero_authorised_units_rejected(self):
        with self.assertRaises(ValueError):
            authorisation_remaining(_req(units_authorised=0), AS_OF)

    def test_negative_used_units_rejected(self):
        with self.assertRaises(ValueError):
            authorisation_remaining(_req(units_used=-1), AS_OF)


class PrepareTests(unittest.TestCase):
    def test_approved_live_request_releases_the_items(self):
        result = prepare_waiver_request(REQUEST, AS_OF)
        self.assertEqual(result["verdict"], VERDICT_APPROVED)
        self.assertTrue(result["release_permitted"])

    def test_draft_request_is_ready_to_submit_only(self):
        result = prepare_waiver_request(_req(approval_state="draft"), AS_OF)
        self.assertEqual(result["verdict"], VERDICT_READY)
        self.assertFalse(result["release_permitted"])

    def test_submitted_request_is_still_pending(self):
        result = prepare_waiver_request(_req(approval_state="submitted"), AS_OF)
        self.assertEqual(result["verdict"], VERDICT_PENDING)
        self.assertFalse(result["release_permitted"])

    def test_rejected_request_blocks_use(self):
        result = prepare_waiver_request(_req(approval_state="rejected"), AS_OF)
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertFalse(result["release_permitted"])

    def test_use_before_approval_is_its_own_nonconformance(self):
        result = prepare_waiver_request(
            _req(approval_state="submitted", items_used_before_approval=True), AS_OF
        )
        self.assertEqual(result["verdict"], VERDICT_VIOLATION)
        self.assertTrue(any("nonconformance" in f for f in result["findings"]))

    def test_spent_effectivity_stops_further_release(self):
        result = prepare_waiver_request(_req(units_used=2), AS_OF)
        self.assertEqual(result["verdict"], VERDICT_EXPIRED)
        self.assertFalse(result["release_permitted"])

    def test_expired_approval_stops_further_release(self):
        result = prepare_waiver_request(_req(expiry_date="2025-12-31"), AS_OF)
        self.assertEqual(result["verdict"], VERDICT_EXPIRED)
        self.assertFalse(result["release_permitted"])

    def test_incomplete_request_never_reaches_a_board(self):
        request = _req()
        del request["justification"]
        result = prepare_waiver_request(request, AS_OF)
        self.assertEqual(result["verdict"], VERDICT_INCOMPLETE)
        self.assertIsNone(result["authority"])

    def test_unknown_approval_state_rejected(self):
        with self.assertRaises(ValueError):
            prepare_waiver_request(_req(approval_state="nearly"), AS_OF)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            prepare_waiver_request("WVR-2031", AS_OF)

    def test_bad_as_of_date_rejected(self):
        with self.assertRaises(ValueError):
            prepare_waiver_request(REQUEST, "15/01/2026")


if __name__ == "__main__":
    unittest.main()
