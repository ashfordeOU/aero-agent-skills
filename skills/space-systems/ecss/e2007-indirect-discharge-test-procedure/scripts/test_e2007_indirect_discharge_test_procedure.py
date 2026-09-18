#!/usr/bin/env python3
"""Gate 3 contract test for e2007-indirect-discharge-test-procedure.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_indirect_discharge_test_procedure.py
"""

import unittest

from e2007_indirect_discharge_test_procedure_logic import (
    BLEED_MULTIPLE,
    CALIBRATION_OMITTED,
    CALIBRATION_OUT_OF_TOLERANCE,
    CALIBRATION_PASSED,
    CALIBRATION_TOLERANCE_PCT,
    MINIMUM_DISCHARGES_PER_POINT,
    RISE_TIME_BAND_S,
    VERDICT_COMPLIANT,
    VERDICT_NONCOMPLIANT,
    VERDICT_WITH_LIMITATIONS,
    assess_indirect_discharge_procedure,
    build_step_plan,
    calibration_deviation_pct,
    estimated_duration_s,
    group_calibration,
    minimum_discharge_interval_s,
    rise_time_is_in_band,
    stabilisation_is_complete,
    total_discharge_count,
    validate_levels,
    validate_polarities,
    validate_procedure,
)

PLANE_TAU_S = 9.4e-5


def procedure(**over):
    record = {
        "achieved_warm_up_s": 900.0,
        "required_warm_up_s": 600.0,
        "discharge_interval_s": 1.0,
        "plane_time_constant_s": PLANE_TAU_S,
        "target_first_peak_a": 7.5,
        "calibration_state": "measured",
        "measured_first_peak_a": 7.6,
        "measured_rise_time_s": 0.8e-9,
        "discharge_points": 4.0,
        "discharges_per_point": 10.0,
        "levels_v": (2000.0, 4000.0, 8000.0),
        "polarities": ("negative", "positive"),
        "unit_monitored": True,
    }
    record.update(over)
    return record


def assess(**over):
    return assess_indirect_discharge_procedure(procedure(**over))


class TestProcedureValidation(unittest.TestCase):
    def test_good_procedure_normalizes(self):
        spec = validate_procedure(procedure())
        self.assertEqual(spec["calibration_state"], "measured")
        self.assertAlmostEqual(spec["target_first_peak_a"], 7.5, places=9)

    def test_calibration_state_token_is_case_normalized(self):
        spec = validate_procedure(procedure(calibration_state="Omitted"))
        self.assertEqual(spec["calibration_state"], "omitted")

    def test_unknown_calibration_state_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_procedure(procedure(calibration_state="probably-fine"))

    def test_an_omitted_calibration_needs_no_measurement(self):
        record = procedure(calibration_state="omitted")
        del record["measured_first_peak_a"]
        del record["measured_rise_time_s"]
        spec = validate_procedure(record)
        self.assertNotIn("measured_first_peak_a", spec)

    def test_a_measured_calibration_without_a_reading_is_rejected(self):
        record = procedure()
        del record["measured_first_peak_a"]
        with self.assertRaises(ValueError):
            validate_procedure(record)

    def test_negative_dwell_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_procedure(procedure(achieved_warm_up_s=-1.0))

    def test_zero_dwell_is_accepted_as_a_value(self):
        spec = validate_procedure(procedure(achieved_warm_up_s=0.0))
        self.assertAlmostEqual(spec["achieved_warm_up_s"], 0.0, places=12)

    def test_zero_plane_time_constant_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_procedure(procedure(plane_time_constant_s=0.0))

    def test_fractional_discharge_points_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_procedure(procedure(discharge_points=3.5))

    def test_boolean_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_procedure(procedure(discharge_interval_s=True))

    def test_non_boolean_monitoring_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_procedure(procedure(unit_monitored="yes"))


class TestLevelsAndPolarities(unittest.TestCase):
    def test_ascending_levels_pass_through(self):
        self.assertEqual(
            validate_levels((2000.0, 4000.0)), (2000.0, 4000.0)
        )

    def test_descending_levels_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_levels((8000.0, 4000.0))

    def test_repeated_level_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_levels((4000.0, 4000.0))

    def test_empty_level_list_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_levels(())

    def test_non_positive_level_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_levels((0.0, 4000.0))

    def test_polarities_come_back_in_a_deterministic_order(self):
        self.assertEqual(
            validate_polarities(("positive", "negative")), ("negative", "positive")
        )

    def test_polarity_token_is_case_normalized(self):
        self.assertEqual(validate_polarities(("Negative",)), ("negative",))

    def test_unknown_polarity_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_polarities(("sideways",))

    def test_duplicate_polarity_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_polarities(("negative", "negative"))

    def test_bare_string_polarity_list_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_polarities("negative")


