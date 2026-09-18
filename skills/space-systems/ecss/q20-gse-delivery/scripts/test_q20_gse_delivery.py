"""Contract tests for the clause 5.8.4.3-5.8.4.4 GSE delivery logic."""

import unittest
from datetime import date

from q20_gse_delivery_logic import (
    BASE_DELIVERY_DOCUMENTS,
    MANDATORY_AGENDA_ITEMS,
    MANDATORY_BOARD_FUNCTIONS,
    action_findings,
    assess_gse_delivery,
    board_decision,
    board_findings,
    certificate_findings,
    delivery_document_findings,
    normalize_token,
    parse_day,
    required_certificates,
    validate_actions,
    validate_board,
)

DELIVERY_DAY = "2026-05-14"

BOARD = {
    "chair_function": "quality-assurance",
    "attending_functions": list(MANDATORY_BOARD_FUNCTIONS),
    "agenda_items": list(MANDATORY_AGENDA_ITEMS),
    "reviewed_function": "gse-engineering",
}

ITEM = {"calibrated": True}

CERTIFICATES = [
    {
        "name": "certificate-of-conformity",
        "issued_on": "2026-05-02",
        "valid_until": "2027-05-02",
        "signatory": "quality-assurance",
    },
    {
        "name": "calibration-certificate",
        "issued_on": "2026-01-10",
        "valid_until": "2027-01-10",
        "signatory": "calibration-laboratory",
    },
]


def _spec(**overrides):
    board = dict(BOARD)
    board.update(overrides.pop("board", {}))
    spec = {
        "board": board,
        "actions": [],
        "item": dict(ITEM),
        "certificates": [dict(c) for c in CERTIFICATES],
        "delivery_date": DELIVERY_DAY,
        "carried_documents": list(BASE_DELIVERY_DOCUMENTS),
        "limitations_apply": False,
    }
    spec.update(overrides)
    return spec


class NormalizeAndDateTests(unittest.TestCase):
    def test_case_and_separator_folded(self):
        self.assertEqual(normalize_token("Quality_Assurance"), "quality-assurance")

    def test_iso_date_parsed(self):
        self.assertEqual(parse_day("2026-05-14"), date(2026, 5, 14))

    def test_date_object_passes_through(self):
        self.assertEqual(parse_day(date(2026, 5, 14)), date(2026, 5, 14))

    def test_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_day("14/05/2026")

    def test_non_string_date_rejected(self):
        with self.assertRaises(ValueError):
            parse_day(20260514)


class BoardTests(unittest.TestCase):
    def test_complete_board_is_clean(self):
        self.assertEqual(board_findings(BOARD), [])

    def test_absent_function_named(self):
        board = dict(BOARD, attending_functions=list(MANDATORY_BOARD_FUNCTIONS[:-1]))
        findings = board_findings(board)
        self.assertEqual(len(findings), 1)
        self.assertIn(MANDATORY_BOARD_FUNCTIONS[-1], findings[0])

    def test_chair_drawn_from_the_reviewed_function_is_a_finding(self):
        board = dict(BOARD, chair_function="gse-engineering")
        findings = board_findings(board)
        self.assertTrue(any("under review" in f for f in findings))

    def test_chair_not_in_the_room_is_a_finding(self):
        board = dict(BOARD, chair_function="programme-management")
        findings = board_findings(board)
        self.assertTrue(any("not listed among the attendees" in f for f in findings))

    def test_uncovered_agenda_item_named(self):
        board = dict(BOARD, agenda_items=list(MANDATORY_AGENDA_ITEMS[:-2]))
        findings = board_findings(board)
        self.assertEqual(len(findings), 2)

    def test_missing_board_key_rejected(self):
        board = dict(BOARD)
        del board["agenda_items"]
        with self.assertRaises(ValueError):
            validate_board(board)

    def test_non_sequence_attendance_rejected(self):
        with self.assertRaises(ValueError):
            validate_board(dict(BOARD, attending_functions="quality-assurance"))


class ActionTests(unittest.TestCase):
    def test_empty_action_list_gives_a_clean_delivery(self):
        self.assertEqual(action_findings([]), [])
        self.assertEqual(board_decision([]), "deliver")

    def test_open_blocking_action_holds_the_delivery(self):
        actions = [{"id": "ACT-1", "severity": "blocking", "state": "open"}]
        self.assertEqual(board_decision(actions), "hold")
        self.assertTrue(any("blocking action" in f for f in action_findings(actions)))

    def test_closed_blocking_action_does_not_hold(self):
        actions = [{"id": "ACT-1", "severity": "blocking", "state": "closed"}]
        self.assertEqual(board_decision(actions), "deliver")
        self.assertEqual(action_findings(actions), [])

    def test_open_standard_action_becomes_a_reservation(self):
        actions = [{"id": "ACT-2", "severity": "standard", "state": "open"}]
        self.assertEqual(board_decision(actions), "deliver-with-reservation")

    def test_open_action_due_before_delivery_is_a_finding(self):
        actions = [
            {
                "id": "ACT-3",
                "severity": "standard",
                "state": "open",
                "due_before_delivery": True,
            }
        ]
        self.assertTrue(any("due before delivery" in f for f in action_findings(actions)))

    def test_duplicate_action_identifier_rejected(self):
        actions = [
            {"id": "ACT-1", "severity": "standard", "state": "open"},
            {"id": "act 1", "severity": "standard", "state": "open"},
        ]
        with self.assertRaises(ValueError):
            validate_actions(actions)

    def test_unknown_severity_rejected(self):
        with self.assertRaises(ValueError):
            validate_actions([{"id": "ACT-1", "severity": "urgent", "state": "open"}])

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_actions([{"id": "ACT-1", "severity": "standard", "state": "pending"}])


