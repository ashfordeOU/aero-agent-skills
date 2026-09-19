"""Contract tests for the ECSS-Q-ST-70-09C solar-absorptance method logic."""

import unittest

from q7009_solar_absorptance_methods_logic import (
    DEFAULT_COVERAGE_FACTOR,
    MIN_SOLAR_COVERAGE,
    STEFAN_BOLTZMANN,
    apply_reference_standard,
    assess_solar_absorptance,
    calorimetric_absorptance,
    integrate_trapezoid,
    interpolate_at,
    method_agreement,
    overlap_span,
    partial_irradiance,
    solar_weighted_mean,
    spectrophotometric_absorptance,
    validate_spectral_table,
)

# A deliberately flat solar spectral irradiance: the weighted mean of a flat
# quantity over it is then the quantity itself, so the integration can be
# checked against a value worked out by hand.
FLAT_SOLAR = [(250.0, 1.0), (1000.0, 1.0), (2500.0, 1.0)]

# A shaped irradiance whose energy is concentrated in the visible.
SHAPED_SOLAR = [(250.0, 0.2), (500.0, 2.0), (1000.0, 1.0), (2500.0, 0.2)]

FLAT_REFLECTANCE = [(250.0, 0.20), (1000.0, 0.20), (2500.0, 0.20)]

SHORT_REFLECTANCE = [(250.0, 0.20), (1000.0, 0.20)]


class SpectralTableTests(unittest.TestCase):
    def test_valid_table_is_returned_as_float_pairs(self):
        points = validate_spectral_table(FLAT_REFLECTANCE, "reflectance")
        self.assertEqual(len(points), 3)
        self.assertAlmostEqual(points[0][0], 250.0)
        self.assertAlmostEqual(points[0][1], 0.20)

    def test_single_point_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectral_table([(250.0, 0.2)], "reflectance")

    def test_decreasing_wavelengths_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectral_table([(1000.0, 0.2), (250.0, 0.3)], "reflectance")

    def test_repeated_wavelength_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectral_table([(250.0, 0.2), (250.0, 0.3)], "reflectance")

    def test_reflectance_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectral_table([(250.0, 0.2), (500.0, 1.4)], "reflectance")

    def test_irradiance_above_unity_allowed_when_unbounded(self):
        points = validate_spectral_table(SHAPED_SOLAR, "irradiance", bounded=False)
        self.assertAlmostEqual(points[1][1], 2.0)

    def test_negative_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectral_table([(250.0, -0.2), (500.0, 0.3)], "reflectance")

    def test_non_positive_wavelength_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectral_table([(0.0, 0.2), (500.0, 0.3)], "reflectance")

    def test_boolean_value_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectral_table([(250.0, True), (500.0, 0.3)], "reflectance")

    def test_malformed_pair_rejected(self):
        with self.assertRaises(ValueError):
            validate_spectral_table([(250.0, 0.2), (500.0,)], "reflectance")


class InterpolationAndIntegrationTests(unittest.TestCase):
    def test_interpolation_at_a_node(self):
        points = validate_spectral_table(FLAT_REFLECTANCE, "reflectance")
        self.assertAlmostEqual(interpolate_at(points, 1000.0), 0.20)

    def test_interpolation_is_linear_between_nodes(self):
        points = validate_spectral_table([(500.0, 0.10), (1500.0, 0.50)], "reflectance")
        self.assertAlmostEqual(interpolate_at(points, 1000.0), 0.30)

    def test_interpolation_outside_the_span_refused(self):
        points = validate_spectral_table(FLAT_REFLECTANCE, "reflectance")
        with self.assertRaises(ValueError):
            interpolate_at(points, 4000.0)

    def test_trapezoid_of_a_rectangle(self):
        self.assertAlmostEqual(integrate_trapezoid([(0.0, 2.0), (10.0, 2.0)]), 20.0)

    def test_trapezoid_of_a_ramp(self):
        self.assertAlmostEqual(integrate_trapezoid([(0.0, 0.0), (10.0, 4.0)]), 20.0)

    def test_trapezoid_needs_two_points(self):
        with self.assertRaises(ValueError):
            integrate_trapezoid([(0.0, 2.0)])

    def test_partial_irradiance_over_the_whole_span(self):
        self.assertAlmostEqual(partial_irradiance(FLAT_SOLAR, 250.0, 2500.0), 2250.0)

    def test_partial_irradiance_over_a_sub_span(self):
        self.assertAlmostEqual(partial_irradiance(FLAT_SOLAR, 250.0, 1000.0), 750.0)

    def test_partial_irradiance_of_a_zero_width_span(self):
        self.assertAlmostEqual(partial_irradiance(FLAT_SOLAR, 600.0, 600.0), 0.0)

    def test_inverted_partial_span_rejected(self):
        with self.assertRaises(ValueError):
            partial_irradiance(FLAT_SOLAR, 1000.0, 250.0)

    def test_disjoint_tables_have_no_overlap(self):
        first = validate_spectral_table([(250.0, 0.2), (500.0, 0.2)], "a")
        second = validate_spectral_table([(900.0, 0.2), (1200.0, 0.2)], "b")
        with self.assertRaises(ValueError):
            overlap_span(first, second)


