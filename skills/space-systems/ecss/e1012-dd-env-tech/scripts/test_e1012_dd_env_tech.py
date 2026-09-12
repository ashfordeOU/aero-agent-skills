"""
Offline deterministic unit tests for e1012_dd_env_tech_logic.py.
Run: python3 test_e1012_dd_env_tech.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_dd_env_tech_logic import (
    get_environment_dd_relevance,
    get_technology_dd_susceptibility,
    requires_dd_analysis,
    get_orbit_environments,
    orbit_has_high_relevance_environment,
    check_dd_analysis_coverage,
    map_mission_dd_scope,
    ENVIRONMENT_DD_RELEVANCE,
    TECHNOLOGY_DD_SUSCEPTIBILITY,
    ORBIT_ENVIRONMENTS,
)


class TestEnvironmentDDRelevance(unittest.TestCase):

    def test_trapped_protons_are_high(self):
        self.assertEqual(get_environment_dd_relevance("trapped_protons"), "HIGH")

    def test_solar_proton_event_is_high(self):
        self.assertEqual(get_environment_dd_relevance("solar_proton_event"), "HIGH")

    def test_galactic_cosmic_rays_are_moderate(self):
        self.assertEqual(get_environment_dd_relevance("galactic_cosmic_rays"), "MODERATE")

    def test_trapped_electrons_are_low(self):
        self.assertEqual(get_environment_dd_relevance("trapped_electrons"), "LOW")

    def test_bremsstrahlung_is_negligible(self):
        self.assertEqual(get_environment_dd_relevance("bremsstrahlung"), "NEGLIGIBLE")

    def test_alias_spe_resolves(self):
        self.assertEqual(get_environment_dd_relevance("spe"), "HIGH")

    def test_alias_gcr_resolves(self):
        self.assertEqual(get_environment_dd_relevance("gcr"), "MODERATE")

    def test_unknown_environment_raises(self):
        with self.assertRaises(ValueError):
            get_environment_dd_relevance("dark_matter")

    def test_empty_environment_raises(self):
        with self.assertRaises(ValueError):
            get_environment_dd_relevance("")


class TestTechnologyDDSusceptibility(unittest.TestCase):

    def test_solar_cell_si_is_critical(self):
        self.assertEqual(get_technology_dd_susceptibility("solar_cell_si"), "CRITICAL")

    def test_solar_cell_gaas_is_critical(self):
        self.assertEqual(get_technology_dd_susceptibility("solar_cell_gaas"), "CRITICAL")

    def test_solar_cell_multijunction_is_critical(self):
        self.assertEqual(get_technology_dd_susceptibility("solar_cell_multijunction"), "CRITICAL")

    def test_ccd_is_high(self):
        self.assertEqual(get_technology_dd_susceptibility("ccd"), "HIGH")

    def test_bipolar_transistor_is_high(self):
        self.assertEqual(get_technology_dd_susceptibility("bipolar_transistor"), "HIGH")

    def test_bipolar_ic_is_high(self):
        self.assertEqual(get_technology_dd_susceptibility("bipolar_ic"), "HIGH")

    def test_optocoupler_is_high(self):
        self.assertEqual(get_technology_dd_susceptibility("optocoupler"), "HIGH")

    def test_photodiode_is_high(self):
        self.assertEqual(get_technology_dd_susceptibility("photodiode"), "HIGH")

    def test_laser_diode_is_high(self):
        self.assertEqual(get_technology_dd_susceptibility("laser_diode"), "HIGH")

    def test_power_mosfet_is_moderate(self):
        self.assertEqual(get_technology_dd_susceptibility("power_mosfet"), "MODERATE")

    def test_cmos_digital_is_low(self):
        self.assertEqual(get_technology_dd_susceptibility("cmos_digital"), "LOW")

    def test_passive_is_none(self):
        self.assertEqual(get_technology_dd_susceptibility("passive"), "NONE")

    def test_alias_bjt_resolves_to_high(self):
        self.assertEqual(get_technology_dd_susceptibility("bjt"), "HIGH")

    def test_alias_opto_resolves_to_high(self):
        self.assertEqual(get_technology_dd_susceptibility("opto"), "HIGH")

    def test_unknown_technology_raises(self):
        with self.assertRaises(ValueError):
            get_technology_dd_susceptibility("quantum_dot_array")


class TestRequiresDDAnalysis(unittest.TestCase):

    def test_critical_tier_requires_analysis(self):
        self.assertTrue(requires_dd_analysis("CRITICAL"))

    def test_high_tier_requires_analysis(self):
        self.assertTrue(requires_dd_analysis("HIGH"))

    def test_moderate_tier_no_high_env_does_not_require(self):
        self.assertFalse(requires_dd_analysis("MODERATE", orbit_has_high_env=False))

    def test_moderate_tier_with_high_env_requires_analysis(self):
        self.assertTrue(requires_dd_analysis("MODERATE", orbit_has_high_env=True))

    def test_low_tier_does_not_require_analysis(self):
        self.assertFalse(requires_dd_analysis("LOW"))

    def test_none_tier_does_not_require_analysis(self):
        self.assertFalse(requires_dd_analysis("NONE"))

    def test_negligible_tier_does_not_require_analysis(self):
        self.assertFalse(requires_dd_analysis("NEGLIGIBLE"))

    def test_invalid_tier_raises(self):
        with self.assertRaises(ValueError):
            requires_dd_analysis("UNKNOWN_TIER")


class TestGetOrbitEnvironments(unittest.TestCase):

    def test_leo_includes_trapped_protons(self):
        envs = get_orbit_environments("LEO")
        self.assertIn("trapped_protons", envs)

    def test_leo_includes_electrons(self):
        envs = get_orbit_environments("LEO")
        self.assertIn("trapped_electrons", envs)

    def test_geo_includes_solar_proton_event(self):
        envs = get_orbit_environments("GEO")
        self.assertIn("solar_proton_event", envs)

    def test_geo_does_not_include_trapped_protons(self):
        envs = get_orbit_environments("GEO")
        self.assertNotIn("trapped_protons", envs)

    def test_meo_includes_trapped_protons(self):
        envs = get_orbit_environments("MEO")
        self.assertIn("trapped_protons", envs)

    def test_interplanetary_no_trapped_protons(self):
        envs = get_orbit_environments("INTERPLANETARY")
        self.assertNotIn("trapped_protons", envs)

    def test_interplanetary_has_spe(self):
        envs = get_orbit_environments("INTERPLANETARY")
        self.assertIn("solar_proton_event", envs)

    def test_case_insensitive_orbit(self):
        envs_upper = get_orbit_environments("LEO")
        envs_lower = get_orbit_environments("leo")
        self.assertEqual(envs_upper, envs_lower)

    def test_unknown_orbit_raises(self):
        with self.assertRaises(ValueError):
            get_orbit_environments("LAGRANGE_POINT_5")

    def test_return_is_list(self):
        self.assertIsInstance(get_orbit_environments("GEO"), list)


class TestOrbitHasHighRelevanceEnvironment(unittest.TestCase):

    def test_leo_has_high_env(self):
        self.assertTrue(orbit_has_high_relevance_environment("LEO"))

    def test_geo_has_high_env(self):
        self.assertTrue(orbit_has_high_relevance_environment("GEO"))

    def test_meo_has_high_env(self):
        self.assertTrue(orbit_has_high_relevance_environment("MEO"))


class TestCheckDDAnalysisCoverage(unittest.TestCase):

    def _make_item(self, name, tech, assigned):
        return {"name": name, "technology": tech, "dd_analysis_assigned": assigned}

    def test_covered_when_critical_tech_assigned(self):
        items = [self._make_item("PV1", "solar_cell_si", True)]
        result = check_dd_analysis_coverage(items, orbit="LEO")
        self.assertIn("PV1", result["covered"])
        self.assertEqual(result["missing"], [])

    def test_missing_when_critical_tech_not_assigned(self):
        items = [self._make_item("PV2", "solar_cell_gaas", False)]
        result = check_dd_analysis_coverage(items, orbit="LEO")
        self.assertIn("PV2", result["missing"])
        self.assertEqual(result["covered"], [])

    def test_passive_component_never_requires_analysis(self):
        items = [self._make_item("R1", "passive", False)]
        result = check_dd_analysis_coverage(items, orbit="LEO")
        self.assertIn("R1", result["covered"])
        self.assertEqual(result["missing"], [])

    def test_cmos_digital_not_missing(self):
        items = [self._make_item("U5", "cmos_digital", False)]
        result = check_dd_analysis_coverage(items, orbit="LEO")
        self.assertIn("U5", result["covered"])

    def test_unknown_tech_goes_to_errors(self):
        items = [self._make_item("X1", "nanowire_array", False)]
        result = check_dd_analysis_coverage(items)
        self.assertEqual(len(result["errors"]), 1)
        self.assertEqual(result["errors"][0][0], "X1")

    def test_mixed_design_coverage(self):
        items = [
            self._make_item("SA1", "solar_cell_si", True),
            self._make_item("CCD1", "ccd", False),
            self._make_item("R10", "resistor", False),
            self._make_item("Q1", "bipolar_transistor", True),
        ]
        result = check_dd_analysis_coverage(items, orbit="LEO")
        self.assertIn("SA1", result["covered"])
        self.assertIn("CCD1", result["missing"])
        self.assertIn("R10", result["covered"])
        self.assertIn("Q1", result["covered"])

    def test_moderate_with_high_env_orbit_requires_analysis(self):
        items = [self._make_item("M1", "power_mosfet", False)]
        result = check_dd_analysis_coverage(items, orbit="LEO")
        self.assertIn("M1", result["missing"])

    def test_moderate_without_high_env_covered_without_analysis(self):
        # Build a hypothetical orbit with no HIGH environments by calling without orbit
        items = [self._make_item("M2", "power_mosfet", False)]
        result = check_dd_analysis_coverage(items, orbit=None)
        self.assertIn("M2", result["covered"])

    def test_empty_design_returns_empty_lists(self):
        result = check_dd_analysis_coverage([])
        self.assertEqual(result["covered"], [])
        self.assertEqual(result["missing"], [])
        self.assertEqual(result["errors"], [])


class TestMapMissionDDScope(unittest.TestCase):

    def test_leo_scope_has_no_error_key(self):
        result = map_mission_dd_scope("LEO", ["solar_cell_si", "ccd", "passive"])
        self.assertNotIn("error", result)

    def test_leo_analysis_required_count(self):
        result = map_mission_dd_scope("LEO", ["solar_cell_si", "ccd", "passive"])
        self.assertEqual(result["analysis_required_count"], 2)

    def test_high_relevance_environments_leo(self):
        result = map_mission_dd_scope("LEO", [])
        self.assertIn("trapped_protons", result["high_relevance_environments"])

    def test_high_relevance_environments_geo(self):
        result = map_mission_dd_scope("GEO", [])
        self.assertIn("solar_proton_event", result["high_relevance_environments"])

    def test_invalid_orbit_returns_error_key(self):
        result = map_mission_dd_scope("DEEP_SPACE_9", ["solar_cell_si"])
        self.assertIn("error", result)

    def test_unknown_tech_goes_to_scope_errors(self):
        result = map_mission_dd_scope("LEO", ["carbon_nanotube"])
        self.assertEqual(len(result["errors"]), 1)

    def test_all_passives_zero_analysis_count(self):
        result = map_mission_dd_scope("GEO", ["passive", "resistor", "capacitor"])
        self.assertEqual(result["analysis_required_count"], 0)

    def test_technology_rows_include_needs_analysis_flag(self):
        result = map_mission_dd_scope("LEO", ["solar_cell_si"])
        self.assertEqual(len(result["technologies"]), 1)
        tech_name, susc, needed = result["technologies"][0]
        self.assertEqual(tech_name, "solar_cell_si")
        self.assertEqual(susc, "CRITICAL")
        self.assertTrue(needed)

    def test_environments_list_contains_tuples(self):
        result = map_mission_dd_scope("MEO", [])
        for item in result["environments"]:
            self.assertEqual(len(item), 2)

    def test_heo_contains_both_proton_sources(self):
        result = map_mission_dd_scope("HEO", [])
        high_envs = result["high_relevance_environments"]
        self.assertIn("trapped_protons", high_envs)
        self.assertIn("solar_proton_event", high_envs)


class TestRegistryCompleteness(unittest.TestCase):

    def test_all_environment_relevance_values_are_valid(self):
        valid = {"HIGH", "MODERATE", "LOW", "NEGLIGIBLE"}
        for k, v in ENVIRONMENT_DD_RELEVANCE.items():
            self.assertIn(v, valid, msg=f"Environment {k!r} has invalid relevance {v!r}")

    def test_all_technology_susceptibility_values_are_valid(self):
        valid = {"CRITICAL", "HIGH", "MODERATE", "LOW", "NONE"}
        for k, v in TECHNOLOGY_DD_SUSCEPTIBILITY.items():
            self.assertIn(v, valid, msg=f"Technology {k!r} has invalid susceptibility {v!r}")

    def test_all_orbit_environments_are_registered(self):
        for orbit, envs in ORBIT_ENVIRONMENTS.items():
            for env in envs:
                self.assertIn(
                    env, ENVIRONMENT_DD_RELEVANCE,
                    msg=f"Orbit {orbit!r} references unknown env {env!r}"
                )


if __name__ == "__main__":
    unittest.main()
