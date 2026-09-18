#!/usr/bin/env python3
"""Contract test for powder bed fusion build monitoring (offline)."""

import copy
import unittest

from q7080_machine_monitoring_logic import (
    LOG_ACCEPTABLE,
    LOG_NONCONFORMING,
    LOG_WITH_OBSERVATIONS,
    MONITORED_PARAMETERS,
    PARAMETER_NONCONFORMANCE,
    PARAMETER_SHORT_EXCURSION,
    PARAMETER_WITHIN_LIMITS,
    SAMPLING_ADEQUATE,
    SAMPLING_GAPPED,
    SAMPLING_TOO_SLOW,
    assess_build_monitoring,
    assess_parameter,
    excursion_episodes,
    grade_sampling,
    layers_touched,
    missing_channels,
    sampling_statistics,
    validate_parameter_limits,
    validate_samples,
)

POWER_LIMITS = {"lower": 180.0, "upper": 220.0, "max_excursion_s": 1.0}


def _steady(count=10, value=200.0, step=1.0):
    return [{"t_s": index * step, "value": value} for index in range(count)]


def _with_excursion(indexes, value=260.0, count=10):
    samples = _steady(count)
    for index in indexes:
        samples[index]["value"] = value
    return samples


def _case(**overrides):
    case = {
        "build_duration_s": 9.0,
        "layer_time_s": 3.0,
        "required_interval_s": 1.0,
        "max_gap_s": 2.0,
        "required_channels": ["laser-power-w"],
        "channels": {
            "laser-power-w": {"samples": _steady(), "limits": POWER_LIMITS}
        },
    }
    case.update(overrides)
    return copy.deepcopy(case)


class LimitAndSampleTests(unittest.TestCase):
    def test_a_well_formed_window_normalizes(self):
        limits = validate_parameter_limits(POWER_LIMITS)
        self.assertAlmostEqual(limits["upper"], 220.0, places=12)

    def test_an_inverted_window_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter_limits({"lower": 220.0, "upper": 180.0})

    def test_a_window_missing_a_bound_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter_limits({"lower": 180.0})

    def test_a_negative_excursion_allowance_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_parameter_limits(dict(POWER_LIMITS, max_excursion_s=-1.0))

    def test_a_single_sample_series_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_samples([{"t_s": 0.0, "value": 200.0}])

    def test_a_time_axis_that_goes_backwards_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_samples(
                [{"t_s": 1.0, "value": 200.0}, {"t_s": 0.5, "value": 200.0}]
            )

    def test_a_repeated_timestamp_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_samples(
                [{"t_s": 1.0, "value": 200.0}, {"t_s": 1.0, "value": 201.0}]
            )

    def test_a_non_numeric_reading_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_samples(
                [{"t_s": 0.0, "value": "200"}, {"t_s": 1.0, "value": 200.0}]
            )


class EpisodeTests(unittest.TestCase):
    def test_a_steady_channel_has_no_episode(self):
        self.assertEqual(excursion_episodes(_steady(), POWER_LIMITS), ())

    def test_neighbouring_out_of_limit_samples_form_one_episode(self):
        episodes = excursion_episodes(_with_excursion([4, 5]), POWER_LIMITS)
        self.assertEqual(len(episodes), 1)
        self.assertEqual(episodes[0]["sample_count"], 2)

    def test_separated_out_of_limit_samples_form_two_episodes(self):
        episodes = excursion_episodes(_with_excursion([2, 6]), POWER_LIMITS)
        self.assertEqual(len(episodes), 2)

    def test_an_episode_runs_to_the_sample_that_returns_in_limit(self):
        episodes = excursion_episodes(_with_excursion([4]), POWER_LIMITS)
        self.assertAlmostEqual(episodes[0]["duration_s"], 1.0, places=12)

    def test_the_worst_deviation_is_measured_from_the_bound_crossed(self):
        episodes = excursion_episodes(_with_excursion([4], value=260.0), POWER_LIMITS)
        self.assertAlmostEqual(episodes[0]["worst_deviation"], 40.0, places=12)
        self.assertEqual(episodes[0]["bound_crossed"], "upper")

    def test_a_low_excursion_is_measured_from_the_lower_bound(self):
        episodes = excursion_episodes(_with_excursion([4], value=150.0), POWER_LIMITS)
        self.assertAlmostEqual(episodes[0]["worst_deviation"], 30.0, places=12)
        self.assertEqual(episodes[0]["bound_crossed"], "lower")

    def test_a_reading_exactly_on_the_bound_is_not_an_excursion(self):
        samples = _with_excursion([4], value=220.0)
        self.assertEqual(excursion_episodes(samples, POWER_LIMITS), ())

    def test_an_excursion_that_never_returns_closes_at_the_last_sample(self):
        samples = _with_excursion([8, 9])
        episodes = excursion_episodes(samples, POWER_LIMITS)
        self.assertAlmostEqual(episodes[0]["end_s"], 9.0, places=12)


