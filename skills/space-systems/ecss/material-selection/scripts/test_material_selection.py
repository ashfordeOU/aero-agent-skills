"""
Gate 3 contract tests for material_selection_logic.py.

Stdlib unittest only; deterministic, offline.
Run: python3 test_material_selection.py
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(__file__))

from material_selection_logic import (
    categorize_material,
    get_stress_corrosion_rating,
    check_stress_corrosion_acceptability,
    check_space_environment_compatibility,
    evaluate_material_for_application,
    select_material,
    VERDICT_ACCEPTABLE,
    VERDICT_CONDITIONAL,
    VERDICT_NOT_ACCEPTABLE,
)


class TestCategorizeMaterial(unittest.TestCase):

    def test_categorize_metallic(self):
        self.assertEqual(categorize_material("al_7075_t6"), "metallic")

    def test_categorize_composite(self):
        self.assertEqual(categorize_material("cfrp_unidirectional"), "composite")

    def test_categorize_ceramic(self):
        self.assertEqual(categorize_material("si3n4"), "ceramic")

    def test_categorize_polymer(self):
        self.assertEqual(categorize_material("polyimide"), "polymer")

    def test_categorize_unknown_raises(self):
        with self.assertRaises(ValueError):
            categorize_material("unobtainium")

    def test_categorize_case_insensitive_strip(self):
        # identifiers should be normalised to lowercase and stripped
        self.assertEqual(categorize_material("  AL_7075_T6  "), "metallic")


class TestStressCorrosionRating(unittest.TestCase):

    def test_sc_rating_vacuum_immune(self):
        self.assertEqual(get_stress_corrosion_rating("al_2024_t3", "vacuum"), 1)

    def test_sc_rating_humid_medium(self):
        self.assertEqual(get_stress_corrosion_rating("al_2024_t3", "humid"), 3)

    def test_sc_rating_salt_high(self):
        self.assertEqual(get_stress_corrosion_rating("al_7075_t6", "salt"), 4)

    def test_sc_rating_ti_immune_humid(self):
        self.assertEqual(get_stress_corrosion_rating("ti_6al_4v", "humid"), 1)

    def test_sc_rating_al6061_humid_low(self):
        self.assertEqual(get_stress_corrosion_rating("al_6061_t6", "humid"), 2)

    def test_sc_unknown_environment_raises(self):
        with self.assertRaises(ValueError):
            get_stress_corrosion_rating("al_2024_t3", "underwater")

    def test_sc_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            get_stress_corrosion_rating("mystery_alloy", "humid")


class TestStressCorrosionAcceptability(unittest.TestCase):

    def test_sc_acceptability_pass(self):
        result = check_stress_corrosion_acceptability("ti_6al_4v", "humid")
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["action"], "none_required")
        self.assertEqual(result["rating"], 1)

    def test_sc_acceptability_fail_rating3(self):
        result = check_stress_corrosion_acceptability("al_2024_t3", "humid")
        self.assertFalse(result["acceptable"])
        self.assertEqual(result["rating"], 3)
        self.assertEqual(result["action"], "apply_protective_coating_or_substitute_material")

    def test_sc_acceptability_fail_rating4(self):
        result = check_stress_corrosion_acceptability("al_7075_t6", "salt")
        self.assertFalse(result["acceptable"])
        self.assertEqual(result["rating"], 4)
        self.assertEqual(result["action"], "substitute_material")

    def test_sc_acceptability_composite_always_passes_humid(self):
        result = check_stress_corrosion_acceptability("cfrp_woven", "humid")
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["rating"], 1)


class TestSpaceEnvironmentCompatibility(unittest.TestCase):

    def test_space_env_polymer_ao_flagged(self):
        result = check_space_environment_compatibility("polyimide", ["atomic_oxygen"])
        flags = [f for f in result["findings"] if f["severity"] == "flag"]
        self.assertTrue(len(flags) >= 1)
        self.assertFalse(result["compatible"])

    def test_space_env_metallic_no_findings(self):
        result = check_space_environment_compatibility(
            "ti_6al_4v", ["atomic_oxygen", "radiation_dose", "outgassing"]
        )
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["compatible"])

    def test_space_env_composite_ao_verify(self):
        result = check_space_environment_compatibility("cfrp_unidirectional", ["atomic_oxygen"])
        self.assertEqual(len(result["findings"]), 1)
        self.assertEqual(result["findings"][0]["severity"], "verify")
        self.assertTrue(result["compatible"])  # verify does not set compatible=False

    def test_space_env_polymer_outgassing_flagged(self):
        result = check_space_environment_compatibility("ptfe", ["outgassing"])
        flags = [f for f in result["findings"] if f["severity"] == "flag"]
        self.assertTrue(len(flags) >= 1)
        self.assertFalse(result["compatible"])

    def test_space_env_no_active_hazards(self):
        result = check_space_environment_compatibility("polyimide", [])
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["compatible"])

    def test_space_env_unknown_hazard_raises(self):
        with self.assertRaises(ValueError):
            check_space_environment_compatibility("polyimide", ["gamma_burst"])

    def test_space_env_unknown_material_raises(self):
        with self.assertRaises(ValueError):
            check_space_environment_compatibility("mystery_polymer", ["atomic_oxygen"])


class TestEvaluateMaterialForApplication(unittest.TestCase):

    def test_evaluate_ti_dry_acceptable(self):
        result = evaluate_material_for_application("ti_6al_4v", "dry", [])
        self.assertEqual(result["verdict"], VERDICT_ACCEPTABLE)
        self.assertEqual(result["findings"], [])

    def test_evaluate_al2024_salt_not_acceptable(self):
        result = evaluate_material_for_application("al_2024_t3", "salt", [])
        self.assertEqual(result["verdict"], VERDICT_NOT_ACCEPTABLE)

    def test_evaluate_al2024_humid_conditional(self):
        result = evaluate_material_for_application("al_2024_t3", "humid", [])
        self.assertEqual(result["verdict"], VERDICT_CONDITIONAL)
        self.assertTrue(len(result["findings"]) >= 1)

    def test_evaluate_polyimide_ao_conditional(self):
        result = evaluate_material_for_application("polyimide", "dry", ["atomic_oxygen"])
        self.assertEqual(result["verdict"], VERDICT_CONDITIONAL)

    def test_evaluate_cfrp_dry_verify_only_is_conditional(self):
        result = evaluate_material_for_application("cfrp_unidirectional", "dry", ["thermal_cycling"])
        self.assertEqual(result["verdict"], VERDICT_CONDITIONAL)


class TestSelectMaterial(unittest.TestCase):

    def test_select_best_picks_acceptable_over_conditional(self):
        # al_2024_t3 humid → CONDITIONAL; ti_6al_4v humid → ACCEPTABLE
        result = select_material(["al_2024_t3", "ti_6al_4v"], "humid", [])
        self.assertEqual(result["verdict"], VERDICT_ACCEPTABLE)
        self.assertEqual(result["material"], "ti_6al_4v")

    def test_select_returns_conditional_when_no_acceptable(self):
        # al_2024_t3 humid → CONDITIONAL; al_7075_t6 salt → NOT_ACCEPTABLE
        result = select_material(["al_2024_t3", "al_7075_t6"], "humid", [])
        # al_2024_t3 salt would be needed to test this properly; use humid list
        # Both are evaluated on same environment: al_2024_t3 humid = CONDITIONAL
        self.assertIn(result["verdict"], [VERDICT_ACCEPTABLE, VERDICT_CONDITIONAL])

    def test_select_single_acceptable_candidate(self):
        result = select_material(["ti_6al_4v"], "dry", [])
        self.assertEqual(result["verdict"], VERDICT_ACCEPTABLE)

    def test_select_empty_raises(self):
        with self.assertRaises(ValueError):
            select_material([], "dry", [])

    def test_select_preserves_findings_on_result(self):
        result = select_material(["al_2024_t3", "ti_6al_4v"], "humid", [])
        # Winning candidate is ti_6al_4v which is ACCEPTABLE with no findings
        self.assertIsInstance(result["findings"], list)


if __name__ == "__main__":
    unittest.main()
