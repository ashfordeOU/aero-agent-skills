#!/usr/bin/env python3
"""Gate 3 contract test for e2007-magnetic-moment-test-sequence.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_magnetic_moment_test_sequence.py
"""

import unittest

from e2007_magnetic_moment_test_sequence_logic import (
    ACTION_DEPERM,
    ACTION_MAGNETIZE,
    SEMI_AXES,
    SEQUENCE_CONFORMING,
    SEQUENCE_DEFICIENT,
    STATE_AS_RECEIVED,
    STATE_DEPERMED,
    STATE_MAGNETIZED,
    assess_magnetic_moment_test_sequence,
    block_contiguity_findings,
    conditioning_order_findings,
    measurement_count,
    measurements_in_state,
    missing_semi_axes,
    normalize_action,
    normalize_semi_axis,
    normalize_state,
    repeated_measurements,
    sequence_duration_s,
    state_placement_findings,
    validate_sequence,
)

DWELL_S = 60.0
DEPERM_S = 600.0
MAGNETIZE_S = 300.0


def block(state, axes=SEMI_AXES):
    return [{"action": "measure", "semi_axis": a, "state": state} for a in axes]


def good_sequence():
    steps = list(block(STATE_AS_RECEIVED))
    steps.append({"action": ACTION_DEPERM})
    steps.extend(block(STATE_DEPERMED))
    steps.append({"action": ACTION_MAGNETIZE})
    steps.extend(block(STATE_MAGNETIZED))
    return steps


class TestTokenNormalization(unittest.TestCase):
    def test_semi_axis_is_case_and_space_normalized(self):
        self.assertEqual(normalize_semi_axis(" +X "), "+x")

    def test_all_six_semi_axes_are_recognized(self):
        self.assertEqual(
            [normalize_semi_axis(a.upper()) for a in SEMI_AXES], list(SEMI_AXES)
        )

    def test_an_unsigned_axis_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_semi_axis("x")

    def test_a_non_string_semi_axis_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_semi_axis(3)

    def test_state_is_case_normalized(self):
        self.assertEqual(normalize_state("As-Received"), STATE_AS_RECEIVED)

    def test_an_unknown_state_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_state("half-depermed")

    def test_action_is_case_normalized(self):
        self.assertEqual(normalize_action("DePerm"), ACTION_DEPERM)

    def test_an_unknown_action_is_rejected(self):
        with self.assertRaises(ValueError):
            normalize_action("shake")


class TestSequenceValidation(unittest.TestCase):
    def test_a_good_sequence_normalizes_to_eighteen_measures(self):
        steps = validate_sequence(good_sequence())
        self.assertEqual(measurement_count(steps), 18)

    def test_step_indices_are_assigned_in_order(self):
        steps = validate_sequence(good_sequence())
        self.assertEqual([s["index"] for s in steps][:3], [0, 1, 2])

    def test_an_empty_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence([])

    def test_a_non_list_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence({"action": ACTION_DEPERM})

    def test_a_measure_step_without_a_semi_axis_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence([{"action": "measure", "state": STATE_AS_RECEIVED}])

    def test_a_conditioning_step_carrying_a_state_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence(
                [{"action": ACTION_DEPERM, "state": STATE_DEPERMED}]
            )

    def test_a_step_that_is_not_a_mapping_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_sequence(["deperm"])