class SamplingTests(unittest.TestCase):
    def test_a_regular_series_reports_its_interval_and_coverage(self):
        stats = sampling_statistics(_steady(), 9.0)
        self.assertAlmostEqual(stats["median_interval_s"], 1.0, places=12)
        self.assertAlmostEqual(stats["coverage_fraction"], 1.0, places=12)

    def test_a_sample_after_the_end_of_the_build_is_rejected(self):
        with self.assertRaises(ValueError):
            sampling_statistics(_steady(), 4.0)

    def test_an_interval_exactly_on_the_requirement_is_adequate(self):
        graded = grade_sampling(_steady(), 9.0, 1.0, 2.0)
        self.assertEqual(graded["verdict"], SAMPLING_ADEQUATE)

    def test_a_slower_interval_than_required_is_reported(self):
        graded = grade_sampling(_steady(step=2.0), 18.0, 1.0, 4.0)
        self.assertEqual(graded["verdict"], SAMPLING_TOO_SLOW)

    def test_a_gap_in_the_record_is_reported(self):
        samples = _steady(5) + [{"t_s": 20.0, "value": 200.0}]
        graded = grade_sampling(samples, 20.0, 1.0, 2.0)
        self.assertEqual(graded["verdict"], SAMPLING_GAPPED)

    def test_short_coverage_of_the_build_is_reported(self):
        graded = grade_sampling(_steady(), 18.0, 1.0, 2.0, 1.0)
        self.assertEqual(graded["verdict"], SAMPLING_GAPPED)

    def test_a_coverage_floor_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_sampling(_steady(), 9.0, 1.0, 2.0, 1.5)


class ChannelAndLayerTests(unittest.TestCase):
    def test_a_required_channel_that_was_never_logged_is_named(self):
        self.assertEqual(
            missing_channels(["laser-power-w", "recoater-force-n"],
                             ["laser-power-w"]),
            ("recoater-force-n",),
        )

    def test_a_fully_logged_requirement_leaves_no_gap(self):
        self.assertEqual(missing_channels(["laser-power-w"], ["laser-power-w"]), ())

    def test_an_unknown_required_channel_is_rejected(self):
        with self.assertRaises(ValueError):
            missing_channels(["thermal-vibes"], ["laser-power-w"])

    def test_every_declared_channel_is_a_known_token(self):
        self.assertIn("laser-power-w", MONITORED_PARAMETERS)
        self.assertIn("residual-oxygen-ppm", MONITORED_PARAMETERS)

    def test_an_excursion_inside_one_layer_names_one_layer(self):
        self.assertEqual(layers_touched(0.5, 2.5, 3.0), (1,))

    def test_an_excursion_spanning_a_layer_boundary_names_both(self):
        self.assertEqual(layers_touched(2.5, 4.0, 3.0), (1, 2))

    def test_an_excursion_that_ends_before_it_starts_is_rejected(self):
        with self.assertRaises(ValueError):
            layers_touched(4.0, 2.0, 3.0)

    def test_a_zero_layer_time_is_rejected(self):
        with self.assertRaises(ValueError):
            layers_touched(0.0, 1.0, 0.0)


