"""Contract tests for the support structure design and removal logic."""

import copy
import unittest

from q7080_support_structure_removal_logic import (
    INTERFACE_BOND_FRACTION,
    allowable_load_n,
    assess_support_removal,
    damage_ratio,
    effective_bond_area_mm2,
    evaluate_region,
    removal_force_n,
    select_removal_method,
    validate_region,
    witness_finding,
)


def region(identifier="s1", interface="toothed", access="open",
           surface_class="non-critical", contact=20.0, section=100.0,
           witness=0.0, allowance=0.0):
    return {
        "id": identifier,
        "interface": interface,
        "access": access,
        "surface_class": surface_class,
        "contact_area_mm2": contact,
        "section_area_mm2": section,
        "witness_height_mm": witness,
        "machining_allowance_mm": allowance,
    }


def regions():
    return [
        region(),
        region("s2", interface="perforated", access="recessed",
               surface_class="machined-later", contact=40.0, witness=0.3, allowance=0.5),
    ]


def spec(items=None, **extra):
    base = {
        "regions": copy.deepcopy(regions() if items is None else items),
        "interface_strength_mpa": 250.0,
        "allowable_stress_mpa": 300.0,
        "safety_factor": 1.5,
        "manual_force_limit_n": 1500.0,
    }
    base.update(extra)
    return base


class RegionValidationTests(unittest.TestCase):
    def test_region_normalised(self):
        record = validate_region(region())
        self.assertEqual(record["interface"], "toothed")
        self.assertAlmostEqual(record["contact_area_mm2"], 20.0, places=9)

    def test_unknown_interface_rejected(self):
        with self.assertRaises(ValueError):
            validate_region(region(interface="glued"))

    def test_unknown_access_rejected(self):
        with self.assertRaises(ValueError):
            validate_region(region(access="somewhere"))

    def test_unknown_surface_class_rejected(self):
        with self.assertRaises(ValueError):
            validate_region(region(surface_class="shiny"))

    def test_missing_contact_area_rejected(self):
        broken = region()
        del broken["contact_area_mm2"]
        with self.assertRaises(ValueError):
            validate_region(broken)

    def test_zero_section_area_rejected(self):
        with self.assertRaises(ValueError):
            validate_region(region(section=0.0))

    def test_negative_witness_rejected(self):
        with self.assertRaises(ValueError):
            validate_region(region(witness=-0.1))

    def test_blank_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_region(region(identifier="  "))


class BondAreaTests(unittest.TestCase):
    def test_solid_interface_fuses_its_whole_footprint(self):
        self.assertAlmostEqual(effective_bond_area_mm2(20.0, "solid"), 20.0, places=9)

    def test_perforated_interface_fuses_half(self):
        self.assertAlmostEqual(effective_bond_area_mm2(20.0, "perforated"), 10.0, places=9)

    def test_toothed_interface_fuses_a_quarter(self):
        self.assertAlmostEqual(effective_bond_area_mm2(20.0, "toothed"), 5.0, places=9)

    def test_bond_fractions_are_ordered(self):
        self.assertAlmostEqual(
            INTERFACE_BOND_FRACTION["toothed"] * 2.0,
            INTERFACE_BOND_FRACTION["perforated"],
            places=9,
        )

    def test_unknown_interface_rejected(self):
        with self.assertRaises(ValueError):
            effective_bond_area_mm2(20.0, "welded")

    def test_zero_contact_area_rejected(self):
        with self.assertRaises(ValueError):
            effective_bond_area_mm2(0.0, "solid")


class ForceTests(unittest.TestCase):
    def test_removal_force_closed_form(self):
        self.assertAlmostEqual(removal_force_n(5.0, 250.0), 1250.0, places=9)

    def test_zero_strength_rejected(self):
        with self.assertRaises(ValueError):
            removal_force_n(5.0, 0.0)

    def test_allowable_load_closed_form(self):
        self.assertAlmostEqual(allowable_load_n(100.0, 300.0, 1.5), 20000.0, places=9)

    def test_safety_factor_below_one_rejected(self):
        with self.assertRaises(ValueError):
            allowable_load_n(100.0, 300.0, 0.8)

    def test_damage_ratio_closed_form(self):
        self.assertAlmostEqual(damage_ratio(1250.0, 20000.0), 0.0625, places=9)

    def test_zero_allowable_rejected(self):
        with self.assertRaises(ValueError):
            damage_ratio(1250.0, 0.0)


