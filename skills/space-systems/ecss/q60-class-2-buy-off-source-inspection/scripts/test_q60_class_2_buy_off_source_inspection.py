"""Contract tests for the clause 5.3.6 Class 2 source buy-off logic.

The cases walk the decision one step at a time: the mode the session was held
in, the notice that mode owed, who in the room could act for the procuring
entity and whether a delegate was independent of the line that built the parts,
the acceptance data package, the activities the buy-off sits on, and the cap the
presented quantity puts on the release. Each step is exercised on both sides of
its limit so the record shows what was judged, not only the verdict.
"""

import unittest

from q60_class_2_buy_off_source_inspection_logic import (
    BUY_OFF_MODES,
    DEFAULT_NOTICE_DAYS,
    DELEGATE_ROLES,
    PROCURING_ROLES,
    REQUIRED_PACKAGE_DOCUMENTS,
    assess_buy_off,
    attendance_state,
    delegate_independence,
    normalize_mode,
    notice_days,
    package_findings,
    parse_day,
    prerequisite_findings,
    releasable_quantity,
)

SESSION = "2025-09-15"
FULL_PACKAGE = list(REQUIRED_PACKAGE_DOCUMENTS)


def _spec(**overrides):
    spec = {
        "mode": "on-site-witnessed",
        "call_day": "2025-09-01",
        "session_day": SESSION,
        "offered_quantity": 500,
        "presented_quantity": 500,
        "attendees": [{"role": "procuring-entity", "name": "K. Aalto"}],
        "documents": list(FULL_PACKAGE),
        "prerequisites": [{"activity": "screening", "completed_day": "2025-09-10"}],
        "manufacturer_audit_current": True,
    }
    spec.update(overrides)
    return spec


class ModeTests(unittest.TestCase):
    def test_mode_normalized(self):
        self.assertEqual(normalize_mode("  On-Site-Witnessed "), "on-site-witnessed")

    def test_every_mode_admissible(self):
        for mode in BUY_OFF_MODES:
            self.assertEqual(normalize_mode(mode), mode)

    def test_unknown_mode_refused(self):
        with self.assertRaises(ValueError):
            normalize_mode("postal-review")

    def test_non_string_mode_refused(self):
        with self.assertRaises(ValueError):
            normalize_mode(3)

    def test_every_mode_has_a_notice_period(self):
        self.assertEqual(set(DEFAULT_NOTICE_DAYS), set(BUY_OFF_MODES))

    def test_on_site_is_called_earliest(self):
        self.assertGreater(
            DEFAULT_NOTICE_DAYS["on-site-witnessed"],
            DEFAULT_NOTICE_DAYS["documentation-review"],
        )


class NoticeTests(unittest.TestCase):
    def test_whole_days_counted(self):
        self.assertEqual(notice_days("2025-09-01", "2025-09-15"), 14)

    def test_same_day_call_is_zero_notice(self):
        self.assertEqual(notice_days(SESSION, SESSION), 0)

    def test_session_before_the_call_refused(self):
        with self.assertRaises(ValueError):
            notice_days("2025-09-16", SESSION)

    def test_malformed_day_refused(self):
        with self.assertRaises(ValueError):
            parse_day("call_day", "15-09-2025")


class IndependenceTests(unittest.TestCase):
    def test_delegate_clear_of_production_is_independent(self):
        independent, reason = delegate_independence(
            {"role": "delegated-inspector", "reports_to": "corporate-quality"}
        )
        self.assertTrue(independent)
        self.assertIn("clear of the build organisation", reason)

    def test_delegate_reporting_into_production_is_not_independent(self):
        independent, reason = delegate_independence(
            {"role": "delegated-inspector", "reports_to": "production"}
        )
        self.assertFalse(independent)
        self.assertIn("built the parts", reason)

    def test_reporting_line_matched_within_a_longer_title(self):
        independent, _ = delegate_independence(
            {"role": "independent-quality-assurance", "reports_to": "Head of Assembly-Line Ops"}
        )
        self.assertFalse(independent)

    def test_undeclared_reporting_line_is_not_independence(self):
        independent, reason = delegate_independence({"role": "delegated-inspector"})
        self.assertFalse(independent)
        self.assertIn("no declared reporting line", reason)

    def test_non_delegate_role_refused(self):
        with self.assertRaises(ValueError):
            delegate_independence({"role": "procuring-entity"})

    def test_non_mapping_attendee_refused(self):
        with self.assertRaises(ValueError):
            delegate_independence("delegated-inspector")


