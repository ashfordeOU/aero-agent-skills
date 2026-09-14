"""Contract tests for the clause 9.6.12 protection diode electron exposure.

Every workflow step the SKILL.md sets out is exercised here, together with
the stop conditions the gate 3 contract reviews: a refused exposure policy, a
run with no unirradiated reference, a staircase that does not rise or is too
short, a step measured off the reference temperature, a damage ratio that
falls back, a step sitting off its own fitted curve, and an end-of-life
projection past the limits the string and the blocking function allow.

Every comparison against a fitted or projected value is made with
assertAlmostEqual rather than a strict inequality: log10 and the power that
undoes it are not correctly rounded, so the last bit differs between
platforms.
"""

import math
import unittest

from e2008_diode_electron_irradiation_test_logic import (
    DEFAULT_IRRADIATION_POLICY,
    DEGRADATION_CHARACTERIZED,
    DEGRADATION_NOT_MONOTONIC,
    END_OF_LIFE_LIMIT_EXCEEDED,
    FLUENCE_STAIRCASE_INVALID,
    MEASUREMENT_CONDITIONS_INCONSISTENT,
    STEP_OFF_DEGRADATION_CURVE,
    UNIRRADIATED_REFERENCE_MISSING,
    assess_diode_electron_irradiation,
    decades_between,
    fit_against_log_fluence,
    fitted_value_at_fluence,
    forward_voltage_ratio,
    leakage_growth_ratio,
    max_relative_residual,
    measurement_at_reference_conditions,
    non_monotonic_fluences,
    projected_forward_voltage_ratio,
    projected_leakage_growth_ratio,
    staircase_rising,
    validate_irradiation_policy,
    validate_reference_measurement,
    validate_step,
)

REFERENCE_VOLTAGE = 0.70
REFERENCE_LEAKAGE = 1.0e-9
LOG_THREE = math.log10(3.0)


def _policy(**overrides):
    policy = dict(DEFAULT_IRRADIATION_POLICY)
    policy.update(overrides)
    return policy


def _reference(**overrides):
    record = {
        "forward_voltage_v": REFERENCE_VOLTAGE,
        "reverse_leakage_a": REFERENCE_LEAKAGE,
        "measurement_temperature_c": 25.0,
    }
    record.update(overrides)
    return record


def _steps():
    return [
        {
            "fluence_e_per_cm2": 1.0e13,
            "forward_voltage_v": 0.714,
            "reverse_leakage_a": 3.0e-9,
            "measurement_temperature_c": 25.0,
        },
        {
            "fluence_e_per_cm2": 1.0e14,
            "forward_voltage_v": 0.728,
            "reverse_leakage_a": 9.0e-9,
            "measurement_temperature_c": 25.0,
        },
        {
            "fluence_e_per_cm2": 1.0e15,
            "forward_voltage_v": 0.742,
            "reverse_leakage_a": 2.7e-8,
            "measurement_temperature_c": 25.0,
        },
        {
            "fluence_e_per_cm2": 1.0e16,
            "forward_voltage_v": 0.756,
            "reverse_leakage_a": 8.1e-8,
            "measurement_temperature_c": 25.0,
        },
    ]


def _case(**overrides):
    case = {
        "unirradiated_reference": _reference(),
        "steps": _steps(),
        "end_of_life_fluence_e_per_cm2": 1.0e15,
    }
    case.update(overrides)
    return case


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_irradiation_policy(DEFAULT_IRRADIATION_POLICY),
            DEFAULT_IRRADIATION_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_irradiation_policy("reference_temperature_c")

    def test_a_single_step_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_irradiation_policy(_policy(min_irradiated_steps=1))

    def test_zero_temperature_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            validate_irradiation_policy(_policy(temperature_tolerance_c=0.0))

    def test_a_forward_limit_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_irradiation_policy(
                _policy(max_end_of_life_forward_voltage_ratio=0.9)
            )

    def test_a_leakage_limit_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_irradiation_policy(
                _policy(max_end_of_life_leakage_growth_ratio=0.5)
            )


