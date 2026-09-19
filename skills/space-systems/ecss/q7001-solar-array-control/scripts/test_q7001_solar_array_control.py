"""Contract tests for the solar-array and second-surface-mirror logic."""

import math
import unittest

from q7001_solar_array_control_logic import (
    MARGIN_TOLERANCE,
    STEFAN_BOLTZMANN,
    array_power_w,
    assess_solar_array,
    cell_temperature_k,
    contaminated_absorptance,
    film_transmittance,
    illumination_factor,
    obscured_area_fraction,
    power_margin_fraction,
    second_surface_mirror_ratio,
    temperature_power_factor,
    validate_array,
)


def array_spec(**overrides):
    base = {
        "bol_power_w": 1000.0,
        "required_power_w": 600.0,
        "solar_flux_w_m2": 1361.0,
        "array_area_m2": 5.0,
        "alpha_cover_bol": 0.75,
        "emittance_cover": 0.82,
        "reference_temperature_k": 301.15,
        "sink_temperature_k": 4.0,
        "temperature_coefficient_per_k": -0.0035,
        "deposition_ng_cm2": 2000.0,
        "absorption_per_ng_cm2": 2.0e-5,
        "percent_area_coverage": 1.0,
        "mirror": {"alpha_bol": 0.08, "emittance": 0.80, "max_ratio": 0.25},
    }
    base.update(overrides)
    return base


class CoverageTests(unittest.TestCase):
    def test_percent_becomes_fraction(self):
        self.assertAlmostEqual(obscured_area_fraction(1.0), 0.01, places=12)

    def test_zero_coverage(self):
        self.assertAlmostEqual(obscured_area_fraction(0.0), 0.0)

    def test_coverage_over_one_hundred_rejected(self):
        with self.assertRaises(ValueError):
            obscured_area_fraction(101.0)

    def test_negative_coverage_rejected(self):
        with self.assertRaises(ValueError):
            obscured_area_fraction(-0.1)


class TransmittanceTests(unittest.TestCase):
    def test_clean_cover_transmits_everything(self):
        self.assertAlmostEqual(film_transmittance(0.0, 2.0e-5), 1.0)

    def test_transmittance_is_exponential(self):
        self.assertAlmostEqual(
            film_transmittance(2000.0, 2.0e-5), math.exp(-0.04), places=12
        )

    def test_doubling_deposition_squares_the_transmittance(self):
        one = film_transmittance(1000.0, 2.0e-5)
        two = film_transmittance(2000.0, 2.0e-5)
        self.assertAlmostEqual(two, one * one, places=12)

    def test_negative_absorption_rejected(self):
        with self.assertRaises(ValueError):
            film_transmittance(1000.0, -1.0e-5)

    def test_illumination_combines_both_mechanisms(self):
        self.assertAlmostEqual(illumination_factor(0.01, 0.96), 0.9504, places=12)

    def test_full_obscuration_blocks_the_array(self):
        self.assertAlmostEqual(illumination_factor(1.0, 0.96), 0.0)

    def test_illumination_rejects_a_transmittance_above_one(self):
        with self.assertRaises(ValueError):
            illumination_factor(0.01, 1.2)


class AbsorptanceTests(unittest.TestCase):
    def test_clean_cover_keeps_its_absorptance(self):
        self.assertAlmostEqual(contaminated_absorptance(0.75, 0.0, 1.0), 0.75)

    def test_film_absorbs_what_it_stops(self):
        value = contaminated_absorptance(0.75, 0.0, 0.96)
        self.assertAlmostEqual(value, 0.75 + 0.04 * 0.25, places=12)

    def test_particles_darker_than_the_cover_raise_absorptance(self):
        value = contaminated_absorptance(0.08, 0.10, 1.0, 0.95)
        self.assertAlmostEqual(value, 0.08 + 0.10 * 0.87, places=12)

    def test_particles_lighter_than_the_cover_do_not_brighten_it(self):
        value = contaminated_absorptance(0.98, 0.10, 1.0, 0.20)
        self.assertAlmostEqual(value, 0.98, places=12)

    def test_absorptance_is_capped_at_unity(self):
        value = contaminated_absorptance(0.9, 1.0, 0.0, 1.0)
        self.assertAlmostEqual(value, 1.0)

    def test_mirror_ratio_is_alpha_over_epsilon(self):
        self.assertAlmostEqual(second_surface_mirror_ratio(0.16, 0.80), 0.2, places=12)

    def test_mirror_ratio_rejects_a_dead_emitter(self):
        with self.assertRaises(ValueError):
            second_surface_mirror_ratio(0.16, 0.0)


class CellTemperatureTests(unittest.TestCase):
    def test_black_body_balance(self):
        flux = STEFAN_BOLTZMANN * 300.0 ** 4
        self.assertAlmostEqual(
            cell_temperature_k(1.0, 1.0, flux, 0.0, 0.0), 300.0, places=9
        )

    def test_extracted_power_cools_the_cell(self):
        hot = cell_temperature_k(0.75, 0.82, 1361.0, 0.0, 4.0)
        cool = cell_temperature_k(0.75, 0.82, 1361.0, 300.0, 4.0)
        self.assertGreater(hot, cool)

    def test_darker_cover_runs_hotter(self):
        light = cell_temperature_k(0.70, 0.82, 1361.0, 200.0, 4.0)
        dark = cell_temperature_k(0.85, 0.82, 1361.0, 200.0, 4.0)
        self.assertGreater(dark, light)

    def test_over_extraction_is_refused(self):
        with self.assertRaises(ValueError):
            cell_temperature_k(0.75, 0.82, 1361.0, 5000.0, 4.0)

    def test_dead_emitter_is_refused(self):
        with self.assertRaises(ValueError):
            cell_temperature_k(0.75, 0.0, 1361.0, 200.0, 4.0)

    def test_derating_is_linear(self):
        self.assertAlmostEqual(
            temperature_power_factor(311.15, 301.15, -0.0035), 0.965, places=12
        )

    def test_reference_temperature_is_unity(self):
        self.assertAlmostEqual(
            temperature_power_factor(301.15, 301.15, -0.0035), 1.0, places=12
        )

    def test_positive_coefficient_rejected(self):
        with self.assertRaises(ValueError):
            temperature_power_factor(311.15, 301.15, 0.0035)

    def test_model_outside_validity_is_refused(self):
        with self.assertRaises(ValueError):
            temperature_power_factor(1000.0, 301.15, -0.01)


