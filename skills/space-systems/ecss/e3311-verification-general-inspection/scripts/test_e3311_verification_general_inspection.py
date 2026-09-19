#!/usr/bin/env python3
"""Contract test for explosive-hardware verification and inspection (offline)."""

import copy
import unittest

from e3311_verification_general_inspection_logic import (
    ARTICLES,
    COVERAGE_MET,
    COVERAGE_NOT_MET,
    DEFAULT_VERIFICATION_POLICY,
    MATRIX_CLOSED,
    MATRIX_OPEN,
    REQUIREMENT_KINDS,
    VERIFICATION_METHODS,
    inspection_coverage,
    lot_sample_size,
    plan_verification,
    screen_verification_matrix,
    select_verification_method,
    validate_verification_policy,
)

CLOSED_CASE = {
    "one_shot_device": True,
    "lot_size": 60,
    "requirements": [
        {"id": "r1", "kind": "function"},
        {"id": "r2", "kind": "workmanship"},
        {"id": "r3", "kind": "material"},
    ],
    "characteristics": [
        {"id": "c1", "critical": True, "inspected": True},
        {"id": "c2", "inspected": True},
        {"id": "c3", "inspected": True},
    ],
    "matrix": [
        {"id": "r1", "method": "test", "article": "lot-sample", "evidence": "LAT 12"},
        {
            "id": "r2",
            "method": "inspection",
            "article": "flight-article",
            "evidence": "FAI sheet 4",
        },
        {
            "id": "r3",
            "method": "analysis",
            "article": "flight-article",
            "evidence": "material data pack",
        },
    ],
}


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_verification_policy(DEFAULT_VERIFICATION_POLICY),
            DEFAULT_VERIFICATION_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_verification_policy("default")

    def test_a_sample_fraction_of_unity_is_rejected(self):
        broken = copy.deepcopy(DEFAULT_VERIFICATION_POLICY)
        broken["lot_sample_fraction"] = 1.0
        with self.assertRaises(ValueError):
            validate_verification_policy(broken)

    def test_a_ceiling_below_the_floor_is_rejected(self):
        broken = copy.deepcopy(DEFAULT_VERIFICATION_POLICY)
        broken["max_lot_sample"] = 1
        with self.assertRaises(ValueError):
            validate_verification_policy(broken)

    def test_a_coverage_threshold_above_unity_is_rejected(self):
        broken = copy.deepcopy(DEFAULT_VERIFICATION_POLICY)
        broken["min_inspection_coverage"] = 1.2
        with self.assertRaises(ValueError):
            validate_verification_policy(broken)


class MethodSelectionTests(unittest.TestCase):
    def test_a_one_shot_function_test_moves_onto_a_lot_sample(self):
        selection = select_verification_method("function", one_shot_device=True)
        self.assertEqual(selection["method"], "test")
        self.assertEqual(selection["article"], "lot-sample")

    def test_the_flight_article_inherits_a_companion_inspection(self):
        selection = select_verification_method("function", one_shot_device=True)
        self.assertEqual(selection["companion_methods"], ["inspection"])

    def test_a_non_destructive_function_test_stays_on_the_flight_article(self):
        selection = select_verification_method("function", one_shot_device=False)
        self.assertEqual(selection["article"], "flight-article")
        self.assertEqual(selection["companion_methods"], [])

    def test_a_destructive_performance_demonstration_moves_to_a_sample(self):
        selection = select_verification_method(
            "performance", destructive_demonstration=True
        )
        self.assertEqual(selection["article"], "lot-sample")

    def test_workmanship_is_closed_by_inspection(self):
        self.assertEqual(
            select_verification_method("workmanship")["method"], "inspection"
        )

    def test_interface_and_marking_are_closed_by_inspection(self):
        for kind in ("interface", "marking"):
            self.assertEqual(select_verification_method(kind)["method"], "inspection")

    def test_a_material_requirement_is_closed_by_analysis(self):
        self.assertEqual(select_verification_method("material")["method"], "analysis")

    def test_heritage_moves_a_material_requirement_to_review_of_design(self):
        selection = select_verification_method("material", heritage_available=True)
        self.assertEqual(selection["method"], "review-of-design")

    def test_every_selection_names_its_article_and_reason(self):
        for kind in REQUIREMENT_KINDS:
            selection = select_verification_method(kind, one_shot_device=True)
            self.assertIn(selection["article"], ARTICLES)
            self.assertIn(selection["method"], VERIFICATION_METHODS)
            self.assertTrue(selection["rationale"])

    def test_an_unknown_requirement_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            select_verification_method("vibes")

    def test_a_non_boolean_one_shot_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            select_verification_method("function", one_shot_device="yes")


