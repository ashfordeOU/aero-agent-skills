"""Contract tests for the clause 7.5.13 bare-cell electron irradiation test."""

import unittest

from e2008_cell_electron_irradiation_test_logic import (
    FACTOR_TOLERANCE,
    IRRADIANCE_TOLERANCE_W_M2,
    MAX_FIT_RESIDUAL,
    NOISE_ALLOWANCE,
    PARAMETERS,
    TEMPERATURE_TOLERANCE_C,
    assess_cell_electron_irradiation,
    condition_findings,
    fit_log_degradation,
    monotonicity_findings,
    predict_remaining,
    remaining_factor,
    remaining_series,
    residual_findings,
    retention_lost_per_decade,
    validate_fluence_steps,
)

REFERENCE_VALUES = {
    "short-circuit-current": 500.0,
    "open-circuit-voltage": 2.700,
    "maximum-power": 1.200,
}
FLUENCES = [1.0e13, 1.0e14, 1.0e15]
STEP_VALUES = [
    {
        "short-circuit-current": 490.0,
        "open-circuit-voltage": 2.619,
        "maximum-power": 1.140,
    },
    {
        "short-circuit-current": 480.0,
        "open-circuit-voltage": 2.538,
        "maximum-power": 1.080,
    },
    {
        "short-circuit-current": 470.0,
        "open-circuit-voltage": 2.457,
        "maximum-power": 1.020,
    },
]
POWER_FACTORS = [0.95, 0.90, 0.85]
REFERENCE = {
    "label": "unirradiated",
    "temperature_c": 28.0,
    "irradiance_w_m2": 1367.0,
    "values": dict(REFERENCE_VALUES),
}


def step(index):
    return {
        "label": "step-%d" % (index + 1),
        "fluence_e_per_cm2": FLUENCES[index],
        "temperature_c": 28.0,
        "irradiance_w_m2": 1367.0,
        "values": dict(STEP_VALUES[index]),
    }


class FluenceStaircaseTests(unittest.TestCase):
    def test_rising_steps_are_returned_as_floats(self):
        self.assertEqual(validate_fluence_steps([1, 2, 3]), [1.0, 2.0, 3.0])

    def test_repeated_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_fluence_steps([1.0e13, 1.0e13])

    def test_falling_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_fluence_steps([1.0e14, 1.0e13])

    def test_single_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_fluence_steps([1.0e13])

    def test_zero_fluence_rejected(self):
        with self.assertRaises(ValueError):
            validate_fluence_steps([0.0, 1.0e13])

    def test_boolean_fluence_rejected(self):
        with self.assertRaises(ValueError):
            validate_fluence_steps([True, 1.0e13])


class RemainingFactorTests(unittest.TestCase):
    def test_factor_is_measured_over_reference(self):
        self.assertAlmostEqual(remaining_factor(490.0, 500.0), 0.98, places=9)

    def test_unchanged_reading_gives_unity(self):
        self.assertAlmostEqual(remaining_factor(500.0, 500.0), 1.0, places=9)

    def test_zero_reference_rejected(self):
        with self.assertRaises(ValueError):
            remaining_factor(490.0, 0.0)

    def test_negative_reading_rejected(self):
        with self.assertRaises(ValueError):
            remaining_factor(-490.0, 500.0)

    def test_three_parameters_are_named(self):
        self.assertEqual(len(PARAMETERS), 3)
        self.assertIn("maximum-power", PARAMETERS)

    def test_series_covers_every_parameter_and_step(self):
        series = remaining_series(REFERENCE_VALUES, STEP_VALUES)
        self.assertEqual(sorted(series), sorted(PARAMETERS))
        for values in series.values():
            self.assertEqual(len(values), 3)

    def test_series_power_factors(self):
        series = remaining_series(REFERENCE_VALUES, STEP_VALUES)
        for measured, expected in zip(series["maximum-power"], POWER_FACTORS):
            self.assertAlmostEqual(measured, expected, places=9)

    def test_reading_missing_a_parameter_rejected(self):
        with self.assertRaises(ValueError):
            remaining_series(REFERENCE_VALUES, [{"maximum-power": 1.1}])

    def test_reading_with_an_unknown_parameter_rejected(self):
        reading = dict(STEP_VALUES[0])
        reading["fill-factor"] = 0.8
        with self.assertRaises(ValueError):
            remaining_series(REFERENCE_VALUES, [reading])

    def test_empty_step_list_rejected(self):
        with self.assertRaises(ValueError):
            remaining_series(REFERENCE_VALUES, [])