class TestCoverage(unittest.TestCase):
    def test_each_state_measures_all_six_semi_axes(self):
        steps = validate_sequence(good_sequence())
        for state in (STATE_AS_RECEIVED, STATE_DEPERMED, STATE_MAGNETIZED):
            self.assertEqual(missing_semi_axes(steps, state), [])

    def test_measurement_order_within_a_state_is_preserved(self):
        steps = validate_sequence(good_sequence())
        self.assertEqual(measurements_in_state(steps, STATE_DEPERMED), list(SEMI_AXES))

    def test_a_dropped_semi_axis_is_reported(self):
        raw = list(block(STATE_AS_RECEIVED, SEMI_AXES[:5]))
        raw.append({"action": ACTION_DEPERM})
        raw.extend(block(STATE_DEPERMED))
        raw.append({"action": ACTION_MAGNETIZE})
        raw.extend(block(STATE_MAGNETIZED))
        steps = validate_sequence(raw)
        self.assertEqual(missing_semi_axes(steps, STATE_AS_RECEIVED), ["-z"])

    def test_a_doubled_semi_axis_is_reported(self):
        raw = list(block(STATE_AS_RECEIVED)) + block(STATE_AS_RECEIVED, ("+x",))
        raw.append({"action": ACTION_DEPERM})
        steps = validate_sequence(raw)
        self.assertEqual(repeated_measurements(steps, STATE_AS_RECEIVED), ["+x"])

    def test_a_complete_block_has_no_repeats(self):
        steps = validate_sequence(good_sequence())
        self.assertEqual(repeated_measurements(steps, STATE_MAGNETIZED), [])


class TestConditioningOrder(unittest.TestCase):
    def test_a_good_sequence_has_no_conditioning_finding(self):
        steps = validate_sequence(good_sequence())
        self.assertEqual(conditioning_order_findings(steps), [])

    def test_a_missing_deperm_step_is_reported(self):
        raw = [s for s in good_sequence() if s.get("action") != ACTION_DEPERM]
        steps = validate_sequence(raw)
        findings = conditioning_order_findings(steps)
        self.assertTrue(any("never runs a deperm" in f for f in findings))

    def test_a_doubled_magnetize_step_is_reported(self):
        raw = good_sequence()
        raw.append({"action": ACTION_MAGNETIZE})
        steps = validate_sequence(raw)
        findings = conditioning_order_findings(steps)
        self.assertTrue(any("2 magnetize steps" in f for f in findings))

    def test_magnetizing_before_deperming_is_reported(self):
        raw = list(block(STATE_AS_RECEIVED))
        raw.append({"action": ACTION_MAGNETIZE})
        raw.extend(block(STATE_MAGNETIZED))
        raw.append({"action": ACTION_DEPERM})
        raw.extend(block(STATE_DEPERMED))
        steps = validate_sequence(raw)
        findings = conditioning_order_findings(steps)
        self.assertEqual(len(findings), 1)
        self.assertIn("before the deperm step", findings[0])


class TestStatePlacement(unittest.TestCase):
    def test_a_good_sequence_has_no_placement_finding(self):
        steps = validate_sequence(good_sequence())
        self.assertEqual(state_placement_findings(steps), [])

    def test_a_depermed_reading_before_the_deperm_step_is_reported(self):
        raw = list(block(STATE_AS_RECEIVED))
        raw.extend(block(STATE_DEPERMED, ("+x",)))
        raw.append({"action": ACTION_DEPERM})
        raw.extend(block(STATE_DEPERMED, SEMI_AXES[1:]))
        steps = validate_sequence(raw)
        findings = state_placement_findings(steps)
        self.assertEqual(len(findings), 1)
        self.assertIn("before the deperm step", findings[0])

    def test_an_as_received_reading_after_conditioning_is_reported(self):
        raw = list(block(STATE_AS_RECEIVED))
        raw.append({"action": ACTION_DEPERM})
        raw.extend(block(STATE_AS_RECEIVED, ("+z",)))
        steps = validate_sequence(raw)
        findings = state_placement_findings(steps)
        self.assertTrue(any("no longer as received" in f for f in findings))

    def test_a_magnetized_reading_with_no_magnetize_step_is_reported(self):
        raw = list(block(STATE_AS_RECEIVED))
        raw.append({"action": ACTION_DEPERM})
        raw.extend(block(STATE_MAGNETIZED, ("+x",)))
        steps = validate_sequence(raw)
        findings = state_placement_findings(steps)
        self.assertEqual(len(findings), 1)


