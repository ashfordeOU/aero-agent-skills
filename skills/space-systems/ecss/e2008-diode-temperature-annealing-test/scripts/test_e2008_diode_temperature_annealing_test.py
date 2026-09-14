"""Contract tests for the clause 9.6.13 diode annealing stability logic."""

import math
import unittest

from e2008_diode_temperature_annealing_test_logic import (
    ANNEALING_PARAMETER_INSTABILITY,
    ANNEALING_SAMPLE_PLAN_DEFICIENT,
    ANNEALING_SOAK_PROFILE_DEFICIENT,
    ANNEALING_STABILITY_ACCEPTED,
    ANNEALING_SUBGROUP,
    ANNEALING_VERDICTS,
    BOLTZMANN_EV_PER_K,
    DEFAULT_DIODE_ANNEALING_POLICY,
    arrhenius_acceleration_factor,
    assess_diode_annealing,
    equivalent_reference_hours,
    measurement_temperature_delta_k,
    relative_parameter_drift,
    reverse_leakage_growth_ratio,
    soak_within_package_rating,
    subgroup_diode_count,
    validate_annealing_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_DIODE_ANNEALING_POLICY)
    policy.update(overrides)
    return policy


def _soak(**overrides):
    soak = {
        "soak_temperature_c": 150.0,
        "soak_duration_h": 1000.0,
        "max_rated_temperature_c": 175.0,
        "recovery_dwell_h": 4.0,
    }
    soak.update(overrides)
    return soak


def _before(**overrides):
    before = {
        "measurement_temperature_c": 25.0,
        "forward_voltage_v": 0.520,
        "reverse_leakage_a": 1.0e-9,
        "blocking_voltage_v": 60.0,
    }
    before.update(overrides)
    return before


def _after(**overrides):
    after = {
        "measurement_temperature_c": 25.0,
        "forward_voltage_v": 0.523,
        "reverse_leakage_a": 2.0e-9,
        "blocking_voltage_v": 59.8,
    }
    after.update(overrides)
    return after