class TestStabilisationAndCalibration(unittest.TestCase):
    def test_a_long_dwell_is_settled(self):
        self.assertTrue(stabilisation_is_complete(900.0, 600.0))

    def test_a_dwell_landing_on_the_requirement_is_settled(self):
        self.assertTrue(stabilisation_is_complete(600.0, 600.0))

    def test_a_short_dwell_is_not_settled(self):
        self.assertFalse(stabilisation_is_complete(300.0, 600.0))

    def test_negative_required_dwell_is_rejected(self):
        with self.assertRaises(ValueError):
            stabilisation_is_complete(600.0, -1.0)

    def test_calibration_deviation_is_a_percentage_of_the_target(self):
        self.assertAlmostEqual(calibration_deviation_pct(8.25, 7.5), 10.0, places=9)

    def test_calibration_deviation_is_symmetric(self):
        self.assertAlmostEqual(calibration_deviation_pct(6.75, 7.5), 10.0, places=9)

    def test_zero_target_peak_is_rejected(self):
        with self.assertRaises(ValueError):
            calibration_deviation_pct(7.5, 0.0)

    def test_rise_time_inside_the_band_passes(self):
        self.assertTrue(rise_time_is_in_band(0.8e-9))

    def test_rise_time_on_the_band_edge_passes(self):
        self.assertTrue(rise_time_is_in_band(RISE_TIME_BAND_S[0]))
        self.assertTrue(rise_time_is_in_band(RISE_TIME_BAND_S[1]))

    def test_rise_time_outside_the_band_fails(self):
        self.assertFalse(rise_time_is_in_band(2.0e-9))

    def test_an_inverted_rise_time_band_is_rejected(self):
        with self.assertRaises(ValueError):
            rise_time_is_in_band(0.8e-9, (1.0e-9, 0.7e-9))

    def test_a_reading_inside_tolerance_is_grouped_as_passed(self):
        self.assertEqual(group_calibration("measured", 2.0), CALIBRATION_PASSED)

    def test_a_reading_on_the_tolerance_is_grouped_as_passed(self):
        self.assertEqual(
            group_calibration("measured", CALIBRATION_TOLERANCE_PCT), CALIBRATION_PASSED
        )

    def test_a_reading_past_the_tolerance_is_grouped_out_of_tolerance(self):
        self.assertEqual(
            group_calibration("measured", 25.0), CALIBRATION_OUT_OF_TOLERANCE
        )

    def test_a_skipped_calibration_is_grouped_as_omitted(self):
        self.assertEqual(group_calibration("omitted"), CALIBRATION_OMITTED)

    def test_a_measured_calibration_without_a_deviation_is_rejected(self):
        with self.assertRaises(ValueError):
            group_calibration("measured")

    def test_an_unknown_calibration_state_is_rejected_by_the_grouping(self):
        with self.assertRaises(ValueError):
            group_calibration("assumed-good", 1.0)


class TestApplicationArithmetic(unittest.TestCase):
    def test_minimum_interval_is_the_bleed_multiple_of_the_time_constant(self):
        self.assertAlmostEqual(
            minimum_discharge_interval_s(PLANE_TAU_S),
            BLEED_MULTIPLE * PLANE_TAU_S,
            places=15,
        )

    def test_bleed_multiple_below_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            minimum_discharge_interval_s(PLANE_TAU_S, 0.5)

    def test_total_discharges_is_the_product_of_the_matrix(self):
        self.assertEqual(
            total_discharge_count((1.0, 2.0, 3.0), ("negative", "positive"), 4.0, 10.0),
            240,
        )

    def test_a_single_polarity_halves_the_matrix(self):
        self.assertEqual(
            total_discharge_count((1.0, 2.0, 3.0), ("negative",), 4.0, 10.0), 120
        )

    def test_fractional_repeat_count_is_rejected(self):
        with self.assertRaises(ValueError):
            total_discharge_count((1.0,), ("negative",), 4.0, 2.5)

    def test_an_empty_polarity_list_is_rejected_by_the_count(self):
        with self.assertRaises(ValueError):
            total_discharge_count((1.0,), (), 4.0, 10.0)

    def test_duration_counts_the_gaps_not_the_events(self):
        self.assertAlmostEqual(estimated_duration_s(240.0, 1.0), 239.0, places=9)

    def test_a_single_discharge_takes_no_interval(self):
        self.assertAlmostEqual(estimated_duration_s(1.0, 2.0), 0.0, places=12)

    def test_zero_interval_is_rejected_by_the_duration(self):
        with self.assertRaises(ValueError):
            estimated_duration_s(10.0, 0.0)


