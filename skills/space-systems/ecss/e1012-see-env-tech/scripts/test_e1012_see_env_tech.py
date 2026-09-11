#!/usr/bin/env python3
"""Stdlib unittest contract test for e1012_see_env_tech_logic.

ECSS-E-ST-10-12C §9.2-9.3 — SEE-relevant environments and susceptible
technologies (orbit categorization, technology-to-SEE-type mapping, destructive
effect identification, control checking).

Run: python3 test_e1012_see_env_tech.py
Must print OK. Offline, deterministic, stdlib only.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e1012_see_env_tech_logic import (  # noqa: E402
    DESTRUCTIVE_EFFECTS,
    NON_DESTRUCTIVE_EFFECTS,
    ORBIT_ENVIRONMENTS,
    ORBIT_SEVERITY,
    SEE_TYPE_ORDER,
    TECHNOLOGY_SEE_MAP,
    SEEEnvironmentError,
    applicable_see_types,
    assess_technology,
    build_environment_technology_matrix,
    categorize_see_severity,
    destructive_see_types,
    destructive_technologies,
    dominant_particles,
    matrix_findings,
    most_severe_orbit,
    normalize_orbit_key,
    normalize_see_type,
    normalize_technology_key,
    orbit_severity,
    required_controls,
    requires_protective_control,
    sort_see_types,
    technology_display_name,
)


class TestOrbitCategorization(unittest.TestCase):
    def test_canonical_orbits_accepted(self):
        for key in ORBIT_ENVIRONMENTS:
            self.assertEqual(normalize_orbit_key(key), key)
            self.assertEqual(normalize_orbit_key(key.upper()), key)

    def test_mixed_case_and_whitespace(self):
        self.assertEqual(normalize_orbit_key("  Leo "), "leo")
        self.assertEqual(normalize_orbit_key("Interplanetary"), "interplanetary")

    def test_alias_direct_space_maps_to_interplanetary(self):
        self.assertEqual(normalize_orbit_key("deep_space"), "interplanetary")
        self.assertEqual(normalize_orbit_key("Deep Space"), "interplanetary")

    def test_alias_geosynchronous_maps_to_geo(self):
        self.assertEqual(normalize_orbit_key("geosynchronous_earth_orbit"), "geo")

    def test_alias_lunar_surface_maps_to_lunar(self):
        self.assertEqual(normalize_orbit_key("lunar surface"), "lunar")

    def test_unknown_orbit_raises(self):
        with self.assertRaises(SEEEnvironmentError):
            normalize_orbit_key("pluto_orbit")

    def test_non_string_orbit_raises(self):
        with self.assertRaises(SEEEnvironmentError):
            normalize_orbit_key(42)

    def test_empty_orbit_raises(self):
        with self.assertRaises(SEEEnvironmentError):
            normalize_orbit_key("   ")


class TestDominantParticles(unittest.TestCase):
    def test_leo_has_trapped_protons_and_heavy_ions(self):
        particles = dominant_particles("leo")
        self.assertIn("trapped_protons", particles)
        self.assertIn("heavy_ions", particles)

    def test_leo_has_no_solar_particle_events(self):
        self.assertNotIn("solar_particle_events", dominant_particles("LEO"))

    def test_meo_has_trapped_electrons_and_solar_events(self):
        particles = dominant_particles("meo")
        self.assertIn("trapped_electrons", particles)
        self.assertIn("solar_particle_events", particles)

    def test_geo_has_no_trapped_belt_populations(self):
        particles = dominant_particles("geo")
        self.assertNotIn("trapped_protons", particles)
        self.assertNotIn("trapped_electrons", particles)

    def test_lunar_adds_secondary_particles(self):
        self.assertIn("secondary_particles", dominant_particles("lunar"))

    def test_unknown_orbit_raises(self):
        with self.assertRaises(SEEEnvironmentError):
            dominant_particles("low_lunar_orbit_typo")


class TestOrbitSeverity(unittest.TestCase):
    def test_meo_outranks_geo_on_trapped_protons(self):
        self.assertGreater(orbit_severity("meo"), orbit_severity("geo"))

    def test_leo_is_lowest_rank(self):
        self.assertEqual(orbit_severity("leo"), min(ORBIT_SEVERITY.values()))

    def test_interplanetary_and_lunar_rank_above_earth_orbits(self):
        for earth_orbit in ("leo", "meo", "geo", "heo"):
            self.assertGreater(orbit_severity("interplanetary"),
                               orbit_severity(earth_orbit))

    def test_most_severe_orbit_picks_highest_rank(self):
        self.assertEqual(most_severe_orbit(["leo", "geo"]), "geo")
        self.assertEqual(most_severe_orbit(["leo", "meo"]), "meo")
        self.assertEqual(most_severe_orbit(["heo", "geo"]), "heo")

    def test_most_severe_orbit_empty_raises(self):
        with self.assertRaises(SEEEnvironmentError):
            most_severe_orbit([])

    def test_most_severe_orbit_unknown_raises(self):
        with self.assertRaises(SEEEnvironmentError):
            most_severe_orbit(["leo", "kuiper_belt"])


class TestSeeTypeCategorization(unittest.TestCase):
    def test_sel_is_destructive(self):
        self.assertEqual(categorize_see_severity("SEL"), "destructive")

    def test_seb_and_segr_are_destructive(self):
        self.assertEqual(categorize_see_severity("SEB"), "destructive")
        self.assertEqual(categorize_see_severity("SEGR"), "destructive")

    def test_sehe_is_destructive(self):
        self.assertEqual(categorize_see_severity("sehe"), "destructive")

    def test_seu_set_sefi_are_non_destructive(self):
        for effect in ("SEU", "SET", "SEFI"):
            self.assertEqual(categorize_see_severity(effect), "non_destructive")

    def test_normalize_see_type_upper(self):
        self.assertEqual(normalize_see_type("seu"), "SEU")
        self.assertEqual(normalize_see_type(" Segr "), "SEGR")

    def test_unknown_see_type_raises(self):
        with self.assertRaises(SEEEnvironmentError):
            categorize_see_severity("SELZ")

    def test_sort_see_types_uses_canonical_order(self):
        self.assertEqual(sort_see_types(["SEL", "SEU"]), ("SEU", "SEL"))
        self.assertEqual(sort_see_types(["SEHE", "SEFI"]), ("SEFI", "SEHE"))

    def test_sort_see_types_rejects_unknown(self):
        with self.assertRaises(SEEEnvironmentError):
            sort_see_types(["SEU", "NOTANEFFECT"])

    def test_effect_sets_partition_the_known_types(self):
        self.assertEqual(
            set(SEE_TYPE_ORDER),
            set(DESTRUCTIVE_EFFECTS) | set(NON_DESTRUCTIVE_EFFECTS),
        )
        self.assertEqual(
            set(DESTRUCTIVE_EFFECTS) & set(NON_DESTRUCTIVE_EFFECTS), set()
        )


class TestTechnologyMapping(unittest.TestCase):
    def test_cmos_row(self):
        self.assertEqual(applicable_see_types("CMOS"), ("SEU", "SET", "SEFI", "SEL"))

    def test_bicmos_row(self):
        self.assertEqual(applicable_see_types("BiCMOS"), ("SEU", "SET", "SEFI", "SEL"))

    def test_bipolar_row_has_no_latch_up(self):
        effects = applicable_see_types("bipolar")
        self.assertEqual(effects, ("SEU", "SET"))
        self.assertNotIn("SEL", effects)

    def test_linear_bipolar_row(self):
        self.assertEqual(applicable_see_types("linear bipolar"), ("SEU", "SET"))

    def test_sram_row(self):
        self.assertEqual(applicable_see_types("SRAM"), ("SEU", "SEFI"))

    def test_dram_row(self):
        self.assertEqual(applicable_see_types("DRAM"), ("SEU", "SEFI"))

    def test_flash_row(self):
        self.assertEqual(applicable_see_types("Flash"), ("SEU", "SEFI"))

    def test_fpga_row(self):
        self.assertEqual(applicable_see_types("FPGA"), ("SEU", "SET", "SEFI"))

    def test_power_mosfet_row(self):
        self.assertEqual(applicable_see_types("power MOSFET"), ("SEB", "SEGR"))

    def test_alias_mosfet_maps_to_power_mosfet(self):
        self.assertEqual(normalize_technology_key("MOSFET"), "power_mosfet")

    def test_alias_flash_memory_maps_to_flash(self):
        self.assertEqual(normalize_technology_key("flash_memory"), "flash")

    def test_display_name(self):
        self.assertEqual(technology_display_name("power mosfet"), "power MOSFET")
        self.assertEqual(technology_display_name("fpga"), "FPGA")

    def test_unknown_technology_raises(self):
        with self.assertRaises(SEEEnvironmentError):
            normalize_technology_key("quantum_flux_capacitor")

    def test_every_mapped_row_has_known_effects(self):
        for key, effects in TECHNOLOGY_SEE_MAP.items():
            self.assertTrue(effects, "row %s must not be empty" % key)
            for effect in effects:
                self.assertIn(effect, SEE_TYPE_ORDER)


class TestDestructiveIdentification(unittest.TestCase):
    def test_cmos_carries_sel(self):
        self.assertEqual(destructive_see_types("CMOS"), ("SEL",))

    def test_power_mosfet_carries_seb_and_segr(self):
        self.assertEqual(destructive_see_types("power_mosfet"), ("SEB", "SEGR"))

    def test_sram_has_no_destructive_type(self):
        self.assertEqual(destructive_see_types("SRAM"), ())
        self.assertFalse(requires_protective_control("SRAM"))

    def test_fpga_has_no_destructive_type(self):
        self.assertFalse(requires_protective_control("FPGA"))

    def test_bipolar_has_no_destructive_type(self):
        self.assertFalse(requires_protective_control("bipolar"))

    def test_control_requirements_for_sel(self):
        self.assertEqual(required_controls("CMOS"), ("current_limiting",))

    def test_control_requirements_for_power_mosfet(self):
        self.assertEqual(
            required_controls("power_mosfet"),
            ("voltage_derating", "lot_screening"),
        )

    def test_no_controls_required_for_sram(self):
        self.assertEqual(required_controls("SRAM"), ())

    def test_destructive_risk_flag_for_cmos(self):
        self.assertTrue(requires_protective_control("cmos"))

    def test_unknown_technology_raises(self):
        with self.assertRaises(SEEEnvironmentError):
            destructive_see_types("unobtainium")


class TestAssessTechnology(unittest.TestCase):
    def test_string_entry_is_accepted(self):
        result = assess_technology("SRAM")
        self.assertEqual(result["technology"], "sram")
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["finding"])
        self.assertFalse(result["destructive_risk"])

    def test_destructive_technology_without_control_is_a_finding(self):
        result = assess_technology("CMOS")
        self.assertTrue(result["destructive_risk"])
        self.assertFalse(result["control_ok"])
        self.assertFalse(result["compliant"])
        self.assertEqual(result["missing_controls"], ("current_limiting",))
        self.assertEqual(
            result["finding"]["issue"],
            "destructive_risk_without_documented_control",
        )

    def test_destructive_technology_with_control_is_compliant(self):
        result = assess_technology(
            {"technology": "CMOS", "controls": ["current_limiting"]}
        )
        self.assertTrue(result["compliant"])
        self.assertIsNone(result["finding"])
        self.assertEqual(result["missing_controls"], ())

    def test_partial_controls_still_flag_the_gap(self):
        result = assess_technology(
            {"technology": "power_mosfet", "controls": ["voltage_derating"]}
        )
        self.assertFalse(result["compliant"])
        self.assertEqual(result["missing_controls"], ("lot_screening",))

    def test_control_labels_are_normalized(self):
        result = assess_technology(
            {"technology": "power MOSFET",
             "controls": ["Voltage Derating", "lot-screening"]}
        )
        self.assertTrue(result["compliant"])

    def test_string_control_accepted(self):
        result = assess_technology(
            {"technology": "CMOS", "controls": "current_limiting"}
        )
        self.assertTrue(result["destructive_risk"])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["documented_controls"], ("current_limiting",))

    def test_technology_without_destructive_risk_needs_no_control(self):
        result = assess_technology({"technology": "FPGA", "controls": []})
        self.assertFalse(result["destructive_risk"])
        self.assertEqual(result["required_controls"], ())
        self.assertTrue(result["compliant"])

    def test_unexpected_control_raises(self):
        with self.assertRaises(SEEEnvironmentError):
            assess_technology({"technology": "CMOS", "controls": ["voltage_derating"]})

    def test_missing_technology_key_raises(self):
        with self.assertRaises(SEEEnvironmentError):
            assess_technology({"controls": ["current_limiting"]})

    def test_non_label_entry_raises(self):
        with self.assertRaises(SEEEnvironmentError):
            assess_technology(17)

    def test_unknown_technology_raises(self):
        with self.assertRaises(SEEEnvironmentError):
            assess_technology("graphene_spintronic")

    def test_input_dict_not_mutated(self):
        spec = {"technology": "SRAM"}
        keys_before = set(spec.keys())
        assess_technology(spec)
        self.assertEqual(set(spec.keys()), keys_before)
        self.assertEqual(spec["technology"], "SRAM")


class TestEnvironmentTechnologyMatrix(unittest.TestCase):
    def test_matrix_rows_carry_orbit_and_technology_context(self):
        rows = build_environment_technology_matrix("meo", ["CMOS", "SRAM"])
        self.assertEqual(len(rows), 2)
        for row in rows:
            self.assertEqual(row["orbit"], "meo")
            self.assertEqual(row["dominant_particles"], dominant_particles("meo"))
            self.assertEqual(row["severity_rank"], orbit_severity("meo"))
        self.assertEqual(rows[0]["applicable_see_types"], ("SEU", "SET", "SEFI", "SEL"))
        self.assertEqual(rows[1]["applicable_see_types"], ("SEU", "SEFI"))

    def test_matrix_accepts_control_dicts(self):
        rows = build_environment_technology_matrix(
            "GEO",
            [{"technology": "power_mosfet",
              "controls": ["voltage_derating", "lot_screening"]}],
        )
        self.assertTrue(rows[0]["compliant"])

    def test_empty_inventory_raises(self):
        with self.assertRaises(SEEEnvironmentError):
            build_environment_technology_matrix("leo", [])

    def test_unknown_orbit_raises(self):
        with self.assertRaises(SEEEnvironmentError):
            build_environment_technology_matrix("lagrange_point_2", ["CMOS"])

    def test_invalid_technology_in_matrix_raises(self):
        with self.assertRaises(SEEEnvironmentError):
            build_environment_technology_matrix("leo", ["CMOS", "dilithium"])

    def test_findings_report_control_gaps_only(self):
        rows = build_environment_technology_matrix(
            "leo", ["CMOS", "SRAM", "FPGA", "power_mosfet"]
        )
        findings = matrix_findings(rows)
        # CMOS (no control) and power_mosfet (no controls) are gaps; SRAM/FPGA pass.
        self.assertEqual(len(findings), 2)
        flagged = {f["technology"] for f in findings}
        self.assertEqual(flagged, {"cmos", "power_mosfet"})

    def test_all_controls_documented_gives_no_findings(self):
        rows = build_environment_technology_matrix(
            "heo",
            [
                {"technology": "CMOS", "controls": ["current_limiting"]},
                {"technology": "power_mosfet",
                 "controls": ["voltage_derating", "lot_screening"]},
                "SRAM",
            ],
        )
        self.assertEqual(matrix_findings(rows), [])

    def test_destructive_technology_rollup(self):
        rows = build_environment_technology_matrix(
            "geo", ["SRAM", "CMOS", "power_mosfet", "FPGA"]
        )
        self.assertEqual(destructive_technologies(rows), ["cmos", "power_mosfet"])


if __name__ == "__main__":
    unittest.main()
