#!/usr/bin/env python3
"""Gate 3 contract test for e2007-lightning-protection-verification.

Stdlib unittest, offline, deterministic.
"""

import unittest

import e2007_lightning_protection_verification_logic as logic


def surface(**overrides):
    rec = {
        "id": "nose-fairing",
        "zone": "zone-1a",
        "effect": "direct-effects",
        "methods": ["test"],
    }
    rec.update(overrides)
    return rec


def circuit(**overrides):
    rec = {
        "id": "pyro-loop",
        "measured_transient_v": 100.0,
        "measurement_uncertainty_db": 0.0,
        "equipment_design_level_v": 400.0,
    }
    rec.update(overrides)
    return rec


def protection_config(**overrides):
    cfg = {
        "surfaces": [
            surface(),
            surface(id="aft-skirt", zone="zone-2b", methods=["similarity"]),
            surface(id="internal-harness-run", zone="zone-3", methods=["analysis"]),
        ],
        "circuits": [circuit(), circuit(id="ordnance-bus")],
        "declared_zones": ["zone-1a", "zone-2b", "zone-3"],
        "required_margin_db": 6.0,
    }
    cfg.update(overrides)
    return cfg


class TestZoning(unittest.TestCase):
    def test_canonical_zone_is_returned(self):
        self.assertEqual(logic.attachment_zone("zone-1a"), logic.ZONE_1A)

    def test_short_zone_alias_resolves(self):
        self.assertEqual(logic.attachment_zone("2B"), logic.ZONE_2B)

    def test_descriptive_zone_alias_resolves(self):
        self.assertEqual(logic.attachment_zone("conduction-only"), logic.ZONE_3)

    def test_blank_zone_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.attachment_zone("  ")

    def test_unknown_zone_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.attachment_zone("zone-4")

    def test_conduction_only_zone_is_not_an_attachment_zone(self):
        self.assertFalse(logic.is_attachment_zone("zone-3"))
        self.assertTrue(logic.is_attachment_zone("zone-2a"))

    def test_dwell_zone_carries_the_full_continuing_current(self):
        self.assertTrue(logic.zone_requires_dwell_component("zone-1b"))
        self.assertFalse(logic.zone_requires_dwell_component("zone-1a"))

    def test_initial_attachment_zone_owes_the_first_return_stroke(self):
        self.assertIn("a", logic.zone_current_components("zone-1a"))

    def test_swept_stroke_zone_does_not_owe_the_first_return_stroke(self):
        self.assertNotIn("a", logic.zone_current_components("zone-2a"))


class TestMethods(unittest.TestCase):
    def test_canonical_method_is_returned(self):
        self.assertEqual(logic.verification_method("test"), "test")

    def test_heritage_alias_resolves_to_similarity(self):
        self.assertEqual(logic.verification_method("Heritage"), "similarity")

    def test_review_of_design_alias_resolves(self):
        self.assertEqual(logic.verification_method("rod"), "review-of-design")

    def test_blank_method_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.verification_method("")

    def test_unknown_method_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.verification_method("engineering-judgement")

    def test_effect_alias_resolves(self):
        self.assertEqual(logic.effect_kind("coupled-transients"), logic.EFFECT_INDIRECT)

    def test_unknown_effect_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.effect_kind("thermal-effects")

    def test_analysis_alone_cannot_close_an_attachment_zone(self):
        self.assertNotIn("analysis", logic.admissible_methods("direct-effects", "zone-1b"))
        self.assertFalse(
            logic.methods_close_requirement("direct-effects", "zone-1b", ["analysis"])
        )

    def test_analysis_may_close_a_conduction_only_zone(self):
        self.assertTrue(
            logic.methods_close_requirement("direct-effects", "zone-3", ["analysis"])
        )

    def test_inspection_never_closes_a_direct_effects_requirement(self):
        self.assertFalse(
            logic.methods_close_requirement("direct", "zone-3", ["inspection"])
        )

    def test_a_single_admissible_method_in_a_mixed_set_closes_it(self):
        self.assertTrue(
            logic.methods_close_requirement(
                "direct-effects", "zone-2a", ["inspection", "test"]
            )
        )

    def test_indirect_effects_admit_analysis(self):
        self.assertTrue(
            logic.methods_close_requirement("indirect-effects", "zone-1a", ["analysis"])
        )

    def test_empty_method_set_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.methods_close_requirement("direct-effects", "zone-1a", [])

    def test_method_set_must_be_a_collection(self):
        with self.assertRaises(ValueError):
            logic.methods_close_requirement("direct-effects", "zone-1a", "test")


