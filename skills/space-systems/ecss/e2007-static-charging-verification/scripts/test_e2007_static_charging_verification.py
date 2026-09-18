#!/usr/bin/env python3
"""Gate 3 contract test for e2007-static-charging-verification.

Stdlib unittest, offline, deterministic.
"""

import unittest

import e2007_static_charging_verification_logic as logic


def material(**overrides):
    rec = {
        "id": "outer-skin-paint",
        "sheet_resistivity_ohm_per_square": 1.0e6,
        "volume_resistivity_ohm_m": 1.0e8,
        "relative_permittivity": 3.0,
        "exposed": True,
    }
    rec.update(overrides)
    return rec


def strap(**overrides):
    rec = {
        "id": "antenna-bracket-strap",
        "category": "category-static-equalization",
        "resistance_ohm": 0.01,
    }
    rec.update(overrides)
    return rec


def blanket(**overrides):
    rec = {
        "id": "upper-stage-blanket",
        "area_m2": 1.0,
        "layer_count": 12,
        "grounded_layer_count": 12,
        "ground_tab_count": 4,
    }
    rec.update(overrides)
    return rec


def charging_config(**overrides):
    cfg = {
        "materials": [material(), material(id="inner-liner", exposed=False)],
        "straps": [strap(), strap(id="skin-panel-strap", resistance_ohm=0.5)],
        "blankets": [blanket(), blanket(id="tank-blanket", area_m2=0.4, ground_tab_count=2)],
        "equalization_limit_s": 1.0,
        "max_area_per_tab_m2": 0.5,
    }
    cfg.update(overrides)
    return cfg


class TestBondingCategories(unittest.TestCase):
    def test_canonical_category_is_returned(self):
        self.assertEqual(
            logic.bonding_category("category-static-equalization"), logic.BOND_STATIC
        )

    def test_short_alias_resolves(self):
        self.assertEqual(logic.bonding_category("Class-R"), logic.BOND_RF)

    def test_descriptive_alias_resolves(self):
        self.assertEqual(
            logic.bonding_category("potential-equalization"), logic.BOND_STATIC
        )

    def test_blank_category_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.bonding_category("   ")

    def test_unknown_category_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.bonding_category("class-z")

    def test_rf_reference_limit_is_tighter_than_the_static_limit(self):
        self.assertLess(
            logic.bonding_resistance_limit_ohm("class-r"),
            logic.bonding_resistance_limit_ohm("class-s"),
        )


class TestStrapResistance(unittest.TestCase):
    def test_resistance_follows_material_and_geometry(self):
        value = logic.strap_resistance_ohm(1.68e-8, 100.0, 4.0)
        self.assertAlmostEqual(value, 4.2e-4, places=12)

    def test_doubling_the_length_doubles_the_resistance(self):
        short = logic.strap_resistance_ohm(1.68e-8, 100.0, 4.0)
        long_strap = logic.strap_resistance_ohm(1.68e-8, 200.0, 4.0)
        self.assertAlmostEqual(long_strap, 2.0 * short, places=12)

    def test_non_positive_length_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.strap_resistance_ohm(1.68e-8, 0.0, 4.0)

    def test_non_positive_cross_section_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.strap_resistance_ohm(1.68e-8, 100.0, -1.0)

    def test_non_numeric_resistivity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.strap_resistance_ohm("copper", 100.0, 4.0)

    def test_strap_exactly_at_its_limit_passes(self):
        limit = logic.bonding_resistance_limit_ohm("class-s")
        self.assertAlmostEqual(limit, 1.0, places=12)
        self.assertTrue(logic.strap_meets_limit(limit, "class-s"))

    def test_strap_above_its_limit_fails(self):
        self.assertFalse(logic.strap_meets_limit(2.0, "class-s"))

    def test_static_strap_would_fail_the_rf_reference_limit(self):
        self.assertTrue(logic.strap_meets_limit(0.5, "class-s"))
        self.assertFalse(logic.strap_meets_limit(0.5, "class-r"))

    def test_negative_resistance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.strap_meets_limit(-0.1, "class-s")

    def test_negative_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.strap_meets_limit(1.0, "class-s", tolerance_rel=-1e-9)