class ConditionTests(unittest.TestCase):
    def test_matching_conditions_give_no_finding(self):
        self.assertEqual(condition_findings(step(0), REFERENCE), [])

    def test_temperature_exactly_on_the_tolerance_is_accepted(self):
        warm = step(0)
        warm["temperature_c"] = 28.0 + TEMPERATURE_TOLERANCE_C
        self.assertEqual(condition_findings(warm, REFERENCE), [])

    def test_hot_measurement_is_a_finding(self):
        warm = step(0)
        warm["temperature_c"] = 45.0
        findings = condition_findings(warm, REFERENCE)
        self.assertEqual(len(findings), 1)
        self.assertIn("C", findings[0])

    def test_off_irradiance_is_a_finding(self):
        dim = step(0)
        dim["irradiance_w_m2"] = 1000.0
        findings = condition_findings(dim, REFERENCE)
        self.assertEqual(len(findings), 1)
        self.assertIn("W/m2", findings[0])

    def test_both_conditions_off_give_two_findings(self):
        bad = step(0)
        bad["temperature_c"] = 60.0
        bad["irradiance_w_m2"] = 900.0
        self.assertEqual(len(condition_findings(bad, REFERENCE)), 2)

    def test_measurement_without_a_temperature_rejected(self):
        bad = step(0)
        del bad["temperature_c"]
        with self.assertRaises(ValueError):
            condition_findings(bad, REFERENCE)

    def test_default_condition_tolerances(self):
        self.assertAlmostEqual(TEMPERATURE_TOLERANCE_C, 2.0, places=9)
        self.assertAlmostEqual(IRRADIANCE_TOLERANCE_W_M2, 10.0, places=9)


class MonotonicityTests(unittest.TestCase):
    def test_falling_factors_give_no_finding(self):
        self.assertEqual(
            monotonicity_findings("maximum-power", FLUENCES, POWER_FACTORS), []
        )

    def test_recovered_factor_is_a_finding(self):
        findings = monotonicity_findings(
            "maximum-power", FLUENCES, [0.95, 0.80, 0.90]
        )
        self.assertTrue(any("recovered" in item for item in findings))

    def test_factor_above_unity_is_a_finding(self):
        findings = monotonicity_findings(
            "short-circuit-current", FLUENCES, [1.05, 0.96, 0.94]
        )
        self.assertTrue(
            any("starting point" in item for item in findings)
        )

    def test_rise_inside_the_noise_allowance_is_accepted(self):
        factors = [0.95, 0.90, 0.90 + NOISE_ALLOWANCE / 2.0]
        self.assertEqual(
            monotonicity_findings("maximum-power", FLUENCES, factors), []
        )

    def test_default_noise_allowance(self):
        self.assertAlmostEqual(NOISE_ALLOWANCE, 0.002, places=9)

    def test_unknown_parameter_rejected(self):
        with self.assertRaises(ValueError):
            monotonicity_findings("fill-factor", FLUENCES, POWER_FACTORS)

    def test_factor_count_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            monotonicity_findings("maximum-power", FLUENCES, [0.95, 0.90])

    def test_factor_tolerance_is_small(self):
        self.assertAlmostEqual(FACTOR_TOLERANCE, 1e-9, places=12)


class FitTests(unittest.TestCase):
    def setUp(self):
        self.fit = fit_log_degradation(FLUENCES, POWER_FACTORS)

    def test_fit_reproduces_every_measured_point(self):
        for fluence, factor in zip(FLUENCES, POWER_FACTORS):
            self.assertAlmostEqual(
                predict_remaining(self.fit, fluence), factor, places=9
            )

    def test_fit_slope_is_negative(self):
        self.assertLess(self.fit["slope"], -0.001)

    def test_point_count_is_reported(self):
        self.assertEqual(self.fit["point_count"], 3)

    def test_retention_lost_per_decade(self):
        self.assertAlmostEqual(
            retention_lost_per_decade(self.fit), 0.05, places=9
        )

    def test_next_decade_costs_the_same_retention(self):
        self.assertAlmostEqual(
            predict_remaining(self.fit, 1.0e16), 0.80, places=9
        )

    def test_prediction_at_zero_fluence_rejected(self):
        with self.assertRaises(ValueError):
            predict_remaining(self.fit, 0.0)

    def test_fit_without_a_slope_rejected(self):
        with self.assertRaises(ValueError):
            predict_remaining({"intercept": 1.0}, 1.0e13)

    def test_fit_with_mismatched_factors_rejected(self):
        with self.assertRaises(ValueError):
            fit_log_degradation(FLUENCES, [0.95, 0.90])

    def test_retention_per_decade_needs_a_slope(self):
        with self.assertRaises(ValueError):
            retention_lost_per_decade({"intercept": 1.0})


