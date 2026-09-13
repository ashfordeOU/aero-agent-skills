"""Gate 3 contract test for e2006-common-charging-engineering-concerns.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2006_common_charging_engineering_concerns.py
"""

import math
import unittest

import e2006_common_charging_engineering_concerns_logic as logic


def surface(**overrides):
    item = {
        "name": "thermal-blanket-outer-layer",
        "kind": "external-surface",
        "potential_v": -200.0,
        "reference_potential_v": -100.0,
    }
    item.update(overrides)
    return item


def dielectric(**overrides):
    item = {
        "name": "harness-insulation",
        "kind": "buried-dielectric",
        "deposited_current_density_a_m2": 1.0e-11,
        "resistivity_ohm_m": 1.0e15,
        "dielectric_strength_v_m": 6.0e7,
    }
    item.update(overrides)
    return item


def conductor(**overrides):
    item = {
        "name": "isolated-bracket",
        "kind": "floating-conductor",
        "bonded": True,
    }
    item.update(overrides)
    return item


class ThresholdTests(unittest.TestCase):
    def test_defaults_are_returned_as_a_fresh_copy(self):
        first = logic.default_thresholds()
        first["absolute_potential_limit_v"] = 1.0
        second = logic.default_thresholds()
        self.assertAlmostEqual(second["absolute_potential_limit_v"], 1000.0, places=9)

    def test_override_replaces_one_threshold_only(self):
        limits = logic.normalize_thresholds({"differential_potential_limit_v": 250.0})
        self.assertAlmostEqual(limits["differential_potential_limit_v"], 250.0, places=9)
        self.assertAlmostEqual(limits["absolute_potential_limit_v"], 1000.0, places=9)

    def test_unknown_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_thresholds({"arc_limit_v": 10.0})

    def test_non_mapping_override_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_thresholds([("differential_potential_limit_v", 250.0)])

    def test_zero_threshold_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_thresholds({"differential_potential_limit_v": 0.0})

    def test_safety_factor_below_one_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_thresholds({"bulk_field_safety_factor": 0.5})

    def test_marginal_fraction_above_one_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_thresholds({"marginal_field_fraction": 1.5})


class ItemNormalisationTests(unittest.TestCase):
    def test_surface_defaults_the_reference_potential(self):
        record = logic.normalize_item(
            {"name": "radiator", "kind": "external-surface", "potential_v": -50.0}
        )
        self.assertAlmostEqual(record["reference_potential_v"], 0.0, places=12)
        self.assertIsNone(record["adjacent_potential_v"])

    def test_unknown_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_item({"name": "strut", "kind": "antenna-horn"})

    def test_missing_name_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_item({"kind": "external-surface", "potential_v": -50.0})

    def test_non_mapping_item_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_item("radiator")

    def test_surface_without_a_potential_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_item({"name": "radiator", "kind": "external-surface"})

    def test_dielectric_without_resistivity_is_rejected(self):
        item = dielectric()
        del item["resistivity_ohm_m"]
        with self.assertRaises(ValueError):
            logic.normalize_item(item)

    def test_zero_resistivity_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_item(dielectric(resistivity_ohm_m=0.0))

    def test_negative_shield_thickness_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_item(dielectric(shield_thickness_mm=-1.0))

    def test_conductor_without_a_bonding_record_is_rejected(self):
        item = conductor()
        del item["bonded"]
        with self.assertRaises(ValueError):
            logic.normalize_item(item)

    def test_non_boolean_bonding_record_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_item(conductor(bonded="yes"))

    def test_boolean_potential_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_item(surface(potential_v=True))

    def test_non_finite_potential_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.normalize_item(surface(potential_v=float("nan")))


class PrimitiveTests(unittest.TestCase):
    def test_differential_potential_is_a_magnitude(self):
        self.assertAlmostEqual(
            logic.differential_potential(-1200.0, -800.0), 400.0, places=9
        )
        self.assertAlmostEqual(
            logic.differential_potential(-800.0, -1200.0), 400.0, places=9
        )

    def test_differential_potential_rejects_a_string(self):
        with self.assertRaises(ValueError):
            logic.differential_potential("-1200", 0.0)

    def test_bulk_field_is_current_density_times_resistivity(self):
        self.assertAlmostEqual(
            logic.bulk_field(2.0e-10, 1.0e17) / 2.0e7, 1.0, places=12
        )

    def test_bulk_field_rejects_zero_resistivity(self):
        with self.assertRaises(ValueError):
            logic.bulk_field(2.0e-10, 0.0)

    def test_allowable_field_applies_the_safety_factor(self):
        self.assertAlmostEqual(
            logic.allowable_bulk_field(6.0e7, 2.0) / 3.0e7, 1.0, places=12
        )

    def test_allowable_field_rejects_a_factor_below_one(self):
        with self.assertRaises(ValueError):
            logic.allowable_bulk_field(6.0e7, 0.5)

    def test_exact_boundary_is_compliant(self):
        self.assertFalse(logic.exceeds_limit(400.0, 400.0))

    def test_one_unit_in_the_last_place_over_is_absorbed(self):
        drifted = math.nextafter(400.0, math.inf)
        self.assertGreater(drifted, 400.0)
        self.assertFalse(logic.exceeds_limit(drifted, 400.0))

    def test_genuine_exceedance_is_reported(self):
        self.assertTrue(logic.exceeds_limit(420.0, 400.0))

    def test_exceeds_limit_rejects_a_non_number(self):
        with self.assertRaises(ValueError):
            logic.exceeds_limit(None, 400.0)


