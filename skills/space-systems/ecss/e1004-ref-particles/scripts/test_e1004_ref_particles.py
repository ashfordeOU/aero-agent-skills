#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C Annex I particle radiation
reference-data lookup.

Exercises scripts/e1004_ref_particles_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - an unrecognized
population or orbit regime raises; energy/altitude range checks raise
on negative input and on an altitude query against a population whose
model is not altitude-bound; LEO geomagnetic shielding excludes
solar_energetic_particle/galactic_cosmic_ray below the polar
inclination threshold and admits them at or above it; the South
Atlantic Anomaly flag requires LEO, its altitude band, and its
inclination threshold together; model selection raises for any
combination no cataloged model covers; and the aggregated review
reports a coverage gap or a range gap as a finding rather than raising,
while structurally invalid input still raises.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_ref_particles_logic as pt  # noqa: E402


class ModelRangeLookupTest(unittest.TestCase):
    def test_energy_range_known_population(self):
        self.assertEqual(pt.model_energy_range_mev(pt.TRAPPED_PROTON), (0.1, 400.0))

    def test_energy_range_unknown_population_raises(self):
        with self.assertRaises(ValueError):
            pt.model_energy_range_mev("mystery_particle")

    def test_altitude_range_known_population(self):
        self.assertEqual(
            pt.model_altitude_range_km(pt.ALBEDO_NEUTRON), (200.0, 2000.0)
        )

    def test_altitude_range_not_altitude_bound_population(self):
        self.assertEqual(
            pt.model_altitude_range_km(pt.SOLAR_ENERGETIC_PARTICLE), (None, None)
        )

    def test_altitude_range_unknown_population_raises(self):
        with self.assertRaises(ValueError):
            pt.model_altitude_range_km("mystery_particle")


class IsEnergyInRangeTest(unittest.TestCase):
    def test_within_range_true(self):
        self.assertTrue(pt.is_energy_in_range(pt.TRAPPED_ELECTRON, 1.0))

    def test_outside_range_false(self):
        self.assertFalse(pt.is_energy_in_range(pt.TRAPPED_ELECTRON, 50.0))

    def test_negative_energy_raises(self):
        with self.assertRaises(ValueError):
            pt.is_energy_in_range(pt.TRAPPED_ELECTRON, -1.0)

    def test_unknown_population_raises(self):
        with self.assertRaises(ValueError):
            pt.is_energy_in_range("mystery_particle", 1.0)


class IsAltitudeInRangeTest(unittest.TestCase):
    def test_within_range_true(self):
        self.assertTrue(pt.is_altitude_in_range(pt.TRAPPED_PROTON, 500.0))

    def test_outside_range_false(self):
        self.assertFalse(pt.is_altitude_in_range(pt.ALBEDO_NEUTRON, 5000.0))

    def test_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            pt.is_altitude_in_range(pt.TRAPPED_PROTON, -1.0)

    def test_not_altitude_bound_population_raises(self):
        with self.assertRaises(ValueError):
            pt.is_altitude_in_range(pt.GALACTIC_COSMIC_RAY, 500.0)


class GeomagneticShieldingTest(unittest.TestCase):
    def test_leo_low_inclination_shielded(self):
        self.assertTrue(pt.is_geomagnetically_shielded("leo", 20.0))

    def test_leo_high_inclination_unshielded(self):
        self.assertFalse(pt.is_geomagnetically_shielded("leo", 60.0))

    def test_leo_threshold_boundary_unshielded(self):
        self.assertFalse(
            pt.is_geomagnetically_shielded("leo", pt.POLAR_SHIELDING_INCLINATION_DEG)
        )

    def test_non_leo_never_shielded(self):
        self.assertFalse(pt.is_geomagnetically_shielded("geo"))
        self.assertFalse(pt.is_geomagnetically_shielded("interplanetary", 5.0))

    def test_leo_missing_inclination_raises(self):
        with self.assertRaises(ValueError):
            pt.is_geomagnetically_shielded("leo")

    def test_leo_invalid_inclination_raises(self):
        with self.assertRaises(ValueError):
            pt.is_geomagnetically_shielded("leo", 200.0)

    def test_unknown_regime_raises(self):
        with self.assertRaises(ValueError):
            pt.is_geomagnetically_shielded("cislunar", 45.0)


class SaaEnhancementAppliesTest(unittest.TestCase):
    def test_leo_in_band_high_inclination_true(self):
        self.assertTrue(pt.saa_enhancement_applies("leo", 500.0, 45.0))

    def test_leo_altitude_outside_band_false(self):
        self.assertFalse(pt.saa_enhancement_applies("leo", 5000.0, 45.0))

    def test_leo_inclination_below_threshold_false(self):
        self.assertFalse(pt.saa_enhancement_applies("leo", 500.0, 10.0))

    def test_non_leo_regime_false(self):
        self.assertFalse(pt.saa_enhancement_applies("meo", 500.0, 45.0))

    def test_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            pt.saa_enhancement_applies("leo", -1.0, 45.0)

    def test_invalid_inclination_raises(self):
        with self.assertRaises(ValueError):
            pt.saa_enhancement_applies("leo", 500.0, -10.0)

    def test_unknown_regime_raises(self):
        with self.assertRaises(ValueError):
            pt.saa_enhancement_applies("cislunar", 500.0, 45.0)


