#!/usr/bin/env python3
"""Contract test for GSE, test equipment and launch-site items (offline)."""

import copy
import unittest

from e3311_gse_test_equipment_launch_site_items_logic import (
    DEFAULT_EXTERNAL_ITEM_POLICY,
    ITEM_ACCEPTABLE,
    ITEM_INCOMPLETE,
    ITEM_KINDS,
    ITEM_REWORK,
    REQ_BONDING,
    REQ_ESD,
    REQ_HANDLING_SHOCK,
    REQ_LIGHTNING,
    REQ_RF,
    REQ_SAFING,
    REQ_SEPARATION,
    REQ_STRAY_ENERGY,
    REQ_TEST_CURRENT,
    applicable_requirements,
    assess_bond_resistance,
    assess_external_item,
    assess_personnel_separation,
    assess_test_instrument,
    max_test_current_a,
    screen_inventory,
    validate_external_item_policy,
)

FIRING_GSE = {
    "id": "gse-1",
    "item_kind": "firing-circuit-gse",
    "contacts_explosive_item": True,
    "energizes_explosive_item": True,
    "bond_resistance_ohm": 0.004,
}

TEST_METER = {
    "id": "te-1",
    "item_kind": "test-equipment",
    "contacts_explosive_item": True,
    "energizes_explosive_item": True,
    "fault_current_a": 0.02,
    "no_fire_current_a": 1.0,
    "bond_resistance_ohm": 0.002,
}

PAD_ITEM = {
    "id": "pad-1",
    "item_kind": "launch-site-item",
    "contacts_explosive_item": False,
    "energizes_explosive_item": False,
    "at_launch_site": True,
    "bond_resistance_ohm": 0.008,
    "personnel_separation_m": 25.0,
}

TROLLEY = {
    "id": "gse-2",
    "item_kind": "handling-transport-gse",
    "contacts_explosive_item": True,
    "energizes_explosive_item": False,
    "bond_resistance_ohm": 0.006,
}


def _item(base, **overrides):
    item = copy.deepcopy(base)
    item.update(overrides)
    return item


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_external_item_policy(DEFAULT_EXTERNAL_ITEM_POLICY),
            DEFAULT_EXTERNAL_ITEM_POLICY,
        )

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_external_item_policy("default")

    def test_a_cap_at_the_no_fire_current_is_rejected(self):
        broken = copy.deepcopy(DEFAULT_EXTERNAL_ITEM_POLICY)
        broken["test_current_fraction_of_no_fire"] = 1.0
        with self.assertRaises(ValueError):
            validate_external_item_policy(broken)

    def test_a_negative_bond_limit_is_rejected(self):
        broken = copy.deepcopy(DEFAULT_EXTERNAL_ITEM_POLICY)
        broken["max_bond_resistance_ohm"] = -0.01
        with self.assertRaises(ValueError):
            validate_external_item_policy(broken)


