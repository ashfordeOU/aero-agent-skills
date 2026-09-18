#!/usr/bin/env python3
"""Gate 3 contract test for e2007-radiated-magnetic-susceptibility-procedure.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_radiated_magnetic_susceptibility_procedure.py
"""

import math
import unittest

from e2007_radiated_magnetic_susceptibility_procedure_logic import (
    DEFAULT_BAND_HZ,
    DEFAULT_DWELL_CYCLES,
    DEFAULT_STEP_FRACTION,
    DEFAULT_THRESHOLD_STEP_DB,
    DEFAULT_VERIFICATION_TOLERANCE_DB,
    DEFAULT_WARM_UP_MINUTES,
    ORDERED_STEPS,
    VERDICT_INVALID,
    VERDICT_VALID,
    assess_procedure,
    dwell_floor_s,
    frequency_step_count,
    normalize_step,
    sequence_report,
    susceptibility_margin_db,
    sweep_time_s,
    threshold_reduction_steps,
    validate_band,
    verification_error_db,
    warm_up_report,
)


def run_kwargs(**over):
    kwargs = {
        "steps": list(ORDERED_STEPS),
        "soak_minutes": 45.0,
        "measured_flux_t": 1.0e-6,
        "reference_flux_t": 1.0e-6,
        "planned_dwell_s": 1.0,
        "monitor_response_s": 0.2,
    }
    kwargs.update(over)
    return kwargs


class TestStepNormalization(unittest.TestCase):
    def test_every_ordered_step_normalizes(self):
        for step in ORDERED_STEPS:
            self.assertEqual(normalize_step(step.upper()), step)

    def test_surrounding_whitespace_is_ignored(self):
        self.assertEqual(normalize_step("  threshold-search "), "threshold-search")

    def test_unrecognized_step_rejected(self):
        with self.assertRaises(ValueError):
            normalize_step("coffee-break")

    def test_non_string_step_rejected(self):
        with self.assertRaises(ValueError):
            normalize_step(3)


class TestSequence(unittest.TestCase):
    def test_the_full_sequence_is_complete_and_ordered(self):
        report = sequence_report(list(ORDERED_STEPS))
        self.assertEqual(report["missing"], [])
        self.assertTrue(report["in_order"])

    def test_a_skipped_step_is_listed(self):
        report = sequence_report([s for s in ORDERED_STEPS if s != "system-verification"])
        self.assertEqual(report["missing"], ["system-verification"])

    def test_an_inversion_is_detected_and_named(self):
        steps = list(ORDERED_STEPS)
        steps.remove("system-verification")
        steps.append("system-verification")
        report = sequence_report(steps)
        self.assertFalse(report["in_order"])
        self.assertTrue(len(report["inversions"]) >= 1)

    def test_a_repeated_step_rejected(self):
        with self.assertRaises(ValueError):
            sequence_report(["instrument-warm-up", "instrument-warm-up"])

    def test_an_empty_step_list_rejected(self):
        with self.assertRaises(ValueError):
            sequence_report([])

    def test_a_partial_but_ordered_run_keeps_its_order(self):
        report = sequence_report(["instrument-warm-up", "stepped-exposure-sweep"])
        self.assertTrue(report["in_order"])
        self.assertEqual(len(report["missing"]), len(ORDERED_STEPS) - 2)


class TestWarmUp(unittest.TestCase):
    def test_a_generous_soak_is_satisfied(self):
        report = warm_up_report(60.0)
        self.assertTrue(report["satisfied"])
        self.assertAlmostEqual(
            report["headroom_minutes"], 60.0 - DEFAULT_WARM_UP_MINUTES, places=9
        )

    def test_a_soak_exactly_at_the_requirement_is_satisfied(self):
        report = warm_up_report(DEFAULT_WARM_UP_MINUTES)
        self.assertTrue(report["satisfied"])
        self.assertAlmostEqual(report["headroom_minutes"], 0.0, places=9)

    def test_a_short_soak_is_not_satisfied(self):
        report = warm_up_report(5.0)
        self.assertFalse(report["satisfied"])

    def test_a_negative_soak_rejected(self):
        with self.assertRaises(ValueError):
            warm_up_report(-1.0)

    def test_a_zero_requirement_rejected(self):
        with self.assertRaises(ValueError):
            warm_up_report(30.0, required_minutes=0.0)


class TestVerificationError(unittest.TestCase):
    def test_an_exact_read_back_has_no_error(self):
        self.assertAlmostEqual(verification_error_db(1.0e-6, 1.0e-6), 0.0, places=12)

    def test_a_doubled_read_back_is_about_six_decibels(self):
        self.assertAlmostEqual(
            verification_error_db(2.0e-6, 1.0e-6), 6.02059991328, places=7
        )

    def test_reading_high_and_low_are_graded_alike(self):
        high = verification_error_db(2.0e-6, 1.0e-6)
        low = verification_error_db(1.0e-6, 2.0e-6)
        self.assertAlmostEqual(high, low, places=12)

    def test_a_zero_read_back_rejected(self):
        with self.assertRaises(ValueError):
            verification_error_db(0.0, 1.0e-6)

    def test_a_zero_reference_rejected(self):
        with self.assertRaises(ValueError):
            verification_error_db(1.0e-6, 0.0)


