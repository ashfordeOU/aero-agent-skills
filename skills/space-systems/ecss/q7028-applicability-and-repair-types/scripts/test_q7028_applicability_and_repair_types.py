"""Contract tests for the board repair applicability and repair-type triage."""

import unittest

from q7028_applicability_and_repair_types_logic import (
    MAX_DAMAGED_AREA_FRACTION,
    MAX_REPAIRS_PER_BOARD,
    MAX_REPAIRS_PER_CATEGORY,
    assembly_scope,
    modification_category,
    normalize_token,
    repair_budget,
    repair_category,
    triage_item,
)


def base_item(**overrides):
    """A cracked track on a multilayer board with no repair history."""
    item = {
        "assembly_type": "multilayer",
        "damage_type": "conductor-open",
        "damaged_area_fraction": 0.05,
        "prior_repairs_same_category": 0,
        "prior_repairs_total": 1,
    }
    item.update(overrides)
    return item


class TokenTests(unittest.TestCase):
    def test_token_is_lowercased_and_hyphenated(self):
        self.assertEqual(normalize_token(" Land_Lifted ", "t"), "land-lifted")

    def test_blank_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token("   ", "t")

    def test_non_string_token_rejected(self):
        with self.assertRaises(ValueError):
            normalize_token(7, "t")


class ScopeTests(unittest.TestCase):
    def test_multilayer_board_is_in_scope(self):
        self.assertTrue(assembly_scope("multilayer")["in_scope"])

    def test_rigid_flex_is_in_scope(self):
        self.assertTrue(assembly_scope("rigid-flex")["in_scope"])

    def test_harness_is_out_of_scope_and_names_its_owner(self):
        verdict = assembly_scope("wire-harness")
        self.assertFalse(verdict["in_scope"])
        self.assertIn("harness", verdict["belongs_to"])

    def test_unknown_assembly_rejected_rather_than_assumed(self):
        with self.assertRaises(ValueError):
            assembly_scope("ceramic-substrate")


class DamageCategoryTests(unittest.TestCase):
    def test_open_track_maps_to_conductor_repair(self):
        self.assertEqual(repair_category("conductor-open")["category"], "conductor-repair")

    def test_lifted_land_maps_to_land_repair(self):
        self.assertEqual(repair_category("land-lifted")["category"], "land-repair")

    def test_cracked_barrel_maps_to_plated_hole_repair(self):
        self.assertEqual(repair_category("barrel-cracked")["category"], "plated-hole-repair")

    def test_carbonised_laminate_has_no_repair_category(self):
        verdict = repair_category("carbonised-laminate")
        self.assertFalse(verdict["repairable"])
        self.assertIsNone(verdict["category"])

    def test_buried_layer_open_is_not_repairable(self):
        self.assertFalse(repair_category("internal-layer-open")["repairable"])

    def test_unknown_damage_rejected(self):
        with self.assertRaises(ValueError):
            repair_category("something-odd")


class ModificationTests(unittest.TestCase):
    def test_added_jumper_is_a_wiring_modification(self):
        verdict = modification_category("jumper-wire-added")
        self.assertEqual(verdict["category"], "wiring-modification")
        self.assertTrue(verdict["drawing_update_required"])

    def test_value_change_is_a_component_modification(self):
        self.assertEqual(
            modification_category("component-value-change")["category"],
            "component-modification",
        )

    def test_marking_correction_needs_no_drawing_update(self):
        self.assertFalse(modification_category("marking-corrected")["drawing_update_required"])

    def test_as_built_tracks_the_drawing_update(self):
        verdict = modification_category("track-cut")
        self.assertEqual(
            verdict["as_built_update_required"], verdict["drawing_update_required"]
        )

    def test_unknown_change_rejected(self):
        with self.assertRaises(ValueError):
            modification_category("repaint-the-box")


class BudgetTests(unittest.TestCase):
    def test_fresh_board_has_the_whole_budget(self):
        budget = repair_budget(0, 0)
        self.assertEqual(budget["category_remaining"], MAX_REPAIRS_PER_CATEGORY)
        self.assertEqual(budget["board_remaining"], MAX_REPAIRS_PER_BOARD)

    def test_category_limit_is_reported_exhausted_on_the_bound(self):
        budget = repair_budget(MAX_REPAIRS_PER_CATEGORY, MAX_REPAIRS_PER_CATEGORY)
        self.assertTrue(budget["category_exhausted"])
        self.assertEqual(budget["category_remaining"], 0)

    def test_board_limit_is_reported_exhausted_on_the_bound(self):
        budget = repair_budget(1, MAX_REPAIRS_PER_BOARD)
        self.assertTrue(budget["board_exhausted"])

    def test_category_count_above_the_total_rejected(self):
        with self.assertRaises(ValueError):
            repair_budget(4, 2)

    def test_negative_history_rejected(self):
        with self.assertRaises(ValueError):
            repair_budget(0, -1)

    def test_non_integer_history_rejected(self):
        with self.assertRaises(ValueError):
            repair_budget(0, 2.5)


class TriageTests(unittest.TestCase):
    def test_nominal_track_damage_is_dispositioned_to_repair(self):
        verdict = triage_item(base_item())
        self.assertEqual(verdict["disposition"], "repair")
        self.assertTrue(verdict["ready"])

    def test_out_of_scope_assembly_short_circuits_the_disposition(self):
        verdict = triage_item(base_item(assembly_type="hybrid-microcircuit"))
        self.assertEqual(verdict["disposition"], "out-of-scope")

    def test_irreparable_damage_goes_to_nonconformance_review(self):
        verdict = triage_item(base_item(damage_type="burn-through"))
        self.assertEqual(verdict["disposition"], "nonconformance-review")
        self.assertFalse(verdict["damage_repairable"])

    def test_area_fraction_exactly_on_the_bound_is_still_repairable(self):
        verdict = triage_item(base_item(damaged_area_fraction=MAX_DAMAGED_AREA_FRACTION))
        self.assertEqual(verdict["disposition"], "repair")

    def test_area_fraction_over_the_bound_is_flagged(self):
        verdict = triage_item(base_item(damaged_area_fraction=0.45))
        self.assertTrue(any("damaged area fraction" in f for f in verdict["findings"]))

    def test_exhausted_category_budget_blocks_the_repair(self):
        verdict = triage_item(
            base_item(
                prior_repairs_same_category=MAX_REPAIRS_PER_CATEGORY,
                prior_repairs_total=MAX_REPAIRS_PER_CATEGORY,
            )
        )
        self.assertEqual(verdict["disposition"], "nonconformance-review")

    def test_modification_is_reported_alongside_the_repair(self):
        verdict = triage_item(base_item(change_type="jumper-wire-added"))
        self.assertIsNotNone(verdict["modification"])
        self.assertTrue(any("as-built update" in f for f in verdict["findings"]))

    def test_finish_modification_does_not_block_the_repair(self):
        verdict = triage_item(base_item(change_type="marking-corrected"))
        self.assertEqual(verdict["disposition"], "repair")

    def test_fraction_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            triage_item(base_item(damaged_area_fraction=1.4))

    def test_missing_damage_key_rejected(self):
        item = base_item()
        del item["damage_type"]
        with self.assertRaises(ValueError):
            triage_item(item)

    def test_non_mapping_item_rejected(self):
        with self.assertRaises(ValueError):
            triage_item("multilayer")


if __name__ == "__main__":
    unittest.main()
