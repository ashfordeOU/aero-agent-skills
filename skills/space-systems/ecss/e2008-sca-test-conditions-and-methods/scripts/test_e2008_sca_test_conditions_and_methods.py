#!/usr/bin/env python3
"""Contract test for solar cell assembly test conditions and methods (offline)."""

import copy
import unittest

from e2008_sca_test_conditions_and_methods_logic import (
    ALIGNED,
    ALIGNED_UNDER_APPROVAL,
    CONDITION_RANK,
    DEMONSTRATED,
    METHOD_SOURCES,
    MISALIGNED,
    OUTSIDE_WINDOW,
    TEST_ALIGNED,
    TEST_ALIGNED_UNDER_APPROVAL,
    TEST_NOT_ALIGNED,
    TEST_RANK,
    UNDEMONSTRATED,
    assess_test,
    assess_test_matrix,
    condition_margin,
    matrix_coverage,
    method_alignment,
)

TEMPERATURE = {
    "kind": "cell-temperature",
    "specified_value": 25.0,
    "declared_value": 25.4,
    "half_window": 2.0,
    "uncertainty": 0.5,
}

ILLUMINATION = {
    "kind": "illumination-ratio",
    "specified_value": 1.0,
    "declared_value": 1.01,
    "half_window": 0.05,
    "uncertainty": 0.045,
}

CYCLE_COUNT = {
    "kind": "cycle-count",
    "specified_value": 100.0,
    "declared_value": 100.0,
    "half_window": 0.0,
    "uncertainty": 0.0,
}

PERFORMANCE_TEST = {
    "test_id": "SCA-IV-01",
    "method_source": "drawing-named",
    "conditions": [TEMPERATURE, ILLUMINATION],
}

CYCLING_TEST = {
    "test_id": "SCA-TC-02",
    "method_source": "drawing-invoked-standard",
    "conditions": [TEMPERATURE, CYCLE_COUNT],
}


def _variant(base, **overrides):
    item = copy.deepcopy(base)
    for key, value in overrides.items():
        if value is None and key in item:
            del item[key]
        else:
            item[key] = value
    return item


class MethodAlignmentTests(unittest.TestCase):
    def test_drawing_named_method_is_aligned(self):
        result = method_alignment("drawing-named")
        self.assertEqual(result["alignment"], ALIGNED)
        self.assertEqual(result["findings"], [])

    def test_standard_invoked_by_the_drawing_is_aligned(self):
        self.assertEqual(
            method_alignment("drawing-invoked-standard")["alignment"], ALIGNED
        )

    def test_approved_equivalent_travels_with_its_approval(self):
        result = method_alignment("approved-equivalent", "DEV-2291")
        self.assertEqual(result["alignment"], ALIGNED_UNDER_APPROVAL)
        self.assertEqual(result["approval_reference"], "DEV-2291")
        self.assertTrue(any("DEV-2291" in f for f in result["findings"]))

    def test_equivalent_without_an_approval_is_rejected(self):
        with self.assertRaises(ValueError):
            method_alignment("approved-equivalent")

    def test_blank_approval_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            method_alignment("approved-equivalent", "   ")

    def test_supplier_internal_method_is_misaligned(self):
        result = method_alignment("supplier-internal")
        self.assertEqual(result["alignment"], MISALIGNED)
        self.assertTrue(any("house procedure" in f for f in result["findings"]))

    def test_redundant_approval_on_a_drawing_method_is_flagged_not_failed(self):
        result = method_alignment("drawing-named", "DEV-9000")
        self.assertEqual(result["alignment"], ALIGNED)
        self.assertTrue(any("redundant" in f for f in result["findings"]))

    def test_unknown_method_source_is_rejected(self):
        with self.assertRaises(ValueError):
            method_alignment("whatever-the-lab-had")

    def test_every_declared_method_source_is_handled(self):
        for source in METHOD_SOURCES:
            approval = "DEV-1" if source == "approved-equivalent" else None
            self.assertIn(
                method_alignment(source, approval)["alignment"],
                (ALIGNED, ALIGNED_UNDER_APPROVAL, MISALIGNED),
            )


