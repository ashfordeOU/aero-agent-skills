"""Contract tests for the ECSS-Q-ST-70-29 exposure-condition logic."""

import unittest

from q7029_exposure_conditions_logic import (
    DIRECTION_COLD,
    DIRECTION_HOT,
    ENV_NITROGEN,
    ENV_VACUUM,
    VERDICT_ACCEPTED,
    VERDICT_REJECTED,
    accumulate_dwell,
    evaluate_exposure,
    group_excursions,
    in_band,
    stabilisation_index,
    validate_environment,
    validate_profile,
    validate_setpoint,
)

SETPOINT = validate_setpoint(50.0, 2.0, 72.0)

# Two-hour ramp, then a clean 72 h soak at the set point.
CLEAN_PROFILE = [(0.0, 22.0), (1.0, 38.0), (2.0, 50.0), (38.0, 50.4), (74.0, 49.6)]


def vacuum_spec(**over):
    spec = {
        "temperature_c": 50.0,
        "tolerance_c": 2.0,
        "dwell_h": 72.0,
        "profile": list(CLEAN_PROFILE),
        "environment": ENV_VACUUM,
        "pressure_pa": 1.0e-3,
        "pressure_ceiling_pa": 1.0e-2,
    }
    spec.update(over)
    return spec


def purge_spec(**over):
    spec = {
        "temperature_c": 50.0,
        "tolerance_c": 2.0,
        "dwell_h": 72.0,
        "profile": list(CLEAN_PROFILE),
        "environment": ENV_NITROGEN,
        "purge_flow_l_per_min": 4.0,
        "min_flow_l_per_min": 2.0,
        "purity_fraction": 0.9999,
        "min_purity_fraction": 0.999,
    }
    spec.update(over)
    return spec


class SetpointTests(unittest.TestCase):
    def test_valid_setpoint_is_normalised(self):
        sp = validate_setpoint(50, 2, 72)
        self.assertAlmostEqual(sp["temperature_c"], 50.0, places=9)
        self.assertAlmostEqual(sp["tolerance_c"], 2.0, places=9)
        self.assertAlmostEqual(sp["dwell_h"], 72.0, places=9)

    def test_zero_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_setpoint(50.0, 0.0, 72.0)

    def test_zero_dwell_rejected(self):
        with self.assertRaises(ValueError):
            validate_setpoint(50.0, 2.0, 0.0)

    def test_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_setpoint(-300.0, 2.0, 72.0)

    def test_boolean_temperature_rejected(self):
        with self.assertRaises(ValueError):
            validate_setpoint(True, 2.0, 72.0)


class EnvironmentTests(unittest.TestCase):
    def test_unknown_environment_rejected(self):
        with self.assertRaises(ValueError):
            validate_environment("argon", pressure_pa=1.0, pressure_ceiling_pa=2.0)

    def test_vacuum_below_ceiling_conforms(self):
        rec = validate_environment(ENV_VACUUM, pressure_pa=1e-3, pressure_ceiling_pa=1e-2)
        self.assertTrue(rec["conforming"])
        self.assertEqual(rec["findings"], [])

    def test_vacuum_above_ceiling_is_a_finding_not_an_error(self):
        rec = validate_environment(ENV_VACUUM, pressure_pa=5e-2, pressure_ceiling_pa=1e-2)
        self.assertFalse(rec["conforming"])
        self.assertEqual(len(rec["findings"]), 1)

    def test_vacuum_pressure_exactly_on_the_ceiling_conforms(self):
        rec = validate_environment(ENV_VACUUM, pressure_pa=0.01, pressure_ceiling_pa=0.01)
        self.assertTrue(rec["conforming"])

    def test_vacuum_missing_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            validate_environment(ENV_VACUUM, pressure_pa=1e-3)

    def test_purge_below_flow_floor_is_a_finding(self):
        rec = validate_environment(
            ENV_NITROGEN,
            purge_flow_l_per_min=1.0,
            min_flow_l_per_min=2.0,
            purity_fraction=0.9999,
            min_purity_fraction=0.999,
        )
        self.assertFalse(rec["conforming"])

    def test_purge_below_purity_floor_is_a_finding(self):
        rec = validate_environment(
            ENV_NITROGEN,
            purge_flow_l_per_min=4.0,
            min_flow_l_per_min=2.0,
            purity_fraction=0.99,
            min_purity_fraction=0.999,
        )
        self.assertFalse(rec["conforming"])

    def test_purity_above_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_environment(
                ENV_NITROGEN,
                purge_flow_l_per_min=4.0,
                min_flow_l_per_min=2.0,
                purity_fraction=1.4,
                min_purity_fraction=0.999,
            )

    def test_purge_missing_purity_rejected(self):
        with self.assertRaises(ValueError):
            validate_environment(
                ENV_NITROGEN, purge_flow_l_per_min=4.0, min_flow_l_per_min=2.0
            )


