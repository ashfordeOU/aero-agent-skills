"""Contract test for the q2007-environment leaf (stdlib unittest)."""

import unittest

from q2007_environment_logic import (
    FINDING_EXCURSION,
    FINDING_INTERVAL_TOO_LONG,
    FINDING_NOT_CONTAINED_HIGH,
    FINDING_NOT_CONTAINED_LOW,
    FINDING_NO_CAPABILITY,
    FINDING_NO_MONITORING,
    PARAMETER_UNITS,
    assess_parameter,
    assess_work_environment,
    band_contains,
    band_from_tolerance,
    band_utilisation,
    containment_margin,
    excursions,
    longest_excursion_seconds,
    validate_band,
    validate_parameter,
    value_in_band,
)


def temperature_spec(**kw):
    spec = {
        "parameter": "air-temperature",
        "required_band": (20.0, 24.0),
        "capability_band": (18.0, 26.0),
        "readings": [21.0, 22.0, 23.0, 22.5],
        "sample_interval_s": 300.0,
        "required_interval_s": 600.0,
    }
    spec.update(kw)
    return spec


def humidity_spec(**kw):
    spec = {
        "parameter": "relative-humidity",
        "required_band": (30.0, 60.0),
        "capability_band": (20.0, 70.0),
        "readings": [45.0, 47.0, 44.0],
        "sample_interval_s": 300.0,
        "required_interval_s": 600.0,
    }
    spec.update(kw)
    return spec


class TestValidation(unittest.TestCase):
    def test_known_parameter_passes(self):
        self.assertEqual(validate_parameter("supply-voltage"), "supply-voltage")

    def test_unknown_parameter_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter("ambient-noise")

    def test_every_parameter_declares_a_unit(self):
        self.assertTrue(all(PARAMETER_UNITS.values()))

    def test_band_is_returned_as_floats(self):
        self.assertEqual(validate_band("b", (1, 2)), (1.0, 2.0))

    def test_inverted_band_raises(self):
        with self.assertRaises(ValueError):
            validate_band("b", (5.0, 1.0))

    def test_three_element_band_raises(self):
        with self.assertRaises(ValueError):
            validate_band("b", (1.0, 2.0, 3.0))

    def test_string_band_raises(self):
        with self.assertRaises(ValueError):
            validate_band("b", "20-24")

    def test_non_numeric_limit_raises(self):
        with self.assertRaises(ValueError):
            validate_band("b", ("low", 2.0))


class TestDerivedBands(unittest.TestCase):
    def test_ten_percent_of_230_volts(self):
        low, high = band_from_tolerance(230.0, 10.0)
        self.assertAlmostEqual(low, 207.0, places=9)
        self.assertAlmostEqual(high, 253.0, places=9)

    def test_zero_tolerance_collapses_the_band(self):
        low, high = band_from_tolerance(50.0, 0.0)
        self.assertAlmostEqual(low, high, places=9)

    def test_negative_tolerance_raises(self):
        with self.assertRaises(ValueError):
            band_from_tolerance(230.0, -1.0)

    def test_tolerance_above_one_hundred_percent_raises(self):
        with self.assertRaises(ValueError):
            band_from_tolerance(230.0, 120.0)

    def test_a_derived_limit_is_inside_its_own_band(self):
        band = band_from_tolerance(50.0, 1.0)
        self.assertTrue(value_in_band(band[1], band))
        self.assertTrue(value_in_band(band[0], band))


class TestContainment(unittest.TestCase):
    def test_wider_capability_contains_the_requirement(self):
        self.assertTrue(band_contains((18.0, 26.0), (20.0, 24.0)))

    def test_equal_bands_are_contained(self):
        self.assertTrue(band_contains((20.0, 24.0), (20.0, 24.0)))

    def test_narrow_capability_does_not_contain(self):
        self.assertFalse(band_contains((21.0, 23.0), (20.0, 24.0)))

    def test_margin_is_reported_at_both_ends(self):
        low, high = containment_margin((18.0, 26.0), (20.0, 24.0))
        self.assertAlmostEqual(low, 2.0, places=9)
        self.assertAlmostEqual(high, 2.0, places=9)

    def test_equal_bands_have_zero_margin(self):
        low, high = containment_margin((20.0, 24.0), (20.0, 24.0))
        self.assertAlmostEqual(low, 0.0, places=9)
        self.assertAlmostEqual(high, 0.0, places=9)

    def test_shortfall_shows_as_a_negative_margin(self):
        low, high = containment_margin((21.0, 23.0), (20.0, 24.0))
        self.assertAlmostEqual(low, -1.0, places=9)
        self.assertAlmostEqual(high, -1.0, places=9)


