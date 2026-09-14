#!/usr/bin/env python3
"""Contract test for the photovoltaic assembly source control drawing (offline)."""

import copy
import unittest

from e2008_photovoltaic_assembly_control_drawing_logic import (
    BLOCK_ABSENT,
    BLOCK_OPEN,
    BLOCK_SPECIFIED,
    BLOCK_WEIGHTS,
    CITED_CURRENT,
    CITED_NOT_GOVERNING,
    CITED_OFF_ISSUE,
    DRAWING_ISSUE_STATES,
    DRAWING_NOT_RELEASABLE,
    DRAWING_OPEN_ITEMS,
    DRAWING_RELEASABLE,
    MAX_RELATIVE_TOLERANCE,
    REQUIRED_CONTENT_BLOCKS,
    audit_photovoltaic_assembly_drawing,
    completeness_share,
    constituent_drawing_standing,
    content_block_state,
    dimension_control,
)

CONTENT_BLOCKS = [
    {"block": name, "present": True, "specified": True, "open_items": 0}
    for name, _weight in REQUIRED_CONTENT_BLOCKS
]

DIMENSIONS = [
    {"name": "assembly-length", "nominal": 400.0, "tolerance": 0.5},
    {"name": "assembly-width", "nominal": 200.0, "tolerance": 0.5},
    {"name": "stack-height", "nominal": 0.60, "tolerance": 0.02},
]

CONSTITUENTS = [
    {
        "item": "solar-cell-assembly",
        "drawing": "SCA-1001",
        "issue_state": "released",
        "cited_issue": "C",
        "released_issue": "C",
    },
    {
        "item": "interconnector",
        "drawing": "ICN-2002",
        "issue_state": "released",
        "cited_issue": "B",
        "released_issue": "B",
    },
    {
        "item": "substrate-adhesive",
        "drawing": "ADH-3003",
        "issue_state": "released",
        "cited_issue": "A",
        "released_issue": "A",
    },
]

CLEAN_SPEC = {
    "drawing": "PVA-SCD-0001",
    "content_blocks": CONTENT_BLOCKS,
    "dimensions": DIMENSIONS,
    "constituent_items": CONSTITUENTS,
}

TOTAL_WEIGHT = float(sum(BLOCK_WEIGHTS.values()))


def _spec(**overrides):
    item = copy.deepcopy(CLEAN_SPEC)
    for key, value in overrides.items():
        if value is None and key in item:
            del item[key]
        else:
            item[key] = value
    return item


def _blocks(**per_block):
    out = copy.deepcopy(CONTENT_BLOCKS)
    for record in out:
        if record["block"] in per_block:
            record.update(per_block[record["block"]])
    return out


class ContentBlockTests(unittest.TestCase):
    def test_a_present_and_specified_block_controls_its_content(self):
        result = content_block_state(CONTENT_BLOCKS[0])
        self.assertEqual(result["state"], BLOCK_SPECIFIED)
        self.assertEqual(result["findings"], [])

    def test_a_block_missing_from_the_drawing_is_absent(self):
        result = content_block_state(
            {"block": "mass-and-mass-distribution", "present": False, "specified": False}
        )
        self.assertEqual(result["state"], BLOCK_ABSENT)
        self.assertTrue(any("not on the drawing" in f for f in result["findings"]))

    def test_a_drawn_but_unspecified_block_is_open_not_specified(self):
        result = content_block_state(
            {"block": "marking-and-traceability", "present": True, "specified": False}
        )
        self.assertEqual(result["state"], BLOCK_OPEN)

    def test_a_specified_block_carrying_open_items_is_still_open(self):
        result = content_block_state(
            {
                "block": "assembly-identification",
                "present": True,
                "specified": True,
                "open_items": 2,
            }
        )
        self.assertEqual(result["state"], BLOCK_OPEN)
        self.assertEqual(result["open_items"], 2)

    def test_a_non_mapping_block_record_is_rejected(self):
        with self.assertRaises(ValueError):
            content_block_state(["assembly-identification", True, True])

    def test_a_block_record_missing_a_key_is_rejected(self):
        with self.assertRaises(ValueError):
            content_block_state({"block": "assembly-identification", "present": True})

    def test_a_non_boolean_presence_is_rejected(self):
        with self.assertRaises(ValueError):
            content_block_state(
                {"block": "assembly-identification", "present": "yes", "specified": True}
            )

    def test_a_negative_open_item_count_is_rejected(self):
        with self.assertRaises(ValueError):
            content_block_state(
                {
                    "block": "assembly-identification",
                    "present": True,
                    "specified": True,
                    "open_items": -1,
                }
            )


