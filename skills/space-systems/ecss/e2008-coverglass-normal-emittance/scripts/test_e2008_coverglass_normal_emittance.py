#!/usr/bin/env python3
"""Contract test for the coverglass normal emittance leaf (offline)."""

import copy
import math
import unittest

from e2008_coverglass_normal_emittance_logic import (
    ACCEPTED_METHODS,
    EMITTANCE_ACCEPTED,
    EMITTANCE_NOT_ACCEPTED,
    MIN_SPECTRAL_COVERAGE,
    MIN_WEIGHTABLE_EXITANCE,
    REDUCTION_KIRCHHOFF,
    REDUCTION_SPECTRAL,
    REFERENCE_TEMPERATURE_BAND_K,
    SPECTRAL_METHODS,
    TOTAL_METHODS,
    assess_normal_emittance,
    band_exitance_fraction,
    band_weighted_emittance,
    blackbody_fraction_below,
    emittance_from_reflectance,
    method_is_accepted,
    missing_evidence,
    normalized_bands,
    reduction_route,
    spectral_coverage,
    temperature_within_reference_band,
    within_declared_band,
)

SPECIMEN_K = 293.0

WIDE_BANDS = (
    {"lower_um": 1.5, "upper_um": 5.0, "emittance": 0.82},
    {"lower_um": 5.0, "upper_um": 12.0, "emittance": 0.86},
    {"lower_um": 12.0, "upper_um": 25.0, "emittance": 0.84},
    {"lower_um": 25.0, "upper_um": 90.0, "emittance": 0.80},
)

SPECTRAL_CASE = {
    "method": "fourier-transform-spectrometer",
    "specimen_temperature_k": SPECIMEN_K,
    "measurement_bands": WIDE_BANDS,
    "declared_emittance_band": {"minimum": 0.78, "maximum": 0.90},
    "reported_uncertainty": 0.01,
    "required_uncertainty": 0.02,
}

TOTAL_CASE = {
    "method": "portable-emissometer",
    "specimen_temperature_k": SPECIMEN_K,
    "measurement_bands": WIDE_BANDS,
    "hemispherical_reflectance": 0.16,
    "hemispherical_transmittance": 0.0,
    "declared_emittance_band": {"minimum": 0.78, "maximum": 0.90},
    "reported_uncertainty": 0.015,
    "required_uncertainty": 0.02,
}


def _spectral(**overrides):
    case = copy.deepcopy(SPECTRAL_CASE)
    case.update(overrides)
    return case


def _total(**overrides):
    case = copy.deepcopy(TOTAL_CASE)
    case.update(overrides)
    return case


class MethodTests(unittest.TestCase):
    def test_every_accepted_method_has_a_reduction_route(self):
        for method in ACCEPTED_METHODS:
            self.assertIn(
                reduction_route(method), (REDUCTION_SPECTRAL, REDUCTION_KIRCHHOFF)
            )

    def test_the_two_method_groups_do_not_overlap(self):
        self.assertEqual(set(SPECTRAL_METHODS) & set(TOTAL_METHODS), set())

    def test_a_spectrometer_feeds_the_band_average(self):
        self.assertEqual(
            reduction_route("fourier-transform-spectrometer"), REDUCTION_SPECTRAL
        )

    def test_an_emissometer_feeds_the_kirchhoff_reduction(self):
        self.assertEqual(reduction_route("portable-emissometer"), REDUCTION_KIRCHHOFF)

    def test_an_instrument_the_reference_method_omits_is_not_accepted(self):
        self.assertFalse(method_is_accepted("handheld-infrared-thermometer"))
        with self.assertRaises(ValueError):
            reduction_route("handheld-infrared-thermometer")

    def test_a_method_that_is_not_a_name_is_refused(self):
        with self.assertRaises(ValueError):
            method_is_accepted(["portable-emissometer"])


class ReferenceTemperatureTests(unittest.TestCase):
    def test_an_ambient_specimen_sits_inside_the_reference_band(self):
        self.assertTrue(temperature_within_reference_band(SPECIMEN_K))

    def test_a_specimen_on_the_band_edge_is_still_inside(self):
        low, high = REFERENCE_TEMPERATURE_BAND_K
        self.assertTrue(temperature_within_reference_band(low))
        self.assertTrue(temperature_within_reference_band(high))

    def test_a_cryogenic_specimen_is_outside_the_reference_band(self):
        self.assertFalse(temperature_within_reference_band(120.0))

    def test_a_zero_kelvin_specimen_is_refused(self):
        with self.assertRaises(ValueError):
            temperature_within_reference_band(0.0)


