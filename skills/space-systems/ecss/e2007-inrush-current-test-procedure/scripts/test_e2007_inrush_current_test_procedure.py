#!/usr/bin/env python3
"""Gate 3 contract test for e2007-inrush-current-test-procedure.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_inrush_current_test_procedure.py
"""

import unittest

from e2007_inrush_current_test_procedure_logic import (
    CHECK_OMITTED,
    CHECK_OUT_OF_TOLERANCE,
    CHECK_PASSED,
    VERDICT_COMPLIANT,
    VERDICT_DEFICIENT,
    assess_inrush_procedure,
    build_switching_sequence,
    capture_window_findings,
    chain_check_status,
    min_recovery_time_s,
    recovery_is_sufficient,
    residual_charge_fraction,
    sequence_duration_s,
    stabilisation_is_complete,
    trigger_findings,
    validate_procedure,
)

TAU_S = 0.02


def good_procedure(**over):
    record = {
        "capture_armed_before_switching": True,
        "chain_check_performed": True,
        "chain_check_error_pct": 1.0,
        "chain_check_tolerance_pct": 3.0,
        "switch_on_events": 3,
        "stabilisation_dwell_s": 600.0,
        "required_dwell_s": 300.0,
        "filter_time_constant_s": TAU_S,
        "off_time_s": 0.5,
        "trigger_level_a": 2.0,
        "noise_floor_a": 0.1,
        "expected_peak_a": 12.0,
        "pre_trigger_s": 0.006,
        "record_length_s": 0.06,
        "transient_duration_s": 0.05,
    }
    record.update(over)
    return record


class TestProcedureValidation(unittest.TestCase):
    def test_good_procedure_normalizes(self):
        procedure = validate_procedure(good_procedure())
        self.assertEqual(procedure["switch_on_events"], 3)
        self.assertAlmostEqual(procedure["off_time_s"], 0.5, places=9)

    def test_missing_field_is_rejected(self):
        record = good_procedure()
        del record["trigger_level_a"]
        with self.assertRaises(ValueError):
            validate_procedure(record)

    def test_negative_dwell_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_procedure(good_procedure(stabilisation_dwell_s=-1.0))

    def test_zero_required_dwell_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_procedure(good_procedure(required_dwell_s=0.0))

    def test_non_boolean_arming_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_procedure(good_procedure(capture_armed_before_switching="yes"))

    def test_fractional_event_count_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_procedure(good_procedure(switch_on_events=2.5))

    def test_boolean_event_count_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_procedure(good_procedure(switch_on_events=True))

    def test_zero_events_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_procedure(good_procedure(switch_on_events=0))

    def test_noise_floor_above_the_expected_peak_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_procedure(good_procedure(noise_floor_a=20.0))

    def test_negative_chain_check_error_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_procedure(good_procedure(chain_check_error_pct=-0.5))


class TestStabilisation(unittest.TestCase):
    def test_a_long_dwell_is_complete(self):
        self.assertTrue(stabilisation_is_complete(600.0, 300.0))

    def test_a_dwell_landing_exactly_on_the_requirement_is_complete(self):
        self.assertTrue(stabilisation_is_complete(300.0, 3.0 * 100.0))

    def test_a_short_dwell_is_incomplete(self):
        self.assertFalse(stabilisation_is_complete(120.0, 300.0))

    def test_negative_dwell_raises(self):
        with self.assertRaises(ValueError):
            stabilisation_is_complete(-1.0, 300.0)


