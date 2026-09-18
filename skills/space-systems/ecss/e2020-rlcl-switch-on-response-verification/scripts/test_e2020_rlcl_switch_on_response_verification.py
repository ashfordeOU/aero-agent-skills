"""Contract tests for the clause 5.4.4.4.1 switch-on response verification logic."""

import unittest

from e2020_rlcl_switch_on_response_verification_logic import (
    CAMPAIGN_MARGIN_THIN,
    CAMPAIGN_NOT_EVALUATED,
    CAMPAIGN_NOT_REPEATABLE,
    CAMPAIGN_OUT_OF_WINDOW,
    CAMPAIGN_VERIFIED,
    DEFAULT_SWITCH_ON_TEST_POLICY,
    RUN_MARGIN_THIN,
    RUN_NO_TURN_ON,
    RUN_STIMULUS_BLUNT,
    RUN_TOO_FAST,
    RUN_TOO_SLOW,
    RUN_VERIFIED,
    assess_switch_on_response,
    first_upward_crossing_s,
    grade_run,
    measure_run,
    output_reached_s,
    response_spread,
    turn_on_delay_s,
    validate_response_spec,
    validate_step_profile,
    validate_switch_on_policy,
    validate_trace,
    worst_standing,
)


def _policy(**overrides):
    policy = dict(DEFAULT_SWITCH_ON_TEST_POLICY)
    policy.update(overrides)
    return policy


def _spec(**overrides):
    spec = {
        "enable_threshold_v": 22.0,
        "nominal_bus_v": 28.0,
        "regulated_output_v": 28.0,
        "min_response_s": 0.001,
        "max_response_s": 0.010,
    }
    spec.update(overrides)
    return spec


def _profile(**overrides):
    profile = {
        "start_v": 18.0,
        "end_v": 28.0,
        "settled_dwell_s": 0.100,
        "edge_time_s": 0.000050,
    }
    profile.update(overrides)
    return profile


def _run(identifier="run-1", delay_s=0.005, **overrides):
    run = {"id": identifier, "profile": _profile(), "delay_s": delay_s}
    run.update(overrides)
    return run


def _campaign(runs=None, **overrides):
    campaign = {
        "spec": _spec(),
        "runs": runs
        if runs is not None
        else [_run("run-1"), _run("run-2"), _run("run-3")],
    }
    campaign.update(overrides)
    return campaign


_INPUT_STEP = [(0.0, 18.0), (0.001, 28.0), (0.010, 28.0)]
_OUTPUT_RISE = [(0.0, 0.0), (0.001, 0.0), (0.006, 28.0)]
_OUTPUT_DEAD = [(0.0, 0.0), (0.010, 1.0)]


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_switch_on_policy(DEFAULT_SWITCH_ON_TEST_POLICY),
            DEFAULT_SWITCH_ON_TEST_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_switch_on_policy("step it and see")

    def test_a_zero_start_margin_rejected(self):
        with self.assertRaises(ValueError):
            validate_switch_on_policy(_policy(start_margin_fraction=0.0))

    def test_a_reached_fraction_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_switch_on_policy(_policy(output_reached_fraction=1.2))

    def test_a_zero_run_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_switch_on_policy(_policy(min_runs=0))

    def test_a_non_integer_run_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_switch_on_policy(_policy(min_runs=3.0))


class SpecTests(unittest.TestCase):
    def test_a_sound_spec_is_returned_normalised(self):
        bands = validate_response_spec(_spec())
        self.assertAlmostEqual(bands["max_response_s"], 0.010, places=9)

    def test_a_nominal_bus_below_the_enable_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_response_spec(_spec(nominal_bus_v=20.0))

    def test_a_nominal_bus_equal_to_the_enable_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_response_spec(_spec(nominal_bus_v=22.0))

    def test_an_inverted_response_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_response_spec(_spec(min_response_s=0.020))

    def test_a_zero_width_response_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_response_spec(_spec(min_response_s=0.010))

    def test_a_missing_regulated_output_rejected(self):
        spec = _spec()
        del spec["regulated_output_v"]
        with self.assertRaises(ValueError):
            validate_response_spec(spec)