class TestReadings(unittest.TestCase):
    def test_reading_inside_the_band(self):
        self.assertTrue(value_in_band(22.0, (20.0, 24.0)))

    def test_reading_exactly_on_the_upper_limit_is_inside(self):
        self.assertTrue(value_in_band(24.0, (20.0, 24.0)))

    def test_reading_above_the_band_is_outside(self):
        self.assertFalse(value_in_band(24.5, (20.0, 24.0)))

    def test_centre_reading_has_zero_utilisation(self):
        self.assertAlmostEqual(band_utilisation(22.0, (20.0, 24.0)), 0.0, places=9)

    def test_limit_reading_has_unit_utilisation(self):
        self.assertAlmostEqual(band_utilisation(24.0, (20.0, 24.0)), 1.0, places=9)

    def test_zero_width_band_has_no_utilisation(self):
        with self.assertRaises(ValueError):
            band_utilisation(22.0, (22.0, 22.0))

    def test_excursions_name_side_and_magnitude(self):
        out = excursions([19.0, 22.0, 25.0], (20.0, 24.0))
        self.assertEqual([e["side"] for e in out], ["below", "above"])
        self.assertAlmostEqual(out[0]["magnitude"], 1.0, places=9)
        self.assertAlmostEqual(out[1]["magnitude"], 1.0, places=9)

    def test_in_band_series_has_no_excursion(self):
        self.assertEqual(excursions([21.0, 22.0], (20.0, 24.0)), [])

    def test_non_sequence_readings_raise(self):
        with self.assertRaises(ValueError):
            excursions("21,22", (20.0, 24.0))

    def test_longest_run_is_the_consecutive_one(self):
        series = [25.0, 25.0, 22.0, 25.0]
        seconds = longest_excursion_seconds(series, (20.0, 24.0), 60.0)
        self.assertAlmostEqual(seconds, 120.0, places=9)

    def test_no_excursion_gives_zero_duration(self):
        seconds = longest_excursion_seconds([21.0, 22.0], (20.0, 24.0), 60.0)
        self.assertAlmostEqual(seconds, 0.0, places=9)

    def test_non_positive_interval_raises(self):
        with self.assertRaises(ValueError):
            longest_excursion_seconds([21.0], (20.0, 24.0), 0.0)


class TestAssessParameter(unittest.TestCase):
    def test_a_well_run_parameter_is_controlled(self):
        result = assess_parameter(temperature_spec())
        self.assertTrue(result["controlled"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["unit"], "degC")

    def test_narrow_capability_is_flagged_at_both_ends(self):
        result = assess_parameter(temperature_spec(capability_band=(21.0, 23.0)))
        self.assertIn(FINDING_NOT_CONTAINED_LOW, result["findings"])
        self.assertIn(FINDING_NOT_CONTAINED_HIGH, result["findings"])

    def test_undeclared_capability_is_its_own_finding(self):
        result = assess_parameter(temperature_spec(capability_band=None))
        self.assertIn(FINDING_NO_CAPABILITY, result["findings"])

    def test_unmonitored_parameter_is_flagged_even_when_suitable(self):
        result = assess_parameter(temperature_spec(readings=[]))
        self.assertIn(FINDING_NO_MONITORING, result["findings"])
        self.assertNotIn(FINDING_NOT_CONTAINED_LOW, result["findings"])

    def test_excursion_is_flagged_and_counted(self):
        result = assess_parameter(temperature_spec(readings=[21.0, 25.0, 22.0]))
        self.assertIn(FINDING_EXCURSION, result["findings"])
        self.assertEqual(len(result["excursions"]), 1)

    def test_slow_sampling_is_flagged_on_its_own(self):
        result = assess_parameter(temperature_spec(sample_interval_s=900.0))
        self.assertIn(FINDING_INTERVAL_TOO_LONG, result["findings"])
        self.assertEqual(result["excursions"], [])

    def test_sampling_exactly_at_the_required_interval_passes(self):
        result = assess_parameter(temperature_spec(sample_interval_s=600.0))
        self.assertNotIn(FINDING_INTERVAL_TOO_LONG, result["findings"])

    def test_worst_utilisation_is_reported(self):
        result = assess_parameter(temperature_spec(readings=[22.0, 24.0]))
        self.assertAlmostEqual(result["worst_band_utilisation"], 1.0, places=9)

    def test_non_mapping_spec_raises(self):
        with self.assertRaises(ValueError):
            assess_parameter(["air-temperature"])

    def test_string_readings_raise(self):
        with self.assertRaises(ValueError):
            assess_parameter(temperature_spec(readings="21,22"))


class TestAssessFacility(unittest.TestCase):
    def test_clean_facility_is_suitable_and_controlled(self):
        report = assess_work_environment([temperature_spec(), humidity_spec()])
        self.assertTrue(report["suitable"])
        self.assertTrue(report["controlled"])

    def test_suitability_and_control_fail_independently(self):
        report = assess_work_environment(
            [temperature_spec(readings=[25.0]), humidity_spec()]
        )
        self.assertTrue(report["suitable"])
        self.assertFalse(report["controlled"])
        self.assertEqual(report["uncontrolled_parameters"], ["air-temperature"])

    def test_unsuitable_parameter_is_listed(self):
        report = assess_work_environment(
            [temperature_spec(capability_band=(21.0, 23.0)), humidity_spec()]
        )
        self.assertEqual(report["unsuitable_parameters"], ["air-temperature"])

    def test_duplicate_parameter_raises(self):
        with self.assertRaises(ValueError):
            assess_work_environment([temperature_spec(), temperature_spec()])

    def test_empty_facility_raises(self):
        with self.assertRaises(ValueError):
            assess_work_environment([])

    def test_non_list_input_raises(self):
        with self.assertRaises(ValueError):
            assess_work_environment(temperature_spec())


if __name__ == "__main__":
    unittest.main()
