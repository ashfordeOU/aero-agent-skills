#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C atmospheric albedo neutrons.

Exercises scripts/e1004_neutrons_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - orbit applicability,
neutron energy-band classification, geomagnetic exposure
classification, RES entry assembly, RES entry completeness check, and
ValueError on invalid input.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_neutrons_logic as neutrons  # noqa: E402


class AlbedoNeutronsApplicableTest(unittest.TestCase):
    def test_leo_within_range_applies(self):
        self.assertTrue(neutrons.albedo_neutrons_applicable("LEO", 500))

    def test_leo_at_upper_bound_applies(self):
        self.assertTrue(neutrons.albedo_neutrons_applicable("LEO", 2000))

    def test_leo_above_range_raises(self):
        with self.assertRaises(ValueError):
            neutrons.albedo_neutrons_applicable("LEO", 2001)

    def test_leo_negative_altitude_raises(self):
        with self.assertRaises(ValueError):
            neutrons.albedo_neutrons_applicable("LEO", -1)

    def test_leo_missing_altitude_raises(self):
        with self.assertRaises(ValueError):
            neutrons.albedo_neutrons_applicable("LEO")

    def test_non_leo_regimes_do_not_apply(self):
        for regime in ("MEO", "GEO", "GTO", "HEO", "L2", "interplanetary"):
            self.assertFalse(neutrons.albedo_neutrons_applicable(regime))

    def test_case_insensitive_regime(self):
        self.assertTrue(neutrons.albedo_neutrons_applicable("leo", 400))

    def test_all_regimes_covered(self):
        expected = {"LEO", "MEO", "GEO", "GTO", "HEO", "L2", "INTERPLANETARY"}
        self.assertEqual(set(neutrons.ORBIT_REGIMES), expected)

    def test_unknown_regime_raises(self):
        with self.assertRaises(ValueError):
            neutrons.albedo_neutrons_applicable("MARS-ORBIT")
        with self.assertRaises(ValueError):
            neutrons.albedo_neutrons_applicable(None)


class NeutronEnergyBandTest(unittest.TestCase):
    def test_thermal_band(self):
        self.assertEqual(neutrons.neutron_energy_band(0.025), "thermal")

    def test_epithermal_band(self):
        self.assertEqual(neutrons.neutron_energy_band(1000.0), "epithermal")

    def test_fast_band(self):
        self.assertEqual(neutrons.neutron_energy_band(1.0e6), "fast")

    def test_high_energy_band(self):
        self.assertEqual(neutrons.neutron_energy_band(1.0e8), "high-energy")

    def test_band_boundaries_are_half_open(self):
        self.assertEqual(neutrons.neutron_energy_band(0.5), "epithermal")
        self.assertEqual(neutrons.neutron_energy_band(1.0e5), "fast")
        self.assertEqual(neutrons.neutron_energy_band(2.0e7), "high-energy")

    def test_negative_energy_raises(self):
        with self.assertRaises(ValueError):
            neutrons.neutron_energy_band(-1.0)

    def test_non_numeric_energy_raises(self):
        with self.assertRaises(ValueError):
            neutrons.neutron_energy_band("1 MeV")


class GeomagneticExposureClassTest(unittest.TestCase):
    def test_equatorial(self):
        self.assertEqual(neutrons.geomagnetic_exposure_class(5.0), "equatorial-shielded")

    def test_mid_latitude(self):
        self.assertEqual(neutrons.geomagnetic_exposure_class(45.0), "mid-latitude")

    def test_polar(self):
        self.assertEqual(neutrons.geomagnetic_exposure_class(98.0), "polar-unshielded")

    def test_boundary_at_180_is_polar(self):
        self.assertEqual(neutrons.geomagnetic_exposure_class(180.0), "polar-unshielded")

    def test_boundary_at_zero_is_equatorial(self):
        self.assertEqual(neutrons.geomagnetic_exposure_class(0.0), "equatorial-shielded")

    def test_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            neutrons.geomagnetic_exposure_class(181.0)
        with self.assertRaises(ValueError):
            neutrons.geomagnetic_exposure_class(-1.0)

    def test_non_numeric_raises(self):
        with self.assertRaises(ValueError):
            neutrons.geomagnetic_exposure_class("polar")


class BuildResEntryTest(unittest.TestCase):
    def test_leo_entry_included_with_bands(self):
        entry = neutrons.build_res_entry(
            "LEO", altitude_km=600, inclination_deg=98.0, energies_ev=[0.02, 1.0e6]
        )
        self.assertTrue(entry["included"])
        self.assertEqual(entry["regime"], "LEO")
        self.assertEqual(entry["energy_bands"], ["fast", "thermal"])
        self.assertEqual(entry["geomagnetic_exposure"], "polar-unshielded")

    def test_leo_entry_without_energies_has_empty_bands(self):
        entry = neutrons.build_res_entry("LEO", altitude_km=500, inclination_deg=30.0)
        self.assertTrue(entry["included"])
        self.assertEqual(entry["energy_bands"], [])
        self.assertEqual(entry["geomagnetic_exposure"], "mid-latitude")

    def test_non_leo_entry_excluded(self):
        entry = neutrons.build_res_entry("GEO")
        self.assertFalse(entry["included"])
        self.assertEqual(entry["energy_bands"], [])
        self.assertIsNone(entry["geomagnetic_exposure"])

    def test_leo_entry_missing_inclination_raises(self):
        with self.assertRaises(ValueError):
            neutrons.build_res_entry("LEO", altitude_km=500)

    def test_leo_entry_empty_energies_raises(self):
        with self.assertRaises(ValueError):
            neutrons.build_res_entry("LEO", altitude_km=500, inclination_deg=10.0, energies_ev=[])

    def test_known_textbook_case(self):
        # A 700 km sun-synchronous mission (near-polar inclination): the
        # RES entry must include the environment, at polar-unshielded
        # exposure, with the fast band present for the SEE-relevant
        # energy quoted.
        entry = neutrons.build_res_entry(
            "leo", altitude_km=700, inclination_deg=98.6, energies_ev=[5.0e6]
        )
        self.assertTrue(entry["included"])
        self.assertEqual(entry["geomagnetic_exposure"], "polar-unshielded")
        self.assertEqual(entry["energy_bands"], ["fast"])


class ResEntryIsCompleteTest(unittest.TestCase):
    def test_complete_included_entry(self):
        entry = neutrons.build_res_entry("LEO", altitude_km=500, inclination_deg=10.0, energies_ev=[1.0])
        self.assertEqual(neutrons.res_entry_is_complete(entry), [])

    def test_complete_excluded_entry(self):
        entry = neutrons.build_res_entry("GEO")
        self.assertEqual(neutrons.res_entry_is_complete(entry), [])

    def test_included_entry_missing_bands_is_incomplete(self):
        entry = neutrons.build_res_entry("LEO", altitude_km=500, inclination_deg=10.0)
        self.assertIn("energy_bands", neutrons.res_entry_is_complete(entry))

    def test_missing_top_level_field_is_incomplete(self):
        entry = neutrons.build_res_entry("LEO", altitude_km=500, inclination_deg=10.0, energies_ev=[1.0])
        del entry["note"]
        self.assertIn("note", neutrons.res_entry_is_complete(entry))

    def test_non_dict_raises(self):
        with self.assertRaises(ValueError):
            neutrons.res_entry_is_complete(["included", True])


if __name__ == "__main__":
    unittest.main(verbosity=2)
