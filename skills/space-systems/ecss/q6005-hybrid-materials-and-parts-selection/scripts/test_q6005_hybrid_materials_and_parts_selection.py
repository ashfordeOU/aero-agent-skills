#!/usr/bin/env python3
"""Gate 3 contract test for q6005-hybrid-materials-and-parts-selection.

Offline, stdlib unittest. Exercises the candidate validation, qualification
standing, expansion-mismatch strain, vacuum outgassing screen, wire-to-pad
couple and the merged three-way selectability of ECSS-Q-ST-60-05C clause 9.2
as paraphrased in the logic module. Strain and outgassing figures land exactly
on their allowables in the ordinary case, so those bounds are asserted with
assertAlmostEqual rather than a strict inequality that could round either way
between the build host and the CI runner.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from q6005_hybrid_materials_and_parts_selection_logic import (  # noqa: E402
    DEFAULT_LIMITS,
    EVALUATION_REQUIRED,
    NOT_SELECTABLE,
    SELECTABLE,
    assess_item,
    assess_selection,
    bond_couple_status,
    cte_mismatch_strain,
    cte_status,
    normalise_metal,
    outgassing_status,
    qualification_status,
    validate_item,
    worst_status,
)


def substrate(**overrides):
    item = {
        "name": "alumina-substrate",
        "category": "substrate",
        "qualification": "qualified",
        "cte_ppm_per_k": 6.5,
    }
    item.update(overrides)
    return item


def adhesive(**overrides):
    item = {
        "name": "silver-filled-die-attach",
        "category": "die-attach",
        "qualification": "qualified",
        "tml_percent": 0.4,
        "cvcm_percent": 0.02,
    }
    item.update(overrides)
    return item


def wire(**overrides):
    item = {
        "name": "bonding-wire-25um",
        "category": "bonding-wire",
        "qualification": "qualified",
        "wire_metal": "gold",
        "pad_metal": "gold",
    }
    item.update(overrides)
    return item


class CandidateValidationTests(unittest.TestCase):
    def test_unknown_category_is_refused(self):
        with self.assertRaises(ValueError):
            validate_item(substrate(category="flux"))

    def test_blank_name_is_refused(self):
        with self.assertRaises(ValueError):
            validate_item(substrate(name="   "))

    def test_unknown_qualification_standing_is_refused(self):
        with self.assertRaises(ValueError):
            validate_item(substrate(qualification="probably-fine"))

    def test_polymeric_item_without_outgassing_data_is_refused(self):
        bare = adhesive()
        del bare["cvcm_percent"]
        with self.assertRaises(ValueError):
            validate_item(bare)

    def test_bonding_wire_without_a_couple_is_refused(self):
        bare = wire()
        del bare["pad_metal"]
        with self.assertRaises(ValueError):
            validate_item(bare)

    def test_negative_expansion_coefficient_is_refused(self):
        with self.assertRaises(ValueError):
            validate_item(substrate(cte_ppm_per_k=-1.0))

    def test_category_and_standing_are_normalised(self):
        record = validate_item(substrate(category="SUBSTRATE", qualification="Qualified"))
        self.assertEqual(record["category"], "substrate")
        self.assertEqual(record["qualification"], "qualified")


class MetalAndCoupleTests(unittest.TestCase):
    def test_symbols_and_spellings_normalise_to_one_name(self):
        self.assertEqual(normalise_metal("Au"), "gold")
        self.assertEqual(normalise_metal("aluminum"), "aluminium")

    def test_unrecognised_finish_is_refused(self):
        with self.assertRaises(ValueError):
            normalise_metal("unobtainium")

    def test_like_metals_are_a_proven_couple(self):
        self.assertEqual(bond_couple_status("gold", "Au"), SELECTABLE)

    def test_gold_to_aluminium_owes_an_intermetallic_evaluation(self):
        self.assertEqual(bond_couple_status("gold", "aluminium"), EVALUATION_REQUIRED)

    def test_tin_bearing_couple_is_refused_from_either_side(self):
        self.assertEqual(bond_couple_status("gold", "tin"), NOT_SELECTABLE)
        self.assertEqual(bond_couple_status("tin", "copper"), NOT_SELECTABLE)

    def test_proven_unlike_couple_needs_no_evaluation(self):
        self.assertEqual(bond_couple_status("gold", "palladium"), SELECTABLE)


class ExpansionMismatchTests(unittest.TestCase):
    def test_strain_is_the_mismatch_times_the_excursion(self):
        self.assertAlmostEqual(cte_mismatch_strain(7.0, 5.0, 100.0), 200.0, places=9)

    def test_matched_expansion_gives_no_strain(self):
        self.assertAlmostEqual(cte_mismatch_strain(6.5, 6.5, 180.0), 0.0, places=9)

    def test_strain_is_symmetric_in_the_two_coefficients(self):
        self.assertAlmostEqual(
            cte_mismatch_strain(5.0, 7.0, 100.0),
            cte_mismatch_strain(7.0, 5.0, 100.0),
            places=9,
        )

    def test_negative_excursion_is_refused(self):
        with self.assertRaises(ValueError):
            cte_mismatch_strain(7.0, 5.0, -10.0)

    def test_comfortable_strain_is_selectable(self):
        self.assertEqual(cte_status(50.0), SELECTABLE)

    def test_strain_landing_on_the_allowable_still_meets_it(self):
        # 250.0 is the allowable itself; it is inside the evaluation band but
        # it is not above the limit, so it is not a refusal.
        self.assertAlmostEqual(DEFAULT_LIMITS["cte_strain_ppm"], 250.0, places=9)
        self.assertEqual(cte_status(DEFAULT_LIMITS["cte_strain_ppm"]), EVALUATION_REQUIRED)

    def test_strain_landing_on_the_band_edge_is_outside_the_band(self):
        band = DEFAULT_LIMITS["cte_evaluation_fraction"] * DEFAULT_LIMITS["cte_strain_ppm"]
        self.assertAlmostEqual(band, 187.5, places=9)
        self.assertEqual(cte_status(band), SELECTABLE)

    def test_strain_above_the_allowable_is_refused(self):
        self.assertEqual(cte_status(300.0), NOT_SELECTABLE)

    def test_project_limit_override_moves_the_allowable(self):
        # 300 ppm refuses against the default 250 allowable and is comfortable
        # against a project allowable of 400, whose evaluation band starts at 300.
        self.assertEqual(cte_status(300.0), NOT_SELECTABLE)
        self.assertEqual(cte_status(300.0, {"cte_strain_ppm": 400.0}), SELECTABLE)
        self.assertEqual(cte_status(350.0, {"cte_strain_ppm": 400.0}), EVALUATION_REQUIRED)

    def test_unrecognised_limit_key_is_refused(self):
        with self.assertRaises(ValueError):
            cte_status(100.0, {"cte_strain_limit": 400.0})


class OutgassingTests(unittest.TestCase):
    def test_clean_polymer_passes_the_screen(self):
        self.assertEqual(outgassing_status(0.4, 0.02)["status"], SELECTABLE)

    def test_figures_landing_on_the_allowables_meet_them(self):
        screen = outgassing_status(DEFAULT_LIMITS["tml_percent"], DEFAULT_LIMITS["cvcm_percent"])
        self.assertEqual(screen["status"], SELECTABLE)
        self.assertEqual(screen["findings"], [])
        self.assertAlmostEqual(screen["tml_percent"], 1.0, places=9)
        self.assertAlmostEqual(screen["cvcm_percent"], 0.10, places=9)

    def test_excess_mass_loss_refuses_the_item(self):
        screen = outgassing_status(1.6, 0.02)
        self.assertEqual(screen["status"], NOT_SELECTABLE)
        self.assertTrue(any("mass loss" in f for f in screen["findings"]))

    def test_excess_condensable_volatiles_refuse_the_item(self):
        screen = outgassing_status(0.4, 0.31)
        self.assertEqual(screen["status"], NOT_SELECTABLE)
        self.assertTrue(any("condensable" in f for f in screen["findings"]))

    def test_both_figures_failing_are_both_named(self):
        screen = outgassing_status(2.0, 0.5)
        self.assertEqual(len(screen["findings"]), 2)

    def test_non_numeric_mass_loss_is_refused(self):
        with self.assertRaises(ValueError):
            outgassing_status("0.4", 0.02)


class StandingAndMergeTests(unittest.TestCase):
    def test_qualified_item_needs_nothing_further(self):
        self.assertEqual(qualification_status("qualified"), SELECTABLE)

    def test_similarity_and_unqualified_standings_owe_an_evaluation(self):
        self.assertEqual(qualification_status("qualified-by-similarity"), EVALUATION_REQUIRED)
        self.assertEqual(qualification_status("unqualified"), EVALUATION_REQUIRED)

    def test_merge_returns_the_most_restrictive_outcome(self):
        self.assertEqual(
            worst_status([SELECTABLE, EVALUATION_REQUIRED, NOT_SELECTABLE]), NOT_SELECTABLE
        )
        self.assertEqual(worst_status([SELECTABLE, SELECTABLE]), SELECTABLE)

    def test_merge_refuses_an_unrecognised_outcome(self):
        with self.assertRaises(ValueError):
            worst_status([SELECTABLE, "maybe"])

    def test_merge_refuses_an_empty_set(self):
        with self.assertRaises(ValueError):
            worst_status([])


class ItemAssessmentTests(unittest.TestCase):
    def test_qualified_clean_substrate_is_selectable(self):
        verdict = assess_item(substrate(), {"mating_cte_ppm_per_k": 6.0,
                                            "temperature_excursion_k": 100.0})
        self.assertEqual(verdict["status"], SELECTABLE)
        self.assertEqual(verdict["findings"], [])
        self.assertAlmostEqual(verdict["measurements"]["cte_mismatch_strain_ppm"], 50.0, places=9)

    def test_mismatch_beyond_the_allowable_refuses_the_substrate(self):
        verdict = assess_item(substrate(cte_ppm_per_k=10.0),
                              {"mating_cte_ppm_per_k": 5.0, "temperature_excursion_k": 100.0})
        self.assertEqual(verdict["status"], NOT_SELECTABLE)
        self.assertTrue(any("mismatch strain" in f for f in verdict["findings"]))

    def test_mismatch_condition_is_skipped_when_no_mating_part_is_declared(self):
        verdict = assess_item(substrate(cte_ppm_per_k=10.0))
        self.assertEqual(verdict["status"], SELECTABLE)
        self.assertNotIn("cte_mismatch_strain_ppm", verdict["measurements"])

    def test_mating_coefficient_without_an_excursion_is_refused(self):
        with self.assertRaises(ValueError):
            assess_item(substrate(), {"mating_cte_ppm_per_k": 6.0})

    def test_unqualified_item_is_open_until_it_is_evaluated(self):
        verdict = assess_item(substrate(qualification="unqualified"))
        self.assertEqual(verdict["status"], EVALUATION_REQUIRED)

    def test_evaluation_owed_with_no_programme_open_becomes_a_refusal(self):
        verdict = assess_item(substrate(qualification="unqualified"),
                              {"evaluation_programme_available": False})
        self.assertEqual(verdict["status"], NOT_SELECTABLE)
        self.assertTrue(any("no evaluation programme" in f for f in verdict["findings"]))

    def test_dirty_adhesive_is_refused_on_outgassing_alone(self):
        verdict = assess_item(adhesive(tml_percent=2.4))
        self.assertEqual(verdict["status"], NOT_SELECTABLE)
        self.assertAlmostEqual(verdict["measurements"]["tml_percent"], 2.4, places=9)

    def test_unlike_wire_couple_is_reported_with_the_couple_named(self):
        verdict = assess_item(wire(pad_metal="aluminium"))
        self.assertEqual(verdict["status"], EVALUATION_REQUIRED)
        self.assertEqual(verdict["measurements"]["bond_couple"], "gold-to-aluminium")

    def test_unrecognised_context_key_is_refused(self):
        with self.assertRaises(ValueError):
            assess_item(substrate(), {"mating_cte": 6.0})

    def test_non_boolean_programme_flag_is_refused(self):
        with self.assertRaises(ValueError):
            assess_item(substrate(), {"evaluation_programme_available": "yes"})


class SelectionRollupTests(unittest.TestCase):
    def test_a_clean_bill_of_materials_is_complete(self):
        result = assess_selection({"items": [substrate(), adhesive(), wire()]})
        self.assertTrue(result["selection_complete"])
        self.assertTrue(result["buildable"])
        self.assertEqual(result["item_count"], 3)
        self.assertAlmostEqual(result["settled_fraction"], 1.0, places=9)

    def test_one_open_item_leaves_the_selection_incomplete_but_buildable(self):
        result = assess_selection(
            {"items": [substrate(), adhesive(), wire(pad_metal="aluminium")]}
        )
        self.assertFalse(result["selection_complete"])
        self.assertTrue(result["buildable"])
        self.assertEqual(result["items_requiring_evaluation"], ["bonding-wire-25um"])

    def test_one_refused_item_makes_the_selection_unbuildable(self):
        result = assess_selection({"items": [substrate(), adhesive(cvcm_percent=0.9)]})
        self.assertFalse(result["buildable"])
        self.assertEqual(result["refused_items"], ["silver-filled-die-attach"])
        self.assertAlmostEqual(result["settled_fraction"], 0.5, places=9)

    def test_duplicate_candidate_names_are_refused(self):
        with self.assertRaises(ValueError):
            assess_selection({"items": [substrate(), substrate()]})

    def test_empty_bill_of_materials_is_refused(self):
        with self.assertRaises(ValueError):
            assess_selection({"items": []})

    def test_missing_items_key_is_refused(self):
        with self.assertRaises(ValueError):
            assess_selection({"temperature_excursion_k": 100.0})

    def test_context_declared_alongside_the_items_reaches_every_item(self):
        result = assess_selection(
            {
                "items": [substrate(cte_ppm_per_k=10.0)],
                "mating_cte_ppm_per_k": 5.0,
                "temperature_excursion_k": 100.0,
            }
        )
        self.assertEqual(result["refused_items"], ["alumina-substrate"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
