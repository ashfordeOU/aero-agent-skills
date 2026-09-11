import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1011_assessment_events_logic import (
    ValidationError,
    REVIEW_TYPES,
    MILESTONE_ORDER,
    HARDWARE_CATEGORIES,
    validate_review_type,
    validate_milestone,
    validate_hardware_category,
    reviews_for_hardware,
    required_reviews_for_milestone,
    check_milestone_coverage,
    reviews_due_before_gate,
    add_finding,
    close_finding,
    waive_finding,
    verify_gate_readiness,
    milestone_index,
)


class TestValidateReviewType(unittest.TestCase):
    def test_usability_accepted(self):
        self.assertEqual(validate_review_type("usability"), "usability")

    def test_design_accepted(self):
        self.assertEqual(validate_review_type("design"), "design")

    def test_crew_station_accepted(self):
        self.assertEqual(validate_review_type("crew-station"), "crew-station")

    def test_unknown_type_raises(self):
        with self.assertRaises(ValidationError):
            validate_review_type("ergonomic-survey")

    def test_empty_string_raises(self):
        with self.assertRaises(ValidationError):
            validate_review_type("")

    def test_all_review_types_valid(self):
        for rt in REVIEW_TYPES:
            self.assertEqual(validate_review_type(rt), rt)


class TestValidateMilestone(unittest.TestCase):
    def test_pdr_accepted(self):
        self.assertEqual(validate_milestone("PDR"), "PDR")

    def test_cdr_accepted(self):
        self.assertEqual(validate_milestone("CDR"), "CDR")

    def test_orr_accepted(self):
        self.assertEqual(validate_milestone("ORR"), "ORR")

    def test_unknown_milestone_raises(self):
        with self.assertRaises(ValidationError):
            validate_milestone("SRR")

    def test_lowercase_rejected(self):
        with self.assertRaises(ValidationError):
            validate_milestone("cdr")

    def test_all_milestones_valid(self):
        for ms in MILESTONE_ORDER:
            self.assertEqual(validate_milestone(ms), ms)


class TestValidateHardwareCategory(unittest.TestCase):
    def test_display_accepted(self):
        self.assertEqual(validate_hardware_category("display"), "display")

    def test_unknown_category_raises(self):
        with self.assertRaises(ValidationError):
            validate_hardware_category("widget")

    def test_all_categories_valid(self):
        for cat in HARDWARE_CATEGORIES:
            self.assertEqual(validate_hardware_category(cat), cat)


class TestReviewsForHardware(unittest.TestCase):
    def test_display_requires_usability(self):
        self.assertIn("usability", reviews_for_hardware("display"))

    def test_display_requires_design(self):
        self.assertIn("design", reviews_for_hardware("display"))

    def test_control_requires_crew_station(self):
        self.assertIn("crew-station", reviews_for_hardware("control"))

    def test_seat_does_not_require_usability(self):
        self.assertNotIn("usability", reviews_for_hardware("seat"))

    def test_habitat_requires_all_three(self):
        result = reviews_for_hardware("habitat")
        self.assertIn("usability", result)
        self.assertIn("design", result)
        self.assertIn("crew-station", result)

    def test_unknown_category_raises(self):
        with self.assertRaises(ValidationError):
            reviews_for_hardware("gadget")

    def test_returns_frozenset(self):
        result = reviews_for_hardware("tool")
        self.assertIsInstance(result, frozenset)


class TestRequiredReviewsForMilestone(unittest.TestCase):
    def test_pdr_requires_design(self):
        self.assertIn("design", required_reviews_for_milestone("PDR"))

    def test_pdr_does_not_require_usability(self):
        self.assertNotIn("usability", required_reviews_for_milestone("PDR"))

    def test_cdr_requires_usability(self):
        self.assertIn("usability", required_reviews_for_milestone("CDR"))

    def test_cdr_requires_crew_station(self):
        self.assertIn("crew-station", required_reviews_for_milestone("CDR"))

    def test_ar_requires_crew_station_only(self):
        result = required_reviews_for_milestone("AR")
        self.assertIn("crew-station", result)
        self.assertNotIn("usability", result)
        self.assertNotIn("design", result)

    def test_orr_requires_usability(self):
        self.assertIn("usability", required_reviews_for_milestone("ORR"))

    def test_unknown_milestone_raises(self):
        with self.assertRaises(ValidationError):
            required_reviews_for_milestone("FRR")


