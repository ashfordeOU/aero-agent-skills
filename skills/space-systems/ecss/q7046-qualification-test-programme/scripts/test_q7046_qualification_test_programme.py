#!/usr/bin/env python3
"""Contract test for the fastener qualification test programme (offline)."""

import copy
import unittest

from q7046_qualification_test_programme_logic import (
    CHANGE_TYPES,
    CRITICALITY_CATEGORIES,
    LOT_SENSITIVE_TESTS,
    TEST_COATING,
    TEST_FATIGUE,
    TEST_HARDNESS,
    TEST_PROOF,
    TEST_TENSILE,
    VERDICT_COMPLETE,
    VERDICT_INCOMPLETE,
    VERDICT_REQUALIFICATION_OPEN,
    allocate_specimens,
    coverage_findings,
    criticality_rules,
    is_lot_sensitive,
    plan_qualification,
    programme_total,
    requalification_scope,
    required_tests,
    shortfall,
    specimens_per_test,
)


def _complete_record(category, lots, variants):
    return dict(allocate_specimens(category, lots, variants))


GOOD_CASE = {
    "category": "structural",
    "lot_count": 2,
    "variant_count": 1,
    "specimens_tested": _complete_record("structural", 2, 1),
    "changes": (),
}


def _case(**overrides):
    case = copy.deepcopy(GOOD_CASE)
    case.update(overrides)
    return case


class CategoryRuleTests(unittest.TestCase):
    def test_every_category_owes_tests_and_a_lot_minimum(self):
        for category in CRITICALITY_CATEGORIES:
            rules = criticality_rules(category)
            self.assertTrue(rules["specimens"])
            self.assertGreaterEqual(rules["min_lots"], 1)

    def test_critical_category_owes_the_most_tests(self):
        self.assertGreater(
            len(required_tests("fracture-critical")),
            len(required_tests("structural")),
        )
        self.assertGreater(
            len(required_tests("structural")),
            len(required_tests("non-structural")),
        )

    def test_tensile_and_hardness_are_owed_by_every_category(self):
        for category in CRITICALITY_CATEGORIES:
            self.assertIn(TEST_TENSILE, required_tests(category))
            self.assertIn(TEST_HARDNESS, required_tests(category))

    def test_fatigue_is_owed_only_by_the_critical_category(self):
        self.assertIn(TEST_FATIGUE, required_tests("fracture-critical"))
        self.assertNotIn(TEST_FATIGUE, required_tests("structural"))

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            criticality_rules("mission-nice-to-have")

    def test_specimen_count_for_a_test_the_category_never_owed_rejected(self):
        with self.assertRaises(ValueError):
            specimens_per_test("non-structural", TEST_FATIGUE)


class SensitivityTests(unittest.TestCase):
    def test_lot_sensitive_tests_are_recognised(self):
        for test in LOT_SENSITIVE_TESTS:
            self.assertTrue(is_lot_sensitive(test))

    def test_fatigue_is_variant_driven_not_lot_sensitive(self):
        self.assertFalse(is_lot_sensitive(TEST_FATIGUE))

    def test_empty_test_name_rejected(self):
        with self.assertRaises(ValueError):
            is_lot_sensitive("")


class AllocationTests(unittest.TestCase):
    def test_lot_sensitive_test_scales_with_lots_and_variants(self):
        per_draw = specimens_per_test("structural", TEST_TENSILE)
        allocation = allocate_specimens("structural", 3, 2)
        self.assertEqual(allocation[TEST_TENSILE], per_draw * 3 * 2)

    def test_variant_driven_test_does_not_scale_with_lots(self):
        one_lot = allocate_specimens("fracture-critical", 1, 2)
        four_lots = allocate_specimens("fracture-critical", 4, 2)
        self.assertEqual(one_lot[TEST_FATIGUE], four_lots[TEST_FATIGUE])

    def test_allocation_covers_exactly_the_required_set(self):
        allocation = allocate_specimens("fracture-critical", 3, 1)
        self.assertEqual(
            sorted(allocation), sorted(required_tests("fracture-critical"))
        )

    def test_programme_total_is_the_sum_of_the_allocation(self):
        allocation = allocate_specimens("structural", 2, 3)
        self.assertEqual(programme_total("structural", 2, 3), sum(allocation.values()))

    def test_programme_total_grows_with_more_lots(self):
        self.assertGreater(
            programme_total("structural", 4, 1),
            programme_total("structural", 2, 1),
        )

    def test_zero_lots_rejected(self):
        with self.assertRaises(ValueError):
            allocate_specimens("structural", 0, 1)

    def test_non_integer_variant_count_rejected(self):
        with self.assertRaises(ValueError):
            allocate_specimens("structural", 2, 1.0)

    def test_boolean_lot_count_rejected(self):
        with self.assertRaises(ValueError):
            allocate_specimens("structural", True, 1)


