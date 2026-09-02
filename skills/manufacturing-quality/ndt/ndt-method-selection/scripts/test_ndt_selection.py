#!/usr/bin/env python3
"""Gate 3 contract test: NDT method selection.

Exercises scripts/ndt_selection_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - applicable_methods from
the decision table (internal -> RT, UT; near-surface -> ET, UT;
surface -> MT, PT for ferromagnetic, ET, PT for non-ferromagnetic,
PT for non-conductive), select_method top pick by sensitivity with
the tie broken toward the later method in TIE_ORDER (MT vs PT ->
PT), sensitivity_rank, cost_rank, and ValueError on unknown defect
class or material class.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import ndt_selection_logic as nsl  # noqa: E402


class ApplicableMethodsTest(unittest.TestCase):
    def test_internal_ferromagnetic(self):
        self.assertEqual(nsl.applicable_methods("internal", "ferromagnetic"), ["RT", "UT"])

    def test_internal_non_conductive(self):
        self.assertEqual(nsl.applicable_methods("internal", "non-conductive"), ["RT", "UT"])

    def test_near_surface_non_ferromagnetic(self):
        self.assertEqual(nsl.applicable_methods("near-surface", "non-ferromagnetic"), ["ET", "UT"])

    def test_surface_ferromagnetic(self):
        self.assertEqual(nsl.applicable_methods("surface", "ferromagnetic"), ["MT", "PT"])

    def test_surface_non_ferromagnetic(self):
        self.assertEqual(nsl.applicable_methods("surface", "non-ferromagnetic"), ["ET", "PT"])

    def test_surface_non_conductive(self):
        self.assertEqual(nsl.applicable_methods("surface", "non-conductive"), ["PT"])

    def test_unknown_defect_class(self):
        with self.assertRaises(ValueError):
            nsl.applicable_methods("volumetric", "ferromagnetic")

    def test_unknown_material_class(self):
        with self.assertRaises(ValueError):
            nsl.applicable_methods("internal", "ceramic")


class SelectMethodTest(unittest.TestCase):
    def test_internal_ferromagnetic_picks_ut(self):
        result = nsl.select_method("internal", "ferromagnetic")
        self.assertEqual(result["method"], "UT")
        self.assertEqual(result["alternates"], ["RT"])

    def test_near_surface_non_ferromagnetic_picks_ut(self):
        result = nsl.select_method("near-surface", "non-ferromagnetic")
        self.assertEqual(result["method"], "UT")
        self.assertEqual(result["alternates"], ["ET"])

    def test_surface_ferromagnetic_tie_picks_pt(self):
        # MT and PT both rank 3; the tie breaks toward the later
        # method in TIE_ORDER (also the alphabetically-later one): PT.
        result = nsl.select_method("surface", "ferromagnetic")
        self.assertEqual(result["method"], "PT")
        self.assertEqual(result["alternates"], ["MT"])

    def test_surface_non_ferromagnetic_picks_et(self):
        result = nsl.select_method("surface", "non-ferromagnetic")
        self.assertEqual(result["method"], "ET")
        self.assertEqual(result["alternates"], ["PT"])

    def test_surface_non_conductive_picks_pt(self):
        result = nsl.select_method("surface", "non-conductive")
        self.assertEqual(result["method"], "PT")
        self.assertEqual(result["alternates"], [])

    def test_internal_non_conductive_picks_ut(self):
        result = nsl.select_method("internal", "non-conductive")
        self.assertEqual(result["method"], "UT")
        self.assertEqual(result["alternates"], ["RT"])

    def test_rationale_names_defect_material_method(self):
        for defect_class, material in [
            ("internal", "ferromagnetic"),
            ("surface", "ferromagnetic"),
            ("surface", "non-conductive"),
            ("near-surface", "non-ferromagnetic"),
        ]:
            result = nsl.select_method(defect_class, material)
            self.assertIn(defect_class, result["rationale"])
            self.assertIn(material, result["rationale"])
            self.assertIn(result["method"], result["rationale"])

    def test_unknown_defect_class(self):
        with self.assertRaises(ValueError):
            nsl.select_method("volumetric", "ferromagnetic")

    def test_unknown_material_class(self):
        with self.assertRaises(ValueError):
            nsl.select_method("surface", "ceramic")


class RankTest(unittest.TestCase):
    def test_sensitivity_ranks(self):
        self.assertEqual(nsl.sensitivity_rank("UT"), 5)
        self.assertEqual(nsl.sensitivity_rank("RT"), 4)
        self.assertEqual(nsl.sensitivity_rank("ET"), 4)
        self.assertEqual(nsl.sensitivity_rank("MT"), 3)
        self.assertEqual(nsl.sensitivity_rank("PT"), 3)

    def test_cost_ranks(self):
        self.assertEqual(nsl.cost_rank("RT"), 4)
        self.assertEqual(nsl.cost_rank("UT"), 3)
        self.assertEqual(nsl.cost_rank("ET"), 2)
        self.assertEqual(nsl.cost_rank("MT"), 2)
        self.assertEqual(nsl.cost_rank("PT"), 1)

    def test_unknown_method(self):
        with self.assertRaises(ValueError):
            nsl.sensitivity_rank("XRAY")
        with self.assertRaises(ValueError):
            nsl.cost_rank("XRAY")


if __name__ == "__main__":
    unittest.main()
