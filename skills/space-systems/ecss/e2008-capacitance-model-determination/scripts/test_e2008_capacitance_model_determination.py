#!/usr/bin/env python3
"""Contract test for the capacitance model determination leaf (offline)."""

import copy
import math
import unittest

from e2008_capacitance_model_determination_logic import (
    ELEMENTARY_CHARGE_C,
    MAX_FORWARD_BIAS_FRACTION,
    MIN_BIAS_POINTS,
    MIN_BIAS_SPAN_V,
    MIN_FIT_QUALITY,
    MODEL_DETERMINED,
    MODEL_NOT_DETERMINED,
    MOTT_SCHOTTKY_ABRUPT,
    POWER_LAW_GRADED,
    SUPPORTED_MODELS,
    VACUUM_PERMITTIVITY_F_PER_M,
    bias_span_v,
    depletion_drive,
    determine_capacitance_model,
    distinct_bias_count,
    doping_concentration_per_m3,
    forward_bias_offenders,
    inverse_square_capacitance,
    least_squares_line,
    mott_schottky_fit,
    power_law_fit,
    validate_bias_sweep,
)

JUNCTION_AREA_M2 = 4.0e-4
RELATIVE_PERMITTIVITY = 13.1
BUILT_IN_VOLTAGE_V = 1.35
DOPING_PER_M3 = 1.0e22


def _slope_constant(built_in_voltage_v=BUILT_IN_VOLTAGE_V, doping=DOPING_PER_M3):
    """The 2 / (q eps A^2 N) factor the synthetic sweep is generated from."""
    epsilon = RELATIVE_PERMITTIVITY * VACUUM_PERMITTIVITY_F_PER_M
    return 2.0 / (
        ELEMENTARY_CHARGE_C
        * epsilon
        * JUNCTION_AREA_M2
        * JUNCTION_AREA_M2
        * doping
    )


def _abrupt_sweep(biases, built_in_voltage_v=BUILT_IN_VOLTAGE_V, doping=DOPING_PER_M3):
    """Readings taken from an exact abrupt-junction depletion model."""
    constant = _slope_constant(built_in_voltage_v, doping)
    readings = []
    for bias in biases:
        inverse_square = constant * (built_in_voltage_v - bias)
        readings.append(
            {
                "bias_voltage_v": bias,
                "capacitance_f": 1.0 / math.sqrt(inverse_square),
            }
        )
    return readings


def _graded_sweep(biases, grading_coefficient, zero_bias_capacitance_f=1.0e-7):
    """Readings taken from an exact graded power-law model."""
    readings = []
    for bias in biases:
        drive = 1.0 - bias / BUILT_IN_VOLTAGE_V
        readings.append(
            {
                "bias_voltage_v": bias,
                "capacitance_f": zero_bias_capacitance_f
                * drive ** (-grading_coefficient),
            }
        )
    return readings


REVERSE_BIASES = (-3.0, -2.5, -2.0, -1.5, -1.0, -0.5, 0.0)

BASE_CASE = {
    "model_form": MOTT_SCHOTTKY_ABRUPT,
    "readings": _abrupt_sweep(REVERSE_BIASES),
    "junction_area_m2": JUNCTION_AREA_M2,
    "relative_permittivity": RELATIVE_PERMITTIVITY,
}


def _case(**overrides):
    case = copy.deepcopy(BASE_CASE)
    case.update(overrides)
    return case


class SweepValidationTests(unittest.TestCase):
    def test_a_sweep_is_returned_sorted_by_bias(self):
        points = validate_bias_sweep(_abrupt_sweep((0.0, -2.0, -1.0)))
        self.assertEqual([bias for bias, _ in points], [-2.0, -1.0, 0.0])

    def test_a_pair_form_reading_is_accepted_alongside_a_mapping(self):
        points = validate_bias_sweep([(-1.0, 1.0e-7), {"bias_voltage_v": 0.0, "capacitance_f": 2.0e-7}])
        self.assertEqual(len(points), 2)

    def test_a_repeated_bias_point_is_refused(self):
        with self.assertRaises(ValueError):
            validate_bias_sweep([(-1.0, 1.0e-7), (-1.0, 1.1e-7)])

    def test_a_non_positive_capacitance_is_refused(self):
        with self.assertRaises(ValueError):
            validate_bias_sweep([(-1.0, 0.0), (0.0, 1.0e-7)])

    def test_an_empty_sweep_is_refused(self):
        with self.assertRaises(ValueError):
            validate_bias_sweep([])

    def test_a_reading_that_is_neither_mapping_nor_pair_is_refused(self):
        with self.assertRaises(ValueError):
            validate_bias_sweep([("minus one volt",)])

    def test_the_span_is_the_distance_between_the_end_points(self):
        self.assertAlmostEqual(bias_span_v(BASE_CASE["readings"]), 3.0, places=12)

    def test_the_point_count_is_the_number_of_distinct_biases(self):
        self.assertEqual(distinct_bias_count(BASE_CASE["readings"]), len(REVERSE_BIASES))


