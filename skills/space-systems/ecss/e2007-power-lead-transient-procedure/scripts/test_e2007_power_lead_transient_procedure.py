#!/usr/bin/env python3
"""Gate 3 contract test for e2007-power-lead-transient-procedure.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_power_lead_transient_procedure.py
"""

import unittest

from e2007_power_lead_transient_procedure_logic import (
    DEFAULT_PULSES_PER_POLARITY,
    DEFAULT_STABILISATION_TOLERANCE_DB,
    DEFAULT_WARMUP_MINUTES,
    MANDATORY_STEPS,
    MODE_COMMON,
    MODE_DIFFERENTIAL,
    OUTCOME_INCONCLUSIVE,
    OUTCOME_SUSCEPTIBLE,
    OUTCOME_TOLERANT,
    POLARITY_NEGATIVE,
    POLARITY_POSITIVE,
    STEP_COMMON_APPLICATION,
    STEP_DIFFERENTIAL_APPLICATION,
    STEP_POST_STABILISATION,
    STEP_PRE_STABILISATION,
    STEP_WARMUP,
    VERDICT_REJECTED,
    VERDICT_VALID,
    assess_transient_procedure,
    at_least,
    at_most,
    categorize_outcome,
    grade_application,
    instrument_is_stable,
    normalize_mode,
    normalize_polarity,
    normalize_step,
    sequence_steps,
    stabilisation_drift_db,
    total_application_time_s,
    warmup_headroom_minutes,
)


def good_application(mode=MODE_DIFFERENTIAL, **over):
    record = {
        "mode": mode,
        "pulses": {POLARITY_POSITIVE: 10, POLARITY_NEGATIVE: 10},
        "pulse_width_us": 10.0,
        "recovery_interval_s": 1.0,
    }
    record.update(over)
    return record


def good_run(**over):
    record = {
        "steps": list(MANDATORY_STEPS),
        "warmup_minutes": 45.0,
        "pre_reading_dbuv": 80.0,
        "post_reading_dbuv": 80.2,
        "applications": [
            good_application(MODE_DIFFERENTIAL),
            good_application(MODE_COMMON),
        ],
        "unit_upset": False,
    }
    record.update(over)
    return record


class TestNormalization(unittest.TestCase):
    def test_every_mandatory_step_normalizes(self):
        for step in MANDATORY_STEPS:
            self.assertEqual(normalize_step(step.upper()), step)

    def test_surrounding_whitespace_is_ignored(self):
        self.assertEqual(normalize_step("  warm-up "), STEP_WARMUP)

    def test_unrecognized_step_rejected(self):
        with self.assertRaises(ValueError):
            normalize_step("coffee-break")

    def test_non_string_step_rejected(self):
        with self.assertRaises(ValueError):
            normalize_step(7)

    def test_both_modes_normalize(self):
        self.assertEqual(normalize_mode("Differential-Mode"), MODE_DIFFERENTIAL)
        self.assertEqual(normalize_mode(" common-mode"), MODE_COMMON)

    def test_unrecognized_mode_rejected(self):
        with self.assertRaises(ValueError):
            normalize_mode("radiated-mode")

    def test_both_polarities_normalize(self):
        self.assertEqual(normalize_polarity("Positive"), POLARITY_POSITIVE)
        self.assertEqual(normalize_polarity(" NEGATIVE "), POLARITY_NEGATIVE)

    def test_unrecognized_polarity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_polarity("alternating")


class TestSequencing(unittest.TestCase):
    def test_full_sequence_is_complete_and_ordered(self):
        report = sequence_steps(list(MANDATORY_STEPS))
        self.assertEqual(report["missing"], [])
        self.assertFalse(report["out_of_order"])
        self.assertTrue(report["complete"])

    def test_a_missing_pre_check_is_reported(self):
        steps = [s for s in MANDATORY_STEPS if s != STEP_PRE_STABILISATION]
        report = sequence_steps(steps)
        self.assertEqual(report["missing"], [STEP_PRE_STABILISATION])
        self.assertFalse(report["out_of_order"])

    def test_applying_pulses_before_the_pre_check_is_out_of_order(self):
        report = sequence_steps(
            [
                STEP_WARMUP,
                STEP_DIFFERENTIAL_APPLICATION,
                STEP_PRE_STABILISATION,
                STEP_COMMON_APPLICATION,
                STEP_POST_STABILISATION,
            ]
        )
        self.assertTrue(report["out_of_order"])
        self.assertFalse(report["complete"])

    def test_a_repeated_step_rejected(self):
        with self.assertRaises(ValueError):
            sequence_steps([STEP_WARMUP, STEP_WARMUP])

    def test_an_empty_step_list_rejected(self):
        with self.assertRaises(ValueError):
            sequence_steps([])

    def test_a_non_list_of_steps_rejected(self):
        with self.assertRaises(ValueError):
            sequence_steps(STEP_WARMUP)


