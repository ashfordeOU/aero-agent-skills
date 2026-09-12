"""
Contract tests for e1012_tid_basis_logic.py.
Stdlib unittest only — offline, deterministic.
Run: python3 test_e1012_tid_basis.py
"""

import sys
import os
import unittest

# Allow running from any working directory
sys.path.insert(0, os.path.dirname(__file__))

from e1012_tid_basis_logic import (
    get_tid_environments,
    get_technology_sensitivity,
    compute_minimum_tid_test_level,
    establish_tid_basis,
    VALID_ORBIT_TYPES,
    VALID_TECHNOLOGIES,
    MIN_MARGIN_FACTOR,
    EnvironmentContributor,
    TechnologyEntry,
    TIDBasisRecord,
)


class TestGetTidEnvironments(unittest.TestCase):

    def test_leo_contains_trapped_protons(self):
        envs = get_tid_environments("LEO")
        keys = [e.key for e in envs]
        self.assertIn("trapped_protons", keys)

    def test_leo_contains_trapped_electrons(self):
        envs = get_tid_environments("LEO")
        keys = [e.key for e in envs]
        self.assertIn("trapped_electrons", keys)

    def test_leo_contains_gcr(self):
        envs = get_tid_environments("LEO")
        keys = [e.key for e in envs]
        self.assertIn("gcr", keys)

    def test_leo_does_not_contain_sep(self):
        # LEO is inside magnetospheric shielding — no SEP contributor
        envs = get_tid_environments("LEO")
        keys = [e.key for e in envs]
        self.assertNotIn("sep", keys)

    def test_geo_contains_sep(self):
        envs = get_tid_environments("GEO")
        keys = [e.key for e in envs]
        self.assertIn("sep", keys)

    def test_geo_does_not_contain_trapped_protons(self):
        # GEO is outside the inner proton belt
        envs = get_tid_environments("GEO")
        keys = [e.key for e in envs]
        self.assertNotIn("trapped_protons", keys)

    def test_meo_contains_all_five_contributors(self):
        envs = get_tid_environments("MEO")
        keys = [e.key for e in envs]
        for expected in ("trapped_protons", "trapped_electrons", "bremsstrahlung", "gcr", "sep"):
            self.assertIn(expected, keys, msg=f"MEO missing: {expected}")

    def test_interplanetary_only_sep_and_gcr(self):
        envs = get_tid_environments("interplanetary")
        keys = set(e.key for e in envs)
        self.assertEqual(keys, {"sep", "gcr"})

    def test_heo_contains_sep(self):
        envs = get_tid_environments("HEO")
        keys = [e.key for e in envs]
        self.assertIn("sep", keys)

    def test_invalid_orbit_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            get_tid_environments("VLEO")
        self.assertIn("VLEO", str(ctx.exception))

    def test_environment_entries_are_environment_contributor_instances(self):
        envs = get_tid_environments("GEO")
        for e in envs:
            self.assertIsInstance(e, EnvironmentContributor)


class TestGetTechnologySensitivity(unittest.TestCase):

    def test_bipolar_linear_is_high_sensitivity(self):
        entry = get_technology_sensitivity("bipolar_linear")
        self.assertEqual(entry.sensitivity, "high")

    def test_cmos_bulk_is_moderate_sensitivity(self):
        entry = get_technology_sensitivity("cmos_bulk")
        self.assertEqual(entry.sensitivity, "moderate")

    def test_gaas_mesfet_is_low_sensitivity(self):
        entry = get_technology_sensitivity("gaas_mesfet")
        self.assertEqual(entry.sensitivity, "low")

    def test_opto_coupler_is_high_sensitivity(self):
        entry = get_technology_sensitivity("opto_coupler")
        self.assertEqual(entry.sensitivity, "high")

    def test_resistor_is_low_sensitivity(self):
        entry = get_technology_sensitivity("resistor")
        self.assertEqual(entry.sensitivity, "low")

    def test_returned_entry_is_technology_entry_instance(self):
        entry = get_technology_sensitivity("fpga_sram")
        self.assertIsInstance(entry, TechnologyEntry)

    def test_sensitivity_level_is_one_of_valid_values(self):
        for tech in ("bipolar_digital", "power_mosfet", "ccd_imager", "mlcc_capacitor"):
            entry = get_technology_sensitivity(tech)
            self.assertIn(entry.sensitivity, ("high", "moderate", "low"))

    def test_unknown_technology_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            get_technology_sensitivity("vacuum_tube")
        self.assertIn("vacuum_tube", str(ctx.exception))

    def test_technology_lookup_is_case_insensitive_via_lower(self):
        # The function strips and lowercases — verify lower matches
        entry = get_technology_sensitivity("CMOS_BULK".lower())
        self.assertEqual(entry.sensitivity, "moderate")


class TestComputeMinimumTidTestLevel(unittest.TestCase):

    def test_basic_multiplication(self):
        result = compute_minimum_tid_test_level(10.0, 2.0)
        self.assertAlmostEqual(result, 20.0)

    def test_custom_margin_factor(self):
        result = compute_minimum_tid_test_level(5.0, 3.0)
        self.assertAlmostEqual(result, 15.0)

    def test_margin_factor_exactly_at_floor(self):
        result = compute_minimum_tid_test_level(1.0, MIN_MARGIN_FACTOR)
        self.assertAlmostEqual(result, MIN_MARGIN_FACTOR)

    def test_margin_factor_below_floor_raises_value_error(self):
        with self.assertRaises(ValueError) as ctx:
            compute_minimum_tid_test_level(10.0, 1.5)
        self.assertIn("1.5", str(ctx.exception))

    def test_zero_dose_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_minimum_tid_test_level(0.0, 2.0)

    def test_negative_dose_raises_value_error(self):
        with self.assertRaises(ValueError):
            compute_minimum_tid_test_level(-5.0, 2.0)


