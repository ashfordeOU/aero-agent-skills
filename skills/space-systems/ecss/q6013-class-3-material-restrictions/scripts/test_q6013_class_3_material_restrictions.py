#!/usr/bin/env python3
"""Contract test for the Class 3 material restrictions (offline)."""

import copy
import unittest

from q6013_class_3_material_restrictions_logic import (
    DEFAULT_RESTRICTION_TABLE,
    ITEM_ACCEPTED,
    ITEM_MITIGATED,
    ITEM_PROHIBITED,
    ITEM_SEVERITY,
    ITEM_UNMITIGATED,
    MOISTURE_FLOOR_LIFE_HOURS,
    MOISTURE_ITEM,
    MOISTURE_ON_LIMIT,
    MOISTURE_OVER,
    MOISTURE_WITHIN,
    RESTRICTION_ACCEPTED,
    RESTRICTION_CONDITIONAL,
    RESTRICTION_PROHIBITED,
    SCREEN_ACCEPTED,
    SCREEN_MITIGATED,
    SCREEN_REJECTED,
    accepted_mitigations,
    assess_construction_item,
    assess_moisture_exposure,
    moisture_floor_life_hours,
    restriction_for,
    screen_construction,
    validate_restriction_table,
)

CLEAN_DECLARATION = {
    "items": ["tin-lead-finish", "hermetic-ceramic-package"],
    "mitigations": {},
}

PLASTIC_DECLARATION = {
    "items": ["pure-tin-finish", "non-hermetic-plastic-encapsulation"],
    "mitigations": {
        "pure-tin-finish": ["hot-solder-dip-lead-bearing"],
        "non-hermetic-plastic-encapsulation": ["dry-pack-and-bake-before-mounting"],
    },
    "moisture_level": "3",
    "exposure_hours": 40.0,
}


def _declaration(base, **overrides):
    case = copy.deepcopy(dict(base))
    case.update(overrides)
    return case


class TableTests(unittest.TestCase):
    def test_default_table_validates(self):
        self.assertIs(
            validate_restriction_table(DEFAULT_RESTRICTION_TABLE),
            DEFAULT_RESTRICTION_TABLE,
        )

    def test_every_conditional_entry_names_a_mitigation(self):
        for item, entry in DEFAULT_RESTRICTION_TABLE.items():
            if entry["category"] == RESTRICTION_CONDITIONAL:
                self.assertTrue(entry["mitigations"], item)

    def test_no_prohibited_entry_names_a_mitigation(self):
        for item, entry in DEFAULT_RESTRICTION_TABLE.items():
            if entry["category"] == RESTRICTION_PROHIBITED:
                self.assertEqual(entry["mitigations"], (), item)

    def test_empty_table_rejected(self):
        with self.assertRaises(ValueError):
            validate_restriction_table({})

    def test_unknown_category_rejected(self):
        broken = copy.deepcopy(DEFAULT_RESTRICTION_TABLE)
        broken["pure-tin-finish"]["category"] = "probably-fine"
        with self.assertRaises(ValueError):
            validate_restriction_table(broken)

    def test_conditional_entry_without_a_mitigation_rejected(self):
        broken = copy.deepcopy(DEFAULT_RESTRICTION_TABLE)
        broken["pure-tin-finish"]["mitigations"] = ()
        with self.assertRaises(ValueError):
            validate_restriction_table(broken)

    def test_prohibited_entry_with_a_mitigation_rejected(self):
        broken = copy.deepcopy(DEFAULT_RESTRICTION_TABLE)
        broken["cadmium-plating"]["mitigations"] = ("wish-very-hard",)
        with self.assertRaises(ValueError):
            validate_restriction_table(broken)

    def test_lookup_returns_the_entry(self):
        self.assertEqual(
            restriction_for("cadmium-plating")["category"], RESTRICTION_PROHIBITED
        )

    def test_undeclared_construction_rejected(self):
        with self.assertRaises(ValueError):
            restriction_for("unobtanium-coating")

    def test_accepted_mitigations_are_listed(self):
        self.assertIn("tin-lead-refinish", accepted_mitigations("pure-tin-finish"))