class TestSurfaceMaterials(unittest.TestCase):
    def test_low_resistivity_surface_is_conductive(self):
        self.assertEqual(logic.surface_material_band(1.0e3), logic.BAND_CONDUCTIVE)

    def test_mid_resistivity_surface_is_dissipative(self):
        self.assertEqual(logic.surface_material_band(1.0e7), logic.BAND_DISSIPATIVE)

    def test_high_resistivity_surface_is_insulating(self):
        self.assertEqual(logic.surface_material_band(1.0e12), logic.BAND_INSULATING)

    def test_value_exactly_on_the_conductive_edge_stays_conductive(self):
        edge = logic.CONDUCTIVE_CEILING_OHM_PER_SQUARE
        self.assertAlmostEqual(edge, 1.0e5, places=6)
        self.assertEqual(logic.surface_material_band(edge), logic.BAND_CONDUCTIVE)

    def test_value_exactly_on_the_dissipative_edge_stays_dissipative(self):
        edge = logic.DISSIPATIVE_CEILING_OHM_PER_SQUARE
        self.assertEqual(logic.surface_material_band(edge), logic.BAND_DISSIPATIVE)

    def test_non_positive_resistivity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.surface_material_band(0.0)

    def test_exposed_insulating_surface_is_not_acceptable(self):
        self.assertFalse(logic.exposed_surface_is_acceptable(1.0e12))
        self.assertTrue(logic.exposed_surface_is_acceptable(1.0e7))


class TestRelaxation(unittest.TestCase):
    def test_relaxation_time_scales_with_resistivity(self):
        slow = logic.relaxation_time_s(2.0e8, 3.0)
        fast = logic.relaxation_time_s(1.0e8, 3.0)
        self.assertAlmostEqual(slow, 2.0 * fast, places=12)

    def test_relaxation_time_uses_the_vacuum_permittivity(self):
        value = logic.relaxation_time_s(1.0e9, 1.0)
        self.assertAlmostEqual(value, 8.8541878128e-3, places=12)

    def test_permittivity_below_unity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.relaxation_time_s(1.0e9, 0.5)

    def test_non_positive_resistivity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.relaxation_time_s(0.0, 3.0)

    def test_relaxation_exactly_at_the_limit_passes(self):
        tau = logic.relaxation_time_s(1.0e9, 1.0)
        self.assertTrue(logic.equalizes_in_time(tau, tau))

    def test_relaxation_above_the_limit_fails(self):
        self.assertFalse(logic.equalizes_in_time(10.0, 1.0))

    def test_non_positive_limit_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.equalizes_in_time(1.0, 0.0)


class TestBlanketGrounding(unittest.TestCase):
    def test_small_blanket_keeps_the_redundancy_floor(self):
        self.assertEqual(logic.required_ground_tabs(0.1, 0.5), 2)

    def test_tab_count_is_rounded_up(self):
        self.assertEqual(logic.required_ground_tabs(1.2, 0.5), 3)

    def test_exact_multiple_does_not_gain_a_spurious_tab(self):
        self.assertEqual(logic.required_ground_tabs(1.5, 0.5), 3)
        self.assertEqual(logic.required_ground_tabs(0.3, 0.1), 3)

    def test_non_positive_area_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.required_ground_tabs(0.0, 0.5)

    def test_non_positive_area_per_tab_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.required_ground_tabs(1.0, 0.0)

    def test_blanket_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.blanket_grounding_report("upper-stage-blanket")

    def test_blanket_without_an_id_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.blanket_grounding_report(blanket(id=" "))

    def test_fractional_layer_count_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.blanket_grounding_report(blanket(layer_count=12.5))

    def test_more_grounded_layers_than_layers_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.blanket_grounding_report(blanket(grounded_layer_count=13))

    def test_ungrounded_layer_is_reported(self):
        report = logic.blanket_grounding_report(blanket(grounded_layer_count=11))
        self.assertFalse(report["all_layers_grounded"])

    def test_tab_shortfall_is_reported(self):
        report = logic.blanket_grounding_report(blanket(ground_tab_count=1))
        self.assertFalse(report["tabs_sufficient"])
        self.assertEqual(report["required_ground_tabs"], 2)

    def test_compliant_blanket_reports_clean(self):
        report = logic.blanket_grounding_report(blanket())
        self.assertTrue(report["all_layers_grounded"])
        self.assertTrue(report["tabs_sufficient"])


