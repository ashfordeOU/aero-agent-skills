#!/usr/bin/env python3
"""Gate 3 contract test for e2007-low-frequency-conducted-emission-procedure.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_low_frequency_conducted_emission_procedure.py
"""

import unittest

from e2007_low_frequency_conducted_emission_procedure_logic import (
    DEFAULT_SYSTEM_CHECK_TOLERANCE_DB,
    DEFAULT_WARMUP_MINUTES,
    MANDATORY_STEPS,
    STEP_AMBIENT_CHECK,
    STEP_POST_CHECK,
    STEP_RECORDING,
    STEP_SYSTEM_CHECK,
    STEP_WARMUP,
    VERDICT_REJECTED,
    VERDICT_VALID,
    assess_procedure,
    at_least,
    at_most,
    maximum_step_hz,
    measured_points,
    minimum_dwell_s,
    normalize_step,
    scan_time_s,
    sequence_steps,
    system_check_error_db,
    validate_sweep_plan,
    warmup_headroom_minutes,
)


def good_plan(**over):
    record = {
        "band_low_hz": 30.0,
        "band_high_hz": 100.0e3,
        "bandwidth_hz": 100.0,
        "step_hz": 50.0,
        "dwell_s": 0.05,
    }
    record.update(over)
    return record


def good_check(**over):
    record = {"injected_dbuv": 80.0, "read_back_dbuv": 79.0}
    record.update(over)
    return record


def all_steps():
    return list(MANDATORY_STEPS)


class TestStepNormalization(unittest.TestCase):
    def test_every_mandatory_step_normalizes(self):
        for step in MANDATORY_STEPS:
            self.assertEqual(normalize_step(step.upper()), step)

    def test_surrounding_whitespace_is_ignored(self):
        self.assertEqual(normalize_step("  recording "), STEP_RECORDING)

    def test_unrecognized_step_rejected(self):
        with self.assertRaises(ValueError):
            normalize_step("coffee-break")

    def test_non_string_step_rejected(self):
        with self.assertRaises(ValueError):
            normalize_step(2)


class TestSequencing(unittest.TestCase):
    def test_full_sequence_is_complete_and_ordered(self):
        report = sequence_steps(all_steps())
        self.assertEqual(report["missing"], [])
        self.assertFalse(report["out_of_order"])

    def test_missing_system_check_is_reported(self):
        steps = [s for s in MANDATORY_STEPS if s != STEP_SYSTEM_CHECK]
        report = sequence_steps(steps)
        self.assertEqual(report["missing"], [STEP_SYSTEM_CHECK])
        self.assertFalse(report["out_of_order"])

    def test_recording_before_the_system_check_is_out_of_order(self):
        steps = [
            STEP_WARMUP,
            STEP_RECORDING,
            STEP_SYSTEM_CHECK,
            STEP_AMBIENT_CHECK,
            STEP_POST_CHECK,
        ]
        report = sequence_steps(steps)
        self.assertTrue(report["out_of_order"])

    def test_repeated_step_rejected(self):
        with self.assertRaises(ValueError):
            sequence_steps([STEP_WARMUP, STEP_WARMUP])

    def test_empty_step_list_rejected(self):
        with self.assertRaises(ValueError):
            sequence_steps([])

    def test_non_list_steps_rejected(self):
        with self.assertRaises(ValueError):
            sequence_steps(STEP_WARMUP)


class TestWarmup(unittest.TestCase):
    def test_headroom_is_elapsed_minus_required(self):
        self.assertAlmostEqual(warmup_headroom_minutes(45.0), 15.0, places=9)

    def test_exact_soak_leaves_no_headroom(self):
        self.assertAlmostEqual(
            warmup_headroom_minutes(DEFAULT_WARMUP_MINUTES), 0.0, places=9
        )

    def test_short_soak_is_negative(self):
        self.assertAlmostEqual(warmup_headroom_minutes(20.0), -10.0, places=9)

    def test_negative_elapsed_rejected(self):
        with self.assertRaises(ValueError):
            warmup_headroom_minutes(-1.0)

    def test_zero_requirement_rejected(self):
        with self.assertRaises(ValueError):
            warmup_headroom_minutes(30.0, required_minutes=0.0)


