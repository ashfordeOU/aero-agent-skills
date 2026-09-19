"""Contract tests for the cleaning-process selection logic."""

import unittest

from q7001_cleaning_process_selection_logic import (
    CONTAMINANT_TYPES,
    PROCESSES,
    admissible_processes,
    exclusion_reasons,
    geometry_admissible,
    level_capability_score,
    material_compatible,
    process_profile,
    rank_processes,
    removal_effectiveness,
    residue_admissible,
    score_process,
    select_cleaning_process,
    sensitivity_admissible,
    validate_hardware,
)


def _hardware(**overrides):
    item = {
        "hardware_id": "BRACKET-A",
        "materials": ["aluminium-7075", "stainless-316"],
        "contaminant": "particulate",
        "required_level_rank": 2,
    }
    item.update(overrides)
    return item


class ProfileTests(unittest.TestCase):
    def test_every_process_covers_every_contaminant(self):
        for name, profile in PROCESSES.items():
            for contaminant in CONTAMINANT_TYPES:
                self.assertIn(contaminant, profile["removal"], name)

    def test_known_process_returns_a_profile(self):
        self.assertIn("removal", process_profile("plasma"))

    def test_unknown_process_rejected(self):
        with self.assertRaises(ValueError):
            process_profile("laser-ablation")

    def test_blank_process_name_rejected(self):
        with self.assertRaises(ValueError):
            process_profile("   ")


class HardwareValidationTests(unittest.TestCase):
    def test_defaults_are_applied(self):
        item = validate_hardware(_hardware())
        self.assertFalse(item["blind_cavities"])
        self.assertTrue(item["immersion_permitted"])

    def test_missing_key_rejected(self):
        broken = _hardware()
        del broken["contaminant"]
        with self.assertRaises(ValueError):
            validate_hardware(broken)

    def test_unknown_contaminant_rejected(self):
        with self.assertRaises(ValueError):
            validate_hardware(_hardware(contaminant="radioactive-dust"))

    def test_empty_material_list_rejected(self):
        with self.assertRaises(ValueError):
            validate_hardware(_hardware(materials=[]))

    def test_negative_level_rank_rejected(self):
        with self.assertRaises(ValueError):
            validate_hardware(_hardware(required_level_rank=-1))

    def test_non_integer_level_rank_rejected(self):
        with self.assertRaises(ValueError):
            validate_hardware(_hardware(required_level_rank=2.5))

    def test_non_mapping_hardware_rejected(self):
        with self.assertRaises(ValueError):
            validate_hardware(["BRACKET-A"])


class ScreeningTests(unittest.TestCase):
    def test_metal_bracket_is_material_compatible_with_aqueous(self):
        self.assertTrue(material_compatible("aqueous-immersion", _hardware()))

    def test_honeycomb_core_blocks_aqueous_immersion(self):
        item = _hardware(materials=["aluminium-7075", "honeycomb-core"])
        self.assertFalse(material_compatible("aqueous-immersion", item))

    def test_soft_gold_plating_blocks_co2_snow(self):
        item = _hardware(materials=["soft-gold-plating"])
        self.assertFalse(material_compatible("co2-snow", item))

    def test_blind_cavity_blocks_a_line_of_sight_process(self):
        self.assertFalse(geometry_admissible("co2-snow", _hardware(blind_cavities=True)))

    def test_blind_cavity_allows_plasma(self):
        self.assertTrue(geometry_admissible("plasma", _hardware(blind_cavities=True)))

    def test_no_immersion_blocks_every_wet_process(self):
        item = _hardware(immersion_permitted=False)
        self.assertFalse(geometry_admissible("aqueous-immersion", item))
        self.assertFalse(geometry_admissible("solvent-wipe", item))

    def test_no_vacuum_facility_blocks_plasma(self):
        self.assertFalse(geometry_admissible("plasma", _hardware(vacuum_permitted=False)))

    def test_optical_surface_refuses_an_abrasive_wet_process(self):
        self.assertFalse(sensitivity_admissible("solvent-wipe", _hardware(optically_sensitive=True)))

    def test_electrostatic_part_refuses_co2_snow(self):
        item = _hardware(electrostatic_sensitive=True)
        self.assertFalse(sensitivity_admissible("co2-snow", item))

    def test_residue_free_process_is_always_residue_admissible(self):
        self.assertTrue(residue_admissible("plasma", _hardware()))

    def test_residue_leaving_process_is_fine_by_default(self):
        self.assertTrue(residue_admissible("solvent-wipe", _hardware()))

    def test_residue_free_finish_blocks_a_residue_leaving_process(self):
        item = _hardware(residue_free_required=True)
        self.assertFalse(residue_admissible("solvent-wipe", item))
        self.assertFalse(residue_admissible("aqueous-immersion", item))

    def test_declared_rinse_step_restores_a_residue_leaving_process(self):
        item = _hardware(residue_free_required=True, post_rinse_step=True)
        self.assertTrue(residue_admissible("aqueous-immersion", item))

    def test_exclusion_reasons_are_collected(self):
        item = _hardware(
            materials=["honeycomb-core"], immersion_permitted=False, blind_cavities=True
        )
        reasons = exclusion_reasons("aqueous-immersion", item)
        self.assertGreaterEqual(len(reasons), 2)

    def test_admissible_set_excludes_the_blocked_processes(self):
        item = _hardware(vacuum_permitted=False, immersion_permitted=False)
        self.assertEqual(admissible_processes(item), ["co2-snow"])