class BlackbodyFractionTests(unittest.TestCase):
    def test_the_fraction_below_a_vanishing_wavelength_is_nothing(self):
        self.assertAlmostEqual(
            blackbody_fraction_below(1.0e-3, SPECIMEN_K), 0.0, places=12
        )

    def test_the_fraction_below_a_very_long_wavelength_is_everything(self):
        self.assertAlmostEqual(
            blackbody_fraction_below(1.0e5, SPECIMEN_K), 1.0, places=6
        )

    def test_the_fraction_rises_with_wavelength(self):
        near = blackbody_fraction_below(5.0, SPECIMEN_K)
        far = blackbody_fraction_below(20.0, SPECIMEN_K)
        self.assertGreater(far, near)

    def test_the_fraction_depends_only_on_the_wavelength_temperature_product(self):
        self.assertAlmostEqual(
            blackbody_fraction_below(10.0, 600.0),
            blackbody_fraction_below(20.0, 300.0),
            places=12,
        )

    def test_half_the_exitance_sits_near_the_known_quarter_wave_product(self):
        # F(0 -> lambda T) reaches one half near lambda T = 4108 um K.
        value = blackbody_fraction_below(4107.55 / SPECIMEN_K, SPECIMEN_K)
        self.assertAlmostEqual(value, 0.5, places=3)

    def test_a_negative_wavelength_is_refused(self):
        with self.assertRaises(ValueError):
            blackbody_fraction_below(-5.0, SPECIMEN_K)

    def test_a_band_share_is_the_difference_of_the_two_edge_fractions(self):
        share = band_exitance_fraction(5.0, 12.0, SPECIMEN_K)
        expected = blackbody_fraction_below(12.0, SPECIMEN_K) - blackbody_fraction_below(
            5.0, SPECIMEN_K
        )
        self.assertAlmostEqual(share, expected, places=12)

    def test_an_inverted_band_is_refused(self):
        with self.assertRaises(ValueError):
            band_exitance_fraction(12.0, 5.0, SPECIMEN_K)


class BandValidationTests(unittest.TestCase):
    def test_bands_come_back_ordered_by_their_lower_edge(self):
        shuffled = (WIDE_BANDS[2], WIDE_BANDS[0], WIDE_BANDS[3], WIDE_BANDS[1])
        ordered = normalized_bands(shuffled)
        edges = [band["lower_um"] for band in ordered]
        self.assertEqual(edges, sorted(edges))

    def test_abutting_bands_are_allowed(self):
        self.assertEqual(len(normalized_bands(WIDE_BANDS)), len(WIDE_BANDS))

    def test_overlapping_bands_are_refused(self):
        with self.assertRaises(ValueError):
            normalized_bands(
                (
                    {"lower_um": 2.0, "upper_um": 10.0, "emittance": 0.8},
                    {"lower_um": 8.0, "upper_um": 20.0, "emittance": 0.8},
                )
            )

    def test_an_emittance_above_unity_is_refused(self):
        with self.assertRaises(ValueError):
            normalized_bands(
                ({"lower_um": 2.0, "upper_um": 10.0, "emittance": 1.4},)
            )

    def test_an_empty_band_list_is_refused(self):
        with self.assertRaises(ValueError):
            normalized_bands(())

    def test_a_band_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            normalized_bands(((2.0, 10.0, 0.8),))


