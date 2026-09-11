#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-11C §4.7.6 workstation design
assessment.

Exercises scripts/e1011_workstations_logic.py (stdlib unittest, offline).
Contract: each workstation element (display or control) must be categorized
into a recognized access-frequency zone before placement assessment; an
unrecognized zone raises; display viewing angles and distance are checked
against zone-specific limits and each exceedance is flagged separately;
control reach distance is checked against its zone's radius cap, with
tertiary zone carrying no cap; ingress/egress access paths are checked for
clear width and clear height against mode-specific minimums, and an
unrecognized access mode raises; the aggregated workstation_review collects
findings from all three element types and is compliant only when all three
finding lists are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1011_workstations_logic as ws  # noqa: E402


class CategorizeZoneTest(unittest.TestCase):
    def test_primary_zone_accepted(self):
        self.assertEqual(ws.categorize_zone("primary"), "primary")

    def test_secondary_zone_accepted(self):
        self.assertEqual(ws.categorize_zone("secondary"), "secondary")

    def test_tertiary_zone_accepted(self):
        self.assertEqual(ws.categorize_zone("tertiary"), "tertiary")

    def test_unrecognized_zone_raises(self):
        with self.assertRaises(ValueError):
            ws.categorize_zone("quaternary")


class CheckDisplayViewingTest(unittest.TestCase):
    def test_primary_display_within_all_limits(self):
        findings = ws.check_display_viewing("primary", 10.0, -15.0, 500.0)
        self.assertEqual(findings, [])

    def test_primary_h_angle_exceeded(self):
        findings = ws.check_display_viewing("primary", 35.0, -15.0, 500.0)
        issues = [f["issue"] for f in findings]
        self.assertIn("horizontal_viewing_angle_exceeded", issues)

    def test_primary_h_angle_left_exceeded(self):
        findings = ws.check_display_viewing("primary", -35.0, -15.0, 500.0)
        issues = [f["issue"] for f in findings]
        self.assertIn("horizontal_viewing_angle_exceeded", issues)

    def test_primary_v_angle_too_low(self):
        findings = ws.check_display_viewing("primary", 0.0, -45.0, 500.0)
        issues = [f["issue"] for f in findings]
        self.assertIn("vertical_viewing_angle_exceeded", issues)

    def test_primary_v_angle_above_horizontal_fails(self):
        findings = ws.check_display_viewing("primary", 0.0, 5.0, 500.0)
        issues = [f["issue"] for f in findings]
        self.assertIn("vertical_viewing_angle_exceeded", issues)

    def test_viewing_distance_too_close(self):
        findings = ws.check_display_viewing("primary", 0.0, -10.0, 200.0)
        issues = [f["issue"] for f in findings]
        self.assertIn("viewing_distance_below_minimum", issues)

    def test_viewing_distance_too_far(self):
        findings = ws.check_display_viewing("primary", 0.0, -10.0, 800.0)
        issues = [f["issue"] for f in findings]
        self.assertIn("viewing_distance_above_maximum", issues)

    def test_secondary_zone_wider_h_limit(self):
        # 45° is outside primary (30°) but inside secondary (60°)
        findings = ws.check_display_viewing("secondary", 45.0, -10.0, 500.0)
        self.assertEqual(findings, [])

    def test_secondary_zone_allows_slight_upward_angle(self):
        # v_angle=5° is inside secondary (v_max=10°) but outside primary (v_max=0°)
        findings = ws.check_display_viewing("secondary", 0.0, 5.0, 500.0)
        self.assertEqual(findings, [])

    def test_negative_distance_raises(self):
        with self.assertRaises(ValueError):
            ws.check_display_viewing("primary", 0.0, -10.0, -1.0)

    def test_multiple_violations_returned_together(self):
        # h > 30 and distance < 300 both violated simultaneously
        findings = ws.check_display_viewing("primary", 40.0, -10.0, 200.0)
        issues = [f["issue"] for f in findings]
        self.assertIn("horizontal_viewing_angle_exceeded", issues)
        self.assertIn("viewing_distance_below_minimum", issues)


class CheckControlReachTest(unittest.TestCase):
    def test_primary_within_functional_reach(self):
        self.assertEqual(ws.check_control_reach("primary", 350.0), [])

    def test_primary_at_limit_boundary(self):
        self.assertEqual(ws.check_control_reach("primary", 400.0), [])

    def test_primary_exceeds_functional_reach(self):
        findings = ws.check_control_reach("primary", 450.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "reach_envelope_exceeded")
        self.assertEqual(findings[0]["zone"], "primary")

    def test_secondary_within_maximum_reach(self):
        self.assertEqual(ws.check_control_reach("secondary", 600.0), [])

    def test_secondary_exceeds_maximum_reach(self):
        findings = ws.check_control_reach("secondary", 700.0)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["issue"], "reach_envelope_exceeded")

    def test_tertiary_zone_no_reach_cap(self):
        # Tertiary controls require repositioning; any distance returns no findings
        self.assertEqual(ws.check_control_reach("tertiary", 900.0), [])

    def test_negative_reach_raises(self):
        with self.assertRaises(ValueError):
            ws.check_control_reach("primary", -10.0)

    def test_unrecognized_zone_raises(self):
        with self.assertRaises(ValueError):
            ws.check_control_reach("overhead", 300.0)


