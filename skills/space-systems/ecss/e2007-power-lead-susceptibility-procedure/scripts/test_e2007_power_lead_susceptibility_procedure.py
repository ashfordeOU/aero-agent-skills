#!/usr/bin/env python3
"""Contract test for the power-lead susceptibility procedure leaf."""

import unittest

from e2007_power_lead_susceptibility_procedure_logic import (
    DWELL_FLOOR_S,
    LEVEL_STEP_MAX_DB,
    MARGIN_REQUIRED_DB,
    POINTS_PER_DECADE_MIN,
    WARM_UP_FLOOR_S,
    check_dwell,
    check_level_ramp,
    check_step_ratio,
    check_warm_up,
    evaluate_injection_step,
    frequency_ladder,
    required_dwell_s,
    run_injection_procedure,
    step_ratio,
    susceptibility_margin_db,
    susceptibility_threshold_db,
)

F0 = 1.0e4
F1 = 1.0e4 * 10.0 ** 0.1
F2 = 1.0e4 * 10.0 ** 0.2


def injection_step(**overrides):
    step = {
        "frequency_hz": F0,
        "required_level_db": 20.0,
        "levels_db": [8.0, 14.0, 20.0],
        "dwell_s": 2.0,
        "response_time_s": 0.5,
    }
    step.update(overrides)
    return step


def profile(**overrides):
    run = {
        "warm_up_s": 1200.0,
        "stabilization_s": 600.0,
        "start_hz": F0,
        "stop_hz": F2,
        "points_per_decade": 10,
        "steps": [
            injection_step(frequency_hz=F0),
            injection_step(frequency_hz=F1),
            injection_step(frequency_hz=F2),
        ],
    }
    run.update(overrides)
    return run


def codes(report):
    return [finding["code"] for finding in report["findings"]]


class TestWarmUp(unittest.TestCase):
    def test_a_long_warm_up_conforms(self):
        check = check_warm_up(1200.0, 600.0)
        self.assertTrue(check["within"])
        self.assertAlmostEqual(check["required_s"], WARM_UP_FLOOR_S, places=9)
        self.assertEqual(check["governed_by"], "floor")

    def test_the_floor_met_exactly_conforms(self):
        self.assertTrue(check_warm_up(WARM_UP_FLOOR_S)["within"])

    def test_a_long_stabilization_time_governs(self):
        check = check_warm_up(1800.0, 1500.0)
        self.assertEqual(check["governed_by"], "stabilization")
        self.assertAlmostEqual(check["required_s"], 1500.0, places=9)

    def test_a_short_warm_up_fails(self):
        self.assertFalse(check_warm_up(60.0)["within"])

    def test_a_negative_warm_up_raises(self):
        with self.assertRaises(ValueError):
            check_warm_up(-1.0)


