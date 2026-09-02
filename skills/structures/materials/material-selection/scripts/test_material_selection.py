#!/usr/bin/env python3
"""Gate 3 contract test: material selection indices logic.

Exercises scripts/material_selection_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - Ashby-style
selection indices (E/rho tension, E^(1/2)/rho beam, E^(1/3)/rho
panel; sigma/rho and strength exponents for strength-limited
parts); representative band values give aluminum > steel on beam
stiffness per weight, titanium > aluminum on strength per weight,
and CFRP dominance on tension stiffness; ranking is deterministic
and the winning material changes with the index mode; temperature,
corrosion, cost, and family screening; invalid material or mode
raises ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import material_selection_logic as msl  # noqa: E402

METALS = ["al-2024-t3", "al-7075-t6", "ti-6al-4v", "steel-4340"]
ALL = METALS + ["cfrp-epoxy-laminate"]


class SelectionIndexTest(unittest.TestCase):
    def test_aluminum_beats_steel_in_beam_stiffness(self):
        al = msl.selection_index("al-2024-t3", "stiffness-beam")
        st = msl.selection_index("steel-4340", "stiffness-beam")
        self.assertGreater(al, st)

    def test_titanium_between_aluminum_and_steel_beam_stiffness(self):
        al = msl.selection_index("al-2024-t3", "stiffness-beam")
        ti = msl.selection_index("ti-6al-4v", "stiffness-beam")
        st = msl.selection_index("steel-4340", "stiffness-beam")
        self.assertGreater(al, ti)
        self.assertGreater(ti, st)

    def test_aluminum_beats_steel_in_panel_stiffness(self):
        al = msl.selection_index("al-2024-t3", "stiffness-panel")
        st = msl.selection_index("steel-4340", "stiffness-panel")
        self.assertGreater(al, st)

    def test_cfrp_dominates_tension_stiffness(self):
        cfrp = msl.selection_index("cfrp-epoxy-laminate", "stiffness-tie")
        al = msl.selection_index("al-2024-t3", "stiffness-tie")
        self.assertGreater(cfrp, 2.0 * al)

    def test_titanium_beats_aluminum_in_strength_per_weight(self):
        ti = msl.selection_index("ti-6al-4v", "strength-tie")
        al7075 = msl.selection_index("al-7075-t6", "strength-tie")
        al2024 = msl.selection_index("al-2024-t3", "strength-tie")
        self.assertGreater(ti, al7075)
        self.assertGreater(al7075, al2024)

    def test_cfrp_beats_titanium_in_strength_per_weight(self):
        cfrp = msl.selection_index("cfrp-epoxy-laminate", "strength-tie")
        ti = msl.selection_index("ti-6al-4v", "strength-tie")
        self.assertGreater(cfrp, ti)

    def test_7075_beats_titanium_in_beam_strength(self):
        al = msl.selection_index("al-7075-t6", "strength-beam")
        ti = msl.selection_index("ti-6al-4v", "strength-beam")
        self.assertGreater(al, ti)

    def test_invalid_mode_raises(self):
        with self.assertRaises(ValueError):
            msl.selection_index("al-2024-t3", "stiffness-torsion")

    def test_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            msl.selection_index("magnesium-az31", "stiffness-tie")


class RankingTest(unittest.TestCase):
    def test_rank_is_deterministic(self):
        first = msl.rank_materials(ALL, "stiffness-beam")
        second = msl.rank_materials(ALL, "stiffness-beam")
        self.assertEqual(first, second)

    def test_index_choice_changes_the_winner(self):
        beam = msl.rank_materials(METALS, "stiffness-beam")
        strength = msl.rank_materials(METALS, "strength-tie")
        self.assertEqual(beam[0][0], "al-2024-t3")
        self.assertEqual(strength[0][0], "ti-6al-4v")

    def test_rank_is_sorted_descending(self):
        ranked = msl.rank_materials(ALL, "strength-tie")
        values = [index for _, index in ranked]
        self.assertEqual(values, sorted(values, reverse=True))

    def test_rank_rejects_empty_list(self):
        with self.assertRaises(ValueError):
            msl.rank_materials([], "stiffness-tie")

    def test_rank_covers_every_candidate(self):
        ranked = msl.rank_materials(ALL, "stiffness-panel")
        self.assertEqual(sorted(m for m, _ in ranked), sorted(ALL))


class ScreeningTest(unittest.TestCase):
    def test_temperature_limit_order(self):
        self.assertGreater(
            msl.temperature_limit("steel-4340"),
            msl.temperature_limit("ti-6al-4v"),
        )
        self.assertGreater(
            msl.temperature_limit("ti-6al-4v"),
            msl.temperature_limit("al-2024-t3"),
        )
        self.assertGreater(
            msl.temperature_limit("al-2024-t3"),
            msl.temperature_limit("cfrp-epoxy-laminate"),
        )

    def test_temperature_ok_verdict(self):
        self.assertTrue(msl.temperature_ok("al-2024-t3", 100.0))
        self.assertFalse(msl.temperature_ok("al-2024-t3", 200.0))
        self.assertTrue(msl.temperature_ok("ti-6al-4v", 300.0))
        self.assertFalse(msl.temperature_ok("cfrp-epoxy-laminate", 150.0))

    def test_corrosion_titanium_rating_is_highest(self):
        ti = msl.corrosion_rating("ti-6al-4v")
        self.assertGreater(ti, msl.corrosion_rating("al-2024-t3"))
        self.assertGreater(ti, msl.corrosion_rating("steel-4340"))
        self.assertGreater(ti, msl.corrosion_rating("cfrp-epoxy-laminate"))

    def test_cost_ordering(self):
        cfrp = msl.relative_cost("cfrp-epoxy-laminate")
        ti = msl.relative_cost("ti-6al-4v")
        al = msl.relative_cost("al-7075-t6")
        st = msl.relative_cost("steel-4340")
        self.assertGreater(cfrp, ti)
        self.assertGreater(ti, al)
        self.assertGreater(al, st)

    def test_family_classification(self):
        self.assertEqual(msl.material_family("al-2024-t3"), "aluminum")
        self.assertEqual(msl.material_family("al-7075-t6"), "aluminum")
        self.assertEqual(msl.material_family("ti-6al-4v"), "titanium")
        self.assertEqual(msl.material_family("steel-4340"), "steel")
        self.assertEqual(msl.material_family("cfrp-epoxy-laminate"), "composite")

    def test_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            msl.material_family("inconel-718")


if __name__ == "__main__":
    unittest.main(verbosity=2)
