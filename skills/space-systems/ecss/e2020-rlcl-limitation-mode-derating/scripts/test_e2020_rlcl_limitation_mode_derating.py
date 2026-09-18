"""Contract tests for the clause 5.2.3.5.1 limitation-mode derating assessment.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused derating policy,
an operating point that is not limitation at all, a component set claiming
more voltage than the bus supplies, a part fast enough to reach the peak
every retrigger cycle, and each of the four derated limits taken past its
allowance on its own.
"""

import unittest

from e2020_rlcl_limitation_mode_derating_logic import (
    CURRENT_DERATING,
    DEFAULT_DERATING_POLICY,
    DERATING_LIMIT_EXCEEDED,
    DERATING_POLICY_NOT_ESTABLISHED,
    DUTY_AVERAGED_DISSIPATION,
    JUNCTION_TEMPERATURE_DERATING,
    LIMITATION_MODE_WITHIN_DERATING,
    LIMITATION_POINT_NOT_ESTABLISHED,
    PEAK_DISSIPATION,
    POWER_DERATING,
    VOLTAGE_DERATING,
    assess_limitation_mode_derating,
    component_derating_verdict,
    component_verdicts,
    duty_averaged_dissipation_w,
    governing_dissipation,
    junction_temperature_c,
    limiter_differential_v,
    limiting_component,
    peak_dissipation_w,
    retrigger_duty_cycle,
    upper_limitation_current_a,
    validate_component,
    validate_component_set,
    validate_derating_policy,
    validate_limitation_point,
)

DIFFERENTIAL_V = 50.0
PEAK_W = 165.0


def _policy(**overrides):
    policy = dict(DEFAULT_DERATING_POLICY)
    policy.update(overrides)
    return policy


def _point(**overrides):
    point = {
        "max_input_voltage_v": 52.0,
        "min_output_voltage_v": 2.0,
        "limitation_current_a": 3.0,
        "limitation_current_tolerance": 0.10,
        "limitation_dwell_s": 0.02,
        "retrigger_recovery_s": 0.18,
        "mounting_temperature_c": 60.0,
    }
    point.update(overrides)
    return point


def _pass_device(**overrides):
    component = {
        "id": "pass-device",
        "differential_share": 0.90,
        "carries_limitation_current": True,
        "rated_voltage_v": 100.0,
        "rated_current_a": 10.0,
        "rated_power_w": 40.0,
        "thermal_resistance_c_per_w": 1.5,
        "thermal_time_constant_s": 0.5,
    }
    component.update(overrides)
    return component


def _sense_element(**overrides):
    component = {
        "id": "sense-element",
        "differential_share": 0.06,
        "carries_limitation_current": True,
        "rated_voltage_v": 20.0,
        "rated_current_a": 8.0,
        "rated_power_w": 25.0,
        "thermal_resistance_c_per_w": 4.0,
    }
    component.update(overrides)
    return component


