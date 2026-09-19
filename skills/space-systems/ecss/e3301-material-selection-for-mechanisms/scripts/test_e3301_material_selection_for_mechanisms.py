#!/usr/bin/env python3
"""Contract test for mechanism material selection (offline)."""

import copy
import unittest

from e3301_material_selection_for_mechanisms_logic import (
    ALLOWABLE_BASES,
    DEFAULT_SELECTION_POLICY,
    LOAD_PATHS,
    OUTCOME_ACCEPTED,
    OUTCOME_ACTION,
    OUTCOME_REJECTED,
    SCC_CATEGORIES,
    SELECTION_ROUTES,
    assess_material_selection,
    assess_stress_corrosion,
    design_allowable_mpa,
    evaluate_candidate,
    screen_outgassing,
    temperature_rating_holds,
    validate_selection_policy,
)

JUSTIFICATION = "alloy used in the temper with the documented resistance rating"

ENVELOPE = {
    "qualification_min_temperature_c": -80.0,
    "qualification_max_temperature_c": 105.0,
}


def candidate(
    name,
    route="declared-list",
    total_mass_loss_percent=0.4,
    collected_volatile_condensable_percent=0.02,
    recovered_mass_loss_percent=0.3,
    stress_corrosion_category="low",
    stress_corrosion_justification="",
    allowable_basis="a-basis",
    load_path="single",
    typical_strength_mpa=480.0,
    min_service_temperature_c=-150.0,
    max_service_temperature_c=180.0,
):
    return {
        "name": name,
        "route": route,
        "total_mass_loss_percent": total_mass_loss_percent,
        "collected_volatile_condensable_percent":
            collected_volatile_condensable_percent,
        "recovered_mass_loss_percent": recovered_mass_loss_percent,
        "stress_corrosion_category": stress_corrosion_category,
        "stress_corrosion_justification": stress_corrosion_justification,
        "allowable_basis": allowable_basis,
        "load_path": load_path,
        "typical_strength_mpa": typical_strength_mpa,
        "min_service_temperature_c": min_service_temperature_c,
        "max_service_temperature_c": max_service_temperature_c,
    }


GOOD_CASE = {
    "envelope": ENVELOPE,
    "candidates": [
        candidate("bearing-race-steel"),
        candidate("housing-alloy", allowable_basis="s-basis",
                  load_path="redundant", typical_strength_mpa=310.0),
    ],
}


class PolicyTests(unittest.TestCase):
    def test_default_policy_validates(self):
        self.assertIs(
            validate_selection_policy(DEFAULT_SELECTION_POLICY),
            DEFAULT_SELECTION_POLICY,
        )

    def test_every_route_is_named(self):
        self.assertEqual(len(SELECTION_ROUTES), 3)
        self.assertIn("new-material", SELECTION_ROUTES)

    def test_every_allowable_basis_is_named(self):
        self.assertEqual(set(ALLOWABLE_BASES),
                         {"a-basis", "b-basis", "s-basis", "typical"})

    def test_every_load_path_and_category_is_named(self):
        self.assertEqual(set(LOAD_PATHS), {"single", "redundant"})
        self.assertIn("high", SCC_CATEGORIES)

    def test_non_mapping_policy_rejected(self):
        with self.assertRaises(ValueError):
            validate_selection_policy("default")

    def test_knockdown_above_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_SELECTION_POLICY)
        broken["allowable_knockdown"]["typical"] = 1.2
        with self.assertRaises(ValueError):
            validate_selection_policy(broken)

    def test_knockdown_missing_a_basis_rejected(self):
        broken = copy.deepcopy(DEFAULT_SELECTION_POLICY)
        del broken["allowable_knockdown"]["b-basis"]
        with self.assertRaises(ValueError):
            validate_selection_policy(broken)

    def test_unknown_single_path_basis_rejected(self):
        broken = copy.deepcopy(DEFAULT_SELECTION_POLICY)
        broken["bases_allowed_on_a_single_load_path"] = ("guessed",)
        with self.assertRaises(ValueError):
            validate_selection_policy(broken)


