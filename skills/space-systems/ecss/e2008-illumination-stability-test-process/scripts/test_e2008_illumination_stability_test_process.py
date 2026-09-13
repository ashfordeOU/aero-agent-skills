"""Contract tests for the clause 6.4.3.12.2 illumination soak run logic."""

import unittest

from e2008_illumination_stability_test_process_logic import (
    CHARACTERISATION_INCOMPLETE,
    DEFAULT_SOAK_POLICY,
    ILLUMINATION_SOAK_CONFORMS,
    SOAK_CONDITIONS_VIOLATED,
    SOAK_DURATION_SHORTFALL,
    SOAK_NOT_CONTINUOUS,
    assess_illumination_soak_run,
    characterisation_inventory,
    interruption_hours,
    irradiance_on_reference,
    longest_continuous_hours,
    missing_characterisation_points,
    ordered_segments,
    plane_non_uniformity,
    segment_hours,
    simulator_plane_uniform,
    simulator_temporally_stable,
    temperature_controlled,
    total_illuminated_hours,
    validate_soak_policy,
)

POINTS = ["pre-soak-iv", "post-soak-iv"]


def _policy(**overrides):
    policy = dict(DEFAULT_SOAK_POLICY)
    policy.update(overrides)
    return policy


def _segment(start, end, irradiance=1367.0, temperature=25.0):
    return {
        "start_hours": start,
        "end_hours": end,
        "irradiance_w_per_m2": irradiance,
        "temperature_c": temperature,
    }


def _case(**overrides):
    case = {
        "simulator": {
            "plane_max_irradiance_w_per_m2": 1400.0,
            "plane_min_irradiance_w_per_m2": 1340.0,
            "temporal_instability": 0.01,
        },
        "segments": [_segment(0.0, 24.0), _segment(24.0, 48.0)],
        "characterisation_points": list(POINTS),
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(validate_soak_policy(DEFAULT_SOAK_POLICY), DEFAULT_SOAK_POLICY)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_soak_policy("two-days")

    def test_zero_required_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_soak_policy(_policy(required_continuous_hours=0.0))

    def test_an_irradiance_band_reaching_darkness_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_soak_policy(_policy(irradiance_tolerance_fraction=1.0))

    def test_negative_interruption_allowance_rejected(self):
        with self.assertRaises(ValueError):
            validate_soak_policy(_policy(max_interruption_hours=-1.0))

    def test_zero_temperature_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_soak_policy(_policy(temperature_tolerance_c=0.0))


class SegmentTests(unittest.TestCase):
    def test_segment_hours_span_start_to_end(self):
        self.assertAlmostEqual(segment_hours(_segment(0.0, 24.0)), 24.0, places=12)

    def test_a_segment_ending_before_it_starts_is_rejected(self):
        with self.assertRaises(ValueError):
            segment_hours(_segment(24.0, 12.0))

    def test_a_zero_length_segment_is_rejected(self):
        with self.assertRaises(ValueError):
            segment_hours(_segment(12.0, 12.0))

    def test_a_non_mapping_segment_is_rejected(self):
        with self.assertRaises(ValueError):
            segment_hours(24.0)

    def test_an_empty_segment_list_is_rejected(self):
        with self.assertRaises(ValueError):
            ordered_segments([])

    def test_overlapping_segments_are_rejected(self):
        with self.assertRaises(ValueError):
            ordered_segments([_segment(0.0, 24.0), _segment(12.0, 36.0)])

    def test_the_total_sums_every_segment(self):
        self.assertAlmostEqual(
            total_illuminated_hours([_segment(0.0, 24.0), _segment(30.0, 54.0)]),
            48.0,
            places=12,
        )

    def test_gaps_between_segments_are_reported(self):
        gaps = interruption_hours([_segment(0.0, 24.0), _segment(30.0, 54.0)])
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0], 6.0, places=12)

    def test_a_single_segment_has_no_gaps(self):
        self.assertEqual(interruption_hours([_segment(0.0, 48.0)]), ())