class TestFrequencyLadder(unittest.TestCase):
    def test_step_ratio_of_ten_points_per_decade(self):
        self.assertAlmostEqual(step_ratio(10), 1.2589254117941673, places=9)

    def test_step_ratio_of_one_point_per_decade_is_a_decade(self):
        self.assertAlmostEqual(step_ratio(1), 10.0, places=9)

    def test_a_zero_point_count_raises(self):
        with self.assertRaises(ValueError):
            step_ratio(0)

    def test_a_non_integer_point_count_raises(self):
        with self.assertRaises(ValueError):
            step_ratio(10.0)

    def test_three_decades_at_ten_points_give_thirty_one_rungs(self):
        rungs = frequency_ladder(1.0e3, 1.0e6, 10)
        self.assertEqual(len(rungs), 31)
        self.assertAlmostEqual(rungs[0], 1.0e3, places=9)
        self.assertAlmostEqual(rungs[-1], 1.0e6, places=3)

    def test_the_last_rung_is_pinned_to_the_stop(self):
        rungs = frequency_ladder(1.0e3, 1.0e6, 10)
        self.assertEqual(rungs[-1], 1.0e6)

    def test_a_partial_decade_ends_on_the_stop(self):
        rungs = frequency_ladder(1.0e3, 2.0e3, 10)
        self.assertEqual(rungs[-1], 2.0e3)
        self.assertGreater(len(rungs), 3)

    def test_a_ladder_that_does_not_rise_raises(self):
        with self.assertRaises(ValueError):
            frequency_ladder(1.0e6, 1.0e3, 10)

    def test_a_zero_start_raises(self):
        with self.assertRaises(ValueError):
            frequency_ladder(0.0, 1.0e3, 10)

    def test_a_step_on_the_allowed_ratio_conforms(self):
        check = check_step_ratio(F0, F1, 10)
        self.assertAlmostEqual(check["ratio"], check["allowed_ratio"], places=9)
        self.assertTrue(check["within"])

    def test_a_step_of_a_whole_decade_is_too_coarse(self):
        self.assertFalse(check_step_ratio(1.0e4, 1.0e5, 10)["within"])

    def test_a_step_that_does_not_rise_raises(self):
        with self.assertRaises(ValueError):
            check_step_ratio(1.0e5, 1.0e4, 10)


class TestDwell(unittest.TestCase):
    def test_a_fast_unit_falls_back_to_the_dwell_floor(self):
        self.assertAlmostEqual(required_dwell_s(0.0), DWELL_FLOOR_S, places=9)

    def test_a_slow_unit_sets_a_longer_dwell(self):
        self.assertAlmostEqual(required_dwell_s(2.0), 6.0, places=9)

    def test_a_dwell_on_its_requirement_conforms(self):
        check = check_dwell(6.0, 2.0)
        self.assertAlmostEqual(check["required_s"], 6.0, places=9)
        self.assertTrue(check["within"])

    def test_a_dwell_well_below_its_requirement_fails(self):
        self.assertFalse(check_dwell(0.5, 2.0)["within"])

    def test_a_zero_dwell_raises(self):
        with self.assertRaises(ValueError):
            check_dwell(0.0, 1.0)

    def test_a_negative_response_time_raises(self):
        with self.assertRaises(ValueError):
            check_dwell(2.0, -1.0)


class TestLevelRamp(unittest.TestCase):
    def test_a_ramp_on_the_allowance_conforms(self):
        check = check_level_ramp([8.0, 14.0, 20.0])
        self.assertAlmostEqual(check["coarsest_db"], LEVEL_STEP_MAX_DB, places=9)
        self.assertTrue(check["within"])
        self.assertAlmostEqual(check["top_db"], 20.0, places=9)

    def test_a_ramp_well_over_the_allowance_fails(self):
        self.assertFalse(check_level_ramp([0.0, 20.0])["within"])

    def test_a_ramp_that_does_not_rise_raises(self):
        with self.assertRaises(ValueError):
            check_level_ramp([10.0, 10.0])

    def test_a_single_level_raises(self):
        with self.assertRaises(ValueError):
            check_level_ramp([10.0])

    def test_a_string_ramp_raises(self):
        with self.assertRaises(ValueError):
            check_level_ramp("8,14,20")


