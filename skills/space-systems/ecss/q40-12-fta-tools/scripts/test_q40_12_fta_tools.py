#!/usr/bin/env python3
"""Contract test for fault tree analysis tool acceptance (offline)."""

import copy
import unittest

from q40_12_fta_tools_logic import (
    DEFAULT_BENCHMARK_TOLERANCE,
    EXCHANGE_FORMATS,
    QUALIFICATION_REQUIRED,
    RESULT_CRITICALITY,
    TOOL_ACCEPTABLE,
    TOOL_CAPABILITIES,
    TOOL_NOT_ACCEPTABLE,
    TOOL_RESTRICTED,
    USE_WITH_INDEPENDENT_CHECK,
    VALIDATION_BY_BENCHMARK,
    capability_gap,
    evaluate_fta_tool,
    exchange_round_trip,
    format_gap,
    grade_benchmark,
    qualification_level,
    repeatability_deviation,
    validate_tool,
)

TOOL = {
    "name": "tree-bench",
    "version": "4.2.1",
    "capabilities": [
        "minimal-cut-set-expansion",
        "exact-quantification",
        "rare-event-quantification",
        "voting-gate-support",
        "importance-measures",
        "sensitivity-sweep",
    ],
    "exchange_formats": ["neutral-model-exchange", "cut-set-table-export"],
    "under_configuration_control": True,
    "deterministic": True,
}

MODEL_SUMMARY = {
    "gate_count": 12,
    "basic_event_count": 27,
    "cut_set_count": 41,
    "top_event_probability": 3.4e-4,
    "top_event": "loss of pressurisation",
}

CASE = {
    "tool": TOOL,
    "required_capabilities": [
        "minimal-cut-set-expansion",
        "exact-quantification",
        "importance-measures",
    ],
    "benchmark_cases": [
        {"case": "iec-example-a", "tool_value": 0.069, "reference_value": 0.069},
        {"case": "iec-example-b", "tool_value": 2.0e-5, "reference_value": 2.0e-5},
    ],
    "first_run": {"top_event_probability": 3.4e-4, "cut_set_count": 41},
    "second_run": {"top_event_probability": 3.4e-4, "cut_set_count": 41},
    "exported_model": MODEL_SUMMARY,
    "reimported_model": dict(MODEL_SUMMARY),
    "required_formats": ["neutral-model-exchange"],
    "result_criticality": "major",
    "independently_reproduced": True,
}


def _case(**overrides):
    case = copy.deepcopy(CASE)
    case.update(overrides)
    return case


class ToolValidationTests(unittest.TestCase):
    def test_a_well_formed_tool_normalizes(self):
        self.assertEqual(validate_tool(TOOL)["name"], "tree-bench")

    def test_a_non_mapping_tool_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_tool("tree-bench 4.2.1")

    def test_a_tool_without_a_version_is_rejected(self):
        broken = copy.deepcopy(TOOL)
        broken["version"] = "  "
        with self.assertRaises(ValueError):
            validate_tool(broken)

    def test_an_unknown_capability_is_rejected(self):
        broken = copy.deepcopy(TOOL)
        broken["capabilities"].append("reads-minds")
        with self.assertRaises(ValueError):
            validate_tool(broken)

    def test_an_unknown_exchange_format_is_rejected(self):
        broken = copy.deepcopy(TOOL)
        broken["exchange_formats"] = ["fax"]
        with self.assertRaises(ValueError):
            validate_tool(broken)

    def test_a_missing_configuration_control_flag_is_rejected(self):
        broken = copy.deepcopy(TOOL)
        del broken["under_configuration_control"]
        with self.assertRaises(ValueError):
            validate_tool(broken)

    def test_capabilities_normalize_to_a_sorted_unique_tuple(self):
        duplicated = copy.deepcopy(TOOL)
        duplicated["capabilities"].append("exact-quantification")
        self.assertEqual(
            validate_tool(duplicated)["capabilities"], validate_tool(TOOL)["capabilities"]
        )