class TestCheckMilestoneCoverage(unittest.TestCase):
    def test_fully_scheduled_returns_no_gaps(self):
        scheduled = {
            "PDR": {"design"},
            "CDR": {"design", "usability", "crew-station"},
            "QR":  {"usability", "crew-station"},
            "AR":  {"crew-station"},
            "ORR": {"usability"},
        }
        self.assertEqual(check_milestone_coverage(scheduled), [])

    def test_missing_usability_at_cdr_flagged(self):
        scheduled = {
            "PDR": {"design"},
            "CDR": {"design", "crew-station"},
        }
        gaps = check_milestone_coverage(scheduled)
        cdr_gap = next((g for g in gaps if g["milestone"] == "CDR"), None)
        self.assertIsNotNone(cdr_gap)
        self.assertIn("usability", cdr_gap["missing"])

    def test_empty_schedule_flags_all_mandatory_milestones(self):
        gaps = check_milestone_coverage({})
        milestone_names = [g["milestone"] for g in gaps]
        self.assertIn("PDR", milestone_names)
        self.assertIn("CDR", milestone_names)
        self.assertIn("QR", milestone_names)

    def test_partial_schedule_flags_only_missing(self):
        scheduled = {
            "PDR": {"design"},
            "CDR": {"design", "usability", "crew-station"},
            "QR":  {"usability"},
        }
        gaps = check_milestone_coverage(scheduled)
        qr_gap = next((g for g in gaps if g["milestone"] == "QR"), None)
        self.assertIsNotNone(qr_gap)
        self.assertIn("crew-station", qr_gap["missing"])
        self.assertNotIn("usability", qr_gap["missing"])

    def test_extra_review_in_schedule_no_gap(self):
        scheduled = {
            "PDR": {"design", "usability"},
            "CDR": {"design", "usability", "crew-station"},
            "QR":  {"usability", "crew-station"},
            "AR":  {"crew-station"},
            "ORR": {"usability"},
        }
        self.assertEqual(check_milestone_coverage(scheduled), [])


class TestReviewsDueBeforeGate(unittest.TestCase):
    def test_all_scheduled_before_cdr_returns_empty(self):
        scheduled = {
            "PDR": {"design"},
            "CDR": {"design", "usability", "crew-station"},
        }
        self.assertEqual(reviews_due_before_gate("CDR", scheduled), [])

    def test_missing_pdr_design_detected_at_cdr_gate(self):
        scheduled = {
            "CDR": {"design", "usability", "crew-station"},
        }
        gaps = reviews_due_before_gate("CDR", scheduled)
        pdr_gap = next((g for g in gaps if g["milestone"] == "PDR"), None)
        self.assertIsNotNone(pdr_gap)
        self.assertIn("design", pdr_gap["missing"])

    def test_gate_at_pdr_only_checks_pdr(self):
        scheduled = {}
        gaps = reviews_due_before_gate("PDR", scheduled)
        milestone_names = [g["milestone"] for g in gaps]
        self.assertIn("PDR", milestone_names)
        self.assertNotIn("CDR", milestone_names)

    def test_invalid_gate_milestone_raises(self):
        with self.assertRaises(ValidationError):
            reviews_due_before_gate("MRR", {})


class TestAddFinding(unittest.TestCase):
    def test_new_finding_is_open(self):
        findings = add_finding({}, "F001", "Display contrast below threshold", "major")
        self.assertEqual(findings["F001"]["status"], "open")

    def test_new_finding_stores_severity(self):
        findings = add_finding({}, "F001", "Grip diameter too large for 5th-percentile hand", "critical")
        self.assertEqual(findings["F001"]["severity"], "critical")

    def test_new_finding_resolution_is_none(self):
        findings = add_finding({}, "F001", "Label too small", "minor")
        self.assertIsNone(findings["F001"]["resolution"])

    def test_duplicate_id_raises(self):
        findings = add_finding({}, "F001", "Issue A", "minor")
        with self.assertRaises(ValidationError):
            add_finding(findings, "F001", "Issue B", "minor")

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValidationError):
            add_finding({}, "F001", "Issue", "blocker")

    def test_empty_description_raises(self):
        with self.assertRaises(ValidationError):
            add_finding({}, "F001", "   ", "minor")

    def test_immutability_original_unchanged(self):
        original = {}
        add_finding(original, "F001", "Issue", "major")
        self.assertEqual(original, {})

    def test_multiple_findings_accumulate(self):
        findings = add_finding({}, "F001", "Issue A", "major")
        findings = add_finding(findings, "F002", "Issue B", "minor")
        self.assertIn("F001", findings)
        self.assertIn("F002", findings)


class TestCloseFinding(unittest.TestCase):
    def test_close_sets_status_closed(self):
        findings = add_finding({}, "F001", "Reach distance marginal", "major")
        findings = close_finding(findings, "F001", "Panel relocated 50 mm closer to seat reference point")
        self.assertEqual(findings["F001"]["status"], "closed")

    def test_close_stores_resolution(self):
        findings = add_finding({}, "F001", "Font size too small", "minor")
        findings = close_finding(findings, "F001", "Font size increased to 12pt Helvetica")
        self.assertEqual(findings["F001"]["resolution"], "Font size increased to 12pt Helvetica")

    def test_close_nonexistent_raises(self):
        with self.assertRaises(ValidationError):
            close_finding({}, "F999", "Some resolution")

    def test_close_already_closed_raises(self):
        findings = add_finding({}, "F001", "Issue", "minor")
        findings = close_finding(findings, "F001", "Fixed")
        with self.assertRaises(ValidationError):
            close_finding(findings, "F001", "Fixed again")

    def test_close_empty_resolution_raises(self):
        findings = add_finding({}, "F001", "Issue", "minor")
        with self.assertRaises(ValidationError):
            close_finding(findings, "F001", "   ")

    def test_close_immutability(self):
        findings = add_finding({}, "F001", "Issue", "major")
        original_status = findings["F001"]["status"]
        close_finding(findings, "F001", "Fixed")
        self.assertEqual(findings["F001"]["status"], original_status)