class ConditionMarginTests(unittest.TestCase):
    def test_a_condition_inside_its_guard_band_is_demonstrated(self):
        result = condition_margin(TEMPERATURE)
        self.assertEqual(result["verdict"], DEMONSTRATED)
        self.assertAlmostEqual(result["margin"], 1.1, places=9)

    def test_window_usage_counts_the_uncertainty_too(self):
        self.assertAlmostEqual(
            condition_margin(TEMPERATURE)["window_usage"], 0.45, places=9
        )

    def test_uncertainty_can_push_a_compliant_setpoint_out_of_the_window(self):
        result = condition_margin(ILLUMINATION)
        self.assertEqual(result["verdict"], UNDEMONSTRATED)
        self.assertTrue(any("declared rather than demonstrated" in f for f in result["findings"]))

    def test_a_setpoint_outside_the_window_outranks_the_uncertainty_finding(self):
        result = condition_margin(_variant(TEMPERATURE, declared_value=28.0))
        self.assertEqual(result["verdict"], OUTSIDE_WINDOW)

    def test_a_margin_landing_exactly_on_zero_is_demonstrated(self):
        exact = _variant(TEMPERATURE, declared_value=26.5, uncertainty=0.5)
        result = condition_margin(exact)
        self.assertEqual(result["verdict"], DEMONSTRATED)
        self.assertAlmostEqual(result["margin"], 0.0, places=9)

    def test_a_signed_deviation_is_reported_not_only_its_size(self):
        result = condition_margin(_variant(TEMPERATURE, declared_value=24.0))
        self.assertAlmostEqual(result["deviation"], -1.0, places=9)

    def test_a_zero_window_is_an_exact_match_not_a_division(self):
        result = condition_margin(CYCLE_COUNT)
        self.assertEqual(result["verdict"], DEMONSTRATED)
        self.assertAlmostEqual(result["window_usage"], 0.0, places=9)

    def test_a_zero_window_missed_is_outside_the_window(self):
        result = condition_margin(_variant(CYCLE_COUNT, declared_value=99.0))
        self.assertEqual(result["verdict"], OUTSIDE_WINDOW)
        self.assertTrue(any("exactly" in f for f in result["findings"]))

    def test_a_zero_window_with_a_blunt_instrument_is_rejected(self):
        with self.assertRaises(ValueError):
            condition_margin(_variant(CYCLE_COUNT, uncertainty=0.5))

    def test_negative_uncertainty_is_rejected(self):
        with self.assertRaises(ValueError):
            condition_margin(_variant(TEMPERATURE, uncertainty=-0.1))

    def test_negative_half_window_is_rejected(self):
        with self.assertRaises(ValueError):
            condition_margin(_variant(TEMPERATURE, half_window=-2.0))

    def test_a_non_numeric_setpoint_is_rejected(self):
        with self.assertRaises(ValueError):
            condition_margin(_variant(TEMPERATURE, declared_value="25 degrees"))

    def test_a_condition_without_a_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            condition_margin(_variant(TEMPERATURE, kind=None))


class MatrixCoverageTests(unittest.TestCase):
    def test_full_coverage_leaves_nothing_missing(self):
        result = matrix_coverage(["SCA-IV-01", "SCA-TC-02"], ["SCA-IV-01", "SCA-TC-02"])
        self.assertEqual(result["missing"], [])
        self.assertAlmostEqual(result["coverage"], 1.0, places=9)

    def test_a_drawing_test_never_declared_is_named(self):
        result = matrix_coverage(["SCA-IV-01"], ["SCA-IV-01", "SCA-TC-02"])
        self.assertEqual(result["missing"], ["SCA-TC-02"])
        self.assertAlmostEqual(result["coverage"], 0.5, places=9)

    def test_a_test_the_drawing_never_called_is_reported_separately(self):
        result = matrix_coverage(["SCA-IV-01", "SCA-XX-99"], ["SCA-IV-01"])
        self.assertEqual(result["undeclared_by_drawing"], ["SCA-XX-99"])

    def test_a_drawing_calling_no_tests_is_rejected(self):
        with self.assertRaises(ValueError):
            matrix_coverage(["SCA-IV-01"], [])

    def test_a_duplicated_declared_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            matrix_coverage(["SCA-IV-01", "SCA-IV-01"], ["SCA-IV-01"])


