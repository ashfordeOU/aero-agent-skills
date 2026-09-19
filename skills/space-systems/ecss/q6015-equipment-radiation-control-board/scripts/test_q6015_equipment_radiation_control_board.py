"""Contract test for the equipment radiation control board leaf."""

import unittest

from q6015_equipment_radiation_control_board_logic import (
    FINDING_ACTION_NO_OWNER,
    FINDING_ACTION_OVERDUE,
    FINDING_ANALYSIS_MISSING,
    FINDING_ANALYSIS_NO_EVIDENCE,
    FINDING_ANALYSIS_NO_MARGIN,
    FINDING_ANALYSIS_ORPHAN,
    FINDING_CHAIR_NOT_INDEPENDENT,
    FINDING_MULTIPLE_CHAIRS,
    FINDING_NO_CHAIR,
    FINDING_QUORUM,
    FINDING_ROLE_MISSING,
    FINDING_SHORTFALL_NO_ACTION,
    MANDATORY_ROLES,
    VERDICT_CLEARED,
    VERDICT_CLEARED_WITH_ACTIONS,
    VERDICT_NOT_CLEARED,
    action_findings,
    analysis_findings,
    board_can_sit,
    board_composition_findings,
    coverage_findings,
    margin_meets_requirement,
    review_radiation_control_board,
    validate_action,
    validate_analysis,
    validate_board_members,
    validate_member,
    validate_part,
)

BOARD_DATE = "2026-05-12"


def members(**overrides):
    base = [
        {"id": "M1", "role": "radiation-effects-engineer", "chair": True},
        {"id": "M2", "role": "product-assurance"},
        {"id": "M3", "role": "design-authority"},
        {"id": "M4", "role": "component-engineer"},
        {"id": "M5", "role": "customer-representative"},
    ]
    for member in base:
        member.update(overrides.get(member["id"], {}))
    return base


def parts():
    return [
        {"id": "U1", "effects": ["total-ionising-dose", "single-event"]},
        {"id": "U2", "effects": ["total-ionising-dose"]},
    ]


def analyses():
    return [
        {
            "part_id": "U1",
            "effect": "total-ionising-dose",
            "margin": 3.0,
            "required_margin": 2.0,
            "evidence_reference": "RAD-TR-011",
        },
        {
            "part_id": "U1",
            "effect": "single-event",
            "margin": 4.0,
            "required_margin": 2.0,
            "evidence_reference": "RAD-TR-012",
        },
        {
            "part_id": "U2",
            "effect": "total-ionising-dose",
            "margin": 2.0,
            "required_margin": 2.0,
            "evidence_reference": "RAD-TR-013",
        },
    ]


def board(**kw):
    record = {
        "board_date": BOARD_DATE,
        "members": members(),
        "parts": parts(),
        "analyses": analyses(),
        "actions": [],
    }
    record.update(kw)
    return record


class TestMemberValidation(unittest.TestCase):
    def test_defaults_put_a_member_in_the_room(self):
        record = validate_member({"id": "M1", "role": "product-assurance"})
        self.assertTrue(record["present"])
        self.assertFalse(record["chair"])

    def test_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            validate_member({"id": "M1", "role": "catering"})

    def test_non_boolean_present_raises(self):
        with self.assertRaises(ValueError):
            validate_member({"id": "M1", "role": "product-assurance", "present": "yes"})

    def test_duplicate_member_id_raises(self):
        with self.assertRaises(ValueError):
            validate_board_members(
                [
                    {"id": "M1", "role": "product-assurance"},
                    {"id": "M1", "role": "component-engineer"},
                ]
            )

    def test_empty_member_list_raises(self):
        with self.assertRaises(ValueError):
            validate_board_members([])