class MethodTests(unittest.TestCase):
    def test_open_access_and_low_force_breaks_off(self):
        self.assertEqual(
            select_removal_method(validate_region(region()), 1250.0, 1500.0),
            "manual-break-off",
        )

    def test_force_exactly_at_the_manual_limit_still_breaks_off(self):
        self.assertEqual(
            select_removal_method(validate_region(region()), 1500.0, 1500.0),
            "manual-break-off",
        )

    def test_open_access_and_high_force_is_machined(self):
        self.assertEqual(
            select_removal_method(validate_region(region()), 5000.0, 1500.0), "machining"
        )

    def test_recessed_access_and_low_force_is_machined(self):
        record = validate_region(region(access="recessed", surface_class="machined-later"))
        self.assertEqual(select_removal_method(record, 1250.0, 1500.0), "machining")

    def test_recessed_access_and_high_force_needs_wire_cutting(self):
        record = validate_region(region(access="recessed", surface_class="machined-later"))
        self.assertEqual(select_removal_method(record, 5000.0, 1500.0), "wire-edm")

    def test_closed_volume_cannot_be_reached(self):
        record = validate_region(region(access="internal-closed"))
        self.assertEqual(
            select_removal_method(record, 100.0, 1500.0), "not-removable-redesign"
        )

    def test_functional_surface_cannot_be_restored(self):
        record = validate_region(region(surface_class="critical-functional"))
        self.assertEqual(
            select_removal_method(record, 100.0, 1500.0), "not-removable-redesign"
        )

    def test_zero_manual_limit_rejected(self):
        with self.assertRaises(ValueError):
            select_removal_method(validate_region(region()), 1250.0, 0.0)


class WitnessTests(unittest.TestCase):
    def test_non_critical_surface_carries_no_witness_finding(self):
        self.assertIsNone(witness_finding(validate_region(region(witness=1.0))))

    def test_witness_inside_the_allowance_passes(self):
        record = validate_region(
            region(surface_class="machined-later", witness=0.3, allowance=0.5)
        )
        self.assertIsNone(witness_finding(record))

    def test_witness_exactly_at_the_allowance_passes(self):
        record = validate_region(
            region(surface_class="machined-later", witness=0.5, allowance=0.5)
        )
        self.assertIsNone(witness_finding(record))

    def test_witness_above_the_allowance_is_a_finding(self):
        record = validate_region(
            region(surface_class="machined-later", witness=0.8, allowance=0.5)
        )
        self.assertIn("witness", witness_finding(record))


class RegionEvaluationTests(unittest.TestCase):
    def test_record_carries_force_and_method(self):
        record = evaluate_region(region(), spec())
        self.assertAlmostEqual(record["removal_force_n"], 1250.0, places=9)
        self.assertEqual(record["method"], "manual-break-off")

    def test_thin_section_escalates_the_break_off_to_cutting(self):
        record = evaluate_region(region(section=2.0), spec())
        self.assertEqual(record["method"], "machining")
        self.assertTrue(record["escalated_from_break_off"])
        self.assertAlmostEqual(record["damage_ratio"], 1250.0 / 400.0, places=9)

    def test_ratio_exactly_one_is_not_escalated(self):
        record = evaluate_region(region(section=6.25), spec())
        self.assertAlmostEqual(record["damage_ratio"], 1.0, places=9)
        self.assertEqual(record["method"], "manual-break-off")
        self.assertFalse(record["escalated_from_break_off"])

    def test_wire_cutting_region_is_not_escalated(self):
        record = evaluate_region(regions()[1], spec())
        self.assertEqual(record["method"], "wire-edm")
        self.assertFalse(record["escalated_from_break_off"])


class AssessmentTests(unittest.TestCase):
    def test_clean_part_is_removable(self):
        result = assess_support_removal(spec())
        self.assertEqual(result["verdict"], "removable")
        self.assertEqual(result["blocking"], [])

    def test_methods_are_reported_per_region(self):
        result = assess_support_removal(spec())
        self.assertEqual(result["methods"], {"s1": "manual-break-off", "s2": "wire-edm"})

    def test_internal_support_forces_a_redesign(self):
        items = regions() + [region("s3", access="internal-closed")]
        result = assess_support_removal(spec(items=items))
        self.assertEqual(result["verdict"], "redesign-required")
        self.assertTrue(any("closed volume" in b for b in result["blocking"]))

    def test_support_on_a_functional_surface_forces_a_redesign(self):
        items = regions() + [region("s3", surface_class="critical-functional")]
        result = assess_support_removal(spec(items=items))
        self.assertEqual(result["verdict"], "redesign-required")
        self.assertTrue(any("functional surface" in b for b in result["blocking"]))

    def test_witness_beyond_the_allowance_forces_a_redesign(self):
        items = [region("s1", surface_class="machined-later", witness=0.9, allowance=0.4)]
        result = assess_support_removal(spec(items=items))
        self.assertEqual(result["verdict"], "redesign-required")

    def test_escalated_break_off_is_a_finding_not_a_block(self):
        items = [region("s1", section=2.0)]
        result = assess_support_removal(spec(items=items))
        self.assertEqual(result["verdict"], "removable-with-findings")
        self.assertTrue(any("cut instead" in f for f in result["findings"]))

    def test_duplicate_region_id_rejected(self):
        items = regions() + [region("s1")]
        with self.assertRaises(ValueError):
            assess_support_removal(spec(items=items))

    def test_empty_region_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_support_removal(spec(items=[]))

    def test_missing_spec_key_rejected(self):
        broken = spec()
        del broken["manual_force_limit_n"]
        with self.assertRaises(ValueError):
            assess_support_removal(broken)

    def test_every_region_is_recorded(self):
        result = assess_support_removal(spec())
        self.assertEqual([record["id"] for record in result["records"]], ["s1", "s2"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