class ResidualTests(unittest.TestCase):
    def test_points_on_the_fit_give_no_finding(self):
        fit = fit_log_degradation(FLUENCES, POWER_FACTORS)
        self.assertEqual(
            residual_findings("maximum-power", FLUENCES, POWER_FACTORS, fit), []
        )

    def test_outlier_step_is_a_finding(self):
        factors = [0.95, 0.60, 0.85]
        fit = fit_log_degradation(FLUENCES, factors)
        findings = residual_findings(
            "maximum-power", FLUENCES, factors, fit
        )
        self.assertTrue(findings)
        self.assertIn("off the", findings[0])

    def test_default_residual_allowance(self):
        self.assertAlmostEqual(MAX_FIT_RESIDUAL, 0.02, places=9)

    def test_residual_allowance_must_be_positive(self):
        fit = fit_log_degradation(FLUENCES, POWER_FACTORS)
        with self.assertRaises(ValueError):
            residual_findings(
                "maximum-power", FLUENCES, POWER_FACTORS, fit, max_residual=0.0
            )


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "reference_measurement": {
                "label": "unirradiated",
                "temperature_c": 28.0,
                "irradiance_w_m2": 1367.0,
                "values": dict(REFERENCE_VALUES),
            },
            "steps": [step(0), step(1), step(2)],
            "eol_fluence_e_per_cm2": 1.0e16,
            "required_retention": {"maximum-power": 0.78},
        }
        spec.update(overrides)
        return spec

    def test_conformant_run_has_no_finding(self):
        result = assess_cell_electron_irradiation(self._spec())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["run_conformant"])

    def test_every_parameter_is_reported(self):
        result = assess_cell_electron_irradiation(self._spec())
        self.assertEqual(sorted(result["parameters"]), sorted(PARAMETERS))
        self.assertEqual(result["step_count"], 3)

    def test_projected_power_retention_is_reported(self):
        result = assess_cell_electron_irradiation(self._spec())
        power = result["parameters"]["maximum-power"]
        self.assertAlmostEqual(power["projected_remaining"], 0.80, places=9)
        self.assertAlmostEqual(
            power["retention_lost_per_decade"], 0.05, places=9
        )

    def test_retention_shortfall_fails_the_run(self):
        result = assess_cell_electron_irradiation(
            self._spec(required_retention={"maximum-power": 0.90})
        )
        self.assertFalse(result["run_conformant"])
        self.assertTrue(
            any("budget asks for" in item for item in result["findings"])
        )

    def test_hot_step_fails_the_run(self):
        spec = self._spec()
        spec["steps"][1]["temperature_c"] = 55.0
        result = assess_cell_electron_irradiation(spec)
        self.assertFalse(result["run_conformant"])

    def test_recovered_power_fails_the_run(self):
        spec = self._spec()
        spec["steps"][2]["values"]["maximum-power"] = 1.180
        result = assess_cell_electron_irradiation(spec)
        self.assertFalse(result["run_conformant"])

    def test_end_of_life_below_the_last_step_is_a_finding(self):
        result = assess_cell_electron_irradiation(
            self._spec(eol_fluence_e_per_cm2=1.0e14)
        )
        self.assertTrue(
            any("extrapolation backwards" in item
                for item in result["findings"])
        )

    def test_single_step_run_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell_electron_irradiation(self._spec(steps=[step(0)]))

    def test_missing_spec_key_rejected(self):
        spec = self._spec()
        del spec["eol_fluence_e_per_cm2"]
        with self.assertRaises(ValueError):
            assess_cell_electron_irradiation(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell_electron_irradiation(["steps"])

    def test_empty_retention_requirement_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell_electron_irradiation(self._spec(required_retention={}))

    def test_unknown_retention_parameter_rejected(self):
        with self.assertRaises(ValueError):
            assess_cell_electron_irradiation(
                self._spec(required_retention={"fill-factor": 0.8})
            )

    def test_step_without_a_fluence_rejected(self):
        spec = self._spec()
        del spec["steps"][0]["fluence_e_per_cm2"]
        with self.assertRaises(ValueError):
            assess_cell_electron_irradiation(spec)


if __name__ == "__main__":
    unittest.main()