class WeightedMeanTests(unittest.TestCase):
    def test_flat_quantity_over_flat_irradiance(self):
        mean, coverage = solar_weighted_mean(FLAT_REFLECTANCE, FLAT_SOLAR)
        self.assertAlmostEqual(mean, 0.20)
        self.assertAlmostEqual(coverage, 1.0, places=9)

    def test_flat_quantity_over_a_shaped_irradiance_is_unchanged(self):
        mean, _ = solar_weighted_mean(FLAT_REFLECTANCE, SHAPED_SOLAR)
        self.assertAlmostEqual(mean, 0.20)

    def test_short_scan_covers_only_part_of_the_irradiance(self):
        _, coverage = solar_weighted_mean(SHORT_REFLECTANCE, FLAT_SOLAR)
        self.assertAlmostEqual(coverage, 750.0 / 2250.0, places=9)

    def test_weighting_follows_the_irradiance_shape(self):
        # 0.1 below 1000 nm, 0.5 above it, over an irradiance that carries most
        # of its energy in the visible: the mean must sit nearer 0.1 than 0.5.
        table = [(250.0, 0.10), (1000.0, 0.10), (1000.1, 0.50), (2500.0, 0.50)]
        mean, _ = solar_weighted_mean(table, SHAPED_SOLAR)
        self.assertLess(mean, 0.30)
        self.assertGreater(mean, 0.10)


class ReferenceStandardTests(unittest.TestCase):
    def test_relative_scan_is_scaled_by_the_certified_reflectance(self):
        ratio = [(250.0, 0.50), (2500.0, 0.50)]
        standard = [(250.0, 0.90), (2500.0, 0.90)]
        transferred = apply_reference_standard(ratio, standard)
        self.assertAlmostEqual(transferred[0][1], 0.45)
        self.assertAlmostEqual(transferred[-1][1], 0.45)

    def test_standard_is_interpolated_at_the_scan_wavelengths(self):
        ratio = [(500.0, 1.0), (1500.0, 1.0)]
        standard = [(250.0, 0.80), (2500.0, 1.0)]
        transferred = apply_reference_standard(ratio, standard)
        self.assertAlmostEqual(transferred[0][1], 0.8 + 0.2 * (250.0 / 2250.0), places=9)

    def test_transfer_above_unity_refused(self):
        ratio = [(250.0, 1.5), (2500.0, 1.5)]
        standard = [(250.0, 0.90), (2500.0, 0.90)]
        with self.assertRaises(ValueError):
            apply_reference_standard(ratio, standard)

    def test_zero_certified_reflectance_refused(self):
        ratio = [(250.0, 0.5), (2500.0, 0.5)]
        standard = [(250.0, 0.0), (2500.0, 0.9)]
        with self.assertRaises(ValueError):
            apply_reference_standard(ratio, standard)