class TestBoardComposition(unittest.TestCase):
    def test_a_full_board_can_sit(self):
        self.assertTrue(board_can_sit(members()))

    def test_missing_mandatory_role_is_a_finding(self):
        short = [m for m in members() if m["role"] != "component-engineer"]
        findings = board_composition_findings(short)
        self.assertIn(
            "%s:component-engineer" % FINDING_ROLE_MISSING, findings
        )

    def test_absent_member_does_not_represent_a_role(self):
        findings = board_composition_findings(
            members(M2={"present": False})
        )
        self.assertIn("%s:product-assurance" % FINDING_ROLE_MISSING, findings)
        self.assertIn(FINDING_QUORUM, findings)

    def test_no_chair_is_a_finding(self):
        findings = board_composition_findings(members(M1={"chair": False}))
        self.assertIn(FINDING_NO_CHAIR, findings)

    def test_two_chairs_is_a_finding(self):
        findings = board_composition_findings(members(M2={"chair": True}))
        self.assertIn(FINDING_MULTIPLE_CHAIRS, findings)

    def test_design_authority_may_not_chair(self):
        findings = board_composition_findings(
            members(M1={"chair": False}, M3={"chair": True})
        )
        self.assertIn(FINDING_CHAIR_NOT_INDEPENDENT, findings)

    def test_every_mandatory_role_is_checked(self):
        self.assertEqual(len(MANDATORY_ROLES), 5)


class TestCoverage(unittest.TestCase):
    def test_full_coverage_has_no_findings(self):
        self.assertEqual(coverage_findings(parts(), analyses()), [])

    def test_missing_analysis_is_a_finding(self):
        short = [a for a in analyses() if a["effect"] != "single-event"]
        findings = coverage_findings(parts(), short)
        self.assertIn(
            "%s:U1/single-event" % FINDING_ANALYSIS_MISSING, findings
        )

    def test_analysis_for_an_unlisted_part_is_a_finding(self):
        extra = analyses() + [
            {
                "part_id": "U9",
                "effect": "total-ionising-dose",
                "margin": 5.0,
                "required_margin": 2.0,
                "evidence_reference": "RAD-TR-099",
            }
        ]
        findings = coverage_findings(parts(), extra)
        self.assertIn("%s:U9" % FINDING_ANALYSIS_ORPHAN, findings)

    def test_unknown_effect_on_a_part_raises(self):
        with self.assertRaises(ValueError):
            validate_part({"id": "U1", "effects": ["cosmic-vibes"]})

    def test_empty_parts_list_raises(self):
        with self.assertRaises(ValueError):
            coverage_findings([], analyses())


class TestAnalysisFindings(unittest.TestCase):
    def test_complete_dossier_has_no_findings(self):
        self.assertEqual(analysis_findings(analyses(), []), [])

    def test_margin_exactly_at_requirement_passes(self):
        self.assertTrue(margin_meets_requirement(2.0, 2.0))

    def test_analysis_without_a_margin_is_a_finding(self):
        records = analyses()
        records[0]["margin"] = None
        findings = analysis_findings(records, [])
        self.assertIn(
            "%s:U1/total-ionising-dose" % FINDING_ANALYSIS_NO_MARGIN, findings
        )

    def test_analysis_without_evidence_is_a_finding(self):
        records = analyses()
        records[1]["evidence_reference"] = None
        findings = analysis_findings(records, [])
        self.assertIn(
            "%s:U1/single-event" % FINDING_ANALYSIS_NO_EVIDENCE, findings
        )

    def test_shortfall_without_an_action_is_a_finding(self):
        records = analyses()
        records[2]["margin"] = 1.2
        findings = analysis_findings(records, [])
        self.assertIn(
            "%s:U2/total-ionising-dose" % FINDING_SHORTFALL_NO_ACTION, findings
        )

    def test_shortfall_with_an_action_is_accepted(self):
        records = analyses()
        records[2]["margin"] = 1.2
        actions = [
            {
                "id": "A1",
                "subject": "U2/total-ionising-dose",
                "owner": "component engineering",
                "due_date": "2026-07-01",
                "status": "open",
            }
        ]
        self.assertEqual(analysis_findings(records, actions), [])

    def test_blank_evidence_reference_raises(self):
        with self.assertRaises(ValueError):
            validate_analysis(
                {
                    "part_id": "U1",
                    "effect": "single-event",
                    "margin": 2.0,
                    "required_margin": 2.0,
                    "evidence_reference": "   ",
                }
            )

    def test_non_positive_required_margin_raises(self):
        with self.assertRaises(ValueError):
            validate_analysis(
                {
                    "part_id": "U1",
                    "effect": "single-event",
                    "margin": 2.0,
                    "required_margin": 0.0,
                }
            )