class CheckAccessPathTest(unittest.TestCase):
    def test_normal_operational_compliant(self):
        self.assertEqual(
            ws.check_access_path("normal_operational", 600, 1900), []
        )

    def test_normal_operational_width_too_narrow(self):
        findings = ws.check_access_path("normal_operational", 500, 1900)
        issues = [f["issue"] for f in findings]
        self.assertIn("access_width_below_minimum", issues)

    def test_normal_operational_height_too_low(self):
        findings = ws.check_access_path("normal_operational", 600, 1700)
        issues = [f["issue"] for f in findings]
        self.assertIn("access_height_below_minimum", issues)

    def test_maintenance_compliant(self):
        self.assertEqual(ws.check_access_path("maintenance", 520, 1600), [])

    def test_maintenance_height_shortfall(self):
        findings = ws.check_access_path("maintenance", 520, 1400)
        issues = [f["issue"] for f in findings]
        self.assertIn("access_height_below_minimum", issues)

    def test_emergency_egress_compliant(self):
        self.assertEqual(ws.check_access_path("emergency_egress", 460, 1500), [])

    def test_emergency_egress_width_too_narrow(self):
        findings = ws.check_access_path("emergency_egress", 400, 1500)
        issues = [f["issue"] for f in findings]
        self.assertIn("access_width_below_minimum", issues)

    def test_unrecognized_mode_raises(self):
        with self.assertRaises(ValueError):
            ws.check_access_path("cargo_transfer", 600, 1800)

    def test_negative_width_raises(self):
        with self.assertRaises(ValueError):
            ws.check_access_path("normal_operational", -1, 1800)

    def test_negative_height_raises(self):
        with self.assertRaises(ValueError):
            ws.check_access_path("normal_operational", 600, -1)


class WorkstationReviewTest(unittest.TestCase):
    def _make_compliant_workstation(self):
        return {
            "workstation_id": "ws-cdh-1",
            "displays": [
                {
                    "display_id": "disp-main",
                    "zone": "primary",
                    "h_angle_deg": 5.0,
                    "v_angle_deg": -10.0,
                    "distance_mm": 500.0,
                },
                {
                    "display_id": "disp-secondary",
                    "zone": "secondary",
                    "h_angle_deg": 45.0,
                    "v_angle_deg": -20.0,
                    "distance_mm": 600.0,
                },
            ],
            "controls": [
                {"control_id": "ctrl-abort", "zone": "primary", "reach_mm": 350.0},
                {"control_id": "ctrl-config", "zone": "secondary", "reach_mm": 600.0},
                {"control_id": "ctrl-ref", "zone": "tertiary", "reach_mm": 850.0},
            ],
            "access_paths": [
                {
                    "path_id": "path-front",
                    "mode": "normal_operational",
                    "width_mm": 600,
                    "height_mm": 1850,
                }
            ],
        }

    def test_fully_compliant_workstation(self):
        review = ws.workstation_review(self._make_compliant_workstation())
        self.assertEqual(review["workstation_id"], "ws-cdh-1")
        self.assertEqual(review["display_findings"], [])
        self.assertEqual(review["reach_findings"], [])
        self.assertEqual(review["access_findings"], [])
        self.assertTrue(ws.is_workstation_compliant(review))

    def test_review_flags_display_violation(self):
        workstation = self._make_compliant_workstation()
        workstation["displays"][0]["h_angle_deg"] = 50.0  # exceeds primary 30°
        review = ws.workstation_review(workstation)
        self.assertTrue(len(review["display_findings"]) > 0)
        self.assertFalse(ws.is_workstation_compliant(review))

    def test_review_flags_reach_violation(self):
        workstation = self._make_compliant_workstation()
        workstation["controls"][0]["reach_mm"] = 500.0  # exceeds primary 400 mm
        review = ws.workstation_review(workstation)
        self.assertTrue(len(review["reach_findings"]) > 0)
        self.assertFalse(ws.is_workstation_compliant(review))

    def test_review_flags_access_path_violation(self):
        workstation = self._make_compliant_workstation()
        workstation["access_paths"][0]["width_mm"] = 400  # < 550 mm minimum
        review = ws.workstation_review(workstation)
        self.assertTrue(len(review["access_findings"]) > 0)
        self.assertFalse(ws.is_workstation_compliant(review))

    def test_review_finding_carries_display_id(self):
        workstation = self._make_compliant_workstation()
        workstation["displays"][0]["h_angle_deg"] = 50.0
        review = ws.workstation_review(workstation)
        self.assertIn("display_id", review["display_findings"][0])

    def test_review_finding_carries_control_id(self):
        workstation = self._make_compliant_workstation()
        workstation["controls"][1]["reach_mm"] = 700.0  # exceeds secondary 650 mm
        review = ws.workstation_review(workstation)
        self.assertIn("control_id", review["reach_findings"][0])

    def test_review_finding_carries_path_id(self):
        workstation = self._make_compliant_workstation()
        workstation["access_paths"][0]["height_mm"] = 1200
        review = ws.workstation_review(workstation)
        self.assertIn("path_id", review["access_findings"][0])

    def test_empty_workstation_is_compliant(self):
        review = ws.workstation_review(
            {"workstation_id": "ws-empty", "displays": [], "controls": [],
             "access_paths": []}
        )
        self.assertTrue(ws.is_workstation_compliant(review))

    def test_review_raises_on_unknown_zone(self):
        workstation = self._make_compliant_workstation()
        workstation["controls"].append(
            {"control_id": "ctrl-bad", "zone": "overhead", "reach_mm": 300.0}
        )
        with self.assertRaises(ValueError):
            ws.workstation_review(workstation)

    def test_review_raises_on_unknown_access_mode(self):
        workstation = self._make_compliant_workstation()
        workstation["access_paths"].append(
            {"path_id": "path-bad", "mode": "spacewalk_exit",
             "width_mm": 600, "height_mm": 1800}
        )
        with self.assertRaises(ValueError):
            ws.workstation_review(workstation)


if __name__ == "__main__":
    unittest.main(verbosity=2)