class SpectrophotometricTests(unittest.TestCase):
    def test_opaque_scan_gives_one_minus_reflectance(self):
        result = spectrophotometric_absorptance(FLAT_REFLECTANCE, FLAT_SOLAR)
        self.assertAlmostEqual(result["alpha_s"], 0.80)
        self.assertTrue(result["coverage_sufficient"])

    def test_transmitted_term_lowers_the_absorptance(self):
        transmittance = [(250.0, 0.30), (2500.0, 0.30)]
        result = spectrophotometric_absorptance(
            FLAT_REFLECTANCE, FLAT_SOLAR, transmittance)
        self.assertAlmostEqual(result["alpha_s"], 0.50)

    def test_short_scan_is_reported_as_insufficient_coverage(self):
        result = spectrophotometric_absorptance(SHORT_REFLECTANCE, FLAT_SOLAR)
        self.assertFalse(result["coverage_sufficient"])
        self.assertAlmostEqual(result["coverage_fraction"], 750.0 / 2250.0, places=9)

    def test_span_is_the_shared_span(self):
        result = spectrophotometric_absorptance(SHORT_REFLECTANCE, FLAT_SOLAR)
        self.assertAlmostEqual(result["span_nm"][0], 250.0)
        self.assertAlmostEqual(result["span_nm"][1], 1000.0)

    def test_over_unity_balance_in_the_scan_refused(self):
        transmittance = [(250.0, 0.90), (2500.0, 0.90)]
        with self.assertRaises(ValueError):
            spectrophotometric_absorptance(FLAT_REFLECTANCE, FLAT_SOLAR, transmittance)

    def test_coverage_floor_is_ninety_five_percent(self):
        self.assertAlmostEqual(MIN_SOLAR_COVERAGE, 0.95, places=9)


class CalorimetricTests(unittest.TestCase):
    def test_steady_state_balance_matches_a_hand_computed_value(self):
        alpha = calorimetric_absorptance(
            solar_irradiance_w_m2=1361.0,
            illuminated_area_m2=1.0,
            emittance=1.0,
            radiating_area_m2=1.0,
            specimen_temperature_k=300.0,
            sink_temperature_k=100.0,
        )
        self.assertAlmostEqual(alpha, 0.333306358, places=8)

    def test_doubling_the_radiating_area_doubles_the_absorptance(self):
        one = calorimetric_absorptance(1361.0, 1.0, 1.0, 1.0, 300.0, 100.0)
        two = calorimetric_absorptance(1361.0, 1.0, 1.0, 2.0, 300.0, 100.0)
        self.assertAlmostEqual(two, 2.0 * one, places=12)

    def test_parasitic_loss_raises_the_inferred_absorptance(self):
        plain = calorimetric_absorptance(1361.0, 1.0, 1.0, 1.0, 300.0, 100.0)
        lossy = calorimetric_absorptance(1361.0, 1.0, 1.0, 1.0, 300.0, 100.0, 136.1)
        self.assertAlmostEqual(lossy - plain, 0.10, places=9)

    def test_specimen_colder_than_the_sink_refused(self):
        with self.assertRaises(ValueError):
            calorimetric_absorptance(1361.0, 1.0, 1.0, 1.0, 90.0, 100.0)

    def test_emittance_above_unity_refused(self):
        with self.assertRaises(ValueError):
            calorimetric_absorptance(1361.0, 1.0, 1.4, 1.0, 300.0, 100.0)

    def test_zero_illuminated_area_refused(self):
        with self.assertRaises(ValueError):
            calorimetric_absorptance(1361.0, 0.0, 1.0, 1.0, 300.0, 100.0)

    def test_radiation_constant_is_the_expected_magnitude(self):
        self.assertAlmostEqual(STEFAN_BOLTZMANN * 1.0e8, 5.670374419, places=9)


class AgreementTests(unittest.TestCase):
    def test_close_determinations_agree(self):
        result = method_agreement(0.30, 0.01, 0.34, 0.02)
        self.assertTrue(result["consistent"])
        self.assertAlmostEqual(result["normalised_error"], 0.894427191, places=8)

    def test_exact_boundary_counts_as_agreement(self):
        result = method_agreement(0.40, 0.03, 0.30, 0.04)
        self.assertAlmostEqual(result["expanded_uncertainty"], 0.10, places=9)
        self.assertAlmostEqual(result["normalised_error"], 1.0, places=9)
        self.assertTrue(result["consistent"])

    def test_wide_separation_disagrees(self):
        result = method_agreement(0.30, 0.01, 0.80, 0.01)
        self.assertFalse(result["consistent"])

    def test_zero_uncertainty_on_both_sides_refused(self):
        with self.assertRaises(ValueError):
            method_agreement(0.30, 0.0, 0.34, 0.0)

    def test_negative_uncertainty_refused(self):
        with self.assertRaises(ValueError):
            method_agreement(0.30, -0.01, 0.34, 0.02)

    def test_default_coverage_factor_is_two(self):
        self.assertAlmostEqual(DEFAULT_COVERAGE_FACTOR, 2.0, places=12)


