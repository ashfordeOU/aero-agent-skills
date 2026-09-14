"""Contract tests for the clause 9.6.18 protection diode life test logic."""

import math
import unittest

from e2008_protection_diode_life_test_logic import (
    BOLTZMANN_EV_PER_K,
    DEFAULT_LIFE_TEST_POLICY,
    LIFE_DRIFT_FAILURE,
    LIFE_SAMPLE_PLAN_DEFICIENT,
    LIFE_STABILITY_ACCEPTED,
    LIFE_STRESS_DEFICIENT,
    LIFE_VERDICTS,
    arrhenius_acceleration_factor,
    assess_diode_life_test,
    drift_rate_per_khour,
    equivalent_mission_hours,
    forward_power_dissipation_w,
    junction_temperature_c,
    parameter_drift_fraction,
    surviving_device_count,
    validate_life_test_policy,
)


def _policy(**overrides):
    policy = dict(DEFAULT_LIFE_TEST_POLICY)
    policy.update(overrides)
    return policy


def _stress(**overrides):
    stress = {
        "forward_current_a": 2.0,
        "case_temperature_c": 125.0,
        "forward_voltage_v": 0.80,
        "thermal_resistance_k_per_w": 10.0,
        "test_duration_h": 2000.0,
        "activation_energy_ev": 0.70,
    }
    stress.update(overrides)
    return stress


def _mission(**overrides):
    mission = {"forward_current_a": 1.0, "case_temperature_c": 60.0}
    mission.update(overrides)
    return mission


def _sample(**overrides):
    sample = {"device_count": 12, "failed_count": 0}
    sample.update(overrides)
    return sample


def _measured(**overrides):
    measured = {
        "initial_forward_voltage_v": 0.800,
        "final_forward_voltage_v": 0.808,
        "initial_leakage_a": 2.0e-8,
        "final_leakage_a": 3.0e-8,
    }
    measured.update(overrides)
    return measured


def _case(**overrides):
    case = {
        "stress": _stress(),
        "mission": _mission(),
        "sample": _sample(),
        "measured": _measured(),
    }
    case.update(overrides)
    return case


def _ratio(value, expected):
    return value / expected


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_life_test_policy(DEFAULT_LIFE_TEST_POLICY),
            DEFAULT_LIFE_TEST_POLICY,
        )

    def test_a_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_life_test_policy("run it long")

    def test_an_equivalent_floor_below_the_run_length_rejected(self):
        with self.assertRaises(ValueError):
            validate_life_test_policy(_policy(min_equivalent_mission_hours=500.0))

    def test_a_zero_activation_energy_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_life_test_policy(_policy(min_activation_energy_ev=0.0))

    def test_a_fractional_sample_floor_rejected(self):
        with self.assertRaises(ValueError):
            validate_life_test_policy(_policy(min_sample_size=10.5))

    def test_a_negative_allowed_failure_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_life_test_policy(_policy(max_failed_devices=-1))

    def test_every_verdict_is_declared(self):
        self.assertEqual(len(set(LIFE_VERDICTS)), 4)


class JunctionTests(unittest.TestCase):
    def test_dissipation_is_the_forward_bias_product(self):
        self.assertAlmostEqual(
            _ratio(forward_power_dissipation_w(0.80, 2.0), 1.6), 1.0, places=12
        )

    def test_the_junction_sits_above_its_case_by_the_self_heating(self):
        self.assertAlmostEqual(
            junction_temperature_c(125.0, 1.6, 10.0), 141.0, places=9
        )

    def test_a_perfect_heat_path_leaves_the_junction_at_its_case(self):
        self.assertAlmostEqual(
            junction_temperature_c(125.0, 0.0, 10.0), 125.0, places=9
        )

    def test_a_worse_thermal_path_raises_the_junction(self):
        stiff = junction_temperature_c(125.0, 1.6, 2.0)
        poor = junction_temperature_c(125.0, 1.6, 40.0)
        self.assertGreater(poor, stiff)

    def test_a_case_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            junction_temperature_c(-300.0, 1.6, 10.0)

    def test_a_negative_dissipation_rejected(self):
        with self.assertRaises(ValueError):
            junction_temperature_c(125.0, -1.6, 10.0)

    def test_a_boolean_forward_current_rejected(self):
        with self.assertRaises(ValueError):
            forward_power_dissipation_w(0.80, True)


