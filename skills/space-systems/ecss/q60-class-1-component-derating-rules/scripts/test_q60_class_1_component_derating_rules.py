#!/usr/bin/env python3
"""Contract test for the Class 1 component derating rules leaf (offline)."""

import copy
import unittest

from q60_class_1_component_derating_rules_logic import (
    DEFAULT_DERATING_RULES,
    ELECTRICAL_STRESSES,
    EQUIPMENT_BREACHED,
    EQUIPMENT_DEMONSTRATED,
    EQUIPMENT_INCOMPLETE,
    ON_MARGIN,
    OVER_MARGIN,
    PART_CATEGORIES,
    WITHIN_MARGIN,
    allowable_applied,
    analysis_coverage,
    assess_equipment,
    grade_part,
    grade_stress,
    max_hot_spot_temperature_c,
    stress_reduction_margin,
    validate_derating_rules,
    worst_case_applied,
)

RESISTOR = {
    "part_reference": "r-0001",
    "category": "resistor",
    "quantity": 4,
    "stresses": {
        "voltage": {"nominal": 10.0, "rated": 50.0, "tolerance_fraction": 0.05},
        "power": {"nominal": 0.10, "rated": 0.50, "tolerance_fraction": 0.10},
    },
    "predicted_hot_spot_c": 90.0,
    "rated_max_hot_spot_c": 155.0,
}

INTEGRATED_CIRCUIT = {
    "part_reference": "u-0002",
    "category": "integrated-circuit",
    "quantity": 2,
    "stresses": {
        "voltage": {"nominal": 3.3, "rated": 5.0},
        "current": {"nominal": 0.05, "rated": 0.10, "transient_uplift": 1.3},
    },
    "predicted_hot_spot_c": 95.0,
    "rated_max_hot_spot_c": 150.0,
}

PARTS_LIST = [
    {"part_reference": "r-0001", "quantity": 4},
    {"part_reference": "u-0002", "quantity": 2},
]

EQUIPMENT = {
    "equipment_name": "power-conditioning-unit",
    "parts_list": PARTS_LIST,
    "analysed_parts": [RESISTOR, INTEGRATED_CIRCUIT],
}


def _part(base, **overrides):
    part = copy.deepcopy(dict(base))
    part.update(overrides)
    return part


def _equipment(**overrides):
    equipment = copy.deepcopy(EQUIPMENT)
    equipment.update(overrides)
    return equipment


class RuleSetTests(unittest.TestCase):
    def test_default_rules_validate(self):
        self.assertIs(
            validate_derating_rules(DEFAULT_DERATING_RULES), DEFAULT_DERATING_RULES
        )

    def test_rules_cover_every_category(self):
        for category in PART_CATEGORIES:
            self.assertIn(category, DEFAULT_DERATING_RULES)

    def test_rules_cover_every_electrical_stress(self):
        for category in PART_CATEGORIES:
            for stress in ELECTRICAL_STRESSES:
                self.assertIn(stress, DEFAULT_DERATING_RULES[category])

    def test_every_margin_sits_inside_the_rating(self):
        for category in PART_CATEGORIES:
            for stress in ELECTRICAL_STRESSES:
                margin = DEFAULT_DERATING_RULES[category][stress]
                self.assertGreater(margin, 0.0)
                self.assertLess(margin, 1.0)

    def test_non_mapping_rules_rejected(self):
        with self.assertRaises(ValueError):
            validate_derating_rules("default")

    def test_rules_missing_a_category_rejected(self):
        broken = copy.deepcopy(DEFAULT_DERATING_RULES)
        del broken["relay-and-switch"]
        with self.assertRaises(ValueError):
            validate_derating_rules(broken)

    def test_rules_missing_a_stress_rejected(self):
        broken = copy.deepcopy(DEFAULT_DERATING_RULES)
        del broken["capacitor"]["power"]
        with self.assertRaises(ValueError):
            validate_derating_rules(broken)

    def test_margin_above_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_DERATING_RULES)
        broken["resistor"]["voltage"] = 1.3
        with self.assertRaises(ValueError):
            validate_derating_rules(broken)

    def test_rules_missing_the_thermal_step_rejected(self):
        broken = copy.deepcopy(DEFAULT_DERATING_RULES)
        del broken["integrated-circuit"]["hot_spot_step_down_c"]
        with self.assertRaises(ValueError):
            validate_derating_rules(broken)

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            stress_reduction_margin("vacuum-tube", "voltage")

    def test_unknown_stress_rejected(self):
        with self.assertRaises(ValueError):
            stress_reduction_margin("resistor", "torque")


