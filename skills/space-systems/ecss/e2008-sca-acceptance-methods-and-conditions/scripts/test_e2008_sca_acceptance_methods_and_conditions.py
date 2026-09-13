"""Contract tests for the clause 6.3.2 acceptance method and condition reuse logic."""

import copy
import unittest

from e2008_sca_acceptance_methods_and_conditions_logic import (
    CONDITION_ESCALATED,
    CONDITION_OMITTED,
    CONDITION_RELAXED,
    CONDITION_REUSED,
    CONDITION_UNBASELINED,
    REUSE_CONFORMING,
    REUSE_DEVIATING,
    TEST_CONDITION_ESCALATED,
    TEST_CONDITION_RELAXED,
    TEST_METHOD_SUBSTITUTED,
    TEST_REUSED,
    TEST_UNBASELINED,
    assess_method_and_condition_reuse,
    compare_condition,
    compare_test,
    validate_condition_baseline,
    validate_identifier,
    validate_real,
    validate_tolerance,
)

# The qualification baseline a solar cell assembly campaign leaves behind:
# the method each activity was run with and the conditions it was run at.
BASELINE = {
    "sca-electrical-performance-measurement": {
        "method": "am0-solar-simulator-iv-sweep",
        "conditions": {
            "irradiance-w-m2": {"value": 1367.0, "sense": "match", "tolerance": 0.02},
            "cell-temperature-c": {"value": 28.0, "sense": "match", "tolerance": 0.02},
            "sweep-point-count": {"value": 200.0, "sense": "at-least", "tolerance": 0.02},
        },
    },
    "sca-visual-inspection": {
        "method": "stereo-microscope-inspection",
        "conditions": {
            "magnification-x": {"value": 10.0, "sense": "at-least", "tolerance": 0.02},
            "illumination-lux": {"value": 1000.0, "sense": "at-least", "tolerance": 0.02},
        },
    },
    "sca-interconnector-adherence-verification": {
        "method": "calibrated-pull-test",
        "conditions": {
            "pull-load-n": {"value": 2.0, "sense": "match", "tolerance": 0.05},
            "pull-rate-mm-min": {"value": 50.0, "sense": "at-most", "tolerance": 0.05},
        },
    },
}


def _declared(**overrides):
    tests = [
        {
            "test": "sca-electrical-performance-measurement",
            "method": "am0-solar-simulator-iv-sweep",
            "conditions": {
                "irradiance-w-m2": 1367.0,
                "cell-temperature-c": 28.0,
                "sweep-point-count": 200.0,
            },
        },
        {
            "test": "sca-visual-inspection",
            "method": "stereo-microscope-inspection",
            "conditions": {"magnification-x": 10.0, "illumination-lux": 1000.0},
        },
        {
            "test": "sca-interconnector-adherence-verification",
            "method": "calibrated-pull-test",
            "conditions": {"pull-load-n": 2.0, "pull-rate-mm-min": 50.0},
        },
    ]
    out = copy.deepcopy(tests)
    for index, activity in enumerate(out):
        if activity["test"] in overrides:
            activity.update(copy.deepcopy(overrides[activity["test"]]))
            out[index] = activity
    return out


def _spec(**overrides):
    spec = {
        "procedure_id": "SCA-ATP-3310 rev A",
        "qualification_baseline": copy.deepcopy(BASELINE),
        "acceptance_tests": _declared(),
    }
    spec.update(overrides)
    return spec


class ValidationHelperTests(unittest.TestCase):
    def test_identifier_is_trimmed(self):
        self.assertEqual(validate_identifier("  SCA-ATP-3310 ", "id"), "SCA-ATP-3310")

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("  ", "id")

    def test_boolean_rejected_as_a_real_number(self):
        with self.assertRaises(ValueError):
            validate_real(False, "value")

    def test_infinite_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_real(float("nan"), "value")

    def test_tolerance_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_tolerance(1.0, "tolerance")

    def test_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_tolerance(-0.01, "tolerance")

    def test_baseline_condition_defaults_to_match(self):
        row = validate_condition_baseline({"value": 5.0}, "pull-load-n")
        self.assertEqual(row["sense"], "match")

    def test_unknown_sense_rejected(self):
        with self.assertRaises(ValueError):
            validate_condition_baseline({"value": 5.0, "sense": "roughly"}, "c")

    def test_baseline_condition_without_a_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_condition_baseline({"sense": "match"}, "c")

    def test_non_mapping_baseline_condition_rejected(self):
        with self.assertRaises(ValueError):
            compare_condition(5.0, [1, 2, 3])


