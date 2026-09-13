#!/usr/bin/env python3
"""Gate 3 contract test for e2006-conductive-surface-material-general-rule."""

import unittest

from e2006_conductive_surface_material_general_rule_logic import (
    DEFAULT_SURFACE_POTENTIAL_CEILING_V,
    FINDING_ABOVE_CEILING,
    FINDING_NOT_BONDED,
    FINDING_SLOW_DECAY,
    METALLIC_MAX_OHM_M,
    PARTIALLY_DISSIPATIVE_MAX_OHM_M,
    REGIME_INSULATING,
    REGIME_METALLIC,
    REGIME_PARTIALLY_DISSIPATIVE,
    REGIME_STATIC_DISSIPATIVE,
    STATIC_DISSIPATIVE_MAX_OHM_M,
    VACUUM_PERMITTIVITY_F_PER_M,
    assess_outer_surface_inventory,
    categorize_conduction_regime,
    charge_decay_time_constant,
    evaluate_surface_material,
    format_material_report,
    lateral_potential,
    max_allowable_bulk_resistivity,
    normalize_material,
    sheet_resistance_from_bulk,
    through_thickness_potential,
)


def material(**overrides):
    record = {
        "surface_id": "radiator-coating-1",
        "material_name": "conductive-white-paint",
        "drain_path": "through-thickness-to-backing",
        "grounded_to_structure": True,
        "bulk_resistivity_ohm_m": 1.0e8,
        "thickness_m": 1.0e-4,
        "characteristic_length_m": 0.2,
        "relative_permittivity": 3.0,
    }
    record.update(overrides)
    return record


class SheetResistanceTests(unittest.TestCase):
    def test_sheet_resistance_is_resistivity_over_thickness(self):
        self.assertAlmostEqual(sheet_resistance_from_bulk(1.0e8, 1.0e-4), 1.0e12)

    def test_thinner_layer_has_higher_sheet_resistance(self):
        thin = sheet_resistance_from_bulk(1.0e8, 1.0e-6)
        thick = sheet_resistance_from_bulk(1.0e8, 1.0e-4)
        self.assertGreater(thin, thick)

    def test_zero_thickness_rejected(self):
        with self.assertRaises(ValueError):
            sheet_resistance_from_bulk(1.0e8, 0.0)

    def test_negative_resistivity_rejected(self):
        with self.assertRaises(ValueError):
            sheet_resistance_from_bulk(-1.0, 1.0e-4)

    def test_non_numeric_resistivity_rejected(self):
        with self.assertRaises(ValueError):
            sheet_resistance_from_bulk("very-high", 1.0e-4)


class ThroughThicknessTests(unittest.TestCase):
    def test_ohmic_drop_across_the_layer(self):
        self.assertAlmostEqual(
            through_thickness_potential(1.0e-6, 1.0e10, 1.0e-4), 1.0, places=9
        )

    def test_zero_current_leaves_no_potential(self):
        self.assertAlmostEqual(
            through_thickness_potential(0.0, 1.0e12, 1.0e-3), 0.0, places=12
        )

    def test_negative_current_density_rejected(self):
        with self.assertRaises(ValueError):
            through_thickness_potential(-1.0e-6, 1.0e10, 1.0e-4)

    def test_zero_thickness_rejected(self):
        with self.assertRaises(ValueError):
            through_thickness_potential(1.0e-6, 1.0e10, 0.0)

    def test_non_finite_current_rejected(self):
        with self.assertRaises(ValueError):
            through_thickness_potential(float("nan"), 1.0e10, 1.0e-4)


class LateralPotentialTests(unittest.TestCase):
    def test_lateral_rise_scales_with_length_squared(self):
        near = lateral_potential(1.0e-6, 1.0e9, 0.1)
        far = lateral_potential(1.0e-6, 1.0e9, 0.2)
        self.assertAlmostEqual(far / near, 4.0, places=9)

    def test_lateral_rise_value(self):
        self.assertAlmostEqual(lateral_potential(1.0e-6, 1.0e9, 0.1), 5.0, places=9)

    def test_geometry_factor_can_be_overridden(self):
        self.assertAlmostEqual(
            lateral_potential(1.0e-6, 1.0e9, 0.1, geometry_factor=1.0), 10.0, places=9
        )

    def test_zero_length_rejected(self):
        with self.assertRaises(ValueError):
            lateral_potential(1.0e-6, 1.0e9, 0.0)

    def test_zero_geometry_factor_rejected(self):
        with self.assertRaises(ValueError):
            lateral_potential(1.0e-6, 1.0e9, 0.1, geometry_factor=0.0)