class ContinuityTests(unittest.TestCase):
    def test_touching_segments_form_one_continuous_soak(self):
        self.assertAlmostEqual(
            longest_continuous_hours(
                [_segment(0.0, 24.0), _segment(24.0, 48.0)], _policy()
            ),
            48.0,
            places=12,
        )

    def test_a_gap_inside_the_allowance_is_bridged(self):
        policy = _policy(max_interruption_hours=0.25)
        self.assertAlmostEqual(
            longest_continuous_hours(
                [_segment(0.0, 24.0), _segment(24.25, 48.25)], policy
            ),
            48.0,
            places=12,
        )

    def test_a_gap_exactly_at_the_allowance_is_bridged(self):
        policy = _policy(max_interruption_hours=6.0)
        gaps = interruption_hours([_segment(0.0, 24.0), _segment(30.0, 54.0)])
        self.assertAlmostEqual(gaps[0], policy["max_interruption_hours"], places=9)
        self.assertAlmostEqual(
            longest_continuous_hours(
                [_segment(0.0, 24.0), _segment(30.0, 54.0)], policy
            ),
            48.0,
            places=12,
        )

    def test_a_long_gap_breaks_the_chain(self):
        self.assertAlmostEqual(
            longest_continuous_hours(
                [_segment(0.0, 24.0), _segment(200.0, 224.0)], _policy()
            ),
            24.0,
            places=12,
        )

    def test_the_longest_chain_wins_over_an_earlier_one(self):
        self.assertAlmostEqual(
            longest_continuous_hours(
                [
                    _segment(0.0, 10.0),
                    _segment(200.0, 224.0),
                    _segment(224.0, 248.0),
                ],
                _policy(),
            ),
            48.0,
            places=12,
        )


class SimulatorTests(unittest.TestCase):
    def test_plane_spread_is_the_normalised_irradiance_difference(self):
        self.assertAlmostEqual(
            plane_non_uniformity(1100.0, 900.0), 0.1, places=12
        )

    def test_a_flat_plane_has_no_spread(self):
        self.assertAlmostEqual(plane_non_uniformity(1367.0, 1367.0), 0.0, places=12)

    def test_a_min_above_the_max_is_rejected(self):
        with self.assertRaises(ValueError):
            plane_non_uniformity(900.0, 1100.0)

    def test_a_spread_exactly_at_the_allowance_is_uniform(self):
        policy = _policy(max_plane_non_uniformity=0.1)
        self.assertAlmostEqual(
            plane_non_uniformity(1100.0, 900.0),
            policy["max_plane_non_uniformity"],
            places=9,
        )
        self.assertTrue(simulator_plane_uniform(1100.0, 900.0, policy))

    def test_a_wide_spread_is_not_uniform(self):
        self.assertFalse(simulator_plane_uniform(1600.0, 900.0, _policy()))

    def test_a_steady_lamp_is_temporally_stable(self):
        self.assertTrue(simulator_temporally_stable(0.005, _policy()))

    def test_an_instability_exactly_at_the_allowance_is_stable(self):
        policy = _policy()
        self.assertTrue(
            simulator_temporally_stable(policy["max_temporal_instability"], policy)
        )

    def test_a_drifting_lamp_is_not_temporally_stable(self):
        self.assertFalse(simulator_temporally_stable(0.3, _policy()))

    def test_the_reference_irradiance_is_on_reference(self):
        policy = _policy()
        self.assertTrue(
            irradiance_on_reference(policy["reference_irradiance_w_per_m2"], policy)
        )

    def test_an_irradiance_exactly_at_the_band_edge_is_on_reference(self):
        policy = _policy(irradiance_tolerance_fraction=0.05)
        edge = policy["reference_irradiance_w_per_m2"] * 1.05
        self.assertTrue(irradiance_on_reference(edge, policy))

    def test_a_dim_lamp_is_not_on_reference(self):
        self.assertFalse(irradiance_on_reference(600.0, _policy()))

    def test_the_reference_temperature_is_controlled(self):
        self.assertTrue(temperature_controlled(25.0, _policy()))

    def test_a_temperature_exactly_at_the_tolerance_is_controlled(self):
        policy = _policy(temperature_tolerance_c=2.0)
        self.assertAlmostEqual(
            abs(27.0 - policy["reference_temperature_c"]),
            policy["temperature_tolerance_c"],
            places=9,
        )
        self.assertTrue(temperature_controlled(27.0, policy))

    def test_a_hot_segment_is_not_controlled(self):
        self.assertFalse(temperature_controlled(80.0, _policy()))


class CharacterisationTests(unittest.TestCase):
    def test_points_are_grouped_once(self):
        self.assertEqual(
            characterisation_inventory(["pre-soak-iv", "pre-soak-iv"]),
            ("pre-soak-iv",),
        )

    def test_an_unknown_point_is_rejected(self):
        with self.assertRaises(ValueError):
            characterisation_inventory(["mid-orbit-iv"])

    def test_a_bare_string_is_not_a_collection_of_points(self):
        with self.assertRaises(ValueError):
            characterisation_inventory("pre-soak-iv")

    def test_both_mandatory_points_leave_nothing_missing(self):
        self.assertEqual(missing_characterisation_points(POINTS), ())

    def test_a_missing_pre_soak_point_is_named(self):
        self.assertEqual(
            missing_characterisation_points(["post-soak-iv"]), ("pre-soak-iv",)
        )