class TestWaiveFinding(unittest.TestCase):
    def test_waive_sets_status_waived(self):
        findings = add_finding({}, "F001", "Grip force slightly above guideline", "observation")
        findings = waive_finding(findings, "F001", "Accepted per design trade DR-42; crew training compensates")
        self.assertEqual(findings["F001"]["status"], "waived")

    def test_waive_stores_rationale(self):
        findings = add_finding({}, "F001", "Label colour contrast marginal", "minor")
        rationale = "Waived per lighting analysis report LR-07"
        findings = waive_finding(findings, "F001", rationale)
        self.assertEqual(findings["F001"]["resolution"], rationale)

    def test_waive_nonexistent_raises(self):
        with self.assertRaises(ValidationError):
            waive_finding({}, "F999", "Rationale")

    def test_waive_already_waived_raises(self):
        findings = add_finding({}, "F001", "Issue", "observation")
        findings = waive_finding(findings, "F001", "Accepted per DR-42")
        with self.assertRaises(ValidationError):
            waive_finding(findings, "F001", "Accepted again")

    def test_waive_empty_rationale_raises(self):
        findings = add_finding({}, "F001", "Issue", "minor")
        with self.assertRaises(ValidationError):
            waive_finding(findings, "F001", "")

    def test_waive_immutability(self):
        findings = add_finding({}, "F001", "Issue", "minor")
        original_status = findings["F001"]["status"]
        waive_finding(findings, "F001", "Accepted per trade")
        self.assertEqual(findings["F001"]["status"], original_status)


class TestVerifyGateReadiness(unittest.TestCase):
    def test_empty_findings_is_ready(self):
        ready, open_ids = verify_gate_readiness({})
        self.assertTrue(ready)
        self.assertEqual(open_ids, [])

    def test_all_closed_is_ready(self):
        findings = add_finding({}, "F001", "Issue A", "minor")
        findings = close_finding(findings, "F001", "Resolved")
        ready, open_ids = verify_gate_readiness(findings)
        self.assertTrue(ready)
        self.assertEqual(open_ids, [])

    def test_all_waived_is_ready(self):
        findings = add_finding({}, "F001", "Issue A", "observation")
        findings = waive_finding(findings, "F001", "Accepted per trade")
        ready, open_ids = verify_gate_readiness(findings)
        self.assertTrue(ready)

    def test_open_finding_blocks_gate(self):
        findings = add_finding({}, "F001", "Critical ergonomic non-compliance", "critical")
        ready, open_ids = verify_gate_readiness(findings)
        self.assertFalse(ready)
        self.assertIn("F001", open_ids)

    def test_mixed_open_and_closed_blocks_gate(self):
        findings = add_finding({}, "F001", "Issue A", "major")
        findings = add_finding(findings, "F002", "Issue B", "minor")
        findings = close_finding(findings, "F001", "Fixed")
        ready, open_ids = verify_gate_readiness(findings)
        self.assertFalse(ready)
        self.assertIn("F002", open_ids)
        self.assertNotIn("F001", open_ids)

    def test_mixed_waived_and_open_blocks_gate(self):
        findings = add_finding({}, "F001", "Issue A", "observation")
        findings = add_finding(findings, "F002", "Issue B", "major")
        findings = waive_finding(findings, "F001", "Accepted per trade")
        ready, open_ids = verify_gate_readiness(findings)
        self.assertFalse(ready)
        self.assertIn("F002", open_ids)

    def test_open_ids_are_sorted(self):
        findings = add_finding({}, "F003", "Issue C", "minor")
        findings = add_finding(findings, "F001", "Issue A", "minor")
        findings = add_finding(findings, "F002", "Issue B", "minor")
        _, open_ids = verify_gate_readiness(findings)
        self.assertEqual(open_ids, sorted(open_ids))


class TestMilestoneIndex(unittest.TestCase):
    def test_pdr_is_first(self):
        self.assertEqual(milestone_index("PDR"), 0)

    def test_orr_is_last(self):
        self.assertEqual(milestone_index("ORR"), len(MILESTONE_ORDER) - 1)

    def test_cdr_after_pdr(self):
        self.assertGreater(milestone_index("CDR"), milestone_index("PDR"))

    def test_invalid_milestone_raises(self):
        with self.assertRaises(ValidationError):
            milestone_index("TRR")


if __name__ == "__main__":
    unittest.main()