class TestIndirectEffects(unittest.TestCase):
    def test_zero_uncertainty_leaves_the_measured_transient_unchanged(self):
        self.assertAlmostEqual(
            logic.transient_control_level_v(100.0, 0.0), 100.0, places=9
        )

    def test_six_decibel_uncertainty_roughly_doubles_the_control_level(self):
        value = logic.transient_control_level_v(100.0, 6.0206)
        self.assertAlmostEqual(value, 200.0, places=3)

    def test_non_positive_measured_transient_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.transient_control_level_v(0.0, 3.0)

    def test_negative_uncertainty_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.transient_control_level_v(100.0, -1.0)

    def test_margin_is_six_decibels_when_the_design_level_doubles_the_control(self):
        margin = logic.lightning_margin_db(200.0, 100.0)
        self.assertAlmostEqual(margin, 6.020599913279624, places=9)

    def test_equal_levels_give_zero_margin(self):
        self.assertAlmostEqual(logic.lightning_margin_db(250.0, 250.0), 0.0, places=9)

    def test_design_level_below_the_control_level_gives_a_negative_margin(self):
        self.assertLess(logic.lightning_margin_db(50.0, 200.0), -6.0)

    def test_non_positive_control_level_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.lightning_margin_db(200.0, 0.0)

    def test_non_positive_design_level_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.lightning_margin_db(-5.0, 100.0)

    def test_a_margin_landing_exactly_on_the_requirement_passes(self):
        control = 100.0
        design = control * (10.0 ** (6.0 / 20.0))
        margin = logic.lightning_margin_db(design, control)
        self.assertAlmostEqual(margin, 6.0, places=9)
        self.assertTrue(logic.meets_required_margin_db(margin, 6.0))

    def test_a_margin_below_the_requirement_fails(self):
        self.assertFalse(logic.meets_required_margin_db(3.0, 6.0))

    def test_negative_tolerance_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.meets_required_margin_db(6.0, 6.0, tolerance=-1e-9)


class TestCircuitReports(unittest.TestCase):
    def test_circuit_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.circuit_margin_report(["pyro-loop"])

    def test_circuit_without_an_id_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.circuit_margin_report(circuit(id="   "))

    def test_circuit_margin_is_twelve_decibels_at_a_four_to_one_ratio(self):
        report = logic.circuit_margin_report(circuit())
        self.assertAlmostEqual(report["margin_db"], 12.041199826559248, places=9)
        self.assertTrue(report["meets_margin"])

    def test_uncertainty_raises_the_control_level_and_eats_the_margin(self):
        report = logic.circuit_margin_report(
            circuit(measurement_uncertainty_db=12.0), required_db=6.0
        )
        self.assertFalse(report["meets_margin"])

    def test_missing_design_level_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.circuit_margin_report(circuit(equipment_design_level_v=None))


class TestSurfaceReports(unittest.TestCase):
    def test_surface_record_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.surface_closure_report("nose-fairing")

    def test_surface_without_an_id_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.surface_closure_report(surface(id=""))

    def test_surface_without_methods_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.surface_closure_report(surface(methods=[]))

    def test_tested_attachment_surface_closes(self):
        report = logic.surface_closure_report(surface())
        self.assertTrue(report["closed"])
        self.assertEqual(report["zone"], logic.ZONE_1A)
        self.assertIn("d", report["components"])

    def test_inspected_attachment_surface_does_not_close(self):
        report = logic.surface_closure_report(surface(methods=["inspection"]))
        self.assertFalse(report["closed"])


class TestTopLevelVerification(unittest.TestCase):
    def test_a_fully_verified_system_closes_clean(self):
        report = logic.verify_lightning_protection(protection_config())
        self.assertTrue(report["acceptable"])
        self.assertEqual(report["findings"], ())
        self.assertEqual(report["unverified_zones"], ())

    def test_worst_circuit_is_the_one_with_the_least_margin(self):
        cfg = protection_config()
        cfg["circuits"] = [
            circuit(),
            circuit(id="thin-margin", equipment_design_level_v=150.0),
        ]
        report = logic.verify_lightning_protection(cfg)
        self.assertEqual(report["worst_circuit"], "thin-margin")
        self.assertLess(report["worst_margin_db"], 6.0)

    def test_a_declared_zone_with_no_surface_is_a_finding(self):
        cfg = protection_config()
        cfg["declared_zones"] = ["zone-1a", "zone-1b", "zone-2b", "zone-3"]
        report = logic.verify_lightning_protection(cfg)
        self.assertIn("zone-not-verified:zone-1b", report["findings"])
        self.assertFalse(report["acceptable"])

    def test_an_inadmissible_method_is_a_finding(self):
        cfg = protection_config()
        cfg["surfaces"] = [surface(methods=["review-of-design"])]
        cfg["declared_zones"] = ["zone-1a"]
        report = logic.verify_lightning_protection(cfg)
        self.assertIn("inadmissible-method:nose-fairing", report["findings"])

    def test_a_margin_shortfall_is_a_finding(self):
        cfg = protection_config()
        cfg["circuits"] = [circuit(id="pyro-loop", equipment_design_level_v=110.0)]
        report = logic.verify_lightning_protection(cfg)
        self.assertIn("lightning-margin-shortfall:pyro-loop", report["findings"])

    def test_configuration_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            logic.verify_lightning_protection("vega-c")

    def test_a_system_without_surfaces_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.verify_lightning_protection(protection_config(surfaces=[]))

    def test_a_system_without_circuits_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.verify_lightning_protection(protection_config(circuits=[]))

    def test_declared_zones_must_be_a_collection(self):
        with self.assertRaises(ValueError):
            logic.verify_lightning_protection(protection_config(declared_zones="zone-1a"))

    def test_omitting_declared_zones_reports_no_unverified_zone(self):
        cfg = protection_config()
        del cfg["declared_zones"]
        report = logic.verify_lightning_protection(cfg)
        self.assertEqual(report["unverified_zones"], ())

    def test_covered_zones_are_returned_in_canonical_order(self):
        report = logic.verify_lightning_protection(protection_config())
        self.assertEqual(report["covered_zones"], ("zone-1a", "zone-2b", "zone-3"))


if __name__ == "__main__":
    unittest.main()