class ItemGradingTests(unittest.TestCase):
    def test_benign_finish_is_accepted(self):
        graded = assess_construction_item("tin-lead-finish")
        self.assertEqual(graded["verdict"], ITEM_ACCEPTED)
        self.assertTrue(graded["compliant"])

    def test_prohibited_plating_is_prohibited(self):
        graded = assess_construction_item("cadmium-plating")
        self.assertEqual(graded["verdict"], ITEM_PROHIBITED)
        self.assertFalse(graded["compliant"])

    def test_prohibited_plating_stays_prohibited_under_any_mitigation(self):
        graded = assess_construction_item("zinc-plating", ["tin-lead-refinish"])
        self.assertEqual(graded["verdict"], ITEM_PROHIBITED)
        self.assertEqual(graded["effective_mitigations"], ())

    def test_bare_tin_without_a_mitigation_is_unmitigated(self):
        graded = assess_construction_item("pure-tin-finish")
        self.assertEqual(graded["verdict"], ITEM_UNMITIGATED)
        self.assertFalse(graded["compliant"])

    def test_bare_tin_with_an_accepted_mitigation_is_cleared(self):
        graded = assess_construction_item("pure-tin-finish", ["tin-lead-refinish"])
        self.assertEqual(graded["verdict"], ITEM_MITIGATED)
        self.assertTrue(graded["compliant"])

    def test_an_unrelated_mitigation_does_not_clear_a_restriction(self):
        graded = assess_construction_item(
            "pure-tin-finish", ["controlled-handling-and-disposal-procedure"]
        )
        self.assertEqual(graded["verdict"], ITEM_UNMITIGATED)

    def test_a_bare_string_mitigation_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_construction_item("pure-tin-finish", "tin-lead-refinish")

    def test_severity_orders_the_four_grades(self):
        self.assertLess(ITEM_SEVERITY[ITEM_ACCEPTED], ITEM_SEVERITY[ITEM_MITIGATED])
        self.assertLess(ITEM_SEVERITY[ITEM_MITIGATED], ITEM_SEVERITY[ITEM_UNMITIGATED])
        self.assertLess(ITEM_SEVERITY[ITEM_UNMITIGATED], ITEM_SEVERITY[ITEM_PROHIBITED])

    def test_every_table_entry_grades_without_error(self):
        for item, entry in DEFAULT_RESTRICTION_TABLE.items():
            graded = assess_construction_item(item, entry["mitigations"])
            self.assertIn(graded["verdict"], ITEM_SEVERITY)
            if entry["category"] == RESTRICTION_ACCEPTED:
                self.assertEqual(graded["verdict"], ITEM_ACCEPTED)


class MoistureTests(unittest.TestCase):
    def test_unrestricted_level_has_no_floor_life(self):
        self.assertIsNone(moisture_floor_life_hours("1"))

    def test_floor_life_shortens_as_the_level_rises(self):
        ordered = ["2", "2a", "3", "4", "5", "5a", "6"]
        hours = [MOISTURE_FLOOR_LIFE_HOURS[k] for k in ordered]
        for earlier, later in zip(hours, hours[1:]):
            self.assertGreater(earlier, later)

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            moisture_floor_life_hours("7b")

    def test_exposure_inside_the_floor_life_is_within(self):
        graded = assess_moisture_exposure("3", 40.0)
        self.assertEqual(graded["verdict"], MOISTURE_WITHIN)
        self.assertTrue(graded["compliant"])

    def test_exposure_exactly_on_the_floor_life_is_on_limit_and_compliant(self):
        floor = moisture_floor_life_hours("4")
        graded = assess_moisture_exposure("4", floor)
        self.assertEqual(graded["verdict"], MOISTURE_ON_LIMIT)
        self.assertTrue(graded["compliant"])
        self.assertAlmostEqual(graded["remaining_hours"], 0.0, places=9)

    def test_representation_error_at_the_floor_life_is_absorbed(self):
        floor = moisture_floor_life_hours("4")
        drifted = floor + floor * 2.0e-16
        self.assertTrue(assess_moisture_exposure("4", drifted)["compliant"])

    def test_exposure_past_the_floor_life_is_over(self):
        graded = assess_moisture_exposure("5a", 50.0)
        self.assertEqual(graded["verdict"], MOISTURE_OVER)
        self.assertFalse(graded["compliant"])
        self.assertIn("bake and reseal", graded["detail"])

    def test_unlimited_level_passes_any_exposure(self):
        graded = assess_moisture_exposure("1", 100000.0)
        self.assertTrue(graded["compliant"])
        self.assertIsNone(graded["floor_life_hours"])

    def test_zero_floor_life_level_fails_any_exposure(self):
        self.assertEqual(assess_moisture_exposure("6", 1.0)["verdict"], MOISTURE_OVER)
        self.assertEqual(
            assess_moisture_exposure("6", 0.0)["verdict"], MOISTURE_ON_LIMIT
        )

    def test_negative_exposure_rejected(self):
        with self.assertRaises(ValueError):
            assess_moisture_exposure("3", -1.0)

    def test_non_numeric_exposure_rejected(self):
        with self.assertRaises(ValueError):
            assess_moisture_exposure("3", "two days")