class ProfileTests(unittest.TestCase):
    def test_valid_profile_is_returned(self):
        self.assertEqual(len(validate_profile(CLEAN_PROFILE)), 5)

    def test_single_sample_profile_rejected(self):
        with self.assertRaises(ValueError):
            validate_profile([(0.0, 22.0)])

    def test_non_monotone_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_profile([(0.0, 22.0), (0.0, 30.0)])

    def test_negative_time_rejected(self):
        with self.assertRaises(ValueError):
            validate_profile([(-1.0, 22.0), (1.0, 30.0)])

    def test_malformed_sample_rejected(self):
        with self.assertRaises(ValueError):
            validate_profile([(0.0, 22.0), (1.0,)])


class BandTests(unittest.TestCase):
    def test_sample_inside_band(self):
        self.assertTrue(in_band(51.0, SETPOINT))

    def test_sample_exactly_on_the_band_edge_is_inside(self):
        self.assertTrue(in_band(52.0, SETPOINT))

    def test_sample_outside_band(self):
        self.assertFalse(in_band(47.0, SETPOINT))

    def test_stabilisation_is_the_first_in_band_sample(self):
        self.assertEqual(stabilisation_index(validate_profile(CLEAN_PROFILE), SETPOINT), 2)

    def test_profile_never_in_band_has_no_stabilisation(self):
        cold = validate_profile([(0.0, 20.0), (5.0, 21.0), (9.0, 22.0)])
        self.assertIsNone(stabilisation_index(cold, SETPOINT))


class DwellTests(unittest.TestCase):
    def test_clean_soak_credits_the_whole_span(self):
        profile = validate_profile(CLEAN_PROFILE)
        effective, out = accumulate_dwell(profile, SETPOINT, 2)
        self.assertAlmostEqual(effective, 72.0, places=9)
        self.assertEqual(out, [])

    def test_ramp_is_not_credited(self):
        profile = validate_profile(CLEAN_PROFILE)
        effective, _ = accumulate_dwell(profile, SETPOINT, 2)
        span = profile[-1][0] - profile[0][0]
        self.assertAlmostEqual(span - effective, 2.0, places=9)

    def test_dip_is_charged_in_full(self):
        profile = validate_profile(
            [(0.0, 50.0), (10.0, 50.0), (12.0, 40.0), (14.0, 50.0), (24.0, 50.0)]
        )
        effective, out = accumulate_dwell(profile, SETPOINT, 0)
        self.assertAlmostEqual(effective, 20.0, places=9)
        self.assertEqual(len(out), 2)

    def test_start_index_beyond_profile_rejected(self):
        profile = validate_profile(CLEAN_PROFILE)
        with self.assertRaises(ValueError):
            accumulate_dwell(profile, SETPOINT, len(profile) - 1)

    def test_boolean_start_index_rejected(self):
        profile = validate_profile(CLEAN_PROFILE)
        with self.assertRaises(ValueError):
            accumulate_dwell(profile, SETPOINT, True)


class ExcursionTests(unittest.TestCase):
    def test_contiguous_intervals_group_into_one_excursion(self):
        profile = validate_profile(
            [(0.0, 50.0), (10.0, 50.0), (12.0, 40.0), (14.0, 41.0), (16.0, 50.0), (80.0, 50.0)]
        )
        _, out = accumulate_dwell(profile, SETPOINT, 0)
        excursions = group_excursions(out, SETPOINT)
        self.assertEqual(len(excursions), 1)
        self.assertAlmostEqual(excursions[0]["duration_h"], 6.0, places=9)
        self.assertEqual(excursions[0]["direction"], DIRECTION_COLD)

    def test_separated_dips_stay_separate_excursions(self):
        profile = validate_profile(
            [
                (0.0, 50.0), (10.0, 50.0), (12.0, 40.0), (14.0, 50.0),
                (30.0, 50.0), (32.0, 40.0), (34.0, 50.0), (90.0, 50.0),
            ]
        )
        _, out = accumulate_dwell(profile, SETPOINT, 0)
        self.assertEqual(len(group_excursions(out, SETPOINT)), 2)

    def test_hot_excursion_is_labelled_above_band(self):
        profile = validate_profile([(0.0, 50.0), (10.0, 50.0), (12.0, 70.0), (14.0, 50.0)])
        _, out = accumulate_dwell(profile, SETPOINT, 0)
        excursions = group_excursions(out, SETPOINT)
        self.assertEqual(excursions[0]["direction"], DIRECTION_HOT)
        self.assertAlmostEqual(excursions[0]["peak_deviation_c"], 20.0, places=9)

    def test_no_out_of_band_intervals_give_no_excursions(self):
        self.assertEqual(group_excursions([], SETPOINT), [])