class AssessmentTests(unittest.TestCase):
    def test_direct_scan_route_is_reportable(self):
        result = assess_solar_absorptance({
            "irradiance": FLAT_SOLAR,
            "reflectance": FLAT_REFLECTANCE,
        })
        self.assertEqual(result["route"], "direct-absolute-scan")
        self.assertAlmostEqual(result["alpha_s_spectrophotometric"], 0.80)
        self.assertTrue(result["reportable"])

    def test_reference_standard_route_is_taken_when_a_ratio_scan_is_given(self):
        result = assess_solar_absorptance({
            "irradiance": FLAT_SOLAR,
            "ratio_scan": [(250.0, 0.50), (2500.0, 0.50)],
            "standard_scan": [(250.0, 0.90), (2500.0, 0.90)],
        })
        self.assertEqual(result["route"], "reference-standard-transfer")
        self.assertAlmostEqual(result["alpha_s_spectrophotometric"], 0.55)

    def test_both_routes_at_once_rejected(self):
        with self.assertRaises(ValueError):
            assess_solar_absorptance({
                "irradiance": FLAT_SOLAR,
                "reflectance": FLAT_REFLECTANCE,
                "ratio_scan": [(250.0, 0.50), (2500.0, 0.50)],
                "standard_scan": [(250.0, 0.90), (2500.0, 0.90)],
            })

    def test_no_route_at_all_rejected(self):
        with self.assertRaises(ValueError):
            assess_solar_absorptance({"irradiance": FLAT_SOLAR})

    def test_missing_irradiance_rejected(self):
        with self.assertRaises(ValueError):
            assess_solar_absorptance({"reflectance": FLAT_REFLECTANCE})

    def test_short_scan_is_a_finding_and_blocks_reporting(self):
        result = assess_solar_absorptance({
            "irradiance": FLAT_SOLAR,
            "reflectance": SHORT_REFLECTANCE,
        })
        self.assertFalse(result["reportable"])
        self.assertTrue(any("solar irradiance" in f for f in result["findings"]))

    def test_calorimetric_run_is_compared_with_the_scan(self):
        result = assess_solar_absorptance({
            "irradiance": FLAT_SOLAR,
            "reflectance": FLAT_REFLECTANCE,
            "calorimetric": {
                "solar_irradiance_w_m2": 1361.0,
                "illuminated_area_m2": 1.0,
                "emittance": 1.0,
                "radiating_area_m2": 1.0,
                "specimen_temperature_k": 372.0,
                "sink_temperature_k": 100.0,
            },
            "spectrophotometric_uncertainty": 0.02,
            "calorimetric_uncertainty": 0.03,
        })
        self.assertIsNotNone(result["agreement"])
        self.assertTrue(result["agreement"]["consistent"])
        self.assertTrue(result["reportable"])

    def test_disagreeing_calorimetric_run_is_a_finding(self):
        result = assess_solar_absorptance({
            "irradiance": FLAT_SOLAR,
            "reflectance": FLAT_REFLECTANCE,
            "calorimetric": {
                "solar_irradiance_w_m2": 1361.0,
                "illuminated_area_m2": 1.0,
                "emittance": 1.0,
                "radiating_area_m2": 1.0,
                "specimen_temperature_k": 250.0,
                "sink_temperature_k": 100.0,
            },
            "spectrophotometric_uncertainty": 0.01,
            "calorimetric_uncertainty": 0.01,
        })
        self.assertFalse(result["reportable"])
        self.assertFalse(result["agreement"]["consistent"])

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_solar_absorptance(["irradiance"])

    def test_non_mapping_calorimetric_block_rejected(self):
        with self.assertRaises(ValueError):
            assess_solar_absorptance({
                "irradiance": FLAT_SOLAR,
                "reflectance": FLAT_REFLECTANCE,
                "calorimetric": [1361.0],
            })


if __name__ == "__main__":
    unittest.main()
