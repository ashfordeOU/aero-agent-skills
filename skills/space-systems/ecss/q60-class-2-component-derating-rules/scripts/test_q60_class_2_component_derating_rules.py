#!/usr/bin/env python3
"""Contract test for the Class 2 component derating rules leaf (offline)."""

import copy
import unittest

from q60_class_2_component_derating_rules_logic import (
    DEFAULT_CLASS_2_DERATING_RULES,
    DEFAULT_MIN_AMBIENT_HEADROOM_C,
    ELECTRICAL_STRESSES,
    EQUIPMENT_BREACHED,
    EQUIPMENT_DEMONSTRATED,
    EQUIPMENT_NO_HEADROOM,
    ON_MARGIN,
    OVER_MARGIN,
    PART_CATEGORIES,
    WITHIN_MARGIN,
    allowable_applied,
    applied_stress,
    assess_equipment,
    grade_part,
    grade_stress,
    limiting_temperature_c,
    rating_retention_factor,
    stress_reduction_margin,
    temperature_adjusted_rating,
    validate_derating_rules,
)

RESISTOR = {
    "part_reference": "r-4001",
    "category": "resistor",
    "quantity": 6,
    "part_temperature_c": 60.0,
    "stresses": {"voltage": {"nominal": 20.0, "rated": 50.0}},
}

INTEGRATED_CIRCUIT = {
    "part_reference": "u-4002",
    "category": "integrated-circuit",
    "quantity": 2,
    "part_temperature_c": 100.0,
    "stresses": {
        "voltage": {"nominal": 3.3, "rated": 10.0},
        "current": {"nominal": 0.05, "rated": 0.2, "transient_uplift": 1.2},
    },
}

EQUIPMENT = {
    "equipment_name": "payload-interface-unit",
    "parts": [RESISTOR, INTEGRATED_CIRCUIT],
}


def _part(base, **overrides):
    item = copy.deepcopy(dict(base))
    item.update(overrides)
    return item


def _equipment(**overrides):
    item = copy.deepcopy(EQUIPMENT)
    item.update(overrides)
    return item


class RuleSetTests(unittest.TestCase):
    def test_default_rules_validate(self):
        self.assertIs(
            validate_derating_rules(DEFAULT_CLASS_2_DERATING_RULES),
            DEFAULT_CLASS_2_DERATING_RULES,
        )

    def test_every_category_carries_every_stress(self):
        for category in PART_CATEGORIES:
            for stress in ELECTRICAL_STRESSES:
                self.assertIn(stress, DEFAULT_CLASS_2_DERATING_RULES[category])

    def test_every_margin_sits_inside_the_rating(self):
        for category in PART_CATEGORIES:
            for stress in ELECTRICAL_STRESSES:
                margin = stress_reduction_margin(category, stress)
                self.assertGreater(margin, 0.0)
                self.assertLess(margin, 1.0)

    def test_every_category_has_a_knee_below_its_maximum(self):
        for category in PART_CATEGORIES:
            entry = DEFAULT_CLASS_2_DERATING_RULES[category]
            self.assertLess(entry["knee_temperature_c"], entry["max_temperature_c"])

    def test_rules_missing_a_category_rejected(self):
        broken = copy.deepcopy(DEFAULT_CLASS_2_DERATING_RULES)
        del broken["relay-and-switch"]
        with self.assertRaises(ValueError):
            validate_derating_rules(broken)

    def test_rules_missing_a_stress_rejected(self):
        broken = copy.deepcopy(DEFAULT_CLASS_2_DERATING_RULES)
        del broken["capacitor"]["power"]
        with self.assertRaises(ValueError):
            validate_derating_rules(broken)

    def test_margin_above_unity_rejected(self):
        broken = copy.deepcopy(DEFAULT_CLASS_2_DERATING_RULES)
        broken["resistor"]["voltage"] = 1.2
        with self.assertRaises(ValueError):
            validate_derating_rules(broken)

    def test_a_knee_above_the_maximum_rejected(self):
        broken = copy.deepcopy(DEFAULT_CLASS_2_DERATING_RULES)
        broken["resistor"]["knee_temperature_c"] = 200.0
        with self.assertRaises(ValueError):
            validate_derating_rules(broken)

    def test_rules_missing_the_knee_rejected(self):
        broken = copy.deepcopy(DEFAULT_CLASS_2_DERATING_RULES)
        del broken["resistor"]["knee_temperature_c"]
        with self.assertRaises(ValueError):
            validate_derating_rules(broken)

    def test_non_mapping_rules_rejected(self):
        with self.assertRaises(ValueError):
            validate_derating_rules("class-2")

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            stress_reduction_margin("crystal-oscillator", "voltage")

    def test_unknown_stress_rejected(self):
        with self.assertRaises(ValueError):
            stress_reduction_margin("resistor", "frequency")