class OutgassingTests(unittest.TestCase):
    def test_a_clean_material_passes(self):
        result = screen_outgassing(0.4, 0.02, 0.3)
        self.assertTrue(result["passes"])
        self.assertEqual(result["findings"], [])

    def test_values_exactly_on_the_limits_pass(self):
        result = screen_outgassing(1.0, 0.1, 1.0)
        self.assertTrue(result["passes"])

    def test_excess_total_mass_loss_fails(self):
        result = screen_outgassing(1.4, 0.02)
        self.assertFalse(result["total_mass_loss_ok"])
        self.assertFalse(result["passes"])

    def test_excess_condensable_fails(self):
        result = screen_outgassing(0.4, 0.3)
        self.assertFalse(result["condensable_ok"])
        self.assertTrue(any("condensable" in f for f in result["findings"]))

    def test_recovered_mass_loss_is_optional(self):
        result = screen_outgassing(0.4, 0.02)
        self.assertIsNone(result["recovered_mass_loss_ok"])
        self.assertTrue(result["passes"])

    def test_recovered_above_total_mass_loss_rejected(self):
        with self.assertRaises(ValueError):
            screen_outgassing(0.4, 0.02, 0.9)

    def test_negative_condensable_rejected(self):
        with self.assertRaises(ValueError):
            screen_outgassing(0.4, -0.01)

    def test_non_numeric_mass_loss_rejected(self):
        with self.assertRaises(ValueError):
            screen_outgassing("low", 0.02)


class StressCorrosionTests(unittest.TestCase):
    def test_a_low_category_needs_no_justification(self):
        result = assess_stress_corrosion("low")
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_a_moderate_category_needs_no_justification(self):
        self.assertTrue(assess_stress_corrosion("moderate")["acceptable"])

    def test_a_susceptible_category_with_a_justification_is_carried(self):
        result = assess_stress_corrosion("high", JUSTIFICATION)
        self.assertTrue(result["acceptable"])
        self.assertTrue(result["findings"])

    def test_a_susceptible_category_without_a_justification_is_refused(self):
        result = assess_stress_corrosion("high", "")
        self.assertFalse(result["acceptable"])

    def test_a_token_justification_does_not_count(self):
        self.assertFalse(assess_stress_corrosion("high", "fine")["acceptable"])

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            assess_stress_corrosion("unknown", JUSTIFICATION)


class DesignAllowableTests(unittest.TestCase):
    def test_a_statistical_basis_is_taken_as_written(self):
        self.assertAlmostEqual(
            design_allowable_mpa(480.0, "a-basis", "single"), 480.0, places=9
        )

    def test_a_typical_value_is_knocked_down(self):
        self.assertAlmostEqual(
            design_allowable_mpa(480.0, "typical", "redundant"), 360.0, places=9
        )

    def test_an_s_basis_value_carries_its_own_factor(self):
        self.assertAlmostEqual(
            design_allowable_mpa(480.0, "s-basis", "single"), 432.0, places=9
        )

    def test_a_b_basis_value_is_refused_on_a_single_load_path(self):
        with self.assertRaises(ValueError):
            design_allowable_mpa(480.0, "b-basis", "single")

    def test_a_b_basis_value_is_allowed_on_a_redundant_path(self):
        self.assertAlmostEqual(
            design_allowable_mpa(480.0, "b-basis", "redundant"), 480.0, places=9
        )

    def test_a_typical_value_is_refused_on_a_single_load_path(self):
        with self.assertRaises(ValueError):
            design_allowable_mpa(480.0, "typical", "single")

    def test_zero_strength_rejected(self):
        with self.assertRaises(ValueError):
            design_allowable_mpa(0.0, "a-basis", "single")

    def test_unknown_load_path_rejected(self):
        with self.assertRaises(ValueError):
            design_allowable_mpa(480.0, "a-basis", "hopeful")


class TemperatureRatingTests(unittest.TestCase):
    def test_a_wide_rating_covers_the_envelope(self):
        result = temperature_rating_holds(-150.0, 180.0, ENVELOPE)
        self.assertTrue(result["holds"])

    def test_a_rating_exactly_on_both_ends_holds(self):
        result = temperature_rating_holds(-80.0, 105.0, ENVELOPE)
        self.assertTrue(result["holds"])

    def test_a_warm_floor_fails_the_cold_case(self):
        result = temperature_rating_holds(-40.0, 180.0, ENVELOPE)
        self.assertFalse(result["cold_ok"])
        self.assertTrue(any("cold case" in f for f in result["findings"]))

    def test_a_low_ceiling_fails_the_hot_case(self):
        result = temperature_rating_holds(-150.0, 80.0, ENVELOPE)
        self.assertFalse(result["hot_ok"])

    def test_an_inverted_rating_rejected(self):
        with self.assertRaises(ValueError):
            temperature_rating_holds(180.0, -150.0, ENVELOPE)

    def test_an_envelope_without_a_hot_case_rejected(self):
        with self.assertRaises(ValueError):
            temperature_rating_holds(
                -150.0, 180.0, {"qualification_min_temperature_c": -80.0}
            )


