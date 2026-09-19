#!/usr/bin/env python3
"""Gate 3 contract test for e2040-device-requirements-specification-task.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_device_requirements_specification_task.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_device_requirements_specification_task_logic import (  # noqa: E402
    CONTENT_AREAS,
    ORIGINS,
    dangling_parents,
    has_open_marker,
    mandatory_sources,
    meets_coverage_target,
    normalize_area,
    normalize_origin,
    open_item_fraction,
    source_coverage,
    specify_requirement_set,
    uncovered_sources,
    unpopulated_areas,
    validate_requirements,
    validate_sources,
    within_open_item_budget,
)


def base_spec():
    return {
        "sources": [
            {"id": "SYS-1", "title": "deliver regulated power", "mandatory": True},
            {"id": "SYS-2", "title": "survive launch loads", "mandatory": True},
            {"id": "SYS-3", "title": "optional telemetry rate", "mandatory": False},
        ],
        "requirements": [
            {
                "id": "DEV-1",
                "area": "function",
                "origin": "allocated",
                "parents": ["SYS-1"],
                "statement": "the device shall provide a regulated 28 V output",
            },
            {
                "id": "DEV-2",
                "area": "performance",
                "origin": "allocated",
                "parents": ["SYS-1"],
                "statement": "the output shall stay within 2 per cent of nominal",
            },
            {
                "id": "DEV-3",
                "area": "environment",
                "origin": "allocated",
                "parents": ["SYS-2"],
                "statement": "the device shall withstand the qualification level",
            },
            {
                "id": "DEV-4",
                "area": "interface",
                "origin": "derived",
                "parents": [],
                "statement": "the connector shall be keyed to prevent mismating",
                "justification": "needed to make the harness build reversible",
            },
            {
                "id": "DEV-5",
                "area": "quality",
                "origin": "heritage",
                "parents": [],
                "statement": "the device shall reuse the qualified potting process",
                "heritage_item": "PCU-mk2 potting process",
            },
            {
                "id": "DEV-6",
                "area": "operation",
                "origin": "derived",
                "parents": [],
                "statement": "the device shall recover from an undervoltage trip",
                "justification": "operations concept requires autonomous recovery",
            },
        ],
        "declared_areas": [
            "function",
            "performance",
            "interface",
            "environment",
            "operation",
            "quality",
        ],
        "open_item_budget": 0.2,
        "coverage_target": 1.0,
    }


def codes(result):
    return sorted({finding["code"] for finding in result["findings"]})


class TestFolding(unittest.TestCase):
    def test_origin_alias_folds(self):
        self.assertEqual(normalize_origin("Flowed Down"), "allocated")

    def test_reused_folds_to_heritage(self):
        self.assertEqual(normalize_origin("reused"), "heritage")

    def test_unknown_origin_rejected(self):
        with self.assertRaises(ValueError):
            normalize_origin("invented")

    def test_area_alias_folds(self):
        self.assertEqual(normalize_area("Operational"), "operation")

    def test_unknown_area_rejected(self):
        with self.assertRaises(ValueError):
            normalize_area("marketing")

    def test_vocabularies_are_closed(self):
        self.assertEqual(len(ORIGINS), 3)
        self.assertEqual(len(CONTENT_AREAS), 6)


class TestOpenMarkers(unittest.TestCase):
    def test_tbd_is_an_open_marker(self):
        self.assertTrue(has_open_marker("the mass shall be below TBD kg"))

    def test_tbc_is_an_open_marker(self):
        self.assertTrue(has_open_marker("the rate shall be 5 Hz (TBC)"))

    def test_spelled_out_marker_is_caught(self):
        self.assertTrue(has_open_marker("the limit is to be confirmed"))

    def test_settled_statement_has_no_marker(self):
        self.assertFalse(
            has_open_marker("the device shall draw no more than 12 W")
        )

    def test_marker_is_not_matched_inside_a_word(self):
        self.assertFalse(has_open_marker("the STBD panel shall be instrumented"))

    def test_open_fraction_is_one_in_six(self):
        spec = base_spec()
        spec["requirements"][2]["statement"] = "shall withstand TBD g rms"
        requirements = validate_requirements(spec["requirements"])
        self.assertAlmostEqual(open_item_fraction(requirements), 1.0 / 6.0, places=9)

    def test_open_fraction_needs_a_requirement(self):
        with self.assertRaises(ValueError):
            open_item_fraction([])


class TestUpwardTrace(unittest.TestCase):
    def test_allocated_without_parent_is_a_finding(self):
        spec = base_spec()
        spec["requirements"][0]["parents"] = []
        result = specify_requirement_set(spec)
        self.assertIn("allocated-requirement-without-parent", codes(result))
        self.assertEqual(result["orphan_requirements"], ["DEV-1"])

    def test_derived_without_justification_is_a_finding(self):
        spec = base_spec()
        spec["requirements"][3]["justification"] = ""
        result = specify_requirement_set(spec)
        self.assertIn("derived-requirement-without-justification", codes(result))

    def test_heritage_without_source_item_is_a_finding(self):
        spec = base_spec()
        spec["requirements"][4]["heritage_item"] = ""
        result = specify_requirement_set(spec)
        self.assertIn("heritage-requirement-without-source-item", codes(result))

    def test_dangling_parent_is_a_finding(self):
        spec = base_spec()
        spec["requirements"][0]["parents"] = ["SYS-9"]
        result = specify_requirement_set(spec)
        self.assertIn("parent-not-in-source-set", codes(result))

    def test_dangling_parents_listed_with_their_requirement(self):
        spec = base_spec()
        spec["requirements"][1]["parents"] = ["SYS-1", "SYS-7"]
        sources = validate_sources(spec["sources"])
        requirements = validate_requirements(spec["requirements"])
        self.assertEqual(
            dangling_parents(sources, requirements),
            [{"requirement": "DEV-2", "parent": "SYS-7"}],
        )

    def test_repeated_parent_is_folded_once(self):
        requirements = validate_requirements(
            [
                {
                    "id": "DEV-1",
                    "area": "function",
                    "origin": "allocated",
                    "parents": ["SYS-1", "SYS-1"],
                }
            ]
        )
        self.assertEqual(requirements[0]["parents"], ["SYS-1"])


class TestDownwardTrace(unittest.TestCase):
    def test_full_coverage_of_mandatory_sources(self):
        spec = base_spec()
        sources = validate_sources(spec["sources"])
        requirements = validate_requirements(spec["requirements"])
        self.assertAlmostEqual(source_coverage(sources, requirements), 1.0, places=9)

    def test_uncovered_mandatory_source_is_a_finding(self):
        spec = base_spec()
        spec["requirements"][2]["parents"] = ["SYS-1"]
        result = specify_requirement_set(spec)
        self.assertIn("source-requirement-uncovered", codes(result))
        self.assertEqual(result["uncovered_sources"], ["SYS-2"])

    def test_coverage_is_one_in_two_when_one_source_is_dropped(self):
        spec = base_spec()
        spec["requirements"][2]["parents"] = ["SYS-1"]
        sources = validate_sources(spec["sources"])
        requirements = validate_requirements(spec["requirements"])
        self.assertAlmostEqual(
            source_coverage(sources, requirements), 0.5, places=9
        )

    def test_optional_source_is_not_required_to_be_covered(self):
        spec = base_spec()
        sources = validate_sources(spec["sources"])
        requirements = validate_requirements(spec["requirements"])
        self.assertEqual(uncovered_sources(sources, requirements), [])
        self.assertEqual(len(mandatory_sources(sources)), 2)

    def test_coverage_needs_a_mandatory_source(self):
        spec = base_spec()
        for source in spec["sources"]:
            source["mandatory"] = False
        with self.assertRaises(ValueError):
            specify_requirement_set(spec)


class TestAreas(unittest.TestCase):
    def test_unpopulated_declared_area_is_a_finding(self):
        spec = base_spec()
        spec["requirements"] = spec["requirements"][:3]
        result = specify_requirement_set(spec)
        self.assertIn("content-area-unpopulated", codes(result))
        self.assertIn("quality", result["unpopulated_areas"])

    def test_undeclared_area_is_not_demanded(self):
        spec = base_spec()
        spec["declared_areas"] = ["function", "performance", "environment"]
        spec["requirements"] = spec["requirements"][:3]
        requirements = validate_requirements(spec["requirements"])
        self.assertEqual(
            unpopulated_areas(requirements, ["function", "performance"]), []
        )

    def test_empty_declared_area_list_rejected(self):
        spec = base_spec()
        spec["declared_areas"] = []
        with self.assertRaises(ValueError):
            specify_requirement_set(spec)


class TestBoundaryPortability(unittest.TestCase):
    def test_coverage_exactly_on_target_passes(self):
        self.assertTrue(meets_coverage_target(2.0 / 3.0, 2.0 / 3.0))

    def test_coverage_below_target_fails(self):
        self.assertFalse(meets_coverage_target(0.5, 0.75))

    def test_open_fraction_exactly_on_budget_is_inside(self):
        self.assertTrue(within_open_item_budget(1.0 / 5.0, 0.2))

    def test_open_fraction_above_budget_is_outside(self):
        self.assertFalse(within_open_item_budget(0.5, 0.2))

    def test_open_budget_exceeded_is_a_finding(self):
        spec = base_spec()
        spec["requirements"][0]["statement"] = "the output shall be TBD volts"
        spec["requirements"][1]["statement"] = "the ripple shall be TBC"
        spec["open_item_budget"] = 0.2
        result = specify_requirement_set(spec)
        self.assertIn("open-item-budget-exceeded", codes(result))

    def test_budget_outside_unit_interval_rejected(self):
        spec = base_spec()
        spec["open_item_budget"] = 1.4
        with self.assertRaises(ValueError):
            specify_requirement_set(spec)


class TestValidation(unittest.TestCase):
    def test_duplicate_source_id_rejected(self):
        spec = base_spec()
        spec["sources"].append(dict(spec["sources"][0]))
        with self.assertRaises(ValueError):
            specify_requirement_set(spec)

    def test_duplicate_requirement_id_rejected(self):
        spec = base_spec()
        spec["requirements"].append(dict(spec["requirements"][0]))
        with self.assertRaises(ValueError):
            specify_requirement_set(spec)

    def test_unknown_requirement_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_requirements(
                [{"id": "DEV-1", "area": "function", "origin": "derived", "owner": "x"}]
            )

    def test_unknown_spec_key_rejected(self):
        spec = base_spec()
        spec["annex"] = "A"
        with self.assertRaises(ValueError):
            specify_requirement_set(spec)

    def test_missing_requirements_rejected(self):
        spec = base_spec()
        del spec["requirements"]
        with self.assertRaises(ValueError):
            specify_requirement_set(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            specify_requirement_set([("sources", [])])


class TestVerdict(unittest.TestCase):
    def test_clean_set_is_baseline_ready(self):
        result = specify_requirement_set(base_spec())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["baseline_ready"])
        self.assertEqual(result["requirement_count"], 6)
        self.assertEqual(result["mandatory_source_count"], 2)

    def test_any_finding_withholds_the_baseline(self):
        spec = base_spec()
        spec["requirements"][3]["justification"] = ""
        result = specify_requirement_set(spec)
        self.assertFalse(result["baseline_ready"])


if __name__ == "__main__":
    unittest.main()