class RetentionTests(unittest.TestCase):
    def test_below_the_knee_the_whole_rating_stands(self):
        self.assertAlmostEqual(
            rating_retention_factor("resistor", 40.0), 1.0, places=9
        )

    def test_exactly_on_the_knee_the_whole_rating_stands(self):
        self.assertAlmostEqual(
            rating_retention_factor("resistor", 70.0), 1.0, places=9
        )

    def test_halfway_to_the_maximum_half_the_rating_stands(self):
        self.assertAlmostEqual(
            rating_retention_factor("resistor", 112.5), 0.5, places=9
        )

    def test_retention_falls_as_the_part_runs_hotter(self):
        cool = rating_retention_factor("integrated-circuit", 80.0)
        hot = rating_retention_factor("integrated-circuit", 120.0)
        self.assertLess(hot, cool)

    def test_at_the_maximum_there_is_no_rating_left_to_reduce(self):
        with self.assertRaises(ValueError):
            rating_retention_factor("resistor", 155.0)

    def test_above_the_maximum_rejected(self):
        with self.assertRaises(ValueError):
            rating_retention_factor("resistor", 180.0)

    def test_a_temperature_below_absolute_zero_rejected(self):
        with self.assertRaises(ValueError):
            rating_retention_factor("resistor", -400.0)

    def test_the_adjusted_rating_is_the_rating_times_the_retention(self):
        self.assertAlmostEqual(
            temperature_adjusted_rating("resistor", 100.0, 112.5), 50.0, places=9
        )

    def test_a_zero_rating_rejected(self):
        with self.assertRaises(ValueError):
            temperature_adjusted_rating("resistor", 0.0, 60.0)


class AppliedStressTests(unittest.TestCase):
    def test_a_bare_nominal_passes_through(self):
        self.assertAlmostEqual(applied_stress(12.0), 12.0, places=9)

    def test_tolerance_drift_and_uplift_all_open_the_stress_out(self):
        self.assertAlmostEqual(
            applied_stress(10.0, 0.1, 0.05, 1.2), 13.86, places=9
        )

    def test_end_of_life_drift_alone_raises_the_stress(self):
        self.assertAlmostEqual(applied_stress(10.0, 0.0, 0.2), 12.0, places=9)

    def test_a_negative_nominal_rejected(self):
        with self.assertRaises(ValueError):
            applied_stress(-1.0)

    def test_a_tolerance_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            applied_stress(10.0, 1.4)

    def test_a_drift_above_unity_rejected(self):
        with self.assertRaises(ValueError):
            applied_stress(10.0, 0.0, 1.4)

    def test_an_uplift_below_unity_rejected(self):
        with self.assertRaises(ValueError):
            applied_stress(10.0, 0.0, 0.0, 0.8)


class AllowableTests(unittest.TestCase):
    def test_below_the_knee_the_allowable_is_the_flat_margined_rating(self):
        self.assertAlmostEqual(
            allowable_applied("resistor", "voltage", 50.0, 60.0), 35.0, places=9
        )

    def test_above_the_knee_the_allowable_falls_with_temperature(self):
        cool = allowable_applied("resistor", "voltage", 50.0, 60.0)
        hot = allowable_applied("resistor", "voltage", 50.0, 112.5)
        self.assertLess(hot, cool)

    def test_the_limiting_temperature_returns_the_allowable_to_the_stress(self):
        limit = limiting_temperature_c("resistor", "voltage", 50.0, 20.0)
        self.assertAlmostEqual(
            allowable_applied("resistor", "voltage", 50.0, limit), 20.0, places=9
        )

    def test_a_stress_on_the_flat_margined_rating_is_limited_at_the_knee(self):
        limit = limiting_temperature_c("resistor", "voltage", 50.0, 35.0)
        self.assertAlmostEqual(limit, 70.0, places=9)

    def test_a_stress_past_the_flat_margined_rating_has_no_limiting_temperature(self):
        self.assertIsNone(
            limiting_temperature_c("resistor", "voltage", 50.0, 44.0)
        )

    def test_a_negative_applied_stress_rejected(self):
        with self.assertRaises(ValueError):
            limiting_temperature_c("resistor", "voltage", 50.0, -1.0)