class LineFittingTests(unittest.TestCase):
    def test_the_ordinate_is_one_over_capacitance_squared(self):
        self.assertAlmostEqual(
            inverse_square_capacitance(2.0e-7), 1.0 / (2.0e-7 * 2.0e-7), places=3
        )

    def test_a_zero_capacitance_has_no_ordinate(self):
        with self.assertRaises(ValueError):
            inverse_square_capacitance(0.0)

    def test_an_exact_line_is_recovered_with_unit_fit_quality(self):
        fit = least_squares_line((0.0, 1.0, 2.0, 3.0), (1.0, 3.0, 5.0, 7.0))
        self.assertAlmostEqual(fit["slope"], 2.0, places=9)
        self.assertAlmostEqual(fit["intercept"], 1.0, places=9)
        self.assertAlmostEqual(fit["r_squared"], 1.0, places=9)

    def test_mismatched_sample_lengths_are_refused(self):
        with self.assertRaises(ValueError):
            least_squares_line((0.0, 1.0), (1.0,))

    def test_a_sweep_that_never_moves_in_bias_has_no_line(self):
        with self.assertRaises(ValueError):
            least_squares_line((1.0, 1.0, 1.0), (1.0, 2.0, 3.0))

    def test_a_single_sample_cannot_form_a_line(self):
        with self.assertRaises(ValueError):
            least_squares_line((1.0,), (2.0,))


class MottSchottkyTests(unittest.TestCase):
    def test_the_fit_recovers_the_built_in_voltage_of_the_synthetic_sweep(self):
        fit = mott_schottky_fit(BASE_CASE["readings"])
        self.assertAlmostEqual(fit["built_in_voltage_v"], BUILT_IN_VOLTAGE_V, places=9)

    def test_an_exact_depletion_sweep_fits_the_line_perfectly(self):
        fit = mott_schottky_fit(BASE_CASE["readings"])
        self.assertAlmostEqual(fit["r_squared"], 1.0, places=9)

    def test_the_fitted_slope_falls_with_forward_bias(self):
        fit = mott_schottky_fit(BASE_CASE["readings"])
        self.assertLess(fit["slope_per_volt"], 0.0)

    def test_a_capacitance_rising_with_reverse_bias_is_refused(self):
        rising = [
            {"bias_voltage_v": bias, "capacitance_f": 1.0e-7 * (1.0 - bias)}
            for bias in (-3.0, -2.0, -1.0, 0.0)
        ]
        with self.assertRaises(ValueError):
            mott_schottky_fit(rising)

    def test_the_slope_returns_the_doping_the_sweep_was_built_from(self):
        fit = mott_schottky_fit(BASE_CASE["readings"])
        doping = doping_concentration_per_m3(
            fit["slope_per_volt"], JUNCTION_AREA_M2, RELATIVE_PERMITTIVITY
        )
        self.assertAlmostEqual(doping / DOPING_PER_M3, 1.0, places=9)

    def test_a_flat_line_carries_no_doping(self):
        with self.assertRaises(ValueError):
            doping_concentration_per_m3(0.0, JUNCTION_AREA_M2, RELATIVE_PERMITTIVITY)

    def test_a_zero_junction_area_is_refused(self):
        with self.assertRaises(ValueError):
            doping_concentration_per_m3(-1.0e13, 0.0, RELATIVE_PERMITTIVITY)


class PowerLawTests(unittest.TestCase):
    def test_the_drive_term_is_one_at_zero_bias(self):
        self.assertAlmostEqual(depletion_drive(0.0, BUILT_IN_VOLTAGE_V), 1.0, places=12)

    def test_a_bias_at_the_built_in_voltage_has_no_drive(self):
        with self.assertRaises(ValueError):
            depletion_drive(BUILT_IN_VOLTAGE_V, BUILT_IN_VOLTAGE_V)

    def test_an_abrupt_sweep_returns_a_grading_coefficient_of_one_half(self):
        graded = power_law_fit(BASE_CASE["readings"], BUILT_IN_VOLTAGE_V)
        self.assertAlmostEqual(graded["grading_coefficient"], 0.5, places=7)

    def test_a_linearly_graded_sweep_returns_one_third(self):
        readings = _graded_sweep(REVERSE_BIASES, 1.0 / 3.0)
        graded = power_law_fit(readings, BUILT_IN_VOLTAGE_V)
        self.assertAlmostEqual(graded["grading_coefficient"], 1.0 / 3.0, places=7)

    def test_the_intercept_returns_the_zero_bias_capacitance(self):
        readings = _graded_sweep(REVERSE_BIASES, 1.0 / 3.0, 8.0e-8)
        graded = power_law_fit(readings, BUILT_IN_VOLTAGE_V)
        self.assertAlmostEqual(graded["zero_bias_capacitance_f"] / 8.0e-8, 1.0, places=7)

    def test_a_power_law_fit_needs_a_positive_built_in_voltage(self):
        with self.assertRaises(ValueError):
            power_law_fit(BASE_CASE["readings"], 0.0)