class WeightingTests(unittest.TestCase):
    def test_a_uniform_spectrum_averages_to_its_own_value(self):
        flat = (
            {"lower_um": 1.5, "upper_um": 12.0, "emittance": 0.85},
            {"lower_um": 12.0, "upper_um": 90.0, "emittance": 0.85},
        )
        self.assertAlmostEqual(
            band_weighted_emittance(flat, SPECIMEN_K), 0.85, places=9
        )

    def test_the_average_is_weighted_by_exitance_not_by_bandwidth(self):
        # The 25-90 um band is by far the widest in wavelength but carries
        # less exitance at 293 K than the 5-12 um band, so a low value put
        # there must move the average less than the same value put at 5-12 um.
        wide_low = band_weighted_emittance(
            (
                {"lower_um": 1.5, "upper_um": 5.0, "emittance": 0.9},
                {"lower_um": 5.0, "upper_um": 12.0, "emittance": 0.9},
                {"lower_um": 12.0, "upper_um": 25.0, "emittance": 0.9},
                {"lower_um": 25.0, "upper_um": 90.0, "emittance": 0.2},
            ),
            SPECIMEN_K,
        )
        narrow_low = band_weighted_emittance(
            (
                {"lower_um": 1.5, "upper_um": 5.0, "emittance": 0.9},
                {"lower_um": 5.0, "upper_um": 12.0, "emittance": 0.2},
                {"lower_um": 12.0, "upper_um": 25.0, "emittance": 0.9},
                {"lower_um": 25.0, "upper_um": 90.0, "emittance": 0.9},
            ),
            SPECIMEN_K,
        )
        self.assertGreater(wide_low, narrow_low)

    def test_a_scan_far_off_the_emitting_spectrum_cannot_be_averaged(self):
        with self.assertRaises(ValueError):
            band_weighted_emittance(
                ({"lower_um": 0.2, "upper_um": 0.3, "emittance": 0.9},), SPECIMEN_K
            )

    def test_a_band_off_the_spectrum_carries_no_weightable_exitance(self):
        self.assertLess(
            band_exitance_fraction(0.2, 0.3, SPECIMEN_K), MIN_WEIGHTABLE_EXITANCE
        )

    def test_a_full_span_scan_covers_nearly_all_the_exitance(self):
        self.assertGreater(spectral_coverage(WIDE_BANDS, SPECIMEN_K), MIN_SPECTRAL_COVERAGE)

    def test_a_truncated_scan_leaves_exitance_unmeasured(self):
        short = ({"lower_um": 2.0, "upper_um": 8.0, "emittance": 0.85},)
        self.assertLess(spectral_coverage(short, SPECIMEN_K), MIN_SPECTRAL_COVERAGE)

    def test_coverage_never_exceeds_the_whole_spectrum(self):
        self.assertLessEqual(spectral_coverage(WIDE_BANDS, SPECIMEN_K), 1.0)


class KirchhoffTests(unittest.TestCase):
    def test_an_opaque_specimen_emits_what_it_does_not_reflect(self):
        self.assertAlmostEqual(emittance_from_reflectance(0.16), 0.84, places=9)

    def test_a_transmitting_specimen_loses_that_share_too(self):
        self.assertAlmostEqual(
            emittance_from_reflectance(0.16, 0.04), 0.80, places=9
        )

    def test_a_perfect_mirror_emits_nothing(self):
        self.assertAlmostEqual(emittance_from_reflectance(1.0), 0.0, places=12)

    def test_a_reading_that_does_not_close_is_refused(self):
        with self.assertRaises(ValueError):
            emittance_from_reflectance(0.8, 0.5)

    def test_a_reflectance_above_unity_is_refused(self):
        with self.assertRaises(ValueError):
            emittance_from_reflectance(1.2)

    def test_a_reading_summing_exactly_to_unity_is_accepted_as_zero(self):
        self.assertAlmostEqual(emittance_from_reflectance(0.7, 0.3), 0.0, places=12)


class DeclaredBandTests(unittest.TestCase):
    def test_a_value_inside_the_drawing_band_holds(self):
        self.assertTrue(
            within_declared_band(0.85, {"minimum": 0.78, "maximum": 0.90})
        )

    def test_a_value_on_the_band_edge_still_holds(self):
        self.assertTrue(
            within_declared_band(0.78, {"minimum": 0.78, "maximum": 0.90})
        )
        self.assertTrue(
            within_declared_band(0.90, {"minimum": 0.78, "maximum": 0.90})
        )

    def test_a_value_under_the_drawing_floor_does_not_hold(self):
        self.assertFalse(
            within_declared_band(0.61, {"minimum": 0.78, "maximum": 0.90})
        )

    def test_an_inverted_drawing_band_is_refused(self):
        with self.assertRaises(ValueError):
            within_declared_band(0.85, {"minimum": 0.90, "maximum": 0.78})

    def test_a_band_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            within_declared_band(0.85, (0.78, 0.90))