class CertificateTests(unittest.TestCase):
    def test_plain_item_owes_only_the_conformity_certificate(self):
        self.assertEqual(required_certificates({}), ["certificate-of-conformity"])

    def test_each_state_adds_its_certificate(self):
        certificates = required_certificates(
            {"calibrated": True, "lifting_duty": True, "pressurised": True, "mains_powered": True}
        )
        self.assertEqual(len(certificates), 5)
        self.assertIn("proof-load-certificate", certificates)

    def test_non_boolean_state_rejected(self):
        with self.assertRaises(ValueError):
            required_certificates({"calibrated": "yes"})

    def test_valid_certificates_are_clean(self):
        required = required_certificates(ITEM)
        self.assertEqual(certificate_findings(CERTIFICATES, required, DELIVERY_DAY), [])

    def test_expired_certificate_named(self):
        certificates = [dict(CERTIFICATES[0]), dict(CERTIFICATES[1], valid_until="2026-02-01")]
        findings = certificate_findings(certificates, required_certificates(ITEM), DELIVERY_DAY)
        self.assertTrue(any("had expired" in f for f in findings))

    def test_certificate_valid_on_its_last_day_is_still_valid(self):
        certificates = [dict(CERTIFICATES[0], valid_until=DELIVERY_DAY)]
        findings = certificate_findings(certificates, ["certificate-of-conformity"], DELIVERY_DAY)
        self.assertEqual(findings, [])

    def test_certificate_dated_after_the_delivery_is_a_finding(self):
        certificates = [dict(CERTIFICATES[0], issued_on="2026-06-01", valid_until="2027-06-01")]
        findings = certificate_findings(certificates, ["certificate-of-conformity"], DELIVERY_DAY)
        self.assertTrue(any("dated after the delivery day" in f for f in findings))

    def test_unsigned_certificate_is_a_finding(self):
        certificates = [dict(CERTIFICATES[0])]
        del certificates[0]["signatory"]
        findings = certificate_findings(certificates, ["certificate-of-conformity"], DELIVERY_DAY)
        self.assertTrue(any("no signatory" in f for f in findings))

    def test_absent_certificate_named(self):
        findings = certificate_findings([], ["certificate-of-conformity"], DELIVERY_DAY)
        self.assertEqual(len(findings), 1)
        self.assertIn("no certificate-of-conformity", findings[0])

    def test_certificate_expiring_before_issue_rejected(self):
        certificates = [dict(CERTIFICATES[0], issued_on="2026-05-02", valid_until="2026-04-02")]
        with self.assertRaises(ValueError):
            certificate_findings(certificates, ["certificate-of-conformity"], DELIVERY_DAY)


class DeliveryDocumentTests(unittest.TestCase):
    def test_base_set_is_clean(self):
        self.assertEqual(delivery_document_findings(list(BASE_DELIVERY_DOCUMENTS), False), [])

    def test_limitations_add_the_limitations_notice(self):
        findings = delivery_document_findings(list(BASE_DELIVERY_DOCUMENTS), True)
        self.assertEqual(len(findings), 1)
        self.assertIn("operating-limitations-notice", findings[0])

    def test_case_difference_is_not_a_gap(self):
        self.assertEqual(
            delivery_document_findings(
                [d.replace("-", " ").title() for d in BASE_DELIVERY_DOCUMENTS], False
            ),
            [],
        )

    def test_non_sequence_rejected(self):
        with self.assertRaises(ValueError):
            delivery_document_findings("delivery-note", False)


class AssessGseDeliveryTests(unittest.TestCase):
    def test_clean_delivery_is_authorised(self):
        result = assess_gse_delivery(_spec())
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["board_decision"], "deliver")
        self.assertTrue(result["delivery_authorised"])

    def test_held_board_blocks_the_delivery(self):
        spec = _spec(actions=[{"id": "ACT-9", "severity": "blocking", "state": "open"}])
        result = assess_gse_delivery(spec)
        self.assertEqual(result["board_decision"], "hold")
        self.assertFalse(result["delivery_authorised"])

    def test_reservation_without_findings_still_authorises(self):
        spec = _spec(actions=[{"id": "ACT-8", "severity": "standard", "state": "open"}])
        result = assess_gse_delivery(spec)
        self.assertEqual(result["board_decision"], "deliver-with-reservation")
        self.assertTrue(result["delivery_authorised"])

    def test_expired_certificate_blocks_an_otherwise_clean_delivery(self):
        spec = _spec()
        spec["certificates"][1]["valid_until"] = "2026-03-01"
        result = assess_gse_delivery(spec)
        self.assertFalse(result["delivery_authorised"])
        self.assertEqual(len(result["certificate_findings"]), 1)

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["certificates"]
        with self.assertRaises(ValueError):
            assess_gse_delivery(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_gse_delivery(["board"])

    def test_findings_accumulate_across_every_check(self):
        spec = _spec(
            board={"attending_functions": ["quality-assurance"], "agenda_items": []},
            actions=[{"id": "ACT-1", "severity": "blocking", "state": "open"}],
            certificates=[],
            carried_documents=[],
            limitations_apply=True,
        )
        result = assess_gse_delivery(spec)
        self.assertFalse(result["delivery_authorised"])
        self.assertGreaterEqual(len(result["findings"]), 15)


if __name__ == "__main__":
    unittest.main()
