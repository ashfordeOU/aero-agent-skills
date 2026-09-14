"""Contract tests for the clause 7.5.7.1.2 damp conditioning process logic."""

import math
import unittest

from e2008_solar_cell_humidity_test_process_logic import (
    CONDENSATION_RISK,
    CONDITIONING_ACCEPTED,
    CONDITIONING_DEFICIENT,
    DEFAULT_CONDITIONING_POLICY,
    PLAN_DEFICIENT,
    SUBGROUP_UNDER_TEST,
    absolute_humidity_g_per_m3,
    assess_damp_conditioning,
    dew_point_c,
    dew_point_margin_k,
    partial_vapour_pressure_pa,
    pressure_is_ambient,
    saturation_vapour_pressure_pa,
    subgroup_cell_count,
    validate_conditioning_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_CONDITIONING_POLICY)
    policy.update(overrides)
    return policy


def _profile(**overrides):
    profile = {
        "temperature_c": 60.0,
        "relative_humidity_pct": 85.0,
        "cell_surface_temperature_c": 60.0,
        "chamber_pressure_pa": 101325.0,
        "ramp_rate_k_per_min": 0.5,
        "stabilisation_dwell_min": 60.0,
        "soak_duration_h": 1000.0,
    }
    profile.update(overrides)
    return profile