class ForwardBiasTests(unittest.TestCase):
    def test_a_reverse_only_sweep_has_no_offenders(self):
        self.assertEqual(
            forward_bias_offenders(BASE_CASE["readings"], BUILT_IN_VOLTAGE_V), ()
        )

    def test_a_point_beyond_the_forward_ceiling_is_an_offender(self):
        readings = _abrupt_sweep(REVERSE_BIASES + (0.9,))
        offenders = forward_bias_offenders(readings, BUILT_IN_VOLTAGE_V)
        self.assertEqual(len(offenders), 1)
        self.assertAlmostEqual(offenders[0][0], 0.9, places=12)

    def test_a_point_landing_exactly_on_the_forward_ceiling_is_kept(self):
        ceiling = MAX_FORWARD_BIAS_FRACTION * BUILT_IN_VOLTAGE_V
        readings = _abrupt_sweep(REVERSE_BIASES + (ceiling,))
        self.assertEqual(
            forward_bias_offenders(readings, BUILT_IN_VOLTAGE_V), ()
        )


class DeterminationTests(unittest.TestCase):
    def test_a_clean_reverse_sweep_determines_the_abrupt_model(self):
        result = determine_capacitance_model(BASE_CASE)
        self.assertEqual(result["verdict"], MODEL_DETERMINED)
        self.assertTrue(result["determined"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(
            result["parameters"]["built_in_voltage_v"], BUILT_IN_VOLTAGE_V, places=9
        )

    def test_the_graded_form_adds_a_grading_coefficient_to_the_parameters(self):
        result = determine_capacitance_model(_case(model_form=POWER_LAW_GRADED))
        self.assertEqual(result["verdict"], MODEL_DETERMINED)
        self.assertAlmostEqual(
            result["parameters"]["grading_coefficient"], 0.5, places=7
        )

    def test_too_few_bias_points_stop_the_determination(self):
        result = determine_capacitance_model(
            _case(readings=_abrupt_sweep((-3.0, -2.0, -1.0, 0.0)))
        )
        self.assertEqual(result["verdict"], MODEL_NOT_DETERMINED)
        self.assertTrue(any("bias points" in f for f in result["findings"]))
        self.assertLess(result["bias_point_count"], MIN_BIAS_POINTS)

    def test_a_span_landing_exactly_on_the_floor_is_accepted(self):
        readings = _abrupt_sweep((-0.5, -0.375, -0.25, -0.125, 0.0))
        result = determine_capacitance_model(_case(readings=readings))
        self.assertAlmostEqual(result["bias_span_v"], MIN_BIAS_SPAN_V, places=9)
        self.assertEqual(result["verdict"], MODEL_DETERMINED)

    def test_a_span_under_the_floor_is_a_finding(self):
        readings = _abrupt_sweep((-0.2, -0.15, -0.1, -0.05, 0.0))
        result = determine_capacitance_model(_case(readings=readings))
        self.assertEqual(result["verdict"], MODEL_NOT_DETERMINED)
        self.assertTrue(any("bias span" in f for f in result["findings"]))

    def test_scattered_readings_fail_the_fit_quality_floor(self):
        readings = _abrupt_sweep(REVERSE_BIASES)
        readings[2]["capacitance_f"] *= 0.85
        readings[4]["capacitance_f"] *= 1.2
        result = determine_capacitance_model(_case(readings=readings))
        self.assertEqual(result["verdict"], MODEL_NOT_DETERMINED)
        self.assertLess(
            result["parameters"]["mott_schottky_r_squared"], MIN_FIT_QUALITY
        )

    def test_a_forward_point_is_reported_against_the_determination(self):
        result = determine_capacitance_model(
            _case(readings=_abrupt_sweep(REVERSE_BIASES + (0.9,)))
        )
        self.assertEqual(result["verdict"], MODEL_NOT_DETERMINED)
        self.assertEqual(result["forward_bias_offender_count"], 1)
        self.assertTrue(any("diffusion capacitance" in f for f in result["findings"]))

    def test_an_implausible_built_in_voltage_is_a_finding(self):
        readings = _abrupt_sweep(REVERSE_BIASES, built_in_voltage_v=4.5)
        result = determine_capacitance_model(_case(readings=readings))
        self.assertEqual(result["verdict"], MODEL_NOT_DETERMINED)
        self.assertTrue(any("built-in voltage" in f for f in result["findings"]))

    def test_an_unknown_model_form_is_refused(self):
        with self.assertRaises(ValueError):
            determine_capacitance_model(_case(model_form="two-point-ratio"))

    def test_a_case_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            determine_capacitance_model("mott-schottky-abrupt")

    def test_a_missing_junction_area_stops_the_determination(self):
        case = _case()
        del case["junction_area_m2"]
        with self.assertRaises(ValueError):
            determine_capacitance_model(case)

    def test_both_supported_forms_are_reachable_from_the_determination(self):
        for form in SUPPORTED_MODELS:
            result = determine_capacitance_model(_case(model_form=form))
            self.assertEqual(result["model_form"], form)


if __name__ == "__main__":
    unittest.main()