class GapTests(unittest.TestCase):
    def test_a_covered_need_leaves_no_capability_gap(self):
        self.assertEqual(capability_gap(TOOL, CASE["required_capabilities"]), ())

    def test_an_uncovered_need_is_named(self):
        self.assertEqual(
            capability_gap(TOOL, ["uncertainty-propagation"]),
            ("uncertainty-propagation",),
        )

    def test_an_unknown_required_capability_is_rejected(self):
        with self.assertRaises(ValueError):
            capability_gap(TOOL, ["telepathy"])

    def test_a_missing_exchange_format_is_named(self):
        self.assertEqual(
            format_gap(["human-readable-report"], TOOL["exchange_formats"]),
            ("human-readable-report",),
        )

    def test_a_supported_format_leaves_no_gap(self):
        self.assertEqual(
            format_gap(["neutral-model-exchange"], TOOL["exchange_formats"]), ()
        )

    def test_every_declared_capability_and_format_is_a_known_token(self):
        self.assertIn("minimal-cut-set-expansion", TOOL_CAPABILITIES)
        self.assertIn("neutral-model-exchange", EXCHANGE_FORMATS)


class BenchmarkTests(unittest.TestCase):
    def test_matching_reference_values_grade_clean(self):
        self.assertEqual(
            grade_benchmark(CASE["benchmark_cases"])["verdict"], "benchmark-clean"
        )

    def test_a_deviation_beyond_tolerance_is_named(self):
        graded = grade_benchmark(
            [{"case": "iec-example-a", "tool_value": 0.08, "reference_value": 0.069}]
        )
        self.assertEqual(graded["failed"], ("iec-example-a",))

    def test_a_deviation_exactly_on_the_tolerance_is_within_it(self):
        graded = grade_benchmark(
            [{"case": "edge", "tool_value": 1.001, "reference_value": 1.0}],
            tolerance=1.0e-3,
        )
        self.assertAlmostEqual(
            graded["worst_relative_error"], 1.0e-3, places=9
        )
        self.assertEqual(graded["verdict"], "benchmark-clean")

    def test_a_zero_reference_falls_back_to_the_absolute_deviation(self):
        graded = grade_benchmark(
            [{"case": "zero", "tool_value": 2.0e-4, "reference_value": 0.0}],
            tolerance=DEFAULT_BENCHMARK_TOLERANCE,
        )
        self.assertAlmostEqual(graded["worst_relative_error"], 2.0e-4, places=12)

    def test_an_empty_benchmark_set_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_benchmark([])

    def test_a_repeated_benchmark_case_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_benchmark(
                [
                    {"case": "a", "tool_value": 1.0, "reference_value": 1.0},
                    {"case": "a", "tool_value": 1.0, "reference_value": 1.0},
                ]
            )

    def test_a_non_numeric_tool_value_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_benchmark([{"case": "a", "tool_value": "0.069",
                              "reference_value": 0.069}])


class RepeatabilityAndExchangeTests(unittest.TestCase):
    def test_two_identical_runs_are_repeatable(self):
        result = repeatability_deviation(CASE["first_run"], CASE["second_run"])
        self.assertEqual(result["verdict"], "repeatable")
        self.assertAlmostEqual(result["worst_relative_deviation"], 0.0, places=12)

    def test_a_drifting_rerun_is_not_repeatable(self):
        drifted = dict(CASE["second_run"], top_event_probability=3.5e-4)
        result = repeatability_deviation(CASE["first_run"], drifted)
        self.assertEqual(result["verdict"], "not-repeatable")
        self.assertEqual(result["worst_quantity"], "top_event_probability")

    def test_runs_reporting_different_quantities_are_rejected(self):
        with self.assertRaises(ValueError):
            repeatability_deviation(
                CASE["first_run"], {"top_event_probability": 3.4e-4}
            )

    def test_an_empty_run_is_rejected(self):
        with self.assertRaises(ValueError):
            repeatability_deviation({}, CASE["second_run"])

    def test_an_unchanged_model_round_trips_faithfully(self):
        self.assertTrue(
            exchange_round_trip(MODEL_SUMMARY, dict(MODEL_SUMMARY))["faithful"]
        )

    def test_a_dropped_field_makes_the_round_trip_lossy(self):
        reduced = dict(MODEL_SUMMARY)
        del reduced["top_event"]
        result = exchange_round_trip(MODEL_SUMMARY, reduced)
        self.assertEqual(result["lost_keys"], ("top_event",))
        self.assertEqual(result["verdict"], "round-trip-lossy")

    def test_a_changed_number_makes_the_round_trip_lossy(self):
        altered = dict(MODEL_SUMMARY, cut_set_count=40)
        self.assertEqual(
            exchange_round_trip(MODEL_SUMMARY, altered)["changed_keys"],
            ("cut_set_count",),
        )

    def test_an_empty_model_is_rejected(self):
        with self.assertRaises(ValueError):
            exchange_round_trip(MODEL_SUMMARY, {})


