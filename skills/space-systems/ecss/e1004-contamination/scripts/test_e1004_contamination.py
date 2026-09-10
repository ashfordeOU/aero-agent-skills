#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-04C clause 11.2 on-orbit
contamination assessment.

Exercises scripts/e1004_contamination_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a source type
classifies as exactly molecular or particulate and an unrecognized
type raises; a molecular source's transport path is direct line-of-
sight when it has a view factor to the surface, return flux when it
instead sits in the LEO ram/wake region, and no-transport-path
otherwise; deposited mass is source rate x transport efficiency x
exposure duration, zero for no-transport-path, and negative rate/
duration or an unrecognized path raises; a surface's summed molecular
deposition is checked against its budget (an unset budget with
nonzero deposition is itself a finding), and a surface with
particulate sources but no cleanliness level is flagged; the
aggregated review is compliant only when both categories are empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1004_contamination_logic as ct  # noqa: E402


class ClassifySourceTest(unittest.TestCase):
    def test_outgassing_is_molecular(self):
        self.assertEqual(ct.classify_source("outgassing"), "molecular")

    def test_venting_is_molecular(self):
        self.assertEqual(ct.classify_source("venting"), "molecular")

    def test_propulsion_effluent_is_molecular(self):
        self.assertEqual(ct.classify_source("propulsion_effluent"), "molecular")

    def test_leak_is_molecular(self):
        self.assertEqual(ct.classify_source("leak"), "molecular")

    def test_debris_is_particulate(self):
        self.assertEqual(ct.classify_source("debris"), "particulate")

    def test_mli_fragment_is_particulate(self):
        self.assertEqual(ct.classify_source("mli_fragment"), "particulate")

    def test_handling_residue_is_particulate(self):
        self.assertEqual(ct.classify_source("handling_residue"), "particulate")

    def test_paint_flake_is_particulate(self):
        self.assertEqual(ct.classify_source("paint_flake"), "particulate")

    def test_unknown_source_raises(self):
        with self.assertRaises(ValueError):
            ct.classify_source("mystery_haze")


class MolecularTransportPathTest(unittest.TestCase):
    def test_line_of_sight_wins(self):
        self.assertEqual(
            ct.molecular_transport_path(True, True), "direct_line_of_sight"
        )

    def test_line_of_sight_only(self):
        self.assertEqual(
            ct.molecular_transport_path(True, False), "direct_line_of_sight"
        )

    def test_ram_wake_without_los_is_return_flux(self):
        self.assertEqual(ct.molecular_transport_path(False, True), "return_flux")

    def test_neither_is_no_transport_path(self):
        self.assertEqual(
            ct.molecular_transport_path(False, False), ct.NO_TRANSPORT_PATH
        )


class MolecularDepositionTest(unittest.TestCase):
    def test_direct_line_of_sight_full_efficiency(self):
        deposition = ct.molecular_deposition(2.0, "direct_line_of_sight", 100.0)
        self.assertAlmostEqual(deposition, 200.0)

    def test_return_flux_reduced_efficiency(self):
        deposition = ct.molecular_deposition(2.0, "return_flux", 100.0)
        self.assertAlmostEqual(deposition, 20.0)

    def test_no_transport_path_is_zero(self):
        self.assertEqual(
            ct.molecular_deposition(5.0, ct.NO_TRANSPORT_PATH, 100.0), 0.0
        )

    def test_negative_rate_raises(self):
        with self.assertRaises(ValueError):
            ct.molecular_deposition(-1.0, "direct_line_of_sight", 100.0)

    def test_negative_duration_raises(self):
        with self.assertRaises(ValueError):
            ct.molecular_deposition(1.0, "direct_line_of_sight", -100.0)

    def test_unrecognized_path_raises(self):
        with self.assertRaises(ValueError):
            ct.molecular_deposition(1.0, "teleportation", 100.0)


