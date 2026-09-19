#!/usr/bin/env python3
"""Gate 3 contract test for e2040-preliminary-device-data-sheet.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_preliminary_device_data_sheet.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_preliminary_device_data_sheet_logic import (  # noqa: E402
    CHARACTERISTIC_GROUPS,
    CONFIRMED,
    ELECTRICAL,
    ENVIRONMENTAL,
    MANDATORY_GROUPS,
    MEASUREMENT,
    PRELIMINARY,
    SIMULATION,
    TIMING,
    basis_supports_confirmation,
    evaluate_data_sheet,
    group_completeness,
    groups_present,
    meets_completeness_threshold,
    missing_mandatory_groups,
    normalize_basis,
    normalize_group,
    normalize_maturity,
    validate_characteristics,
    within_declared_range,
)


def base_sheet():
    return {
        "characteristics": [
            {
                "name": "supply-voltage",
                "group": "electrical",
                "value": 3.3,
                "unit": "V",
                "minimum": 3.0,
                "maximum": 3.6,
                "maturity": "preliminary",
                "basis": "simulation",
                "description": "nominal core supply the device expects",
            },
            {
                "name": "clock-frequency",
                "group": "timing",
                "value": 100.0,
                "unit": "MHz",
                "minimum": 0.0,
                "maximum": 120.0,
                "maturity": "preliminary",
                "basis": "estimate",
                "description": "highest clock the device is being designed for",
            },
            {
                "name": "command-set",
                "group": "functional",
                "value": "sixteen register-mapped commands",
                "maturity": "preliminary",
                "basis": "analysis",
                "description": "what a host can ask the device to do",
            },
            {
                "name": "total-dose-capability",
                "group": "environmental",
                "value": 100.0,
                "unit": "krad",
                "minimum": 0.0,
                "maximum": 300.0,
                "maturity": "preliminary",
                "basis": "estimate",
                "description": "dose the device is expected to survive",
            },
        ],
        "completeness_threshold": 1.0,
    }


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestFolding(unittest.TestCase):
    def test_power_folds_to_electrical(self):
        self.assertEqual(normalize_group("Power"), ELECTRICAL)

    def test_radiation_folds_to_environmental(self):
        self.assertEqual(normalize_group("radiation"), ENVIRONMENTAL)

    def test_performance_folds_to_timing(self):
        self.assertEqual(normalize_group("performance"), TIMING)

    def test_unknown_group_rejected(self):
        with self.assertRaises(ValueError):
            normalize_group("commercial")

    def test_five_groups_are_the_whole_set(self):
        self.assertEqual(len(CHARACTERISTIC_GROUPS), 5)

    def test_four_groups_are_mandatory(self):
        self.assertEqual(len(MANDATORY_GROUPS), 4)

    def test_tbc_folds_to_preliminary(self):
        self.assertEqual(normalize_maturity("TBC"), PRELIMINARY)

    def test_final_folds_to_confirmed(self):
        self.assertEqual(normalize_maturity("Final"), CONFIRMED)

    def test_unknown_maturity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_maturity("almost")

    def test_measured_folds_to_measurement(self):
        self.assertEqual(normalize_basis("measured"), MEASUREMENT)

    def test_model_folds_to_simulation(self):
        self.assertEqual(normalize_basis("model"), SIMULATION)

    def test_unknown_basis_rejected(self):
        with self.assertRaises(ValueError):
            normalize_basis("intuition")


class TestBasisAndRange(unittest.TestCase):
    def test_only_measurement_confirms_a_figure(self):
        self.assertTrue(basis_supports_confirmation("measurement"))
        self.assertFalse(basis_supports_confirmation("simulation"))
        self.assertFalse(basis_supports_confirmation("estimate"))
        self.assertFalse(basis_supports_confirmation("analysis"))

    def test_a_figure_inside_its_range_passes(self):
        self.assertTrue(within_declared_range(3.3, 3.0, 3.6))

    def test_a_figure_exactly_on_the_upper_bound_is_inside(self):
        self.assertTrue(within_declared_range(3.6, 3.0, 3.6))

    def test_a_figure_exactly_on_the_lower_bound_is_inside(self):
        self.assertTrue(within_declared_range(3.0, 3.0, 3.6))

    def test_a_computed_third_landing_on_a_third_bound_is_inside(self):
        self.assertTrue(within_declared_range(1 / 3, None, 1 / 3))

    def test_a_figure_above_its_upper_bound_is_outside(self):
        self.assertFalse(within_declared_range(3.7, 3.0, 3.6))

    def test_a_figure_below_its_lower_bound_is_outside(self):
        self.assertFalse(within_declared_range(2.9, 3.0, 3.6))

    def test_an_open_range_accepts_anything_finite(self):
        self.assertTrue(within_declared_range(-40.0))

    def test_a_non_finite_figure_rejected(self):
        with self.assertRaises(ValueError):
            within_declared_range(float("inf"), 0.0, 1.0)


class TestCharacteristicValidation(unittest.TestCase):
    def test_characteristics_resolve_in_declared_order(self):
        entries = validate_characteristics(base_sheet()["characteristics"])
        self.assertEqual(entries[0]["name"], "supply-voltage")
        self.assertTrue(entries[0]["numeric"])
        self.assertFalse(entries[2]["numeric"])

    def test_duplicate_name_rejected(self):
        records = base_sheet()["characteristics"]
        records.append(dict(records[0]))
        with self.assertRaises(ValueError):
            validate_characteristics(records)

    def test_unknown_key_rejected(self):
        records = base_sheet()["characteristics"]
        records[0]["owner"] = "someone"
        with self.assertRaises(ValueError):
            validate_characteristics(records)

    def test_missing_group_rejected(self):
        with self.assertRaises(ValueError):
            validate_characteristics([{"name": "a"}])

    def test_inverted_range_rejected(self):
        records = base_sheet()["characteristics"]
        records[0]["minimum"] = 4.0
        with self.assertRaises(ValueError):
            validate_characteristics(records)

    def test_a_range_on_a_textual_value_rejected(self):
        records = base_sheet()["characteristics"]
        records[2]["minimum"] = 0.0
        with self.assertRaises(ValueError):
            validate_characteristics(records)

    def test_a_boolean_value_rejected(self):
        records = base_sheet()["characteristics"]
        records[0]["value"] = True
        with self.assertRaises(ValueError):
            validate_characteristics(records)

    def test_maturity_defaults_to_preliminary(self):
        entries = validate_characteristics(
            [{"name": "a", "group": "electrical", "value": "text"}]
        )
        self.assertEqual(entries[0]["maturity"], PRELIMINARY)


class TestGroupCompleteness(unittest.TestCase):
    def setUp(self):
        self.entries = validate_characteristics(base_sheet()["characteristics"])

    def test_groups_present_are_reported_in_canonical_order(self):
        self.assertEqual(
            groups_present(self.entries),
            ["functional", "electrical", "timing", "environmental"],
        )

    def test_the_base_sheet_fills_every_mandatory_group(self):
        self.assertEqual(missing_mandatory_groups(self.entries), [])
        self.assertAlmostEqual(group_completeness(self.entries), 1.0, places=12)

    def test_an_empty_mandatory_group_lowers_completeness(self):
        records = base_sheet()["characteristics"][:3]
        entries = validate_characteristics(records)
        self.assertEqual(missing_mandatory_groups(entries), ["environmental"])
        self.assertAlmostEqual(group_completeness(entries), 0.75, places=12)

    def test_a_threshold_met_exactly_is_met(self):
        self.assertTrue(meets_completeness_threshold(3 / 4, 0.75))

    def test_a_threshold_missed_is_missed(self):
        self.assertFalse(meets_completeness_threshold(0.5, 0.75))

    def test_a_threshold_outside_zero_to_one_rejected(self):
        with self.assertRaises(ValueError):
            meets_completeness_threshold(0.5, 2.0)


class TestEvaluateDataSheet(unittest.TestCase):
    def test_a_coherent_sheet_is_acceptable(self):
        result = evaluate_data_sheet(base_sheet())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_figures_reach_the_result(self):
        result = evaluate_data_sheet(base_sheet())
        self.assertEqual(result["characteristic_count"], 4)
        self.assertAlmostEqual(result["group_completeness"], 1.0, places=12)

    def test_a_threshold_met_exactly_does_not_fail_the_sheet(self):
        sheet = base_sheet()
        sheet["completeness_threshold"] = 4 / 4
        result = evaluate_data_sheet(sheet)
        self.assertNotIn("group-completeness-below-threshold", codes(result))

    def test_a_bare_number_is_reported(self):
        sheet = base_sheet()
        sheet["characteristics"][0]["unit"] = ""
        result = evaluate_data_sheet(sheet)
        self.assertIn("numeric-figure-without-unit", codes(result))

    def test_a_dimensionless_unit_is_accepted(self):
        sheet = base_sheet()
        sheet["characteristics"][0]["unit"] = "1"
        result = evaluate_data_sheet(sheet)
        self.assertNotIn("numeric-figure-without-unit", codes(result))

    def test_a_figure_outside_its_range_is_reported(self):
        sheet = base_sheet()
        sheet["characteristics"][0]["value"] = 5.0
        result = evaluate_data_sheet(sheet)
        self.assertIn("figure-outside-declared-range", codes(result))

    def test_a_figure_exactly_on_its_bound_is_not_reported(self):
        sheet = base_sheet()
        sheet["characteristics"][0]["value"] = 3.6
        result = evaluate_data_sheet(sheet)
        self.assertNotIn("figure-outside-declared-range", codes(result))

    def test_a_confirmed_figure_on_a_simulation_is_reported(self):
        sheet = base_sheet()
        sheet["characteristics"][0]["maturity"] = "confirmed"
        result = evaluate_data_sheet(sheet)
        self.assertIn("confirmed-figure-on-unconfirmed-basis", codes(result))

    def test_a_confirmed_figure_on_a_measurement_is_accepted(self):
        sheet = base_sheet()
        sheet["characteristics"][0]["maturity"] = "confirmed"
        sheet["characteristics"][0]["basis"] = "measurement"
        result = evaluate_data_sheet(sheet)
        self.assertNotIn("confirmed-figure-on-unconfirmed-basis", codes(result))

    def test_a_characteristic_without_a_description_is_reported(self):
        sheet = base_sheet()
        sheet["characteristics"][1]["description"] = ""
        result = evaluate_data_sheet(sheet)
        self.assertIn("characteristic-without-description", codes(result))

    def test_a_characteristic_stating_nothing_is_reported(self):
        sheet = base_sheet()
        sheet["characteristics"][2]["value"] = ""
        result = evaluate_data_sheet(sheet)
        self.assertIn("characteristic-without-value", codes(result))

    def test_an_empty_mandatory_group_is_reported(self):
        sheet = base_sheet()
        sheet["characteristics"] = sheet["characteristics"][:3]
        result = evaluate_data_sheet(sheet)
        self.assertIn("mandatory-group-empty", codes(result))
        self.assertIn("group-completeness-below-threshold", codes(result))

    def test_unknown_sheet_key_rejected(self):
        sheet = base_sheet()
        sheet["price"] = 1
        with self.assertRaises(ValueError):
            evaluate_data_sheet(sheet)

    def test_missing_characteristics_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_data_sheet({"completeness_threshold": 1.0})

    def test_empty_sheet_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_data_sheet({"characteristics": []})

    def test_non_mapping_sheet_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_data_sheet([("characteristics", [])])


if __name__ == "__main__":
    unittest.main()