class TestSystemCheck(unittest.TestCase):
    def test_error_is_the_magnitude_of_the_read_back_difference(self):
        self.assertAlmostEqual(system_check_error_db(80.0, 77.5), 2.5, places=9)

    def test_error_is_symmetric(self):
        self.assertAlmostEqual(
            system_check_error_db(80.0, 82.5),
            system_check_error_db(80.0, 77.5),
            places=9,
        )

    def test_perfect_read_back_is_zero_error(self):
        self.assertAlmostEqual(system_check_error_db(80.0, 80.0), 0.0, places=9)

    def test_non_numeric_level_rejected(self):
        with self.assertRaises(ValueError):
            system_check_error_db("eighty", 80.0)

    def test_at_most_absorbs_float_error_only(self):
        self.assertTrue(at_most(3.0, 3.0))
        self.assertFalse(at_most(4.0, 3.0))

    def test_at_least_absorbs_float_error_only(self):
        self.assertTrue(at_least(3.0, 3.0))
        self.assertFalse(at_least(2.0, 3.0))


class TestSweepArithmetic(unittest.TestCase):
    def test_step_ceiling_is_half_the_bandwidth(self):
        self.assertAlmostEqual(maximum_step_hz(100.0), 50.0, places=9)

    def test_step_fraction_of_one_is_allowed(self):
        self.assertAlmostEqual(maximum_step_hz(100.0, fraction=1.0), 100.0, places=9)

    def test_zero_bandwidth_rejected_for_the_step_ceiling(self):
        with self.assertRaises(ValueError):
            maximum_step_hz(0.0)

    def test_step_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            maximum_step_hz(100.0, fraction=1.5)

    def test_dwell_floor_is_the_reciprocal_bandwidth(self):
        self.assertAlmostEqual(minimum_dwell_s(100.0), 0.01, places=9)

    def test_zero_bandwidth_rejected_for_the_dwell_floor(self):
        with self.assertRaises(ValueError):
            minimum_dwell_s(0.0)

    def test_point_count_includes_both_edges(self):
        self.assertEqual(measured_points((100.0, 200.0), 10.0), 11)

    def test_point_count_of_a_single_step_band(self):
        self.assertEqual(measured_points((100.0, 110.0), 10.0), 2)

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            measured_points((200.0, 100.0), 10.0)

    def test_zero_step_rejected(self):
        with self.assertRaises(ValueError):
            measured_points((100.0, 200.0), 0.0)

    def test_scan_time_is_points_times_dwell(self):
        self.assertAlmostEqual(scan_time_s((100.0, 200.0), 10.0, 0.5), 5.5, places=9)

    def test_zero_dwell_rejected_for_the_scan_time(self):
        with self.assertRaises(ValueError):
            scan_time_s((100.0, 200.0), 10.0, 0.0)


class TestSweepPlan(unittest.TestCase):
    def test_good_plan_passes_both_checks(self):
        plan = validate_sweep_plan(good_plan())
        self.assertTrue(plan["step_ok"])
        self.assertTrue(plan["dwell_ok"])

    def test_step_exactly_on_the_ceiling_is_accepted(self):
        plan = validate_sweep_plan(good_plan(bandwidth_hz=100.0, step_hz=50.0))
        self.assertAlmostEqual(plan["step_ceiling_hz"], 50.0, places=9)
        self.assertTrue(plan["step_ok"])

    def test_step_wider_than_the_ceiling_is_flagged(self):
        plan = validate_sweep_plan(good_plan(step_hz=400.0))
        self.assertFalse(plan["step_ok"])

    def test_dwell_exactly_on_the_floor_is_accepted(self):
        plan = validate_sweep_plan(good_plan(dwell_s=0.01))
        self.assertAlmostEqual(plan["dwell_floor_s"], 0.01, places=9)
        self.assertTrue(plan["dwell_ok"])

    def test_dwell_below_the_floor_is_flagged(self):
        plan = validate_sweep_plan(good_plan(dwell_s=0.0005))
        self.assertFalse(plan["dwell_ok"])

    def test_scan_time_follows_from_the_plan(self):
        plan = validate_sweep_plan(good_plan())
        self.assertEqual(plan["points"], 2000)
        self.assertAlmostEqual(plan["scan_time_s"], 100.0, places=9)

    def test_inverted_plan_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep_plan(good_plan(band_high_hz=10.0))

    def test_zero_plan_bandwidth_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep_plan(good_plan(bandwidth_hz=0.0))

    def test_non_mapping_plan_rejected(self):
        with self.assertRaises(ValueError):
            validate_sweep_plan([30.0, 100.0e3])


