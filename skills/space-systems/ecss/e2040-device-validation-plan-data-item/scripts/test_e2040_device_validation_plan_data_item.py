"""Contract tests for the Annex D device validation plan data-item logic."""

import unittest

from e2040_device_validation_plan_data_item_logic import (
    APPROACHES,
    COVERAGE_TOLERANCE,
    REQUIRED_SECTIONS,
    approach_shortfalls,
    assess_validation_plan,
    coverage_matrix,
    criterion_measurability,
    evaluate_criterion,
    missing_sections,
    validate_activities,
    validate_activity,
    validate_criterion,
    validate_use_case,
    validate_use_cases,
    weighted_coverage_fraction,
)

ALL_SECTIONS = list(REQUIRED_SECTIONS)

USE_CASES = [
    {"id": "UC-1", "criticality_weight": 4.0, "safety_driving": True},
    {"id": "UC-2", "criticality_weight": 2.0, "safety_driving": False},
    {"id": "UC-3", "criticality_weight": 2.0, "safety_driving": False},
]

GOOD_CRITERION = {"comparator": "<=", "bound": 12.5, "unit": "mA"}


def activity(identifier, approach, covers, criterion=None):
    return {
        "id": identifier,
        "approach": approach,
        "covers": covers,
        "criterion": dict(criterion or GOOD_CRITERION),
    }


class SectionTests(unittest.TestCase):
    def test_complete_section_list_has_no_gap(self):
        self.assertEqual(missing_sections(ALL_SECTIONS), [])

    def test_missing_section_is_named(self):
        partial = [s for s in ALL_SECTIONS if s != "pass-criteria"]
        self.assertEqual(missing_sections(partial), ["pass-criteria"])

    def test_section_match_ignores_case(self):
        shouted = [s.upper() for s in ALL_SECTIONS]
        self.assertEqual(missing_sections(shouted), [])

    def test_extra_sections_are_not_a_gap(self):
        self.assertEqual(missing_sections(ALL_SECTIONS + ["annexes"]), [])

    def test_non_sequence_section_list_rejected(self):
        with self.assertRaises(ValueError):
            missing_sections("scope")

    def test_empty_section_name_rejected(self):
        with self.assertRaises(ValueError):
            missing_sections(["scope", "  "])


class UseCaseValidationTests(unittest.TestCase):
    def test_normalized_record_carries_weight_as_float(self):
        record = validate_use_case({"id": " UC-9 ", "criticality_weight": 3, "safety_driving": False})
        self.assertEqual(record["id"], "UC-9")
        self.assertAlmostEqual(record["criticality_weight"], 3.0)

    def test_zero_weight_rejected(self):
        with self.assertRaises(ValueError):
            validate_use_case({"id": "UC-9", "criticality_weight": 0.0, "safety_driving": False})

    def test_negative_weight_rejected(self):
        with self.assertRaises(ValueError):
            validate_use_case({"id": "UC-9", "criticality_weight": -1.0, "safety_driving": False})

    def test_missing_safety_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_use_case({"id": "UC-9", "criticality_weight": 1.0})

    def test_non_boolean_safety_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_use_case({"id": "UC-9", "criticality_weight": 1.0, "safety_driving": "yes"})

    def test_duplicate_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_use_cases(USE_CASES + [dict(USE_CASES[0])])

    def test_empty_use_case_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_use_cases([])


