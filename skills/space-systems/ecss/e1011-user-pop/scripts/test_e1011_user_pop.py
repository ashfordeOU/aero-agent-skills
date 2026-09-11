#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-11 §4.2.1.3 user population definition.

Exercises scripts/e1011_user_pop_logic.py (stdlib unittest, offline).
Contract: a user group type is categorized as exactly one of crew,
ground_operator, or maintainer, and an unrecognized type raises; a
capability range is valid when min <= max and both values fall within the
dimension's established bounds, and is flagged otherwise; an unrecognized
dimension is flagged; a population with a valid type and consistent ranges
passes validation; a design parameter within the population's capability
range returns True and outside it returns False; an inverted capability
range in check_design_parameter raises; the coverage check returns missing
types when fewer than all required types are present; the full population-set
review surfaces both per-population violations and coverage gaps; and the
set is compliant only when both lists are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1011_user_pop_logic as up  # noqa: E402


class CategorizeUserGroupTest(unittest.TestCase):
    def test_crew_is_valid(self):
        self.assertEqual(up.categorize_user_group("crew"), "crew")

    def test_ground_operator_is_valid(self):
        self.assertEqual(up.categorize_user_group("ground_operator"), "ground_operator")

    def test_maintainer_is_valid(self):
        self.assertEqual(up.categorize_user_group("maintainer"), "maintainer")

    def test_unknown_group_raises(self):
        with self.assertRaises(ValueError):
            up.categorize_user_group("passenger")

    def test_empty_string_raises(self):
        with self.assertRaises(ValueError):
            up.categorize_user_group("")


class ValidateCapabilityRangeTest(unittest.TestCase):
    def test_valid_reach_range_no_violations(self):
        self.assertEqual(
            up.validate_capability_range("physical_reach_mm", 500.0, 900.0), []
        )

    def test_valid_cognitive_load_range_no_violations(self):
        self.assertEqual(
            up.validate_capability_range("cognitive_load_rating", 1.0, 8.0), []
        )

    def test_inverted_range_flagged(self):
        violations = up.validate_capability_range("physical_reach_mm", 900.0, 500.0)
        self.assertTrue(any(v["issue"] == "inverted_range" for v in violations))

    def test_range_min_below_bounds_flagged(self):
        violations = up.validate_capability_range("physical_reach_mm", -1.0, 800.0)
        self.assertTrue(
            any(v["issue"] == "range_exceeds_dimension_bounds" for v in violations)
        )

    def test_range_max_above_bounds_flagged(self):
        violations = up.validate_capability_range("physical_reach_mm", 500.0, 9999.0)
        self.assertTrue(
            any(v["issue"] == "range_exceeds_dimension_bounds" for v in violations)
        )

    def test_unrecognized_dimension_flagged(self):
        violations = up.validate_capability_range("telepathy_rating", 1.0, 5.0)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "unrecognized_dimension")

    def test_boundary_values_accepted(self):
        bounds = up.DIMENSION_BOUNDS["training_level"]
        self.assertEqual(
            up.validate_capability_range("training_level", bounds[0], bounds[1]), []
        )


class ValidatePopulationTest(unittest.TestCase):
    def test_valid_population_no_violations(self):
        pop = {
            "population_id": "crew-1",
            "type": "crew",
            "capability_ranges": {
                "physical_reach_mm": {"min": 600.0, "max": 850.0},
                "training_level": {"min": 3.0, "max": 4.0},
            },
        }
        self.assertEqual(up.validate_population(pop), [])

    def test_invalid_type_flagged(self):
        pop = {
            "population_id": "unknown-1",
            "type": "robot",
            "capability_ranges": {},
        }
        violations = up.validate_population(pop)
        self.assertTrue(
            any(v["issue"] == "unrecognized_population_type" for v in violations)
        )

    def test_population_id_included_in_violation(self):
        pop = {
            "population_id": "bad-pop",
            "type": "alien",
            "capability_ranges": {},
        }
        violations = up.validate_population(pop)
        self.assertTrue(all(v.get("population") == "bad-pop" for v in violations))

    def test_inverted_range_in_population_flagged(self):
        pop = {
            "population_id": "crew-2",
            "type": "crew",
            "capability_ranges": {
                "cognitive_load_rating": {"min": 9.0, "max": 3.0},
            },
        }
        violations = up.validate_population(pop)
        self.assertTrue(any(v["issue"] == "inverted_range" for v in violations))