class TestActionFindings(unittest.TestCase):
    def test_action_without_an_owner_is_a_finding(self):
        actions = [
            {
                "id": "A1",
                "subject": "U2/total-ionising-dose",
                "due_date": "2026-07-01",
                "status": "open",
            }
        ]
        self.assertIn(
            "%s:A1" % FINDING_ACTION_NO_OWNER, action_findings(actions, BOARD_DATE)
        )

    def test_open_action_past_its_date_is_a_finding(self):
        actions = [
            {
                "id": "A2",
                "subject": "U1/single-event",
                "owner": "radiation effects",
                "due_date": "2026-01-05",
                "status": "open",
            }
        ]
        self.assertIn(
            "%s:A2" % FINDING_ACTION_OVERDUE, action_findings(actions, BOARD_DATE)
        )

    def test_closed_action_past_its_date_is_not_overdue(self):
        actions = [
            {
                "id": "A3",
                "subject": "U1/single-event",
                "owner": "radiation effects",
                "due_date": "2026-01-05",
                "status": "closed",
            }
        ]
        self.assertEqual(action_findings(actions, BOARD_DATE), [])

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            validate_action(
                {
                    "id": "A4",
                    "subject": "U1/single-event",
                    "owner": "x",
                    "due_date": "2026-01-05",
                    "status": "maybe",
                }
            )

    def test_malformed_due_date_raises(self):
        with self.assertRaises(ValueError):
            validate_action(
                {
                    "id": "A5",
                    "subject": "U1/single-event",
                    "owner": "x",
                    "due_date": "12 May 2026",
                    "status": "open",
                }
            )


class TestBoardReview(unittest.TestCase):
    def test_a_clean_dossier_is_cleared(self):
        report = review_radiation_control_board(board())
        self.assertEqual(report["verdict"], VERDICT_CLEARED)
        self.assertTrue(report["cleared"])

    def test_open_actions_downgrade_a_clean_board(self):
        records = analyses()
        records[2]["margin"] = 1.2
        report = review_radiation_control_board(
            board(
                analyses=records,
                actions=[
                    {
                        "id": "A1",
                        "subject": "U2/total-ionising-dose",
                        "owner": "component engineering",
                        "due_date": "2026-07-01",
                        "status": "open",
                    }
                ],
            )
        )
        self.assertEqual(report["verdict"], VERDICT_CLEARED_WITH_ACTIONS)
        self.assertEqual(report["open_action_ids"], ["A1"])

    def test_a_coverage_hole_blocks_clearance(self):
        short = [a for a in analyses() if a["effect"] != "single-event"]
        report = review_radiation_control_board(board(analyses=short))
        self.assertEqual(report["verdict"], VERDICT_NOT_CLEARED)
        self.assertFalse(report["cleared"])

    def test_a_badly_chaired_board_cannot_clear(self):
        report = review_radiation_control_board(
            board(members=members(M1={"chair": False}, M3={"chair": True}))
        )
        self.assertIn(FINDING_CHAIR_NOT_INDEPENDENT, report["composition_findings"])
        self.assertEqual(report["verdict"], VERDICT_NOT_CLEARED)

    def test_findings_are_the_concatenation_of_the_four_checks(self):
        report = review_radiation_control_board(board())
        self.assertEqual(
            report["findings"],
            report["composition_findings"]
            + report["coverage_findings"]
            + report["analysis_findings"]
            + report["action_findings"],
        )

    def test_missing_parts_list_raises(self):
        with self.assertRaises(ValueError):
            review_radiation_control_board(board(parts=[]))

    def test_non_mapping_board_raises(self):
        with self.assertRaises(ValueError):
            review_radiation_control_board(["M1"])

    def test_missing_board_date_raises(self):
        record = board()
        del record["board_date"]
        with self.assertRaises(ValueError):
            review_radiation_control_board(record)


if __name__ == "__main__":
    unittest.main()
