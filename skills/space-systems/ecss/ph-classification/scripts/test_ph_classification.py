"""
test_ph_classification.py

Offline unit tests for ph_classification_logic.
Run: python3 test_ph_classification.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from ph_classification_logic import (
    HardwareItem,
    CategoryError,
    CategoryResult,
    determine_category,
    determine_composite_category,
    meets_spe_criteria,
    spe_failing_criteria,
    SPE_MAX_MEOP_BAR,
    SPE_MAX_VOLUME_LITRES,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _item(**overrides) -> HardwareItem:
    """Return an SPE-eligible HardwareItem, optionally overriding fields."""
    base = dict(
        item_id="item-001",
        is_assembly=False,
        carries_structural_loads=False,
        shape_simple=True,
        meop_bar=10.0,
        volume_litres=5.0,
        uses_common_material=True,
        no_heat_source=True,
        sub_items=(),
    )
    base.update(overrides)
    return HardwareItem(**base)


def _sub(item_id: str = "sub-001") -> HardwareItem:
    """Return a minimal SPE-eligible sub-item."""
    return _item(item_id=item_id)


# ---------------------------------------------------------------------------
# SPE criteria gate
# ---------------------------------------------------------------------------

class TestSpeGate(unittest.TestCase):

    def test_all_criteria_met_returns_true(self):
        self.assertTrue(meets_spe_criteria(_item()))

    def test_non_simple_shape_fails(self):
        self.assertFalse(meets_spe_criteria(_item(shape_simple=False)))

    def test_meop_at_threshold_passes(self):
        self.assertTrue(meets_spe_criteria(_item(meop_bar=SPE_MAX_MEOP_BAR)))

    def test_meop_above_threshold_fails(self):
        self.assertFalse(meets_spe_criteria(_item(meop_bar=SPE_MAX_MEOP_BAR + 0.01)))

    def test_volume_at_threshold_passes(self):
        self.assertTrue(meets_spe_criteria(_item(volume_litres=SPE_MAX_VOLUME_LITRES)))

    def test_volume_above_threshold_fails(self):
        self.assertFalse(meets_spe_criteria(_item(volume_litres=SPE_MAX_VOLUME_LITRES + 0.01)))

    def test_non_standard_material_fails(self):
        self.assertFalse(meets_spe_criteria(_item(uses_common_material=False)))

    def test_heat_source_present_fails(self):
        self.assertFalse(meets_spe_criteria(_item(no_heat_source=False)))

    def test_failing_criteria_reports_high_meop(self):
        failures = spe_failing_criteria(_item(meop_bar=SPE_MAX_MEOP_BAR + 5.0))
        self.assertTrue(any("MEOP" in f for f in failures))

    def test_failing_criteria_empty_when_all_pass(self):
        self.assertEqual(spe_failing_criteria(_item()), [])


# ---------------------------------------------------------------------------
# Single-item category determination — happy paths
# ---------------------------------------------------------------------------

class TestCategoryHappyPaths(unittest.TestCase):

    def test_spe_category_assigned(self):
        result = determine_category(_item())
        self.assertEqual(result.category, "SPE")

    def test_pv_category_high_pressure(self):
        result = determine_category(_item(meop_bar=200.0))
        self.assertEqual(result.category, "PV")

    def test_pv_category_complex_shape(self):
        result = determine_category(_item(shape_simple=False))
        self.assertEqual(result.category, "PV")

    def test_pv_category_large_volume(self):
        result = determine_category(_item(volume_litres=SPE_MAX_VOLUME_LITRES + 1.0))
        self.assertEqual(result.category, "PV")

    def test_pc_category_structural_loads(self):
        result = determine_category(_item(carries_structural_loads=True))
        self.assertEqual(result.category, "PC")

    def test_ps_category_assembly(self):
        result = determine_category(
            _item(is_assembly=True, sub_items=(_sub("c1"), _sub("c2")))
        )
        self.assertEqual(result.category, "PS")

    def test_ps_sub_item_results_count(self):
        result = determine_category(
            _item(is_assembly=True, sub_items=(_sub("c1"), _sub("c2"), _sub("c3")))
        )
        self.assertEqual(len(result.sub_item_results), 3)

    def test_ps_sub_item_categories_resolved(self):
        high_p_sub = _item(item_id="tank-pv", meop_bar=200.0)
        result = determine_category(
            _item(is_assembly=True, sub_items=(high_p_sub,))
        )
        self.assertEqual(result.sub_item_results[0].category, "PV")


# ---------------------------------------------------------------------------
# Priority ordering (PC before SPE; PS before PC)
# ---------------------------------------------------------------------------

class TestCategoryPriority(unittest.TestCase):

    def test_pc_wins_over_spe_when_loads_present(self):
        # item meets SPE criteria but also carries structural loads → PC
        result = determine_category(_item(carries_structural_loads=True))
        self.assertEqual(result.category, "PC")

    def test_ps_wins_over_pc_when_assembly(self):
        # assembly flag takes top priority regardless of structural loads
        result = determine_category(
            _item(is_assembly=True, carries_structural_loads=True, sub_items=(_sub(),))
        )
        self.assertEqual(result.category, "PS")

    def test_pv_is_default_when_no_other_branch_matches(self):
        # exotic material, within pressure/volume limits but non-standard material
        result = determine_category(_item(uses_common_material=False))
        self.assertEqual(result.category, "PV")


# ---------------------------------------------------------------------------
# Result metadata
# ---------------------------------------------------------------------------

class TestResultMetadata(unittest.TestCase):

    def test_item_id_preserved_in_result(self):
        result = determine_category(_item(item_id="tank-007"))
        self.assertEqual(result.item_id, "tank-007")

    def test_rationale_non_empty_for_spe(self):
        result = determine_category(_item())
        self.assertGreater(len(result.rationale), 0)

    def test_rationale_non_empty_for_pv(self):
        result = determine_category(_item(meop_bar=500.0))
        self.assertGreater(len(result.rationale), 0)

    def test_rationale_non_empty_for_pc(self):
        result = determine_category(_item(carries_structural_loads=True))
        self.assertGreater(len(result.rationale), 0)

    def test_rationale_non_empty_for_ps(self):
        result = determine_category(_item(is_assembly=True, sub_items=(_sub(),)))
        self.assertGreater(len(result.rationale), 0)

    def test_result_is_immutable(self):
        result = determine_category(_item())
        with self.assertRaises((AttributeError, TypeError)):
            result.category = "CHANGED"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Composite / batch determination
# ---------------------------------------------------------------------------

class TestCompositeCategory(unittest.TestCase):

    def test_returns_one_result_per_item(self):
        items = [
            _item(item_id="a"),
            _item(item_id="b", meop_bar=100.0),
            _item(item_id="c", carries_structural_loads=True),
        ]
        results = determine_composite_category(items)
        self.assertEqual(len(results), 3)

    def test_mixed_categories_resolved_correctly(self):
        items = [
            _item(item_id="spe-x"),
            _item(item_id="pv-x", meop_bar=200.0),
            _item(item_id="pc-x", carries_structural_loads=True),
        ]
        by_id = {r.item_id: r.category for r in determine_composite_category(items)}
        self.assertEqual(by_id["spe-x"], "SPE")
        self.assertEqual(by_id["pv-x"], "PV")
        self.assertEqual(by_id["pc-x"], "PC")

    def test_empty_list_raises_category_error(self):
        with self.assertRaises(CategoryError):
            determine_composite_category([])

    def test_single_item_list_works(self):
        results = determine_composite_category([_item(item_id="only")])
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].item_id, "only")


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestInputValidation(unittest.TestCase):

    def test_empty_item_id_raises(self):
        with self.assertRaises(CategoryError):
            determine_category(_item(item_id=""))

    def test_whitespace_only_item_id_raises(self):
        with self.assertRaises(CategoryError):
            determine_category(_item(item_id="   "))

    def test_negative_meop_raises(self):
        with self.assertRaises(CategoryError):
            determine_category(_item(meop_bar=-1.0))

    def test_negative_volume_raises(self):
        with self.assertRaises(CategoryError):
            determine_category(_item(volume_litres=-0.5))

    def test_assembly_with_no_sub_items_raises(self):
        with self.assertRaises(CategoryError):
            determine_category(_item(is_assembly=True, sub_items=()))

    def test_zero_meop_accepted(self):
        result = determine_category(_item(meop_bar=0.0))
        self.assertIn(result.category, ("SPE", "PV", "PC", "PS"))

    def test_zero_volume_accepted(self):
        result = determine_category(_item(volume_litres=0.0))
        self.assertIn(result.category, ("SPE", "PV", "PC", "PS"))


if __name__ == "__main__":
    unittest.main()
