#!/usr/bin/env python3
"""Gate 3 contract test for e2040-data-sheet-detailed-design-update.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_data_sheet_detailed_design_update.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_data_sheet_detailed_design_update_logic import (  # noqa: E402
    CANONICAL_UNITS,
    PARAMETER_KINDS,
    budget_margin,
    canonical_unit,
    categorize_movement,
    meets_budget,
    normalize_direction,
    normalize_kind,
    refresh_data_sheet,
    relative_change,
    to_canonical,
    validate_data_sheet,
    validate_figures,
)


def base_sheet():
    return [
        {
            "id": "t-clk-to-q",
            "kind": "timing",
            "preliminary": 4.0,
            "unit": "ns",
            "budget": 5.0,
            "direction": "not-to-exceed",
        },
        {
            "id": "p-core",
            "kind": "power",
            "preliminary": 800.0,
            "unit": "mW",
            "budget": 1000.0,
            "direction": "max",
        },
        {"id": "a-die", "kind": "area", "preliminary": 12.0, "unit": "mm2"},
        {
            "id": "f-clk",
            "kind": "frequency",
            "preliminary": 100.0,
            "unit": "MHz",
            "budget": 80.0,
            "direction": "at-least",
        },
    ]


def base_figures():
    return [
        {"id": "t-clk-to-q", "value": 4.1, "unit": "ns", "source": "extraction"},
        {"id": "p-core", "value": 0.82, "unit": "W", "source": "simulation"},
        {"id": "a-die", "value": 12.5, "unit": "mm2", "source": "synthesis"},
        {"id": "f-clk", "value": 98.0, "unit": "MHz", "source": "extraction"},
    ]


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestKindsAndUnits(unittest.TestCase):
    def test_delay_folds_to_timing(self):
        self.assertEqual(normalize_kind("Delay"), "timing")

    def test_weight_folds_to_mass(self):
        self.assertEqual(normalize_kind("weight"), "mass")

    def test_unknown_kind_rejected(self):
        with self.assertRaises(ValueError):
            normalize_kind("radiation")

    def test_every_kind_has_a_canonical_unit(self):
        for kind in PARAMETER_KINDS:
            self.assertIn(kind, CANONICAL_UNITS)
        self.assertEqual(canonical_unit("timing"), "s")

    def test_nanoseconds_fold_onto_seconds(self):
        self.assertAlmostEqual(to_canonical("timing", 4.0, "ns"), 4e-9, places=18)

    def test_milliwatts_fold_onto_watts(self):
        self.assertAlmostEqual(to_canonical("power", 800.0, "mW"), 0.8, places=9)

    def test_megahertz_folds_onto_hertz(self):
        self.assertAlmostEqual(to_canonical("frequency", 100.0, "MHz"), 1e8, places=3)

    def test_a_unit_from_another_kind_rejected(self):
        with self.assertRaises(ValueError):
            to_canonical("power", 1.0, "ns")

    def test_a_non_numeric_value_rejected(self):
        with self.assertRaises(ValueError):
            to_canonical("timing", "four", "ns")

    def test_a_boolean_value_rejected(self):
        with self.assertRaises(ValueError):
            to_canonical("timing", True, "ns")


class TestMovement(unittest.TestCase):
    def test_a_small_move_is_confirmed(self):
        self.assertEqual(categorize_movement(100.0, 102.0, 0.05), "confirmed")

    def test_a_move_landing_exactly_on_tolerance_is_confirmed(self):
        self.assertEqual(categorize_movement(100.0, 105.0, 0.05), "confirmed")

    def test_a_big_move_upward_is_increased(self):
        self.assertEqual(categorize_movement(100.0, 140.0, 0.05), "increased")

    def test_a_big_move_downward_is_decreased(self):
        self.assertEqual(categorize_movement(100.0, 60.0, 0.05), "decreased")

    def test_relative_change_is_signed(self):
        self.assertAlmostEqual(relative_change(100.0, 110.0), 0.1, places=9)

    def test_change_against_a_zero_estimate_rejected(self):
        with self.assertRaises(ValueError):
            relative_change(0.0, 1.0)

    def test_a_negative_tolerance_rejected(self):
        with self.assertRaises(ValueError):
            categorize_movement(100.0, 110.0, -0.1)


class TestBudgets(unittest.TestCase):
    def test_a_figure_under_a_ceiling_meets_it(self):
        self.assertTrue(meets_budget(4.0, 5.0, "not-to-exceed"))

    def test_a_figure_exactly_on_a_ceiling_meets_it(self):
        self.assertTrue(meets_budget(3 * 0.1, 0.3, "not-to-exceed"))

    def test_a_figure_over_a_ceiling_fails_it(self):
        self.assertFalse(meets_budget(6.0, 5.0, "maximum"))

    def test_a_figure_under_a_floor_fails_it(self):
        self.assertFalse(meets_budget(70.0, 80.0, "at-least"))

    def test_a_figure_exactly_on_a_floor_meets_it(self):
        self.assertTrue(meets_budget(3 * 0.1, 0.3, "minimum"))

    def test_margin_against_a_ceiling_is_positive_when_met(self):
        self.assertAlmostEqual(budget_margin(4.0, 5.0, "not-to-exceed"), 0.2, places=9)

    def test_margin_against_a_floor_is_negative_when_missed(self):
        self.assertAlmostEqual(budget_margin(70.0, 80.0, "at-least"), -0.125, places=9)

    def test_margin_against_a_zero_budget_rejected(self):
        with self.assertRaises(ValueError):
            budget_margin(1.0, 0.0, "not-to-exceed")

    def test_unknown_direction_rejected(self):
        with self.assertRaises(ValueError):
            normalize_direction("thereabouts")

    def test_direction_underscores_fold(self):
        self.assertEqual(normalize_direction("NOT_TO_EXCEED"), "not-to-exceed")


class TestValidation(unittest.TestCase):
    def test_the_sheet_resolves_onto_canonical_units(self):
        resolved = validate_data_sheet(base_sheet())
        self.assertAlmostEqual(resolved[0]["preliminary"], 4e-9, places=18)
        self.assertEqual(resolved[0]["unit"], "s")

    def test_duplicate_parameter_id_rejected(self):
        entries = base_sheet()
        entries.append(dict(entries[0]))
        with self.assertRaises(ValueError):
            validate_data_sheet(entries)

    def test_unknown_parameter_key_rejected(self):
        entries = base_sheet()
        entries[0]["owner"] = "someone"
        with self.assertRaises(ValueError):
            validate_data_sheet(entries)

    def test_a_direction_without_a_budget_rejected(self):
        with self.assertRaises(ValueError):
            validate_data_sheet(
                [
                    {
                        "id": "x",
                        "kind": "timing",
                        "preliminary": 1.0,
                        "unit": "ns",
                        "direction": "max",
                    }
                ]
            )

    def test_a_parameter_without_a_unit_rejected(self):
        with self.assertRaises(ValueError):
            validate_data_sheet([{"id": "x", "kind": "timing", "preliminary": 1.0}])

    def test_duplicate_figure_rejected(self):
        entries = base_figures()
        entries.append(dict(entries[0]))
        with self.assertRaises(ValueError):
            validate_figures(entries)

    def test_unknown_figure_source_rejected(self):
        entries = base_figures()
        entries[0]["source"] = "guesswork"
        with self.assertRaises(ValueError):
            validate_figures(entries)

    def test_non_boolean_provisional_rejected(self):
        entries = base_figures()
        entries[0]["provisional"] = "yes"
        with self.assertRaises(ValueError):
            validate_figures(entries)

    def test_non_list_sheet_rejected(self):
        with self.assertRaises(ValueError):
            validate_data_sheet({"id": "x"})


class TestRefresh(unittest.TestCase):
    def test_a_fully_refreshed_sheet_is_acceptable(self):
        result = refresh_data_sheet(base_sheet(), base_figures())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_the_refresh_fraction_reaches_one(self):
        result = refresh_data_sheet(base_sheet(), base_figures())
        self.assertAlmostEqual(result["refresh_fraction"], 1.0, places=9)

    def test_a_parameter_with_no_figure_is_reported(self):
        figures = base_figures()[:-1]
        result = refresh_data_sheet(base_sheet(), figures, refresh_goal=0.0)
        self.assertIn("parameter-not-refreshed", codes(result))
        self.assertEqual(result["not_refreshed"], ["f-clk"])

    def test_the_refresh_fraction_counts_the_unrefreshed_parameter(self):
        result = refresh_data_sheet(
            base_sheet(), base_figures()[:-1], refresh_goal=0.0
        )
        self.assertAlmostEqual(result["refresh_fraction"], 0.75, places=9)

    def test_a_goal_met_exactly_does_not_fail_the_sheet(self):
        result = refresh_data_sheet(
            base_sheet(), base_figures()[:3], refresh_goal=3 / 4
        )
        self.assertNotIn("refresh-goal-missed", codes(result))

    def test_a_missed_refresh_goal_is_reported(self):
        result = refresh_data_sheet(base_sheet(), base_figures()[:2])
        self.assertIn("refresh-goal-missed", codes(result))

    def test_a_refreshed_figure_breaking_its_budget_is_reported(self):
        figures = base_figures()
        figures[0]["value"] = 6.0
        result = refresh_data_sheet(base_sheet(), figures)
        self.assertIn("budget-broken-by-refreshed-figure", codes(result))

    def test_a_floor_budget_broken_by_the_refreshed_figure_is_reported(self):
        figures = base_figures()
        figures[3]["value"] = 70.0
        result = refresh_data_sheet(base_sheet(), figures)
        self.assertIn("budget-broken-by-refreshed-figure", codes(result))

    def test_a_figure_exactly_on_its_ceiling_is_not_reported(self):
        figures = base_figures()
        figures[0]["value"] = 5.0
        result = refresh_data_sheet(base_sheet(), figures)
        self.assertNotIn("budget-broken-by-refreshed-figure", codes(result))

    def test_a_figure_for_an_unknown_parameter_is_reported(self):
        figures = base_figures()
        figures.append({"id": "t-setup", "value": 1.0, "unit": "ns"})
        result = refresh_data_sheet(base_sheet(), figures)
        self.assertIn("figure-without-parameter", codes(result))

    def test_a_provisional_figure_is_reported(self):
        figures = base_figures()
        figures[1]["provisional"] = True
        result = refresh_data_sheet(base_sheet(), figures)
        self.assertIn("figure-still-provisional", codes(result))

    def test_a_figure_still_sourced_from_an_estimate_is_reported(self):
        figures = base_figures()
        figures[2]["source"] = "estimate"
        result = refresh_data_sheet(base_sheet(), figures)
        self.assertIn("figure-still-an-estimate", codes(result))

    def test_a_unit_change_between_sheet_and_figure_is_folded(self):
        result = refresh_data_sheet(base_sheet(), base_figures())
        power = [r for r in result["parameters"] if r["id"] == "p-core"][0]
        self.assertAlmostEqual(power["refreshed"], 0.82, places=9)
        self.assertEqual(power["movement"], "confirmed")

    def test_a_large_movement_is_grouped_as_increased(self):
        figures = base_figures()
        figures[2]["value"] = 18.0
        result = refresh_data_sheet(base_sheet(), figures)
        area = [r for r in result["parameters"] if r["id"] == "a-die"][0]
        self.assertEqual(area["movement"], "increased")

    def test_an_empty_sheet_rejected(self):
        with self.assertRaises(ValueError):
            refresh_data_sheet([], [])

    def test_a_goal_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            refresh_data_sheet(base_sheet(), base_figures(), refresh_goal=1.5)


if __name__ == "__main__":
    unittest.main()