class SurfaceConcernTests(unittest.TestCase):
    def test_quiet_surface_is_concern_free(self):
        result = logic.evaluate_item(surface())
        self.assertTrue(result["concern_free"])
        self.assertEqual(result["severity"], "none")

    def test_large_frame_potential_raises_an_excursion(self):
        result = logic.evaluate_item(
            surface(potential_v=-1500.0, reference_potential_v=-1400.0)
        )
        self.assertIn("absolute-frame-potential-excursion", result["concerns"])
        self.assertNotIn("structure-referenced-differential-esd", result["concerns"])
        self.assertEqual(result["severity"], "major")

    def test_structure_differential_raises_a_discharge_concern(self):
        result = logic.evaluate_item(surface(potential_v=-600.0, reference_potential_v=0.0))
        self.assertIn("structure-referenced-differential-esd", result["concerns"])
        self.assertEqual(result["severity"], "critical")

    def test_adjacent_surface_differential_is_reported_separately(self):
        result = logic.evaluate_item(surface(adjacent_potential_v=400.0))
        self.assertEqual(result["concerns"], ("adjacent-surface-differential-esd",))

    def test_one_surface_can_carry_every_surface_concern(self):
        result = logic.evaluate_item(
            surface(
                potential_v=-2000.0,
                reference_potential_v=0.0,
                adjacent_potential_v=-500.0,
            )
        )
        self.assertEqual(len(result["concerns"]), 3)
        self.assertEqual(result["severity"], "critical")

    def test_differential_exactly_at_the_limit_passes(self):
        result = logic.evaluate_item(surface(potential_v=-400.0, reference_potential_v=0.0))
        self.assertTrue(result["concern_free"])

    def test_differential_drift_above_the_limit_is_absorbed(self):
        drifted = -(0.1 + 0.2)
        self.assertGreater(abs(drifted), 0.3)
        result = logic.evaluate_item(
            surface(potential_v=drifted, reference_potential_v=0.0),
            {"differential_potential_limit_v": 0.3},
        )
        self.assertTrue(result["concern_free"])

    def test_clear_exceedance_still_fails_the_tightened_limit(self):
        result = logic.evaluate_item(
            surface(potential_v=-0.5, reference_potential_v=0.0),
            {"differential_potential_limit_v": 0.3},
        )
        self.assertIn("structure-referenced-differential-esd", result["concerns"])


class InternalDepositionTests(unittest.TestCase):
    def test_benign_dielectric_is_concern_free(self):
        result = logic.evaluate_item(dielectric())
        self.assertTrue(result["concern_free"])

    def test_high_field_raises_a_breakdown_concern(self):
        result = logic.evaluate_item(
            dielectric(
                deposited_current_density_a_m2=5.0e-10,
                resistivity_ohm_m=1.0e17,
                dielectric_strength_v_m=6.0e7,
            )
        )
        self.assertIn("buried-charge-breakdown", result["concerns"])
        self.assertEqual(result["severity"], "critical")

    def test_deposition_rate_is_screened_independently_of_the_field(self):
        result = logic.evaluate_item(
            dielectric(
                deposited_current_density_a_m2=5.0e-9,
                resistivity_ohm_m=1.0e12,
                dielectric_strength_v_m=1.0e8,
            )
        )
        self.assertEqual(
            result["concerns"], ("deposition-rate-above-screening-limit",)
        )
        self.assertEqual(result["severity"], "major")

    def test_field_in_the_top_tenth_of_the_band_is_marginal(self):
        result = logic.evaluate_item(
            dielectric(
                deposited_current_density_a_m2=2.9e-10,
                resistivity_ohm_m=1.0e17,
                dielectric_strength_v_m=6.0e7,
            )
        )
        self.assertEqual(result["concerns"], ("marginal-bulk-field",))
        self.assertEqual(result["severity"], "watch")

    def test_field_exactly_at_the_allowable_does_not_break_down(self):
        field = logic.bulk_field(5.0e-10, 1.0e17)
        result = logic.evaluate_item(
            dielectric(
                deposited_current_density_a_m2=5.0e-10,
                resistivity_ohm_m=1.0e17,
                dielectric_strength_v_m=2.0 * field,
            )
        )
        self.assertNotIn("buried-charge-breakdown", result["concerns"])

    def test_allowable_one_unit_in_the_last_place_low_is_absorbed(self):
        field = logic.bulk_field(5.0e-10, 1.0e17)
        allowable = math.nextafter(field, -math.inf)
        self.assertLess(allowable, field)
        result = logic.evaluate_item(
            dielectric(
                deposited_current_density_a_m2=5.0e-10,
                resistivity_ohm_m=1.0e17,
                dielectric_strength_v_m=2.0 * allowable,
            )
        )
        self.assertNotIn("buried-charge-breakdown", result["concerns"])

    def test_thin_shielding_is_flagged(self):
        result = logic.evaluate_item(dielectric(shield_thickness_mm=1.0))
        self.assertIn("shielding-below-guideline", result["concerns"])
        self.assertEqual(result["severity"], "watch")

    def test_shielding_at_the_guideline_passes(self):
        result = logic.evaluate_item(dielectric(shield_thickness_mm=2.0))
        self.assertTrue(result["concern_free"])

    def test_generous_shielding_passes(self):
        result = logic.evaluate_item(dielectric(shield_thickness_mm=5.0))
        self.assertTrue(result["concern_free"])

    def test_breakdown_and_rate_concerns_can_coexist(self):
        result = logic.evaluate_item(
            dielectric(
                deposited_current_density_a_m2=5.0e-9,
                resistivity_ohm_m=1.0e17,
                dielectric_strength_v_m=6.0e7,
            )
        )
        self.assertIn("buried-charge-breakdown", result["concerns"])
        self.assertIn("deposition-rate-above-screening-limit", result["concerns"])


