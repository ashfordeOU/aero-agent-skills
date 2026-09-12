"""
Gate 3 contract tests for e1012-bg-basis.
Stdlib unittest, offline, deterministic.  Run:  python3 test_e1012_bg_basis.py
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_bg_basis_logic import (
    build_assessment_basis,
    check_basis_complete,
    get_environments,
    get_sensor_info,
    list_orbit_types,
    list_sensor_families,
    lookup_family_by_variant,
)


# ---------------------------------------------------------------------------
# get_environments
# ---------------------------------------------------------------------------

class TestGetEnvironments(unittest.TestCase):

    def test_leo_contains_trapped_electrons(self):
        self.assertIn("trapped_electrons", get_environments("LEO"))

    def test_leo_contains_trapped_protons(self):
        self.assertIn("trapped_protons", get_environments("LEO"))

    def test_leo_contains_albedo_neutrons(self):
        self.assertIn("albedo_neutrons", get_environments("LEO"))

    def test_leo_contains_five_environments(self):
        self.assertEqual(len(get_environments("LEO")), 5)

    def test_deep_space_has_only_gcr(self):
        envs = get_environments("DEEP_SPACE")
        self.assertEqual(envs, ["cosmic_rays_gcr"])

    def test_geo_has_outer_belt_electrons(self):
        self.assertIn("trapped_electrons_outer_belt", get_environments("GEO"))

    def test_geo_excludes_trapped_protons(self):
        self.assertNotIn("trapped_protons", get_environments("GEO"))

    def test_interplanetary_contains_sep(self):
        self.assertIn("solar_energetic_particles", get_environments("INTERPLANETARY"))

    def test_orbit_label_is_case_insensitive(self):
        self.assertEqual(get_environments("leo"), get_environments("LEO"))

    def test_meo_has_four_environments(self):
        self.assertEqual(len(get_environments("MEO")), 4)

    def test_invalid_orbit_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_environments("LUNAR_POLAR")

    def test_returns_list_type(self):
        self.assertIsInstance(get_environments("HEO"), list)

    def test_result_is_independent_copy(self):
        envs = get_environments("GEO")
        envs.append("phantom")
        self.assertNotIn("phantom", get_environments("GEO"))


# ---------------------------------------------------------------------------
# get_sensor_info
# ---------------------------------------------------------------------------

class TestGetSensorInfo(unittest.TestCase):

    def test_silicon_mechanism_is_ionization(self):
        info = get_sensor_info("silicon_semiconductor")
        self.assertEqual(
            info["background_mechanism"], "direct_ionization_and_charge_deposition"
        )

    def test_silicon_has_energy_range_tuple(self):
        rng = get_sensor_info("silicon_semiconductor")["energy_range_kev"]
        self.assertIsNotNone(rng)
        self.assertEqual(len(rng), 2)

    def test_silicon_energy_range_ordered(self):
        lo, hi = get_sensor_info("silicon_semiconductor")["energy_range_kev"]
        self.assertLess(lo, hi)

    def test_neutron_detector_energy_range_is_none(self):
        self.assertIsNone(get_sensor_info("neutron_detector")["energy_range_kev"])

    def test_scintillator_variants_include_nai(self):
        self.assertIn("nai", get_sensor_info("scintillator")["variants"])

    def test_scintillator_variants_include_bgo(self):
        self.assertIn("bgo", get_sensor_info("scintillator")["variants"])

    def test_proportional_counter_mechanism(self):
        self.assertEqual(
            get_sensor_info("proportional_counter")["background_mechanism"],
            "gas_ionization_by_particles",
        )

    def test_germanium_mechanism_high_resolution(self):
        self.assertIn(
            "high_resolution",
            get_sensor_info("germanium_solid_state")["background_mechanism"],
        )

    def test_invalid_family_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_sensor_info("unknown_sensor_xyz")

    def test_returns_dict(self):
        self.assertIsInstance(get_sensor_info("cdte_family"), dict)


# ---------------------------------------------------------------------------
# lookup_family_by_variant
# ---------------------------------------------------------------------------

class TestLookupFamilyByVariant(unittest.TestCase):

    def test_ccd_maps_to_silicon_semiconductor(self):
        self.assertEqual(lookup_family_by_variant("ccd"), "silicon_semiconductor")

    def test_photodiode_maps_to_silicon_semiconductor(self):
        self.assertEqual(lookup_family_by_variant("photodiode"), "silicon_semiconductor")

    def test_bgo_maps_to_scintillator(self):
        self.assertEqual(lookup_family_by_variant("bgo"), "scintillator")

    def test_nai_maps_to_scintillator(self):
        self.assertEqual(lookup_family_by_variant("nai"), "scintillator")

    def test_hpge_maps_to_germanium_solid_state(self):
        self.assertEqual(lookup_family_by_variant("hpge"), "germanium_solid_state")

    def test_cdznte_maps_to_cdte_family(self):
        self.assertEqual(lookup_family_by_variant("cdznte"), "cdte_family")

    def test_he3_tube_maps_to_neutron_detector(self):
        self.assertEqual(lookup_family_by_variant("he3_tube"), "neutron_detector")

    def test_mcp_single_maps_to_microchannel_plate(self):
        self.assertEqual(lookup_family_by_variant("mcp_single"), "microchannel_plate")

    def test_variant_lookup_case_insensitive(self):
        self.assertEqual(lookup_family_by_variant("CCD"), "silicon_semiconductor")

    def test_unknown_variant_raises_value_error(self):
        with self.assertRaises(ValueError):
            lookup_family_by_variant("bolometer")


# ---------------------------------------------------------------------------
# build_assessment_basis
# ---------------------------------------------------------------------------

class TestBuildAssessmentBasis(unittest.TestCase):

    def test_record_complete_for_leo_silicon(self):
        record = build_assessment_basis("LEO", "silicon_semiconductor")
        self.assertTrue(record["complete"])

    def test_orbit_type_normalized_to_upper(self):
        record = build_assessment_basis("leo", "scintillator")
        self.assertEqual(record["orbit_type"], "LEO")

    def test_record_contains_environments_list(self):
        record = build_assessment_basis("GEO", "cdte_family")
        self.assertGreater(len(record["environments"]), 0)

    def test_record_mechanism_matches_family(self):
        record = build_assessment_basis("LEO", "proportional_counter")
        self.assertEqual(record["background_mechanism"], "gas_ionization_by_particles")

    def test_deep_space_scintillator_only_gcr(self):
        record = build_assessment_basis("DEEP_SPACE", "scintillator")
        self.assertEqual(record["environments"], ["cosmic_rays_gcr"])

    def test_deep_space_scintillator_complete(self):
        self.assertTrue(build_assessment_basis("DEEP_SPACE", "scintillator")["complete"])

    def test_invalid_orbit_raises_value_error(self):
        with self.assertRaises(ValueError):
            build_assessment_basis("UNKNOWN_ORBIT", "silicon_semiconductor")

    def test_invalid_family_raises_value_error(self):
        with self.assertRaises(ValueError):
            build_assessment_basis("LEO", "mystery_detector")

    def test_heo_germanium_complete(self):
        self.assertTrue(
            build_assessment_basis("HEO", "germanium_solid_state")["complete"]
        )

    def test_geo_has_sensor_family_key(self):
        record = build_assessment_basis("GEO", "microchannel_plate")
        self.assertEqual(record["sensor_family"], "microchannel_plate")


# ---------------------------------------------------------------------------
# check_basis_complete
# ---------------------------------------------------------------------------

class TestCheckBasisComplete(unittest.TestCase):

    def test_valid_heo_record_is_complete(self):
        record = build_assessment_basis("HEO", "germanium_solid_state")
        self.assertTrue(check_basis_complete(record))

    def test_empty_orbit_type_is_incomplete(self):
        record = build_assessment_basis("LEO", "silicon_semiconductor")
        record["orbit_type"] = ""
        self.assertFalse(check_basis_complete(record))

    def test_empty_environments_list_is_incomplete(self):
        record = build_assessment_basis("LEO", "silicon_semiconductor")
        record["environments"] = []
        self.assertFalse(check_basis_complete(record))

    def test_missing_mechanism_is_incomplete(self):
        record = build_assessment_basis("LEO", "silicon_semiconductor")
        record["background_mechanism"] = ""
        self.assertFalse(check_basis_complete(record))

    def test_missing_sensor_family_is_incomplete(self):
        record = build_assessment_basis("LEO", "silicon_semiconductor")
        record["sensor_family"] = ""
        self.assertFalse(check_basis_complete(record))


# ---------------------------------------------------------------------------
# list_orbit_types / list_sensor_families
# ---------------------------------------------------------------------------

class TestListFunctions(unittest.TestCase):

    def test_list_orbit_types_is_nonempty(self):
        self.assertGreater(len(list_orbit_types()), 0)

    def test_list_orbit_types_contains_leo(self):
        self.assertIn("LEO", list_orbit_types())

    def test_list_orbit_types_contains_deep_space(self):
        self.assertIn("DEEP_SPACE", list_orbit_types())

    def test_list_sensor_families_is_nonempty(self):
        self.assertGreater(len(list_sensor_families()), 0)

    def test_list_sensor_families_contains_silicon(self):
        self.assertIn("silicon_semiconductor", list_sensor_families())

    def test_list_sensor_families_has_seven_entries(self):
        self.assertEqual(len(list_sensor_families()), 7)

    def test_list_orbit_types_has_six_entries(self):
        self.assertEqual(len(list_orbit_types()), 6)


if __name__ == "__main__":
    unittest.main()
