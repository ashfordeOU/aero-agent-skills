#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-11C §4.7.4 architecture complements
assessment.

Exercises scripts/e1011_arch_complements_logic.py (stdlib unittest,
offline). Contract: an unrecognized complement type raises ValueError;
handrail spacing at or within 500 mm passes and above fails, negative
raises; a workstation with a foot, body, or tether restraint passes and
one with no recognized restraint fails; stowage at or within 710 mm
passes and beyond fails, negative raises; a mobility path with all gaps
at or within 500 mm is continuous and one exceeding the limit is not,
negative gap raises; aggregated zone review collects findings per
category; the zone is compliant only when all four categories are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1011_arch_complements_logic as ac  # noqa: E402


class CategorizeComplementTest(unittest.TestCase):
    def test_handrail_accepted(self):
        self.assertEqual(ac.categorize_complement("handrail"), "handrail")

    def test_restraint_accepted(self):
        self.assertEqual(ac.categorize_complement("restraint"), "restraint")

    def test_mobility_aid_accepted(self):
        self.assertEqual(ac.categorize_complement("mobility_aid"), "mobility_aid")

    def test_stowage_accepted(self):
        self.assertEqual(ac.categorize_complement("stowage"), "stowage")

    def test_unknown_type_raises(self):
        with self.assertRaises(ValueError):
            ac.categorize_complement("ladder_rung")


class HandrailSpacingTest(unittest.TestCase):
    def test_spacing_within_limit(self):
        self.assertTrue(ac.check_handrail_spacing(400.0))

    def test_spacing_at_limit(self):
        self.assertTrue(ac.check_handrail_spacing(500.0))

    def test_spacing_exceeds_limit(self):
        self.assertFalse(ac.check_handrail_spacing(501.0))

    def test_zero_spacing_accepted(self):
        self.assertTrue(ac.check_handrail_spacing(0.0))

    def test_negative_spacing_raises(self):
        with self.assertRaises(ValueError):
            ac.check_handrail_spacing(-10.0)


class WorkstationRestraintTest(unittest.TestCase):
    def test_foot_restraint_accepted(self):
        self.assertTrue(ac.check_workstation_restraint(["foot_restraint"]))

    def test_body_restraint_accepted(self):
        self.assertTrue(ac.check_workstation_restraint(["body_restraint"]))

    def test_tether_point_accepted(self):
        self.assertTrue(ac.check_workstation_restraint(["tether_point"]))

    def test_empty_restraint_list_fails(self):
        self.assertFalse(ac.check_workstation_restraint([]))

    def test_unrecognized_restraint_type_fails(self):
        self.assertFalse(ac.check_workstation_restraint(["velcro_patch"]))

    def test_mixed_list_passes_when_one_valid(self):
        self.assertTrue(ac.check_workstation_restraint(["velcro_patch", "foot_restraint"]))


class StowageReachTest(unittest.TestCase):
    def test_within_reach_envelope(self):
        self.assertTrue(ac.check_stowage_reach(600.0))

    def test_at_reach_limit(self):
        self.assertTrue(ac.check_stowage_reach(710.0))

    def test_outside_reach_envelope(self):
        self.assertFalse(ac.check_stowage_reach(711.0))

    def test_negative_distance_raises(self):
        with self.assertRaises(ValueError):
            ac.check_stowage_reach(-5.0)


class MobilityPathContinuityTest(unittest.TestCase):
    def test_all_gaps_within_limit(self):
        is_cont, max_gap = ac.check_mobility_path_continuity([200.0, 350.0, 500.0])
        self.assertTrue(is_cont)
        self.assertAlmostEqual(max_gap, 500.0)

    def test_one_gap_exceeds_limit(self):
        is_cont, max_gap = ac.check_mobility_path_continuity([200.0, 600.0])
        self.assertFalse(is_cont)
        self.assertAlmostEqual(max_gap, 600.0)

    def test_empty_path_is_continuous(self):
        is_cont, max_gap = ac.check_mobility_path_continuity([])
        self.assertTrue(is_cont)
        self.assertAlmostEqual(max_gap, 0.0)

    def test_negative_gap_raises(self):
        with self.assertRaises(ValueError):
            ac.check_mobility_path_continuity([200.0, -10.0])