class WorstCaseTests(unittest.TestCase):
    def test_nominal_alone_is_carried_through(self):
        self.assertAlmostEqual(worst_case_applied(10.0), 10.0, places=9)

    def test_tolerance_opens_the_stress_out(self):
        self.assertAlmostEqual(worst_case_applied(10.0, 0.05), 10.5, places=9)

    def test_transient_uplift_raises_the_stress_again(self):
        self.assertAlmostEqual(worst_case_applied(10.0, 0.05, 1.2), 12.6, places=9)

    def test_negative_nominal_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_applied(-1.0)

    def test_tolerance_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_applied(10.0, 1.5)

    def test_uplift_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            worst_case_applied(10.0, 0.0, 0.8)


class AllowableTests(unittest.TestCase):
    def test_allowable_is_the_rating_times_the_margin(self):
        self.assertAlmostEqual(
            allowable_applied("resistor", "voltage", 50.0), 30.0, places=9
        )

    def test_zero_rating_rejected(self):
        with self.assertRaises(ValueError):
            allowable_applied("resistor", "voltage", 0.0)

    def test_hot_spot_ceiling_steps_down_from_the_rating(self):
        self.assertAlmostEqual(
            max_hot_spot_temperature_c("resistor", 155.0), 115.0, places=9
        )

    def test_hot_spot_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            max_hot_spot_temperature_c("resistor", -400.0)


class StressGradeTests(unittest.TestCase):
    def test_comfortable_stress_is_within_margin(self):
        graded = grade_stress(
            "resistor", "voltage", {"nominal": 10.0, "rated": 50.0}
        )
        self.assertEqual(graded["verdict"], WITHIN_MARGIN)

    def test_stress_landing_on_the_allowable_is_on_margin(self):
        graded = grade_stress(
            "resistor", "voltage", {"nominal": 30.0, "rated": 50.0}
        )
        self.assertEqual(graded["verdict"], ON_MARGIN)
        self.assertTrue(graded["compliant"])
        self.assertAlmostEqual(graded["headroom"], 0.0, places=9)

    def test_stress_above_the_allowable_is_over_margin(self):
        graded = grade_stress(
            "resistor", "voltage", {"nominal": 31.0, "rated": 50.0}
        )
        self.assertEqual(graded["verdict"], OVER_MARGIN)
        self.assertFalse(graded["compliant"])

    def test_transient_uplift_can_break_a_nominally_safe_stress(self):
        graded = grade_stress(
            "resistor",
            "voltage",
            {"nominal": 28.0, "rated": 50.0, "transient_uplift": 1.5},
        )
        self.assertEqual(graded["verdict"], OVER_MARGIN)

    def test_stress_entry_missing_the_rating_rejected(self):
        with self.assertRaises(ValueError):
            grade_stress("resistor", "voltage", {"nominal": 10.0})

    def test_non_mapping_stress_entry_rejected(self):
        with self.assertRaises(ValueError):
            grade_stress("resistor", "voltage", 10.0)


class PartGradeTests(unittest.TestCase):
    def test_sound_part_is_compliant(self):
        graded = grade_part(RESISTOR)
        self.assertTrue(graded["compliant"])
        self.assertTrue(graded["thermal_demonstrated"])
        self.assertEqual(graded["findings"], [])

    def test_hot_spot_on_the_ceiling_is_compliant(self):
        graded = grade_part(_part(RESISTOR, predicted_hot_spot_c=115.0))
        self.assertEqual(graded["thermal"]["verdict"], ON_MARGIN)
        self.assertTrue(graded["compliant"])

    def test_hot_spot_above_the_ceiling_breaches(self):
        graded = grade_part(_part(RESISTOR, predicted_hot_spot_c=130.0))
        self.assertFalse(graded["compliant"])

    def test_part_without_a_thermal_prediction_is_flagged(self):
        part = _part(RESISTOR)
        del part["predicted_hot_spot_c"]
        del part["rated_max_hot_spot_c"]
        graded = grade_part(part)
        self.assertFalse(graded["thermal_demonstrated"])
        self.assertEqual(len(graded["findings"]), 1)

    def test_half_a_thermal_pair_rejected(self):
        part = _part(RESISTOR)
        del part["rated_max_hot_spot_c"]
        with self.assertRaises(ValueError):
            grade_part(part)

    def test_tightest_stress_is_named(self):
        graded = grade_part(INTEGRATED_CIRCUIT)
        self.assertEqual(graded["tightest_stress"], "current")

    def test_unknown_stress_key_rejected(self):
        part = _part(RESISTOR)
        part["stresses"]["torque"] = {"nominal": 1.0, "rated": 2.0}
        with self.assertRaises(ValueError):
            grade_part(part)

    def test_empty_stresses_rejected(self):
        with self.assertRaises(ValueError):
            grade_part(_part(RESISTOR, stresses={}))

    def test_blank_part_reference_rejected(self):
        with self.assertRaises(ValueError):
            grade_part(_part(RESISTOR, part_reference="  "))

    def test_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            grade_part(_part(RESISTOR, quantity=0))

    def test_non_integer_quantity_rejected(self):
        with self.assertRaises(ValueError):
            grade_part(_part(RESISTOR, quantity=2.5))