class ConditionComparisonTests(unittest.TestCase):
    def test_identical_condition_is_reuse(self):
        row = compare_condition(1367.0, {"condition": "irradiance-w-m2", "value": 1367.0})
        self.assertEqual(row["verdict"], CONDITION_REUSED)
        self.assertAlmostEqual(row["relative_deviation"], 0.0, places=9)

    def test_condition_inside_the_tolerance_band_is_reuse(self):
        row = compare_condition(
            1380.0,
            {"condition": "irradiance-w-m2", "value": 1367.0, "tolerance": 0.02},
        )
        self.assertTrue(row["within_tolerance"])
        self.assertEqual(row["verdict"], CONDITION_REUSED)

    def test_condition_exactly_on_the_tolerance_edge_is_reuse(self):
        row = compare_condition(
            102.0, {"condition": "c", "value": 100.0, "tolerance": 0.02, "sense": "match"}
        )
        self.assertAlmostEqual(row["relative_deviation"], 0.02, places=9)
        self.assertEqual(row["verdict"], CONDITION_REUSED)

    def test_severity_condition_below_baseline_is_a_relaxation(self):
        row = compare_condition(
            5.0,
            {"condition": "magnification-x", "value": 10.0, "sense": "at-least",
             "tolerance": 0.02},
        )
        self.assertEqual(row["verdict"], CONDITION_RELAXED)
        self.assertAlmostEqual(row["relative_deviation"], -0.5, places=9)

    def test_severity_condition_modestly_above_baseline_is_still_reuse(self):
        row = compare_condition(
            11.0,
            {"condition": "magnification-x", "value": 10.0, "sense": "at-least",
             "tolerance": 0.02},
        )
        self.assertEqual(row["verdict"], CONDITION_REUSED)

    def test_severity_condition_far_above_baseline_is_an_escalation(self):
        row = compare_condition(
            40.0,
            {"condition": "magnification-x", "value": 10.0, "sense": "at-least",
             "tolerance": 0.02},
        )
        self.assertEqual(row["verdict"], CONDITION_ESCALATED)

    def test_limit_condition_above_baseline_is_a_relaxation(self):
        row = compare_condition(
            80.0,
            {"condition": "pull-rate-mm-min", "value": 50.0, "sense": "at-most",
             "tolerance": 0.05},
        )
        self.assertEqual(row["verdict"], CONDITION_RELAXED)

    def test_limit_condition_far_below_baseline_is_an_escalation(self):
        row = compare_condition(
            5.0,
            {"condition": "pull-rate-mm-min", "value": 50.0, "sense": "at-most",
             "tolerance": 0.05},
        )
        self.assertEqual(row["verdict"], CONDITION_ESCALATED)

    def test_matched_condition_below_baseline_is_a_relaxation(self):
        row = compare_condition(
            900.0,
            {"condition": "illumination-lux", "value": 1000.0, "sense": "match",
             "tolerance": 0.02},
        )
        self.assertEqual(row["verdict"], CONDITION_RELAXED)

    def test_over_test_factor_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            compare_condition(
                10.0, {"condition": "c", "value": 10.0}, over_test_factor=0.8
            )

    def test_zero_baseline_uses_an_absolute_band(self):
        row = compare_condition(
            0.01, {"condition": "offset", "value": 0.0, "sense": "match", "tolerance": 0.02}
        )
        self.assertEqual(row["verdict"], CONDITION_REUSED)