class StressGradingTests(unittest.TestCase):
    def test_a_stress_inside_its_allowable_is_within_margin(self):
        result = grade_stress(
            "resistor", "voltage", {"nominal": 20.0, "rated": 50.0}, 60.0
        )
        self.assertEqual(result["verdict"], WITHIN_MARGIN)
        self.assertTrue(result["compliant"])

    def test_a_stress_exactly_on_its_allowable_is_on_margin_not_a_breach(self):
        result = grade_stress(
            "resistor", "voltage", {"nominal": 35.0, "rated": 50.0}, 60.0
        )
        self.assertAlmostEqual(
            result["applied"], result["allowable_applied"], places=9
        )
        self.assertEqual(result["verdict"], ON_MARGIN)
        self.assertTrue(result["compliant"])

    def test_a_stress_past_its_allowable_is_over_margin(self):
        result = grade_stress(
            "resistor", "voltage", {"nominal": 40.0, "rated": 50.0}, 60.0
        )
        self.assertEqual(result["verdict"], OVER_MARGIN)
        self.assertFalse(result["compliant"])

    def test_the_same_stress_can_pass_cool_and_fail_hot(self):
        entry = {"nominal": 30.0, "rated": 50.0}
        cool = grade_stress("resistor", "voltage", entry, 60.0)
        hot = grade_stress("resistor", "voltage", entry, 140.0)
        self.assertTrue(cool["compliant"])
        self.assertFalse(hot["compliant"])

    def test_the_ambient_headroom_is_reported_in_degrees(self):
        result = grade_stress(
            "resistor", "voltage", {"nominal": 20.0, "rated": 50.0}, 60.0
        )
        self.assertAlmostEqual(
            result["ambient_headroom_c"],
            result["limiting_temperature_c"] - 60.0,
            places=9,
        )

    def test_a_stress_with_no_limiting_temperature_reports_no_headroom(self):
        result = grade_stress(
            "resistor", "voltage", {"nominal": 44.0, "rated": 50.0}, 60.0
        )
        self.assertIsNone(result["ambient_headroom_c"])

    def test_a_stress_entry_without_a_rating_rejected(self):
        with self.assertRaises(ValueError):
            grade_stress("resistor", "voltage", {"nominal": 20.0}, 60.0)

    def test_a_non_mapping_stress_entry_rejected(self):
        with self.assertRaises(ValueError):
            grade_stress("resistor", "voltage", 20.0, 60.0)


class PartTests(unittest.TestCase):
    def test_a_cool_part_passes_every_stress(self):
        result = grade_part(RESISTOR)
        self.assertTrue(result["compliant"])
        self.assertEqual(result["tightest_stress"], "voltage")

    def test_a_hot_part_is_graded_against_its_reduced_rating(self):
        result = grade_part(INTEGRATED_CIRCUIT)
        self.assertAlmostEqual(result["retention_factor"], 0.625, places=9)
        self.assertTrue(result["compliant"])

    def test_the_binding_stress_is_the_one_with_least_ambient_headroom(self):
        result = grade_part(INTEGRATED_CIRCUIT)
        self.assertEqual(result["binding_stress"], "voltage")
        self.assertAlmostEqual(result["ambient_headroom_c"], 17.0, places=6)

    def test_a_breached_part_names_the_stress_in_its_findings(self):
        part = _part(
            RESISTOR, stresses={"voltage": {"nominal": 40.0, "rated": 50.0}}
        )
        result = grade_part(part)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("voltage" in f for f in result["findings"]))

    def test_an_unknown_stress_name_rejected(self):
        with self.assertRaises(ValueError):
            grade_part(
                _part(RESISTOR, stresses={"frequency": {"nominal": 1.0, "rated": 2.0}})
            )

    def test_a_part_with_no_stresses_rejected(self):
        with self.assertRaises(ValueError):
            grade_part(_part(RESISTOR, stresses={}))

    def test_a_part_without_a_temperature_rejected(self):
        part = _part(RESISTOR)
        del part["part_temperature_c"]
        with self.assertRaises(ValueError):
            grade_part(part)

    def test_an_uncategorized_part_rejected(self):
        part = _part(RESISTOR)
        del part["category"]
        with self.assertRaises(ValueError):
            grade_part(part)

    def test_a_zero_quantity_rejected(self):
        with self.assertRaises(ValueError):
            grade_part(_part(RESISTOR, quantity=0))

    def test_a_part_without_a_reference_rejected(self):
        with self.assertRaises(ValueError):
            grade_part(_part(RESISTOR, part_reference=""))


