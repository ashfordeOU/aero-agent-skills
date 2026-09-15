"""Contract tests for the clause 4.3.6 Class 1 witnessed buy-off logic.

The cases follow the session in the order it happens: the notice that let the
procuring entity attend, who was actually in the room, whether the activities
the buy-off sits on top of had finished, how many pieces were presented, and
the ship-or-hold decision that comes out of all four. Each gate is exercised on
both sides of its limit.
"""

import unittest

from q60_class_1_buy_off_source_inspection_logic import (
    DEFAULT_NOTICE_DAYS,
    WITNESS_ROLES,
    assess_buy_off,
    notice_days,
    parse_day,
    prerequisite_findings,
    releasable_quantity,
    witness_state,
)


def _attendee(role="procuring-entity", organisation="prime"):
    return {"role": role, "organisation": organisation}


def _spec(**overrides):
    spec = {
        "call_day": "2025-08-01",
        "inspection_day": "2025-08-20",
        "attendees": [_attendee(), _attendee("manufacturer-quality", "supplier")],
        "offered": 400,
        "presented": 400,
        "requested_release": 400,
        "prerequisites": {
            "screening": "2025-08-10",
            "lot-acceptance": "2025-08-14",
        },
        "required_prerequisites": ("screening", "lot-acceptance"),
        "required_notice_days": 10,
        "open_major_nonconformances": 0,
    }
    spec.update(overrides)
    return spec


class NoticeTests(unittest.TestCase):
    def test_whole_days_of_notice_counted(self):
        self.assertEqual(notice_days("2025-08-01", "2025-08-20"), 19)

    def test_same_day_call_is_zero_notice(self):
        self.assertEqual(notice_days("2025-08-20", "2025-08-20"), 0)

    def test_notice_across_a_month_boundary(self):
        self.assertEqual(notice_days("2025-07-31", "2025-08-01"), 1)

    def test_session_before_the_call_refused(self):
        with self.assertRaises(ValueError):
            notice_days("2025-08-20", "2025-08-19")

    def test_malformed_day_refused(self):
        with self.assertRaises(ValueError):
            notice_days("01-08-2025", "2025-08-20")

    def test_default_notice_is_a_positive_whole_number_of_days(self):
        self.assertIsInstance(DEFAULT_NOTICE_DAYS, int)
        self.assertGreater(DEFAULT_NOTICE_DAYS, 0)

    def test_parse_day_accepts_iso_text(self):
        self.assertEqual(parse_day("day", "2025-08-20").day, 20)


class WitnessTests(unittest.TestCase):
    def test_entitled_attendee_makes_it_witnessed(self):
        record = witness_state([_attendee()])
        self.assertEqual(record["state"], "witnessed")
        self.assertTrue(record["admissible"])

    def test_delegated_inspector_is_entitled(self):
        record = witness_state([_attendee("delegated-inspector", "agency")])
        self.assertEqual(record["state"], "witnessed")

    def test_role_matching_ignores_letter_case(self):
        record = witness_state([_attendee("Procuring-Entity")])
        self.assertEqual(record["state"], "witnessed")

    def test_supplier_only_room_is_unwitnessed(self):
        record = witness_state([_attendee("manufacturer-quality", "supplier")])
        self.assertEqual(record["state"], "unwitnessed")
        self.assertFalse(record["admissible"])

    def test_empty_room_is_unwitnessed(self):
        self.assertEqual(witness_state([])["state"], "unwitnessed")

    def test_referenced_waiver_converts_an_unwitnessed_session(self):
        record = witness_state(
            [], waiver={"reference": "WV-2025-031", "reason": "travel embargo"}
        )
        self.assertEqual(record["state"], "witness-waived")
        self.assertTrue(record["admissible"])
        self.assertEqual(record["waiver_reference"], "WV-2025-031")

    def test_waiver_without_a_reference_refused(self):
        with self.assertRaises(ValueError):
            witness_state([], waiver={"reason": "travel embargo"})

    def test_waiver_without_a_reason_refused(self):
        with self.assertRaises(ValueError):
            witness_state([], waiver={"reference": "WV-2025-031"})

    def test_waiver_is_ignored_when_a_witness_did_attend(self):
        record = witness_state(
            [_attendee()], waiver={"reference": "WV-2025-031", "reason": "travel embargo"}
        )
        self.assertEqual(record["state"], "witnessed")
        self.assertIsNone(record["waiver_reference"])

    def test_attendee_without_an_organisation_refused(self):
        with self.assertRaises(ValueError):
            witness_state([{"role": "procuring-entity"}])

    def test_non_mapping_attendee_refused(self):
        with self.assertRaises(ValueError):
            witness_state(["procuring-entity"])

    def test_entitled_roles_are_named_not_open(self):
        self.assertIn("procuring-entity", WITNESS_ROLES)


