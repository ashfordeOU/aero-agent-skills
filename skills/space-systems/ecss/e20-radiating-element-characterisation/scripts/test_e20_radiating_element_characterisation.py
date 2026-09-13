#!/usr/bin/env python3
"""Gate 3 contract test for the ECSS-E-ST-20C clause 7.2.2.3.1
radiating element characterisation logic. Stdlib unittest, offline,
deterministic."""

import math
import unittest

from e20_radiating_element_characterisation_logic import (
    ISOLATED_PATTERN_MAX_COUPLING_DB,
    ISOLATED_PATTERN_MIN_SPACING_WAVELENGTHS,
    NO_FORWARD_RADIATION_DBI,
    assess_radiating_element,
    categorize_radiating_element,
    cosine_pattern_exponent,
    cross_polar_discrimination_db,
    element_pattern_gain_dbi,
    embedded_pattern_required,
    isolated_directivity_dbi,
    mismatch_efficiency,
    missing_characterisation_quantities,
    phase_centre_defocus_deg,
    realised_element_gain_dbi,
    required_characterisation_quantities,
    wavelength_m,
)


def aperture_record(**overrides):
    record = {
        "element_type": "corrugated_horn",
        "frequency_hz": 12.0e9,
        "recorded_quantities": [
            "co_polar_pattern",
            "cross_polar_pattern",
            "input_reflection_coefficient",
            "phase_centre_location",
            "aperture_efficiency",
            "aperture_field_taper",
        ],
        "aperture_area_m2": 0.01,
        "aperture_efficiency": 0.60,
        "standing_wave_ratio": 1.25,
        "radiation_efficiency": 0.95,
        "required_gain_dbi": 19.0,
        "half_power_beamwidth_deg": 30.0,
        "cross_polar_peak_dbi": -10.0,
        "required_xpd_db": 25.0,
        "phase_centre_offset_m": 0.002,
        "subtended_half_angle_deg": 25.0,
        "max_phase_centre_defocus_deg": 15.0,
    }
    record.update(overrides)
    return record


def printed_record(**overrides):
    record = {
        "element_type": "microstrip_patch",
        "frequency_hz": 2.2e9,
        "recorded_quantities": [
            "co_polar_pattern",
            "cross_polar_pattern",
            "input_reflection_coefficient",
            "phase_centre_location",
            "impedance_bandwidth",
            "surface_wave_efficiency",
        ],
        "measured_directivity_dbi": 7.2,
        "standing_wave_ratio": 1.5,
        "radiation_efficiency": 0.80,
        "required_gain_dbi": 5.0,
        "half_power_beamwidth_deg": 80.0,
        "cross_polar_peak_dbi": -12.0,
        "required_xpd_db": 15.0,
        "phase_centre_offset_m": 0.001,
        "subtended_half_angle_deg": 60.0,
        "max_phase_centre_defocus_deg": 10.0,
    }
    record.update(overrides)
    return record


class TestElementCategorization(unittest.TestCase):
    def test_horn_is_aperture_type(self):
        self.assertEqual(categorize_radiating_element("corrugated_horn"), "aperture_type")

    def test_open_ended_waveguide_is_aperture_type(self):
        self.assertEqual(
            categorize_radiating_element("open_ended_waveguide"), "aperture_type"
        )

    def test_patch_is_resonant_printed(self):
        self.assertEqual(
            categorize_radiating_element("microstrip_patch"), "resonant_printed"
        )

    def test_crossed_slot_is_resonant_printed(self):
        self.assertEqual(
            categorize_radiating_element("crossed_slot"), "resonant_printed"
        )

    def test_helix_is_travelling_wave(self):
        self.assertEqual(
            categorize_radiating_element("axial_mode_helix"), "travelling_wave"
        )

    def test_spiral_is_travelling_wave(self):
        self.assertEqual(
            categorize_radiating_element("archimedean_spiral"), "travelling_wave"
        )

    def test_uncategorized_element_type_raises(self):
        with self.assertRaises(ValueError):
            categorize_radiating_element("plasma_antenna")

    def test_empty_element_type_raises(self):
        with self.assertRaises(ValueError):
            categorize_radiating_element("")