class TestActivityComparisonTests(unittest.TestCase):
    def test_identical_activity_reuses_the_baseline(self):
        row = compare_test(_declared()[1], BASELINE["sca-visual-inspection"])
        self.assertEqual(row["verdict"], TEST_REUSED)
        self.assertTrue(row["method_reused"])

    def test_activity_with_no_baseline_is_ranked_worst(self):
        row = compare_test({"test": "sca-tape-peel-check", "method": "adhesive-tape"}, None)
        self.assertEqual(row["verdict"], TEST_UNBASELINED)
        self.assertEqual(row["rank"], 0)

    def test_substituted_method_outranks_a_condition_deviation(self):
        declared = copy.deepcopy(_declared()[1])
        declared["method"] = "unaided-eye-inspection"
        declared["conditions"]["magnification-x"] = 2.0
        row = compare_test(declared, BASELINE["sca-visual-inspection"])
        self.assertEqual(row["verdict"], TEST_METHOD_SUBSTITUTED)

    def test_relaxed_condition_marks_the_activity_relaxed(self):
        declared = copy.deepcopy(_declared()[1])
        declared["conditions"]["illumination-lux"] = 300.0
        row = compare_test(declared, BASELINE["sca-visual-inspection"])
        self.assertEqual(row["verdict"], TEST_CONDITION_RELAXED)
        self.assertEqual(row["relaxed_conditions"], ["illumination-lux"])

    def test_omitted_condition_is_treated_as_a_reuse_gap(self):
        declared = copy.deepcopy(_declared()[1])
        del declared["conditions"]["illumination-lux"]
        row = compare_test(declared, BASELINE["sca-visual-inspection"])
        self.assertEqual(row["omitted_conditions"], ["illumination-lux"])
        self.assertEqual(row["verdict"], TEST_CONDITION_RELAXED)

    def test_condition_absent_from_the_baseline_is_named(self):
        declared = copy.deepcopy(_declared()[1])
        declared["conditions"]["dwell-time-s"] = 30.0
        row = compare_test(declared, BASELINE["sca-visual-inspection"])
        self.assertEqual(row["unbaselined_conditions"], ["dwell-time-s"])
        verdicts = [c["verdict"] for c in row["conditions"]]
        self.assertIn(CONDITION_UNBASELINED, verdicts)

    def test_escalation_alone_marks_the_activity_escalated(self):
        declared = copy.deepcopy(_declared()[1])
        declared["conditions"]["magnification-x"] = 60.0
        row = compare_test(declared, BASELINE["sca-visual-inspection"])
        self.assertEqual(row["verdict"], TEST_CONDITION_ESCALATED)
        self.assertEqual(row["escalated_conditions"], ["magnification-x"])

    def test_relaxation_outranks_an_escalation(self):
        declared = copy.deepcopy(_declared()[1])
        declared["conditions"]["magnification-x"] = 60.0
        declared["conditions"]["illumination-lux"] = 100.0
        row = compare_test(declared, BASELINE["sca-visual-inspection"])
        self.assertEqual(row["verdict"], TEST_CONDITION_RELAXED)

    def test_omitted_condition_row_records_the_baseline(self):
        declared = copy.deepcopy(_declared()[1])
        del declared["conditions"]["magnification-x"]
        row = compare_test(declared, BASELINE["sca-visual-inspection"])
        omitted = [c for c in row["conditions"] if c["verdict"] == CONDITION_OMITTED][0]
        self.assertAlmostEqual(omitted["baseline"], 10.0, places=9)
        self.assertIsNone(omitted["declared"])

    def test_non_mapping_conditions_rejected(self):
        declared = copy.deepcopy(_declared()[1])
        declared["conditions"] = ["magnification-x"]
        with self.assertRaises(ValueError):
            compare_test(declared, BASELINE["sca-visual-inspection"])

    def test_activity_without_a_method_rejected(self):
        declared = copy.deepcopy(_declared()[1])
        del declared["method"]
        with self.assertRaises(ValueError):
            compare_test(declared, BASELINE["sca-visual-inspection"])