class AttendanceTests(unittest.TestCase):
    def test_procuring_entity_needs_no_independence_argument(self):
        state = attendance_state([{"role": "procuring-entity", "name": "K. Aalto"}])
        self.assertTrue(state["witnessed"])
        self.assertEqual(state["procuring"], ["K. Aalto"])

    def test_independent_delegate_acts_for_the_procuring_entity(self):
        state = attendance_state(
            [{"role": "delegated-inspector", "name": "R. Sole", "reports_to": "corporate-quality"}]
        )
        self.assertTrue(state["witnessed"])
        self.assertEqual(state["delegates"], ["R. Sole"])

    def test_dependent_delegate_is_set_aside_with_a_reason(self):
        state = attendance_state(
            [{"role": "delegated-inspector", "name": "R. Sole", "reports_to": "production"}]
        )
        self.assertFalse(state["witnessed"])
        self.assertEqual(len(state["rejected"]), 1)
        self.assertIn("R. Sole", state["rejected"][0])

    def test_manufacturer_staff_alone_is_not_a_witness(self):
        state = attendance_state([{"role": "manufacturer-quality", "name": "T. Voss"}])
        self.assertFalse(state["witnessed"])

    def test_empty_room_is_not_a_witness(self):
        self.assertFalse(attendance_state([])["witnessed"])

    def test_missing_attendees_treated_as_empty(self):
        self.assertFalse(attendance_state(None)["witnessed"])

    def test_attendee_without_a_role_refused(self):
        with self.assertRaises(ValueError):
            attendance_state([{"name": "K. Aalto"}])

    def test_role_tables_do_not_overlap(self):
        self.assertFalse(set(PROCURING_ROLES) & set(DELEGATE_ROLES))


class PackageTests(unittest.TestCase):
    def test_complete_package_has_no_findings(self):
        self.assertEqual(package_findings(FULL_PACKAGE), [])

    def test_missing_document_named(self):
        held = [d for d in FULL_PACKAGE if d != "screening-data"]
        self.assertEqual(package_findings(held), ["screening-data"])

    def test_document_names_are_case_insensitive(self):
        self.assertEqual(package_findings([d.upper() for d in FULL_PACKAGE]), [])

    def test_empty_package_names_every_document(self):
        self.assertEqual(len(package_findings([])), len(REQUIRED_PACKAGE_DOCUMENTS))

    def test_non_sequence_package_refused(self):
        with self.assertRaises(ValueError):
            package_findings("certificate-of-conformity")


class PrerequisiteTests(unittest.TestCase):
    def test_activity_completed_before_the_session_passes(self):
        findings = prerequisite_findings(
            [{"activity": "screening", "completed_day": "2025-09-10"}], SESSION
        )
        self.assertEqual(findings, [])

    def test_activity_completed_on_the_session_day_passes(self):
        findings = prerequisite_findings(
            [{"activity": "screening", "completed_day": SESSION}], SESSION
        )
        self.assertEqual(findings, [])

    def test_activity_completed_after_the_session_is_a_finding(self):
        findings = prerequisite_findings(
            [{"activity": "screening", "completed_day": "2025-09-16"}], SESSION
        )
        self.assertEqual(len(findings), 1)
        self.assertIn("after the session", findings[0])

    def test_open_activity_is_a_finding(self):
        findings = prerequisite_findings([{"activity": "screening"}], SESSION)
        self.assertIn("had not completed", findings[0])

    def test_prerequisite_without_an_activity_refused(self):
        with self.assertRaises(ValueError):
            prerequisite_findings([{"completed_day": SESSION}], SESSION)


class ReleaseQuantityTests(unittest.TestCase):
    def test_whole_lot_presented_releases_the_lot(self):
        self.assertEqual(releasable_quantity(500, 500), 500)

    def test_release_capped_at_the_pieces_presented(self):
        self.assertEqual(releasable_quantity(500, 300), 300)

    def test_release_capped_at_what_was_requested(self):
        self.assertEqual(releasable_quantity(500, 500, 200), 200)

    def test_presented_above_the_lot_refused(self):
        with self.assertRaises(ValueError):
            releasable_quantity(500, 501)

    def test_zero_lot_refused(self):
        with self.assertRaises(ValueError):
            releasable_quantity(0, 0)

    def test_zero_request_refused(self):
        with self.assertRaises(ValueError):
            releasable_quantity(500, 500, 0)