class TestSweepPlanning(unittest.TestCase):
    def test_default_band_validates(self):
        low, high = validate_band(DEFAULT_BAND_HZ)
        self.assertAlmostEqual(low, 30.0)
        self.assertAlmostEqual(high, 100.0e3)

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_band((1.0e5, 30.0))

    def test_a_band_spanning_exactly_one_step_gives_two_points(self):
        self.assertEqual(frequency_step_count((100.0, 105.0), 0.05), 2)

    def test_a_finer_step_needs_more_points(self):
        coarse = frequency_step_count(DEFAULT_BAND_HZ, 0.10)
        fine = frequency_step_count(DEFAULT_BAND_HZ, 0.01)
        self.assertGreater(fine, coarse * 5)

    def test_a_step_fraction_of_one_or_more_rejected(self):
        with self.assertRaises(ValueError):
            frequency_step_count(DEFAULT_BAND_HZ, 1.0)

    def test_a_zero_step_fraction_rejected(self):
        with self.assertRaises(ValueError):
            frequency_step_count(DEFAULT_BAND_HZ, 0.0)

    def test_the_dwell_floor_follows_the_cycle_count_at_the_band_bottom(self):
        floor = dwell_floor_s(30.0, 0.0)
        self.assertAlmostEqual(floor, DEFAULT_DWELL_CYCLES / 30.0, places=12)

    def test_a_slow_monitor_governs_the_dwell_floor(self):
        floor = dwell_floor_s(1.0e4, 2.0)
        self.assertAlmostEqual(floor, 2.0, places=12)

    def test_a_zero_dwell_frequency_rejected(self):
        with self.assertRaises(ValueError):
            dwell_floor_s(0.0, 0.2)

    def test_a_negative_monitor_response_rejected(self):
        with self.assertRaises(ValueError):
            dwell_floor_s(1.0e3, -0.2)

    def test_sweep_time_is_points_times_dwell(self):
        self.assertAlmostEqual(sweep_time_s(120, 0.5), 60.0, places=9)

    def test_a_fractional_point_count_rejected(self):
        with self.assertRaises(ValueError):
            sweep_time_s(120.5, 0.5)

    def test_a_zero_dwell_rejected(self):
        with self.assertRaises(ValueError):
            sweep_time_s(120, 0.0)


class TestThresholdSearch(unittest.TestCase):
    def test_no_reduction_is_needed_at_the_applied_level(self):
        self.assertEqual(threshold_reduction_steps(1.0e-6, 1.0e-6), 0)

    def test_a_halving_of_the_level_takes_four_two_decibel_steps(self):
        # A factor of two in flux density is 6.02 dB, which is three whole
        # 2 dB steps plus a remainder, so the search needs a fourth.
        steps = threshold_reduction_steps(
            2.0e-6, 1.0e-6, step_db=DEFAULT_THRESHOLD_STEP_DB
        )
        self.assertEqual(steps, 4)

    def test_an_exact_multiple_of_the_step_is_not_rounded_up(self):
        # 10**(6/20) is not exactly representable, so the derived drop can
        # land a unit in the last place either side of 6 dB. An exact three
        # steps must stay three steps on every platform.
        applied = 1.0e-6 * (10.0 ** (6.0 / 20.0))
        self.assertEqual(threshold_reduction_steps(applied, 1.0e-6, step_db=2.0), 3)

    def test_a_partial_step_is_rounded_up(self):
        steps = threshold_reduction_steps(1.0e-6, 0.5e-6, step_db=5.0)
        self.assertEqual(steps, 2)

    def test_a_threshold_above_the_applied_level_rejected(self):
        with self.assertRaises(ValueError):
            threshold_reduction_steps(1.0e-6, 2.0e-6)

    def test_a_zero_step_size_rejected(self):
        with self.assertRaises(ValueError):
            threshold_reduction_steps(2.0e-6, 1.0e-6, step_db=0.0)

    def test_margin_is_zero_at_the_required_level(self):
        self.assertAlmostEqual(
            susceptibility_margin_db(1.0e-6, 1.0e-6), 0.0, places=12
        )

    def test_margin_is_positive_above_the_required_level(self):
        self.assertAlmostEqual(
            susceptibility_margin_db(2.0e-6, 1.0e-6), 6.02059991328, places=7
        )

    def test_margin_is_negative_below_the_required_level(self):
        self.assertAlmostEqual(
            susceptibility_margin_db(0.5e-6, 1.0e-6), -6.02059991328, places=7
        )

    def test_a_zero_required_level_rejected(self):
        with self.assertRaises(ValueError):
            susceptibility_margin_db(1.0e-6, 0.0)