class LotSampleTests(unittest.TestCase):
    def test_the_sample_is_a_fraction_of_the_lot_rounded_up(self):
        self.assertEqual(lot_sample_size(55), 6)

    def test_a_small_lot_is_lifted_to_the_floor(self):
        self.assertEqual(lot_sample_size(12), 2)

    def test_a_large_lot_is_capped_at_the_ceiling(self):
        self.assertEqual(lot_sample_size(500), 10)

    def test_a_lot_the_sample_would_consume_is_rejected(self):
        with self.assertRaises(ValueError):
            lot_sample_size(2)

    def test_a_fractional_lot_size_is_rejected(self):
        with self.assertRaises(ValueError):
            lot_sample_size(55.5)

    def test_a_zero_lot_is_rejected(self):
        with self.assertRaises(ValueError):
            lot_sample_size(0)


class CoverageTests(unittest.TestCase):
    def test_full_coverage_passes(self):
        result = inspection_coverage(CLOSED_CASE["characteristics"])
        self.assertEqual(result["verdict"], COVERAGE_MET)
        self.assertAlmostEqual(result["coverage_fraction"], 1.0, places=12)

    def test_an_uninspected_critical_characteristic_fails_high_coverage(self):
        characteristics = [{"id": "c%d" % i, "inspected": True} for i in range(39)]
        characteristics.append({"id": "c40", "critical": True, "inspected": False})
        result = inspection_coverage(characteristics)
        self.assertAlmostEqual(result["coverage_fraction"], 0.975, places=12)
        self.assertEqual(result["verdict"], COVERAGE_NOT_MET)
        self.assertEqual(result["critical_gaps"], ["c40"])

    def test_coverage_exactly_on_the_threshold_passes(self):
        characteristics = [{"id": "c%d" % i, "inspected": True} for i in range(19)]
        characteristics.append({"id": "c20", "inspected": False})
        result = inspection_coverage(characteristics)
        self.assertAlmostEqual(
            result["coverage_fraction"], result["required_fraction"], places=9
        )
        self.assertEqual(result["verdict"], COVERAGE_MET)

    def test_coverage_below_the_threshold_fails(self):
        result = inspection_coverage(
            [
                {"id": "c1", "inspected": True},
                {"id": "c2", "inspected": False},
            ]
        )
        self.assertEqual(result["verdict"], COVERAGE_NOT_MET)
        self.assertEqual(result["gaps"], ["c2"])

    def test_a_duplicate_characteristic_id_is_rejected(self):
        with self.assertRaises(ValueError):
            inspection_coverage(
                [{"id": "c1", "inspected": True}, {"id": "c1", "inspected": True}]
            )

    def test_an_empty_characteristic_list_is_rejected(self):
        with self.assertRaises(ValueError):
            inspection_coverage([])

    def test_a_non_boolean_inspected_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            inspection_coverage([{"id": "c1", "inspected": "yes"}])