class BuyOffAssessmentTests(unittest.TestCase):
    def test_clean_witnessed_session_releases_the_lot(self):
        result = assess_buy_off(_spec())
        self.assertEqual(result["disposition"], "release-full-lot")
        self.assertEqual(result["released_quantity"], 500)
        self.assertEqual(result["blocking"], [])

    def test_short_notice_holds_the_lot(self):
        result = assess_buy_off(_spec(call_day="2025-09-14"))
        self.assertEqual(result["disposition"], "hold")
        self.assertEqual(result["released_quantity"], 0)
        self.assertIn("requires", result["blocking"][0])

    def test_remote_session_admissible_on_shorter_notice(self):
        result = assess_buy_off(_spec(mode="remote-witnessed", call_day="2025-09-09"))
        self.assertEqual(result["disposition"], "release-full-lot")

    def test_same_notice_fails_the_on_site_mode(self):
        result = assess_buy_off(_spec(mode="on-site-witnessed", call_day="2025-09-09"))
        self.assertEqual(result["disposition"], "hold")

    def test_unwitnessed_session_holds_the_lot(self):
        result = assess_buy_off(_spec(attendees=[{"role": "manufacturer-quality"}]))
        self.assertEqual(result["disposition"], "hold")
        self.assertFalse(result["witnessed"])

    def test_delegated_mode_needs_an_independent_inspector(self):
        result = assess_buy_off(
            _spec(
                mode="delegated",
                call_day="2025-09-09",
                attendees=[{"role": "delegated-inspector", "reports_to": "production"}],
            )
        )
        self.assertEqual(result["disposition"], "hold")
        self.assertTrue(any("independent" in item for item in result["blocking"]))

    def test_delegated_mode_releases_on_an_independent_inspector(self):
        result = assess_buy_off(
            _spec(
                mode="delegated",
                call_day="2025-09-09",
                attendees=[
                    {"role": "delegated-inspector", "name": "R. Sole", "reports_to": "corporate-quality"}
                ],
            )
        )
        self.assertEqual(result["disposition"], "release-full-lot")
        self.assertEqual(result["acting_for_procuring_entity"], ["R. Sole"])

    def test_documentation_review_needs_a_current_audit(self):
        result = assess_buy_off(
            _spec(
                mode="documentation-review",
                call_day="2025-09-12",
                attendees=[],
                manufacturer_audit_current=False,
            )
        )
        self.assertEqual(result["disposition"], "hold")
        self.assertTrue(any("audit is current" in item for item in result["blocking"]))

    def test_documentation_review_releases_without_a_room(self):
        result = assess_buy_off(
            _spec(mode="documentation-review", call_day="2025-09-12", attendees=[])
        )
        self.assertEqual(result["disposition"], "release-full-lot")
        self.assertFalse(result["witnessed"])

    def test_missing_document_holds_a_witnessed_session(self):
        held = [d for d in FULL_PACKAGE if d != "lot-acceptance-report"]
        result = assess_buy_off(_spec(documents=held))
        self.assertEqual(result["disposition"], "hold")
        self.assertEqual(result["missing_documents"], ["lot-acceptance-report"])

    def test_open_prerequisite_holds_the_lot(self):
        result = assess_buy_off(_spec(prerequisites=[{"activity": "screening"}]))
        self.assertEqual(result["disposition"], "hold")

    def test_part_presented_lot_releases_only_what_was_seen(self):
        result = assess_buy_off(_spec(presented_quantity=300))
        self.assertEqual(result["disposition"], "release-part-lot")
        self.assertEqual(result["released_quantity"], 300)
        self.assertEqual(result["withheld_quantity"], 200)

    def test_dependent_delegate_reported_as_advisory_when_others_witnessed(self):
        result = assess_buy_off(
            _spec(
                attendees=[
                    {"role": "procuring-entity", "name": "K. Aalto"},
                    {"role": "delegated-inspector", "name": "R. Sole", "reports_to": "production"},
                ]
            )
        )
        self.assertEqual(result["disposition"], "release-full-lot")
        self.assertTrue(any("R. Sole" in item for item in result["advisory"]))

    def test_hold_releases_no_pieces_at_all(self):
        result = assess_buy_off(_spec(call_day="2025-09-14", presented_quantity=300))
        self.assertEqual(result["released_quantity"], 0)
        self.assertEqual(result["withheld_quantity"], 500)

    def test_missing_spec_key_refused(self):
        spec = _spec()
        del spec["mode"]
        with self.assertRaises(ValueError):
            assess_buy_off(spec)

    def test_non_mapping_spec_refused(self):
        with self.assertRaises(ValueError):
            assess_buy_off(["mode"])

    def test_non_boolean_audit_flag_refused(self):
        with self.assertRaises(ValueError):
            assess_buy_off(_spec(manufacturer_audit_current="yes"))

    def test_notice_table_without_the_mode_refused(self):
        with self.assertRaises(ValueError):
            assess_buy_off(_spec(notice_table={"remote-witnessed": 5}))


if __name__ == "__main__":
    unittest.main()
