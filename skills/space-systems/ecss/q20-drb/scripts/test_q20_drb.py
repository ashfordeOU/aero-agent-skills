"""Contract tests for the clause 5.7.3 delivery review board logic."""

import unittest

from q20_drb_logic import (
    QUORUM_TOLERANCE,
    REQUIRED_BOARD_FUNCTIONS,
    REQUIRED_QUORUM_RATIO,
    assess_delivery_review,
    board_findings,
    combine_decision,
    data_package_findings,
    minute_findings,
    nonconformance_finding,
    nonconformance_findings,
    normalize_token,
    quorum_ratio,
    validate_board,
    waiver_findings,
)

FULL_BOARD = [{"function": f} for f in REQUIRED_BOARD_FUNCTIONS]

REQUIRED_PACK = [
    "end-item-data-package-index",
    "certificate-of-conformity",
    "as-built-configuration-list",
    "nonconformance-summary",
]

GOOD_MINUTES = {
    "date": "2026-09-18",
    "chair-function": "quality-assurance",
    "attendance": ["quality-assurance", "engineering"],
    "inputs-reviewed": ["eidp", "ncr-log"],
    "decision": "deliver",
    "actions": ["close ncr log"],
}


def _spec(**overrides):
    spec = {
        "members": [dict(m) for m in FULL_BOARD],
        "required_data_package": list(REQUIRED_PACK),
        "presented_data_package": list(REQUIRED_PACK),
        "nonconformances": [],
        "waivers": [],
        "minutes": dict(GOOD_MINUTES),
    }
    spec.update(overrides)
    return spec


class NormalizeTokenTests(unittest.TestCase):
    def test_case_and_spacing_folded(self):
        self.assertEqual(normalize_token("  Quality  Assurance "), "quality-assurance")

    def test_underscores_and_hyphens_agree(self):
        self.assertEqual(normalize_token("customer_representative"), "customer-representative")

    def test_blank_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token("   ")

    def test_non_string_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token(7)


class ValidateBoardTests(unittest.TestCase):
    def test_roster_defaults_to_present_and_independent(self):
        roster = validate_board([{"function": "engineering"}])
        self.assertEqual(roster[0]["function"], "engineering")
        self.assertTrue(roster[0]["present"])
        self.assertTrue(roster[0]["independent"])

    def test_empty_board_rejected(self):
        with self.assertRaises(ValueError):
            validate_board([])

    def test_duplicate_function_rejected(self):
        with self.assertRaises(ValueError):
            validate_board([{"function": "engineering"}, {"function": "Engineering"}])

    def test_missing_function_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_board([{"present": True}])

    def test_non_boolean_present_rejected(self):
        with self.assertRaises(ValueError):
            validate_board([{"function": "engineering", "present": "yes"}])


class QuorumTests(unittest.TestCase):
    def test_full_board_is_unity(self):
        roster = validate_board(FULL_BOARD)
        self.assertAlmostEqual(quorum_ratio(roster), REQUIRED_QUORUM_RATIO, places=9)

    def test_one_absentee_drops_the_ratio(self):
        members = [dict(m) for m in FULL_BOARD]
        members[0]["present"] = False
        roster = validate_board(members)
        self.assertAlmostEqual(quorum_ratio(roster), 4.0 / 5.0, places=9)

    def test_extra_observer_does_not_raise_the_ratio(self):
        roster = validate_board(FULL_BOARD + [{"function": "safety"}])
        self.assertAlmostEqual(quorum_ratio(roster), REQUIRED_QUORUM_RATIO, places=9)

    def test_empty_required_set_rejected(self):
        roster = validate_board(FULL_BOARD)
        with self.assertRaises(ValueError):
            quorum_ratio(roster, [])

    def test_tolerance_is_small(self):
        self.assertLess(QUORUM_TOLERANCE, 1e-6)


class BoardFindingTests(unittest.TestCase):
    def test_full_independent_board_is_clean(self):
        self.assertEqual(board_findings(validate_board(FULL_BOARD)), [])

    def test_unseated_function_named(self):
        roster = validate_board([{"function": f} for f in REQUIRED_BOARD_FUNCTIONS[:-1]])
        findings = board_findings(roster)
        self.assertTrue(any("customer-representative" in f for f in findings))

    def test_seated_but_absent_is_a_different_finding(self):
        members = [dict(m) for m in FULL_BOARD]
        members[-1]["present"] = False
        findings = board_findings(validate_board(members))
        self.assertTrue(any("did not attend" in f for f in findings))

    def test_dependent_quality_member_is_a_finding(self):
        members = [dict(m) for m in FULL_BOARD]
        members[0]["independent"] = False
        findings = board_findings(validate_board(members))
        self.assertTrue(any("not independent" in f for f in findings))


class DataPackageTests(unittest.TestCase):
    def test_complete_pack_is_clean(self):
        self.assertEqual(data_package_findings(REQUIRED_PACK, REQUIRED_PACK), [])

    def test_missing_document_named(self):
        findings = data_package_findings(REQUIRED_PACK[:-1], REQUIRED_PACK)
        self.assertEqual(len(findings), 1)
        self.assertIn("nonconformance-summary", findings[0])

    def test_case_difference_is_not_a_gap(self):
        self.assertEqual(
            data_package_findings(["Certificate Of Conformity"], ["certificate-of-conformity"]), []
        )

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            data_package_findings("certificate-of-conformity", REQUIRED_PACK)