class TestCharacterisationRecord(unittest.TestCase):
    def test_aperture_family_requires_aperture_efficiency(self):
        self.assertIn(
            "aperture_efficiency", required_characterisation_quantities("conical_horn")
        )

    def test_printed_family_requires_surface_wave_efficiency(self):
        self.assertIn(
            "surface_wave_efficiency",
            required_characterisation_quantities("stacked_patch"),
        )

    def test_travelling_wave_family_requires_axial_ratio_pattern(self):
        self.assertIn(
            "axial_ratio_pattern",
            required_characterisation_quantities("quadrifilar_helix"),
        )

    def test_every_family_requires_the_common_four(self):
        for element in ("conical_horn", "printed_dipole", "dielectric_rod"):
            required = required_characterisation_quantities(element)
            self.assertEqual(len(required), 6)
            self.assertIn("phase_centre_location", required)

    def test_complete_record_has_no_missing_quantities(self):
        self.assertEqual(
            missing_characterisation_quantities(
                "corrugated_horn", aperture_record()["recorded_quantities"]
            ),
            [],
        )

    def test_missing_quantities_are_reported_sorted(self):
        missing = missing_characterisation_quantities(
            "corrugated_horn",
            ["co_polar_pattern", "input_reflection_coefficient"],
        )
        self.assertEqual(
            missing,
            [
                "aperture_efficiency",
                "aperture_field_taper",
                "cross_polar_pattern",
                "phase_centre_location",
            ],
        )

    def test_unrecognised_quantity_token_raises(self):
        with self.assertRaises(ValueError):
            missing_characterisation_quantities(
                "corrugated_horn", ["co_polar_pattern", "vibration_spectrum"]
            )


class TestDirectivityAndGain(unittest.TestCase):
    def test_wavelength_at_twelve_gigahertz(self):
        self.assertAlmostEqual(wavelength_m(12.0e9), 0.0249827, places=6)

    def test_non_positive_frequency_raises(self):
        with self.assertRaises(ValueError):
            wavelength_m(0.0)

    def test_negative_frequency_raises(self):
        with self.assertRaises(ValueError):
            wavelength_m(-3.0e9)

    def test_isolated_directivity_of_a_horn(self):
        lam = wavelength_m(12.0e9)
        expected = 10.0 * math.log10(4.0 * math.pi * 0.01 * 0.60 / (lam * lam))
        self.assertAlmostEqual(isolated_directivity_dbi(0.01, 12.0e9, 0.60), expected, places=9)

    def test_directivity_rises_three_decibels_when_area_doubles(self):
        one = isolated_directivity_dbi(0.01, 12.0e9, 0.60)
        two = isolated_directivity_dbi(0.02, 12.0e9, 0.60)
        self.assertAlmostEqual(two - one, 10.0 * math.log10(2.0), places=9)

    def test_zero_aperture_area_raises(self):
        with self.assertRaises(ValueError):
            isolated_directivity_dbi(0.0, 12.0e9, 0.60)

    def test_aperture_efficiency_above_unity_raises(self):
        with self.assertRaises(ValueError):
            isolated_directivity_dbi(0.01, 12.0e9, 1.2)

    def test_aperture_efficiency_of_zero_raises(self):
        with self.assertRaises(ValueError):
            isolated_directivity_dbi(0.01, 12.0e9, 0.0)

    def test_matched_input_has_unit_mismatch_efficiency(self):
        self.assertAlmostEqual(mismatch_efficiency(1.0), 1.0, places=12)

    def test_mismatch_efficiency_of_a_two_to_one_input(self):
        self.assertAlmostEqual(mismatch_efficiency(2.0), 1.0 - (1.0 / 3.0) ** 2, places=12)

    def test_standing_wave_ratio_below_unity_raises(self):
        with self.assertRaises(ValueError):
            mismatch_efficiency(0.9)

    def test_realised_gain_is_below_directivity(self):
        gain = realised_element_gain_dbi(20.0, 1.25, 0.95)
        self.assertLess(gain, 20.0)
        self.assertAlmostEqual(
            gain, 20.0 + 10.0 * math.log10(mismatch_efficiency(1.25) * 0.95), places=9
        )

    def test_lossless_matched_element_keeps_its_directivity(self):
        self.assertAlmostEqual(realised_element_gain_dbi(20.0, 1.0, 1.0), 20.0, places=9)

    def test_radiation_efficiency_above_unity_raises(self):
        with self.assertRaises(ValueError):
            realised_element_gain_dbi(20.0, 1.2, 1.05)

    def test_negative_radiation_efficiency_raises(self):
        with self.assertRaises(ValueError):
            realised_element_gain_dbi(20.0, 1.2, -0.1)


