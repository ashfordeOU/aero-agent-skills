"""Contract tests for the clause 6.4.3.18.1 long duration life test purpose."""

import math
import unittest

from e2008_long_duration_life_test_purpose_logic import (
    ACCELERATION_NOT_JUSTIFIED,
    BOLTZMANN_EV_PER_KELVIN,
    DEFAULT_PURPOSE_POLICY,
    ECLIPSE_THERMAL_CYCLING,
    EXPOSURE_SHORT_OF_SERVICE,
    HOT_OPERATING_TEMPERATURE,
    HOURS_PER_YEAR,
    MAXIMUM_OPERATING_BIAS,
    PEAK_ILLUMINATION,
    PURPOSE_NOT_ESTABLISHED,
    PURPOSE_SERVED,
    RECOGNISED_OPERATING_CONDITIONS,
    acceleration_findings,
    arrhenius_acceleration_factor,
    assess_long_duration_life_test_purpose,
    celsius_to_kelvin,
    coverage_ratio,
    equivalent_service_hours,
    mechanism_ceiling_findings,
    required_service_hours,
    uncovered_operating_conditions,
    validate_purpose_policy,
    validate_service_profile,
)

DECLARED = [
    HOT_OPERATING_TEMPERATURE,
    MAXIMUM_OPERATING_BIAS,
    PEAK_ILLUMINATION,
    ECLIPSE_THERMAL_CYCLING,
]


def _policy(**overrides):
    policy = dict(DEFAULT_PURPOSE_POLICY)
    policy.update(overrides)
    return policy


def _profile(**overrides):
    profile = {
        "service_life_years": 15.0,
        "worst_case_operating_temperature_c": 60.0,
        "declared_operating_conditions": list(DECLARED),
    }
    profile.update(overrides)
    return profile


def _plan(**overrides):
    plan = {
        "test_temperature_c": 110.0,
        "test_duration_hours": 8000.0,
        "reproduced_operating_conditions": list(DECLARED),
        "reports_power_stability": True,
    }
    plan.update(overrides)
    return plan


def _case(**overrides):
    case = {"service_profile": _profile(), "test_plan": _plan()}
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_purpose_policy(DEFAULT_PURPOSE_POLICY), DEFAULT_PURPOSE_POLICY
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_purpose_policy("arrhenius")

    def test_zero_activation_energy_rejected(self):
        with self.assertRaises(ValueError):
            validate_purpose_policy(_policy(activation_energy_ev=0.0))

    def test_absurd_activation_energy_rejected(self):
        with self.assertRaises(ValueError):
            validate_purpose_policy(_policy(activation_energy_ev=7.5))

    def test_coverage_ratio_below_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_purpose_policy(_policy(minimum_coverage_ratio=0.8))

    def test_maximum_factor_of_one_rejected(self):
        with self.assertRaises(ValueError):
            validate_purpose_policy(_policy(maximum_acceleration_factor=1.0))

    def test_ceiling_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            validate_purpose_policy(_policy(mechanism_ceiling_c=-400.0))


class ServiceProfileTests(unittest.TestCase):
    def test_profile_returns_years_temperature_and_conditions(self):
        years, temperature, conditions = validate_service_profile(_profile())
        self.assertAlmostEqual(years, 15.0, places=9)
        self.assertAlmostEqual(temperature, 60.0, places=9)
        self.assertEqual(conditions, tuple(DECLARED))

    def test_non_mapping_profile_rejected(self):
        with self.assertRaises(ValueError):
            validate_service_profile([15.0])

    def test_zero_service_life_rejected(self):
        with self.assertRaises(ValueError):
            validate_service_profile(_profile(service_life_years=0.0))

    def test_empty_condition_envelope_rejected(self):
        with self.assertRaises(ValueError):
            validate_service_profile(_profile(declared_operating_conditions=[]))

    def test_unknown_operating_condition_rejected(self):
        with self.assertRaises(ValueError):
            validate_service_profile(
                _profile(declared_operating_conditions=["launch-acoustics"])
            )

    def test_duplicate_operating_condition_rejected(self):
        with self.assertRaises(ValueError):
            validate_service_profile(
                _profile(
                    declared_operating_conditions=[
                        HOT_OPERATING_TEMPERATURE,
                        HOT_OPERATING_TEMPERATURE,
                    ]
                )
            )

    def test_recognised_conditions_are_hyphenated_and_unique(self):
        self.assertEqual(
            len(set(RECOGNISED_OPERATING_CONDITIONS)),
            len(RECOGNISED_OPERATING_CONDITIONS),
        )
        for name in RECOGNISED_OPERATING_CONDITIONS:
            self.assertNotIn(" ", name)


