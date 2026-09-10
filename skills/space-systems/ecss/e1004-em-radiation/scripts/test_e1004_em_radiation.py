#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C clause 6.2 natural EM
radiation environment workflow (solar spectrum bands, TSI scaling,
planetary albedo/IR contribution).

Exercises scripts/e1004_em_radiation_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - each spectrum
band must have a non-empty name, 0 <= wavelength_min_nm <
wavelength_max_nm, and irradiance_w_m2 >= 0; a spectrum is verified
only when its bands are ascending by wavelength with no overlap; TSI
scales from the 1-AU reference by the inverse-square law and must not
increase as distance increases; albedo must be in [0, 1]; planetary IR
must be >= 0; invalid inputs (non-positive distance, out-of-range
albedo, negative IR, empty band/distance collections, malformed bands)
raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_em_radiation_logic as em  # noqa: E402


def make_band(name, wavelength_min_nm, wavelength_max_nm, irradiance_w_m2):
    return {
        "name": name,
        "wavelength_min_nm": wavelength_min_nm,
        "wavelength_max_nm": wavelength_max_nm,
        "irradiance_w_m2": irradiance_w_m2,
    }


ORDERED_BANDS = [
    make_band("XUV", 0.1, 10, 0.001),
    make_band("EUV", 10, 121, 0.01),
    make_band("UV", 121, 400, 118.0),
    make_band("VIS", 400, 700, 635.0),
    make_band("IR", 700, 1000000, 527.0),
]

OVERLAPPING_BANDS = [
    make_band("UV", 121, 400, 118.0),
    make_band("VIS", 380, 700, 635.0),
]

OUT_OF_ORDER_BANDS = [
    make_band("VIS", 400, 700, 635.0),
    make_band("UV", 121, 400, 118.0),
]


class ValidateDistanceAuTest(unittest.TestCase):
    def test_valid_passes(self):
        em.validate_distance_au(1.0)
        em.validate_distance_au(0.39)

    def test_zero_raises(self):
        with self.assertRaises(ValueError):
            em.validate_distance_au(0)

    def test_negative_raises(self):
        with self.assertRaises(ValueError):
            em.validate_distance_au(-1.0)


class ValidateAlbedoTest(unittest.TestCase):
    def test_valid_passes(self):
        em.validate_albedo(0)
        em.validate_albedo(0.3)
        em.validate_albedo(1)

    def test_below_range_raises(self):
        with self.assertRaises(ValueError):
            em.validate_albedo(-0.1)

    def test_above_range_raises(self):
        with self.assertRaises(ValueError):
            em.validate_albedo(1.1)


class ValidateBandTest(unittest.TestCase):
    def test_valid_passes(self):
        em.validate_band(make_band("UV", 121, 400, 118.0))

    def test_missing_name_raises(self):
        with self.assertRaises(ValueError):
            em.validate_band(make_band("", 121, 400, 118.0))

    def test_negative_wavelength_min_raises(self):
        with self.assertRaises(ValueError):
            em.validate_band(make_band("UV", -1, 400, 118.0))

    def test_max_not_greater_than_min_raises(self):
        with self.assertRaises(ValueError):
            em.validate_band(make_band("UV", 400, 400, 118.0))

    def test_negative_irradiance_raises(self):
        with self.assertRaises(ValueError):
            em.validate_band(make_band("UV", 121, 400, -1.0))


class CheckSpectrumBandOrderTest(unittest.TestCase):
    def test_ordered_bands_have_no_violations(self):
        report = em.check_spectrum_band_order(ORDERED_BANDS)
        self.assertEqual(report["order_violations"], [])
        self.assertEqual(report["overlap_violations"], [])

    def test_overlapping_bands_reported(self):
        report = em.check_spectrum_band_order(OVERLAPPING_BANDS)
        self.assertEqual(report["order_violations"], [])
        self.assertTrue(report["overlap_violations"])

    def test_out_of_order_bands_reported(self):
        report = em.check_spectrum_band_order(OUT_OF_ORDER_BANDS)
        self.assertTrue(report["order_violations"])

    def test_empty_bands_raises(self):
        with self.assertRaises(ValueError):
            em.check_spectrum_band_order([])

    def test_malformed_band_raises(self):
        with self.assertRaises(ValueError):
            em.check_spectrum_band_order([make_band("UV", 400, 121, 118.0)])