class ReadingTests(unittest.TestCase):
    def test_the_reference_measurement_is_read_back(self):
        forward, leakage, temperature = validate_reference_measurement(_reference())
        self.assertAlmostEqual(forward, REFERENCE_VOLTAGE, places=9)
        self.assertAlmostEqual(leakage, REFERENCE_LEAKAGE, places=15)
        self.assertAlmostEqual(temperature, 25.0, places=9)

    def test_a_zero_reference_leakage_rejected(self):
        with self.assertRaises(ValueError):
            validate_reference_measurement(_reference(reverse_leakage_a=0.0))

    def test_a_missing_reference_voltage_rejected(self):
        record = _reference()
        del record["forward_voltage_v"]
        with self.assertRaises(ValueError):
            validate_reference_measurement(record)

    def test_a_step_is_read_back_in_full(self):
        fluence, forward, leakage, temperature = validate_step(_steps()[0])
        self.assertAlmostEqual(fluence, 1.0e13, places=3)
        self.assertAlmostEqual(forward, 0.714, places=9)
        self.assertAlmostEqual(leakage, 3.0e-9, places=15)
        self.assertAlmostEqual(temperature, 25.0, places=9)

    def test_a_zero_fluence_step_rejected(self):
        step = _steps()[0]
        step["fluence_e_per_cm2"] = 0.0
        with self.assertRaises(ValueError):
            validate_step(step)

    def test_a_non_mapping_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_step(["fluence_e_per_cm2"])


class StaircaseTests(unittest.TestCase):
    def test_a_rising_staircase_is_recognised(self):
        self.assertTrue(staircase_rising([1.0e13, 1.0e14, 1.0e15]))

    def test_a_repeated_exposure_is_not_a_rise(self):
        self.assertFalse(staircase_rising([1.0e13, 1.0e13, 1.0e15]))

    def test_a_falling_exposure_is_not_a_rise(self):
        self.assertFalse(staircase_rising([1.0e15, 1.0e14]))

    def test_a_single_exposure_cannot_form_a_staircase(self):
        with self.assertRaises(ValueError):
            staircase_rising([1.0e13])

    def test_two_decades_separate_two_exposures(self):
        self.assertAlmostEqual(decades_between(1.0e13, 1.0e15), 2.0, places=9)

    def test_a_reversed_span_rejected(self):
        with self.assertRaises(ValueError):
            decades_between(1.0e15, 1.0e13)

    def test_a_measurement_on_the_tolerance_edge_is_admitted(self):
        self.assertTrue(measurement_at_reference_conditions(27.0))

    def test_a_measurement_past_the_tolerance_is_refused(self):
        self.assertFalse(measurement_at_reference_conditions(40.0))


class RatioTests(unittest.TestCase):
    def test_the_forward_ratio_is_the_drop_over_its_unirradiated_value(self):
        self.assertAlmostEqual(
            forward_voltage_ratio(0.714, 0.70), 0.714 / 0.70, places=12
        )

    def test_an_unirradiated_forward_ratio_is_one(self):
        self.assertAlmostEqual(forward_voltage_ratio(0.70, 0.70), 1.0, places=12)

    def test_a_zero_reference_voltage_rejected(self):
        with self.assertRaises(ValueError):
            forward_voltage_ratio(0.714, 0.0)

    def test_the_leakage_ratio_multiplies_the_unirradiated_leakage(self):
        self.assertAlmostEqual(
            leakage_growth_ratio(3.0e-9, 1.0e-9), 3.0, places=9
        )

    def test_a_zero_step_leakage_rejected(self):
        with self.assertRaises(ValueError):
            leakage_growth_ratio(0.0, 1.0e-9)