class EvaluateExposureTests(unittest.TestCase):
    def test_clean_vacuum_run_is_accepted(self):
        result = evaluate_exposure(vacuum_spec())
        self.assertEqual(result["verdict"], VERDICT_ACCEPTED)
        self.assertAlmostEqual(result["effective_dwell_h"], 72.0, places=9)
        self.assertAlmostEqual(result["dwell_shortfall_h"], 0.0, places=9)

    def test_dwell_exactly_on_the_requirement_is_accepted(self):
        result = evaluate_exposure(vacuum_spec(dwell_h=72.0))
        self.assertAlmostEqual(result["effective_dwell_h"], result["setpoint"]["dwell_h"], places=9)
        self.assertEqual(result["verdict"], VERDICT_ACCEPTED)

    def test_clean_purge_run_is_accepted(self):
        self.assertEqual(evaluate_exposure(purge_spec())["verdict"], VERDICT_ACCEPTED)

    def test_ramp_credited_run_would_have_passed_but_does_not(self):
        short = [(0.0, 22.0), (1.0, 38.0), (2.0, 50.0), (40.0, 50.2), (72.0, 49.8)]
        result = evaluate_exposure(vacuum_spec(profile=short))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertAlmostEqual(result["effective_dwell_h"], 70.0, places=9)
        self.assertAlmostEqual(result["dwell_shortfall_h"], 2.0, places=9)

    def test_pressure_above_ceiling_rejects_an_otherwise_clean_run(self):
        result = evaluate_exposure(vacuum_spec(pressure_pa=1.0))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertAlmostEqual(result["effective_dwell_h"], 72.0, places=9)

    def test_hot_excursion_rejects_the_run(self):
        hot = [(0.0, 50.0), (30.0, 50.0), (32.0, 75.0), (34.0, 50.0), (110.0, 50.0)]
        result = evaluate_exposure(vacuum_spec(profile=hot))
        self.assertEqual(result["verdict"], VERDICT_REJECTED)
        self.assertEqual(result["hot_excursion_count"], 1)

    def test_profile_never_in_band_credits_no_dwell(self):
        cold = [(0.0, 20.0), (40.0, 21.0), (80.0, 22.0)]
        result = evaluate_exposure(vacuum_spec(profile=cold))
        self.assertIsNone(result["stabilisation_h"])
        self.assertAlmostEqual(result["effective_dwell_h"], 0.0, places=9)
        self.assertEqual(result["verdict"], VERDICT_REJECTED)

    def test_long_stabilisation_is_reported(self):
        slow = [(0.0, 22.0), (60.0, 35.0), (90.0, 50.0), (150.0, 50.0)]
        result = evaluate_exposure(vacuum_spec(profile=slow))
        self.assertTrue(
            any("stabilisation consumed" in f for f in result["findings"])
        )

    def test_missing_spec_key_rejected(self):
        spec = vacuum_spec()
        del spec["dwell_h"]
        with self.assertRaises(ValueError):
            evaluate_exposure(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_exposure(["temperature_c"])

    def test_excursion_count_and_longest_are_both_reported(self):
        wobbly = [
            (0.0, 50.0), (10.0, 50.0), (12.0, 40.0), (14.0, 50.0),
            (30.0, 50.0), (38.0, 40.0), (40.0, 50.0), (110.0, 50.0),
        ]
        result = evaluate_exposure(vacuum_spec(profile=wobbly))
        self.assertEqual(result["excursion_count"], 2)
        self.assertAlmostEqual(result["longest_excursion_h"], 10.0, places=9)


if __name__ == "__main__":
    unittest.main()