class TestElementPatternModel(unittest.TestCase):
    def test_exponent_reproduces_the_half_power_point(self):
        exponent = cosine_pattern_exponent(60.0)
        level = element_pattern_gain_dbi(0.0, exponent, 30.0)
        self.assertAlmostEqual(level, -10.0 * math.log10(2.0), places=9)

    def test_narrower_beam_needs_a_larger_exponent(self):
        self.assertGreater(cosine_pattern_exponent(20.0), cosine_pattern_exponent(80.0))

    def test_zero_beamwidth_raises(self):
        with self.assertRaises(ValueError):
            cosine_pattern_exponent(0.0)

    def test_beamwidth_of_one_hundred_eighty_degrees_raises(self):
        with self.assertRaises(ValueError):
            cosine_pattern_exponent(180.0)

    def test_boresight_level_equals_the_peak(self):
        self.assertAlmostEqual(element_pattern_gain_dbi(12.0, 2.0, 0.0), 12.0, places=12)

    def test_pattern_is_symmetric_about_boresight(self):
        self.assertAlmostEqual(
            element_pattern_gain_dbi(12.0, 2.0, 35.0),
            element_pattern_gain_dbi(12.0, 2.0, -35.0),
            places=12,
        )

    def test_endfire_direction_returns_no_forward_radiation(self):
        self.assertAlmostEqual(
            element_pattern_gain_dbi(12.0, 2.0, 90.0), NO_FORWARD_RADIATION_DBI, places=12
        )

    def test_non_positive_exponent_raises(self):
        with self.assertRaises(ValueError):
            element_pattern_gain_dbi(12.0, 0.0, 10.0)

    def test_angle_beyond_half_turn_raises(self):
        with self.assertRaises(ValueError):
            element_pattern_gain_dbi(12.0, 2.0, 200.0)


class TestPolarisationAndPhaseCentre(unittest.TestCase):
    def test_cross_polar_separation(self):
        self.assertAlmostEqual(cross_polar_discrimination_db(18.0, -12.0), 30.0, places=12)

    def test_equal_peaks_give_zero_separation(self):
        self.assertAlmostEqual(cross_polar_discrimination_db(5.0, 5.0), 0.0, places=12)

    def test_cross_polar_above_co_polar_raises(self):
        with self.assertRaises(ValueError):
            cross_polar_discrimination_db(5.0, 6.0)

    def test_defocus_grows_with_offset(self):
        small = phase_centre_defocus_deg(0.001, 12.0e9, 25.0)
        large = phase_centre_defocus_deg(0.004, 12.0e9, 25.0)
        self.assertAlmostEqual(large, 4.0 * small, places=9)

    def test_defocus_value_at_twelve_gigahertz(self):
        lam = wavelength_m(12.0e9)
        expected = 360.0 * 0.002 * (1.0 - math.cos(math.radians(25.0))) / lam
        self.assertAlmostEqual(phase_centre_defocus_deg(0.002, 12.0e9, 25.0), expected, places=9)

    def test_zero_offset_gives_no_defocus(self):
        self.assertAlmostEqual(phase_centre_defocus_deg(0.0, 12.0e9, 25.0), 0.0, places=12)

    def test_negative_offset_raises(self):
        with self.assertRaises(ValueError):
            phase_centre_defocus_deg(-0.001, 12.0e9, 25.0)

    def test_subtended_half_angle_above_ninety_raises(self):
        with self.assertRaises(ValueError):
            phase_centre_defocus_deg(0.001, 12.0e9, 95.0)

    def test_zero_subtended_half_angle_raises(self):
        with self.assertRaises(ValueError):
            phase_centre_defocus_deg(0.001, 12.0e9, 0.0)