class CriterionTests(unittest.TestCase):
    def test_normalized_criterion_defaults_tolerance_to_none(self):
        record = validate_criterion(GOOD_CRITERION)
        self.assertIsNone(record["tolerance"])

    def test_unknown_comparator_rejected(self):
        with self.assertRaises(ValueError):
            validate_criterion({"comparator": "=~", "bound": 1.0, "unit": "V"})

    def test_non_finite_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_criterion({"comparator": "<=", "bound": float("inf"), "unit": "V"})

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_criterion({"comparator": "==", "bound": 1.0, "unit": "V", "tolerance": -0.1})

    def test_placeholder_unit_is_unmeasurable(self):
        record = validate_criterion({"comparator": "<=", "bound": 1.0, "unit": "TBD"})
        measurable, reason = criterion_measurability(record)
        self.assertFalse(measurable)
        self.assertIn("placeholder", reason)

    def test_equality_without_tolerance_is_unmeasurable(self):
        record = validate_criterion({"comparator": "==", "bound": 1.0, "unit": "V"})
        self.assertFalse(criterion_measurability(record)[0])

    def test_equality_with_tolerance_is_measurable(self):
        record = validate_criterion(
            {"comparator": "==", "bound": 1.0, "unit": "V", "tolerance": 0.05}
        )
        self.assertTrue(criterion_measurability(record)[0])

    def test_value_at_an_inclusive_bound_passes(self):
        record = validate_criterion(GOOD_CRITERION)
        self.assertTrue(evaluate_criterion(record, 12.5))

    def test_value_past_an_inclusive_bound_fails(self):
        record = validate_criterion(GOOD_CRITERION)
        self.assertFalse(evaluate_criterion(record, 13.0))

    def test_value_inside_an_equality_tolerance_passes(self):
        record = validate_criterion(
            {"comparator": "==", "bound": 1.0, "unit": "V", "tolerance": 0.05}
        )
        self.assertTrue(evaluate_criterion(record, 1.04))
        self.assertFalse(evaluate_criterion(record, 1.06))

    def test_unmeasurable_criterion_cannot_be_evaluated(self):
        record = validate_criterion({"comparator": "==", "bound": 1.0, "unit": "V"})
        with self.assertRaises(ValueError):
            evaluate_criterion(record, 1.0)


class ActivityTests(unittest.TestCase):
    def setUp(self):
        self.known = set(record["id"] for record in validate_use_cases(USE_CASES))

    def test_activity_covers_are_deduplicated(self):
        record = validate_activity(activity("A-1", "test", ["UC-1", "UC-1"]), self.known)
        self.assertEqual(record["covers"], ["UC-1"])

    def test_approach_is_lowercased(self):
        record = validate_activity(activity("A-1", "Test", ["UC-1"]), self.known)
        self.assertEqual(record["approach"], "test")
        self.assertIn(record["approach"], APPROACHES)

    def test_unknown_approach_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity(activity("A-1", "vibe-check", ["UC-1"]), self.known)

    def test_dangling_use_case_reference_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity(activity("A-1", "test", ["UC-404"]), self.known)

    def test_empty_covers_rejected(self):
        with self.assertRaises(ValueError):
            validate_activity(activity("A-1", "test", []), self.known)

    def test_duplicate_activity_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_activities(
                [activity("A-1", "test", ["UC-1"]), activity("A-1", "analysis", ["UC-2"])],
                self.known,
            )


class CoverageTests(unittest.TestCase):
    def setUp(self):
        self.use_cases = validate_use_cases(USE_CASES)
        self.known = set(record["id"] for record in self.use_cases)

    def _matrix(self, activities):
        records = validate_activities(activities, self.known)
        return records, coverage_matrix(self.use_cases, records)

    def test_matrix_lists_every_use_case(self):
        _, matrix = self._matrix([activity("A-1", "test", ["UC-1"])])
        self.assertEqual(sorted(matrix), ["UC-1", "UC-2", "UC-3"])

    def test_many_activities_on_one_use_case_do_not_raise_coverage(self):
        _, matrix = self._matrix(
            [activity("A-1", "test", ["UC-1"]), activity("A-2", "analysis", ["UC-1"])]
        )
        self.assertAlmostEqual(weighted_coverage_fraction(self.use_cases, matrix), 0.5, places=9)

    def test_full_coverage_is_one(self):
        _, matrix = self._matrix([activity("A-1", "test", ["UC-1", "UC-2", "UC-3"])])
        self.assertAlmostEqual(weighted_coverage_fraction(self.use_cases, matrix), 1.0, places=9)

    def test_coverage_is_weighted_not_counted(self):
        _, matrix = self._matrix([activity("A-1", "test", ["UC-2", "UC-3"])])
        self.assertAlmostEqual(weighted_coverage_fraction(self.use_cases, matrix), 0.5, places=9)

    def test_safety_driving_case_on_analysis_only_is_a_shortfall(self):
        records, matrix = self._matrix([activity("A-1", "analysis", ["UC-1"])])
        self.assertEqual(approach_shortfalls(self.use_cases, records, matrix), ["UC-1"])

    def test_one_observing_activity_clears_the_shortfall(self):
        records, matrix = self._matrix(
            [activity("A-1", "analysis", ["UC-1"]), activity("A-2", "demonstration", ["UC-1"])]
        )
        self.assertEqual(approach_shortfalls(self.use_cases, records, matrix), [])

    def test_uncovered_safety_case_is_not_reported_as_a_shortfall(self):
        records, matrix = self._matrix([activity("A-1", "test", ["UC-2"])])
        self.assertEqual(approach_shortfalls(self.use_cases, records, matrix), [])