class AllowableResistivityTests(unittest.TestCase):
    def test_allowable_resistivity_from_ceiling(self):
        self.assertAlmostEqual(
            max_allowable_bulk_resistivity(100.0, 1.0e-6, 1.0e-3) / 1.0e11, 1.0, places=9
        )

    def test_thicker_layer_allows_less_resistivity(self):
        thin = max_allowable_bulk_resistivity(100.0, 1.0e-6, 1.0e-5)
        thick = max_allowable_bulk_resistivity(100.0, 1.0e-6, 1.0e-3)
        self.assertGreater(thin, thick)

    def test_zero_current_density_rejected(self):
        with self.assertRaises(ValueError):
            max_allowable_bulk_resistivity(100.0, 0.0, 1.0e-3)

    def test_zero_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            max_allowable_bulk_resistivity(0.0, 1.0e-6, 1.0e-3)


class DecayTimeTests(unittest.TestCase):
    def test_decay_time_is_relaxation_time(self):
        self.assertAlmostEqual(
            charge_decay_time_constant(1.0e12, 3.0),
            1.0e12 * VACUUM_PERMITTIVITY_F_PER_M * 3.0,
            places=9,
        )

    def test_vacuum_permittivity_gives_shortest_decay(self):
        self.assertLess(
            charge_decay_time_constant(1.0e12, 1.0),
            charge_decay_time_constant(1.0e12, 4.0),
        )

    def test_permittivity_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            charge_decay_time_constant(1.0e12, 0.5)

    def test_negative_resistivity_rejected(self):
        with self.assertRaises(ValueError):
            charge_decay_time_constant(-1.0e12, 3.0)


class ConductionRegimeTests(unittest.TestCase):
    def test_metal_is_metallic(self):
        self.assertEqual(categorize_conduction_regime(1.0e-7), REGIME_METALLIC)

    def test_metallic_upper_bound_is_inclusive(self):
        self.assertEqual(
            categorize_conduction_regime(METALLIC_MAX_OHM_M), REGIME_METALLIC
        )

    def test_dissipative_coating(self):
        self.assertEqual(categorize_conduction_regime(1.0e3), REGIME_STATIC_DISSIPATIVE)

    def test_dissipative_upper_bound_is_inclusive(self):
        self.assertEqual(
            categorize_conduction_regime(STATIC_DISSIPATIVE_MAX_OHM_M),
            REGIME_STATIC_DISSIPATIVE,
        )

    def test_partially_dissipative_band(self):
        self.assertEqual(
            categorize_conduction_regime(1.0e7), REGIME_PARTIALLY_DISSIPATIVE
        )

    def test_partially_dissipative_upper_bound_is_inclusive(self):
        self.assertEqual(
            categorize_conduction_regime(PARTIALLY_DISSIPATIVE_MAX_OHM_M),
            REGIME_PARTIALLY_DISSIPATIVE,
        )

    def test_insulator_is_flagged(self):
        self.assertEqual(categorize_conduction_regime(1.0e14), REGIME_INSULATING)

    def test_zero_resistivity_rejected(self):
        with self.assertRaises(ValueError):
            categorize_conduction_regime(0.0)


class NormalizeMaterialTests(unittest.TestCase):
    def test_valid_record_is_normalized(self):
        out = normalize_material(material(surface_id=" panel-b "))
        self.assertEqual(out["surface_id"], "panel-b")
        self.assertAlmostEqual(out["thickness_m"], 1.0e-4)

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            normalize_material("conductive-white-paint")

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            normalize_material(material(surface_id=""))

    def test_blank_material_name_rejected(self):
        with self.assertRaises(ValueError):
            normalize_material(material(material_name="  "))

    def test_unknown_drain_path_rejected(self):
        with self.assertRaises(ValueError):
            normalize_material(material(drain_path="evaporation"))

    def test_non_boolean_ground_flag_rejected(self):
        with self.assertRaises(ValueError):
            normalize_material(material(grounded_to_structure="yes"))

    def test_missing_resistivity_rejected(self):
        record = material()
        del record["bulk_resistivity_ohm_m"]
        with self.assertRaises(ValueError):
            normalize_material(record)

    def test_zero_thickness_rejected(self):
        with self.assertRaises(ValueError):
            normalize_material(material(thickness_m=0.0))

    def test_permittivity_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_material(material(relative_permittivity=0.9))


