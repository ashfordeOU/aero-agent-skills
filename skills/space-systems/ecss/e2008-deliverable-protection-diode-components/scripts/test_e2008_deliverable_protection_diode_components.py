#!/usr/bin/env python3
"""Contract test for PVA deliverable protection diode items (offline).

Walks the clause workflow step by step: the mounting that decides which
delivery line a protection diode belongs on, the two ways an item can be
misfiled between those lines, the protection the string architecture
requires against the diodes actually fitted, the fitted count against
the count the paperwork declares, the bracket those three figures leave
on what the string really delivers, the per-string disposition and the
diode-weighted roll-up into one assembly verdict. This is the gate 3
review evidence for the leaf.
"""

import copy
import unittest

from e2008_deliverable_protection_diode_components_logic import (
    STRING_CONCESSION,
    STRING_DELIVERABLE,
    STRING_WITHHELD,
    assess_assembly_deliverables,
    assess_string_deliverables,
    categorize_diode_mounting,
    deliverable_diode_bracket,
    item_line_placement,
    reconcile_diode_inventory,
    required_protection_diodes,
)

SOUND_STRING = {
    "string_id": "STR-01",
    "sections": 4,
    "fitted_bypass": 4,
    "fitted_blocking": 1,
    "declared_diodes": 5,
    "mounting": "integral-on-panel",
    "listed_on": "assembly-item-list",
}


def _string(string_id, **overrides):
    record = copy.deepcopy(SOUND_STRING)
    record["string_id"] = string_id
    record.update(overrides)
    return record


class MountingCategoryTests(unittest.TestCase):
    def test_a_diode_bonded_to_the_cell_ships_with_the_assembly(self):
        result = categorize_diode_mounting("integral-on-cell")
        self.assertTrue(result["integral"])
        self.assertEqual(result["expected_item_line"], "assembly-item-list")

    def test_a_diode_on_the_substrate_ships_with_the_assembly(self):
        self.assertTrue(categorize_diode_mounting("integral-on-panel")["integral"])

    def test_a_diode_in_the_spacecraft_wiring_is_a_separate_deliverable(self):
        result = categorize_diode_mounting("external-on-bus")
        self.assertFalse(result["integral"])
        self.assertEqual(result["expected_item_line"], "separate-item-list")

    def test_unknown_mounting_rejected(self):
        with self.assertRaises(ValueError):
            categorize_diode_mounting("somewhere-on-the-wing")


class ItemLinePlacementTests(unittest.TestCase):
    def test_integral_diode_on_the_assembly_line_is_placed_correctly(self):
        result = item_line_placement("integral-on-panel", "assembly-item-list")
        self.assertTrue(result["correctly_placed"])
        self.assertEqual(result["findings"], [])

    def test_external_diode_on_its_own_line_is_placed_correctly(self):
        result = item_line_placement("external-on-bus", "separate-item-list")
        self.assertTrue(result["correctly_placed"])

    def test_integral_diode_booked_as_a_separate_item_is_misfiled(self):
        result = item_line_placement("integral-on-cell", "separate-item-list")
        self.assertFalse(result["correctly_placed"])
        self.assertTrue(result["findings"])

    def test_external_diode_on_the_assembly_line_is_misfiled(self):
        result = item_line_placement("external-on-bus", "assembly-item-list")
        self.assertFalse(result["correctly_placed"])

    def test_a_diode_no_line_carries_is_reported(self):
        result = item_line_placement("integral-on-panel", "not-listed")
        self.assertFalse(result["correctly_placed"])

    def test_unknown_item_line_rejected(self):
        with self.assertRaises(ValueError):
            item_line_placement("integral-on-panel", "the-packing-note")


class RequirementTests(unittest.TestCase):
    def test_required_total_is_bypass_per_section_plus_blocking(self):
        result = required_protection_diodes(4)
        self.assertEqual(result["required_bypass"], 4)
        self.assertEqual(result["required_blocking"], 1)
        self.assertEqual(result["required_total"], 5)

    def test_policy_can_call_for_two_bypass_diodes_a_section(self):
        result = required_protection_diodes(3, {"bypass_diodes_per_section": 2})
        self.assertEqual(result["required_total"], 7)

    def test_a_policy_asking_for_no_protection_is_rejected(self):
        with self.assertRaises(ValueError):
            required_protection_diodes(
                4, {"bypass_diodes_per_section": 0, "blocking_diodes_per_string": 0}
            )

    def test_zero_sections_rejected(self):
        with self.assertRaises(ValueError):
            required_protection_diodes(0)

    def test_fractional_section_count_rejected(self):
        with self.assertRaises(ValueError):
            required_protection_diodes(2.5)


class InventoryTests(unittest.TestCase):
    def test_matching_counts_reconcile(self):
        result = reconcile_diode_inventory(5, 5)
        self.assertTrue(result["reconciled"])
        self.assertEqual(result["unlisted"], 0)
        self.assertEqual(result["phantom"], 0)

    def test_hardware_ahead_of_the_paperwork_leaves_unlisted_items(self):
        result = reconcile_diode_inventory(6, 5)
        self.assertEqual(result["unlisted"], 1)
        self.assertEqual(result["accounted"], 5)

    def test_paperwork_ahead_of_the_hardware_leaves_phantom_items(self):
        result = reconcile_diode_inventory(4, 5)
        self.assertEqual(result["phantom"], 1)

    def test_negative_declared_count_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_diode_inventory(5, -1)

    def test_boolean_count_rejected(self):
        with self.assertRaises(ValueError):
            reconcile_diode_inventory(True, 1)