class ApplicabilityTests(unittest.TestCase):
    def test_bonding_binds_every_item_kind(self):
        for kind in ITEM_KINDS:
            allocation = applicable_requirements(kind, False, False, False)
            self.assertIn(REQ_BONDING, allocation["requirements"])

    def test_contact_adds_discharge_control(self):
        allocation = applicable_requirements(
            "handling-transport-gse", True, False, False
        )
        self.assertIn(REQ_ESD, allocation["requirements"])

    def test_an_energizing_item_owes_stray_energy_and_safing(self):
        allocation = applicable_requirements("test-equipment", True, True, False)
        self.assertIn(REQ_STRAY_ENERGY, allocation["requirements"])
        self.assertIn(REQ_SAFING, allocation["requirements"])

    def test_firing_circuit_gse_owes_safing_even_without_the_flag(self):
        allocation = applicable_requirements(
            "firing-circuit-gse", False, False, False
        )
        self.assertIn(REQ_SAFING, allocation["requirements"])

    def test_only_energizing_test_equipment_owes_the_current_cap(self):
        with_energy = applicable_requirements("test-equipment", True, True, False)
        without = applicable_requirements("test-equipment", True, False, False)
        self.assertIn(REQ_TEST_CURRENT, with_energy["requirements"])
        self.assertNotIn(REQ_TEST_CURRENT, without["requirements"])

    def test_a_handling_item_owes_shock_control(self):
        allocation = applicable_requirements(
            "handling-transport-gse", True, False, False
        )
        self.assertIn(REQ_HANDLING_SHOCK, allocation["requirements"])

    def test_the_pad_adds_requirements_rather_than_relaxing_them(self):
        indoors = applicable_requirements("firing-circuit-gse", True, True, False)
        at_pad = applicable_requirements("firing-circuit-gse", True, True, True)
        self.assertLess(len(indoors["requirements"]), len(at_pad["requirements"]))
        for requirement in (REQ_LIGHTNING, REQ_RF, REQ_SEPARATION):
            self.assertIn(requirement, at_pad["requirements"])

    def test_every_allocated_requirement_carries_a_reason(self):
        allocation = applicable_requirements("test-equipment", True, True, True)
        for requirement in allocation["requirements"]:
            self.assertTrue(allocation["rationale"][requirement])

    def test_energizing_without_contacting_is_rejected(self):
        with self.assertRaises(ValueError):
            applicable_requirements("test-equipment", False, True, False)

    def test_an_unknown_item_kind_is_rejected(self):
        with self.assertRaises(ValueError):
            applicable_requirements("coffee-machine", False, False, False)

    def test_a_non_boolean_flag_is_rejected(self):
        with self.assertRaises(ValueError):
            applicable_requirements("test-equipment", "yes", False, False)


class LimitTests(unittest.TestCase):
    def test_the_instrument_cap_is_a_fraction_of_the_no_fire_current(self):
        self.assertAlmostEqual(max_test_current_a(1.0), 0.10, places=12)

    def test_the_cap_sits_below_the_no_fire_current(self):
        self.assertLess(max_test_current_a(0.75), 0.75)

    def test_a_fault_current_inside_the_cap_passes(self):
        self.assertTrue(assess_test_instrument(0.02, 1.0)["within_limit"])

    def test_a_fault_current_exactly_on_the_cap_passes(self):
        result = assess_test_instrument(max_test_current_a(0.75), 0.75)
        self.assertAlmostEqual(result["fault_current_a"], result["limit_a"], places=12)
        self.assertTrue(result["within_limit"])

    def test_a_fault_current_graded_against_the_no_fire_value_would_have_passed(self):
        result = assess_test_instrument(0.5, 1.0)
        self.assertFalse(result["within_limit"])
        self.assertLess(result["fault_current_a"], result["no_fire_current_a"])

    def test_a_negative_fault_current_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_test_instrument(-0.02, 1.0)

    def test_a_bond_inside_the_limit_passes(self):
        self.assertTrue(assess_bond_resistance(0.004)["within_limit"])

    def test_a_bond_exactly_on_the_limit_passes(self):
        limit = DEFAULT_EXTERNAL_ITEM_POLICY["max_bond_resistance_ohm"]
        result = assess_bond_resistance(limit)
        self.assertAlmostEqual(result["resistance_ohm"], result["limit_ohm"], places=15)
        self.assertTrue(result["within_limit"])

    def test_a_bond_above_the_limit_fails(self):
        self.assertFalse(assess_bond_resistance(0.05)["within_limit"])

    def test_a_non_numeric_bond_reading_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bond_resistance("4 milliohm")

    def test_separation_exactly_on_the_minimum_passes(self):
        minimum = DEFAULT_EXTERNAL_ITEM_POLICY["min_personnel_separation_m"]
        result = assess_personnel_separation(minimum)
        self.assertAlmostEqual(result["separation_m"], result["minimum_m"], places=15)
        self.assertTrue(result["within_limit"])

    def test_separation_below_the_minimum_fails(self):
        self.assertFalse(assess_personnel_separation(5.0)["within_limit"])