class CheckDesignParameterTest(unittest.TestCase):
    def test_value_within_range_returns_true(self):
        self.assertTrue(up.check_design_parameter(700.0, 600.0, 900.0))

    def test_value_at_minimum_returns_true(self):
        self.assertTrue(up.check_design_parameter(600.0, 600.0, 900.0))

    def test_value_at_maximum_returns_true(self):
        self.assertTrue(up.check_design_parameter(900.0, 600.0, 900.0))

    def test_value_below_range_returns_false(self):
        self.assertFalse(up.check_design_parameter(500.0, 600.0, 900.0))

    def test_value_above_range_returns_false(self):
        self.assertFalse(up.check_design_parameter(1000.0, 600.0, 900.0))

    def test_inverted_range_raises(self):
        with self.assertRaises(ValueError):
            up.check_design_parameter(700.0, 900.0, 600.0)


class PopulationCoverageCheckTest(unittest.TestCase):
    def test_all_types_present_returns_empty(self):
        populations = [
            {"type": "crew"},
            {"type": "ground_operator"},
            {"type": "maintainer"},
        ]
        self.assertEqual(up.population_coverage_check(populations), [])

    def test_missing_maintainer_returned(self):
        populations = [{"type": "crew"}, {"type": "ground_operator"}]
        missing = up.population_coverage_check(populations)
        self.assertIn("maintainer", missing)

    def test_empty_population_list_returns_all_types(self):
        missing = up.population_coverage_check([])
        self.assertEqual(sorted(missing), sorted(up.POPULATION_TYPES))

    def test_custom_required_types(self):
        populations = [{"type": "crew"}]
        missing = up.population_coverage_check(populations, ["crew", "ground_operator"])
        self.assertEqual(missing, ["ground_operator"])


class PopulationSetReviewTest(unittest.TestCase):
    def _make_valid_set(self):
        return [
            {
                "population_id": "crew-1",
                "type": "crew",
                "capability_ranges": {
                    "physical_reach_mm": {"min": 650.0, "max": 880.0},
                    "training_level": {"min": 3.0, "max": 4.0},
                },
            },
            {
                "population_id": "gnd-1",
                "type": "ground_operator",
                "capability_ranges": {
                    "cognitive_load_rating": {"min": 1.0, "max": 7.0},
                    "training_level": {"min": 2.0, "max": 4.0},
                },
            },
            {
                "population_id": "mnt-1",
                "type": "maintainer",
                "capability_ranges": {
                    "physical_reach_mm": {"min": 550.0, "max": 900.0},
                    "training_level": {"min": 2.0, "max": 3.0},
                },
            },
        ]

    def test_compliant_set_has_empty_violations(self):
        review = up.population_set_review(self._make_valid_set())
        self.assertEqual(review["populations"], [])
        self.assertEqual(review["coverage"], [])

    def test_is_compliant_true_for_valid_set(self):
        review = up.population_set_review(self._make_valid_set())
        self.assertTrue(up.is_population_set_compliant(review))

    def test_missing_type_surfaces_in_coverage(self):
        pops = [p for p in self._make_valid_set() if p["type"] != "maintainer"]
        review = up.population_set_review(pops)
        self.assertTrue(
            any(v["type"] == "maintainer" for v in review["coverage"])
        )
        self.assertFalse(up.is_population_set_compliant(review))

    def test_invalid_population_type_surfaces_in_populations(self):
        pops = self._make_valid_set()
        pops[0] = dict(pops[0], type="cyborg")
        review = up.population_set_review(pops)
        self.assertTrue(
            any(v["issue"] == "unrecognized_population_type" for v in review["populations"])
        )

    def test_inverted_range_surfaces_in_populations(self):
        pops = self._make_valid_set()
        pops[1] = dict(
            pops[1],
            capability_ranges={"cognitive_load_rating": {"min": 9.0, "max": 2.0}},
        )
        review = up.population_set_review(pops)
        self.assertTrue(
            any(v["issue"] == "inverted_range" for v in review["populations"])
        )

    def test_is_compliant_false_when_violations_present(self):
        pops = [p for p in self._make_valid_set() if p["type"] != "crew"]
        review = up.population_set_review(pops)
        self.assertFalse(up.is_population_set_compliant(review))

    def test_empty_population_list_has_all_coverage_gaps(self):
        review = up.population_set_review([])
        missing_types = {v["type"] for v in review["coverage"]}
        self.assertEqual(missing_types, up.POPULATION_TYPES)


if __name__ == "__main__":
    unittest.main()