class TestWarmup(unittest.TestCase):
    def test_headroom_is_elapsed_minus_required(self):
        self.assertAlmostEqual(warmup_headroom_minutes(45.0), 15.0, places=9)

    def test_an_exact_soak_leaves_no_headroom(self):
        self.assertAlmostEqual(
            warmup_headroom_minutes(DEFAULT_WARMUP_MINUTES), 0.0, places=9
        )

    def test_a_short_soak_is_negative(self):
        self.assertAlmostEqual(warmup_headroom_minutes(20.0), -10.0, places=9)

    def test_a_negative_soak_rejected(self):
        with self.assertRaises(ValueError):
            warmup_headroom_minutes(-1.0)

    def test_a_zero_requirement_rejected(self):
        with self.assertRaises(ValueError):
            warmup_headroom_minutes(30.0, required_minutes=0.0)


class TestStabilisationCheck(unittest.TestCase):
    def test_drift_is_the_magnitude_of_the_difference(self):
        self.assertAlmostEqual(stabilisation_drift_db(80.0, 77.5), 2.5, places=9)

    def test_drift_is_symmetric(self):
        self.assertAlmostEqual(
            stabilisation_drift_db(80.0, 82.5),
            stabilisation_drift_db(80.0, 77.5),
            places=9,
        )

    def test_an_identical_read_back_shows_no_drift(self):
        self.assertAlmostEqual(stabilisation_drift_db(80.0, 80.0), 0.0, places=9)

    def test_drift_inside_the_tolerance_is_stable(self):
        self.assertTrue(instrument_is_stable(80.0, 80.5))

    def test_drift_exactly_at_the_tolerance_is_stable(self):
        self.assertTrue(
            instrument_is_stable(
                80.0, 80.0 + DEFAULT_STABILISATION_TOLERANCE_DB
            )
        )

    def test_drift_beyond_the_tolerance_is_not_stable(self):
        self.assertFalse(instrument_is_stable(80.0, 85.0))

    def test_a_zero_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            instrument_is_stable(80.0, 80.0, tolerance_db=0.0)

    def test_a_non_numeric_reading_rejected(self):
        with self.assertRaises(ValueError):
            stabilisation_drift_db("eighty", 80.0)


class TestTolerantComparison(unittest.TestCase):
    def test_at_least_absorbs_float_error_only(self):
        self.assertTrue(at_least(3.0, 3.0))
        self.assertFalse(at_least(2.0, 3.0))

    def test_at_most_absorbs_float_error_only(self):
        self.assertTrue(at_most(3.0, 3.0))
        self.assertFalse(at_most(4.0, 3.0))


class TestApplicationTime(unittest.TestCase):
    def test_elapsed_time_counts_every_pulse_and_its_gap(self):
        self.assertAlmostEqual(
            total_application_time_s(20, 10.0, 1.0), 20.0002, places=9
        )

    def test_a_longer_gap_dominates_the_elapsed_time(self):
        self.assertAlmostEqual(
            total_application_time_s(10, 10.0, 5.0), 50.0001, places=9
        )

    def test_a_zero_pulse_count_rejected(self):
        with self.assertRaises(ValueError):
            total_application_time_s(0, 10.0, 1.0)

    def test_a_fractional_pulse_count_rejected(self):
        with self.assertRaises(ValueError):
            total_application_time_s(10.5, 10.0, 1.0)

    def test_a_zero_recovery_interval_rejected(self):
        with self.assertRaises(ValueError):
            total_application_time_s(10, 10.0, 0.0)

    def test_a_zero_pulse_width_rejected(self):
        with self.assertRaises(ValueError):
            total_application_time_s(10, 0.0, 1.0)


class TestApplicationGrading(unittest.TestCase):
    def test_a_nominal_application_conforms(self):
        report = grade_application(good_application())
        self.assertTrue(report["conforming"])
        self.assertEqual(report["missing_polarities"], [])
        self.assertEqual(report["applied_pulses"], 2 * DEFAULT_PULSES_PER_POLARITY)

    def test_one_polarity_only_names_the_missing_one(self):
        report = grade_application(
            good_application(pulses={POLARITY_POSITIVE: 10})
        )
        self.assertEqual(report["missing_polarities"], [POLARITY_NEGATIVE])
        self.assertFalse(report["conforming"])

    def test_too_few_pulses_is_a_short_polarity_not_a_missing_one(self):
        report = grade_application(
            good_application(pulses={POLARITY_POSITIVE: 10, POLARITY_NEGATIVE: 3})
        )
        self.assertEqual(report["missing_polarities"], [])
        self.assertEqual(report["short_polarities"], [POLARITY_NEGATIVE])

    def test_a_pulse_width_outside_the_window_is_caught(self):
        report = grade_application(good_application(pulse_width_us=60.0))
        self.assertFalse(report["width_in_window"])
        self.assertFalse(report["conforming"])

    def test_a_pulse_width_on_the_window_edge_is_accepted(self):
        report = grade_application(good_application(pulse_width_us=5.0))
        self.assertTrue(report["width_in_window"])

    def test_a_short_recovery_interval_is_caught(self):
        report = grade_application(good_application(recovery_interval_s=0.05))
        self.assertFalse(report["interval_sufficient"])

    def test_a_recovery_interval_exactly_at_the_floor_is_sufficient(self):
        report = grade_application(good_application(recovery_interval_s=1.0))
        self.assertTrue(report["interval_sufficient"])

    def test_a_repeated_polarity_key_rejected(self):
        with self.assertRaises(ValueError):
            grade_application(
                good_application(pulses={"positive": 10, "Positive ": 10})
            )

    def test_an_empty_pulse_mapping_rejected(self):
        with self.assertRaises(ValueError):
            grade_application(good_application(pulses={}))

    def test_a_non_mapping_pulse_record_rejected(self):
        with self.assertRaises(ValueError):
            grade_application(good_application(pulses=[10, 10]))

    def test_a_boolean_pulse_count_rejected(self):
        with self.assertRaises(ValueError):
            grade_application(good_application(pulses={POLARITY_POSITIVE: True}))

    def test_a_non_mapping_application_rejected(self):
        with self.assertRaises(ValueError):
            grade_application([MODE_DIFFERENTIAL])


