#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-11C §4.8 on-board informatics support.

Exercises scripts/e1011_informatics_logic.py (stdlib unittest, offline).
Contract: a display element type is accepted when it belongs to the known
set and rejected with ValueError otherwise; alert urgency is determined
from hazard severity and time criticality with unrecognized inputs raising;
display format violations are raised for contrast ratio or character height
below their respective minima, with negative inputs raising; automation
authority at supervisory or autonomous level requires crew override and its
absence is flagged, while advisory and shared_control require none; the
workstation-level check aggregates all three violation categories; and a
review is informatics-compliant only when every violation list is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1011_informatics_logic as inf  # noqa: E402


class CategorizeDisplayElementTest(unittest.TestCase):
    def test_numerical_element_accepted(self):
        self.assertEqual(inf.categorize_display_element("numerical"), "numerical")

    def test_graphical_element_accepted(self):
        self.assertEqual(inf.categorize_display_element("graphical"), "graphical")

    def test_status_text_element_accepted(self):
        self.assertEqual(inf.categorize_display_element("status_text"), "status_text")

    def test_alert_element_accepted(self):
        self.assertEqual(inf.categorize_display_element("alert"), "alert")

    def test_control_element_accepted(self):
        self.assertEqual(inf.categorize_display_element("control"), "control")

    def test_unknown_element_type_raises(self):
        with self.assertRaises(ValueError):
            inf.categorize_display_element("hologram")


class DetermineAlertLevelTest(unittest.TestCase):
    def test_high_severity_seconds_is_warning(self):
        self.assertEqual(inf.determine_alert_level("high", "seconds"), "warning")

    def test_high_severity_minutes_is_caution(self):
        self.assertEqual(inf.determine_alert_level("high", "minutes"), "caution")

    def test_medium_severity_seconds_is_caution(self):
        self.assertEqual(inf.determine_alert_level("medium", "seconds"), "caution")

    def test_medium_severity_minutes_is_caution(self):
        self.assertEqual(inf.determine_alert_level("medium", "minutes"), "caution")

    def test_low_severity_seconds_is_advisory(self):
        self.assertEqual(inf.determine_alert_level("low", "seconds"), "advisory")

    def test_high_severity_hours_is_advisory(self):
        self.assertEqual(inf.determine_alert_level("high", "hours"), "advisory")

    def test_low_severity_none_is_advisory(self):
        self.assertEqual(inf.determine_alert_level("low", "none"), "advisory")

    def test_unknown_severity_raises(self):
        with self.assertRaises(ValueError):
            inf.determine_alert_level("critical", "seconds")

    def test_unknown_criticality_raises(self):
        with self.assertRaises(ValueError):
            inf.determine_alert_level("high", "milliseconds")


class CheckDisplayFormatTest(unittest.TestCase):
    def test_compliant_format_no_violations(self):
        self.assertEqual(inf.check_display_format(5.0, 4.0), [])

    def test_contrast_at_minimum_no_violation(self):
        self.assertEqual(inf.check_display_format(inf.MIN_CONTRAST_RATIO, 4.0), [])

    def test_contrast_below_minimum_flagged(self):
        violations = inf.check_display_format(3.0, 4.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "contrast_below_minimum")
        self.assertEqual(violations[0]["contrast_ratio"], 3.0)
        self.assertEqual(violations[0]["minimum"], inf.MIN_CONTRAST_RATIO)

    def test_char_height_below_minimum_flagged(self):
        violations = inf.check_display_format(5.0, 2.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "char_height_below_minimum")

    def test_both_below_minimum_two_violations(self):
        violations = inf.check_display_format(2.0, 1.0)
        self.assertEqual(len(violations), 2)
        issues = {v["issue"] for v in violations}
        self.assertIn("contrast_below_minimum", issues)
        self.assertIn("char_height_below_minimum", issues)

    def test_negative_contrast_raises(self):
        with self.assertRaises(ValueError):
            inf.check_display_format(-1.0, 4.0)

    def test_negative_char_height_raises(self):
        with self.assertRaises(ValueError):
            inf.check_display_format(5.0, -1.0)


class AssessAutomationAuthorityTest(unittest.TestCase):
    def test_advisory_without_override_no_violation(self):
        self.assertEqual(inf.assess_automation_authority("advisory", False), [])

    def test_shared_control_without_override_no_violation(self):
        self.assertEqual(inf.assess_automation_authority("shared_control", False), [])

    def test_supervisory_with_override_no_violation(self):
        self.assertEqual(inf.assess_automation_authority("supervisory", True), [])

    def test_autonomous_with_override_no_violation(self):
        self.assertEqual(inf.assess_automation_authority("autonomous", True), [])

    def test_supervisory_without_override_flagged(self):
        violations = inf.assess_automation_authority("supervisory", False)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_crew_override")
        self.assertEqual(violations[0]["authority_level"], "supervisory")

    def test_autonomous_without_override_flagged(self):
        violations = inf.assess_automation_authority("autonomous", False)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_crew_override")
        self.assertEqual(violations[0]["authority_level"], "autonomous")

    def test_unknown_authority_level_raises(self):
        with self.assertRaises(ValueError):
            inf.assess_automation_authority("rogue_ai", True)