class TestBlockContiguity(unittest.TestCase):
    def test_a_good_sequence_has_contiguous_blocks(self):
        steps = validate_sequence(good_sequence())
        self.assertEqual(block_contiguity_findings(steps), [])

    def test_a_block_resumed_after_another_state_is_reported(self):
        raw = list(block(STATE_AS_RECEIVED))
        raw.append({"action": ACTION_DEPERM})
        raw.extend(block(STATE_DEPERMED, SEMI_AXES[:3]))
        raw.append({"action": ACTION_MAGNETIZE})
        raw.extend(block(STATE_MAGNETIZED))
        raw.extend(block(STATE_DEPERMED, SEMI_AXES[3:]))
        steps = validate_sequence(raw)
        findings = block_contiguity_findings(steps)
        self.assertEqual(len(findings), 1)
        self.assertIn("split into 2 runs", findings[0])


class TestDuration(unittest.TestCase):
    def test_duration_sums_dwell_and_both_conditioning_steps(self):
        steps = validate_sequence(good_sequence())
        self.assertAlmostEqual(
            sequence_duration_s(steps, DWELL_S, DEPERM_S, MAGNETIZE_S),
            1980.0,
            places=9,
        )

    def test_a_zero_dwell_is_rejected(self):
        steps = validate_sequence(good_sequence())
        with self.assertRaises(ValueError):
            sequence_duration_s(steps, 0.0, DEPERM_S, MAGNETIZE_S)

    def test_a_non_numeric_conditioning_time_is_rejected(self):
        steps = validate_sequence(good_sequence())
        with self.assertRaises(ValueError):
            sequence_duration_s(steps, DWELL_S, "ten minutes", MAGNETIZE_S)


class TestFullAssessment(unittest.TestCase):
    def test_a_good_sequence_conforms(self):
        report = assess_magnetic_moment_test_sequence(
            good_sequence(), DWELL_S, DEPERM_S, MAGNETIZE_S
        )
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], SEQUENCE_CONFORMING)
        self.assertEqual(report["measurement_count"], 18)

    def test_a_dropped_semi_axis_makes_the_sequence_deficient(self):
        raw = list(block(STATE_AS_RECEIVED, SEMI_AXES[:5]))
        raw.append({"action": ACTION_DEPERM})
        raw.extend(block(STATE_DEPERMED))
        raw.append({"action": ACTION_MAGNETIZE})
        raw.extend(block(STATE_MAGNETIZED))
        report = assess_magnetic_moment_test_sequence(raw)
        self.assertEqual(report["verdict"], SEQUENCE_DEFICIENT)
        self.assertTrue(any("never measures -z" in f for f in report["findings"]))

    def test_coverage_is_reported_per_state(self):
        report = assess_magnetic_moment_test_sequence(good_sequence())
        self.assertEqual(
            report["coverage"][STATE_DEPERMED]["measured"], list(SEMI_AXES)
        )

    def test_a_run_inside_the_slot_fits(self):
        report = assess_magnetic_moment_test_sequence(
            good_sequence(), DWELL_S, DEPERM_S, MAGNETIZE_S, available_time_s=7200.0
        )
        self.assertTrue(report["fits_available_time"])
        self.assertEqual(report["limitations"], [])

    def test_a_run_exactly_filling_the_slot_still_fits(self):
        report = assess_magnetic_moment_test_sequence(
            good_sequence(), DWELL_S, DEPERM_S, MAGNETIZE_S, available_time_s=1980.0
        )
        self.assertAlmostEqual(report["duration_s"], 1980.0, places=9)
        self.assertTrue(report["fits_available_time"])

    def test_a_run_past_the_slot_is_a_limitation_not_a_finding(self):
        report = assess_magnetic_moment_test_sequence(
            good_sequence(), DWELL_S, DEPERM_S, MAGNETIZE_S, available_time_s=600.0
        )
        self.assertFalse(report["fits_available_time"])
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], SEQUENCE_CONFORMING)

    def test_assessment_propagates_a_step_error(self):
        with self.assertRaises(ValueError):
            assess_magnetic_moment_test_sequence(
                [{"action": "measure", "semi_axis": "+q", "state": STATE_AS_RECEIVED}]
            )


if __name__ == "__main__":
    unittest.main()