class CandidateTests(unittest.TestCase):
    def test_a_clean_candidate_is_accepted(self):
        result = evaluate_candidate(candidate("race-steel"), ENVELOPE)
        self.assertEqual(result["outcome"], OUTCOME_ACCEPTED)
        self.assertEqual(result["actions"], [])

    def test_a_new_material_owes_an_approval(self):
        result = evaluate_candidate(
            candidate("new-polymer", route="new-material"), ENVELOPE
        )
        self.assertEqual(result["outcome"], OUTCOME_ACTION)
        self.assertTrue(any("approval" in a for a in result["actions"]))

    def test_a_typical_allowable_on_a_redundant_path_owes_a_statistical_value(self):
        result = evaluate_candidate(
            candidate("bracket-alloy", allowable_basis="typical",
                      load_path="redundant"),
            ENVELOPE,
        )
        self.assertEqual(result["outcome"], OUTCOME_ACTION)
        self.assertAlmostEqual(result["design_allowable_mpa"], 360.0, places=9)

    def test_a_dirty_candidate_is_rejected(self):
        result = evaluate_candidate(
            candidate("wet-polymer", collected_volatile_condensable_percent=0.5),
            ENVELOPE,
        )
        self.assertEqual(result["outcome"], OUTCOME_REJECTED)
        self.assertFalse(result["outgassing_passes"])

    def test_an_unjustified_susceptible_alloy_is_rejected(self):
        result = evaluate_candidate(
            candidate("susceptible-alloy", stress_corrosion_category="high"),
            ENVELOPE,
        )
        self.assertEqual(result["outcome"], OUTCOME_REJECTED)
        self.assertFalse(result["stress_corrosion_acceptable"])

    def test_an_inadmissible_basis_is_reported_rather_than_raised(self):
        result = evaluate_candidate(
            candidate("fitting-alloy", allowable_basis="b-basis",
                      load_path="single"),
            ENVELOPE,
        )
        self.assertFalse(result["basis_admissible"])
        self.assertIsNone(result["design_allowable_mpa"])
        self.assertEqual(result["outcome"], OUTCOME_REJECTED)

    def test_a_narrow_temperature_rating_is_rejected(self):
        result = evaluate_candidate(
            candidate("cold-shy-grease", max_service_temperature_c=60.0), ENVELOPE
        )
        self.assertFalse(result["temperature_rating_holds"])
        self.assertEqual(result["outcome"], OUTCOME_REJECTED)

    def test_unknown_route_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_candidate(candidate("mystery", route="vendor-said-so"), ENVELOPE)

    def test_blank_candidate_name_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_candidate(candidate("  "), ENVELOPE)


class SelectionTests(unittest.TestCase):
    def test_a_clean_list_is_acceptable(self):
        result = assess_material_selection(GOOD_CASE)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["verdict"], "selection-acceptable")
        self.assertEqual(len(result["grouped"][OUTCOME_ACCEPTED]), 2)

    def test_an_open_action_holds_the_selection_open(self):
        case = copy.deepcopy(GOOD_CASE)
        case["candidates"].append(candidate("new-lubricant", route="new-material"))
        result = assess_material_selection(case)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["verdict"], "selection-open-actions")
        self.assertTrue(result["open_actions"])

    def test_a_rejection_outranks_an_open_action(self):
        case = copy.deepcopy(GOOD_CASE)
        case["candidates"].append(candidate("new-lubricant", route="new-material"))
        case["candidates"].append(
            candidate("wet-polymer", total_mass_loss_percent=3.0)
        )
        result = assess_material_selection(case)
        self.assertEqual(result["verdict"], "selection-not-acceptable")
        self.assertIn("wet-polymer", result["grouped"][OUTCOME_REJECTED])

    def test_duplicate_candidate_name_rejected(self):
        case = copy.deepcopy(GOOD_CASE)
        case["candidates"].append(candidate("bearing-race-steel"))
        with self.assertRaises(ValueError):
            assess_material_selection(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_material_selection("titanium")

    def test_missing_envelope_rejected(self):
        with self.assertRaises(ValueError):
            assess_material_selection({"candidates": [candidate("a")]})

    def test_empty_candidate_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_material_selection({"envelope": ENVELOPE, "candidates": []})


if __name__ == "__main__":
    unittest.main()