class TestAssessment(unittest.TestCase):
    def test_a_clean_run_is_valid(self):
        report = assess_procedure(**run_kwargs())
        self.assertEqual(report["verdict"], VERDICT_VALID)
        self.assertEqual(report["findings"], [])

    def test_a_skipped_verification_is_a_finding(self):
        steps = [s for s in ORDERED_STEPS if s != "system-verification"]
        report = assess_procedure(**run_kwargs(steps=steps))
        self.assertEqual(report["verdict"], VERDICT_INVALID)
        self.assertTrue(any("never executed" in f for f in report["findings"]))

    def test_a_verification_after_the_sweep_is_a_finding(self):
        steps = list(ORDERED_STEPS)
        steps.remove("system-verification")
        steps.append("system-verification")
        report = assess_procedure(**run_kwargs(steps=steps))
        self.assertTrue(any("was executed before" in f for f in report["findings"]))

    def test_a_short_soak_is_a_finding(self):
        report = assess_procedure(**run_kwargs(soak_minutes=4.0))
        self.assertEqual(report["verdict"], VERDICT_INVALID)
        self.assertTrue(any("soaked" in f for f in report["findings"]))

    def test_a_thin_soak_headroom_is_a_limitation(self):
        report = assess_procedure(
            **run_kwargs(soak_minutes=DEFAULT_WARM_UP_MINUTES + 1.0)
        )
        self.assertEqual(report["verdict"], VERDICT_VALID)
        self.assertTrue(any("headroom" in n for n in report["limitations"]))

    def test_a_read_back_outside_the_tolerance_is_a_finding(self):
        report = assess_procedure(**run_kwargs(measured_flux_t=4.0e-6))
        self.assertTrue(any("read-back is" in f for f in report["findings"]))

    def test_a_read_back_exactly_at_the_tolerance_is_accepted(self):
        edge = 1.0e-6 * (10.0 ** (DEFAULT_VERIFICATION_TOLERANCE_DB / 20.0))
        report = assess_procedure(**run_kwargs(measured_flux_t=edge))
        self.assertAlmostEqual(
            report["verification_error_db"],
            DEFAULT_VERIFICATION_TOLERANCE_DB,
            places=9,
        )
        self.assertFalse(any("read-back is" in f and "out against" in f
                             for f in report["findings"]))

    def test_a_dwell_under_the_floor_is_a_finding(self):
        report = assess_procedure(**run_kwargs(planned_dwell_s=0.01))
        self.assertTrue(any("under the" in f for f in report["findings"]))

    def test_a_dwell_exactly_at_the_floor_is_accepted(self):
        floor = dwell_floor_s(DEFAULT_BAND_HZ[0], 0.2)
        report = assess_procedure(**run_kwargs(planned_dwell_s=floor))
        self.assertFalse(any("under the" in f for f in report["findings"]))

    def test_a_sweep_longer_than_the_slot_is_a_finding(self):
        report = assess_procedure(**run_kwargs(allowed_sweep_time_s=10.0))
        self.assertTrue(any("the run is allowed" in f for f in report["findings"]))

    def test_a_sweep_nearly_filling_the_slot_is_a_limitation(self):
        baseline = assess_procedure(**run_kwargs())
        report = assess_procedure(
            **run_kwargs(allowed_sweep_time_s=baseline["sweep_time_s"] * 1.01)
        )
        self.assertEqual(report["verdict"], VERDICT_VALID)
        self.assertTrue(any("of the" in n for n in report["limitations"]))

    def test_the_tuned_point_count_matches_the_step_helper(self):
        report = assess_procedure(**run_kwargs())
        self.assertEqual(
            report["tuned_points"],
            frequency_step_count(DEFAULT_BAND_HZ, DEFAULT_STEP_FRACTION),
        )

    def test_a_reaction_below_the_required_level_is_a_finding(self):
        report = assess_procedure(
            **run_kwargs(
                measured_flux_t=4.0e-6,
                reference_flux_t=4.0e-6,
                threshold_flux_t=0.5e-6,
                required_flux_t=1.0e-6,
            )
        )
        self.assertTrue(any("reacts" in f for f in report["findings"]))

    def test_a_thin_reaction_margin_is_a_limitation(self):
        report = assess_procedure(
            **run_kwargs(
                measured_flux_t=4.0e-6,
                reference_flux_t=4.0e-6,
                threshold_flux_t=1.5e-6,
                required_flux_t=1.0e-6,
            )
        )
        self.assertTrue(any("only" in n for n in report["limitations"]))

    def test_the_threshold_search_depth_is_reported(self):
        report = assess_procedure(
            **run_kwargs(
                measured_flux_t=4.0e-6,
                reference_flux_t=4.0e-6,
                threshold_flux_t=2.0e-6,
                required_flux_t=1.0e-6,
            )
        )
        self.assertEqual(report["threshold"]["reduction_steps"], 4)

    def test_a_threshold_without_a_required_level_rejected(self):
        with self.assertRaises(ValueError):
            assess_procedure(**run_kwargs(threshold_flux_t=1.0e-6))

    def test_a_zero_verification_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            assess_procedure(**run_kwargs(verification_tolerance_db=0.0))

    def test_a_zero_planned_dwell_rejected(self):
        with self.assertRaises(ValueError):
            assess_procedure(**run_kwargs(planned_dwell_s=0.0))


if __name__ == "__main__":
    unittest.main()
