#!/usr/bin/env python3
"""Gate 3 contract test for e2001-test-execution-control.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2001_test_execution_control.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2001_test_execution_control_logic import (  # noqa: E402
    EXPECTED_PROCEDURE_ELEMENTS,
    KNOWN_STEPS,
    assess_test_execution_control,
    at_or_above,
    categorize_deviation,
    deviation_index,
    evaluate_execution_log,
    missing_procedure_elements,
    normalise_step_order,
    precedence_violations,
    required_test_level_w,
    validate_power_schedule,
)

CANONICAL_ORDER = list(KNOWN_STEPS)


def codes(findings):
    return [finding["code"] for finding in findings]


def accumulated_level_w(nominal_w, fraction, count):
    """Level a data system reports after adding ``count`` equal contributions.

    The contributions are added one at a time, in plain IEEE-754 arithmetic
    rather than the compensated summation the builtin sum() applies to
    floats, so the few-ULP shortfall this reproduces is the same on every
    platform and every Python version.
    """
    total = 0.0
    for _ in range(count):
        total += fraction
    return nominal_w * total


class TestProcedureContent(unittest.TestCase):
    def test_complete_procedure_has_nothing_missing(self):
        self.assertEqual(missing_procedure_elements(list(EXPECTED_PROCEDURE_ELEMENTS)), [])

    def test_absent_element_reported(self):
        elements = [e for e in EXPECTED_PROCEDURE_ELEMENTS if e != "power-profile"]
        self.assertEqual(missing_procedure_elements(elements), ["power-profile"])

    def test_several_absent_elements_keep_canonical_order(self):
        elements = [
            e
            for e in EXPECTED_PROCEDURE_ELEMENTS
            if e not in ("abort-criteria", "item-identification")
        ]
        self.assertEqual(
            missing_procedure_elements(elements),
            ["item-identification", "abort-criteria"],
        )

    def test_set_input_accepted(self):
        self.assertEqual(missing_procedure_elements(set(EXPECTED_PROCEDURE_ELEMENTS)), [])

    def test_unknown_element_rejected(self):
        with self.assertRaises(ValueError):
            missing_procedure_elements(["item-identification", "coffee-break"])

    def test_non_sequence_elements_rejected(self):
        with self.assertRaises(ValueError):
            missing_procedure_elements("item-identification")

    def test_non_string_element_rejected(self):
        with self.assertRaises(ValueError):
            missing_procedure_elements([7])


class TestStepOrder(unittest.TestCase):
    def test_canonical_order_normalises(self):
        self.assertEqual(normalise_step_order(CANONICAL_ORDER), CANONICAL_ORDER)

    def test_unknown_step_rejected(self):
        with self.assertRaises(ValueError):
            normalise_step_order(["chamber-pumpdown", "coffee-break"])

    def test_repeated_step_rejected(self):
        with self.assertRaises(ValueError):
            normalise_step_order(["power-ramp", "power-ramp"])

    def test_empty_order_rejected(self):
        with self.assertRaises(ValueError):
            normalise_step_order([])

    def test_non_sequence_order_rejected(self):
        with self.assertRaises(ValueError):
            normalise_step_order("power-ramp")

    def test_canonical_order_breaks_no_precedence(self):
        self.assertEqual(precedence_violations(CANONICAL_ORDER), [])

    def test_calibration_after_power_is_a_violation(self):
        order = [s for s in CANONICAL_ORDER if s != "path-calibration"]
        order.insert(order.index("power-ramp") + 1, "path-calibration")
        violations = precedence_violations(order)
        self.assertEqual(codes(violations), ["step-precedence-broken"])
        self.assertEqual(violations[0]["earlier"], "path-calibration")

    def test_vent_before_power_down_is_a_violation(self):
        order = list(CANONICAL_ORDER)
        i, j = order.index("power-down"), order.index("chamber-vent")
        order[i], order[j] = order[j], order[i]
        violations = precedence_violations(order)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["later"], "chamber-vent")

    def test_every_violated_pair_is_reported(self):
        violations = precedence_violations(list(reversed(CANONICAL_ORDER)))
        self.assertGreaterEqual(len(violations), 5)

    def test_partial_order_skips_absent_pairs(self):
        self.assertEqual(
            precedence_violations(["path-calibration", "power-ramp"]), []
        )

    def test_detection_baseline_after_power_is_a_violation(self):
        order = [s for s in CANONICAL_ORDER if s != "detection-baseline-check"]
        order.insert(order.index("power-ramp") + 1, "detection-baseline-check")
        self.assertEqual(
            precedence_violations(order)[0]["earlier"], "detection-baseline-check"
        )


class TestRequiredLevel(unittest.TestCase):
    def test_three_db_roughly_doubles_the_power(self):
        self.assertAlmostEqual(required_test_level_w(100.0, 3.0), 199.526231, places=5)

    def test_zero_margin_returns_nominal(self):
        self.assertAlmostEqual(required_test_level_w(250.0, 0.0), 250.0, places=9)

    def test_six_db_quadruples_the_power(self):
        self.assertAlmostEqual(
            required_test_level_w(50.0, 10.0 * 0.6020599913279624) / 50.0, 4.0, places=9
        )

    def test_negative_margin_rejected(self):
        with self.assertRaises(ValueError):
            required_test_level_w(100.0, -1.0)

    def test_zero_nominal_rejected(self):
        with self.assertRaises(ValueError):
            required_test_level_w(0.0, 3.0)

    def test_non_numeric_nominal_rejected(self):
        with self.assertRaises(ValueError):
            required_test_level_w("100", 3.0)


class TestLimitComparison(unittest.TestCase):
    def test_exact_equality_reaches_the_limit(self):
        self.assertTrue(at_or_above(199.52623149688787, 199.52623149688787))

    def test_representation_error_absorbed(self):
        # Ten measured contributions summed back to the un-margined level:
        # binary addition lands the total a few ULPs under it on every
        # IEEE-754 platform, and that shortfall is representation, not power.
        required = required_test_level_w(100.0, 0.0)
        summed = accumulated_level_w(100.0, 0.1, 10)
        self.assertLess(summed, required)
        self.assertTrue(at_or_above(summed, required))

    def test_real_shortfall_fails(self):
        required = required_test_level_w(100.0, 3.0)
        self.assertFalse(at_or_above(required * 0.999, required))


class TestPowerSchedule(unittest.TestCase):
    def good_steps(self):
        return [
            {"level_w": 100.0, "dwell_s": 120.0},
            {"level_w": 150.0, "dwell_s": 120.0},
            {"level_w": 200.0, "dwell_s": 120.0},
        ]

    def test_sound_staircase_has_no_findings(self):
        self.assertEqual(
            validate_power_schedule(self.good_steps(), required_test_level_w(100.0, 3.0)),
            [],
        )

    def test_summed_peak_at_the_limit_is_accepted(self):
        required = required_test_level_w(100.0, 0.0)
        peak = accumulated_level_w(100.0, 0.1, 10)
        self.assertLess(peak, required)  # a genuine few-ULP shortfall
        steps = [{"level_w": peak, "dwell_s": 120.0}]
        self.assertEqual(validate_power_schedule(steps, required), [])

    def test_equal_consecutive_levels_allowed(self):
        steps = self.good_steps()
        steps[1]["level_w"] = 100.0
        self.assertEqual(
            validate_power_schedule(steps, required_test_level_w(100.0, 3.0)), []
        )

    def test_peak_below_required_flagged(self):
        steps = self.good_steps()
        steps[2]["level_w"] = 180.0
        findings = validate_power_schedule(steps, required_test_level_w(100.0, 3.0))
        self.assertEqual(codes(findings), ["test-level-not-reached"])

    def test_non_monotonic_staircase_flagged(self):
        steps = self.good_steps()
        steps[1]["level_w"] = 90.0
        findings = validate_power_schedule(steps, required_test_level_w(100.0, 3.0))
        self.assertEqual(codes(findings), ["power-step-not-monotonic"])
        self.assertEqual(findings[0]["index"], 1)

    def test_short_dwell_flagged(self):
        steps = self.good_steps()
        steps[0]["dwell_s"] = 10.0
        findings = validate_power_schedule(
            steps, required_test_level_w(100.0, 3.0), min_dwell_s=60.0
        )
        self.assertEqual(codes(findings), ["dwell-too-short"])
        self.assertEqual(findings[0]["index"], 0)

    def test_dwell_exactly_at_the_floor_is_accepted(self):
        steps = self.good_steps()
        steps[0]["dwell_s"] = 60.0
        self.assertEqual(
            validate_power_schedule(
                steps, required_test_level_w(100.0, 3.0), min_dwell_s=60.0
            ),
            [],
        )

    def test_empty_schedule_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_schedule([], 200.0)

    def test_non_sequence_schedule_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_schedule({"level_w": 100.0, "dwell_s": 60.0}, 200.0)

    def test_entry_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_schedule([{"level_w": 100.0}], 200.0)

    def test_entry_unknown_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_schedule(
                [{"level_w": 100.0, "dwell_s": 60.0, "operator": "A"}], 200.0
            )

    def test_entry_not_a_mapping_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_schedule([(100.0, 60.0)], 200.0)

    def test_negative_level_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_schedule([{"level_w": -1.0, "dwell_s": 60.0}], 200.0)

    def test_zero_dwell_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_schedule([{"level_w": 200.0, "dwell_s": 0.0}], 200.0)

    def test_non_positive_dwell_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_power_schedule(self.good_steps(), 200.0, min_dwell_s=0.0)


class TestDeviations(unittest.TestCase):
    def test_full_record_is_an_authorised_deviation(self):
        record = {
            "step": "hold-at-level",
            "reason": "amplifier interlock tripped",
            "authorised_by": "test-conductor",
        }
        self.assertEqual(categorize_deviation(record), "authorised-deviation")

    def test_missing_authoriser_is_unauthorised(self):
        record = {"step": "hold-at-level", "reason": "interlock tripped"}
        self.assertEqual(categorize_deviation(record), "unauthorised")

    def test_blank_authoriser_is_unauthorised(self):
        record = {
            "step": "hold-at-level",
            "reason": "interlock tripped",
            "authorised_by": "   ",
        }
        self.assertEqual(categorize_deviation(record), "unauthorised")

    def test_missing_reason_is_uncontrolled(self):
        record = {"step": "hold-at-level", "authorised_by": "test-conductor"}
        self.assertEqual(categorize_deviation(record), "uncontrolled")

    def test_unknown_step_in_record_rejected(self):
        with self.assertRaises(ValueError):
            categorize_deviation({"step": "coffee-break", "reason": "r"})

    def test_unknown_key_in_record_rejected(self):
        with self.assertRaises(ValueError):
            categorize_deviation(
                {"step": "power-ramp", "reason": "r", "waiver_number": 3}
            )

    def test_non_mapping_record_rejected(self):
        with self.assertRaises(ValueError):
            categorize_deviation(["power-ramp"])

    def test_index_of_no_records_is_empty(self):
        self.assertEqual(deviation_index(None), {})

    def test_index_maps_step_to_state(self):
        records = [
            {"step": "power-ramp", "reason": "r", "authorised_by": "a"},
            {"step": "chamber-vent", "reason": "r"},
        ]
        self.assertEqual(
            deviation_index(records),
            {"power-ramp": "authorised-deviation", "chamber-vent": "unauthorised"},
        )

    def test_contradictory_records_rejected(self):
        records = [
            {"step": "power-ramp", "reason": "r", "authorised_by": "a"},
            {"step": "power-ramp", "reason": "r"},
        ]
        with self.assertRaises(ValueError):
            deviation_index(records)

    def test_non_sequence_records_rejected(self):
        with self.assertRaises(ValueError):
            deviation_index({"step": "power-ramp"})


class TestExecutionLog(unittest.TestCase):
    def test_faithful_execution_has_no_findings(self):
        self.assertEqual(evaluate_execution_log(CANONICAL_ORDER, CANONICAL_ORDER), [])

    def test_skipped_step_without_deviation_flagged(self):
        executed = [s for s in CANONICAL_ORDER if s != "detection-baseline-check"]
        findings = evaluate_execution_log(CANONICAL_ORDER, executed)
        self.assertEqual(codes(findings), ["step-not-executed-uncontrolled"])
        self.assertEqual(findings[0]["step"], "detection-baseline-check")

    def test_skipped_step_with_authorised_deviation_accepted(self):
        executed = [s for s in CANONICAL_ORDER if s != "chamber-vent"]
        records = [
            {
                "step": "chamber-vent",
                "reason": "item stayed under vacuum for the next run",
                "authorised_by": "test-conductor",
            }
        ]
        self.assertEqual(
            evaluate_execution_log(CANONICAL_ORDER, executed, records), []
        )

    def test_skipped_step_with_unauthorised_deviation_flagged_twice(self):
        executed = [s for s in CANONICAL_ORDER if s != "chamber-vent"]
        records = [{"step": "chamber-vent", "reason": "kept under vacuum"}]
        found = codes(evaluate_execution_log(CANONICAL_ORDER, executed, records))
        self.assertIn("deviation-not-authorised", found)
        self.assertIn("step-not-executed-uncontrolled", found)

    def test_record_without_reason_flagged(self):
        records = [{"step": "power-ramp", "authorised_by": "test-conductor"}]
        found = codes(evaluate_execution_log(CANONICAL_ORDER, CANONICAL_ORDER, records))
        self.assertEqual(found, ["deviation-without-reason"])

    def test_out_of_order_execution_flagged(self):
        executed = list(CANONICAL_ORDER)
        i, j = executed.index("path-calibration"), executed.index("power-ramp")
        executed[i], executed[j] = executed[j], executed[i]
        self.assertIn(
            "step-order-violation", codes(evaluate_execution_log(CANONICAL_ORDER, executed))
        )

    def test_executed_step_outside_the_procedure_rejected(self):
        order = [s for s in CANONICAL_ORDER if s != "data-archive"]
        with self.assertRaises(ValueError):
            evaluate_execution_log(order, CANONICAL_ORDER)

    def test_empty_execution_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_execution_log(CANONICAL_ORDER, [])


class TestAssessment(unittest.TestCase):
    def procedure(self):
        return {
            "elements": list(EXPECTED_PROCEDURE_ELEMENTS),
            "step_order": list(CANONICAL_ORDER),
            "power_steps": [
                {"level_w": 100.0, "dwell_s": 120.0},
                {"level_w": 150.0, "dwell_s": 120.0},
                {"level_w": 200.0, "dwell_s": 120.0},
            ],
            "nominal_power_w": 100.0,
            "margin_db": 3.0,
        }

    def execution(self):
        return {"executed_steps": list(CANONICAL_ORDER)}

    def test_controlled_run(self):
        result = assess_test_execution_control(self.procedure(), self.execution())
        self.assertTrue(result["controlled"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["missing_procedure_elements"], [])
        self.assertAlmostEqual(result["required_test_level_w"], 199.526231, places=5)

    def test_missing_element_makes_the_run_uncontrolled(self):
        procedure = self.procedure()
        procedure["elements"] = [
            e for e in EXPECTED_PROCEDURE_ELEMENTS if e != "abort-criteria"
        ]
        result = assess_test_execution_control(procedure, self.execution())
        self.assertFalse(result["controlled"])
        self.assertEqual(codes(result["findings"]), ["procedure-element-missing"])

    def test_broken_precedence_reported(self):
        procedure = self.procedure()
        order = [s for s in CANONICAL_ORDER if s != "path-calibration"]
        order.insert(order.index("power-ramp") + 1, "path-calibration")
        procedure["step_order"] = order
        result = assess_test_execution_control(
            procedure, {"executed_steps": list(order)}
        )
        self.assertIn("step-precedence-broken", codes(result["findings"]))

    def test_schedule_finding_reported(self):
        procedure = self.procedure()
        procedure["power_steps"][2]["level_w"] = 120.0
        result = assess_test_execution_control(procedure, self.execution())
        self.assertIn("test-level-not-reached", codes(result["findings"]))

    def test_short_dwell_honours_procedure_floor(self):
        procedure = self.procedure()
        procedure["min_dwell_s"] = 300.0
        result = assess_test_execution_control(procedure, self.execution())
        self.assertEqual(
            set(codes(result["findings"])), {"dwell-too-short"}
        )

    def test_execution_finding_reported(self):
        execution = {
            "executed_steps": [s for s in CANONICAL_ORDER if s != "power-down"]
        }
        result = assess_test_execution_control(self.procedure(), execution)
        self.assertIn("step-not-executed-uncontrolled", codes(result["findings"]))

    def test_authorised_deviation_keeps_the_run_controlled(self):
        execution = {
            "executed_steps": [s for s in CANONICAL_ORDER if s != "chamber-vent"],
            "deviations": [
                {
                    "step": "chamber-vent",
                    "reason": "item held under vacuum for the next run",
                    "authorised_by": "test-conductor",
                }
            ],
        }
        self.assertTrue(
            assess_test_execution_control(self.procedure(), execution)["controlled"]
        )

    def test_unknown_key_rejected(self):
        procedure = self.procedure()
        procedure["chamber_pressure_pa"] = 1e-5
        with self.assertRaises(ValueError):
            assess_test_execution_control(procedure, self.execution())

    def test_missing_procedure_key_rejected(self):
        procedure = self.procedure()
        del procedure["margin_db"]
        with self.assertRaises(ValueError):
            assess_test_execution_control(procedure, self.execution())

    def test_missing_executed_steps_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_execution_control(self.procedure(), {})

    def test_non_mapping_inputs_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_execution_control(self.procedure(), ["power-ramp"])


if __name__ == "__main__":
    unittest.main()