class ComputeTsiAtDistanceTest(unittest.TestCase):
    def test_reference_distance_returns_reference_value(self):
        self.assertAlmostEqual(em.compute_tsi_at_distance(1.0), em.REFERENCE_TSI_W_M2)

    def test_closer_distance_increases_tsi(self):
        tsi = em.compute_tsi_at_distance(0.5)
        self.assertAlmostEqual(tsi, em.REFERENCE_TSI_W_M2 / 0.25)

    def test_farther_distance_decreases_tsi(self):
        tsi = em.compute_tsi_at_distance(2.0)
        self.assertAlmostEqual(tsi, em.REFERENCE_TSI_W_M2 / 4.0)

    def test_non_positive_distance_raises(self):
        with self.assertRaises(ValueError):
            em.compute_tsi_at_distance(0)

    def test_non_positive_reference_raises(self):
        with self.assertRaises(ValueError):
            em.compute_tsi_at_distance(1.0, reference_tsi_w_m2=0)


class CheckTsiDistanceMonotonicityTest(unittest.TestCase):
    def test_monotonic_passes(self):
        result = em.check_tsi_distance_monotonicity([0.39, 0.72, 1.0, 1.52, 5.2])
        self.assertTrue(result["monotonic"])
        self.assertEqual(
            [p[0] for p in result["pairs"]], [0.39, 0.72, 1.0, 1.52, 5.2]
        )

    def test_empty_distances_raises(self):
        with self.assertRaises(ValueError):
            em.check_tsi_distance_monotonicity([])


class ComputePlanetaryReflectedFluxTest(unittest.TestCase):
    def test_valid_computation(self):
        flux = em.compute_planetary_reflected_flux(1361.0, 0.3)
        self.assertAlmostEqual(flux, 408.3)

    def test_negative_incident_raises(self):
        with self.assertRaises(ValueError):
            em.compute_planetary_reflected_flux(-1.0, 0.3)

    def test_invalid_albedo_raises(self):
        with self.assertRaises(ValueError):
            em.compute_planetary_reflected_flux(1361.0, 1.5)


class ComputePlanetaryTotalFluxTest(unittest.TestCase):
    def test_valid_computation(self):
        result = em.compute_planetary_total_flux(1361.0, 0.3, 237.0)
        self.assertAlmostEqual(result["reflected_flux_w_m2"], 408.3)
        self.assertEqual(result["planetary_ir_w_m2"], 237.0)
        self.assertAlmostEqual(result["total_w_m2"], 645.3)

    def test_negative_ir_raises(self):
        with self.assertRaises(ValueError):
            em.compute_planetary_total_flux(1361.0, 0.3, -1.0)


class EmRadiationEnvironmentSpecificationTest(unittest.TestCase):
    def test_ordered_spectrum_is_verified(self):
        spec = em.em_radiation_environment_specification(
            ORDERED_BANDS, 1.0, 0.3, 237.0
        )
        self.assertTrue(spec["verified"])
        self.assertAlmostEqual(spec["tsi_w_m2"], em.REFERENCE_TSI_W_M2)
        self.assertAlmostEqual(spec["planetary"]["total_w_m2"], 645.3)

    def test_overlapping_spectrum_is_not_verified(self):
        spec = em.em_radiation_environment_specification(
            OVERLAPPING_BANDS, 1.0, 0.3, 237.0
        )
        self.assertFalse(spec["verified"])

    def test_distance_scales_tsi(self):
        spec = em.em_radiation_environment_specification(
            ORDERED_BANDS, 0.72, 0.75, 0.0
        )
        self.assertAlmostEqual(spec["tsi_w_m2"], em.REFERENCE_TSI_W_M2 / (0.72 ** 2))


if __name__ == "__main__":
    unittest.main()