class MatrixTests(unittest.TestCase):
    def test_a_fully_evidenced_matrix_is_closed(self):
        result = screen_verification_matrix(CLOSED_CASE["matrix"])
        self.assertEqual(result["verdict"], MATRIX_CLOSED)
        self.assertEqual(result["open_items"], [])

    def test_a_row_with_a_method_and_no_evidence_is_open(self):
        rows = copy.deepcopy(CLOSED_CASE["matrix"])
        rows[0]["evidence"] = ""
        result = screen_verification_matrix(rows)
        self.assertEqual(result["verdict"], MATRIX_OPEN)
        self.assertEqual(result["open_items"], ["r1"])

    def test_a_missing_evidence_key_is_open_too(self):
        rows = copy.deepcopy(CLOSED_CASE["matrix"])
        del rows[1]["evidence"]
        result = screen_verification_matrix(rows)
        self.assertIn("r2", result["open_items"])

    def test_an_unknown_method_is_rejected(self):
        rows = copy.deepcopy(CLOSED_CASE["matrix"])
        rows[0]["method"] = "hoping"
        with self.assertRaises(ValueError):
            screen_verification_matrix(rows)

    def test_an_unknown_article_is_rejected(self):
        rows = copy.deepcopy(CLOSED_CASE["matrix"])
        rows[0]["article"] = "the-other-one"
        with self.assertRaises(ValueError):
            screen_verification_matrix(rows)

    def test_a_duplicate_requirement_id_is_rejected(self):
        rows = copy.deepcopy(CLOSED_CASE["matrix"])
        rows.append(copy.deepcopy(rows[0]))
        with self.assertRaises(ValueError):
            screen_verification_matrix(rows)

    def test_an_empty_matrix_is_rejected(self):
        with self.assertRaises(ValueError):
            screen_verification_matrix([])


class PlanTests(unittest.TestCase):
    def test_a_complete_strategy_closes(self):
        result = plan_verification(CLOSED_CASE)
        self.assertTrue(result["closed"])
        self.assertEqual(result["verdict"], MATRIX_CLOSED)
        self.assertEqual(result["findings"], [])

    def test_a_one_shot_device_needs_a_lot_sample(self):
        result = plan_verification(CLOSED_CASE)
        self.assertTrue(result["needs_lot_sample"])
        self.assertEqual(result["lot_sample_size"], 6)

    def test_a_missing_lot_size_leaves_the_sample_unsized(self):
        case = _case(CLOSED_CASE)
        del case["lot_size"]
        result = plan_verification(case)
        self.assertIsNone(result["lot_sample_size"])
        self.assertFalse(result["closed"])

    def test_a_non_one_shot_device_needs_no_sample(self):
        case = _case(CLOSED_CASE, one_shot_device=False)
        case["matrix"] = copy.deepcopy(case["matrix"])
        case["matrix"][0]["article"] = "flight-article"
        result = plan_verification(case)
        self.assertFalse(result["needs_lot_sample"])
        self.assertIsNone(result["lot_sample_size"])

    def test_an_uninspected_critical_characteristic_reopens_a_full_matrix(self):
        case = _case(CLOSED_CASE)
        case["characteristics"] = copy.deepcopy(case["characteristics"])
        case["characteristics"][0]["inspected"] = False
        result = plan_verification(case)
        self.assertEqual(result["matrix"]["verdict"], MATRIX_CLOSED)
        self.assertFalse(result["closed"])

    def test_a_missing_matrix_leaves_every_requirement_unevidenced(self):
        case = _case(CLOSED_CASE)
        del case["matrix"]
        result = plan_verification(case)
        self.assertIsNone(result["matrix"])
        self.assertFalse(result["closed"])
        self.assertTrue(any("no verification matrix" in f for f in result["findings"]))

    def test_a_missing_characteristic_list_leaves_coverage_ungraded(self):
        case = _case(CLOSED_CASE)
        del case["characteristics"]
        result = plan_verification(case)
        self.assertIsNone(result["coverage"])
        self.assertFalse(result["closed"])

    def test_heritage_changes_the_material_selection_in_the_plan(self):
        result = plan_verification(_case(CLOSED_CASE, heritage_available=True))
        material = [s for s in result["selections"] if s["id"] == "r3"][0]
        self.assertEqual(material["method"], "review-of-design")

    def test_plan_rejects_an_empty_requirements_list(self):
        with self.assertRaises(ValueError):
            plan_verification(_case(CLOSED_CASE, requirements=[]))

    def test_plan_rejects_a_requirement_without_an_id(self):
        case = _case(CLOSED_CASE)
        case["requirements"] = [{"kind": "function"}]
        with self.assertRaises(ValueError):
            plan_verification(case)

    def test_plan_rejects_a_non_mapping_case(self):
        with self.assertRaises(ValueError):
            plan_verification("verify everything")


if __name__ == "__main__":
    unittest.main()