class AssessmentTests(unittest.TestCase):
    def _plan(self, **overrides):
        plan = {
            "sections": list(ALL_SECTIONS),
            "use_cases": [dict(u) for u in USE_CASES],
            "activities": [
                activity("A-1", "test", ["UC-1"]),
                activity("A-2", "analysis", ["UC-2", "UC-3"]),
            ],
            "required_coverage_fraction": 1.0,
        }
        plan.update(overrides)
        return plan

    def test_complete_plan_is_compliant(self):
        result = assess_validation_plan(self._plan())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=9)

    def test_uncovered_use_case_is_a_finding(self):
        result = assess_validation_plan(
            self._plan(activities=[activity("A-1", "test", ["UC-1"])])
        )
        self.assertEqual(result["uncovered_use_cases"], ["UC-2", "UC-3"])
        self.assertFalse(result["compliant"])

    def test_missing_section_is_a_finding(self):
        sections = [s for s in ALL_SECTIONS if s != "scope"]
        result = assess_validation_plan(self._plan(sections=sections))
        self.assertEqual(result["missing_sections"], ["scope"])
        self.assertFalse(result["compliant"])

    def test_unmeasurable_criterion_is_a_finding(self):
        bad = activity("A-1", "test", ["UC-1"], {"comparator": "==", "bound": 1.0, "unit": "V"})
        result = assess_validation_plan(
            self._plan(activities=[bad, activity("A-2", "analysis", ["UC-2", "UC-3"])])
        )
        self.assertEqual(len(result["unmeasurable_criteria"]), 1)
        self.assertFalse(result["compliant"])

    def test_approach_shortfall_is_a_finding(self):
        result = assess_validation_plan(
            self._plan(activities=[activity("A-1", "analysis", ["UC-1", "UC-2", "UC-3"])])
        )
        self.assertEqual(result["approach_shortfalls"], ["UC-1"])
        self.assertFalse(result["compliant"])

    def test_coverage_exactly_at_the_required_fraction_is_met(self):
        result = assess_validation_plan(
            self._plan(
                activities=[activity("A-1", "test", ["UC-2", "UC-3"])],
                required_coverage_fraction=0.5,
            )
        )
        self.assertTrue(result["coverage_met"])
        self.assertLessEqual(
            abs(result["coverage_fraction"] - result["required_coverage_fraction"]),
            COVERAGE_TOLERANCE,
        )

    def test_coverage_below_the_required_fraction_is_a_finding(self):
        result = assess_validation_plan(
            self._plan(
                activities=[activity("A-1", "test", ["UC-2"])],
                required_coverage_fraction=0.9,
            )
        )
        self.assertFalse(result["coverage_met"])
        self.assertTrue(any("below the required" in f for f in result["findings"]))

    def test_required_fraction_outside_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            assess_validation_plan(self._plan(required_coverage_fraction=1.2))

    def test_missing_plan_key_rejected(self):
        plan = self._plan()
        del plan["use_cases"]
        with self.assertRaises(ValueError):
            assess_validation_plan(plan)

    def test_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            assess_validation_plan(["sections"])


if __name__ == "__main__":
    unittest.main()