class ParameterAssessmentTests(unittest.TestCase):
    def test_a_steady_channel_is_within_limits(self):
        result = assess_parameter("laser-power-w", _steady(), POWER_LIMITS)
        self.assertEqual(result["verdict"], PARAMETER_WITHIN_LIMITS)

    def test_an_episode_inside_the_allowance_is_recorded_not_raised(self):
        result = assess_parameter("laser-power-w", _with_excursion([4]), POWER_LIMITS)
        self.assertEqual(result["verdict"], PARAMETER_SHORT_EXCURSION)

    def test_an_episode_exactly_on_the_allowance_is_still_short(self):
        result = assess_parameter("laser-power-w", _with_excursion([4]), POWER_LIMITS)
        self.assertAlmostEqual(result["total_out_of_limit_s"], 1.0, places=12)
        self.assertEqual(result["verdict"], PARAMETER_SHORT_EXCURSION)

    def test_a_longer_episode_is_a_nonconformance(self):
        result = assess_parameter(
            "laser-power-w", _with_excursion([4, 5]), POWER_LIMITS
        )
        self.assertEqual(result["verdict"], PARAMETER_NONCONFORMANCE)

    def test_the_assessment_attributes_the_episode_to_its_layers(self):
        result = assess_parameter(
            "laser-power-w", _with_excursion([4, 5]), POWER_LIMITS, layer_time_s=3.0
        )
        self.assertEqual(result["affected_layers"], (2, 3))

    def test_an_unknown_parameter_name_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_parameter("thermal-vibes", _steady(), POWER_LIMITS)


class BuildAssessmentTests(unittest.TestCase):
    def test_a_clean_build_log_is_acceptable(self):
        self.assertEqual(assess_build_monitoring(_case())["verdict"], LOG_ACCEPTABLE)

    def test_a_short_excursion_leaves_an_observation(self):
        case = _case()
        case["channels"]["laser-power-w"]["samples"] = _with_excursion([4])
        self.assertEqual(
            assess_build_monitoring(case)["verdict"], LOG_WITH_OBSERVATIONS
        )

    def test_a_long_excursion_makes_the_log_nonconforming(self):
        case = _case()
        case["channels"]["laser-power-w"]["samples"] = _with_excursion([4, 5])
        result = assess_build_monitoring(case)
        self.assertEqual(result["verdict"], LOG_NONCONFORMING)
        self.assertEqual(result["nonconforming_parameters"], ("laser-power-w",))

    def test_a_missing_required_channel_makes_the_log_nonconforming(self):
        case = _case(required_channels=["laser-power-w", "residual-oxygen-ppm"])
        result = assess_build_monitoring(case)
        self.assertEqual(result["verdict"], LOG_NONCONFORMING)
        self.assertEqual(result["missing_channels"], ("residual-oxygen-ppm",))

    def test_a_gapped_record_makes_the_log_nonconforming(self):
        case = _case(build_duration_s=20.0)
        case["channels"]["laser-power-w"]["samples"] = (
            _steady(5) + [{"t_s": 20.0, "value": 200.0}]
        )
        self.assertEqual(assess_build_monitoring(case)["verdict"], LOG_NONCONFORMING)

    def test_the_build_record_carries_the_affected_layers(self):
        case = _case()
        case["channels"]["laser-power-w"]["samples"] = _with_excursion([4, 5])
        self.assertEqual(assess_build_monitoring(case)["affected_layers"], (2, 3))

    def test_a_case_without_channels_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_build_monitoring(_case(channels={}))

    def test_a_non_mapping_case_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_build_monitoring("laser-power-w")

    def test_a_zero_build_duration_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_build_monitoring(_case(build_duration_s=0.0))


if __name__ == "__main__":
    unittest.main()