class HandrailViolationsTest(unittest.TestCase):
    def test_no_violations_when_all_within_limit(self):
        self.assertEqual(ac.handrail_violations("zone-a", [300.0, 400.0, 500.0]), [])

    def test_violation_flagged_for_oversized_gap(self):
        violations = ac.handrail_violations("zone-a", [300.0, 600.0])
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "handrail_spacing_exceeds_limit")
        self.assertEqual(violations[0]["gap_index"], 1)
        self.assertAlmostEqual(violations[0]["spacing_mm"], 600.0)

    def test_multiple_violations_all_reported(self):
        violations = ac.handrail_violations("zone-b", [600.0, 700.0])
        self.assertEqual(len(violations), 2)


class RestraintViolationsTest(unittest.TestCase):
    def test_no_violation_with_valid_restraint(self):
        self.assertEqual(
            ac.restraint_violations("ws-1", ["foot_restraint"]), []
        )

    def test_violation_when_no_restraint_present(self):
        violations = ac.restraint_violations("ws-2", [])
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_workstation_restraint")
        self.assertEqual(violations[0]["workstation"], "ws-2")


class StowageViolationsTest(unittest.TestCase):
    def test_no_violation_when_all_within_reach(self):
        items = [{"item_id": "kit-1", "distance_mm": 500.0}]
        self.assertEqual(ac.stowage_violations("zone-a", items), [])

    def test_violation_flagged_for_item_outside_reach(self):
        items = [{"item_id": "kit-2", "distance_mm": 800.0}]
        violations = ac.stowage_violations("zone-a", items)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "stowage_outside_reach_envelope")
        self.assertEqual(violations[0]["item_id"], "kit-2")


class MobilityPathViolationsTest(unittest.TestCase):
    def test_no_violation_when_path_continuous(self):
        self.assertEqual(ac.mobility_path_violations("zone-a", [200.0, 300.0]), [])

    def test_violation_when_gap_exceeds_limit(self):
        violations = ac.mobility_path_violations("zone-a", [200.0, 650.0])
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "mobility_path_gap_exceeds_limit")
        self.assertAlmostEqual(violations[0]["max_gap_mm"], 650.0)


class ArchComplementsReviewTest(unittest.TestCase):
    def test_fully_compliant_zone(self):
        zone = {
            "zone_id": "hab-fwd",
            "handrail_spacings_mm": [300.0, 400.0],
            "workstations": [
                {"workstation_id": "ws-1", "restraint_types": ["foot_restraint"]}
            ],
            "mobility_path_gaps_mm": [250.0, 350.0],
            "stowage_items": [{"item_id": "kit-a", "distance_mm": 600.0}],
        }
        review = ac.arch_complements_review(zone)
        self.assertEqual(review, {"handrail": [], "restraint": [], "mobility": [], "stowage": []})
        self.assertTrue(ac.is_complements_compliant(review))

    def test_zone_with_multiple_category_violations(self):
        zone = {
            "zone_id": "hab-aft",
            "handrail_spacings_mm": [600.0],
            "workstations": [
                {"workstation_id": "ws-2", "restraint_types": []}
            ],
            "mobility_path_gaps_mm": [700.0],
            "stowage_items": [{"item_id": "kit-b", "distance_mm": 900.0}],
        }
        review = ac.arch_complements_review(zone)
        self.assertTrue(review["handrail"])
        self.assertTrue(review["restraint"])
        self.assertTrue(review["mobility"])
        self.assertTrue(review["stowage"])
        self.assertFalse(ac.is_complements_compliant(review))

    def test_zone_with_no_workstations_no_restraint_violation(self):
        zone = {
            "zone_id": "corridor-1",
            "handrail_spacings_mm": [400.0],
            "workstations": [],
            "mobility_path_gaps_mm": [300.0],
            "stowage_items": [],
        }
        review = ac.arch_complements_review(zone)
        self.assertEqual(review["restraint"], [])
        self.assertTrue(ac.is_complements_compliant(review))

    def test_is_compliant_false_with_one_category_violation(self):
        review = {"handrail": [{"issue": "handrail_spacing_exceeds_limit"}],
                  "restraint": [], "mobility": [], "stowage": []}
        self.assertFalse(ac.is_complements_compliant(review))


if __name__ == "__main__":
    unittest.main()