class StepProfileTests(unittest.TestCase):
    def test_a_sound_profile_reports_a_sharp_edge(self):
        profile = validate_step_profile(_profile(), _spec())
        self.assertTrue(profile["edge_is_sharp"])
        self.assertAlmostEqual(profile["edge_ceiling_s"], 0.0001, places=12)

    def test_a_start_point_too_close_to_the_enable_point_rejected(self):
        with self.assertRaises(ValueError):
            validate_step_profile(_profile(start_v=21.0), _spec())

    def test_a_start_point_exactly_on_its_margin_accepted(self):
        profile = validate_step_profile(_profile(start_v=19.8), _spec())
        self.assertAlmostEqual(profile["start_v"], 19.8, places=9)

    def test_an_end_point_short_of_nominal_rejected(self):
        with self.assertRaises(ValueError):
            validate_step_profile(_profile(end_v=25.0), _spec())

    def test_an_end_point_inside_the_nominal_tolerance_accepted(self):
        profile = validate_step_profile(_profile(end_v=28.5), _spec())
        self.assertAlmostEqual(profile["end_v"], 28.5, places=9)

    def test_too_short_a_settled_dwell_rejected(self):
        with self.assertRaises(ValueError):
            validate_step_profile(_profile(settled_dwell_s=0.010), _spec())

    def test_a_blunt_edge_is_reported_rather_than_refused(self):
        profile = validate_step_profile(_profile(edge_time_s=0.0005), _spec())
        self.assertFalse(profile["edge_is_sharp"])

    def test_a_negative_edge_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_step_profile(_profile(edge_time_s=-1e-6), _spec())


class TraceTests(unittest.TestCase):
    def test_a_single_sample_trace_rejected(self):
        with self.assertRaises(ValueError):
            validate_trace([(0.0, 18.0)])

    def test_a_non_increasing_time_axis_rejected(self):
        with self.assertRaises(ValueError):
            validate_trace([(0.0, 18.0), (0.0, 28.0)])

    def test_the_input_crossing_is_interpolated(self):
        crossing = first_upward_crossing_s(_INPUT_STEP, 22.0)
        self.assertAlmostEqual(crossing, 0.0004, places=9)

    def test_a_trace_already_above_the_level_cannot_be_timed(self):
        with self.assertRaises(ValueError):
            first_upward_crossing_s([(0.0, 26.0), (0.001, 28.0)], 22.0)

    def test_a_trace_that_never_crosses_is_refused(self):
        with self.assertRaises(ValueError):
            first_upward_crossing_s(_OUTPUT_DEAD, 25.2)

    def test_the_output_reach_level_follows_the_policy_fraction(self):
        reached = output_reached_s(_OUTPUT_RISE, 28.0)
        self.assertAlmostEqual(reached, 0.0055, places=9)

    def test_a_lower_reach_fraction_times_an_earlier_instant(self):
        early = output_reached_s(_OUTPUT_RISE, 28.0, _policy(output_reached_fraction=0.5))
        late = output_reached_s(_OUTPUT_RISE, 28.0)
        self.assertLess(early, late)

    def test_the_delay_is_the_difference_of_the_two_instants(self):
        delay = turn_on_delay_s(
            {"input_samples": _INPUT_STEP, "output_samples": _OUTPUT_RISE}, _spec()
        )
        self.assertAlmostEqual(delay, 0.0051, places=9)

    def test_traces_on_different_time_bases_are_refused(self):
        with self.assertRaises(ValueError):
            turn_on_delay_s(
                {
                    "input_samples": [(0.010, 18.0), (0.011, 28.0)],
                    "output_samples": _OUTPUT_RISE,
                },
                _spec(),
            )