def _case(**overrides):
    case = {
        "limitation_point": _point(),
        "components": [_pass_device(), _sense_element()],
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        rules = validate_derating_policy(DEFAULT_DERATING_POLICY)
        self.assertAlmostEqual(rules["power_factor"], 0.50, places=9)

    def test_a_factor_above_one_is_refused(self):
        with self.assertRaises(ValueError):
            validate_derating_policy(_policy(voltage_factor=1.2))

    def test_a_zero_factor_is_refused(self):
        with self.assertRaises(ValueError):
            validate_derating_policy(_policy(current_factor=0.0))

    def test_a_non_mapping_policy_is_refused(self):
        with self.assertRaises(ValueError):
            validate_derating_policy(["voltage_factor"])

    def test_a_policy_with_no_reference_closes_the_assessment(self):
        result = assess_limitation_mode_derating(
            _case(), _policy(policy_reference="   ")
        )
        self.assertEqual(result["verdict"], DERATING_POLICY_NOT_ESTABLISHED)


class LimitationPointTests(unittest.TestCase):
    def test_an_output_at_the_input_is_not_limitation(self):
        with self.assertRaises(ValueError):
            validate_limitation_point(_point(min_output_voltage_v=52.0))

    def test_a_negative_tolerance_is_refused(self):
        with self.assertRaises(ValueError):
            validate_limitation_point(_point(limitation_current_tolerance=-0.05))

    def test_a_zero_dwell_is_refused(self):
        with self.assertRaises(ValueError):
            validate_limitation_point(_point(limitation_dwell_s=0.0))

    def test_the_differential_is_input_minus_held_output(self):
        self.assertAlmostEqual(
            limiter_differential_v(_point()), DIFFERENTIAL_V, places=9
        )

    def test_the_band_edge_sets_the_stressing_current(self):
        self.assertAlmostEqual(upper_limitation_current_a(_point()), 3.3, places=9)

    def test_peak_dissipation_takes_the_worst_corner(self):
        self.assertAlmostEqual(peak_dissipation_w(_point()), PEAK_W, places=9)

    def test_the_retrigger_duty_thins_the_average(self):
        self.assertAlmostEqual(retrigger_duty_cycle(_point()), 0.10, places=9)
        self.assertAlmostEqual(
            duty_averaged_dissipation_w(_point()), PEAK_W * 0.10, places=9
        )

    def test_a_limiter_that_never_retries_runs_at_unity_duty(self):
        self.assertAlmostEqual(
            retrigger_duty_cycle(_point(retrigger_recovery_s=0.0)), 1.0, places=9
        )


class ComponentSetTests(unittest.TestCase):
    def test_shares_beyond_the_differential_are_refused(self):
        with self.assertRaises(ValueError):
            validate_component_set(
                [_pass_device(differential_share=0.9), _sense_element(
                    differential_share=0.4
                )],
                _point(),
            )

    def test_shares_landing_exactly_on_the_differential_are_admitted(self):
        checked = validate_component_set(
            [
                _pass_device(differential_share=0.94),
                _sense_element(differential_share=0.06),
            ],
            _point(),
        )
        self.assertEqual(len(checked), 2)

    def test_a_duplicate_component_id_is_refused(self):
        with self.assertRaises(ValueError):
            validate_component_set([_pass_device(), _pass_device()], _point())

    def test_an_empty_component_set_is_refused(self):
        with self.assertRaises(ValueError):
            validate_component_set([], _point())

    def test_a_non_boolean_current_flag_is_refused(self):
        with self.assertRaises(ValueError):
            validate_component(_pass_device(carries_limitation_current="yes"))


class GoverningDissipationTests(unittest.TestCase):
    def test_a_slow_part_rides_the_duty_average(self):
        power, basis = governing_dissipation(_pass_device(), _point())
        self.assertEqual(basis, DUTY_AVERAGED_DISSIPATION)
        self.assertAlmostEqual(power, PEAK_W * 0.10 * 0.90, places=9)

    def test_a_part_faster_than_the_dwell_reaches_the_peak(self):
        power, basis = governing_dissipation(
            _pass_device(thermal_time_constant_s=0.001), _point()
        )
        self.assertEqual(basis, PEAK_DISSIPATION)
        self.assertAlmostEqual(power, PEAK_W * 0.90, places=9)

    def test_a_part_with_no_time_constant_is_taken_at_the_peak(self):
        power, basis = governing_dissipation(_sense_element(), _point())
        self.assertEqual(basis, PEAK_DISSIPATION)
        self.assertAlmostEqual(power, PEAK_W * 0.06, places=9)

    def test_junction_temperature_rises_from_the_mounting_reference(self):
        self.assertAlmostEqual(junction_temperature_c(10.0, 2.0, 55.0), 75.0, places=9)


class ComponentVerdictTests(unittest.TestCase):
    def test_the_nominal_pass_device_is_inside_every_limit(self):
        verdict = component_derating_verdict(_pass_device(), _point())
        self.assertTrue(verdict["within_derating"])
        self.assertAlmostEqual(
            verdict["utilisations"][VOLTAGE_DERATING], 0.60, places=9
        )
        self.assertAlmostEqual(
            verdict["utilisations"][CURRENT_DERATING], 0.44, places=9
        )

    def test_a_power_stress_exactly_on_the_allowance_is_admitted(self):
        verdict = component_derating_verdict(
            _pass_device(rated_power_w=29.7), _point()
        )
        self.assertTrue(verdict["within_derating"])
        self.assertAlmostEqual(
            verdict["utilisations"][POWER_DERATING], 1.0, places=9
        )

    def test_a_power_stress_past_the_allowance_is_found(self):
        verdict = component_derating_verdict(
            _pass_device(rated_power_w=20.0), _point()
        )
        self.assertFalse(verdict["within_derating"])
        self.assertIn(POWER_DERATING, verdict["exceedances"])

    def test_a_voltage_stress_past_the_allowance_is_found(self):
        verdict = component_derating_verdict(
            _pass_device(rated_voltage_v=55.0), _point()
        )
        self.assertIn(VOLTAGE_DERATING, verdict["exceedances"])

    def test_a_current_stress_past_the_allowance_is_found(self):
        verdict = component_derating_verdict(
            _pass_device(rated_current_a=4.0), _point()
        )
        self.assertIn(CURRENT_DERATING, verdict["exceedances"])

    def test_a_junction_temperature_past_the_ceiling_is_found(self):
        verdict = component_derating_verdict(
            _pass_device(thermal_resistance_c_per_w=6.0), _point()
        )
        self.assertIn(JUNCTION_TEMPERATURE_DERATING, verdict["exceedances"])

    def test_a_part_out_of_the_current_path_carries_no_current(self):
        verdict = component_derating_verdict(
            _sense_element(carries_limitation_current=False), _point()
        )
        self.assertAlmostEqual(verdict["applied_current_a"], 0.0, places=12)

    def test_a_mounting_reference_at_the_ceiling_is_refused(self):
        with self.assertRaises(ValueError):
            component_derating_verdict(
                _pass_device(), _point(mounting_temperature_c=110.0)
            )

    def test_a_component_ceiling_below_the_policy_ceiling_governs(self):
        verdict = component_derating_verdict(
            _pass_device(max_junction_temperature_c=70.0), _point()
        )
        self.assertAlmostEqual(verdict["junction_ceiling_c"], 70.0, places=9)
        self.assertIn(JUNCTION_TEMPERATURE_DERATING, verdict["exceedances"])


class AssessmentTests(unittest.TestCase):
    def test_the_nominal_case_is_within_derating(self):
        result = assess_limitation_mode_derating(_case())
        self.assertEqual(result["verdict"], LIMITATION_MODE_WITHIN_DERATING)
        self.assertEqual(result["findings"], [])

    def test_the_small_series_part_can_be_the_limiting_one(self):
        result = assess_limitation_mode_derating(_case())
        self.assertEqual(result["limiting_component_id"], "sense-element")

    def test_the_limiting_component_is_the_least_margin_record(self):
        verdicts = component_verdicts(
            [_pass_device(), _sense_element()], _point()
        )
        self.assertEqual(limiting_component(verdicts)["id"], "sense-element")

    def test_an_exceedance_names_the_component_and_the_limit(self):
        case = _case(components=[_pass_device(rated_power_w=12.0), _sense_element()])
        result = assess_limitation_mode_derating(case)
        self.assertEqual(result["verdict"], DERATING_LIMIT_EXCEEDED)
        self.assertIn("pass-device", result["findings"][0])

    def test_a_missing_limitation_point_closes_the_assessment(self):
        case = _case()
        del case["limitation_point"]
        result = assess_limitation_mode_derating(case)
        self.assertEqual(result["verdict"], LIMITATION_POINT_NOT_ESTABLISHED)
        self.assertEqual(result["component_verdicts"], ())

    def test_a_single_valued_limitation_threshold_is_advised(self):
        result = assess_limitation_mode_derating(
            _case(limitation_point=_point(limitation_current_tolerance=0.0))
        )
        self.assertTrue(
            any("no tolerance" in advisory for advisory in result["advisories"])
        )

    def test_a_limiter_with_no_recovery_is_advised(self):
        result = assess_limitation_mode_derating(
            _case(limitation_point=_point(retrigger_recovery_s=0.0))
        )
        self.assertTrue(
            any("continuously" in advisory for advisory in result["advisories"])
        )

    def test_the_reported_dissipation_pair_is_carried_out(self):
        result = assess_limitation_mode_derating(_case())
        self.assertAlmostEqual(result["peak_dissipation_w"], PEAK_W, places=9)
        self.assertAlmostEqual(
            result["duty_averaged_dissipation_w"], PEAK_W * 0.10, places=9
        )

    def test_a_non_mapping_case_is_refused(self):
        with self.assertRaises(ValueError):
            assess_limitation_mode_derating(["limitation_point"])


if __name__ == "__main__":
    unittest.main()