class TestThresholdAndMargin(unittest.TestCase):
    def test_the_threshold_is_the_lowest_responding_level(self):
        record = [(0.0, False), (6.0, False), (12.0, True), (18.0, True)]
        self.assertAlmostEqual(susceptibility_threshold_db(record), 12.0, places=9)

    def test_a_record_with_no_response_has_no_threshold(self):
        record = [(0.0, False), (6.0, False), (12.0, False)]
        self.assertIsNone(susceptibility_threshold_db(record))

    def test_a_recovery_above_the_threshold_raises(self):
        record = [(0.0, False), (6.0, True), (12.0, False)]
        with self.assertRaises(ValueError):
            susceptibility_threshold_db(record)

    def test_levels_that_do_not_rise_raise(self):
        with self.assertRaises(ValueError):
            susceptibility_threshold_db([(6.0, False), (6.0, True)])

    def test_a_non_boolean_response_raises(self):
        with self.assertRaises(ValueError):
            susceptibility_threshold_db([(6.0, "yes")])

    def test_an_observation_of_the_wrong_width_raises(self):
        with self.assertRaises(ValueError):
            susceptibility_threshold_db([(6.0, False, "note")])

    def test_an_empty_record_raises(self):
        with self.assertRaises(ValueError):
            susceptibility_threshold_db([])

    def test_a_margin_on_its_requirement_is_within(self):
        margin = susceptibility_margin_db(20.0, 14.0)
        self.assertAlmostEqual(margin["margin_db"], MARGIN_REQUIRED_DB, places=9)
        self.assertTrue(margin["within"])
        self.assertTrue(margin["above_required"])

    def test_a_threshold_below_the_required_level_is_not_above_it(self):
        margin = susceptibility_margin_db(10.0, 14.0)
        self.assertFalse(margin["above_required"])
        self.assertFalse(margin["within"])

    def test_a_thin_margin_is_above_the_level_but_short_of_the_requirement(self):
        margin = susceptibility_margin_db(16.0, 14.0)
        self.assertTrue(margin["above_required"])
        self.assertFalse(margin["within"])


class TestEvaluateInjectionStep(unittest.TestCase):
    def test_a_clean_step_conforms(self):
        record = evaluate_injection_step(injection_step())
        self.assertEqual(record["verdict"], "conforming")
        self.assertTrue(record["conforming"])
        self.assertEqual(record["findings"], [])

    def test_a_responding_step_is_susceptible(self):
        record = evaluate_injection_step(
            injection_step(required_level_db=8.0, responded_at_db=14.0)
        )
        self.assertEqual(record["verdict"], "susceptible")
        self.assertFalse(record["conforming"])
        self.assertIn("unit-responded", [f["code"] for f in record["findings"]])

    def test_a_thin_margin_is_reported_on_a_responding_step(self):
        record = evaluate_injection_step(
            injection_step(required_level_db=12.0, responded_at_db=14.0)
        )
        self.assertIn(
            "margin-below-requirement", [f["code"] for f in record["findings"]]
        )

    def test_a_coarse_ramp_is_reported(self):
        record = evaluate_injection_step(injection_step(levels_db=[0.0, 20.0]))
        self.assertIn("level-step-too-coarse", [f["code"] for f in record["findings"]])

    def test_a_short_dwell_is_reported(self):
        record = evaluate_injection_step(injection_step(dwell_s=0.2))
        self.assertIn("dwell-too-short", [f["code"] for f in record["findings"]])

    def test_a_drive_limited_step_is_marked(self):
        record = evaluate_injection_step(
            injection_step(levels_db=[8.0, 14.0], drive_limited=True)
        )
        self.assertEqual(record["verdict"], "drive-limited")
        self.assertIn("drive-limit-reached", [f["code"] for f in record["findings"]])

    def test_a_ramp_stopped_short_with_no_drive_limit_is_reported(self):
        record = evaluate_injection_step(injection_step(levels_db=[8.0, 14.0]))
        self.assertIn(
            "required-level-not-reached", [f["code"] for f in record["findings"]]
        )

    def test_a_response_outside_the_ramp_raises(self):
        with self.assertRaises(ValueError):
            evaluate_injection_step(injection_step(responded_at_db=40.0))

    def test_an_unknown_step_key_raises(self):
        step = injection_step()
        step["bandwidth_hz"] = 1.0e3
        with self.assertRaises(ValueError):
            evaluate_injection_step(step)

    def test_a_step_without_a_ramp_raises(self):
        step = injection_step()
        del step["levels_db"]
        with self.assertRaises(ValueError):
            evaluate_injection_step(step)

    def test_a_non_mapping_step_raises(self):
        with self.assertRaises(ValueError):
            evaluate_injection_step("10 kHz")