class RunMeasurementTests(unittest.TestCase):
    def test_a_run_with_no_id_rejected(self):
        with self.assertRaises(ValueError):
            measure_run(_run(identifier="  "), _spec())

    def test_a_run_with_neither_traces_nor_a_delay_rejected(self):
        run = _run()
        del run["delay_s"]
        with self.assertRaises(ValueError):
            measure_run(run, _spec())

    def test_a_negative_delay_rejected(self):
        with self.assertRaises(ValueError):
            measure_run(_run(delay_s=-0.001), _spec())

    def test_a_sampled_run_takes_its_delay_from_the_traces(self):
        record = measure_run(
            {
                "id": "run-1",
                "profile": _profile(),
                "input_samples": _INPUT_STEP,
                "output_samples": _OUTPUT_RISE,
            },
            _spec(),
        )
        self.assertAlmostEqual(record["delay_s"], 0.0051, places=9)

    def test_an_output_that_never_answers_is_recorded_as_no_turn_on(self):
        record = measure_run(
            {
                "id": "run-1",
                "profile": _profile(),
                "input_samples": _INPUT_STEP,
                "output_samples": _OUTPUT_DEAD,
            },
            _spec(),
        )
        self.assertFalse(record["turned_on"])
        self.assertTrue(record["gaps"])

    def test_a_blunt_edge_leaves_a_gap_on_the_record(self):
        record = measure_run(
            _run(profile=_profile(edge_time_s=0.0005)), _spec()
        )
        self.assertTrue(record["gaps"])


class RunGradingTests(unittest.TestCase):
    def test_a_central_delay_is_verified(self):
        record = measure_run(_run(delay_s=0.005), _spec())
        self.assertEqual(grade_run(record, _spec()), RUN_VERIFIED)

    def test_a_delay_past_the_ceiling_is_too_slow(self):
        record = measure_run(_run(delay_s=0.012), _spec())
        self.assertEqual(grade_run(record, _spec()), RUN_TOO_SLOW)

    def test_a_delay_under_the_floor_is_too_fast(self):
        record = measure_run(_run(delay_s=0.0005), _spec())
        self.assertEqual(grade_run(record, _spec()), RUN_TOO_FAST)

    def test_a_delay_just_inside_the_floor_is_thin(self):
        record = measure_run(_run(delay_s=0.0015), _spec())
        self.assertEqual(grade_run(record, _spec()), RUN_MARGIN_THIN)

    def test_a_delay_just_inside_the_ceiling_is_thin(self):
        record = measure_run(_run(delay_s=0.0095), _spec())
        self.assertEqual(grade_run(record, _spec()), RUN_MARGIN_THIN)

    def test_a_delay_exactly_on_the_ceiling_guard_is_verified(self):
        record = measure_run(_run(delay_s=0.0091), _spec())
        self.assertEqual(grade_run(record, _spec()), RUN_VERIFIED)

    def test_a_blunt_stimulus_outranks_a_good_delay(self):
        record = measure_run(
            _run(delay_s=0.005, profile=_profile(edge_time_s=0.0005)), _spec()
        )
        self.assertEqual(grade_run(record, _spec()), RUN_STIMULUS_BLUNT)

    def test_a_dead_output_grades_as_no_turn_on(self):
        record = measure_run(
            {
                "id": "run-1",
                "profile": _profile(),
                "input_samples": _INPUT_STEP,
                "output_samples": _OUTPUT_DEAD,
            },
            _spec(),
        )
        self.assertEqual(grade_run(record, _spec()), RUN_NO_TURN_ON)


