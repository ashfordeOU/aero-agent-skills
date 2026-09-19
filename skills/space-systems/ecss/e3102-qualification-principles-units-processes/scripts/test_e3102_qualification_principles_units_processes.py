#!/usr/bin/env python3
"""Contract test for the two-phase qualification unit and process plan."""

import copy
import unittest

from e3102_qualification_principles_units_processes_logic import (
    CHANGE_CATEGORIES,
    CHANGE_FLAGS,
    DELTA_QUALIFICATION,
    FULL_QUALIFICATION,
    MINIMUM_UNITS_BY_PROCESS,
    PROCESS_BY_CATEGORY,
    QUALIFICATION_BY_HERITAGE,
    QUALIFICATION_BY_SIMILARITY,
    SOURCE_REQUALIFICATION,
    categorize_change,
    escalate_heritage_claim,
    plan_qualification,
    qualification_process,
    required_units,
    units_for_build_standards,
    validate_change_declaration,
)

NO_CHANGE = {flag: False for flag in CHANGE_FLAGS}


def _changes(**overrides):
    declaration = dict(NO_CHANGE)
    declaration.update(overrides)
    return declaration


NEW_DESIGN_CASE = {
    "changes": _changes(no_qualified_predecessor=True),
    "build_standards": 2,
    "destructive_tests": 1,
}

HERITAGE_CASE = {
    "changes": _changes(),
    "build_standards": 1,
    "destructive_tests": 0,
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class ChangeDeclarationTests(unittest.TestCase):
    def test_a_complete_declaration_validates(self):
        self.assertIs(validate_change_declaration(NO_CHANGE), NO_CHANGE)

    def test_a_missing_flag_rejected(self):
        broken = _changes()
        del broken["new_technology"]
        with self.assertRaises(ValueError):
            validate_change_declaration(broken)

    def test_an_unknown_flag_rejected(self):
        broken = _changes()
        broken["repainted"] = True
        with self.assertRaises(ValueError):
            validate_change_declaration(broken)

    def test_a_non_boolean_flag_rejected(self):
        broken = _changes()
        broken["new_technology"] = "yes"
        with self.assertRaises(ValueError):
            validate_change_declaration(broken)

    def test_a_non_mapping_declaration_rejected(self):
        with self.assertRaises(ValueError):
            validate_change_declaration(CHANGE_FLAGS)


class CategorizationTests(unittest.TestCase):
    def test_no_change_is_identical(self):
        self.assertEqual(categorize_change(_changes()), "identical")

    def test_new_technology_outranks_every_other_flag(self):
        declaration = _changes(
            new_technology=True,
            manufacturing_source_change=True,
            resized_within_qualified_range=True,
        )
        self.assertEqual(categorize_change(declaration), "new-technology")

    def test_a_missing_predecessor_gives_a_new_design(self):
        self.assertEqual(
            categorize_change(_changes(no_qualified_predecessor=True)), "new-design"
        )

    def test_a_performance_change_outranks_a_source_change(self):
        declaration = _changes(
            performance_affecting_change=True, manufacturing_source_change=True
        )
        self.assertEqual(categorize_change(declaration), "performance-change")

    def test_a_source_change_alone_gives_a_source_change(self):
        self.assertEqual(
            categorize_change(_changes(manufacturing_source_change=True)),
            "source-change",
        )

    def test_a_resize_inside_the_range_gives_a_scaled_case(self):
        self.assertEqual(
            categorize_change(_changes(resized_within_qualified_range=True)),
            "scaled-within-range",
        )


class ProcessSelectionTests(unittest.TestCase):
    def test_every_category_maps_to_a_process(self):
        for category in CHANGE_CATEGORIES:
            self.assertIn(qualification_process(category)["process"], MINIMUM_UNITS_BY_PROCESS)

    def test_a_new_design_takes_a_full_qualification(self):
        self.assertEqual(
            qualification_process("new-design")["process"], FULL_QUALIFICATION
        )

    def test_a_performance_change_takes_a_delta_qualification(self):
        self.assertEqual(
            qualification_process("performance-change")["process"], DELTA_QUALIFICATION
        )

    def test_a_source_change_takes_a_source_requalification(self):
        self.assertEqual(
            qualification_process("source-change")["process"], SOURCE_REQUALIFICATION
        )

    def test_a_heritage_case_needs_no_new_hardware(self):
        selection = qualification_process("identical")
        self.assertEqual(selection["process"], QUALIFICATION_BY_HERITAGE)
        self.assertFalse(selection["needs_new_hardware"])

    def test_an_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            qualification_process("refurbished")


class UnitCountTests(unittest.TestCase):
    def test_a_full_qualification_carries_a_two_unit_floor(self):
        self.assertEqual(units_for_build_standards(FULL_QUALIFICATION, 1), 2)

    def test_one_unit_per_build_standard_on_a_full_qualification(self):
        self.assertEqual(units_for_build_standards(FULL_QUALIFICATION, 5), 5)

    def test_a_similarity_case_bounds_several_build_standards(self):
        self.assertEqual(units_for_build_standards(QUALIFICATION_BY_SIMILARITY, 4), 1)

    def test_a_similarity_case_rolls_over_to_a_second_unit(self):
        self.assertEqual(units_for_build_standards(QUALIFICATION_BY_SIMILARITY, 5), 2)

    def test_a_heritage_case_builds_nothing(self):
        self.assertEqual(units_for_build_standards(QUALIFICATION_BY_HERITAGE, 3), 0)

    def test_each_destructive_test_adds_a_unit(self):
        base = required_units(DELTA_QUALIFICATION, 2, 0)
        self.assertEqual(required_units(DELTA_QUALIFICATION, 2, 2), base + 2)

    def test_a_destructive_test_on_a_heritage_case_rejected(self):
        with self.assertRaises(ValueError):
            required_units(QUALIFICATION_BY_HERITAGE, 1, 1)

    def test_zero_build_standards_rejected(self):
        with self.assertRaises(ValueError):
            units_for_build_standards(FULL_QUALIFICATION, 0)

    def test_a_non_integer_build_standard_count_rejected(self):
        with self.assertRaises(ValueError):
            units_for_build_standards(FULL_QUALIFICATION, 2.5)

    def test_a_negative_destructive_count_rejected(self):
        with self.assertRaises(ValueError):
            required_units(FULL_QUALIFICATION, 1, -1)

    def test_an_unknown_process_rejected(self):
        with self.assertRaises(ValueError):
            units_for_build_standards("hope", 1)


class EscalationTests(unittest.TestCase):
    def test_a_matching_claim_raises_no_finding(self):
        result = escalate_heritage_claim(FULL_QUALIFICATION, "new-design")
        self.assertEqual(result["findings"], [])

    def test_a_heritage_claim_against_a_new_design_escalates(self):
        result = escalate_heritage_claim(QUALIFICATION_BY_HERITAGE, "new-design")
        self.assertEqual(result["process"], FULL_QUALIFICATION)
        self.assertTrue(result["findings"])

    def test_a_similarity_claim_against_a_performance_change_escalates(self):
        result = escalate_heritage_claim(
            QUALIFICATION_BY_SIMILARITY, "performance-change"
        )
        self.assertEqual(result["process"], DELTA_QUALIFICATION)
        self.assertTrue(result["findings"])

    def test_claiming_more_than_obliged_is_not_a_finding(self):
        result = escalate_heritage_claim(FULL_QUALIFICATION, "identical")
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["process"], QUALIFICATION_BY_HERITAGE)

    def test_an_unknown_claim_rejected(self):
        with self.assertRaises(ValueError):
            escalate_heritage_claim("vendor-word", "identical")


