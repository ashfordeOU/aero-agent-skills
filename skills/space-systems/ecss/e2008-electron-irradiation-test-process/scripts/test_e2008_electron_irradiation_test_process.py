"""Contract tests for the clause 6.4.3.11.2 electron irradiation run logic."""

import math
import unittest

from e2008_electron_irradiation_test_process_logic import (
    CHARACTERISATION_INCOMPLETE,
    DEFAULT_IRRADIATION_POLICY,
    EXPOSURE_FLUENCE_SHORTFALL,
    IRRADIATION_RUN_CONFORMS,
    RUN_CONDITIONS_VIOLATED,
    accumulated_fluence_e_per_cm2,
    assess_electron_irradiation_run,
    beam_energy_on_nominal,
    beam_plane_uniform,
    characterisation_inventory,
    cumulative_fluence_schedule,
    degradation_fraction,
    exposure_duration_s,
    fluence_point_met,
    flux_within_window,
    missing_characterisation_points,
    plane_non_uniformity,
    remaining_power_factor,
    sample_environment_acceptable,
    segment_fluences,
    validate_irradiation_policy,
)

POINTS = ["pre-irradiation-iv", "post-irradiation-iv"]


def _policy(**overrides):
    policy = dict(DEFAULT_IRRADIATION_POLICY)
    policy.update(overrides)
    return policy