class ScreenConstructionTests(unittest.TestCase):
    def test_benign_declaration_is_accepted(self):
        result = screen_construction(CLEAN_DECLARATION)
        self.assertEqual(result["verdict"], SCREEN_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["mitigation_coverage"], 1.0, places=9)

    def test_fully_mitigated_declaration_is_accepted_with_mitigations(self):
        result = screen_construction(PLASTIC_DECLARATION)
        self.assertEqual(result["verdict"], SCREEN_MITIGATED)
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["restricted_count"], 2)
        self.assertAlmostEqual(result["mitigation_coverage"], 1.0, places=9)

    def test_an_unmitigated_restriction_rejects_the_part(self):
        case = _declaration(PLASTIC_DECLARATION)
        case["mitigations"] = {}
        result = screen_construction(case)
        self.assertEqual(result["verdict"], SCREEN_REJECTED)
        self.assertAlmostEqual(result["mitigation_coverage"], 0.0, places=9)

    def test_half_mitigated_coverage_is_the_cleared_fraction(self):
        case = _declaration(PLASTIC_DECLARATION)
        case["mitigations"] = {"pure-tin-finish": ["tin-lead-refinish"]}
        result = screen_construction(case)
        self.assertAlmostEqual(result["mitigation_coverage"], 0.5, places=9)

    def test_a_prohibited_item_rejects_and_governs(self):
        case = _declaration(PLASTIC_DECLARATION, items=["pure-tin-finish", "cadmium-plating"])
        case["mitigations"] = {"pure-tin-finish": ["tin-lead-refinish"]}
        result = screen_construction(case)
        self.assertEqual(result["verdict"], SCREEN_REJECTED)
        self.assertEqual(result["governing_item"], "cadmium-plating")
        self.assertEqual(result["prohibited_count"], 1)

    def test_moisture_over_the_floor_life_rejects_an_otherwise_clean_part(self):
        case = _declaration(PLASTIC_DECLARATION, exposure_hours=400.0)
        result = screen_construction(case)
        self.assertEqual(result["verdict"], SCREEN_REJECTED)
        self.assertEqual(result["governing_item"], MOISTURE_ITEM)

    def test_moisture_screen_is_optional(self):
        result = screen_construction(CLEAN_DECLARATION)
        self.assertIsNone(result["moisture"])

    def test_half_a_moisture_pair_rejected(self):
        case = _declaration(PLASTIC_DECLARATION)
        del case["exposure_hours"]
        with self.assertRaises(ValueError):
            screen_construction(case)

    def test_empty_item_list_rejected(self):
        with self.assertRaises(ValueError):
            screen_construction(_declaration(CLEAN_DECLARATION, items=[]))

    def test_non_mapping_declaration_rejected(self):
        with self.assertRaises(ValueError):
            screen_construction(["pure-tin-finish"])

    def test_mitigation_for_an_undeclared_item_rejected(self):
        case = _declaration(CLEAN_DECLARATION)
        case["mitigations"] = {"pure-tin-finish": ["tin-lead-refinish"]}
        with self.assertRaises(ValueError):
            screen_construction(case)

    def test_undeclared_construction_in_a_declaration_rejected(self):
        with self.assertRaises(ValueError):
            screen_construction(_declaration(CLEAN_DECLARATION, items=["mystery-goo"]))

    def test_every_finding_names_its_item(self):
        case = _declaration(PLASTIC_DECLARATION, items=["pure-tin-finish", "zinc-plating"])
        case["mitigations"] = {}
        result = screen_construction(case)
        self.assertTrue(result["findings"])
        for finding in result["findings"]:
            self.assertIn(":", finding)


if __name__ == "__main__":
    unittest.main(verbosity=1)