class TestAssessmentTests(unittest.TestCase):
    def test_a_drawing_method_inside_every_guard_band_is_aligned(self):
        result = assess_test(_variant(PERFORMANCE_TEST, conditions=[TEMPERATURE]))
        self.assertEqual(result["verdict"], TEST_ALIGNED)

    def test_an_undemonstrated_condition_downgrades_the_test(self):
        self.assertEqual(assess_test(PERFORMANCE_TEST)["verdict"], TEST_ALIGNED_UNDER_APPROVAL)

    def test_a_house_method_outranks_every_green_condition(self):
        result = assess_test(
            _variant(PERFORMANCE_TEST, method_source="supplier-internal", conditions=[TEMPERATURE])
        )
        self.assertEqual(result["verdict"], TEST_NOT_ALIGNED)

    def test_a_condition_outside_the_window_fails_the_test(self):
        result = assess_test(
            _variant(
                PERFORMANCE_TEST,
                conditions=[_variant(TEMPERATURE, declared_value=30.0)],
            )
        )
        self.assertEqual(result["verdict"], TEST_NOT_ALIGNED)

    def test_the_governing_condition_is_the_one_eating_most_of_its_window(self):
        self.assertEqual(
            assess_test(PERFORMANCE_TEST)["governing_condition"], "illumination-ratio"
        )

    def test_a_test_with_no_conditions_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_test(_variant(PERFORMANCE_TEST, conditions=[]))

    def test_a_repeated_condition_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_test(_variant(PERFORMANCE_TEST, conditions=[TEMPERATURE, TEMPERATURE]))

    def test_a_non_mapping_test_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_test("SCA-IV-01")

    def test_every_condition_verdict_is_ranked(self):
        for condition in assess_test(PERFORMANCE_TEST)["conditions"]:
            self.assertIn(condition["verdict"], CONDITION_RANK)


class MatrixRollUpTests(unittest.TestCase):
    def test_a_clean_matrix_rolls_up_aligned(self):
        case = {
            "drawing_reference": "SCD-4471",
            "tests": [
                _variant(PERFORMANCE_TEST, conditions=[TEMPERATURE]),
                CYCLING_TEST,
            ],
            "required_test_ids": ["SCA-IV-01", "SCA-TC-02"],
        }
        result = assess_test_matrix(case)
        self.assertEqual(result["verdict"], TEST_ALIGNED)
        self.assertAlmostEqual(result["aligned_share"], 1.0, places=9)

    def test_one_house_method_drags_the_matrix_down_and_is_named(self):
        case = {
            "drawing_reference": "SCD-4471",
            "tests": [
                _variant(PERFORMANCE_TEST, conditions=[TEMPERATURE]),
                _variant(CYCLING_TEST, method_source="supplier-internal"),
            ],
            "required_test_ids": ["SCA-IV-01", "SCA-TC-02"],
        }
        result = assess_test_matrix(case)
        self.assertEqual(result["verdict"], TEST_NOT_ALIGNED)
        self.assertEqual(result["not_aligned_tests"], ["SCA-TC-02"])
        self.assertEqual(result["weakest_test"], "SCA-TC-02")
        self.assertAlmostEqual(result["aligned_share"], 0.5, places=9)

    def test_a_drawing_test_never_run_downgrades_an_otherwise_clean_matrix(self):
        case = {
            "drawing_reference": "SCD-4471",
            "tests": [_variant(PERFORMANCE_TEST, conditions=[TEMPERATURE])],
            "required_test_ids": ["SCA-IV-01", "SCA-TC-02"],
        }
        result = assess_test_matrix(case)
        self.assertEqual(result["verdict"], TEST_ALIGNED_UNDER_APPROVAL)
        self.assertTrue(any("never declares it" in f for f in result["findings"]))

    def test_the_drawing_reference_is_carried_into_the_roll_up(self):
        case = {
            "drawing_reference": "SCD-4471",
            "tests": [CYCLING_TEST],
            "required_test_ids": ["SCA-TC-02"],
        }
        self.assertEqual(assess_test_matrix(case)["drawing_reference"], "SCD-4471")

    def test_a_duplicated_test_identifier_is_rejected(self):
        case = {
            "drawing_reference": "SCD-4471",
            "tests": [CYCLING_TEST, copy.deepcopy(CYCLING_TEST)],
            "required_test_ids": ["SCA-TC-02"],
        }
        with self.assertRaises(ValueError):
            assess_test_matrix(case)

    def test_an_empty_matrix_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_matrix(
                {"drawing_reference": "SCD-4471", "tests": [], "required_test_ids": ["SCA-TC-02"]}
            )

    def test_a_matrix_without_a_drawing_reference_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_matrix({"tests": [CYCLING_TEST], "required_test_ids": ["SCA-TC-02"]})

    def test_every_test_verdict_is_ranked(self):
        case = {
            "drawing_reference": "SCD-4471",
            "tests": [PERFORMANCE_TEST, CYCLING_TEST],
            "required_test_ids": ["SCA-IV-01", "SCA-TC-02"],
        }
        for assessment in assess_test_matrix(case)["assessments"]:
            self.assertIn(assessment["verdict"], TEST_RANK)


if __name__ == "__main__":
    unittest.main()