class TestTopLevelVerification(unittest.TestCase):
    def test_a_compliant_vehicle_closes_clean(self):
        report = logic.verify_static_charging_provisions(charging_config())
        self.assertTrue(report["acceptable"])
        self.assertEqual(report["findings"], ())

    def test_insulating_exposed_surface_is_a_finding(self):
        cfg = charging_config()
        cfg["materials"] = [material(sheet_resistivity_ohm_per_square=1.0e13)]
        report = logic.verify_static_charging_provisions(cfg)
        self.assertIn("insulating-exposed-surface:outer-skin-paint", report["findings"])

    def test_buried_insulating_surface_is_not_a_finding(self):
        cfg = charging_config()
        cfg["materials"] = [
            material(id="inner-liner", sheet_resistivity_ohm_per_square=1.0e13, exposed=False)
        ]
        report = logic.verify_static_charging_provisions(cfg)
        self.assertTrue(report["acceptable"])

    def test_slow_relaxation_on_an_exposed_surface_is_a_finding(self):
        cfg = charging_config()
        cfg["materials"] = [material(volume_resistivity_ohm_m=1.0e13)]
        report = logic.verify_static_charging_provisions(cfg)
        self.assertIn("slow-charge-relaxation:outer-skin-paint", report["findings"])

    def test_strap_over_its_limit_is_a_finding(self):
        cfg = charging_config()
        cfg["straps"] = [strap(id="rf-bracket", category="class-r", resistance_ohm=0.05)]
        report = logic.verify_static_charging_provisions(cfg)
        self.assertIn("bonding-strap-over-limit:rf-bracket", report["findings"])

    def test_strap_resistance_is_computed_when_geometry_is_given(self):
        cfg = charging_config()
        cfg["straps"] = [
            {
                "id": "computed-strap",
                "category": "class-s",
                "resistivity_ohm_m": 1.68e-8,
                "length_mm": 100.0,
                "cross_section_mm2": 4.0,
            }
        ]
        report = logic.verify_static_charging_provisions(cfg)
        self.assertAlmostEqual(report["straps"][0]["resistance_ohm"], 4.2e-4, places=12)
        self.assertTrue(report["straps"][0]["meets_limit"])

    def test_ungrounded_blanket_layer_is_a_finding(self):
        cfg = charging_config()
        cfg["blankets"] = [blanket(grounded_layer_count=10)]
        report = logic.verify_static_charging_provisions(cfg)
        self.assertIn("blanket-layer-not-grounded:upper-stage-blanket", report["findings"])

    def test_tab_shortfall_is_a_finding(self):
        cfg = charging_config()
        cfg["blankets"] = [blanket(area_m2=4.0, ground_tab_count=3)]
        report = logic.verify_static_charging_provisions(cfg)
        self.assertIn("insufficient-ground-tabs:upper-stage-blanket", report["findings"])

    def test_configuration_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.verify_static_charging_provisions("vehicle")

    def test_missing_material_list_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.verify_static_charging_provisions(charging_config(materials=[]))

    def test_missing_strap_list_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.verify_static_charging_provisions(charging_config(straps=[]))

    def test_missing_blanket_list_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.verify_static_charging_provisions(charging_config(blankets=[]))

    def test_material_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.verify_static_charging_provisions(charging_config(materials=["skin"]))

    def test_every_material_band_is_reported(self):
        report = logic.verify_static_charging_provisions(charging_config())
        self.assertEqual(len(report["materials"]), 2)
        for entry in report["materials"]:
            self.assertIn(entry["band"], logic.MATERIAL_BANDS)


if __name__ == "__main__":
    unittest.main()