class PlanTests(unittest.TestCase):
    def test_a_new_design_plan_counts_coverage_plus_destruction(self):
        result = plan_qualification(NEW_DESIGN_CASE)
        self.assertEqual(result["process"], FULL_QUALIFICATION)
        self.assertEqual(result["coverage_units"], 2)
        self.assertEqual(result["qualification_units"], 3)
        self.assertEqual(result["verdict"], "plan-consistent")

    def test_a_heritage_plan_builds_no_unit(self):
        result = plan_qualification(HERITAGE_CASE)
        self.assertEqual(result["process"], QUALIFICATION_BY_HERITAGE)
        self.assertEqual(result["qualification_units"], 0)
        self.assertEqual(result["findings"], [])

    def test_a_heritage_plan_with_a_destructive_test_is_escalated(self):
        result = plan_qualification(_case(HERITAGE_CASE, destructive_tests=1))
        self.assertEqual(result["verdict"], "plan-escalated")
        self.assertEqual(result["destructive_tests"], 0)
        self.assertTrue(any("destructive" in f for f in result["findings"]))

    def test_a_heritage_claim_on_a_changed_design_is_escalated(self):
        case = _case(NEW_DESIGN_CASE, claimed_process=QUALIFICATION_BY_HERITAGE)
        result = plan_qualification(case)
        self.assertEqual(result["process"], FULL_QUALIFICATION)
        self.assertEqual(result["verdict"], "plan-escalated")

    def test_retaining_a_unit_a_heritage_case_never_builds_is_a_finding(self):
        result = plan_qualification(_case(HERITAGE_CASE, retain_unit=True))
        self.assertTrue(any("retention" in f for f in result["findings"]))

    def test_more_build_standards_never_lower_the_unit_count(self):
        few = plan_qualification(_case(NEW_DESIGN_CASE, build_standards=2))
        many = plan_qualification(_case(NEW_DESIGN_CASE, build_standards=6))
        self.assertGreaterEqual(
            many["qualification_units"], few["qualification_units"]
        )

    def test_every_category_produces_a_usable_plan(self):
        for category in CHANGE_CATEGORIES:
            process = PROCESS_BY_CATEGORY[category]
            self.assertIn(process, MINIMUM_UNITS_BY_PROCESS)

    def test_a_missing_change_declaration_rejected(self):
        case = _case(NEW_DESIGN_CASE)
        del case["changes"]
        with self.assertRaises(ValueError):
            plan_qualification(case)

    def test_a_missing_build_standard_count_rejected(self):
        case = _case(NEW_DESIGN_CASE)
        del case["build_standards"]
        with self.assertRaises(ValueError):
            plan_qualification(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            plan_qualification("new-design")

    def test_a_non_boolean_retention_flag_rejected(self):
        with self.assertRaises(ValueError):
            plan_qualification(_case(NEW_DESIGN_CASE, retain_unit="yes"))


if __name__ == "__main__":
    unittest.main()