class EvaluateMaterialTests(unittest.TestCase):
    def test_conductive_coating_is_compliant(self):
        out = evaluate_surface_material(
            material(bulk_resistivity_ohm_m=1.0e-5, thickness_m=1.0e-5)
        )
        self.assertTrue(out["compliant"])
        self.assertEqual(out["conduction_regime"], REGIME_METALLIC)

    def test_potential_exactly_at_ceiling_is_compliant(self):
        out = evaluate_surface_material(
            material(bulk_resistivity_ohm_m=1.0e11, thickness_m=1.0e-3)
        )
        self.assertAlmostEqual(
            out["governing_potential_v"], DEFAULT_SURFACE_POTENTIAL_CEILING_V, places=9
        )
        self.assertTrue(out["compliant"])
        self.assertEqual(out["findings"], [])

    def test_resistive_layer_breaches_the_ceiling(self):
        out = evaluate_surface_material(
            material(bulk_resistivity_ohm_m=1.0e12, thickness_m=1.0e-3)
        )
        self.assertIn(FINDING_ABOVE_CEILING, out["findings"])
        self.assertFalse(out["compliant"])

    def test_slow_bleed_off_is_flagged_on_its_own(self):
        out = evaluate_surface_material(
            material(bulk_resistivity_ohm_m=2.0e14, thickness_m=1.0e-7)
        )
        self.assertEqual(out["findings"], [FINDING_SLOW_DECAY])
        self.assertGreater(out["charge_decay_time_constant_s"], out["decay_limit_s"])

    def test_unbonded_material_is_flagged(self):
        out = evaluate_surface_material(
            material(
                bulk_resistivity_ohm_m=1.0e-5,
                thickness_m=1.0e-5,
                grounded_to_structure=False,
            )
        )
        self.assertEqual(out["findings"], [FINDING_NOT_BONDED])

    def test_lateral_drain_path_governs_when_selected(self):
        out = evaluate_surface_material(
            material(
                drain_path="lateral-to-grounded-edge",
                bulk_resistivity_ohm_m=1.0e5,
                thickness_m=1.0e-4,
                characteristic_length_m=0.1,
            )
        )
        self.assertEqual(out["governing_drain_path"], "lateral-to-grounded-edge")
        self.assertAlmostEqual(out["governing_potential_v"], 5.0, places=6)

    def test_two_drain_paths_pick_the_easier_one(self):
        out = evaluate_surface_material(
            material(
                drain_path="both-paths-available",
                bulk_resistivity_ohm_m=1.0e10,
                thickness_m=1.0e-3,
                characteristic_length_m=1.0e-4,
            )
        )
        self.assertEqual(out["governing_drain_path"], "lateral-to-grounded-edge")
        self.assertLess(
            out["governing_potential_v"], out["through_thickness_potential_v"]
        )

    def test_two_drain_paths_can_select_the_backing(self):
        out = evaluate_surface_material(
            material(
                drain_path="both-paths-available",
                bulk_resistivity_ohm_m=1.0e10,
                thickness_m=1.0e-3,
                characteristic_length_m=1.0,
            )
        )
        self.assertEqual(out["governing_drain_path"], "through-thickness-to-backing")

    def test_margin_is_ceiling_minus_governing_potential(self):
        out = evaluate_surface_material(
            material(bulk_resistivity_ohm_m=1.0e10, thickness_m=1.0e-3)
        )
        self.assertAlmostEqual(
            out["potential_margin_v"],
            out["ceiling_v"] - out["governing_potential_v"],
            places=9,
        )

    def test_custom_ceiling_changes_the_verdict(self):
        record = material(bulk_resistivity_ohm_m=1.0e11, thickness_m=1.0e-3)
        self.assertFalse(evaluate_surface_material(record, ceiling_v=50.0)["compliant"])

    def test_anchor_clause_is_reported(self):
        out = evaluate_surface_material(material())
        self.assertEqual(out["anchor"], "ECSS-E-ST-20-06C 6.3.3.2")

    def test_negative_current_density_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_surface_material(material(), current_density_a_per_m2=-1.0e-6)


class InventoryTests(unittest.TestCase):
    def test_inventory_aggregates_results(self):
        out = assess_outer_surface_inventory(
            [
                material(surface_id="a", bulk_resistivity_ohm_m=1.0e-5, thickness_m=1.0e-5),
                material(surface_id="b", bulk_resistivity_ohm_m=1.0e12, thickness_m=1.0e-3),
            ]
        )
        self.assertEqual(out["compliant_count"], 1)
        self.assertEqual(out["non_compliant"], ["b"])
        self.assertEqual(out["worst_surface_id"], "b")
        self.assertFalse(out["compliant"])

    def test_all_compliant_inventory(self):
        out = assess_outer_surface_inventory(
            [material(surface_id="a", bulk_resistivity_ohm_m=1.0e-5, thickness_m=1.0e-5)]
        )
        self.assertTrue(out["compliant"])

    def test_duplicate_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_outer_surface_inventory(
                [material(surface_id="a"), material(surface_id="a")]
            )

    def test_empty_inventory_rejected(self):
        with self.assertRaises(ValueError):
            assess_outer_surface_inventory([])

    def test_non_sequence_inventory_rejected(self):
        with self.assertRaises(ValueError):
            assess_outer_surface_inventory(material())


class ReportTests(unittest.TestCase):
    def test_report_lists_each_material(self):
        assessment = assess_outer_surface_inventory(
            [
                material(surface_id="a", bulk_resistivity_ohm_m=1.0e-5, thickness_m=1.0e-5),
                material(surface_id="b", bulk_resistivity_ohm_m=1.0e12, thickness_m=1.0e-3),
            ]
        )
        text = format_material_report(assessment)
        self.assertIn("a (conductive-white-paint)", text)
        self.assertIn("finding: %s" % FINDING_ABOVE_CEILING, text)
        self.assertIn("compliant=false", text)

    def test_report_rejects_foreign_input(self):
        with self.assertRaises(ValueError):
            format_material_report({"results_missing": True})


if __name__ == "__main__":
    unittest.main()
