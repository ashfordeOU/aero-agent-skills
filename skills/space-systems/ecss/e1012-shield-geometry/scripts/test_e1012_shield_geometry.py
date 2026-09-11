"""
Gate-3 contract tests for e1012-shield-geometry logic.
Covers layer creation, areal-density summation, geometry-model assembly,
interface checking, evaluation and validation.
stdlib unittest only — offline, deterministic.
Run: python3 test_e1012_shield_geometry.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from e1012_shield_geometry_logic import (
    ShieldingError,
    ShieldInterface,
    ShieldLayer,
    TIER_EQUIPMENT,
    TIER_PARTS_PACKAGING,
    TIER_SPACECRAFT,
    TIERS,
    build_geometry_model,
    check_interfaces,
    evaluate_shielding,
    layer_areal_density,
    make_layer,
    tier_areal_density,
    total_effective_shielding,
    validate_geometry_model,
)


# Representative spacecraft lay-up: ceramic package body, aluminium box wall,
# aluminium structural panel. All densities are bulk material values (g/cm³).
PKG = make_layer("package_body", "alumina", 0.08, 3.9, TIER_PARTS_PACKAGING)
EQP = make_layer("box_wall", "aluminium", 0.2, 2.7, TIER_EQUIPMENT)
SCP = make_layer("panel", "aluminium", 0.4, 2.7, TIER_SPACECRAFT)


class TestLayerCreation(unittest.TestCase):

    def test_make_layer_areal_density(self):
        # 0.1 cm × 3.9 g/cm³ = 0.39 g/cm²
        layer = make_layer("lid", "alumina", 0.1, 3.9, TIER_PARTS_PACKAGING)
        self.assertAlmostEqual(layer.areal_density_g_cm2, 0.39, places=9)

    def test_layer_areal_density_helper_matches_property(self):
        self.assertAlmostEqual(
            layer_areal_density(PKG), PKG.areal_density_g_cm2, places=12
        )

    def test_layer_areal_density_rejects_non_layer(self):
        with self.assertRaises(ShieldingError):
            layer_areal_density("not-a-layer")

    def test_zero_thickness_layer_allowed(self):
        layer = make_layer("shim", "aluminium", 0.0, 2.7, TIER_EQUIPMENT)
        self.assertEqual(layer.areal_density_g_cm2, 0.0)

    def test_empty_layer_name_raises(self):
        with self.assertRaises(ShieldingError):
            make_layer("", "aluminium", 0.2, 2.7, TIER_EQUIPMENT)

    def test_empty_material_raises(self):
        with self.assertRaises(ShieldingError):
            make_layer("wall", "", 0.2, 2.7, TIER_EQUIPMENT)

    def test_negative_thickness_raises(self):
        with self.assertRaises(ShieldingError):
            make_layer("wall", "aluminium", -0.1, 2.7, TIER_EQUIPMENT)

    def test_zero_density_raises(self):
        with self.assertRaises(ShieldingError):
            make_layer("wall", "aluminium", 0.2, 0.0, TIER_EQUIPMENT)

    def test_negative_density_raises(self):
        with self.assertRaises(ShieldingError):
            make_layer("wall", "aluminium", 0.2, -2.7, TIER_EQUIPMENT)

    def test_unknown_tier_raises(self):
        with self.assertRaises(ShieldingError):
            make_layer("wall", "aluminium", 0.2, 2.7, "propulsion_bay")


class TestArealDensitySummation(unittest.TestCase):

    LAYERS = [PKG, EQP, SCP]

    def test_tier_areal_density_selects_only_its_tier(self):
        # Equipment tier holds exactly one layer: 0.2 × 2.7 = 0.54 g/cm²
        self.assertAlmostEqual(
            tier_areal_density(self.LAYERS, TIER_EQUIPMENT), 0.54, places=9
        )

    def test_tier_areal_density_sums_multiple_layers(self):
        extra = make_layer("cover_plate", "titanium", 0.05, 4.5, TIER_EQUIPMENT)
        # 0.54 + 0.05 × 4.5 = 0.765 g/cm²
        self.assertAlmostEqual(
            tier_areal_density(self.LAYERS + [extra], TIER_EQUIPMENT),
            0.765,
            places=9,
        )

    def test_tier_with_no_layers_is_zero(self):
        self.assertEqual(tier_areal_density([PKG], TIER_SPACECRAFT), 0.0)

    def test_tier_areal_density_unknown_tier_raises(self):
        with self.assertRaises(ShieldingError):
            tier_areal_density(self.LAYERS, "no_such_tier")

    def test_total_effective_shielding_sums_all_tiers(self):
        # 0.312 (pkg) + 0.54 (eqp) + 1.08 (scp) = 1.932 g/cm²
        expected = 0.08 * 3.9 + 0.2 * 2.7 + 0.4 * 2.7
        self.assertAlmostEqual(
            total_effective_shielding(self.LAYERS), expected, places=9
        )

    def test_total_equals_sum_of_tier_contributions(self):
        total = total_effective_shielding(self.LAYERS)
        tier_sum = sum(tier_areal_density(self.LAYERS, t) for t in TIERS)
        self.assertAlmostEqual(total, tier_sum, places=12)

    def test_total_effective_shielding_empty_raises(self):
        with self.assertRaises(ShieldingError):
            total_effective_shielding([])

    def test_total_rejects_non_layer_member(self):
        with self.assertRaises(ShieldingError):
            total_effective_shielding([PKG, 0.5])


class TestGeometryModelAssembly(unittest.TestCase):

    def test_build_geometry_model_structure(self):
        model = build_geometry_model("sram_01", [PKG, EQP, SCP])
        self.assertEqual(model["part_id"], "sram_01")
        self.assertEqual(set(model["tiers"]), set(TIERS))
        self.assertEqual(len(model["layers"]), 3)
        self.assertEqual(model["interfaces"], [])
        self.assertAlmostEqual(
            model["total_effective_shielding_g_cm2"], 1.932, places=9
        )

    def test_build_geometry_model_carries_interfaces(self):
        iface = ShieldInterface("J1_connector", TIER_EQUIPMENT, 0.05)
        model = build_geometry_model("sram_01", [PKG, EQP, SCP], [iface])
        self.assertEqual(len(model["interfaces"]), 1)
        self.assertIs(model["interfaces"][0], iface)

    def test_build_geometry_model_empty_part_id_raises(self):
        with self.assertRaises(ShieldingError):
            build_geometry_model("", [PKG])

    def test_build_geometry_model_no_layers_raises(self):
        with self.assertRaises(ShieldingError):
            build_geometry_model("sram_01", [])

    def test_build_geometry_model_tier_values_match_helpers(self):
        model = build_geometry_model("sram_01", [PKG, EQP, SCP])
        for tier in TIERS:
            self.assertAlmostEqual(
                model["tiers"][tier],
                tier_areal_density([PKG, EQP, SCP], tier),
                places=12,
            )


class TestInterfaceChecks(unittest.TestCase):

    def test_interface_flags_below_threshold(self):
        iface = ShieldInterface("feedthrough", TIER_EQUIPMENT, 0.05)
        findings = check_interfaces([iface], 0.15)
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["interface"], "feedthrough")
        self.assertAlmostEqual(findings[0]["shortfall_g_cm2"], 0.10, places=9)

    def test_interface_at_threshold_passes(self):
        iface = ShieldInterface("feedthrough", TIER_EQUIPMENT, 0.15)
        self.assertEqual(check_interfaces([iface], 0.15), [])

    def test_interface_above_threshold_passes(self):
        iface = ShieldInterface("connector", TIER_EQUIPMENT, 0.40)
        self.assertEqual(check_interfaces([iface], 0.15), [])

    def test_check_interfaces_empty_list(self):
        self.assertEqual(check_interfaces([], 0.15), [])

    def test_negative_threshold_raises(self):
        with self.assertRaises(ShieldingError):
            check_interfaces([], -0.01)

    def test_check_interfaces_rejects_non_interface(self):
        with self.assertRaises(ShieldingError):
            check_interfaces([{"name": "x"}], 0.1)

    def test_interface_empty_name_raises(self):
        with self.assertRaises(ShieldingError):
            ShieldInterface("", TIER_EQUIPMENT, 0.1)

    def test_interface_unknown_tier_raises(self):
        with self.assertRaises(ShieldingError):
            ShieldInterface("connector", "bogus", 0.1)

    def test_interface_negative_areal_density_raises(self):
        with self.assertRaises(ShieldingError):
            ShieldInterface("connector", TIER_EQUIPMENT, -0.1)


class TestEvaluation(unittest.TestCase):

    def test_compliant_when_above_both_minima(self):
        model = build_geometry_model("sram_01", [PKG, EQP, SCP])
        res = evaluate_shielding(model, 1.0, 0.0)
        self.assertTrue(res["compliant"])
        self.assertEqual(res["deficiency_findings"], [])
        self.assertEqual(res["gap_findings"], [])

    def test_deficiency_finding_when_total_too_low(self):
        model = build_geometry_model("sram_01", [PKG])
        res = evaluate_shielding(model, 1.0, 0.0)
        self.assertFalse(res["compliant"])
        self.assertEqual(len(res["deficiency_findings"]), 1)
        self.assertAlmostEqual(
            res["deficiency_findings"][0]["shortfall_g_cm2"],
            1.0 - 0.312,
            places=9,
        )

    def test_gap_finding_from_weak_interface(self):
        iface = ShieldInterface("cutout", TIER_SPACECRAFT, 0.01)
        model = build_geometry_model("sram_01", [PKG, EQP, SCP], [iface])
        res = evaluate_shielding(model, 1.0, 0.10)
        self.assertFalse(res["compliant"])
        self.assertEqual(res["deficiency_findings"], [])
        self.assertEqual(len(res["gap_findings"]), 1)

    def test_both_findings_reported_together(self):
        iface = ShieldInterface("cutout", TIER_SPACECRAFT, 0.01)
        model = build_geometry_model("sram_01", [PKG], [iface])
        res = evaluate_shielding(model, 5.0, 0.10)
        self.assertEqual(len(res["deficiency_findings"]), 1)
        self.assertEqual(len(res["gap_findings"]), 1)
        self.assertFalse(res["compliant"])

    def test_evaluate_negative_minimum_raises(self):
        model = build_geometry_model("sram_01", [PKG, EQP, SCP])
        with self.assertRaises(ShieldingError):
            evaluate_shielding(model, -1.0, 0.0)
        with self.assertRaises(ShieldingError):
            evaluate_shielding(model, 1.0, -0.1)

    def test_evaluate_rejects_inconsistent_model(self):
        model = build_geometry_model("sram_01", [PKG, EQP, SCP])
        model["total_effective_shielding_g_cm2"] = 99.0  # tampered
        with self.assertRaises(ShieldingError):
            evaluate_shielding(model, 1.0, 0.0)


class TestModelValidation(unittest.TestCase):

    def test_valid_model_returns_no_errors(self):
        model = build_geometry_model("sram_01", [PKG, EQP, SCP])
        self.assertEqual(validate_geometry_model(model), [])

    def test_non_dict_raises(self):
        with self.assertRaises(ShieldingError):
            validate_geometry_model(["not", "a", "dict"])

    def test_missing_tier_detected(self):
        model = build_geometry_model("sram_01", [PKG, EQP, SCP])
        del model["tiers"][TIER_SPACECRAFT]
        errors = validate_geometry_model(model)
        self.assertTrue(any("missing" in e for e in errors))

    def test_total_mismatch_detected(self):
        model = build_geometry_model("sram_01", [PKG, EQP, SCP])
        model["total_effective_shielding_g_cm2"] = 1.0
        errors = validate_geometry_model(model)
        self.assertTrue(any("does not equal" in e for e in errors))

    def test_empty_part_id_detected(self):
        model = build_geometry_model("sram_01", [PKG, EQP, SCP])
        model["part_id"] = ""
        self.assertTrue(any("part_id" in e for e in validate_geometry_model(model)))

    def test_missing_layers_detected(self):
        model = build_geometry_model("sram_01", [PKG, EQP, SCP])
        model["layers"] = []
        self.assertTrue(
            any("layers" in e for e in validate_geometry_model(model))
        )


if __name__ == "__main__":
    unittest.main()