class PowerTests(unittest.TestCase):
    def test_power_is_the_product(self):
        self.assertAlmostEqual(array_power_w(1000.0, 0.95, 0.8), 760.0, places=9)

    def test_zero_bol_power_rejected(self):
        with self.assertRaises(ValueError):
            array_power_w(0.0, 0.95, 0.8)

    def test_illumination_above_one_rejected(self):
        with self.assertRaises(ValueError):
            array_power_w(1000.0, 1.1, 0.8)

    def test_margin_is_relative(self):
        self.assertAlmostEqual(power_margin_fraction(750.0, 600.0), 0.25, places=12)

    def test_exactly_met_requirement_is_zero_margin(self):
        self.assertAlmostEqual(power_margin_fraction(600.0, 600.0), 0.0)

    def test_zero_requirement_rejected(self):
        with self.assertRaises(ValueError):
            power_margin_fraction(750.0, 0.0)


class ValidationTests(unittest.TestCase):
    def test_defaults_are_applied(self):
        record = validate_array(
            {
                "bol_power_w": 1000.0,
                "required_power_w": 600.0,
                "solar_flux_w_m2": 1361.0,
                "array_area_m2": 5.0,
            }
        )
        self.assertAlmostEqual(record["temperature_coefficient_per_k"], -0.0035)
        self.assertIsNone(record["mirror"])

    def test_missing_key_rejected(self):
        bad = array_spec()
        del bad["array_area_m2"]
        with self.assertRaises(ValueError):
            validate_array(bad)

    def test_positive_temperature_coefficient_rejected(self):
        with self.assertRaises(ValueError):
            validate_array(array_spec(temperature_coefficient_per_k=0.002))

    def test_mirror_missing_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_array(array_spec(mirror={"alpha_bol": 0.08, "emittance": 0.8}))

    def test_non_mapping_mirror_rejected(self):
        with self.assertRaises(ValueError):
            validate_array(array_spec(mirror=["alpha_bol"]))

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            validate_array("bol_power_w")


class AssessmentTests(unittest.TestCase):
    def test_baseline_is_compliant(self):
        result = assess_solar_array(array_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_contamination_reduces_illumination(self):
        result = assess_solar_array(array_spec())
        self.assertLess(result["illumination_factor"], 1.0)

    def test_clean_array_has_unit_illumination(self):
        result = assess_solar_array(
            array_spec(deposition_ng_cm2=0.0, percent_area_coverage=0.0)
        )
        self.assertAlmostEqual(result["illumination_factor"], 1.0, places=12)

    def test_contamination_raises_the_cell_temperature(self):
        result = assess_solar_array(array_spec())
        self.assertGreater(
            result["cell_temperature_eol_k"], result["cell_temperature_bol_k"]
        )

    def test_heavier_deposition_delivers_less_power(self):
        light = assess_solar_array(array_spec(deposition_ng_cm2=500.0))
        heavy = assess_solar_array(array_spec(deposition_ng_cm2=8000.0))
        self.assertGreater(light["delivered_power_w"], heavy["delivered_power_w"])

    def test_power_shortfall_is_flagged(self):
        result = assess_solar_array(array_spec(required_power_w=900.0))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("falls short" in f for f in result["findings"]))

    def test_exactly_met_requirement_is_accepted(self):
        probe = assess_solar_array(array_spec())
        result = assess_solar_array(
            array_spec(required_power_w=probe["delivered_power_w"])
        )
        self.assertAlmostEqual(result["power_margin_fraction"], 0.0, places=12)
        self.assertLessEqual(
            abs(result["power_margin_fraction"]), MARGIN_TOLERANCE
        )
        self.assertTrue(result["compliant"])

    def test_mirror_ratio_is_reported(self):
        result = assess_solar_array(array_spec())
        self.assertGreater(
            result["mirror"]["alpha_eol"], result["mirror"]["alpha_bol"]
        )

    def test_mirror_over_its_limit_is_flagged(self):
        result = assess_solar_array(
            array_spec(mirror={"alpha_bol": 0.08, "emittance": 0.80, "max_ratio": 0.12})
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("second-surface mirror" in f for f in result["findings"]))

    def test_array_without_a_mirror_reports_none(self):
        spec = array_spec()
        spec["mirror"] = None
        self.assertIsNone(assess_solar_array(spec)["mirror"])

    def test_particulate_alone_still_costs_power(self):
        clean = assess_solar_array(
            array_spec(deposition_ng_cm2=0.0, percent_area_coverage=0.0)
        )
        dusty = assess_solar_array(
            array_spec(deposition_ng_cm2=0.0, percent_area_coverage=4.0)
        )
        self.assertGreater(clean["delivered_power_w"], dusty["delivered_power_w"])

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_solar_array(["bol_power_w"])


if __name__ == "__main__":
    unittest.main()