class FitTests(unittest.TestCase):
    def test_a_straight_run_recovers_its_slope_per_decade(self):
        points = [(1.0e13, 1.02), (1.0e14, 1.04), (1.0e15, 1.06)]
        _, slope = fit_against_log_fluence(points)
        self.assertAlmostEqual(slope, 0.02, places=9)

    def test_the_fitted_line_reads_back_at_a_fitted_point(self):
        points = [(1.0e13, 1.02), (1.0e14, 1.04), (1.0e15, 1.06)]
        fit = fit_against_log_fluence(points)
        self.assertAlmostEqual(fitted_value_at_fluence(fit, 1.0e14), 1.04, places=9)

    def test_a_fit_through_one_point_rejected(self):
        with self.assertRaises(ValueError):
            fit_against_log_fluence([(1.0e13, 1.02)])

    def test_a_fit_with_no_spread_in_fluence_rejected(self):
        with self.assertRaises(ValueError):
            fit_against_log_fluence([(1.0e13, 1.02), (1.0e13, 1.04)])

    def test_a_straight_run_leaves_no_residual(self):
        points = [(1.0e13, 1.02), (1.0e14, 1.04), (1.0e15, 1.06)]
        self.assertAlmostEqual(max_relative_residual(points), 0.0, places=9)

    def test_a_kinked_run_leaves_a_residual(self):
        points = [(1.0e13, 1.02), (1.0e14, 1.04), (1.0e15, 1.40)]
        self.assertAlmostEqual(max_relative_residual(points), 0.108974359, places=6)

    def test_leakage_is_projected_as_a_power_law(self):
        points = [(1.0e13, 3.0), (1.0e14, 9.0), (1.0e15, 27.0)]
        self.assertAlmostEqual(
            projected_leakage_growth_ratio(points, 1.0e16), 81.0, places=6
        )

    def test_the_forward_projection_extends_the_line(self):
        points = [(1.0e13, 1.02), (1.0e14, 1.04), (1.0e15, 1.06)]
        self.assertAlmostEqual(
            projected_forward_voltage_ratio(points, 1.0e16), 1.08, places=9
        )

    def test_a_growing_series_is_monotonic(self):
        points = [(1.0e13, 3.0), (1.0e14, 9.0), (1.0e15, 27.0)]
        self.assertEqual(non_monotonic_fluences(points), ())

    def test_a_series_that_falls_back_names_the_step(self):
        points = [(1.0e13, 3.0), (1.0e14, 9.0), (1.0e15, 5.0)]
        self.assertEqual(non_monotonic_fluences(points), (1.0e15,))

    def test_a_flat_step_inside_the_noise_tolerance_is_admitted(self):
        points = [(1.0e13, 3.0), (1.0e14, 2.999)]
        self.assertEqual(non_monotonic_fluences(points), ())

    def test_monotonicity_needs_two_points(self):
        with self.assertRaises(ValueError):
            non_monotonic_fluences([(1.0e13, 3.0)])

    def test_the_leakage_slope_is_the_decades_gained_per_decade(self):
        points = [(1.0e13, math.log10(3.0)), (1.0e14, math.log10(9.0))]
        _, slope = fit_against_log_fluence(points)
        self.assertAlmostEqual(slope, LOG_THREE, places=9)