class TestAssessment(unittest.TestCase):
    def test_clean_run_is_valid(self):
        report = assess_procedure(all_steps(), 45.0, good_check(), good_plan())
        self.assertEqual(report["verdict"], VERDICT_VALID)
        self.assertEqual(report["findings"], [])

    def test_missing_step_rejects_the_run(self):
        steps = [s for s in MANDATORY_STEPS if s != STEP_AMBIENT_CHECK]
        report = assess_procedure(steps, 45.0, good_check(), good_plan())
        self.assertEqual(report["verdict"], VERDICT_REJECTED)
        self.assertTrue(
            any("mandatory step not executed" in f for f in report["findings"])
        )

    def test_swapped_steps_reject_the_run(self):
        steps = [
            STEP_WARMUP,
            STEP_RECORDING,
            STEP_SYSTEM_CHECK,
            STEP_AMBIENT_CHECK,
            STEP_POST_CHECK,
        ]
        report = assess_procedure(steps, 45.0, good_check(), good_plan())
        self.assertTrue(any("out of order" in f for f in report["findings"]))

    def test_short_warm_up_rejects_the_run(self):
        report = assess_procedure(all_steps(), 10.0, good_check(), good_plan())
        self.assertEqual(report["verdict"], VERDICT_REJECTED)
        self.assertTrue(any("warm-up short" in f for f in report["findings"]))

    def test_bare_warm_up_margin_is_a_limitation(self):
        report = assess_procedure(all_steps(), 31.0, good_check(), good_plan())
        self.assertEqual(report["verdict"], VERDICT_VALID)
        self.assertTrue(any("margin" in l for l in report["limitations"]))

    def test_system_check_error_past_tolerance_rejects_the_run(self):
        report = assess_procedure(
            all_steps(), 45.0, good_check(read_back_dbuv=70.0), good_plan()
        )
        self.assertTrue(any("system check read back" in f for f in report["findings"]))

    def test_system_check_error_on_the_tolerance_is_accepted(self):
        report = assess_procedure(
            all_steps(),
            45.0,
            good_check(read_back_dbuv=80.0 - DEFAULT_SYSTEM_CHECK_TOLERANCE_DB),
            good_plan(),
        )
        self.assertAlmostEqual(
            report["system_check_error_db"],
            DEFAULT_SYSTEM_CHECK_TOLERANCE_DB,
            places=9,
        )
        self.assertEqual(report["verdict"], VERDICT_VALID)

    def test_coarse_step_rejects_the_run(self):
        report = assess_procedure(
            all_steps(), 45.0, good_check(), good_plan(step_hz=2000.0)
        )
        self.assertTrue(any("tuning step" in f for f in report["findings"]))

    def test_short_dwell_rejects_the_run(self):
        report = assess_procedure(
            all_steps(), 45.0, good_check(), good_plan(dwell_s=0.0002)
        )
        self.assertTrue(any("dwell" in f for f in report["findings"]))

    def test_scan_time_beyond_the_slot_rejects_the_run(self):
        report = assess_procedure(
            all_steps(), 45.0, good_check(), good_plan(), allowed_scan_time_s=10.0
        )
        self.assertTrue(any("scan needs" in f for f in report["findings"]))

    def test_scan_time_inside_the_slot_is_accepted(self):
        report = assess_procedure(
            all_steps(), 45.0, good_check(), good_plan(), allowed_scan_time_s=600.0
        )
        self.assertEqual(report["verdict"], VERDICT_VALID)

    def test_zero_allowed_scan_time_rejected(self):
        with self.assertRaises(ValueError):
            assess_procedure(
                all_steps(), 45.0, good_check(), good_plan(), allowed_scan_time_s=0.0
            )

    def test_zero_system_check_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            assess_procedure(
                all_steps(),
                45.0,
                good_check(),
                good_plan(),
                system_check_tolerance_db=0.0,
            )

    def test_non_mapping_system_check_rejected(self):
        with self.assertRaises(ValueError):
            assess_procedure(all_steps(), 45.0, ["80 dBuV"], good_plan())

    def test_report_carries_the_sequence_and_the_plan(self):
        report = assess_procedure(all_steps(), 45.0, good_check(), good_plan())
        self.assertEqual(report["sequence"]["executed"], list(MANDATORY_STEPS))
        self.assertEqual(report["sweep_plan"]["points"], 2000)


if __name__ == "__main__":
    unittest.main()