class TestStepPlan(unittest.TestCase):
    def test_plan_starts_with_stabilisation(self):
        plan = assess()["step_plan"]
        self.assertEqual(plan[0]["action"], "stabilise")

    def test_calibration_follows_stabilisation_when_it_is_run(self):
        plan = assess()["step_plan"]
        self.assertEqual(plan[1]["action"], "calibrate")

    def test_an_omitted_calibration_leaves_no_step(self):
        plan = assess(calibration_state="omitted")["step_plan"]
        self.assertEqual([s["action"] for s in plan].count("calibrate"), 0)
        self.assertEqual(plan[1]["action"], "expose")

    def test_plan_ends_with_recovery(self):
        plan = assess()["step_plan"]
        self.assertEqual(plan[-1]["action"], "recover")

    def test_plan_holds_one_exposure_step_per_level_polarity_and_point(self):
        plan = assess()["step_plan"]
        exposures = [s for s in plan if s["action"] == "expose"]
        self.assertEqual(len(exposures), 3 * 2 * 4)

    def test_exposure_steps_climb_the_levels(self):
        plan = assess()["step_plan"]
        levels = [s["level_v"] for s in plan if s["action"] == "expose"]
        self.assertAlmostEqual(levels[0], 2000.0, places=9)
        self.assertAlmostEqual(levels[-1], 8000.0, places=9)

    def test_plan_indices_are_contiguous(self):
        plan = assess()["step_plan"]
        self.assertEqual([s["index"] for s in plan], list(range(len(plan))))

    def test_a_short_interval_is_stretched_to_the_derived_minimum(self):
        report = assess(discharge_interval_s=1.0e-6)
        exposures = [s for s in report["step_plan"] if s["action"] == "expose"]
        self.assertAlmostEqual(
            exposures[0]["interval_s"], report["minimum_discharge_interval_s"], places=15
        )

    def test_an_unknown_calibration_group_is_rejected_by_the_planner(self):
        spec = validate_procedure(procedure())
        with self.assertRaises(ValueError):
            build_step_plan(spec, "calibration-maybe", 1.0)


class TestProcedureAssessment(unittest.TestCase):
    def test_good_procedure_is_compliant(self):
        report = assess()
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["limitations"], [])
        self.assertEqual(report["verdict"], VERDICT_COMPLIANT)
        self.assertEqual(report["calibration_group"], CALIBRATION_PASSED)

    def test_report_carries_the_matrix_totals(self):
        report = assess()
        self.assertEqual(report["total_discharges"], 240)
        self.assertAlmostEqual(report["estimated_duration_s"], 239.0, places=9)

    def test_a_short_dwell_is_a_finding(self):
        report = assess(achieved_warm_up_s=60.0)
        self.assertFalse(report["stabilisation_is_complete"])
        self.assertEqual(report["verdict"], VERDICT_NONCOMPLIANT)

    def test_a_calibration_past_tolerance_is_a_finding(self):
        report = assess(measured_first_peak_a=10.0)
        self.assertEqual(report["calibration_group"], CALIBRATION_OUT_OF_TOLERANCE)
        self.assertEqual(report["verdict"], VERDICT_NONCOMPLIANT)

    def test_a_skipped_calibration_is_a_limitation_not_a_finding(self):
        report = assess(calibration_state="omitted")
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], VERDICT_WITH_LIMITATIONS)
        self.assertEqual(len(report["limitations"]), 1)

    def test_a_rise_time_outside_the_band_is_a_finding(self):
        report = assess(measured_rise_time_s=3.0e-9)
        self.assertFalse(report["rise_time_is_in_band"])
        self.assertEqual(report["verdict"], VERDICT_NONCOMPLIANT)

    def test_an_interval_shorter_than_the_bleed_minimum_is_a_finding(self):
        report = assess(discharge_interval_s=1.0e-5)
        self.assertFalse(report["interval_is_adequate"])
        self.assertEqual(report["verdict"], VERDICT_NONCOMPLIANT)

    def test_an_interval_on_the_bleed_minimum_is_accepted(self):
        report = assess(discharge_interval_s=minimum_discharge_interval_s(PLANE_TAU_S))
        self.assertTrue(report["interval_is_adequate"])
        self.assertEqual(report["findings"], [])

    def test_too_few_repeats_per_point_is_a_finding(self):
        report = assess(discharges_per_point=float(MINIMUM_DISCHARGES_PER_POINT - 1))
        self.assertFalse(report["repeats_are_adequate"])
        self.assertEqual(report["verdict"], VERDICT_NONCOMPLIANT)

    def test_an_unwatched_unit_is_a_finding(self):
        report = assess(unit_monitored=False)
        self.assertEqual(report["verdict"], VERDICT_NONCOMPLIANT)

    def test_a_single_polarity_run_is_a_limitation(self):
        report = assess(polarities=("negative",))
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], VERDICT_WITH_LIMITATIONS)
        self.assertEqual(report["total_discharges"], 120)

    def test_two_faults_are_both_reported(self):
        report = assess(achieved_warm_up_s=1.0, unit_monitored=False)
        self.assertEqual(len(report["findings"]), 2)

    def test_assessment_propagates_a_procedure_error(self):
        with self.assertRaises(ValueError):
            assess(levels_v=(8000.0, 2000.0))


if __name__ == "__main__":
    unittest.main()