class CoverageTests(unittest.TestCase):
    def test_single_lot_flagged_for_the_critical_category(self):
        findings = coverage_findings("fracture-critical", 1, 1)
        self.assertTrue(any("production lot" in f for f in findings))

    def test_enough_lots_raises_no_coverage_finding(self):
        self.assertEqual(coverage_findings("fracture-critical", 3, 1), [])

    def test_non_structural_category_accepts_one_lot(self):
        self.assertEqual(coverage_findings("non-structural", 1, 1), [])


class RequalificationTests(unittest.TestCase):
    def test_coating_change_leaves_tensile_evidence_standing(self):
        scope = requalification_scope("fracture-critical", "coating-process")
        self.assertIn(TEST_COATING, scope)
        self.assertNotIn(TEST_TENSILE, scope)

    def test_source_change_reopens_the_whole_required_set(self):
        scope = requalification_scope("structural", "manufacturing-source")
        self.assertEqual(sorted(scope), sorted(required_tests("structural")))

    def test_scope_never_names_a_test_the_category_did_not_owe(self):
        for change in CHANGE_TYPES:
            scope = requalification_scope("non-structural", change)
            for test in scope:
                self.assertIn(test, required_tests("non-structural"))

    def test_heat_treatment_change_reopens_proof_and_hardness(self):
        scope = requalification_scope("structural", "heat-treatment")
        self.assertIn(TEST_PROOF, scope)
        self.assertIn(TEST_HARDNESS, scope)

    def test_unknown_change_rejected_not_treated_as_harmless(self):
        with self.assertRaises(ValueError):
            requalification_scope("structural", "painted-the-crate")


class ShortfallTests(unittest.TestCase):
    def test_complete_record_leaves_nothing_outstanding(self):
        gaps = shortfall("structural", 2, 1, _complete_record("structural", 2, 1))
        self.assertEqual(gaps["outstanding"], {})

    def test_missing_test_is_outstanding_in_full(self):
        record = _complete_record("structural", 2, 1)
        owed = record.pop(TEST_TENSILE)
        gaps = shortfall("structural", 2, 1, record)
        self.assertEqual(gaps["outstanding"][TEST_TENSILE], owed)

    def test_partial_record_reports_only_the_difference(self):
        record = _complete_record("structural", 2, 1)
        record[TEST_HARDNESS] -= 2
        gaps = shortfall("structural", 2, 1, record)
        self.assertEqual(gaps["outstanding"][TEST_HARDNESS], 2)

    def test_surplus_specimens_are_not_a_shortfall(self):
        record = _complete_record("structural", 2, 1)
        record[TEST_HARDNESS] += 5
        gaps = shortfall("structural", 2, 1, record)
        self.assertEqual(gaps["outstanding"], {})

    def test_unexpected_test_is_reported_separately(self):
        record = _complete_record("structural", 2, 1)
        record["paint-colour-match"] = 2
        gaps = shortfall("structural", 2, 1, record)
        self.assertEqual(gaps["unexpected_tests"], ["paint-colour-match"])

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            shortfall("structural", 2, 1, [TEST_TENSILE])

    def test_negative_specimen_count_rejected(self):
        record = _complete_record("structural", 2, 1)
        record[TEST_TENSILE] = -1
        with self.assertRaises(ValueError):
            shortfall("structural", 2, 1, record)


class PlanTests(unittest.TestCase):
    def test_complete_programme_with_no_change_is_qualified(self):
        self.assertEqual(plan_qualification(_case())["verdict"], VERDICT_COMPLETE)

    def test_short_programme_is_incomplete(self):
        record = _complete_record("structural", 2, 1)
        record[TEST_TENSILE] = 0
        result = plan_qualification(_case(specimens_tested=record))
        self.assertEqual(result["verdict"], VERDICT_INCOMPLETE)
        self.assertIn(TEST_TENSILE, result["outstanding"])

    def test_complete_programme_with_an_open_change_is_not_qualified(self):
        result = plan_qualification(_case(changes=("coating-process",)))
        self.assertEqual(result["verdict"], VERDICT_REQUALIFICATION_OPEN)
        self.assertIn("coating-process", result["requalification"])

    def test_findings_name_the_outstanding_test(self):
        record = _complete_record("structural", 2, 1)
        record[TEST_HARDNESS] = 0
        result = plan_qualification(_case(specimens_tested=record))
        self.assertTrue(any(TEST_HARDNESS in f for f in result["findings"]))

    def test_plan_reports_the_programme_total(self):
        result = plan_qualification(_case())
        self.assertEqual(
            result["programme_total"], programme_total("structural", 2, 1)
        )

    def test_missing_lot_count_rejected(self):
        case = _case()
        del case["lot_count"]
        with self.assertRaises(ValueError):
            plan_qualification(case)

    def test_string_change_list_rejected(self):
        with self.assertRaises(ValueError):
            plan_qualification(_case(changes="coating-process"))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            plan_qualification("qualify the M6 bolts please")


if __name__ == "__main__":
    unittest.main()