def _case(**overrides):
    case = {
        "sample_plan": {"subgroup": "O", "cell_count": 6},
        "chamber_profile": _profile(),
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_conditioning_policy(DEFAULT_CONDITIONING_POLICY),
            DEFAULT_CONDITIONING_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_conditioning_policy("ambient")

    def test_a_tolerance_wider_than_ambient_pressure_rejected(self):
        with self.assertRaises(ValueError):
            validate_conditioning_policy(_policy(pressure_tolerance_pa=200000.0))

    def test_zero_dew_point_margin_rejected(self):
        with self.assertRaises(ValueError):
            validate_conditioning_policy(_policy(min_dew_point_margin_k=0.0))

    def test_fractional_minimum_cell_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_conditioning_policy(_policy(min_subgroup_cells=5.5))


class PsychrometryTests(unittest.TestCase):
    def test_saturation_pressure_follows_the_magnus_form(self):
        expected = 610.94 * math.exp(17.625 * 60.0 / (243.04 + 60.0))
        self.assertAlmostEqual(
            _ratio(saturation_vapour_pressure_pa(60.0), expected), 1.0, places=12
        )

    def test_saturation_pressure_rises_with_temperature(self):
        self.assertLess(
            saturation_vapour_pressure_pa(20.0), saturation_vapour_pressure_pa(60.0)
        )

    def test_partial_pressure_scales_with_relative_humidity(self):
        half = partial_vapour_pressure_pa(60.0, 50.0)
        full = partial_vapour_pressure_pa(60.0, 100.0)
        self.assertAlmostEqual(_ratio(full, 2.0 * half), 1.0, places=12)

    def test_saturated_air_dews_at_its_own_temperature(self):
        self.assertAlmostEqual(dew_point_c(60.0, 100.0), 60.0, places=9)

    def test_drier_air_dews_lower(self):
        self.assertLess(dew_point_c(60.0, 40.0), dew_point_c(60.0, 85.0))

    def test_dew_point_stays_below_the_air_temperature(self):
        self.assertLess(dew_point_c(60.0, 85.0), 60.0)

    def test_absolute_humidity_grows_with_relative_humidity(self):
        self.assertLess(
            absolute_humidity_g_per_m3(60.0, 40.0),
            absolute_humidity_g_per_m3(60.0, 85.0),
        )

    def test_margin_is_the_surface_above_the_dew_point(self):
        dew = dew_point_c(60.0, 85.0)
        self.assertAlmostEqual(
            dew_point_margin_k(dew + 4.0, 60.0, 85.0), 4.0, places=9
        )

    def test_a_surface_below_the_dew_point_gives_a_negative_margin(self):
        dew = dew_point_c(60.0, 85.0)
        self.assertLess(dew_point_margin_k(dew - 1.0, 60.0, 85.0), 0.0)

    def test_humidity_above_one_hundred_per_cent_rejected(self):
        with self.assertRaises(ValueError):
            dew_point_c(60.0, 130.0)

    def test_zero_humidity_rejected(self):
        with self.assertRaises(ValueError):
            dew_point_c(60.0, 0.0)

    def test_a_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            saturation_vapour_pressure_pa(-300.0)


class SamplePlanTests(unittest.TestCase):
    def test_the_subgroup_under_test_is_counted(self):
        self.assertEqual(
            subgroup_cell_count({"subgroup": SUBGROUP_UNDER_TEST, "cell_count": 6}), 6
        )

    def test_a_lower_case_subgroup_label_still_counts(self):
        self.assertEqual(subgroup_cell_count({"subgroup": "o", "cell_count": 6}), 6)

    def test_another_subgroup_contributes_nothing(self):
        self.assertEqual(subgroup_cell_count({"subgroup": "D", "cell_count": 6}), 0)

    def test_a_missing_subgroup_label_rejected(self):
        with self.assertRaises(ValueError):
            subgroup_cell_count({"cell_count": 6})

    def test_a_fractional_cell_count_rejected(self):
        with self.assertRaises(ValueError):
            subgroup_cell_count({"subgroup": "O", "cell_count": 6.5})

    def test_a_non_mapping_sample_plan_rejected(self):
        with self.assertRaises(ValueError):
            subgroup_cell_count(["O", 6])


class PressureTests(unittest.TestCase):
    def test_the_ambient_setpoint_is_ambient(self):
        self.assertTrue(pressure_is_ambient(101325.0, _policy()))

    def test_a_pressure_exactly_at_the_tolerance_edge_is_ambient(self):
        policy = _policy()
        edge = policy["ambient_pressure_pa"] + policy["pressure_tolerance_pa"]
        self.assertAlmostEqual(
            abs(edge - policy["ambient_pressure_pa"]),
            policy["pressure_tolerance_pa"],
            places=9,
        )
        self.assertTrue(pressure_is_ambient(edge, policy))

    def test_a_pressurised_chamber_is_not_ambient(self):
        self.assertFalse(pressure_is_ambient(250000.0, _policy()))

    def test_a_pumped_down_chamber_is_not_ambient(self):
        self.assertFalse(pressure_is_ambient(20000.0, _policy()))

    def test_zero_pressure_rejected(self):
        with self.assertRaises(ValueError):
            pressure_is_ambient(0.0, _policy())


class ConditioningAssessmentTests(unittest.TestCase):
    def test_a_nominal_profile_is_accepted(self):
        result = assess_damp_conditioning(_case())
        self.assertEqual(result["verdict"], CONDITIONING_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_the_dew_point_and_margin_are_reported(self):
        result = assess_damp_conditioning(_case())
        expected = dew_point_c(60.0, 85.0)
        self.assertAlmostEqual(_ratio(result["dew_point_c"], expected), 1.0,
                               places=12)
        self.assertAlmostEqual(
            _ratio(result["dew_point_margin_k"], 60.0 - expected), 1.0, places=12
        )

    def test_a_cold_cell_surface_is_a_condensation_risk(self):
        dew = dew_point_c(60.0, 85.0)
        result = assess_damp_conditioning(
            _case(chamber_profile=_profile(cell_surface_temperature_c=dew - 2.0))
        )
        self.assertEqual(result["verdict"], CONDENSATION_RISK)
        self.assertLess(result["dew_point_margin_k"], 0.0)

    def test_a_margin_exactly_at_the_floor_is_accepted(self):
        policy = _policy()
        dew = dew_point_c(60.0, 85.0)
        surface = dew + policy["min_dew_point_margin_k"]
        result = assess_damp_conditioning(
            _case(chamber_profile=_profile(cell_surface_temperature_c=surface)),
            policy,
        )
        self.assertAlmostEqual(
            result["dew_point_margin_k"], policy["min_dew_point_margin_k"], places=9
        )
        self.assertEqual(result["verdict"], CONDITIONING_ACCEPTED)

    def test_condensation_outranks_a_short_sample(self):
        dew = dew_point_c(60.0, 85.0)
        case = _case(
            sample_plan={"subgroup": "O", "cell_count": 1},
            chamber_profile=_profile(cell_surface_temperature_c=dew - 2.0),
        )
        result = assess_damp_conditioning(case)
        self.assertEqual(result["verdict"], CONDENSATION_RISK)
        self.assertEqual(len(result["findings"]), 2)

    def test_too_few_subgroup_cells_is_a_plan_deficiency(self):
        result = assess_damp_conditioning(
            _case(sample_plan={"subgroup": "O", "cell_count": 2})
        )
        self.assertEqual(result["verdict"], PLAN_DEFICIENT)

    def test_cells_drawn_from_another_subgroup_do_not_fill_the_plan(self):
        result = assess_damp_conditioning(
            _case(sample_plan={"subgroup": "D", "cell_count": 12})
        )
        self.assertEqual(result["verdict"], PLAN_DEFICIENT)
        self.assertEqual(result["subgroup_cells"], 0)

    def test_a_sample_count_exactly_at_the_floor_is_accepted(self):
        policy = _policy()
        result = assess_damp_conditioning(
            _case(
                sample_plan={
                    "subgroup": "O",
                    "cell_count": int(policy["min_subgroup_cells"]),
                }
            ),
            policy,
        )
        self.assertEqual(result["verdict"], CONDITIONING_ACCEPTED)

    def test_a_pressurised_chamber_is_a_conditioning_deficiency(self):
        result = assess_damp_conditioning(
            _case(chamber_profile=_profile(chamber_pressure_pa=300000.0))
        )
        self.assertEqual(result["verdict"], CONDITIONING_DEFICIENT)
        self.assertFalse(result["pressure_ambient"])

    def test_a_fast_ramp_is_a_conditioning_deficiency(self):
        result = assess_damp_conditioning(
            _case(chamber_profile=_profile(ramp_rate_k_per_min=5.0))
        )
        self.assertEqual(result["verdict"], CONDITIONING_DEFICIENT)

    def test_a_short_stabilisation_dwell_is_a_conditioning_deficiency(self):
        result = assess_damp_conditioning(
            _case(chamber_profile=_profile(stabilisation_dwell_min=5.0))
        )
        self.assertEqual(result["verdict"], CONDITIONING_DEFICIENT)

    def test_a_truncated_soak_is_a_conditioning_deficiency(self):
        result = assess_damp_conditioning(
            _case(chamber_profile=_profile(soak_duration_h=200.0))
        )
        self.assertEqual(result["verdict"], CONDITIONING_DEFICIENT)

    def test_every_profile_finding_is_reported_not_only_the_first(self):
        result = assess_damp_conditioning(
            _case(
                chamber_profile=_profile(
                    chamber_pressure_pa=300000.0,
                    ramp_rate_k_per_min=5.0,
                    stabilisation_dwell_min=5.0,
                    soak_duration_h=200.0,
                )
            )
        )
        self.assertEqual(len(result["findings"]), 4)

    def test_missing_sample_plan_rejected(self):
        case = _case()
        del case["sample_plan"]
        with self.assertRaises(ValueError):
            assess_damp_conditioning(case)

    def test_missing_chamber_profile_rejected(self):
        case = _case()
        del case["chamber_profile"]
        with self.assertRaises(ValueError):
            assess_damp_conditioning(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_damp_conditioning(["sample_plan"])

    def test_a_negative_soak_duration_rejected(self):
        with self.assertRaises(ValueError):
            assess_damp_conditioning(
                _case(chamber_profile=_profile(soak_duration_h=-10.0))
            )


if __name__ == "__main__":
    unittest.main()