class AccelerationTests(unittest.TestCase):
    def test_the_factor_follows_the_arrhenius_form(self):
        expected = math.exp(
            (0.70 / BOLTZMANN_EV_PER_K)
            * (1.0 / (68.0 + 273.15) - 1.0 / (141.0 + 273.15))
        )
        self.assertAlmostEqual(
            _ratio(arrhenius_acceleration_factor(141.0, 68.0, 0.70), expected),
            1.0,
            places=12,
        )

    def test_a_run_at_the_mission_junction_buys_nothing(self):
        self.assertAlmostEqual(
            arrhenius_acceleration_factor(68.0, 68.0, 0.70), 1.0, places=12
        )

    def test_a_hotter_run_buys_mission_time(self):
        self.assertGreater(arrhenius_acceleration_factor(141.0, 68.0, 0.70), 10.0)

    def test_a_cooler_run_buys_less_than_its_own_hours(self):
        self.assertLess(arrhenius_acceleration_factor(40.0, 68.0, 0.70), 1.0)

    def test_a_higher_activation_energy_claims_more_acceleration(self):
        low = arrhenius_acceleration_factor(141.0, 68.0, 0.40)
        high = arrhenius_acceleration_factor(141.0, 68.0, 0.90)
        self.assertGreater(high, low)

    def test_equivalent_hours_are_the_run_times_the_factor(self):
        self.assertAlmostEqual(
            _ratio(equivalent_mission_hours(2000.0, 30.0), 60000.0), 1.0, places=12
        )

    def test_a_zero_acceleration_factor_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_mission_hours(2000.0, 0.0)

    def test_a_junction_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            arrhenius_acceleration_factor(-300.0, 68.0, 0.70)


class DriftAndSampleTests(unittest.TestCase):
    def test_a_ten_per_cent_move_is_a_drift_of_one_tenth(self):
        self.assertAlmostEqual(parameter_drift_fraction(0.80, 0.88), 0.1, places=9)

    def test_an_unchanged_parameter_has_no_drift(self):
        self.assertAlmostEqual(parameter_drift_fraction(0.80, 0.80), 0.0, places=12)

    def test_drift_is_taken_in_either_direction(self):
        self.assertGreater(parameter_drift_fraction(0.80, 0.72), 0.0)

    def test_a_zero_starting_value_rejected(self):
        with self.assertRaises(ValueError):
            parameter_drift_fraction(0.0, 0.80)

    def test_the_rate_spreads_the_drift_over_the_run(self):
        self.assertAlmostEqual(drift_rate_per_khour(0.04, 2000.0), 0.02, places=9)

    def test_a_shorter_run_reports_the_same_drift_as_a_faster_rate(self):
        slow = drift_rate_per_khour(0.04, 4000.0)
        fast = drift_rate_per_khour(0.04, 500.0)
        self.assertGreater(fast, slow)

    def test_a_zero_length_run_rejected(self):
        with self.assertRaises(ValueError):
            drift_rate_per_khour(0.04, 0.0)

    def test_survivors_are_the_load_less_the_failures(self):
        self.assertEqual(
            surviving_device_count({"device_count": 12, "failed_count": 2}), 10
        )

    def test_more_failures_than_devices_rejected(self):
        with self.assertRaises(ValueError):
            surviving_device_count({"device_count": 12, "failed_count": 15})

    def test_a_non_mapping_sample_rejected(self):
        with self.assertRaises(ValueError):
            surviving_device_count([12, 2])