class TestRunInjectionProcedure(unittest.TestCase):
    def test_a_clean_run_is_accepted(self):
        report = run_injection_procedure(profile())
        self.assertTrue(report["accepted"])
        self.assertEqual(report["verdict"], "run-accepted")
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["step_count"], 3)
        self.assertAlmostEqual(report["conforming_fraction"], 1.0, places=12)

    def test_a_short_warm_up_is_reported(self):
        self.assertIn(
            "warm-up-too-short", codes(run_injection_procedure(profile(warm_up_s=30.0)))
        )

    def test_a_coarse_ladder_is_reported(self):
        run = profile(points_per_decade=2)
        self.assertIn("ladder-too-coarse", codes(run_injection_procedure(run)))
        self.assertLess(2, POINTS_PER_DECADE_MIN)

    def test_a_ladder_step_of_a_decade_is_reported(self):
        run = profile(
            stop_hz=1.0e5,
            steps=[
                injection_step(frequency_hz=1.0e4),
                injection_step(frequency_hz=1.0e5),
            ],
        )
        self.assertIn("ladder-step-too-coarse", codes(run_injection_procedure(run)))

    def test_a_ladder_that_does_not_ascend_is_reported(self):
        run = profile(
            steps=[
                injection_step(frequency_hz=F2),
                injection_step(frequency_hz=F0),
                injection_step(frequency_hz=F2),
            ]
        )
        self.assertIn("ladder-not-ascending", codes(run_injection_procedure(run)))

    def test_a_run_starting_above_the_band_bottom_is_reported(self):
        run = profile(start_hz=1.0e3)
        self.assertIn("band-bottom-not-reached", codes(run_injection_procedure(run)))

    def test_a_run_ending_below_the_band_top_is_reported(self):
        run = profile(stop_hz=1.0e6)
        self.assertIn("band-top-not-reached", codes(run_injection_procedure(run)))

    def test_a_susceptible_step_is_counted(self):
        run = profile()
        run["steps"][1] = injection_step(
            frequency_hz=F1, required_level_db=8.0, responded_at_db=14.0
        )
        report = run_injection_procedure(run)
        self.assertEqual(report["susceptible_count"], 1)
        self.assertFalse(report["accepted"])
        self.assertAlmostEqual(report["conforming_fraction"], 2.0 / 3.0, places=12)

    def test_a_drive_limited_step_is_counted(self):
        run = profile()
        run["steps"][2] = injection_step(
            frequency_hz=F2, levels_db=[8.0, 14.0], drive_limited=True
        )
        report = run_injection_procedure(run)
        self.assertEqual(report["drive_limited_count"], 1)

    def test_an_unknown_profile_key_raises(self):
        run = profile()
        run["chamber"] = "shielded"
        with self.assertRaises(ValueError):
            run_injection_procedure(run)

    def test_a_profile_without_a_warm_up_raises(self):
        run = profile()
        del run["warm_up_s"]
        with self.assertRaises(ValueError):
            run_injection_procedure(run)

    def test_a_band_that_does_not_rise_raises(self):
        with self.assertRaises(ValueError):
            run_injection_procedure(profile(start_hz=F2, stop_hz=F0))

    def test_an_empty_step_list_raises(self):
        with self.assertRaises(ValueError):
            run_injection_procedure(profile(steps=[]))

    def test_a_string_step_list_raises(self):
        with self.assertRaises(ValueError):
            run_injection_procedure(profile(steps="10 kHz"))

    def test_a_non_mapping_profile_raises(self):
        with self.assertRaises(ValueError):
            run_injection_procedure("run")

    def test_findings_carry_code_subject_and_detail(self):
        report = run_injection_procedure(profile(warm_up_s=30.0))
        for finding in report["findings"]:
            self.assertEqual(sorted(finding.keys()), ["code", "detail", "subject"])


if __name__ == "__main__":
    unittest.main()