class DimensionControlTests(unittest.TestCase):
    def test_a_toleranced_dimension_is_controlled_and_carries_bounds(self):
        result = dimension_control(DIMENSIONS[0])
        self.assertTrue(result["controlled"])
        self.assertAlmostEqual(result["lower"], 399.5, places=9)
        self.assertAlmostEqual(result["upper"], 400.5, places=9)

    def test_a_nominal_with_no_tolerance_controls_nothing(self):
        result = dimension_control({"name": "cell-pitch", "nominal": 42.0})
        self.assertFalse(result["controlled"])
        self.assertTrue(any("not a control" in f for f in result["findings"]))

    def test_a_reference_dimension_controls_nothing(self):
        result = dimension_control(
            {"name": "harness-routing-length", "nominal": 120.0, "reference": True}
        )
        self.assertFalse(result["controlled"])
        self.assertTrue(result["reference"])

    def test_a_zero_width_band_controls_nothing(self):
        result = dimension_control(
            {"name": "coverglass-edge-offset", "nominal": 1.0, "tolerance": 0.0}
        )
        self.assertFalse(result["controlled"])
        self.assertFalse(result["over_wide"])

    def test_a_band_exactly_on_the_relative_cap_is_still_a_control(self):
        result = dimension_control(
            {"name": "stack-height", "nominal": 40.0, "tolerance": 4.0}
        )
        self.assertAlmostEqual(
            result["relative_tolerance"], MAX_RELATIVE_TOLERANCE, places=9
        )
        self.assertTrue(result["controlled"])
        self.assertFalse(result["over_wide"])

    def test_a_band_past_the_relative_cap_is_a_note_not_a_control(self):
        result = dimension_control(
            {"name": "stack-height", "nominal": 40.0, "tolerance": 8.0}
        )
        self.assertTrue(result["over_wide"])
        self.assertFalse(result["controlled"])

    def test_a_zero_nominal_dimension_is_rejected(self):
        with self.assertRaises(ValueError):
            dimension_control({"name": "gap", "nominal": 0.0, "tolerance": 0.1})

    def test_a_negative_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            dimension_control({"name": "gap", "nominal": 1.0, "tolerance": -0.1})

    def test_a_dimension_missing_its_nominal_is_rejected(self):
        with self.assertRaises(ValueError):
            dimension_control({"name": "gap", "tolerance": 0.1})


class ConstituentStandingTests(unittest.TestCase):
    def test_a_released_drawing_cited_at_its_released_issue_governs(self):
        result = constituent_drawing_standing(CONSTITUENTS[0])
        self.assertEqual(result["standing"], CITED_CURRENT)
        self.assertEqual(result["findings"], [])

    def test_a_draft_constituent_drawing_governs_nothing(self):
        item = dict(CONSTITUENTS[0], issue_state="draft")
        self.assertEqual(
            constituent_drawing_standing(item)["standing"], CITED_NOT_GOVERNING
        )

    def test_a_cancelled_constituent_drawing_governs_nothing(self):
        item = dict(CONSTITUENTS[0], issue_state="cancelled")
        self.assertEqual(
            constituent_drawing_standing(item)["standing"], CITED_NOT_GOVERNING
        )

    def test_a_superseded_constituent_drawing_leaves_a_step_to_disposition(self):
        item = dict(CONSTITUENTS[0], issue_state="superseded", released_issue="D")
        result = constituent_drawing_standing(item)
        self.assertEqual(result["standing"], CITED_OFF_ISSUE)
        self.assertTrue(any("superseded" in f for f in result["findings"]))

    def test_a_citation_at_an_issue_that_is_not_the_released_one_is_off_issue(self):
        item = dict(CONSTITUENTS[0], cited_issue="B")
        self.assertEqual(
            constituent_drawing_standing(item)["standing"], CITED_OFF_ISSUE
        )

    def test_every_declared_issue_state_resolves_to_a_standing(self):
        for state in DRAWING_ISSUE_STATES:
            item = dict(CONSTITUENTS[0], issue_state=state)
            self.assertIn(
                constituent_drawing_standing(item)["standing"],
                (CITED_CURRENT, CITED_OFF_ISSUE, CITED_NOT_GOVERNING),
            )

    def test_an_unknown_issue_state_is_rejected(self):
        item = dict(CONSTITUENTS[0], issue_state="in-review-probably")
        with self.assertRaises(ValueError):
            constituent_drawing_standing(item)

    def test_a_blank_drawing_number_is_rejected(self):
        item = dict(CONSTITUENTS[0], drawing="   ")
        with self.assertRaises(ValueError):
            constituent_drawing_standing(item)