class LifeTestAssessmentTests(unittest.TestCase):
    def test_a_nominal_run_is_accepted(self):
        result = assess_diode_life_test(_case())
        self.assertEqual(result["verdict"], LIFE_STABILITY_ACCEPTED)
        self.assertEqual(result["findings"], [])

    def test_the_derived_endurance_quantities_are_reported(self):
        result = assess_diode_life_test(_case())
        self.assertAlmostEqual(result["stress_junction_c"], 141.0, places=9)
        self.assertAlmostEqual(result["mission_junction_c"], 68.0, places=9)
        self.assertAlmostEqual(result["junction_margin_k"], 73.0, places=9)
        self.assertAlmostEqual(
            _ratio(
                result["equivalent_mission_hours"],
                2000.0 * arrhenius_acceleration_factor(141.0, 68.0, 0.70),
            ),
            1.0,
            places=12,
        )

    def test_a_run_length_exactly_at_the_floor_is_accepted(self):
        policy = _policy()
        floor = float(policy["min_test_duration_h"])
        result = assess_diode_life_test(
            _case(stress=_stress(test_duration_h=floor)), policy
        )
        self.assertAlmostEqual(result["test_duration_h"], floor, places=9)
        self.assertEqual(result["verdict"], LIFE_STABILITY_ACCEPTED)

    def test_a_junction_margin_exactly_at_the_floor_is_representative(self):
        policy = _policy()
        floor = float(policy["min_junction_stress_margin_k"])
        result = assess_diode_life_test(
            _case(stress=_stress(case_temperature_c=68.0 + floor - 16.0)), policy
        )
        self.assertAlmostEqual(result["junction_margin_k"], floor, places=9)
        self.assertTrue(result["stress_representative"])
        self.assertNotEqual(result["verdict"], LIFE_STRESS_DEFICIENT)

    def test_a_leakage_drift_exactly_at_the_limit_is_accepted(self):
        policy = _policy()
        limit = float(policy["max_leakage_drift_fraction"])
        start = 2.0e-8
        result = assess_diode_life_test(
            _case(
                measured=_measured(
                    initial_leakage_a=start, final_leakage_a=start * (1.0 + limit)
                )
            ),
            policy,
        )
        self.assertAlmostEqual(result["leakage_drift_fraction"], limit, places=9)
        self.assertEqual(result["verdict"], LIFE_STABILITY_ACCEPTED)

    def test_a_forward_drift_rate_exactly_at_the_limit_is_accepted(self):
        policy = _policy()
        rate_limit = float(policy["max_forward_drift_rate_per_khour"])
        start = 0.800
        drift = rate_limit * 2000.0 / 1000.0
        result = assess_diode_life_test(
            _case(
                measured=_measured(
                    initial_forward_voltage_v=start,
                    final_forward_voltage_v=start * (1.0 + drift),
                )
            ),
            policy,
        )
        self.assertAlmostEqual(
            result["forward_drift_rate_per_khour"], rate_limit, places=9
        )
        self.assertEqual(result["verdict"], LIFE_STABILITY_ACCEPTED)

    def test_a_junction_over_the_ceiling_is_a_stress_deficiency(self):
        result = assess_diode_life_test(
            _case(stress=_stress(case_temperature_c=145.0))
        )
        self.assertEqual(result["verdict"], LIFE_STRESS_DEFICIENT)
        self.assertFalse(result["stress_representative"])

    def test_a_run_no_hotter_than_the_mission_is_a_stress_deficiency(self):
        result = assess_diode_life_test(
            _case(stress=_stress(case_temperature_c=60.0))
        )
        self.assertEqual(result["verdict"], LIFE_STRESS_DEFICIENT)

    def test_a_run_below_the_mission_current_is_a_stress_deficiency(self):
        result = assess_diode_life_test(
            _case(
                stress=_stress(forward_current_a=0.5),
                mission=_mission(forward_current_a=3.0),
            )
        )
        self.assertEqual(result["verdict"], LIFE_STRESS_DEFICIENT)

    def test_an_overstated_activation_energy_is_a_stress_deficiency(self):
        result = assess_diode_life_test(
            _case(stress=_stress(activation_energy_ev=0.20))
        )
        self.assertEqual(result["verdict"], LIFE_STRESS_DEFICIENT)

    def test_no_acceleration_is_reported_when_the_stress_is_not_representative(self):
        result = assess_diode_life_test(
            _case(stress=_stress(case_temperature_c=145.0))
        )
        self.assertIsNone(result["acceleration_factor"])
        self.assertIsNone(result["equivalent_mission_hours"])

    def test_the_stress_outranks_a_drift_failure(self):
        result = assess_diode_life_test(
            _case(
                stress=_stress(case_temperature_c=145.0),
                measured=_measured(final_forward_voltage_v=0.960),
            )
        )
        self.assertEqual(result["verdict"], LIFE_STRESS_DEFICIENT)

    def test_a_shifted_forward_voltage_is_a_drift_failure(self):
        result = assess_diode_life_test(
            _case(measured=_measured(final_forward_voltage_v=0.960))
        )
        self.assertEqual(result["verdict"], LIFE_DRIFT_FAILURE)
        self.assertGreater(result["forward_voltage_drift_fraction"], 0.05)

    def test_grown_leakage_is_a_drift_failure(self):
        result = assess_diode_life_test(
            _case(measured=_measured(final_leakage_a=9.0e-8))
        )
        self.assertEqual(result["verdict"], LIFE_DRIFT_FAILURE)

    def test_a_part_still_moving_at_the_end_is_a_drift_failure(self):
        result = assess_diode_life_test(
            _case(
                stress=_stress(test_duration_h=2100.0),
                measured=_measured(final_forward_voltage_v=0.836),
            )
        )
        self.assertEqual(result["verdict"], LIFE_DRIFT_FAILURE)
        self.assertGreater(result["forward_drift_rate_per_khour"], 0.02)

    def test_a_device_lost_during_the_run_is_a_drift_failure(self):
        result = assess_diode_life_test(_case(sample=_sample(failed_count=1)))
        self.assertEqual(result["verdict"], LIFE_DRIFT_FAILURE)
        self.assertEqual(result["surviving_devices"], 11)

    def test_a_drift_failure_outranks_a_thin_sample(self):
        result = assess_diode_life_test(
            _case(
                sample=_sample(device_count=4),
                measured=_measured(final_forward_voltage_v=0.960),
            )
        )
        self.assertEqual(result["verdict"], LIFE_DRIFT_FAILURE)

    def test_too_few_survivors_is_a_sample_plan_deficiency(self):
        result = assess_diode_life_test(_case(sample=_sample(device_count=4)))
        self.assertEqual(result["verdict"], LIFE_SAMPLE_PLAN_DEFICIENT)

    def test_a_short_run_is_a_sample_plan_deficiency(self):
        result = assess_diode_life_test(
            _case(
                stress=_stress(test_duration_h=250.0),
                measured=_measured(final_forward_voltage_v=0.801),
            )
        )
        self.assertEqual(result["verdict"], LIFE_SAMPLE_PLAN_DEFICIENT)

    def test_too_little_mission_time_bought_is_a_sample_plan_deficiency(self):
        result = assess_diode_life_test(
            _case(stress=_stress(case_temperature_c=95.0))
        )
        self.assertEqual(result["verdict"], LIFE_SAMPLE_PLAN_DEFICIENT)
        self.assertLess(result["equivalent_mission_hours"], 60000.0)

    def test_every_sample_finding_is_reported_not_only_the_first(self):
        result = assess_diode_life_test(
            _case(
                sample=_sample(device_count=4),
                stress=_stress(test_duration_h=250.0),
                measured=_measured(final_forward_voltage_v=0.801),
            )
        )
        self.assertEqual(len(result["findings"]), 3)

    def test_a_missing_stress_block_rejected(self):
        case = _case()
        del case["stress"]
        with self.assertRaises(ValueError):
            assess_diode_life_test(case)

    def test_a_missing_mission_block_rejected(self):
        case = _case()
        del case["mission"]
        with self.assertRaises(ValueError):
            assess_diode_life_test(case)

    def test_a_missing_measured_block_rejected(self):
        case = _case()
        del case["measured"]
        with self.assertRaises(ValueError):
            assess_diode_life_test(case)

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_life_test(["stress"])

    def test_a_negative_run_length_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_life_test(_case(stress=_stress(test_duration_h=-100.0)))


if __name__ == "__main__":
    unittest.main()