class BracketTests(unittest.TestCase):
    def test_a_sound_string_brackets_to_a_single_number(self):
        result = deliverable_diode_bracket(5, 5, 5)
        self.assertEqual(result["at_most"], 5)
        self.assertEqual(result["at_least"], 5)
        self.assertEqual(result["bracket_width"], 0)

    def test_a_protection_shortfall_pushes_the_lower_bound_down(self):
        result = deliverable_diode_bracket(5, 3, 3)
        self.assertEqual(result["protection_shortfall"], 2)
        self.assertEqual(result["at_least"], 1)

    def test_the_lower_bound_never_goes_below_zero(self):
        result = deliverable_diode_bracket(5, 0, 0)
        self.assertEqual(result["at_least"], 0)

    def test_zero_requirement_rejected(self):
        with self.assertRaises(ValueError):
            deliverable_diode_bracket(0, 1, 1)


class StringDispositionTests(unittest.TestCase):
    def test_sound_string_is_deliverable(self):
        result = assess_string_deliverables(_string("STR-01"))
        self.assertEqual(result["disposition"], STRING_DELIVERABLE)
        self.assertTrue(result["fully_protected"])
        self.assertEqual(result["findings"], [])

    def test_a_missing_bypass_diode_withholds_the_string(self):
        result = assess_string_deliverables(_string("STR-02", fitted_bypass=3,
                                                    declared_diodes=4))
        self.assertEqual(result["disposition"], STRING_WITHHELD)
        self.assertFalse(result["fully_protected"])

    def test_a_missing_blocking_diode_withholds_the_string(self):
        result = assess_string_deliverables(_string("STR-03", fitted_blocking=0,
                                                    declared_diodes=4))
        self.assertEqual(result["disposition"], STRING_WITHHELD)

    def test_an_undeclared_fitted_diode_releases_under_concession(self):
        result = assess_string_deliverables(_string("STR-04", declared_diodes=4))
        self.assertEqual(result["disposition"], STRING_CONCESSION)
        self.assertEqual(result["inventory"]["unlisted"], 1)

    def test_a_phantom_item_withholds_the_string(self):
        result = assess_string_deliverables(_string("STR-05", declared_diodes=7))
        self.assertEqual(result["disposition"], STRING_WITHHELD)

    def test_a_misfiled_item_line_withholds_the_string(self):
        result = assess_string_deliverables(
            _string("STR-06", listed_on="separate-item-list")
        )
        self.assertEqual(result["disposition"], STRING_WITHHELD)

    def test_non_mapping_string_rejected(self):
        with self.assertRaises(ValueError):
            assess_string_deliverables("all diodes were fitted")


class AssemblyRollUpTests(unittest.TestCase):
    def _case(self, strings, policy=None):
        case = {"assembly_id": "PVA-9", "strings": strings}
        if policy is not None:
            case["policy"] = policy
        return case

    def test_a_sound_assembly_releases_every_required_diode(self):
        result = assess_assembly_deliverables(
            self._case([_string("STR-01"), _string("STR-02")])
        )
        self.assertEqual(result["disposition"], STRING_DELIVERABLE)
        self.assertEqual(result["released_diodes"], 10)
        self.assertAlmostEqual(result["release_share"], 1.0, places=9)
        self.assertTrue(result["meets_release_floor"])

    def test_release_is_weighted_by_diodes_not_by_strings(self):
        big = _string("STR-BIG", sections=20, fitted_bypass=20,
                      declared_diodes=21)
        small = _string("STR-SMALL", sections=1, fitted_bypass=0,
                        fitted_blocking=0, declared_diodes=0)
        result = assess_assembly_deliverables(self._case([big, small]))
        self.assertEqual(result["required_diodes"], 23)
        self.assertEqual(result["released_diodes"], 21)
        self.assertAlmostEqual(result["release_share"], 21.0 / 23.0, places=9)

    def test_one_withheld_string_pulls_the_assembly_disposition_down(self):
        result = assess_assembly_deliverables(
            self._case(
                [_string("STR-01"), _string("STR-02", fitted_blocking=0,
                                             declared_diodes=4)]
            )
        )
        self.assertEqual(result["disposition"], STRING_WITHHELD)
        self.assertEqual(result["withheld_strings"], ["STR-02"])
        self.assertEqual(result["weakest_string"], "STR-02")

    def test_a_concession_string_is_named_separately(self):
        result = assess_assembly_deliverables(
            self._case([_string("STR-01"), _string("STR-02", declared_diodes=4)])
        )
        self.assertEqual(result["disposition"], STRING_CONCESSION)
        self.assertEqual(result["concession_strings"], ["STR-02"])

    def test_a_release_floor_exactly_met_is_accepted(self):
        result = assess_assembly_deliverables(
            self._case([_string("STR-01")], {"min_release_share": 1.0})
        )
        self.assertTrue(result["meets_release_floor"])
        self.assertAlmostEqual(result["release_share"], 1.0, places=9)

    def test_a_repeated_string_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_assembly_deliverables(
                self._case([_string("STR-01"), _string("STR-01")])
            )

    def test_empty_assembly_rejected(self):
        with self.assertRaises(ValueError):
            assess_assembly_deliverables(self._case([]))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_assembly_deliverables("every diode was on the item list")


if __name__ == "__main__":
    unittest.main()