class ProcedureAssessmentTests(unittest.TestCase):
    def test_clean_procedure_conforms(self):
        result = assess_method_and_condition_reuse(_spec())
        self.assertEqual(result["verdict"], REUSE_CONFORMING)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["reuse_share"], 1.0, places=9)

    def test_substituted_method_deviates(self):
        spec = _spec(
            acceptance_tests=_declared(
                **{"sca-visual-inspection": {"method": "unaided-eye-inspection"}}
            )
        )
        result = assess_method_and_condition_reuse(spec)
        self.assertEqual(result["verdict"], REUSE_DEVIATING)
        self.assertEqual(
            result["tests_by_verdict"][TEST_METHOD_SUBSTITUTED], ["sca-visual-inspection"]
        )

    def test_relaxed_condition_reaches_the_findings(self):
        spec = _spec(
            acceptance_tests=_declared(
                **{
                    "sca-electrical-performance-measurement": {
                        "conditions": {
                            "irradiance-w-m2": 1000.0,
                            "cell-temperature-c": 28.0,
                            "sweep-point-count": 200.0,
                        }
                    }
                }
            )
        )
        result = assess_method_and_condition_reuse(spec)
        self.assertEqual(result["verdict"], REUSE_DEVIATING)
        self.assertTrue(any("irradiance-w-m2" in f for f in result["findings"]))

    def test_activity_with_no_baseline_is_reported_first(self):
        spec = _spec()
        spec["acceptance_tests"] = spec["acceptance_tests"] + [
            {"test": "sca-tape-peel-check", "method": "adhesive-tape", "conditions": {}}
        ]
        result = assess_method_and_condition_reuse(spec)
        self.assertIn("sca-tape-peel-check", result["findings"][0])
        self.assertEqual(
            result["tests_by_verdict"][TEST_UNBASELINED], ["sca-tape-peel-check"]
        )

    def test_baseline_activity_not_reused_is_listed_without_being_a_finding(self):
        spec = _spec()
        spec["acceptance_tests"] = [
            a for a in spec["acceptance_tests"] if a["test"] != "sca-visual-inspection"
        ]
        result = assess_method_and_condition_reuse(spec)
        self.assertEqual(result["baseline_tests_not_reused"], ["sca-visual-inspection"])
        self.assertEqual(result["verdict"], REUSE_CONFORMING)

    def test_reuse_share_drops_with_one_deviating_activity(self):
        spec = _spec(
            acceptance_tests=_declared(
                **{"sca-visual-inspection": {"method": "unaided-eye-inspection"}}
            )
        )
        result = assess_method_and_condition_reuse(spec)
        self.assertAlmostEqual(result["reuse_share"], 2.0 / 3.0, places=9)

    def test_over_test_factor_can_be_tightened(self):
        spec = _spec(over_test_factor=1.05)
        spec["acceptance_tests"] = _declared(
            **{
                "sca-visual-inspection": {
                    "conditions": {"magnification-x": 12.0, "illumination-lux": 1000.0}
                }
            }
        )
        result = assess_method_and_condition_reuse(spec)
        self.assertEqual(
            result["tests_by_verdict"][TEST_CONDITION_ESCALATED], ["sca-visual-inspection"]
        )

    def test_duplicate_acceptance_activity_rejected(self):
        spec = _spec()
        spec["acceptance_tests"] = spec["acceptance_tests"] + [
            copy.deepcopy(spec["acceptance_tests"][0])
        ]
        with self.assertRaises(ValueError):
            assess_method_and_condition_reuse(spec)

    def test_empty_baseline_rejected(self):
        with self.assertRaises(ValueError):
            assess_method_and_condition_reuse(_spec(qualification_baseline={}))

    def test_empty_acceptance_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_method_and_condition_reuse(_spec(acceptance_tests=[]))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["qualification_baseline"]
        with self.assertRaises(ValueError):
            assess_method_and_condition_reuse(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_method_and_condition_reuse(["SCA-ATP-3310"])

    def test_over_test_factor_below_unity_rejected_by_the_assessment(self):
        with self.assertRaises(ValueError):
            assess_method_and_condition_reuse(_spec(over_test_factor=0.9))

    def test_procedure_id_is_trimmed_in_the_report(self):
        result = assess_method_and_condition_reuse(
            _spec(procedure_id="  SCA-ATP-3310 rev A  ")
        )
        self.assertEqual(result["procedure_id"], "SCA-ATP-3310 rev A")


if __name__ == "__main__":
    unittest.main()