class TemperatureTests(unittest.TestCase):
    def test_zero_celsius_converts_to_the_ice_point(self):
        self.assertAlmostEqual(celsius_to_kelvin(0.0), 273.15, places=9)

    def test_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            celsius_to_kelvin(-273.15)

    def test_non_numeric_temperature_rejected(self):
        with self.assertRaises(ValueError):
            celsius_to_kelvin("60 C")


class AccelerationTests(unittest.TestCase):
    def test_equal_temperatures_give_unity_factor(self):
        self.assertAlmostEqual(
            arrhenius_acceleration_factor(60.0, 60.0, 0.7), 1.0, places=9
        )

    def test_factor_matches_the_arrhenius_expression(self):
        use_k = celsius_to_kelvin(60.0)
        test_k = celsius_to_kelvin(100.0)
        expected = math.exp(
            (0.7 / BOLTZMANN_EV_PER_KELVIN) * (1.0 / use_k - 1.0 / test_k)
        )
        self.assertAlmostEqual(
            arrhenius_acceleration_factor(60.0, 100.0, 0.7) / expected,
            1.0,
            places=12,
        )

    def test_hotter_test_gives_a_larger_factor(self):
        cooler = arrhenius_acceleration_factor(60.0, 80.0, 0.7)
        hotter = arrhenius_acceleration_factor(60.0, 100.0, 0.7)
        self.assertGreater(hotter, cooler * 1.5)

    def test_test_below_service_temperature_rejected(self):
        with self.assertRaises(ValueError):
            arrhenius_acceleration_factor(60.0, 40.0, 0.7)

    def test_higher_activation_energy_gives_a_larger_factor(self):
        low = arrhenius_acceleration_factor(60.0, 100.0, 0.5)
        high = arrhenius_acceleration_factor(60.0, 100.0, 0.9)
        self.assertGreater(high, low * 1.5)


class ExposureTests(unittest.TestCase):
    def test_required_hours_scale_with_the_service_life(self):
        self.assertAlmostEqual(
            required_service_hours(15.0), 15.0 * HOURS_PER_YEAR, places=6
        )

    def test_equivalent_hours_are_the_product(self):
        self.assertAlmostEqual(
            equivalent_service_hours(4000.0, 12.5), 50000.0, places=6
        )

    def test_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_service_hours(4000.0, 0.5)

    def test_zero_test_duration_rejected(self):
        with self.assertRaises(ValueError):
            equivalent_service_hours(0.0, 12.5)

    def test_coverage_ratio_of_exactly_one_at_the_demand(self):
        required = required_service_hours(1.0)
        self.assertAlmostEqual(coverage_ratio(required, required), 1.0, places=9)

    def test_coverage_ratio_rejects_a_negative_demand(self):
        with self.assertRaises(ValueError):
            coverage_ratio(1000.0, -1.0)


class ConditionCoverageTests(unittest.TestCase):
    def test_full_coverage_leaves_nothing_uncovered(self):
        self.assertEqual(uncovered_operating_conditions(DECLARED, DECLARED), ())

    def test_dropped_bias_is_named(self):
        reproduced = [HOT_OPERATING_TEMPERATURE, PEAK_ILLUMINATION]
        self.assertEqual(
            uncovered_operating_conditions(DECLARED, reproduced),
            (MAXIMUM_OPERATING_BIAS, ECLIPSE_THERMAL_CYCLING),
        )

    def test_unknown_reproduced_condition_rejected(self):
        with self.assertRaises(ValueError):
            uncovered_operating_conditions(DECLARED, ["pyroshock"])

    def test_non_sequence_reproduced_record_rejected(self):
        with self.assertRaises(ValueError):
            uncovered_operating_conditions(DECLARED, HOT_OPERATING_TEMPERATURE)