class TestRecovery(unittest.TestCase):
    def test_min_recovery_is_the_declared_multiple_of_tau(self):
        self.assertAlmostEqual(min_recovery_time_s(TAU_S, 5.0), 0.1, places=9)

    def test_off_time_landing_on_the_requirement_is_sufficient(self):
        self.assertTrue(recovery_is_sufficient(5.0 * TAU_S, TAU_S, 5.0))

    def test_a_short_off_time_is_insufficient(self):
        self.assertFalse(recovery_is_sufficient(0.03, TAU_S, 5.0))

    def test_discharge_constants_below_unity_are_rejected(self):
        with self.assertRaises(ValueError):
            min_recovery_time_s(TAU_S, 0.5)

    def test_no_off_time_leaves_the_filter_fully_charged(self):
        self.assertAlmostEqual(residual_charge_fraction(0.0, TAU_S), 1.0, places=9)

    def test_residual_charge_falls_as_the_off_time_grows(self):
        early = residual_charge_fraction(TAU_S, TAU_S)
        late = residual_charge_fraction(5.0 * TAU_S, TAU_S)
        self.assertLess(late, early)

    def test_residual_charge_rejects_a_zero_time_constant(self):
        with self.assertRaises(ValueError):
            residual_charge_fraction(0.1, 0.0)


class TestChainCheck(unittest.TestCase):
    def test_a_check_inside_tolerance_passes(self):
        self.assertEqual(chain_check_status(True, 1.0, 3.0), CHECK_PASSED)

    def test_a_check_landing_on_the_tolerance_passes(self):
        self.assertEqual(chain_check_status(True, 0.1 + 0.2, 0.3), CHECK_PASSED)

    def test_a_check_beyond_tolerance_is_out_of_tolerance(self):
        self.assertEqual(chain_check_status(True, 7.5, 3.0), CHECK_OUT_OF_TOLERANCE)

    def test_a_check_not_run_is_omitted_whatever_the_stored_error(self):
        self.assertEqual(chain_check_status(False, 7.5, 3.0), CHECK_OMITTED)

    def test_non_boolean_performed_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            chain_check_status(1, 1.0, 3.0)


class TestTriggerLevel(unittest.TestCase):
    def test_a_usable_trigger_has_no_finding(self):
        self.assertEqual(trigger_findings(2.0, 0.1, 12.0), [])

    def test_a_trigger_landing_on_the_noise_margin_has_no_finding(self):
        self.assertEqual(trigger_findings(3.0 * 0.1, 0.1, 12.0), [])

    def test_a_trigger_inside_the_noise_is_reported(self):
        self.assertEqual(len(trigger_findings(0.2, 0.1, 12.0)), 1)

    def test_a_trigger_above_the_usable_fraction_of_the_peak_is_reported(self):
        self.assertEqual(len(trigger_findings(11.0, 0.1, 12.0)), 1)

    def test_an_impossible_peak_fraction_is_rejected(self):
        with self.assertRaises(ValueError):
            trigger_findings(2.0, 0.1, 12.0, 3.0, 1.5)


class TestCaptureWindow(unittest.TestCase):
    def test_an_adequate_window_has_no_finding(self):
        self.assertEqual(capture_window_findings(0.006, 0.06, 0.05), [])

    def test_a_record_landing_exactly_on_the_need_has_no_finding(self):
        self.assertEqual(capture_window_findings(0.01, 0.01 + 0.05, 0.05), [])

    def test_a_short_record_is_reported(self):
        findings = capture_window_findings(0.006, 0.02, 0.05)
        self.assertEqual(len(findings), 1)

    def test_no_pre_trigger_is_reported(self):
        findings = capture_window_findings(0.0, 0.06, 0.05)
        self.assertEqual(len(findings), 1)

    def test_negative_pre_trigger_is_rejected(self):
        with self.assertRaises(ValueError):
            capture_window_findings(-0.001, 0.06, 0.05)