class ScoringTests(unittest.TestCase):
    def test_co2_snow_is_the_particulate_specialist(self):
        self.assertAlmostEqual(removal_effectiveness("co2-snow", "particulate"), 0.90)

    def test_plasma_is_the_molecular_specialist(self):
        self.assertAlmostEqual(removal_effectiveness("plasma", "molecular-film"), 0.95)

    def test_unknown_contaminant_has_no_effectiveness(self):
        with self.assertRaises(ValueError):
            removal_effectiveness("plasma", "soot")

    def test_process_reaching_the_level_scores_unity_capability(self):
        self.assertAlmostEqual(level_capability_score("plasma", 3), 1.0, places=9)

    def test_process_short_of_the_level_is_tapered(self):
        self.assertAlmostEqual(level_capability_score("solvent-wipe", 0), 0.5, places=9)

    def test_capability_score_never_goes_negative(self):
        value = level_capability_score("solvent-wipe", 0)
        self.assertGreaterEqual(value, 0.0)

    def test_wet_process_carries_a_penalty(self):
        wet = score_process("solvent-wipe", _hardware())
        self.assertAlmostEqual(wet, 0.65 - 0.10, places=9)

    def test_abrasive_on_a_soft_surface_carries_a_penalty(self):
        plain = score_process("co2-snow", _hardware())
        soft = score_process("co2-snow", _hardware(soft_surface=True))
        self.assertAlmostEqual(plain - soft, 0.15, places=9)

    def test_scoring_an_inadmissible_process_is_refused(self):
        with self.assertRaises(ValueError):
            score_process("plasma", _hardware(vacuum_permitted=False))

    def test_ranking_is_ordered_best_first(self):
        ranked = rank_processes(_hardware())
        values = [value for _name, value in ranked]
        self.assertEqual(values, sorted(values, reverse=True))


class SelectionTests(unittest.TestCase):
    def test_particulate_on_a_plain_bracket_picks_co2_snow(self):
        result = select_cleaning_process(_hardware())
        self.assertEqual(result["selected"], "co2-snow")
        self.assertTrue(result["decided"])

    def test_ionic_salt_picks_the_aqueous_route(self):
        result = select_cleaning_process(_hardware(contaminant="ionic-salt"))
        self.assertEqual(result["selected"], "aqueous-immersion")

    def test_molecular_film_in_a_blind_cavity_picks_plasma(self):
        result = select_cleaning_process(
            _hardware(contaminant="molecular-film", blind_cavities=True)
        )
        self.assertEqual(result["selected"], "plasma")

    def test_rejected_processes_carry_their_reasons(self):
        result = select_cleaning_process(_hardware(optically_sensitive=True))
        self.assertIn("solvent-wipe", result["rejected"])
        self.assertTrue(result["rejected"]["solvent-wipe"])

    def test_no_admissible_process_is_refused_not_defaulted(self):
        item = _hardware(
            materials=["honeycomb-core", "soft-gold-plating"],
            vacuum_permitted=False,
            immersion_permitted=False,
        )
        result = select_cleaning_process(item)
        self.assertIsNone(result["selected"])
        self.assertFalse(result["decided"])
        self.assertEqual(len(result["findings"]), 1)

    def test_level_shortfall_is_reported_on_the_winner(self):
        item = _hardware(
            contaminant="machining-oil",
            required_level_rank=0,
            vacuum_permitted=False,
            electrostatic_sensitive=True,
        )
        result = select_cleaning_process(item)
        self.assertEqual(result["selected"], "aqueous-immersion")
        self.assertTrue(any("does not reach" in note for note in result["findings"]))

    def test_selected_score_matches_the_top_of_the_ranking(self):
        result = select_cleaning_process(_hardware())
        self.assertAlmostEqual(result["selected_score"], result["ranked"][0][1], places=12)

    def test_every_process_is_either_ranked_or_rejected(self):
        result = select_cleaning_process(_hardware())
        named = set(name for name, _value in result["ranked"]) | set(result["rejected"])
        self.assertEqual(named, set(PROCESSES))

    def test_non_mapping_input_rejected(self):
        with self.assertRaises(ValueError):
            select_cleaning_process("BRACKET-A")


if __name__ == "__main__":
    unittest.main()