class ItemTests(unittest.TestCase):
    def test_a_compliant_firing_gse_item_is_acceptable(self):
        result = assess_external_item(FIRING_GSE)
        self.assertEqual(result["verdict"], ITEM_ACCEPTABLE)
        self.assertEqual(result["findings"], [])

    def test_a_meter_over_its_cap_is_rework(self):
        result = assess_external_item(_item(TEST_METER, fault_current_a=0.5))
        self.assertEqual(result["verdict"], ITEM_REWORK)
        self.assertEqual(result["failure_count"], 1)

    def test_an_item_with_no_bond_reading_is_not_fully_graded(self):
        item = _item(FIRING_GSE)
        del item["bond_resistance_ohm"]
        result = assess_external_item(item)
        self.assertEqual(result["verdict"], ITEM_INCOMPLETE)
        self.assertIn(REQ_BONDING, result["ungraded"])

    def test_a_pad_item_without_a_separation_is_not_fully_graded(self):
        item = _item(PAD_ITEM)
        del item["personnel_separation_m"]
        result = assess_external_item(item)
        self.assertEqual(result["verdict"], ITEM_INCOMPLETE)
        self.assertIn(REQ_SEPARATION, result["ungraded"])

    def test_a_trolley_owes_shock_control_without_energizing_anything(self):
        result = assess_external_item(TROLLEY)
        self.assertIn(REQ_HANDLING_SHOCK, result["requirements"])
        self.assertNotIn(REQ_STRAY_ENERGY, result["requirements"])
        self.assertEqual(result["verdict"], ITEM_ACCEPTABLE)

    def test_an_item_without_an_id_is_rejected(self):
        item = _item(FIRING_GSE)
        del item["id"]
        with self.assertRaises(ValueError):
            assess_external_item(item)

    def test_a_non_mapping_item_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_external_item("a firing box")


class InventoryTests(unittest.TestCase):
    def test_a_clean_inventory_is_acceptable(self):
        result = screen_inventory([FIRING_GSE, TEST_METER, PAD_ITEM, TROLLEY])
        self.assertEqual(result["verdict"], "inventory-acceptable")
        self.assertEqual(result["item_count"], 4)
        self.assertEqual(result["counts"][ITEM_ACCEPTABLE], 4)

    def test_every_item_is_counted_against_bonding(self):
        result = screen_inventory([FIRING_GSE, TEST_METER, PAD_ITEM, TROLLEY])
        self.assertEqual(result["requirement_counts"][REQ_BONDING], 4)

    def test_one_failing_item_marks_the_inventory(self):
        result = screen_inventory(
            [FIRING_GSE, _item(TEST_METER, fault_current_a=0.5)]
        )
        self.assertEqual(result["verdict"], "inventory-rework")
        self.assertEqual(result["counts"][ITEM_REWORK], 1)

    def test_an_ungraded_item_does_not_read_as_a_pass(self):
        item = _item(TROLLEY, id="gse-3")
        del item["bond_resistance_ohm"]
        result = screen_inventory([FIRING_GSE, item])
        self.assertEqual(result["counts"][ITEM_INCOMPLETE], 1)
        self.assertFalse(result["clean"])

    def test_a_duplicate_item_id_is_rejected(self):
        with self.assertRaises(ValueError):
            screen_inventory([FIRING_GSE, _item(FIRING_GSE)])

    def test_an_empty_inventory_is_rejected(self):
        with self.assertRaises(ValueError):
            screen_inventory([])

    def test_a_tighter_policy_can_fail_a_passing_inventory(self):
        policy = copy.deepcopy(DEFAULT_EXTERNAL_ITEM_POLICY)
        policy["max_bond_resistance_ohm"] = 0.003
        result = screen_inventory([FIRING_GSE, TEST_METER], policy)
        self.assertEqual(result["verdict"], "inventory-rework")


if __name__ == "__main__":
    unittest.main()