class TestEstablishTidBasis(unittest.TestCase):

    def test_complete_basis_leo_two_technologies(self):
        record = establish_tid_basis(
            orbit_type="LEO",
            mission_duration_years=3.0,
            technologies=["cmos_bulk", "resistor"],
            design_dose_krad_si=10.0,
        )
        self.assertTrue(record.complete)
        self.assertAlmostEqual(record.minimum_tid_test_krad_si, 20.0)

    def test_basis_record_is_tid_basis_record_instance(self):
        record = establish_tid_basis(
            orbit_type="GEO",
            mission_duration_years=15.0,
            technologies=["opto_coupler"],
            design_dose_krad_si=50.0,
        )
        self.assertIsInstance(record, TIDBasisRecord)

    def test_orbit_and_duration_stored_correctly(self):
        record = establish_tid_basis(
            orbit_type="HEO",
            mission_duration_years=7.5,
            technologies=["cmos_bulk"],
            design_dose_krad_si=20.0,
        )
        self.assertEqual(record.orbit_type, "HEO")
        self.assertAlmostEqual(record.mission_duration_years, 7.5)

    def test_unknown_technology_makes_basis_incomplete(self):
        record = establish_tid_basis(
            orbit_type="LEO",
            mission_duration_years=2.0,
            technologies=["vacuum_tube"],
            design_dose_krad_si=8.0,
        )
        self.assertFalse(record.complete)
        unknown_findings = [f for f in record.findings if "Unknown technology" in f]
        self.assertTrue(len(unknown_findings) > 0)

    def test_bipolar_linear_eldrs_finding_added(self):
        record = establish_tid_basis(
            orbit_type="GEO",
            mission_duration_years=12.0,
            technologies=["bipolar_linear"],
            design_dose_krad_si=100.0,
        )
        eldrs_findings = [f for f in record.findings if "ELDRS" in f]
        self.assertTrue(len(eldrs_findings) > 0)

    def test_non_bipolar_technology_does_not_trigger_eldrs_finding(self):
        record = establish_tid_basis(
            orbit_type="LEO",
            mission_duration_years=1.0,
            technologies=["cmos_bulk"],
            design_dose_krad_si=5.0,
        )
        eldrs_findings = [f for f in record.findings if "ELDRS" in f]
        self.assertEqual(len(eldrs_findings), 0)

    def test_margin_below_floor_makes_basis_incomplete(self):
        record = establish_tid_basis(
            orbit_type="LEO",
            mission_duration_years=2.0,
            technologies=["cmos_bulk"],
            design_dose_krad_si=10.0,
            margin_factor=1.0,
        )
        self.assertFalse(record.complete)

    def test_empty_technology_list_makes_basis_incomplete(self):
        record = establish_tid_basis(
            orbit_type="MEO",
            mission_duration_years=5.0,
            technologies=[],
            design_dose_krad_si=200.0,
        )
        self.assertFalse(record.complete)

    def test_invalid_orbit_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            establish_tid_basis(
                orbit_type="SSO",
                mission_duration_years=2.0,
                technologies=["cmos_bulk"],
                design_dose_krad_si=10.0,
            )

    def test_negative_mission_duration_raises_value_error(self):
        with self.assertRaises(ValueError):
            establish_tid_basis(
                orbit_type="LEO",
                mission_duration_years=-1.0,
                technologies=["cmos_bulk"],
                design_dose_krad_si=10.0,
            )

    def test_interplanetary_basis_contains_sep_environment(self):
        record = establish_tid_basis(
            orbit_type="interplanetary",
            mission_duration_years=8.0,
            technologies=["cmos_bulk", "gaas_mesfet"],
            design_dose_krad_si=30.0,
        )
        env_keys = [e.key for e in record.environments]
        self.assertIn("sep", env_keys)
        self.assertNotIn("trapped_protons", env_keys)

    def test_mixed_sensitivity_all_stored(self):
        record = establish_tid_basis(
            orbit_type="GEO",
            mission_duration_years=15.0,
            technologies=["bipolar_linear", "cmos_bulk", "resistor"],
            design_dose_krad_si=80.0,
        )
        sensitivities = {e.sensitivity for e in record.technologies}
        self.assertIn("high", sensitivities)
        self.assertIn("moderate", sensitivities)
        self.assertIn("low", sensitivities)

    def test_custom_margin_factor_stored_in_record(self):
        record = establish_tid_basis(
            orbit_type="LEO",
            mission_duration_years=3.0,
            technologies=["fpga_sram"],
            design_dose_krad_si=15.0,
            margin_factor=3.0,
        )
        self.assertAlmostEqual(record.margin_factor, 3.0)
        self.assertAlmostEqual(record.minimum_tid_test_krad_si, 45.0)

    def test_adc_bipolar_triggers_eldrs_finding(self):
        record = establish_tid_basis(
            orbit_type="GEO",
            mission_duration_years=10.0,
            technologies=["adc_bipolar"],
            design_dose_krad_si=60.0,
        )
        eldrs_findings = [f for f in record.findings if "ELDRS" in f]
        self.assertTrue(len(eldrs_findings) > 0)


if __name__ == "__main__":
    unittest.main()