class EquipmentTests(unittest.TestCase):
    def test_a_margined_equipment_is_demonstrated(self):
        result = assess_equipment(EQUIPMENT)
        self.assertEqual(result["verdict"], EQUIPMENT_DEMONSTRATED)
        self.assertTrue(result["compliant"])

    def test_the_binding_part_and_stress_are_named(self):
        result = assess_equipment(EQUIPMENT)
        self.assertEqual(result["binding_part"], "u-4002")
        self.assertEqual(result["binding_stress"], "voltage")

    def test_the_equipment_headroom_is_the_smallest_part_headroom(self):
        result = assess_equipment(EQUIPMENT)
        self.assertAlmostEqual(result["ambient_headroom_c"], 17.0, places=6)

    def test_a_thin_headroom_is_reported_without_calling_the_design_breached(self):
        hot = _part(INTEGRATED_CIRCUIT)
        hot["stresses"]["voltage"]["rated"] = 8.0
        result = assess_equipment(_equipment(parts=[RESISTOR, hot]))
        self.assertEqual(result["verdict"], EQUIPMENT_NO_HEADROOM)
        self.assertTrue(result["compliant"])

    def test_a_headroom_exactly_on_the_floor_is_demonstrated(self):
        result = assess_equipment(EQUIPMENT)
        floor = result["ambient_headroom_c"]
        again = assess_equipment(EQUIPMENT, DEFAULT_CLASS_2_DERATING_RULES, floor)
        self.assertAlmostEqual(again["ambient_headroom_c"], floor, places=9)
        self.assertEqual(again["verdict"], EQUIPMENT_DEMONSTRATED)

    def test_an_over_margin_part_breaches_the_equipment(self):
        hot = _part(INTEGRATED_CIRCUIT)
        hot["stresses"]["voltage"]["rated"] = 5.0
        result = assess_equipment(_equipment(parts=[RESISTOR, hot]))
        self.assertEqual(result["verdict"], EQUIPMENT_BREACHED)
        self.assertFalse(result["compliant"])
        self.assertIn("u-4002", result["breached_parts"])

    def test_a_stress_no_cooling_can_save_breaches_the_equipment(self):
        hot = _part(INTEGRATED_CIRCUIT)
        hot["stresses"]["voltage"]["nominal"] = 9.0
        result = assess_equipment(_equipment(parts=[RESISTOR, hot]))
        self.assertEqual(result["verdict"], EQUIPMENT_BREACHED)

    def test_the_tightest_part_is_named_by_utilisation(self):
        result = assess_equipment(EQUIPMENT)
        self.assertEqual(result["tightest_part"], "u-4002")
        self.assertGreater(result["tightest_utilisation"], 0.0)

    def test_a_repeated_part_reference_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment(_equipment(parts=[RESISTOR, _part(RESISTOR)]))

    def test_an_equipment_with_no_parts_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment(_equipment(parts=[]))

    def test_an_equipment_without_a_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment(_equipment(equipment_name=" "))

    def test_a_non_mapping_equipment_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment("payload-interface-unit")

    def test_a_negative_headroom_floor_rejected(self):
        with self.assertRaises(ValueError):
            assess_equipment(EQUIPMENT, DEFAULT_CLASS_2_DERATING_RULES, -5.0)

    def test_the_default_headroom_floor_is_a_real_margin(self):
        self.assertGreater(DEFAULT_MIN_AMBIENT_HEADROOM_C, 0.0)


if __name__ == "__main__":
    unittest.main(verbosity=1)