class CompletenessShareTests(unittest.TestCase):
    def test_a_fully_specified_block_set_is_complete(self):
        blocks = [content_block_state(r) for r in CONTENT_BLOCKS]
        self.assertAlmostEqual(completeness_share(blocks), 1.0, places=9)

    def test_an_open_block_costs_exactly_its_own_weight(self):
        records = _blocks(
            **{"handling-and-storage-constraint": {"specified": False}}
        )
        blocks = [content_block_state(r) for r in records]
        expected = (TOTAL_WEIGHT - 1.0) / TOTAL_WEIGHT
        self.assertAlmostEqual(completeness_share(blocks), expected, places=9)

    def test_a_heavier_block_costs_more_than_a_lighter_one(self):
        light = [
            content_block_state(r)
            for r in _blocks(**{"handling-and-storage-constraint": {"present": False}})
        ]
        heavy = [
            content_block_state(r)
            for r in _blocks(**{"constituent-item-list": {"present": False}})
        ]
        self.assertGreater(completeness_share(light), completeness_share(heavy))

    def test_a_block_outside_the_required_set_earns_no_weight(self):
        extra = content_block_state(
            {"block": "colour-of-the-title-block", "present": True, "specified": True}
        )
        blocks = [content_block_state(r) for r in CONTENT_BLOCKS] + [extra]
        self.assertAlmostEqual(completeness_share(blocks), 1.0, places=9)

    def test_an_empty_block_set_earns_nothing(self):
        self.assertAlmostEqual(completeness_share([]), 0.0, places=9)

    def test_a_non_sequence_block_set_is_rejected(self):
        with self.assertRaises(ValueError):
            completeness_share({"block": "assembly-identification"})


