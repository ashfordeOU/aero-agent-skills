"""Contract tests for the clause 7.5.4 bare cell temperature coefficient logic."""

import unittest

from e2008_bare_cell_temperature_coefficients_logic import (
    DEFAULT_REFERENCE_TEMPERATURE_C,
    MIN_POINT_SEPARATION_C,
    assess_bare_cell_temperature_coefficients,
    derive_coefficient,
    distinct_temperature_count,
    evaluate_sample_coefficients,
    fit_quality,
    least_squares_fit,
    relative_coefficient_per_c,
    temperature_span_c,
    validate_sample_eligibility,
    value_at_temperature,
)

TEMPERATURES = [-20.0, 0.0, 28.0, 55.0, 80.0]
ALPHA_ISC = 0.00025
BETA_VOC = -0.0060
DELTA_PMPP = -0.0040


def _point(temperature_c):
    delta = temperature_c - DEFAULT_REFERENCE_TEMPERATURE_C
    return {
        "temperature_c": temperature_c,
        "isc_a": 0.500 + ALPHA_ISC * delta,
        "voc_v": 2.700 + BETA_VOC * delta,
        "pmpp_w": 1.150 + DELTA_PMPP * delta,
    }


def _sample(sample_id="QSG-01", temperatures=None, **overrides):
    sample = {
        "id": sample_id,
        "irradiated": True,
        "points": [_point(t) for t in (temperatures or TEMPERATURES)],
    }
    sample.update(overrides)
    return sample


def _spec(**overrides):
    spec = {
        "samples": [_sample("QSG-01"), _sample("QSG-02")],
        "subgroup_ids": ["QSG-01", "QSG-02"],
    }
    spec.update(overrides)
    return spec


class LeastSquaresTests(unittest.TestCase):
    def test_slope_and_intercept_of_an_exactly_linear_set(self):
        slope, intercept = least_squares_fit([0.0, 10.0, 20.0], [1.0, 3.0, 5.0])
        self.assertAlmostEqual(slope, 0.2, places=9)
        self.assertAlmostEqual(intercept, 1.0, places=9)

    def test_slope_recovers_the_declared_current_coefficient(self):
        currents = [_point(t)["isc_a"] for t in TEMPERATURES]
        slope, _ = least_squares_fit(TEMPERATURES, currents)
        self.assertAlmostEqual(slope, ALPHA_ISC, places=9)

    def test_slope_recovers_the_declared_voltage_coefficient(self):
        voltages = [_point(t)["voc_v"] for t in TEMPERATURES]
        slope, _ = least_squares_fit(TEMPERATURES, voltages)
        self.assertAlmostEqual(slope, BETA_VOC, places=9)

    def test_readings_all_at_one_temperature_have_no_slope(self):
        with self.assertRaises(ValueError):
            least_squares_fit([28.0, 28.0, 28.0], [1.0, 1.1, 0.9])

    def test_mismatched_series_lengths_are_rejected(self):
        with self.assertRaises(ValueError):
            least_squares_fit([0.0, 10.0, 20.0], [1.0, 3.0])

    def test_single_point_is_rejected(self):
        with self.assertRaises(ValueError):
            least_squares_fit([28.0], [0.5])

    def test_boolean_reading_is_rejected(self):
        with self.assertRaises(ValueError):
            least_squares_fit([0.0, 10.0], [1.0, True])


class FitQualityTests(unittest.TestCase):
    def test_exactly_linear_set_is_fully_accounted_for(self):
        powers = [_point(t)["pmpp_w"] for t in TEMPERATURES]
        slope, intercept = least_squares_fit(TEMPERATURES, powers)
        self.assertAlmostEqual(
            fit_quality(TEMPERATURES, powers, slope, intercept), 1.0, places=9
        )

    def test_scattered_set_is_only_partly_accounted_for(self):
        values = [1.40, 0.90, 1.30, 0.80, 1.00]
        slope, intercept = least_squares_fit(TEMPERATURES, values)
        self.assertLess(fit_quality(TEMPERATURES, values, slope, intercept), 0.9)

    def test_flat_series_with_a_flat_line_is_fully_accounted_for(self):
        self.assertAlmostEqual(
            fit_quality([0.0, 10.0, 20.0], [2.0, 2.0, 2.0], 0.0, 2.0), 1.0, places=9
        )

    def test_fitted_value_lands_on_the_line(self):
        self.assertAlmostEqual(value_at_temperature(0.2, 1.0, 20.0), 5.0, places=9)


class TemperatureSetTests(unittest.TestCase):
    def test_span_is_the_width_of_the_set(self):
        self.assertAlmostEqual(temperature_span_c(TEMPERATURES), 100.0, places=9)

    def test_well_separated_readings_all_count(self):
        self.assertEqual(distinct_temperature_count(TEMPERATURES), 5)

    def test_clustered_readings_collapse_to_one_point(self):
        clustered = [20.0, 20.1, 20.2, 20.3]
        self.assertEqual(distinct_temperature_count(clustered), 1)

    def test_readings_exactly_on_the_separation_edge_are_separate(self):
        edge = [0.0, MIN_POINT_SEPARATION_C, 2.0 * MIN_POINT_SEPARATION_C]
        self.assertEqual(distinct_temperature_count(edge), 3)

    def test_empty_temperature_set_is_rejected(self):
        with self.assertRaises(ValueError):
            temperature_span_c([])