class GuardTests(unittest.TestCase):
    def test_test_at_the_ceiling_raises_no_finding(self):
        self.assertEqual(mechanism_ceiling_findings(110.0), ())

    def test_test_above_the_ceiling_raises_a_finding(self):
        self.assertEqual(len(mechanism_ceiling_findings(130.0)), 1)

    def test_factor_at_the_policy_maximum_raises_no_finding(self):
        self.assertEqual(acceleration_findings(100.0), ())

    def test_factor_above_the_policy_maximum_raises_a_finding(self):
        self.assertEqual(len(acceleration_findings(250.0)), 1)


class AssessmentTests(unittest.TestCase):
    def test_absent_service_profile_closes_the_assessment(self):
        result = assess_long_duration_life_test_purpose({"test_plan": _plan()})
        self.assertEqual(result["verdict"], PURPOSE_NOT_ESTABLISHED)
        self.assertEqual(len(result["findings"]), 1)

    def test_a_covering_plan_serves_the_purpose(self):
        result = assess_long_duration_life_test_purpose(_case())
        self.assertEqual(result["verdict"], PURPOSE_SERVED)
        self.assertEqual(result["uncovered_operating_conditions"], ())
        self.assertEqual(result["advisories"], [])

    def test_short_test_is_short_of_the_service_demand(self):
        case = _case(test_plan=_plan(test_duration_hours=20.0))
        result = assess_long_duration_life_test_purpose(case)
        self.assertEqual(result["verdict"], EXPOSURE_SHORT_OF_SERVICE)
        self.assertLess(result["coverage_ratio"], 1.0)

    def test_test_above_the_mechanism_ceiling_is_not_justified(self):
        case = _case(test_plan=_plan(test_temperature_c=140.0))
        result = assess_long_duration_life_test_purpose(case)
        self.assertEqual(result["verdict"], ACCELERATION_NOT_JUSTIFIED)
        self.assertTrue(result["findings"])

    def test_narrowed_envelope_is_reported_as_an_advisory(self):
        case = _case(
            test_plan=_plan(
                reproduced_operating_conditions=[
                    HOT_OPERATING_TEMPERATURE,
                    PEAK_ILLUMINATION,
                ]
            )
        )
        result = assess_long_duration_life_test_purpose(case)
        self.assertEqual(
            result["uncovered_operating_conditions"],
            (MAXIMUM_OPERATING_BIAS, ECLIPSE_THERMAL_CYCLING),
        )
        self.assertEqual(len(result["advisories"]), 2)

    def test_survival_only_plan_is_advised_against(self):
        case = _case(test_plan=_plan(reports_power_stability=False))
        result = assess_long_duration_life_test_purpose(case)
        self.assertEqual(len(result["advisories"]), 1)

    def test_missing_stability_statement_rejected(self):
        plan = _plan()
        del plan["reports_power_stability"]
        with self.assertRaises(ValueError):
            assess_long_duration_life_test_purpose(_case(test_plan=plan))

    def test_missing_test_plan_rejected(self):
        case = _case()
        del case["test_plan"]
        with self.assertRaises(ValueError):
            assess_long_duration_life_test_purpose(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_long_duration_life_test_purpose(["service_profile"])

    def test_reported_equivalent_hours_match_the_factor(self):
        result = assess_long_duration_life_test_purpose(_case())
        self.assertAlmostEqual(
            result["equivalent_service_hours"]
            / (8000.0 * result["acceleration_factor"]),
            1.0,
            places=12,
        )


if __name__ == "__main__":
    unittest.main()