class CoverageTests(unittest.TestCase):
    def test_full_coverage_is_complete(self):
        coverage = analysis_coverage(PARTS_LIST, ["r-0001", "u-0002"])
        self.assertTrue(coverage["complete"])
        self.assertAlmostEqual(coverage["line_coverage"], 1.0, places=9)
        self.assertAlmostEqual(coverage["quantity_coverage"], 1.0, places=9)

    def test_missed_line_is_reported(self):
        parts_list = PARTS_LIST + [{"part_reference": "c-0003", "quantity": 6}]
        coverage = analysis_coverage(parts_list, ["r-0001", "u-0002"])
        self.assertFalse(coverage["complete"])
        self.assertEqual(coverage["uncovered_lines"], ["c-0003"])

    def test_quantity_coverage_weighs_the_missed_line(self):
        parts_list = PARTS_LIST + [{"part_reference": "c-0003", "quantity": 6}]
        coverage = analysis_coverage(parts_list, ["r-0001", "u-0002"])
        self.assertAlmostEqual(coverage["quantity_coverage"], 0.5, places=9)

    def test_analysis_of_a_part_absent_from_the_list_rejected(self):
        with self.assertRaises(ValueError):
            analysis_coverage(PARTS_LIST, ["r-0001", "u-0002", "x-0009"])

    def test_duplicate_parts_list_line_rejected(self):
        parts_list = PARTS_LIST + [{"part_reference": "r-0001", "quantity": 1}]
        with self.assertRaises(ValueError):
            analysis_coverage(parts_list, ["r-0001"])

    def test_empty_parts_list_rejected(self):
        with self.assertRaises(ValueError):
            analysis_coverage([], [])


class EquipmentTests(unittest.TestCase):
    def test_complete_and_clean_equipment_is_demonstrated(self):
        result = assess_equipment(EQUIPMENT)
        self.assertEqual(result["verdict"], EQUIPMENT_DEMONSTRATED)
        self.assertTrue(result["compliant"])

    def test_uncovered_line_leaves_the_equipment_incomplete(self):
        equipment = _equipment(
            parts_list=PARTS_LIST + [{"part_reference": "c-0003", "quantity": 6}]
        )
        result = assess_equipment(equipment)
        self.assertEqual(result["verdict"], EQUIPMENT_INCOMPLETE)
        self.assertIn("c-0003", result["coverage"]["uncovered_lines"])

    def test_every_analysed_part_passing_does_not_cover_a_gap(self):
        equipment = _equipment(
            parts_list=PARTS_LIST + [{"part_reference": "c-0003", "quantity": 6}]
        )
        result = assess_equipment(equipment)
        self.assertTrue(all(part["compliant"] for part in result["parts"]))
        self.assertFalse(result["compliant"])

    def test_a_breach_outranks_a_coverage_gap(self):
        broken = _part(RESISTOR)
        broken["stresses"]["power"]["nominal"] = 0.25
        equipment = _equipment(
            parts_list=PARTS_LIST + [{"part_reference": "c-0003", "quantity": 6}],
            analysed_parts=[broken, INTEGRATED_CIRCUIT],
        )
        result = assess_equipment(equipment)
        self.assertEqual(result["verdict"], EQUIPMENT_BREACHED)
        self.assertEqual(result["breached_parts"], ["r-0001"])

    def test_missing_thermal_prediction_leaves_the_equipment_incomplete(self):
        part = _part(INTEGRATED_CIRCUIT)
        del part["predicted_hot_spot_c"]
        del part["rated_max_hot_spot_c"]
        result = assess_equipment(_equipment(analysed_parts=[RESISTOR, part]))
        self.assertEqual(result["verdict"], EQUIPMENT_INCOMPLETE)
        self.assertEqual(result["parts_without_thermal"], ["u-0002"])

    def test_tightest_part_and_stress_are_named(self):
        result = assess_equipment(EQUIPMENT)
        self.assertEqual(result["tightest_part"], "u-0002")
        self.assertEqual(result["tightest_stress"], "current")

    def test_analysing_a_part_twice_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment(_equipment(analysed_parts=[RESISTOR, _part(RESISTOR)]))

    def test_equipment_without_a_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment(_equipment(equipment_name=""))

    def test_equipment_with_no_analysed_parts_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment(_equipment(analysed_parts=[]))

    def test_non_mapping_equipment_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment("power-conditioning-unit")

    def test_findings_name_the_uncovered_line(self):
        equipment = _equipment(
            parts_list=PARTS_LIST + [{"part_reference": "c-0003", "quantity": 6}]
        )
        result = assess_equipment(equipment)
        self.assertTrue(any("c-0003" in finding for finding in result["findings"]))


if __name__ == "__main__":
    unittest.main(verbosity=1)