def _case(**overrides):
    case = {
        "beam": {
            "energy_mev": 1.0,
            "plane_max_flux_e_per_cm2_s": 1.05e10,
            "plane_min_flux_e_per_cm2_s": 0.95e10,
        },
        "environment": {
            "sample_temperature_c": 25.0,
            "chamber_pressure_pa": 1.0e-4,
        },
        "segments": [
            {"flux_e_per_cm2_s": 1.0e10, "duration_s": 5.0e4},
            {"flux_e_per_cm2_s": 1.0e10, "duration_s": 5.0e4},
        ],
        "planned_fluence_e_per_cm2": 1.0e15,
        "degradation": {
            "coefficient": 0.10,
            "reference_fluence_e_per_cm2": 1.0e13,
        },
        "characterisation_points": list(POINTS),
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_irradiation_policy(DEFAULT_IRRADIATION_POLICY),
            DEFAULT_IRRADIATION_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_irradiation_policy("one-mev")

    def test_inverted_flux_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_irradiation_policy(
                _policy(min_flux_e_per_cm2_s=1.0e11, max_flux_e_per_cm2_s=1.0e9)
            )

    def test_inverted_temperature_window_rejected(self):
        with self.assertRaises(ValueError):
            validate_irradiation_policy(
                _policy(min_sample_temperature_c=30.0, max_sample_temperature_c=20.0)
            )

    def test_negative_fluence_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_irradiation_policy(_policy(fluence_tolerance_fraction=-0.1))


class ExposureTests(unittest.TestCase):
    def test_fluence_is_flux_integrated_over_time(self):
        self.assertAlmostEqual(
            _ratio(accumulated_fluence_e_per_cm2(1.0e10, 5.0e4), 5.0e14),
            1.0,
            places=12,
        )

    def test_exposure_duration_inverts_the_fluence(self):
        self.assertAlmostEqual(
            _ratio(exposure_duration_s(1.0e15, 1.0e10), 1.0e5), 1.0, places=12
        )

    def test_segment_fluences_are_reported_in_run_order(self):
        delivered = segment_fluences(
            [
                {"flux_e_per_cm2_s": 1.0e10, "duration_s": 1.0e4},
                {"flux_e_per_cm2_s": 2.0e10, "duration_s": 1.0e4},
            ]
        )
        self.assertAlmostEqual(_ratio(delivered[0], 1.0e14), 1.0, places=12)
        self.assertAlmostEqual(_ratio(delivered[1], 2.0e14), 1.0, places=12)

    def test_the_schedule_accumulates_across_segments(self):
        schedule = cumulative_fluence_schedule(_case()["segments"])
        self.assertEqual(len(schedule), 2)
        self.assertAlmostEqual(_ratio(schedule[-1], 1.0e15), 1.0, places=12)

    def test_an_empty_segment_list_is_rejected(self):
        with self.assertRaises(ValueError):
            segment_fluences([])

    def test_a_non_mapping_segment_is_rejected(self):
        with self.assertRaises(ValueError):
            segment_fluences([1.0e10])

    def test_zero_duration_segment_rejected(self):
        with self.assertRaises(ValueError):
            accumulated_fluence_e_per_cm2(1.0e10, 0.0)

    def test_boolean_flux_rejected(self):
        with self.assertRaises(ValueError):
            accumulated_fluence_e_per_cm2(True, 5.0e4)


class BeamTests(unittest.TestCase):
    def test_plane_spread_is_the_normalised_flux_difference(self):
        self.assertAlmostEqual(plane_non_uniformity(1.05e10, 0.95e10), 0.05, places=12)

    def test_a_perfectly_flat_plane_has_no_spread(self):
        self.assertAlmostEqual(plane_non_uniformity(1.0e10, 1.0e10), 0.0, places=12)

    def test_a_min_above_the_max_is_rejected(self):
        with self.assertRaises(ValueError):
            plane_non_uniformity(1.0e10, 2.0e10)

    def test_a_spread_exactly_at_the_allowance_is_uniform(self):
        policy = _policy(max_plane_non_uniformity=0.05)
        self.assertAlmostEqual(
            plane_non_uniformity(1.05e10, 0.95e10),
            policy["max_plane_non_uniformity"],
            places=9,
        )
        self.assertTrue(beam_plane_uniform(1.05e10, 0.95e10, policy))

    def test_a_spread_beyond_the_allowance_is_not_uniform(self):
        self.assertFalse(beam_plane_uniform(1.5e10, 0.5e10, _policy()))

    def test_the_nominal_energy_is_on_nominal(self):
        self.assertTrue(beam_energy_on_nominal(1.0, _policy()))

    def test_an_energy_exactly_at_the_tolerance_is_on_nominal(self):
        policy = _policy(beam_energy_tolerance_mev=0.05)
        self.assertAlmostEqual(
            abs(1.05 - policy["beam_energy_nominal_mev"]),
            policy["beam_energy_tolerance_mev"],
            places=9,
        )
        self.assertTrue(beam_energy_on_nominal(1.05, policy))

    def test_a_far_off_energy_is_not_on_nominal(self):
        self.assertFalse(beam_energy_on_nominal(0.5, _policy()))

    def test_a_flux_inside_the_window_is_accepted(self):
        self.assertTrue(flux_within_window(1.0e10, _policy()))

    def test_a_flux_exactly_at_the_window_ceiling_is_accepted(self):
        policy = _policy()
        self.assertTrue(flux_within_window(policy["max_flux_e_per_cm2_s"], policy))

    def test_a_flux_above_the_window_is_refused(self):
        self.assertFalse(flux_within_window(1.0e13, _policy()))

    def test_environment_inside_both_bounds_is_acceptable(self):
        self.assertTrue(sample_environment_acceptable(25.0, 1.0e-4, _policy()))

    def test_a_hot_holder_is_not_acceptable(self):
        self.assertFalse(sample_environment_acceptable(80.0, 1.0e-4, _policy()))

    def test_a_soft_vacuum_is_not_acceptable(self):
        self.assertFalse(sample_environment_acceptable(25.0, 10.0, _policy()))


class DegradationTests(unittest.TestCase):
    def test_zero_fluence_leaves_the_output_undamaged(self):
        self.assertAlmostEqual(remaining_power_factor(0.0, 0.10, 1.0e13), 1.0, places=12)

    def test_the_factor_follows_the_logarithmic_law(self):
        expected = 1.0 - 0.10 * math.log10(1.0 + 1.0e15 / 1.0e13)
        self.assertAlmostEqual(
            remaining_power_factor(1.0e15, 0.10, 1.0e13), expected, places=12
        )

    def test_a_decade_of_fluence_costs_a_fixed_increment(self):
        first = remaining_power_factor(1.0e16, 0.10, 1.0e13)
        second = remaining_power_factor(1.0e17, 0.10, 1.0e13)
        self.assertAlmostEqual(first - second, 0.10, places=3)

    def test_more_fluence_never_leaves_more_output(self):
        self.assertLess(
            remaining_power_factor(1.0e16, 0.10, 1.0e13),
            remaining_power_factor(1.0e15, 0.10, 1.0e13),
        )

    def test_the_factor_is_floored_at_zero(self):
        self.assertAlmostEqual(
            remaining_power_factor(1.0e30, 0.90, 1.0e13), 0.0, places=12
        )

    def test_degradation_complements_the_remaining_factor(self):
        fraction = degradation_fraction(1.0e15, 0.10, 1.0e13)
        factor = remaining_power_factor(1.0e15, 0.10, 1.0e13)
        self.assertAlmostEqual(fraction + factor, 1.0, places=12)

    def test_negative_fluence_rejected(self):
        with self.assertRaises(ValueError):
            remaining_power_factor(-1.0, 0.10, 1.0e13)

    def test_zero_reference_fluence_rejected(self):
        with self.assertRaises(ValueError):
            remaining_power_factor(1.0e15, 0.10, 0.0)


class FluencePointTests(unittest.TestCase):
    def test_the_planned_fluence_is_met_exactly(self):
        self.assertTrue(fluence_point_met(1.0e15, 1.0e15, _policy()))

    def test_a_delivery_exactly_at_the_tolerance_floor_is_met(self):
        policy = _policy(fluence_tolerance_fraction=0.10)
        floor = 1.0e15 * (1.0 - policy["fluence_tolerance_fraction"])
        self.assertAlmostEqual(_ratio(floor, 9.0e14), 1.0, places=12)
        self.assertTrue(fluence_point_met(floor, 1.0e15, policy))

    def test_a_short_delivery_is_not_met(self):
        self.assertFalse(fluence_point_met(1.0e14, 1.0e15, _policy()))

    def test_an_over_delivery_is_met(self):
        self.assertTrue(fluence_point_met(2.0e15, 1.0e15, _policy()))


class CharacterisationTests(unittest.TestCase):
    def test_points_are_grouped_once(self):
        grouped = characterisation_inventory(
            ["pre-irradiation-iv", "pre-irradiation-iv"]
        )
        self.assertEqual(grouped, ("pre-irradiation-iv",))

    def test_an_unknown_point_is_rejected(self):
        with self.assertRaises(ValueError):
            characterisation_inventory(["mid-flight-iv"])

    def test_a_bare_string_is_not_a_collection_of_points(self):
        with self.assertRaises(ValueError):
            characterisation_inventory("pre-irradiation-iv")

    def test_both_mandatory_points_present_leaves_nothing_missing(self):
        self.assertEqual(missing_characterisation_points(POINTS), ())

    def test_a_missing_post_point_is_named(self):
        self.assertEqual(
            missing_characterisation_points(["pre-irradiation-iv"]),
            ("post-irradiation-iv",),
        )


class RunAssessmentTests(unittest.TestCase):
    def test_a_conforming_run_is_recognised(self):
        result = assess_electron_irradiation_run(_case())
        self.assertEqual(result["verdict"], IRRADIATION_RUN_CONFORMS)
        self.assertEqual(result["findings"], [])

    def test_the_delivered_fluence_is_reported(self):
        result = assess_electron_irradiation_run(_case())
        self.assertAlmostEqual(
            _ratio(result["delivered_fluence_e_per_cm2"], 1.0e15), 1.0, places=12
        )

    def test_the_remaining_power_factor_is_reported(self):
        result = assess_electron_irradiation_run(_case())
        expected = 1.0 - 0.10 * math.log10(1.0 + 1.0e15 / 1.0e13)
        self.assertAlmostEqual(result["remaining_power_factor"], expected, places=12)

    def test_an_off_nominal_energy_violates_the_run_conditions(self):
        case = _case()
        case["beam"]["energy_mev"] = 0.5
        result = assess_electron_irradiation_run(case)
        self.assertEqual(result["verdict"], RUN_CONDITIONS_VIOLATED)
        self.assertFalse(result["conditions_acceptable"])

    def test_a_non_uniform_plane_violates_the_run_conditions(self):
        case = _case()
        case["beam"]["plane_min_flux_e_per_cm2_s"] = 0.5e10
        case["beam"]["plane_max_flux_e_per_cm2_s"] = 1.5e10
        result = assess_electron_irradiation_run(case)
        self.assertEqual(result["verdict"], RUN_CONDITIONS_VIOLATED)

    def test_an_over_rate_segment_violates_the_run_conditions(self):
        case = _case()
        case["segments"] = [{"flux_e_per_cm2_s": 1.0e13, "duration_s": 1.0e2}]
        result = assess_electron_irradiation_run(case)
        self.assertEqual(result["verdict"], RUN_CONDITIONS_VIOLATED)

    def test_a_short_run_is_a_fluence_shortfall(self):
        case = _case()
        case["segments"] = [{"flux_e_per_cm2_s": 1.0e10, "duration_s": 1.0e3}]
        result = assess_electron_irradiation_run(case)
        self.assertEqual(result["verdict"], EXPOSURE_FLUENCE_SHORTFALL)
        self.assertFalse(result["fluence_point_met"])

    def test_a_missing_characterisation_point_is_its_own_verdict(self):
        result = assess_electron_irradiation_run(
            _case(characterisation_points=["pre-irradiation-iv"])
        )
        self.assertEqual(result["verdict"], CHARACTERISATION_INCOMPLETE)
        self.assertEqual(
            result["missing_characterisation_points"], ("post-irradiation-iv",)
        )

    def test_every_finding_is_reported_not_only_the_first(self):
        case = _case(characterisation_points=["pre-irradiation-iv"])
        case["beam"]["energy_mev"] = 0.5
        case["segments"] = [{"flux_e_per_cm2_s": 1.0e10, "duration_s": 1.0e3}]
        result = assess_electron_irradiation_run(case)
        self.assertEqual(len(result["findings"]), 3)

    def test_absent_characterisation_key_rejected(self):
        case = _case()
        del case["characterisation_points"]
        with self.assertRaises(ValueError):
            assess_electron_irradiation_run(case)

    def test_missing_beam_block_rejected(self):
        case = _case()
        del case["beam"]
        with self.assertRaises(ValueError):
            assess_electron_irradiation_run(case)

    def test_missing_degradation_block_rejected(self):
        case = _case()
        del case["degradation"]
        with self.assertRaises(ValueError):
            assess_electron_irradiation_run(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_electron_irradiation_run(["beam"])


if __name__ == "__main__":
    unittest.main()