class QualificationLevelTests(unittest.TestCase):
    def test_a_catastrophic_result_without_an_independent_check_needs_qualification(self):
        self.assertEqual(
            qualification_level("catastrophic", False, True), QUALIFICATION_REQUIRED
        )

    def test_a_catastrophic_result_with_an_independent_check_is_allowed(self):
        self.assertEqual(
            qualification_level("catastrophic", True, True),
            USE_WITH_INDEPENDENT_CHECK,
        )

    def test_a_major_result_with_a_clean_benchmark_rests_on_the_benchmark(self):
        self.assertEqual(
            qualification_level("major", False, True), VALIDATION_BY_BENCHMARK
        )

    def test_a_minor_result_with_neither_evidence_still_needs_qualification(self):
        self.assertEqual(
            qualification_level("minor", False, False), QUALIFICATION_REQUIRED
        )

    def test_an_unknown_criticality_is_rejected(self):
        with self.assertRaises(ValueError):
            qualification_level("inconvenient", True, True)

    def test_every_declared_criticality_resolves_to_a_level(self):
        for level in RESULT_CRITICALITY:
            self.assertIn(
                qualification_level(level, True, True),
                (QUALIFICATION_REQUIRED, VALIDATION_BY_BENCHMARK,
                 USE_WITH_INDEPENDENT_CHECK),
            )


class AcceptanceTests(unittest.TestCase):
    def test_a_clean_tool_is_acceptable(self):
        self.assertEqual(evaluate_fta_tool(CASE)["verdict"], TOOL_ACCEPTABLE)

    def test_a_capability_gap_blocks_acceptance(self):
        result = evaluate_fta_tool(
            _case(required_capabilities=["uncertainty-propagation"])
        )
        self.assertEqual(result["verdict"], TOOL_NOT_ACCEPTABLE)
        self.assertEqual(result["capability_gap"], ("uncertainty-propagation",))

    def test_a_failed_benchmark_blocks_acceptance(self):
        result = evaluate_fta_tool(
            _case(benchmark_cases=[
                {"case": "iec-example-a", "tool_value": 0.08,
                 "reference_value": 0.069}
            ])
        )
        self.assertEqual(result["verdict"], TOOL_NOT_ACCEPTABLE)

    def test_a_lossy_round_trip_blocks_acceptance(self):
        reduced = dict(MODEL_SUMMARY)
        del reduced["top_event"]
        self.assertEqual(
            evaluate_fta_tool(_case(reimported_model=reduced))["verdict"],
            TOOL_NOT_ACCEPTABLE,
        )

    def test_a_missing_output_format_restricts_rather_than_blocks(self):
        result = evaluate_fta_tool(_case(required_formats=["human-readable-report"]))
        self.assertEqual(result["verdict"], TOOL_RESTRICTED)
        self.assertTrue(result["restrictions"])

    def test_a_tool_outside_configuration_control_is_restricted(self):
        loose = copy.deepcopy(TOOL)
        loose["under_configuration_control"] = False
        self.assertEqual(evaluate_fta_tool(_case(tool=loose))["verdict"], TOOL_RESTRICTED)

    def test_a_catastrophic_result_without_reproduction_is_restricted(self):
        result = evaluate_fta_tool(
            _case(result_criticality="catastrophic", independently_reproduced=False)
        )
        self.assertEqual(result["qualification_level"], QUALIFICATION_REQUIRED)
        self.assertEqual(result["verdict"], TOOL_RESTRICTED)

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_fta_tool("tree-bench")

    def test_the_verdict_carries_the_tool_version_with_it(self):
        self.assertEqual(evaluate_fta_tool(CASE)["tool"], "tree-bench 4.2.1")


if __name__ == "__main__":
    unittest.main()