class PrerequisiteTests(unittest.TestCase):
    def test_completed_prerequisites_are_in_sequence(self):
        record = prerequisite_findings(
            {"screening": "2025-08-10"}, "2025-08-20", ("screening",)
        )
        self.assertTrue(record["in_sequence"])
        self.assertEqual(record["findings"], [])

    def test_prerequisite_completing_on_the_day_is_in_sequence(self):
        record = prerequisite_findings({"screening": "2025-08-20"}, "2025-08-20")
        self.assertTrue(record["in_sequence"])

    def test_prerequisite_completing_after_the_session_is_out_of_sequence(self):
        record = prerequisite_findings({"screening": "2025-08-21"}, "2025-08-20")
        self.assertFalse(record["in_sequence"])
        self.assertIn("after the session", record["findings"][0])

    def test_open_prerequisite_raises_a_finding(self):
        record = prerequisite_findings({"screening": None}, "2025-08-20")
        self.assertFalse(record["in_sequence"])
        self.assertIn("has not completed", record["findings"][0])

    def test_absent_required_prerequisite_raises_a_finding(self):
        record = prerequisite_findings({}, "2025-08-20", ("lot-acceptance",))
        self.assertFalse(record["in_sequence"])
        self.assertIn("absent from the record", record["findings"][0])

    def test_non_mapping_prerequisites_refused(self):
        with self.assertRaises(ValueError):
            prerequisite_findings(["screening"], "2025-08-20")


class QuantityTests(unittest.TestCase):
    def test_full_presentation_releases_the_request(self):
        record = releasable_quantity(400, 400, 400)
        self.assertEqual(record["released"], 400)
        self.assertFalse(record["capped"])

    def test_release_capped_at_the_presented_quantity(self):
        record = releasable_quantity(400, 250, 400)
        self.assertEqual(record["released"], 250)
        self.assertEqual(record["withheld"], 150)
        self.assertTrue(record["capped"])

    def test_partial_request_below_the_presentation_is_untouched(self):
        record = releasable_quantity(400, 400, 120)
        self.assertEqual(record["released"], 120)
        self.assertFalse(record["capped"])

    def test_presenting_more_than_offered_refused(self):
        with self.assertRaises(ValueError):
            releasable_quantity(400, 401, 400)

    def test_requesting_more_than_offered_refused(self):
        with self.assertRaises(ValueError):
            releasable_quantity(400, 400, 401)

    def test_zero_offer_refused(self):
        with self.assertRaises(ValueError):
            releasable_quantity(0, 0, 0)

    def test_negative_presentation_refused(self):
        with self.assertRaises(ValueError):
            releasable_quantity(400, -1, 0)


class BuyOffDecisionTests(unittest.TestCase):
    def test_clean_session_releases_for_shipment(self):
        result = assess_buy_off(_spec())
        self.assertTrue(result["releasable"])
        self.assertEqual(result["disposition"], "release-for-shipment")
        self.assertEqual(result["released"], 400)
        self.assertEqual(result["findings"], [])

    def test_short_notice_holds_the_lot(self):
        result = assess_buy_off(_spec(call_day="2025-08-18"))
        self.assertFalse(result["releasable"])
        self.assertEqual(result["disposition"], "hold-at-manufacturer")
        self.assertTrue(any("short of the" in item for item in result["findings"]))

    def test_notice_exactly_at_the_required_period_releases(self):
        result = assess_buy_off(_spec(call_day="2025-08-10"))
        self.assertEqual(result["notice_days_given"], 10)
        self.assertTrue(result["releasable"])

    def test_unwitnessed_session_holds_the_lot(self):
        result = assess_buy_off(
            _spec(attendees=[_attendee("manufacturer-quality", "supplier")])
        )
        self.assertFalse(result["releasable"])
        self.assertTrue(any("no entitled witness" in item for item in result["findings"]))

    def test_referenced_waiver_releases_but_is_reported(self):
        result = assess_buy_off(
            _spec(
                attendees=[_attendee("manufacturer-quality", "supplier")],
                waiver={"reference": "WV-2025-031", "reason": "travel embargo"},
            )
        )
        self.assertTrue(result["releasable"])
        self.assertTrue(any("waived under WV-2025-031" in item for item in result["findings"]))

    def test_out_of_sequence_prerequisite_holds_the_lot(self):
        result = assess_buy_off(
            _spec(prerequisites={"screening": "2025-08-25", "lot-acceptance": "2025-08-14"})
        )
        self.assertFalse(result["releasable"])
        self.assertEqual(result["released"], 0)

    def test_open_major_nonconformance_holds_the_lot(self):
        result = assess_buy_off(_spec(open_major_nonconformances=2))
        self.assertFalse(result["releasable"])
        self.assertTrue(any("open major" in item for item in result["findings"]))

    def test_short_presentation_releases_only_what_was_seen(self):
        result = assess_buy_off(_spec(presented=250))
        self.assertTrue(result["releasable"])
        self.assertEqual(result["released"], 250)
        self.assertEqual(result["quantity"]["withheld"], 150)
        self.assertTrue(any("capped at the 250" in item for item in result["findings"]))

    def test_nothing_presented_releases_nothing(self):
        result = assess_buy_off(_spec(presented=0, requested_release=0))
        self.assertEqual(result["released"], 0)
        self.assertFalse(result["releasable"])

    def test_missing_attendees_key_refused(self):
        spec = _spec()
        del spec["attendees"]
        with self.assertRaises(ValueError):
            assess_buy_off(spec)

    def test_non_mapping_spec_refused(self):
        with self.assertRaises(ValueError):
            assess_buy_off(["call_day"])

    def test_findings_name_every_failing_gate_not_the_first(self):
        result = assess_buy_off(
            _spec(
                call_day="2025-08-19",
                attendees=[_attendee("manufacturer-quality", "supplier")],
                open_major_nonconformances=1,
            )
        )
        self.assertGreaterEqual(len(result["findings"]), 3)


if __name__ == "__main__":
    unittest.main()