class CheckWorkstationInformationTest(unittest.TestCase):
    def _make_compliant_workstation(self):
        return {
            "workstation_id": "ws-nav-1",
            "display_elements": [
                {"type": "numerical", "contrast_ratio": 5.0, "char_height_mm": 4.0},
                {"type": "alert", "contrast_ratio": 7.0, "char_height_mm": 5.0},
            ],
            "alerts": [
                {
                    "hazard_severity": "high",
                    "time_criticality": "seconds",
                    "declared_level": "warning",
                }
            ],
            "automation": [
                {"authority_level": "supervisory", "crew_override_available": True}
            ],
        }

    def test_compliant_workstation_no_violations(self):
        review = inf.check_workstation_information(self._make_compliant_workstation())
        self.assertEqual(review["format_violations"], [])
        self.assertEqual(review["alert_level_mismatches"], [])
        self.assertEqual(review["automation_violations"], [])
        self.assertTrue(inf.is_informatics_compliant(review))

    def test_unknown_display_element_type_raises(self):
        ws = self._make_compliant_workstation()
        ws["display_elements"].append(
            {"type": "telepathic_overlay", "contrast_ratio": 5.0, "char_height_mm": 4.0}
        )
        with self.assertRaises(ValueError):
            inf.check_workstation_information(ws)

    def test_format_violation_surfaced(self):
        ws = self._make_compliant_workstation()
        ws["display_elements"][0]["contrast_ratio"] = 2.0
        review = inf.check_workstation_information(ws)
        self.assertEqual(len(review["format_violations"]), 1)
        self.assertEqual(review["format_violations"][0]["workstation"], "ws-nav-1")
        self.assertFalse(inf.is_informatics_compliant(review))

    def test_alert_level_mismatch_surfaced(self):
        ws = self._make_compliant_workstation()
        ws["alerts"][0]["declared_level"] = "advisory"
        review = inf.check_workstation_information(ws)
        self.assertEqual(len(review["alert_level_mismatches"]), 1)
        mismatch = review["alert_level_mismatches"][0]
        self.assertEqual(mismatch["issue"], "alert_level_mismatch")
        self.assertEqual(mismatch["expected"], "warning")
        self.assertEqual(mismatch["declared"], "advisory")
        self.assertFalse(inf.is_informatics_compliant(review))

    def test_automation_violation_surfaced(self):
        ws = self._make_compliant_workstation()
        ws["automation"][0]["crew_override_available"] = False
        review = inf.check_workstation_information(ws)
        self.assertEqual(len(review["automation_violations"]), 1)
        self.assertEqual(
            review["automation_violations"][0]["issue"], "missing_crew_override"
        )
        self.assertFalse(inf.is_informatics_compliant(review))

    def test_empty_workstation_passes(self):
        ws = {"workstation_id": "ws-empty", "display_elements": [], "alerts": [], "automation": []}
        review = inf.check_workstation_information(ws)
        self.assertTrue(inf.is_informatics_compliant(review))

    def test_multiple_violations_all_returned(self):
        ws = {
            "workstation_id": "ws-bad",
            "display_elements": [
                {"type": "graphical", "contrast_ratio": 1.0, "char_height_mm": 1.0}
            ],
            "alerts": [
                {
                    "hazard_severity": "high",
                    "time_criticality": "seconds",
                    "declared_level": "advisory",
                }
            ],
            "automation": [
                {"authority_level": "autonomous", "crew_override_available": False}
            ],
        }
        review = inf.check_workstation_information(ws)
        self.assertEqual(len(review["format_violations"]), 2)
        self.assertEqual(len(review["alert_level_mismatches"]), 1)
        self.assertEqual(len(review["automation_violations"]), 1)
        self.assertFalse(inf.is_informatics_compliant(review))


class IsInformaticsCompliantTest(unittest.TestCase):
    def test_all_empty_lists_is_compliant(self):
        review = {
            "format_violations": [],
            "alert_level_mismatches": [],
            "automation_violations": [],
        }
        self.assertTrue(inf.is_informatics_compliant(review))

    def test_one_nonempty_list_not_compliant(self):
        review = {
            "format_violations": [{"issue": "contrast_below_minimum"}],
            "alert_level_mismatches": [],
            "automation_violations": [],
        }
        self.assertFalse(inf.is_informatics_compliant(review))


if __name__ == "__main__":
    unittest.main(verbosity=2)