class TestOutcomeGrouping(unittest.TestCase):
    def test_a_settled_instrument_and_a_quiet_unit_is_tolerant(self):
        self.assertEqual(categorize_outcome(False, True), OUTCOME_TOLERANT)

    def test_a_settled_instrument_and_an_upset_unit_is_susceptible(self):
        self.assertEqual(categorize_outcome(True, True), OUTCOME_SUSCEPTIBLE)

    def test_a_drifting_instrument_makes_an_upset_inconclusive(self):
        self.assertEqual(categorize_outcome(True, False), OUTCOME_INCONCLUSIVE)

    def test_a_drifting_instrument_makes_a_quiet_run_inconclusive_too(self):
        self.assertEqual(categorize_outcome(False, False), OUTCOME_INCONCLUSIVE)

    def test_a_non_boolean_upset_flag_rejected(self):
        with self.assertRaises(ValueError):
            categorize_outcome("yes", True)


class TestAssessment(unittest.TestCase):
    def test_a_good_run_is_valid(self):
        report = assess_transient_procedure(good_run())
        self.assertEqual(report["verdict"], VERDICT_VALID)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["outcome"], OUTCOME_TOLERANT)

    def test_a_run_without_the_common_mode_application_is_rejected(self):
        report = assess_transient_procedure(
            good_run(
                steps=[s for s in MANDATORY_STEPS if s != STEP_COMMON_APPLICATION],
                applications=[good_application(MODE_DIFFERENTIAL)],
            )
        )
        self.assertEqual(report["verdict"], VERDICT_REJECTED)
        self.assertTrue(
            any(MODE_COMMON in finding for finding in report["findings"])
        )

    def test_a_short_warmup_is_a_finding(self):
        report = assess_transient_procedure(good_run(warmup_minutes=5.0))
        self.assertEqual(report["verdict"], VERDICT_REJECTED)
        self.assertLess(report["warmup_headroom_minutes"], 0.0)

    def test_a_drifting_instrument_makes_the_run_inconclusive(self):
        report = assess_transient_procedure(
            good_run(post_reading_dbuv=86.0, unit_upset=True)
        )
        self.assertEqual(report["outcome"], OUTCOME_INCONCLUSIVE)
        self.assertEqual(report["verdict"], VERDICT_REJECTED)

    def test_a_short_polarity_is_a_limitation_not_a_finding(self):
        report = assess_transient_procedure(
            good_run(
                applications=[
                    good_application(
                        MODE_DIFFERENTIAL,
                        pulses={POLARITY_POSITIVE: 10, POLARITY_NEGATIVE: 4},
                    ),
                    good_application(MODE_COMMON),
                ]
            )
        )
        self.assertEqual(report["findings"], [])
        self.assertEqual(len(report["limitations"]), 1)
        self.assertEqual(report["verdict"], VERDICT_VALID)

    def test_a_mode_applied_twice_rejected(self):
        with self.assertRaises(ValueError):
            assess_transient_procedure(
                good_run(
                    applications=[
                        good_application(MODE_DIFFERENTIAL),
                        good_application(MODE_DIFFERENTIAL),
                    ]
                )
            )

    def test_an_empty_application_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_transient_procedure(good_run(applications=[]))

    def test_a_non_mapping_run_rejected(self):
        with self.assertRaises(ValueError):
            assess_transient_procedure([MODE_DIFFERENTIAL])

    def test_total_elapsed_time_sums_both_applications(self):
        report = assess_transient_procedure(good_run())
        self.assertAlmostEqual(report["total_elapsed_s"], 40.0004, places=9)

    def test_an_upset_on_a_settled_instrument_is_a_susceptibility(self):
        report = assess_transient_procedure(good_run(unit_upset=True))
        self.assertEqual(report["outcome"], OUTCOME_SUSCEPTIBLE)
        self.assertEqual(report["verdict"], VERDICT_VALID)


if __name__ == "__main__":
    unittest.main(verbosity=1)