class RunAssessmentTests(unittest.TestCase):
    def test_a_conforming_two_day_soak_is_recognised(self):
        result = assess_illumination_soak_run(_case())
        self.assertEqual(result["verdict"], ILLUMINATION_SOAK_CONFORMS)
        self.assertEqual(result["findings"], [])

    def test_the_accumulated_and_continuous_hours_are_reported(self):
        result = assess_illumination_soak_run(_case())
        self.assertAlmostEqual(result["total_illuminated_hours"], 48.0, places=12)
        self.assertAlmostEqual(result["longest_continuous_hours"], 48.0, places=12)

    def test_a_soak_exactly_at_the_required_duration_is_met(self):
        result = assess_illumination_soak_run(_case())
        self.assertAlmostEqual(
            result["longest_continuous_hours"],
            result["required_continuous_hours"],
            places=9,
        )
        self.assertTrue(result["duration_met"])

    def test_a_short_soak_is_a_duration_shortfall(self):
        result = assess_illumination_soak_run(
            _case(segments=[_segment(0.0, 12.0)])
        )
        self.assertEqual(result["verdict"], SOAK_DURATION_SHORTFALL)
        self.assertFalse(result["duration_met"])

    def test_two_broken_day_long_soaks_are_not_continuous(self):
        result = assess_illumination_soak_run(
            _case(segments=[_segment(0.0, 24.0), _segment(200.0, 224.0)])
        )
        self.assertEqual(result["verdict"], SOAK_NOT_CONTINUOUS)
        self.assertFalse(result["continuous"])
        self.assertTrue(result["duration_met"])

    def test_a_dim_segment_violates_the_soak_conditions(self):
        result = assess_illumination_soak_run(
            _case(segments=[_segment(0.0, 24.0), _segment(24.0, 48.0, irradiance=600.0)])
        )
        self.assertEqual(result["verdict"], SOAK_CONDITIONS_VIOLATED)
        self.assertFalse(result["conditions_acceptable"])

    def test_a_hot_segment_violates_the_soak_conditions(self):
        result = assess_illumination_soak_run(
            _case(
                segments=[_segment(0.0, 24.0), _segment(24.0, 48.0, temperature=80.0)]
            )
        )
        self.assertEqual(result["verdict"], SOAK_CONDITIONS_VIOLATED)

    def test_a_non_uniform_plane_violates_the_soak_conditions(self):
        case = _case()
        case["simulator"]["plane_max_irradiance_w_per_m2"] = 1600.0
        case["simulator"]["plane_min_irradiance_w_per_m2"] = 900.0
        result = assess_illumination_soak_run(case)
        self.assertEqual(result["verdict"], SOAK_CONDITIONS_VIOLATED)

    def test_a_drifting_lamp_violates_the_soak_conditions(self):
        case = _case()
        case["simulator"]["temporal_instability"] = 0.3
        result = assess_illumination_soak_run(case)
        self.assertEqual(result["verdict"], SOAK_CONDITIONS_VIOLATED)

    def test_a_missing_characterisation_point_is_its_own_verdict(self):
        result = assess_illumination_soak_run(
            _case(characterisation_points=["post-soak-iv"])
        )
        self.assertEqual(result["verdict"], CHARACTERISATION_INCOMPLETE)
        self.assertEqual(result["missing_characterisation_points"], ("pre-soak-iv",))

    def test_every_finding_is_reported_not_only_the_first(self):
        case = _case(characterisation_points=["post-soak-iv"])
        case["simulator"]["temporal_instability"] = 0.3
        case["segments"] = [_segment(0.0, 12.0, temperature=80.0)]
        result = assess_illumination_soak_run(case)
        self.assertEqual(len(result["findings"]), 4)

    def test_absent_characterisation_key_rejected(self):
        case = _case()
        del case["characterisation_points"]
        with self.assertRaises(ValueError):
            assess_illumination_soak_run(case)

    def test_missing_simulator_block_rejected(self):
        case = _case()
        del case["simulator"]
        with self.assertRaises(ValueError):
            assess_illumination_soak_run(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_illumination_soak_run(["segments"])


if __name__ == "__main__":
    unittest.main()