class RunTests(unittest.TestCase):
    def test_a_clean_exposure_is_characterized(self):
        result = assess_diode_electron_irradiation(_case())
        self.assertEqual(result["verdict"], DEGRADATION_CHARACTERIZED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(len(result["step_records"]), 4)

    def test_every_step_carries_both_damage_ratios(self):
        result = assess_diode_electron_irradiation(_case())
        first = result["step_records"][0]
        self.assertAlmostEqual(
            first["forward_voltage_ratio"], 0.714 / 0.70, places=12
        )
        self.assertAlmostEqual(first["leakage_growth_ratio"], 3.0, places=9)

    def test_the_forward_drift_per_decade_is_reported(self):
        result = assess_diode_electron_irradiation(_case())
        self.assertAlmostEqual(
            result["forward_voltage_ratio_per_decade"], 0.014 / 0.70, places=9
        )

    def test_the_leakage_gains_a_fixed_number_of_decades_per_decade(self):
        result = assess_diode_electron_irradiation(_case())
        self.assertAlmostEqual(
            result["leakage_decades_per_decade"], LOG_THREE, places=9
        )

    def test_the_end_of_life_projection_is_reported(self):
        result = assess_diode_electron_irradiation(_case())
        self.assertAlmostEqual(
            result["projected_forward_voltage_ratio"], 0.742 / 0.70, places=9
        )
        self.assertAlmostEqual(
            result["projected_leakage_growth_ratio"], 27.0, places=6
        )

    def test_a_straight_run_leaves_no_residual_in_the_result(self):
        result = assess_diode_electron_irradiation(_case())
        self.assertAlmostEqual(result["max_relative_residual"], 0.0, places=9)

    def test_a_run_with_no_unirradiated_reference_closes(self):
        case = _case()
        del case["unirradiated_reference"]
        result = assess_diode_electron_irradiation(case)
        self.assertEqual(result["verdict"], UNIRRADIATED_REFERENCE_MISSING)
        self.assertTrue(result["findings"])

    def test_too_few_steps_closes_the_run(self):
        result = assess_diode_electron_irradiation(_case(steps=_steps()[:2]))
        self.assertEqual(result["verdict"], FLUENCE_STAIRCASE_INVALID)

    def test_a_staircase_that_does_not_rise_closes_the_run(self):
        steps = _steps()
        steps[2]["fluence_e_per_cm2"] = 1.0e13
        result = assess_diode_electron_irradiation(_case(steps=steps))
        self.assertEqual(result["verdict"], FLUENCE_STAIRCASE_INVALID)

    def test_a_step_measured_warm_closes_the_run(self):
        steps = _steps()
        steps[1]["measurement_temperature_c"] = 45.0
        result = assess_diode_electron_irradiation(_case(steps=steps))
        self.assertEqual(result["verdict"], MEASUREMENT_CONDITIONS_INCONSISTENT)

    def test_a_reference_measured_warm_closes_the_run(self):
        result = assess_diode_electron_irradiation(
            _case(unirradiated_reference=_reference(measurement_temperature_c=45.0))
        )
        self.assertEqual(result["verdict"], MEASUREMENT_CONDITIONS_INCONSISTENT)

    def test_leakage_that_falls_back_closes_the_run(self):
        steps = _steps()
        steps[2]["reverse_leakage_a"] = 5.0e-9
        result = assess_diode_electron_irradiation(_case(steps=steps))
        self.assertEqual(result["verdict"], DEGRADATION_NOT_MONOTONIC)

    def test_a_forward_drop_that_recovers_closes_the_run(self):
        steps = _steps()
        steps[3]["forward_voltage_v"] = 0.715
        result = assess_diode_electron_irradiation(_case(steps=steps))
        self.assertEqual(result["verdict"], DEGRADATION_NOT_MONOTONIC)

    def test_a_step_off_its_own_curve_closes_the_run(self):
        steps = _steps()
        steps[3]["forward_voltage_v"] = 1.05
        result = assess_diode_electron_irradiation(_case(steps=steps))
        self.assertEqual(result["verdict"], STEP_OFF_DEGRADATION_CURVE)
        self.assertTrue(result["findings"])

    def test_a_far_end_of_life_fluence_exceeds_the_leakage_limit(self):
        result = assess_diode_electron_irradiation(
            _case(end_of_life_fluence_e_per_cm2=1.0e17)
        )
        self.assertEqual(result["verdict"], END_OF_LIFE_LIMIT_EXCEEDED)
        self.assertTrue(
            any("leakage" in note for note in result["findings"])
        )

    def test_both_end_of_life_limits_can_be_reported_together(self):
        result = assess_diode_electron_irradiation(
            _case(end_of_life_fluence_e_per_cm2=1.0e21)
        )
        self.assertEqual(result["verdict"], END_OF_LIFE_LIMIT_EXCEEDED)
        self.assertEqual(len(result["findings"]), 2)

    def test_a_missing_end_of_life_fluence_rejected(self):
        case = _case()
        del case["end_of_life_fluence_e_per_cm2"]
        with self.assertRaises(ValueError):
            assess_diode_electron_irradiation(case)

    def test_a_missing_steps_record_rejected(self):
        case = _case()
        del case["steps"]
        with self.assertRaises(ValueError):
            assess_diode_electron_irradiation(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_diode_electron_irradiation(["steps"])

    def test_the_end_of_life_fluence_travels_with_the_result(self):
        result = assess_diode_electron_irradiation(_case())
        self.assertAlmostEqual(
            result["end_of_life_fluence_e_per_cm2"], 1.0e15, places=1
        )


if __name__ == "__main__":
    unittest.main()