class MolecularBudgetViolationsTest(unittest.TestCase):
    def test_within_budget_has_no_violation(self):
        sources = [
            {
                "source_rate_ng_cm2_s": 1.0,
                "transport_path": "direct_line_of_sight",
                "exposure_duration_s": 10.0,
            }
        ]
        self.assertEqual(
            ct.molecular_budget_violations("optic-1", sources, 50.0), []
        )

    def test_exceeding_budget_flagged(self):
        sources = [
            {
                "source_rate_ng_cm2_s": 1.0,
                "transport_path": "direct_line_of_sight",
                "exposure_duration_s": 100.0,
            }
        ]
        violations = ct.molecular_budget_violations("optic-1", sources, 50.0)
        self.assertEqual(
            violations,
            [
                {
                    "issue": "molecular_deposition_budget_exceeded",
                    "surface": "optic-1",
                    "total_ng_cm2": 100.0,
                    "budget_ng_cm2": 50.0,
                }
            ],
        )

    def test_missing_budget_with_deposition_flagged(self):
        sources = [
            {
                "source_rate_ng_cm2_s": 1.0,
                "transport_path": "direct_line_of_sight",
                "exposure_duration_s": 10.0,
            }
        ]
        violations = ct.molecular_budget_violations("optic-1", sources, None)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0]["issue"], "missing_molecular_budget_q_st_70_01")

    def test_missing_budget_with_zero_deposition_not_flagged(self):
        self.assertEqual(ct.molecular_budget_violations("optic-1", [], None), [])

    def test_sums_multiple_sources(self):
        sources = [
            {
                "source_rate_ng_cm2_s": 1.0,
                "transport_path": "direct_line_of_sight",
                "exposure_duration_s": 10.0,
            },
            {
                "source_rate_ng_cm2_s": 2.0,
                "transport_path": "return_flux",
                "exposure_duration_s": 10.0,
            },
        ]
        # 1.0*1.0*10 + 2.0*0.1*10 = 10 + 2 = 12, under a 20 budget.
        self.assertEqual(ct.molecular_budget_violations("optic-1", sources, 20.0), [])


class ParticulateControlViolationsTest(unittest.TestCase):
    def test_no_particulate_sources_no_violation(self):
        self.assertEqual(
            ct.particulate_control_violations("panel-1", False, None), []
        )

    def test_particulate_sources_with_level_no_violation(self):
        self.assertEqual(
            ct.particulate_control_violations("panel-1", True, "VC-1000"), []
        )

    def test_particulate_sources_without_level_flagged(self):
        violations = ct.particulate_control_violations("panel-1", True, None)
        self.assertEqual(
            violations,
            [{"issue": "missing_cleanliness_level_q_st_70_01", "surface": "panel-1"}],
        )


class ContaminationReviewTest(unittest.TestCase):
    def test_fully_compliant_review(self):
        surface = {
            "surface_id": "optic-1",
            "sources": [
                {
                    "source_type": "outgassing",
                    "transport_path": "direct_line_of_sight",
                    "source_rate_ng_cm2_s": 0.5,
                    "exposure_duration_s": 10.0,
                },
                {"source_type": "debris"},
            ],
            "allowable_budget_ng_cm2": 20.0,
            "cleanliness_level": "VC-1000",
        }
        review = ct.contamination_review(surface)
        self.assertEqual(review, {"molecular": [], "particulate": []})
        self.assertTrue(ct.is_contamination_compliant(review))

    def test_review_surfaces_each_category_independently(self):
        surface = {
            "surface_id": "optic-2",
            "sources": [
                {
                    "source_type": "leak",
                    "transport_path": "direct_line_of_sight",
                    "source_rate_ng_cm2_s": 5.0,
                    "exposure_duration_s": 100.0,
                },
                {"source_type": "paint_flake"},
            ],
            "allowable_budget_ng_cm2": 10.0,
            "cleanliness_level": None,
        }
        review = ct.contamination_review(surface)
        self.assertTrue(review["molecular"])
        self.assertTrue(review["particulate"])
        self.assertFalse(ct.is_contamination_compliant(review))

    def test_review_ignores_no_transport_path_source(self):
        surface = {
            "surface_id": "optic-3",
            "sources": [
                {
                    "source_type": "venting",
                    "transport_path": ct.NO_TRANSPORT_PATH,
                    "source_rate_ng_cm2_s": 5.0,
                    "exposure_duration_s": 100.0,
                },
            ],
            "allowable_budget_ng_cm2": 0.0,
            "cleanliness_level": None,
        }
        review = ct.contamination_review(surface)
        self.assertEqual(review["molecular"], [])

    def test_review_raises_on_unknown_source_type(self):
        surface = {
            "surface_id": "optic-4",
            "sources": [{"source_type": "unobtainium_dust"}],
            "allowable_budget_ng_cm2": None,
            "cleanliness_level": None,
        }
        with self.assertRaises(ValueError):
            ct.contamination_review(surface)


if __name__ == "__main__":
    unittest.main(verbosity=2)