class SelectParticleModelTest(unittest.TestCase):
    def test_trapped_electron_in_geo(self):
        self.assertEqual(
            pt.select_particle_model(pt.TRAPPED_ELECTRON, "geo"),
            "AE-8/AE-9 trapped electron model",
        )

    def test_sep_in_shielded_leo_raises(self):
        with self.assertRaises(ValueError):
            pt.select_particle_model(pt.SOLAR_ENERGETIC_PARTICLE, "leo", 20.0)

    def test_sep_in_unshielded_leo(self):
        self.assertEqual(
            pt.select_particle_model(pt.SOLAR_ENERGETIC_PARTICLE, "leo", 80.0),
            "ESP worst-case SEP fluence model",
        )

    def test_gcr_in_interplanetary(self):
        self.assertEqual(
            pt.select_particle_model(pt.GALACTIC_COSMIC_RAY, "interplanetary"),
            "ISO-15390 GCR model",
        )

    def test_albedo_neutron_regime_not_covered_raises(self):
        with self.assertRaises(ValueError):
            pt.select_particle_model(pt.ALBEDO_NEUTRON, "geo")

    def test_unknown_population_raises(self):
        with self.assertRaises(ValueError):
            pt.select_particle_model("mystery_particle", "leo", 80.0)

    def test_unknown_regime_raises(self):
        with self.assertRaises(ValueError):
            pt.select_particle_model(pt.TRAPPED_PROTON, "cislunar")


class ParticleReferenceReviewTest(unittest.TestCase):
    def test_compliant_review_flags_saa(self):
        review = pt.particle_reference_review(
            pt.TRAPPED_PROTON, "leo", inclination_deg=45.0, altitude_km=500.0, energy_mev=50.0
        )
        self.assertEqual(review["model_id"], "AP-8/AP-9 trapped proton model")
        self.assertTrue(review["saa_applicable"])
        self.assertEqual(review["issues"], [])
        self.assertTrue(pt.is_particle_review_compliant(review))

    def test_energy_out_of_range_flagged(self):
        review = pt.particle_reference_review(pt.TRAPPED_ELECTRON, "geo", energy_mev=50.0)
        self.assertEqual(review["model_id"], "AE-8/AE-9 trapped electron model")
        self.assertEqual(len(review["issues"]), 1)
        self.assertEqual(review["issues"][0]["issue"], "energy_out_of_model_range")
        self.assertFalse(pt.is_particle_review_compliant(review))

    def test_altitude_not_applicable_flagged(self):
        review = pt.particle_reference_review(
            pt.GALACTIC_COSMIC_RAY, "interplanetary", altitude_km=1000.0
        )
        self.assertEqual(len(review["issues"]), 1)
        self.assertEqual(review["issues"][0]["issue"], "altitude_not_applicable_to_model")

    def test_altitude_out_of_range_flagged(self):
        review = pt.particle_reference_review(
            pt.ALBEDO_NEUTRON, "leo", altitude_km=5000.0
        )
        self.assertEqual(len(review["issues"]), 1)
        self.assertEqual(review["issues"][0]["issue"], "altitude_out_of_model_range")

    def test_no_model_coverage_flagged_not_raised(self):
        review = pt.particle_reference_review(pt.ALBEDO_NEUTRON, "geo")
        self.assertIsNone(review["model_id"])
        self.assertIsNone(review["saa_applicable"])
        self.assertEqual(review["issues"][0]["issue"], "no_model_coverage")
        self.assertFalse(pt.is_particle_review_compliant(review))

    def test_shielded_leo_sep_reported_as_no_coverage(self):
        review = pt.particle_reference_review(
            pt.SOLAR_ENERGETIC_PARTICLE, "leo", inclination_deg=20.0
        )
        self.assertIsNone(review["model_id"])
        self.assertEqual(review["issues"][0]["issue"], "no_model_coverage")

    def test_leo_sep_missing_inclination_raises(self):
        with self.assertRaises(ValueError):
            pt.particle_reference_review(pt.SOLAR_ENERGETIC_PARTICLE, "leo")

    def test_unknown_population_raises(self):
        with self.assertRaises(ValueError):
            pt.particle_reference_review("mystery_particle", "leo", inclination_deg=45.0)

    def test_saa_not_flagged_without_altitude_and_inclination(self):
        review = pt.particle_reference_review(pt.TRAPPED_PROTON, "leo", inclination_deg=45.0)
        self.assertIsNone(review["saa_applicable"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
