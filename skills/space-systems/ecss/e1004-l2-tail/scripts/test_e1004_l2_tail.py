#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C clause 9.2.7 L2 / deep
magnetotail radiation environment definition.

Exercises scripts/e1004_l2_tail_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - a segment is only in this
leaf's scope once it is outside the trapped-belt boundary; a
plasma-sheet crossing takes precedence over a lobe crossing; every
L2/deep-magnetotail segment carries the unshielded GCR + SEP baseline,
plasma-sheet segments additionally carry the charging supplement, and
geomagnetic shielding never applies in this region.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_l2_tail_logic as l2t  # noqa: E402


class TrappedBeltAppliesTest(unittest.TestCase):
    def test_inside_boundary_true(self):
        self.assertTrue(l2t.trapped_belt_applies(5.0))

    def test_at_boundary_false(self):
        self.assertFalse(l2t.trapped_belt_applies(10.0))

    def test_beyond_boundary_false(self):
        self.assertFalse(l2t.trapped_belt_applies(235.0))

    def test_negative_distance_raises(self):
        with self.assertRaises(ValueError):
            l2t.trapped_belt_applies(-1.0)


class ClassifySegmentTest(unittest.TestCase):
    def test_deep_space_default(self):
        self.assertEqual(l2t.classify_segment(235.0, False, False), "l2_deep_space")

    def test_lobe_crossing(self):
        self.assertEqual(l2t.classify_segment(60.0, False, True), "magnetotail_lobe")

    def test_plasma_sheet_crossing(self):
        self.assertEqual(l2t.classify_segment(60.0, True, False), "magnetotail_plasma_sheet")

    def test_plasma_sheet_takes_precedence_over_lobe(self):
        self.assertEqual(l2t.classify_segment(60.0, True, True), "magnetotail_plasma_sheet")

    def test_crossing_inside_trapped_belt_raises(self):
        with self.assertRaises(ValueError):
            l2t.classify_segment(5.0, True, False)

    def test_negative_distance_raises(self):
        with self.assertRaises(ValueError):
            l2t.classify_segment(-1.0, False, False)


class RequiredComponentsTest(unittest.TestCase):
    def test_deep_space_baseline_only(self):
        self.assertEqual(l2t.required_components("l2_deep_space"), l2t.DEEP_SPACE_COMPONENTS)

    def test_lobe_baseline_only(self):
        self.assertEqual(l2t.required_components("magnetotail_lobe"), l2t.DEEP_SPACE_COMPONENTS)

    def test_plasma_sheet_adds_charging_component(self):
        components = l2t.required_components("magnetotail_plasma_sheet")
        self.assertIn(l2t.MAGNETOTAIL_CHARGING_COMPONENT, components)
        for baseline_component in l2t.DEEP_SPACE_COMPONENTS:
            self.assertIn(baseline_component, components)

    def test_unknown_region_raises(self):
        with self.assertRaises(ValueError):
            l2t.required_components("leo")


class GeomagneticShieldingAppliesTest(unittest.TestCase):
    def test_false_for_every_known_region(self):
        for region in l2t.REGIONS:
            self.assertFalse(l2t.geomagnetic_shielding_applies(region))

    def test_unknown_region_raises(self):
        with self.assertRaises(ValueError):
            l2t.geomagnetic_shielding_applies("leo")


class BuildEnvironmentDefinitionTest(unittest.TestCase):
    def test_empty_segments_raises(self):
        with self.assertRaises(ValueError):
            l2t.build_environment_definition([])

    def test_pure_deep_space_timeline_has_no_charging_supplement(self):
        segments = [
            {"distance_re": 235.0, "plasma_sheet_crossing": False, "lobe_crossing": False},
            {"distance_re": 240.0, "plasma_sheet_crossing": False, "lobe_crossing": False},
        ]
        definition = l2t.build_environment_definition(segments)
        self.assertEqual(len(definition["segments"]), 2)
        self.assertFalse(definition["needs_magnetotail_charging_supplement"])
        self.assertEqual(set(definition["components_required"]), set(l2t.DEEP_SPACE_COMPONENTS))

    def test_timeline_with_plasma_sheet_crossing_needs_supplement(self):
        segments = [
            {"distance_re": 235.0, "plasma_sheet_crossing": False, "lobe_crossing": False},
            {"distance_re": 60.0, "plasma_sheet_crossing": True, "lobe_crossing": False},
        ]
        definition = l2t.build_environment_definition(segments)
        self.assertTrue(definition["needs_magnetotail_charging_supplement"])
        self.assertIn(l2t.MAGNETOTAIL_CHARGING_COMPONENT, definition["components_required"])
        regions = [segment["region"] for segment in definition["segments"]]
        self.assertEqual(regions, ["l2_deep_space", "magnetotail_plasma_sheet"])

    def test_segment_inside_trapped_belt_propagates_error(self):
        segments = [{"distance_re": 5.0, "plasma_sheet_crossing": True, "lobe_crossing": False}]
        with self.assertRaises(ValueError):
            l2t.build_environment_definition(segments)


class VerifyDefinitionCompleteTest(unittest.TestCase):
    def test_true_for_well_formed_definition(self):
        segments = [
            {"distance_re": 235.0, "plasma_sheet_crossing": False, "lobe_crossing": False},
            {"distance_re": 60.0, "plasma_sheet_crossing": True, "lobe_crossing": False},
        ]
        definition = l2t.build_environment_definition(segments)
        self.assertTrue(l2t.verify_definition_complete(definition))

    def test_false_when_a_segment_claims_geomagnetic_shielding(self):
        definition = l2t.build_environment_definition(
            [{"distance_re": 235.0, "plasma_sheet_crossing": False, "lobe_crossing": False}]
        )
        tampered_segment = dict(definition["segments"][0])
        tampered_segment["geomagnetic_shielding"] = True
        tampered = {
            "segments": [tampered_segment],
            "components_required": definition["components_required"],
            "needs_magnetotail_charging_supplement": definition["needs_magnetotail_charging_supplement"],
        }
        self.assertFalse(l2t.verify_definition_complete(tampered))

    def test_false_when_required_components_incomplete(self):
        definition = l2t.build_environment_definition(
            [{"distance_re": 60.0, "plasma_sheet_crossing": True, "lobe_crossing": False}]
        )
        truncated = {
            "segments": definition["segments"],
            "components_required": (l2t.DEEP_SPACE_COMPONENTS[0],),
            "needs_magnetotail_charging_supplement": definition["needs_magnetotail_charging_supplement"],
        }
        self.assertFalse(l2t.verify_definition_complete(truncated))


if __name__ == "__main__":
    unittest.main(verbosity=2)