class RelativeCoefficientTests(unittest.TestCase):
    def test_relative_current_coefficient_against_the_reference_value(self):
        self.assertAlmostEqual(
            relative_coefficient_per_c(ALPHA_ISC, 0.500), ALPHA_ISC / 0.500, places=9
        )

    def test_relative_coefficient_against_zero_is_undefined(self):
        with self.assertRaises(ValueError):
            relative_coefficient_per_c(ALPHA_ISC, 0.0)

    def test_derived_coefficient_carries_slope_quality_and_reference_value(self):
        currents = [_point(t)["isc_a"] for t in TEMPERATURES]
        derived = derive_coefficient(TEMPERATURES, currents)
        self.assertAlmostEqual(derived["slope_per_c"], ALPHA_ISC, places=9)
        self.assertAlmostEqual(derived["fit_quality"], 1.0, places=9)
        self.assertAlmostEqual(derived["value_at_reference"], 0.500, places=9)
        self.assertAlmostEqual(derived["relative_per_c"], ALPHA_ISC / 0.500, places=9)


class EligibilityTests(unittest.TestCase):
    def test_irradiated_subgroup_member_raises_no_finding(self):
        sample_id, findings = validate_sample_eligibility(
            _sample("QSG-01"), ["QSG-01", "QSG-02"]
        )
        self.assertEqual(sample_id, "QSG-01")
        self.assertEqual(findings, [])

    def test_pristine_sample_is_a_finding(self):
        _, findings = validate_sample_eligibility(_sample(irradiated=False))
        self.assertTrue(any("irradiation" in item for item in findings))

    def test_sample_outside_the_subgroup_is_a_finding(self):
        _, findings = validate_sample_eligibility(_sample("OTHER-09"), ["QSG-01"])
        self.assertTrue(any("subgroup" in item for item in findings))

    def test_non_boolean_irradiation_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample_eligibility(_sample(irradiated="yes"))

    def test_empty_sample_id_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample_eligibility(_sample(id="  "))


class SampleCoefficientTests(unittest.TestCase):
    def test_clean_sample_conforms_with_all_three_coefficients(self):
        record = evaluate_sample_coefficients(_sample(), None, ["QSG-01"])
        self.assertTrue(record["conforms"])
        self.assertEqual(sorted(record["coefficients"]), ["isc_a", "pmpp_w", "voc_v"])
        self.assertAlmostEqual(
            record["coefficients"]["voc_v"]["slope_per_c"], BETA_VOC, places=9
        )

    def test_narrow_temperature_span_is_a_finding(self):
        record = evaluate_sample_coefficients(
            _sample(temperatures=[24.0, 26.0, 28.0, 30.0, 32.0])
        )
        self.assertFalse(record["conforms"])
        self.assertTrue(any("narrower" in item for item in record["findings"]))

    def test_too_few_separate_temperatures_is_a_finding(self):
        record = evaluate_sample_coefficients(
            _sample(temperatures=[-20.0, -19.5, 80.0])
        )
        self.assertTrue(any("separate temperatures" in item for item in record["findings"]))

    def test_voltage_coefficient_of_the_wrong_sign_is_a_finding(self):
        sample = _sample()
        for point in sample["points"]:
            delta = point["temperature_c"] - DEFAULT_REFERENCE_TEMPERATURE_C
            point["voc_v"] = 2.700 - BETA_VOC * delta
        record = evaluate_sample_coefficients(sample)
        self.assertFalse(record["coefficients"]["voc_v"]["sign_as_expected"])
        self.assertTrue(any("expected sign" in item for item in record["findings"]))

    def test_scattered_power_fails_the_fit_quality_floor(self):
        sample = _sample()
        for point, power in zip(sample["points"], [1.40, 0.90, 1.30, 0.80, 1.00]):
            point["pmpp_w"] = power
        record = evaluate_sample_coefficients(sample)
        self.assertTrue(any("its own spread" in item for item in record["findings"]))

    def test_missing_point_key_is_rejected(self):
        sample = _sample()
        del sample["points"][0]["voc_v"]
        with self.assertRaises(ValueError):
            evaluate_sample_coefficients(sample)

    def test_empty_point_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_sample_coefficients(_sample(points=[]))

    def test_minimum_point_count_below_two_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_sample_coefficients(_sample(), {"min_points": 1})


class SubgroupAssessmentTests(unittest.TestCase):
    def test_clean_subgroup_is_valid(self):
        result = assess_bare_cell_temperature_coefficients(_spec())
        self.assertTrue(result["valid"])
        self.assertEqual(result["samples_measured"], 2)
        self.assertEqual(result["unmeasured_subgroup_ids"], [])

    def test_unmeasured_subgroup_member_is_reported(self):
        result = assess_bare_cell_temperature_coefficients(
            _spec(subgroup_ids=["QSG-01", "QSG-02", "QSG-07"])
        )
        self.assertEqual(result["unmeasured_subgroup_ids"], ["QSG-07"])
        self.assertFalse(result["valid"])

    def test_pristine_sample_invalidates_the_subgroup(self):
        result = assess_bare_cell_temperature_coefficients(
            _spec(samples=[_sample("QSG-01"), _sample("QSG-02", irradiated=False)])
        )
        self.assertEqual(result["samples_rejected"], 1)
        self.assertFalse(result["valid"])

    def test_duplicate_sample_id_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_temperature_coefficients(
                _spec(samples=[_sample("QSG-01"), _sample("QSG-01")])
            )

    def test_empty_sample_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_temperature_coefficients(_spec(samples=[]))

    def test_non_mapping_spec_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_temperature_coefficients(["samples"])

    def test_subgroup_roster_defaults_to_empty(self):
        spec = _spec()
        del spec["subgroup_ids"]
        result = assess_bare_cell_temperature_coefficients(spec)
        self.assertEqual(result["subgroup_roster"], [])
        self.assertTrue(result["valid"])


if __name__ == "__main__":
    unittest.main()