class NonconformanceTests(unittest.TestCase):
    def test_closed_record_yields_nothing(self):
        self.assertEqual(nonconformance_finding({"id": "n1", "category": "major", "status": "closed"}), (None, None))

    def test_open_without_disposition_blocks(self):
        severity, _ = nonconformance_finding({"id": "n2", "category": "minor", "status": "open"})
        self.assertEqual(severity, "blocking")

    def test_major_use_as_is_without_agreement_blocks(self):
        severity, message = nonconformance_finding(
            {"id": "n3", "category": "major", "status": "open", "disposition": "use-as-is"}
        )
        self.assertEqual(severity, "blocking")
        self.assertIn("customer agreement", message)

    def test_major_use_as_is_with_agreement_is_a_reservation(self):
        severity, _ = nonconformance_finding(
            {
                "id": "n4",
                "category": "major",
                "status": "open",
                "disposition": "use-as-is",
                "customer_approved": True,
            }
        )
        self.assertEqual(severity, "reservation")

    def test_minor_repair_is_a_reservation_without_agreement(self):
        severity, _ = nonconformance_finding(
            {"id": "n5", "category": "minor", "status": "open", "disposition": "repair"}
        )
        self.assertEqual(severity, "reservation")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            nonconformance_finding({"id": "n6", "category": "critical", "status": "open"})

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            nonconformance_finding(
                {"id": "n7", "category": "minor", "status": "open", "disposition": "ignore"}
            )

    def test_set_is_grouped_into_blocking_and_reservations(self):
        grouped = nonconformance_findings(
            [
                {"id": "a", "category": "major", "status": "closed"},
                {"id": "b", "category": "minor", "status": "open", "disposition": "rework"},
                {"id": "c", "category": "major", "status": "open", "disposition": "repair"},
            ]
        )
        self.assertEqual(len(grouped["blocking"]), 1)
        self.assertEqual(len(grouped["reservations"]), 1)

    def test_none_set_is_empty(self):
        grouped = nonconformance_findings(None)
        self.assertEqual(grouped, {"blocking": [], "reservations": []})


class WaiverTests(unittest.TestCase):
    def test_approved_waiver_is_a_reservation(self):
        grouped = waiver_findings([{"id": "w1", "approved": True}])
        self.assertEqual(grouped["blocking"], [])
        self.assertEqual(len(grouped["reservations"]), 1)

    def test_unapproved_waiver_blocks(self):
        grouped = waiver_findings([{"id": "w2", "approved": False}])
        self.assertEqual(len(grouped["blocking"]), 1)

    def test_lapsed_waiver_blocks_even_when_approved(self):
        grouped = waiver_findings([{"id": "w3", "approved": True, "expired": True}])
        self.assertIn("lapsed", grouped["blocking"][0])

    def test_missing_id_rejected(self):
        with self.assertRaises(ValueError):
            waiver_findings([{"approved": True}])


class MinuteTests(unittest.TestCase):
    def test_full_minutes_are_clean(self):
        self.assertEqual(minute_findings(GOOD_MINUTES), [])

    def test_blank_field_is_a_finding(self):
        minutes = dict(GOOD_MINUTES)
        minutes["actions"] = "   "
        self.assertEqual(len(minute_findings(minutes)), 1)

    def test_empty_attendance_list_is_a_finding(self):
        minutes = dict(GOOD_MINUTES)
        minutes["attendance"] = []
        self.assertTrue(any("attendance" in f for f in minute_findings(minutes)))

    def test_non_mapping_minutes_rejected(self):
        with self.assertRaises(ValueError):
            minute_findings(["date"])


class CombineTests(unittest.TestCase):
    def test_clean_board_delivers(self):
        self.assertEqual(combine_decision([], []), "deliver")

    def test_reservation_only_delivers_with_reservation(self):
        self.assertEqual(combine_decision([], ["waiver w1"]), "deliver-with-reservation")

    def test_blocking_holds_even_with_reservations(self):
        self.assertEqual(combine_decision(["missing doc"], ["waiver w1"]), "hold")

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            combine_decision("missing doc", [])


class AssessDeliveryReviewTests(unittest.TestCase):
    def test_clean_board_returns_deliver(self):
        result = assess_delivery_review(_spec())
        self.assertEqual(result["decision"], "deliver")
        self.assertTrue(result["deliverable"])
        self.assertAlmostEqual(result["quorum_ratio"], 1.0, places=9)

    def test_missing_document_holds_the_delivery(self):
        result = assess_delivery_review(_spec(presented_data_package=REQUIRED_PACK[:2]))
        self.assertEqual(result["decision"], "hold")
        self.assertEqual(len(result["data_package_findings"]), 2)

    def test_approved_waiver_yields_reservation_not_hold(self):
        result = assess_delivery_review(_spec(waivers=[{"id": "w9", "approved": True}]))
        self.assertEqual(result["decision"], "deliver-with-reservation")
        self.assertTrue(result["deliverable"])

    def test_absent_member_holds_the_delivery(self):
        members = [dict(m) for m in FULL_BOARD]
        members[2]["present"] = False
        result = assess_delivery_review(_spec(members=members))
        self.assertEqual(result["decision"], "hold")

    def test_empty_minutes_hold_the_delivery(self):
        result = assess_delivery_review(_spec(minutes={}))
        self.assertEqual(result["decision"], "hold")
        self.assertEqual(len(result["record_findings"]), 6)

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["required_data_package"]
        with self.assertRaises(ValueError):
            assess_delivery_review(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_delivery_review(["members"])

    def test_findings_are_reported_together_not_at_first_failure(self):
        result = assess_delivery_review(
            _spec(
                presented_data_package=[],
                waivers=[{"id": "w4", "approved": False}],
                nonconformances=[{"id": "n8", "category": "minor", "status": "open"}],
            )
        )
        self.assertGreaterEqual(len(result["blocking"]), 6)


if __name__ == "__main__":
    unittest.main()