class DrawingAuditTests(unittest.TestCase):
    def test_a_complete_drawing_package_is_releasable(self):
        result = audit_photovoltaic_assembly_drawing(_spec())
        self.assertEqual(result["verdict"], DRAWING_RELEASABLE)
        self.assertAlmostEqual(result["completeness_share"], 1.0, places=9)
        self.assertEqual(result["findings"], [])

    def test_a_required_block_the_package_never_mentions_is_reported(self):
        records = [
            r for r in copy.deepcopy(CONTENT_BLOCKS)
            if r["block"] != "marking-and-traceability"
        ]
        result = audit_photovoltaic_assembly_drawing(_spec(content_blocks=records))
        self.assertEqual(result["missing_blocks"], ["marking-and-traceability"])
        self.assertEqual(result["verdict"], DRAWING_NOT_RELEASABLE)

    def test_an_absent_block_stops_the_release(self):
        records = _blocks(
            **{"electrical-output-at-reference-conditions": {"present": False, "specified": False}}
        )
        result = audit_photovoltaic_assembly_drawing(_spec(content_blocks=records))
        self.assertEqual(
            result["absent_blocks"], ["electrical-output-at-reference-conditions"]
        )
        self.assertEqual(result["verdict"], DRAWING_NOT_RELEASABLE)

    def test_an_open_block_releases_only_against_open_items(self):
        records = _blocks(**{"mass-and-mass-distribution": {"open_items": 1}})
        result = audit_photovoltaic_assembly_drawing(
            _spec(content_blocks=records, required_completeness_share=0.5)
        )
        self.assertEqual(result["open_blocks"], ["mass-and-mass-distribution"])
        self.assertEqual(result["verdict"], DRAWING_OPEN_ITEMS)

    def test_a_dimension_without_a_tolerance_stops_the_release(self):
        dims = copy.deepcopy(DIMENSIONS)
        del dims[1]["tolerance"]
        result = audit_photovoltaic_assembly_drawing(_spec(dimensions=dims))
        self.assertEqual(result["uncontrolled_dimensions"], ["assembly-width"])
        self.assertEqual(result["verdict"], DRAWING_NOT_RELEASABLE)

    def test_an_over_wide_band_stops_the_release_as_an_uncontrolled_dimension(self):
        dims = copy.deepcopy(DIMENSIONS)
        dims[2]["tolerance"] = 0.30
        result = audit_photovoltaic_assembly_drawing(_spec(dimensions=dims))
        self.assertEqual(result["over_wide_dimensions"], ["stack-height"])
        self.assertEqual(result["verdict"], DRAWING_NOT_RELEASABLE)

    def test_a_reference_dimension_does_not_stop_the_release(self):
        dims = copy.deepcopy(DIMENSIONS)
        dims.append({"name": "harness-length", "nominal": 300.0, "reference": True})
        result = audit_photovoltaic_assembly_drawing(_spec(dimensions=dims))
        self.assertEqual(result["uncontrolled_dimensions"], [])
        self.assertEqual(result["verdict"], DRAWING_RELEASABLE)

    def test_a_constituent_cited_on_a_draft_drawing_stops_the_release(self):
        items = copy.deepcopy(CONSTITUENTS)
        items[1]["issue_state"] = "draft"
        result = audit_photovoltaic_assembly_drawing(_spec(constituent_items=items))
        self.assertEqual(result["not_governing_constituents"], ["interconnector"])
        self.assertEqual(result["verdict"], DRAWING_NOT_RELEASABLE)

    def test_an_off_issue_constituent_releases_only_against_open_items(self):
        items = copy.deepcopy(CONSTITUENTS)
        items[0]["cited_issue"] = "B"
        result = audit_photovoltaic_assembly_drawing(_spec(constituent_items=items))
        self.assertEqual(result["off_issue_constituents"], ["solar-cell-assembly"])
        self.assertEqual(result["verdict"], DRAWING_OPEN_ITEMS)

    def test_a_completeness_share_exactly_on_its_threshold_is_met(self):
        records = _blocks(
            **{"handling-and-storage-constraint": {"specified": False}}
        )
        expected = (TOTAL_WEIGHT - 1.0) / TOTAL_WEIGHT
        result = audit_photovoltaic_assembly_drawing(
            _spec(content_blocks=records, required_completeness_share=expected)
        )
        self.assertAlmostEqual(result["completeness_share"], expected, places=9)
        self.assertEqual(result["verdict"], DRAWING_OPEN_ITEMS)

    def test_a_completeness_share_under_its_threshold_stops_the_release(self):
        records = _blocks(
            **{"handling-and-storage-constraint": {"specified": False}}
        )
        result = audit_photovoltaic_assembly_drawing(
            _spec(content_blocks=records, required_completeness_share=1.0)
        )
        self.assertEqual(result["verdict"], DRAWING_NOT_RELEASABLE)

    def test_the_same_block_graded_twice_is_rejected(self):
        records = copy.deepcopy(CONTENT_BLOCKS)
        records.append(copy.deepcopy(CONTENT_BLOCKS[0]))
        with self.assertRaises(ValueError):
            audit_photovoltaic_assembly_drawing(_spec(content_blocks=records))

    def test_a_drawing_showing_no_dimension_is_rejected(self):
        with self.assertRaises(ValueError):
            audit_photovoltaic_assembly_drawing(_spec(dimensions=[]))

    def test_an_assembly_with_no_constituent_item_is_rejected(self):
        with self.assertRaises(ValueError):
            audit_photovoltaic_assembly_drawing(_spec(constituent_items=[]))

    def test_a_threshold_outside_the_unit_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            audit_photovoltaic_assembly_drawing(
                _spec(required_completeness_share=1.2)
            )

    def test_a_non_mapping_spec_is_rejected(self):
        with self.assertRaises(ValueError):
            audit_photovoltaic_assembly_drawing([CLEAN_SPEC])

    def test_a_spec_missing_its_drawing_number_is_rejected(self):
        with self.assertRaises(ValueError):
            audit_photovoltaic_assembly_drawing(_spec(drawing=None))


if __name__ == "__main__":
    unittest.main(verbosity=1)