class SpreadTests(unittest.TestCase):
    def test_identical_runs_have_no_spread(self):
        statistics = response_spread([0.005, 0.005, 0.005])
        self.assertAlmostEqual(statistics["relative_spread"], 0.0, places=12)

    def test_the_mean_and_extremes_are_reported(self):
        statistics = response_spread([0.004, 0.005, 0.006])
        self.assertAlmostEqual(statistics["mean_s"], 0.005, places=12)
        self.assertAlmostEqual(statistics["min_s"], 0.004, places=12)
        self.assertAlmostEqual(statistics["max_s"], 0.006, places=12)

    def test_the_relative_spread_is_against_the_mean(self):
        statistics = response_spread([0.004, 0.006])
        self.assertAlmostEqual(statistics["relative_spread"], 0.4, places=9)

    def test_an_empty_set_of_delays_rejected(self):
        with self.assertRaises(ValueError):
            response_spread([])

    def test_a_negative_delay_in_the_set_rejected(self):
        with self.assertRaises(ValueError):
            response_spread([0.005, -0.001])


class CampaignTests(unittest.TestCase):
    def test_a_sound_campaign_is_verified(self):
        result = assess_switch_on_response(_campaign())
        self.assertEqual(result["verdict"], CAMPAIGN_VERIFIED)
        self.assertEqual(result["findings"], [])

    def test_a_slow_run_puts_the_campaign_out_of_window(self):
        result = assess_switch_on_response(
            _campaign([_run("run-1"), _run("run-2"), _run("run-3", 0.012)])
        )
        self.assertEqual(result["verdict"], CAMPAIGN_OUT_OF_WINDOW)
        self.assertIn("run-3", result["standings"][RUN_TOO_SLOW])

    def test_a_fast_run_is_a_finding_and_not_a_bonus(self):
        result = assess_switch_on_response(
            _campaign([_run("run-1"), _run("run-2"), _run("run-3", 0.0005)])
        )
        self.assertIn("run-3", result["standings"][RUN_TOO_FAST])

    def test_too_few_runs_leaves_the_campaign_unevaluated(self):
        result = assess_switch_on_response(_campaign([_run("run-1")]))
        self.assertEqual(result["verdict"], CAMPAIGN_NOT_EVALUATED)

    def test_a_scattered_set_of_runs_is_not_repeatable(self):
        result = assess_switch_on_response(
            _campaign(
                [_run("run-1", 0.004), _run("run-2", 0.005), _run("run-3", 0.007)]
            )
        )
        self.assertEqual(result["verdict"], CAMPAIGN_NOT_REPEATABLE)

    def test_a_thin_margin_is_reported_without_a_breach(self):
        result = assess_switch_on_response(
            _campaign(
                [_run("run-1", 0.0095), _run("run-2", 0.0095), _run("run-3", 0.0095)]
            )
        )
        self.assertEqual(result["verdict"], CAMPAIGN_MARGIN_THIN)

    def test_a_duplicate_run_id_rejected(self):
        with self.assertRaises(ValueError):
            assess_switch_on_response(
                _campaign([_run("run-1"), _run("run-1"), _run("run-3")])
            )

    def test_a_campaign_with_no_runs_rejected(self):
        with self.assertRaises(ValueError):
            assess_switch_on_response(_campaign([]))

    def test_a_campaign_with_no_spec_rejected(self):
        campaign = _campaign()
        del campaign["spec"]
        with self.assertRaises(ValueError):
            assess_switch_on_response(campaign)

    def test_findings_name_the_run_that_produced_them(self):
        result = assess_switch_on_response(
            _campaign([_run("run-1"), _run("run-2"), _run("run-7", 0.012)])
        )
        self.assertTrue(any(f.startswith("run-7:") for f in result["findings"]))

    def test_the_statistics_cover_every_timed_run(self):
        result = assess_switch_on_response(_campaign())
        self.assertEqual(result["statistics"]["count"], 3)

    def test_the_worst_standing_is_the_one_reported(self):
        result = assess_switch_on_response(
            _campaign([_run("run-1"), _run("run-2", 0.0095), _run("run-3", 0.012)])
        )
        self.assertEqual(worst_standing(result["runs"]), RUN_TOO_SLOW)

    def test_worst_standing_rejects_an_empty_set(self):
        with self.assertRaises(ValueError):
            worst_standing([])


if __name__ == "__main__":
    unittest.main()