class TestSwitchingSequence(unittest.TestCase):
    def test_the_sequence_starts_with_stabilisation_and_is_contiguous(self):
        steps = build_switching_sequence(good_procedure())
        self.assertEqual(steps[0]["step"], "stabilise-unit")
        self.assertEqual([s["order"] for s in steps], list(range(1, len(steps) + 1)))

    def test_the_capture_is_armed_before_every_switch_on(self):
        steps = build_switching_sequence(good_procedure())
        names = [s["step"] for s in steps]
        for index, name in enumerate(names):
            if name == "switch-on":
                self.assertEqual(names[index - 1], "arm-capture")

    def test_skipping_the_chain_check_drops_its_step(self):
        with_check = build_switching_sequence(good_procedure())
        without = build_switching_sequence(
            good_procedure(chain_check_performed=False)
        )
        self.assertEqual(len(with_check) - len(without), 1)

    def test_a_single_event_needs_no_recovery_step(self):
        steps = build_switching_sequence(good_procedure(switch_on_events=1))
        self.assertNotIn("recover-input-filter", [s["step"] for s in steps])

    def test_a_short_off_time_is_stretched_to_the_recovery_minimum(self):
        steps = build_switching_sequence(good_procedure(off_time_s=0.01))
        recovery = [s for s in steps if s["step"] == "recover-input-filter"]
        self.assertAlmostEqual(recovery[0]["duration_s"], 0.1, places=9)

    def test_sequence_duration_sums_the_steps(self):
        steps = build_switching_sequence(good_procedure())
        self.assertAlmostEqual(sequence_duration_s(steps), 601.18, places=6)

    def test_sequence_duration_rejects_a_malformed_step(self):
        with self.assertRaises(ValueError):
            sequence_duration_s([{"step": "stabilise-unit"}])


class TestProcedureAssessment(unittest.TestCase):
    def test_a_good_procedure_is_compliant(self):
        report = assess_inrush_procedure(good_procedure())
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], VERDICT_COMPLIANT)
        self.assertEqual(report["chain_check_status"], CHECK_PASSED)

    def test_arming_after_the_command_is_a_finding(self):
        report = assess_inrush_procedure(
            good_procedure(capture_armed_before_switching=False)
        )
        self.assertEqual(report["verdict"], VERDICT_DEFICIENT)
        self.assertEqual(len(report["findings"]), 1)

    def test_a_short_dwell_is_a_finding(self):
        report = assess_inrush_procedure(good_procedure(stabilisation_dwell_s=10.0))
        self.assertFalse(report["stabilisation_is_complete"])
        self.assertEqual(report["verdict"], VERDICT_DEFICIENT)

    def test_a_short_off_time_is_a_finding(self):
        report = assess_inrush_procedure(good_procedure(off_time_s=0.01))
        self.assertFalse(report["recovery_is_sufficient"])
        self.assertAlmostEqual(report["min_recovery_time_s"], 0.1, places=9)

    def test_too_few_repeats_is_a_finding(self):
        report = assess_inrush_procedure(good_procedure(switch_on_events=2))
        self.assertEqual(report["verdict"], VERDICT_DEFICIENT)
        self.assertEqual(len(report["findings"]), 1)

    def test_an_out_of_tolerance_chain_check_is_a_finding(self):
        report = assess_inrush_procedure(good_procedure(chain_check_error_pct=9.0))
        self.assertEqual(report["chain_check_status"], CHECK_OUT_OF_TOLERANCE)
        self.assertEqual(report["verdict"], VERDICT_DEFICIENT)

    def test_an_omitted_chain_check_is_a_limitation_not_a_finding(self):
        report = assess_inrush_procedure(
            good_procedure(chain_check_performed=False)
        )
        self.assertEqual(report["chain_check_status"], CHECK_OMITTED)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], VERDICT_COMPLIANT)
        self.assertEqual(len(report["limitations"]), 1)

    def test_a_lenient_discharge_rule_leaves_residual_charge_as_a_limitation(self):
        report = assess_inrush_procedure(
            good_procedure(off_time_s=3.0 * TAU_S), discharge_constants=3.0
        )
        self.assertTrue(report["recovery_is_sufficient"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(len(report["limitations"]), 1)

    def test_the_report_carries_the_step_plan(self):
        report = assess_inrush_procedure(good_procedure())
        self.assertEqual(report["steps"][0]["step"], "stabilise-unit")
        self.assertGreater(len(report["steps"]), 10)

    def test_assessment_propagates_a_procedure_error(self):
        with self.assertRaises(ValueError):
            assess_inrush_procedure(good_procedure(record_length_s=0.0))


if __name__ == "__main__":
    unittest.main()