class BondingTests(unittest.TestCase):
    def test_bonded_conductor_is_concern_free(self):
        result = logic.evaluate_item(conductor())
        self.assertTrue(result["concern_free"])

    def test_unbonded_conductor_is_critical(self):
        result = logic.evaluate_item(conductor(bonded=False))
        self.assertEqual(result["concerns"], ("unbonded-floating-conductor",))
        self.assertEqual(result["severity"], "critical")

    def test_high_resistance_bond_is_major(self):
        result = logic.evaluate_item(conductor(bond_resistance_ohm=1.0e7))
        self.assertEqual(result["concerns"], ("high-impedance-bond",))
        self.assertEqual(result["severity"], "major")

    def test_bond_resistance_at_the_limit_passes(self):
        result = logic.evaluate_item(conductor(bond_resistance_ohm=1.0e6))
        self.assertTrue(result["concern_free"])

    def test_low_resistance_bond_passes(self):
        result = logic.evaluate_item(conductor(bond_resistance_ohm=0.01))
        self.assertTrue(result["concern_free"])

    def test_unbonded_conductor_ignores_its_resistance_record(self):
        result = logic.evaluate_item(
            conductor(bonded=False, bond_resistance_ohm=0.01)
        )
        self.assertEqual(result["concerns"], ("unbonded-floating-conductor",))


class SeverityTests(unittest.TestCase):
    def test_every_concern_token_has_a_severity(self):
        for concern in logic.CONCERN_SEVERITY:
            self.assertIn(logic.severity_of(concern), logic.SEVERITY_ORDER)

    def test_unknown_concern_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.severity_of("paint-flake")

    def test_empty_concern_set_is_none(self):
        self.assertEqual(logic.worst_severity(()), "none")

    def test_worst_severity_wins_over_a_lesser_one(self):
        self.assertEqual(
            logic.worst_severity(
                ("marginal-bulk-field", "unbonded-floating-conductor")
            ),
            "critical",
        )

    def test_severity_order_is_ascending(self):
        self.assertEqual(
            logic.SEVERITY_ORDER, ("none", "watch", "major", "critical")
        )


class RollUpTests(unittest.TestCase):
    def test_clean_item_list_rolls_up_clean(self):
        summary = logic.assess_items([surface(), dielectric(), conductor()])
        self.assertTrue(summary["concern_free"])
        self.assertEqual(summary["worst_severity"], "none")
        self.assertEqual(summary["severity_counts"]["none"], 3)

    def test_flagged_items_are_named(self):
        summary = logic.assess_items(
            [
                surface(potential_v=-2000.0, reference_potential_v=0.0),
                dielectric(shield_thickness_mm=0.5),
                conductor(),
            ]
        )
        self.assertFalse(summary["concern_free"])
        self.assertEqual(len(summary["flagged_items"]), 2)
        self.assertEqual(summary["worst_severity"], "critical")

    def test_severity_counts_add_up_to_the_item_count(self):
        summary = logic.assess_items(
            [surface(), conductor(bonded=False), dielectric(shield_thickness_mm=0.5)]
        )
        self.assertEqual(sum(summary["severity_counts"].values()), summary["count"])

    def test_thresholds_flow_through_to_every_item(self):
        summary = logic.assess_items(
            [surface(potential_v=-350.0, reference_potential_v=0.0)],
            {"differential_potential_limit_v": 300.0},
        )
        self.assertFalse(summary["concern_free"])

    def test_empty_item_list_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_items([])

    def test_non_iterable_item_list_is_rejected(self):
        with self.assertRaises(ValueError):
            logic.assess_items(17)

    def test_a_bad_item_aborts_the_roll_up(self):
        with self.assertRaises(ValueError):
            logic.assess_items([surface(), {"name": "mystery", "kind": "unknown"}])


if __name__ == "__main__":
    unittest.main()