class EvidenceTests(unittest.TestCase):
    def test_a_complete_record_is_missing_nothing(self):
        self.assertEqual(missing_evidence(SPECTRAL_CASE), ())

    def test_a_record_without_a_declared_band_is_incomplete(self):
        case = _spectral()
        del case["declared_emittance_band"]
        self.assertEqual(missing_evidence(case), ("declared_emittance_band",))

    def test_missing_evidence_stops_the_assessment(self):
        case = _spectral()
        del case["specimen_temperature_k"]
        with self.assertRaises(ValueError):
            assess_normal_emittance(case)

    def test_a_case_that_is_not_a_mapping_is_refused(self):
        with self.assertRaises(ValueError):
            assess_normal_emittance("fourier-transform-spectrometer")


class AssessmentTests(unittest.TestCase):
    def test_a_sound_spectral_record_is_accepted(self):
        result = assess_normal_emittance(SPECTRAL_CASE)
        self.assertEqual(result["verdict"], EMITTANCE_ACCEPTED)
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["reduction_route"], REDUCTION_SPECTRAL)

    def test_a_sound_emissometer_record_is_accepted(self):
        result = assess_normal_emittance(TOTAL_CASE)
        self.assertEqual(result["verdict"], EMITTANCE_ACCEPTED)
        self.assertEqual(result["reduction_route"], REDUCTION_KIRCHHOFF)
        self.assertAlmostEqual(result["normal_emittance"], 0.84, places=9)

    def test_an_instrument_outside_the_reference_method_stops_the_run(self):
        with self.assertRaises(ValueError):
            assess_normal_emittance(_spectral(method="handheld-infrared-thermometer"))

    def test_a_cold_specimen_is_a_finding_against_the_reference_band(self):
        result = assess_normal_emittance(_spectral(specimen_temperature_k=150.0))
        self.assertEqual(result["verdict"], EMITTANCE_NOT_ACCEPTED)
        self.assertTrue(any("specimen temperature" in f for f in result["findings"]))

    def test_a_truncated_scan_is_a_coverage_finding(self):
        result = assess_normal_emittance(
            _spectral(
                measurement_bands=(
                    {"lower_um": 2.0, "upper_um": 8.0, "emittance": 0.85},
                )
            )
        )
        self.assertEqual(result["verdict"], EMITTANCE_NOT_ACCEPTED)
        self.assertTrue(any("blackbody exitance" in f for f in result["findings"]))
        self.assertLess(result["spectral_coverage"], MIN_SPECTRAL_COVERAGE)

    def test_an_emittance_under_the_drawing_band_is_a_finding(self):
        low_bands = tuple(
            dict(band, emittance=0.40) for band in WIDE_BANDS
        )
        result = assess_normal_emittance(_spectral(measurement_bands=low_bands))
        self.assertEqual(result["verdict"], EMITTANCE_NOT_ACCEPTED)
        self.assertTrue(any("drawing declares" in f for f in result["findings"]))

    def test_an_uncertainty_over_the_requirement_is_a_finding(self):
        result = assess_normal_emittance(_spectral(reported_uncertainty=0.09))
        self.assertEqual(result["verdict"], EMITTANCE_NOT_ACCEPTED)
        self.assertFalse(result["uncertainty_met"])

    def test_an_uncertainty_landing_on_the_requirement_is_accepted(self):
        result = assess_normal_emittance(
            _spectral(reported_uncertainty=0.02, required_uncertainty=0.02)
        )
        self.assertTrue(result["uncertainty_met"])
        self.assertEqual(result["verdict"], EMITTANCE_ACCEPTED)

    def test_a_kirchhoff_method_without_a_reflectance_stops_the_run(self):
        case = _total()
        del case["hemispherical_reflectance"]
        with self.assertRaises(ValueError):
            assess_normal_emittance(case)

    def test_the_reported_emittance_matches_the_band_weighted_reduction(self):
        result = assess_normal_emittance(SPECTRAL_CASE)
        self.assertAlmostEqual(
            result["normal_emittance"],
            band_weighted_emittance(WIDE_BANDS, SPECIMEN_K),
            places=12,
        )

    def test_several_defects_are_all_reported_not_just_the_first(self):
        result = assess_normal_emittance(
            _spectral(
                specimen_temperature_k=150.0,
                measurement_bands=(
                    {"lower_um": 2.0, "upper_um": 8.0, "emittance": 0.30},
                ),
                reported_uncertainty=0.5,
            )
        )
        self.assertEqual(result["verdict"], EMITTANCE_NOT_ACCEPTED)
        self.assertGreaterEqual(len(result["findings"]), 3)


if __name__ == "__main__":
    unittest.main()