def _case(**overrides):
    case = {
        "sample_plan": {"subgroup": ANNEALING_SUBGROUP, "diode_count": 6},
        "soak": _soak(),
        "before": _before(),
        "after": _after(),
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_annealing_policy(DEFAULT_DIODE_ANNEALING_POLICY),
            DEFAULT_DIODE_ANNEALING_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_annealing_policy("anneal")

    def test_a_reference_hotter_than_the_soak_rejected(self):
        with self.assertRaises(ValueError):
            validate_annealing_policy(_policy(reference_temperature_c=200.0))

    def test_a_leakage_growth_ceiling_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_annealing_policy(_policy(max_reverse_leakage_growth_ratio=1.0))

    def test_a_drift_ceiling_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_annealing_policy(
                _policy(max_forward_voltage_drift_fraction=1.0)
            )

    def test_a_fractional_minimum_device_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_annealing_policy(_policy(min_subgroup_diodes=5.5))

    def test_a_negative_activation_energy_rejected(self):
        with self.assertRaises(ValueError):
            validate_annealing_policy(_policy(activation_energy_ev=-0.7))

    def test_every_verdict_is_declared(self):
        self.assertEqual(len(set(ANNEALING_VERDICTS)), 4)


class ArrheniusTests(unittest.TestCase):
    def test_the_factor_follows_the_arrhenius_form(self):
        expected = math.exp(
            (0.7 / BOLTZMANN_EV_PER_K)
            * ((1.0 / (25.0 + 273.15)) - (1.0 / (150.0 + 273.15)))
        )
        self.assertAlmostEqual(
            _ratio(arrhenius_acceleration_factor(150.0, 25.0, 0.7), expected),
            1.0,
            places=12,
        )

    def test_a_soak_at_the_reference_accelerates_nothing(self):
        self.assertAlmostEqual(
            arrhenius_acceleration_factor(25.0, 25.0, 0.7), 1.0, places=9
        )

    def test_a_hotter_soak_accelerates_more(self):
        cool = arrhenius_acceleration_factor(100.0, 25.0, 0.7)
        hot = arrhenius_acceleration_factor(150.0, 25.0, 0.7)
        self.assertGreater(hot, cool * 2.0)

    def test_a_larger_activation_energy_accelerates_more(self):
        low = arrhenius_acceleration_factor(150.0, 25.0, 0.4)
        high = arrhenius_acceleration_factor(150.0, 25.0, 0.9)
        self.assertGreater(high, low * 2.0)

    def test_equivalent_hours_scale_with_the_soak_duration(self):
        single = equivalent_reference_hours(100.0, 150.0, 25.0, 0.7)
        double = equivalent_reference_hours(200.0, 150.0, 25.0, 0.7)
        self.assertAlmostEqual(_ratio(double, single), 2.0, places=9)

    def test_equivalent_hours_are_the_duration_times_the_factor(self):
        factor = arrhenius_acceleration_factor(150.0, 25.0, 0.7)
        self.assertAlmostEqual(
            _ratio(
                equivalent_reference_hours(1000.0, 150.0, 25.0, 0.7),
                1000.0 * factor,
            ),
            1.0,
            places=12,
        )

    def test_a_soak_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            arrhenius_acceleration_factor(-300.0, 25.0, 0.7)

    def test_a_zero_soak_duration_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_reference_hours(0.0, 150.0, 25.0, 0.7)

    def test_a_boolean_duration_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_reference_hours(True, 150.0, 25.0, 0.7)


class DriftTests(unittest.TestCase):
    def test_drift_is_the_move_as_a_share_of_the_start(self):
        self.assertAlmostEqual(
            relative_parameter_drift(0.500, 0.525), 0.05, places=9
        )

    def test_drift_is_unsigned(self):
        self.assertAlmostEqual(
            relative_parameter_drift(0.500, 0.475),
            relative_parameter_drift(0.500, 0.525),
            places=9,
        )

    def test_an_unchanged_parameter_has_no_drift(self):
        self.assertAlmostEqual(relative_parameter_drift(0.52, 0.52), 0.0, places=12)

    def test_a_zero_starting_value_rejected(self):
        with self.assertRaises(ValueError):
            relative_parameter_drift(0.0, 0.1)

    def test_leakage_growth_is_a_ratio_not_a_percentage(self):
        self.assertAlmostEqual(
            reverse_leakage_growth_ratio(1.0e-9, 5.0e-9), 5.0, places=9
        )

    def test_leakage_that_fell_gives_a_ratio_below_one(self):
        self.assertLess(reverse_leakage_growth_ratio(4.0e-9, 1.0e-9), 1.0)

    def test_a_zero_leakage_reading_rejected(self):
        with self.assertRaises(ValueError):
            reverse_leakage_growth_ratio(0.0, 1.0e-9)

    def test_the_reading_temperature_gap_is_unsigned(self):
        self.assertAlmostEqual(measurement_temperature_delta_k(25.0, 31.0), 6.0, places=9)
        self.assertAlmostEqual(measurement_temperature_delta_k(31.0, 25.0), 6.0, places=9)

    def test_a_reading_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            measurement_temperature_delta_k(25.0, -400.0)


class PackageRatingTests(unittest.TestCase):
    def test_a_soak_under_the_rating_is_within_it(self):
        self.assertTrue(soak_within_package_rating(150.0, 175.0))

    def test_a_soak_exactly_at_the_rating_is_within_it(self):
        self.assertTrue(soak_within_package_rating(175.0, 175.0))

    def test_a_soak_above_the_rating_is_not(self):
        self.assertFalse(soak_within_package_rating(200.0, 175.0))


class SamplePlanTests(unittest.TestCase):
    def test_the_subgroup_under_test_is_counted(self):
        self.assertEqual(
            subgroup_diode_count(
                {"subgroup": ANNEALING_SUBGROUP, "diode_count": 6}
            ),
            6,
        )

    def test_a_lower_case_subgroup_label_still_counts(self):
        self.assertEqual(
            subgroup_diode_count(
                {"subgroup": ANNEALING_SUBGROUP.lower(), "diode_count": 6}
            ),
            6,
        )

    def test_another_subgroup_contributes_nothing(self):
        self.assertEqual(subgroup_diode_count({"subgroup": "B", "diode_count": 9}), 0)

    def test_a_missing_subgroup_label_rejected(self):
        with self.assertRaises(ValueError):
            subgroup_diode_count({"diode_count": 6})

    def test_a_non_mapping_sample_plan_rejected(self):
        with self.assertRaises(ValueError):
            subgroup_diode_count([ANNEALING_SUBGROUP, 6])


class AnnealingAssessmentTests(unittest.TestCase):
    def test_a_nominal_anneal_is_accepted(self):
        result = assess_diode_annealing(_case())
        self.assertEqual(result["verdict"], ANNEALING_STABILITY_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_the_acceleration_and_equivalent_hours_are_reported(self):
        result = assess_diode_annealing(_case())
        factor = arrhenius_acceleration_factor(150.0, 25.0, 0.7)
        self.assertAlmostEqual(
            _ratio(result["acceleration_factor"], factor), 1.0, places=12
        )
        self.assertAlmostEqual(
            _ratio(result["equivalent_reference_hours"], 1000.0 * factor),
            1.0,
            places=12,
        )

    def test_a_forward_voltage_that_walked_is_an_instability(self):
        result = assess_diode_annealing(
            _case(after=_after(forward_voltage_v=0.620))
        )
        self.assertEqual(result["verdict"], ANNEALING_PARAMETER_INSTABILITY)

    def test_a_drift_exactly_on_the_ceiling_is_accepted(self):
        policy = _policy()
        base = 0.520
        limit = policy["max_forward_voltage_drift_fraction"]
        result = assess_diode_annealing(
            _case(after=_after(forward_voltage_v=base * (1.0 + limit))), policy
        )
        self.assertAlmostEqual(
            result["forward_voltage_drift_fraction"], limit, places=9
        )
        self.assertEqual(result["verdict"], ANNEALING_STABILITY_ACCEPTED)

    def test_runaway_reverse_leakage_is_an_instability(self):
        result = assess_diode_annealing(
            _case(after=_after(reverse_leakage_a=1.0e-6))
        )
        self.assertEqual(result["verdict"], ANNEALING_PARAMETER_INSTABILITY)
        self.assertGreater(result["reverse_leakage_growth_ratio"], 10.0)

    def test_a_leakage_ratio_exactly_on_the_ceiling_is_accepted(self):
        policy = _policy()
        result = assess_diode_annealing(
            _case(
                after=_after(
                    reverse_leakage_a=1.0e-9
                    * policy["max_reverse_leakage_growth_ratio"]
                )
            ),
            policy,
        )
        self.assertAlmostEqual(
            result["reverse_leakage_growth_ratio"],
            policy["max_reverse_leakage_growth_ratio"],
            places=9,
        )
        self.assertEqual(result["verdict"], ANNEALING_STABILITY_ACCEPTED)

    def test_a_collapsed_blocking_voltage_is_an_instability(self):
        result = assess_diode_annealing(
            _case(after=_after(blocking_voltage_v=40.0))
        )
        self.assertEqual(result["verdict"], ANNEALING_PARAMETER_INSTABILITY)

    def test_readings_taken_at_different_temperatures_outrank_the_drift(self):
        result = assess_diode_annealing(
            _case(
                after=_after(measurement_temperature_c=85.0, forward_voltage_v=0.620)
            )
        )
        self.assertEqual(result["verdict"], ANNEALING_SOAK_PROFILE_DEFICIENT)
        self.assertAlmostEqual(
            result["measurement_temperature_delta_k"], 60.0, places=9
        )

    def test_a_reading_gap_exactly_on_the_ceiling_is_accepted(self):
        policy = _policy()
        gap = policy["max_measurement_temperature_delta_k"]
        result = assess_diode_annealing(
            _case(after=_after(measurement_temperature_c=25.0 + gap)), policy
        )
        self.assertAlmostEqual(
            result["measurement_temperature_delta_k"], gap, places=9
        )
        self.assertEqual(result["verdict"], ANNEALING_STABILITY_ACCEPTED)

    def test_too_few_subgroup_diodes_is_a_plan_deficiency(self):
        result = assess_diode_annealing(
            _case(sample_plan={"subgroup": ANNEALING_SUBGROUP, "diode_count": 2})
        )
        self.assertEqual(result["verdict"], ANNEALING_SAMPLE_PLAN_DEFICIENT)

    def test_diodes_drawn_from_another_subgroup_do_not_fill_the_plan(self):
        result = assess_diode_annealing(
            _case(sample_plan={"subgroup": "B", "diode_count": 40})
        )
        self.assertEqual(result["verdict"], ANNEALING_SAMPLE_PLAN_DEFICIENT)
        self.assertEqual(result["subgroup_diodes"], 0)

    def test_an_instability_outranks_a_short_sample(self):
        result = assess_diode_annealing(
            _case(
                sample_plan={"subgroup": ANNEALING_SUBGROUP, "diode_count": 2},
                after=_after(forward_voltage_v=0.700),
            )
        )
        self.assertEqual(result["verdict"], ANNEALING_PARAMETER_INSTABILITY)

    def test_a_sample_count_exactly_at_the_floor_is_accepted(self):
        policy = _policy()
        floor = int(policy["min_subgroup_diodes"])
        result = assess_diode_annealing(
            _case(
                sample_plan={"subgroup": ANNEALING_SUBGROUP, "diode_count": floor}
            ),
            policy,
        )
        self.assertEqual(result["verdict"], ANNEALING_STABILITY_ACCEPTED)

    def test_a_soak_above_the_package_rating_is_a_profile_deficiency(self):
        result = assess_diode_annealing(
            _case(soak=_soak(soak_temperature_c=200.0))
        )
        self.assertEqual(result["verdict"], ANNEALING_SOAK_PROFILE_DEFICIENT)
        self.assertFalse(result["soak_within_rating"])

    def test_a_cool_soak_is_a_profile_deficiency(self):
        result = assess_diode_annealing(
            _case(soak=_soak(soak_temperature_c=60.0))
        )
        self.assertEqual(result["verdict"], ANNEALING_SOAK_PROFILE_DEFICIENT)

    def test_a_short_soak_is_a_profile_deficiency(self):
        result = assess_diode_annealing(_case(soak=_soak(soak_duration_h=24.0)))
        self.assertEqual(result["verdict"], ANNEALING_SOAK_PROFILE_DEFICIENT)

    def test_a_short_recovery_dwell_is_a_profile_deficiency(self):
        result = assess_diode_annealing(_case(soak=_soak(recovery_dwell_h=0.1)))
        self.assertEqual(result["verdict"], ANNEALING_SOAK_PROFILE_DEFICIENT)

    def test_a_dose_short_of_the_equivalent_hours_floor_is_a_profile_deficiency(self):
        policy = _policy(min_equivalent_reference_hours=1.0e12)
        result = assess_diode_annealing(_case(), policy)
        self.assertEqual(result["verdict"], ANNEALING_SOAK_PROFILE_DEFICIENT)

    def test_every_profile_finding_is_reported_not_only_the_first(self):
        result = assess_diode_annealing(
            _case(soak=_soak(soak_temperature_c=60.0, soak_duration_h=24.0,
                             recovery_dwell_h=0.1))
        )
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_missing_sample_plan_rejected(self):
        case = _case()
        del case["sample_plan"]
        with self.assertRaises(ValueError):
            assess_diode_annealing(case)

    def test_missing_soak_block_rejected(self):
        case = _case()
        del case["soak"]
        with self.assertRaises(ValueError):
            assess_diode_annealing(case)

    def test_missing_before_block_rejected(self):
        case = _case()
        del case["before"]
        with self.assertRaises(ValueError):
            assess_diode_annealing(case)

    def test_missing_after_block_rejected(self):
        case = _case()
        del case["after"]
        with self.assertRaises(ValueError):
            assess_diode_annealing(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_annealing(["sample_plan"])

    def test_a_negative_soak_duration_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_annealing(_case(soak=_soak(soak_duration_h=-10.0)))

    def test_a_missing_forward_voltage_reading_rejected(self):
        after = _after()
        del after["forward_voltage_v"]
        with self.assertRaises(ValueError):
            assess_diode_annealing(_case(after=after))


if __name__ == "__main__":
    unittest.main()