class TestEmbeddedPatternTrigger(unittest.TestCase):
    def test_wide_lattice_and_weak_coupling_keeps_the_isolated_record(self):
        self.assertFalse(embedded_pattern_required(0.75, -28.0))

    def test_tight_lattice_forces_an_embedded_pattern(self):
        self.assertTrue(embedded_pattern_required(0.45, -30.0))

    def test_strong_coupling_forces_an_embedded_pattern(self):
        self.assertTrue(embedded_pattern_required(0.9, -12.0))

    def test_spacing_exactly_on_the_threshold_is_accepted(self):
        self.assertFalse(
            embedded_pattern_required(
                ISOLATED_PATTERN_MIN_SPACING_WAVELENGTHS, ISOLATED_PATTERN_MAX_COUPLING_DB
            )
        )

    def test_coupling_a_shade_above_the_threshold_is_rejected(self):
        self.assertTrue(
            embedded_pattern_required(0.9, ISOLATED_PATTERN_MAX_COUPLING_DB + 0.01)
        )

    def test_non_positive_spacing_raises(self):
        with self.assertRaises(ValueError):
            embedded_pattern_required(0.0, -30.0)

    def test_positive_coupling_level_raises(self):
        with self.assertRaises(ValueError):
            embedded_pattern_required(0.7, 3.0)


class TestAssessment(unittest.TestCase):
    def test_compliant_horn_record_supports_the_prediction(self):
        result = assess_radiating_element(aperture_record())
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["supports_antenna_prediction"])
        self.assertEqual(result["element_family"], "aperture_type")

    def test_compliant_patch_record_uses_the_measured_directivity(self):
        result = assess_radiating_element(printed_record())
        self.assertAlmostEqual(result["isolated_directivity_dbi"], 7.2, places=9)
        self.assertTrue(result["supports_antenna_prediction"])

    def test_gain_shortfall_is_reported(self):
        result = assess_radiating_element(aperture_record(required_gain_dbi=24.0))
        self.assertIn("realised_element_gain_below_requirement", result["findings"])
        self.assertFalse(result["supports_antenna_prediction"])

    def test_gain_exactly_on_the_requirement_passes(self):
        base = assess_radiating_element(aperture_record())
        tight = assess_radiating_element(
            aperture_record(required_gain_dbi=base["realised_element_gain_dbi"])
        )
        self.assertNotIn("realised_element_gain_below_requirement", tight["findings"])

    def test_poor_cross_polar_separation_is_reported(self):
        result = assess_radiating_element(aperture_record(cross_polar_peak_dbi=5.0))
        self.assertIn("cross_polar_discrimination_below_requirement", result["findings"])

    def test_excess_phase_centre_defocus_is_reported(self):
        result = assess_radiating_element(
            aperture_record(phase_centre_offset_m=0.02, max_phase_centre_defocus_deg=5.0)
        )
        self.assertIn("phase_centre_defocus_above_limit", result["findings"])

    def test_missing_quantity_is_reported_as_a_finding(self):
        record = aperture_record()
        record["recorded_quantities"] = [
            q for q in record["recorded_quantities"] if q != "aperture_field_taper"
        ]
        result = assess_radiating_element(record)
        self.assertIn(
            "missing_characterisation_quantity:aperture_field_taper", result["findings"]
        )

    def test_tight_lattice_is_reported_as_a_finding(self):
        result = assess_radiating_element(
            aperture_record(spacing_wavelengths=0.45, worst_coupling_db=-25.0)
        )
        self.assertTrue(result["embedded_pattern_required"])
        self.assertIn("embedded_element_pattern_required", result["findings"])

    def test_array_context_absent_leaves_the_embedded_decision_false(self):
        result = assess_radiating_element(aperture_record())
        self.assertFalse(result["embedded_pattern_required"])

    def test_partial_array_context_raises(self):
        with self.assertRaises(ValueError):
            assess_radiating_element(aperture_record(spacing_wavelengths=0.8))

    def test_missing_required_key_raises(self):
        record = aperture_record()
        del record["standing_wave_ratio"]
        with self.assertRaises(ValueError):
            assess_radiating_element(record)

    def test_aperture_record_without_mouth_area_raises(self):
        record = aperture_record()
        del record["aperture_area_m2"]
        with self.assertRaises(ValueError):
            assess_radiating_element(record)

    def test_printed_record_without_measured_directivity_raises(self):
        record = printed_record()
        del record["measured_directivity_dbi"]
        with self.assertRaises(ValueError):
            assess_radiating_element(record)

    def test_non_mapping_record_raises(self):
        with self.assertRaises(ValueError):
            assess_radiating_element(["corrugated_horn"])


if __name__ == "__main__":
    unittest.main()
