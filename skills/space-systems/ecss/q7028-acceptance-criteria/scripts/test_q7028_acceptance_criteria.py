"""Contract tests for the board-repair acceptance criteria logic."""

import unittest

from q7028_acceptance_criteria_logic import (
    ASSURANCE_LEVEL_FACTORS,
    DEFAULT_ASSURANCE_LEVEL,
    REPAIR_CRITERIA,
    assess_repair_acceptance,
    criterion_names,
    criterion_utilisation,
    defect_repair_category,
    grade_measurements,
    open_items,
    repair_criteria,
    scaled_limit,
)

MAX_CRITERION = {
    "name": "conductor-width-reduction",
    "bound": "max",
    "limit": 0.20,
    "unit": "fraction",
}
MIN_CRITERION = {
    "name": "jumper-overlap-length-mm",
    "bound": "min",
    "limit": 3.0,
    "unit": "mm",
}


def conductor_repair(**overrides):
    """A broken conductor repaired with a jumper, every criterion comfortable."""
    repair = {
        "defect": "broken-conductor",
        "assurance_level": DEFAULT_ASSURANCE_LEVEL,
        "measurements": {
            "conductor-width-reduction": 0.05,
            "jumper-overlap-length-mm": 6.0,
            "conductor-resistance-increase": 0.02,
        },
    }
    repair.update(overrides)
    return repair


class DefectRoutingTests(unittest.TestCase):
    def test_a_broken_conductor_routes_to_a_conductor_repair(self):
        self.assertEqual(defect_repair_category("broken-conductor"), "conductor-repair")

    def test_a_lifted_land_routes_to_a_land_repair(self):
        self.assertEqual(defect_repair_category("lifted-land"), "land-repair")

    def test_defect_lookup_ignores_case_and_padding(self):
        self.assertEqual(defect_repair_category("  Measling "), "laminate-damage-repair")

    def test_unknown_defect_rejected(self):
        with self.assertRaises(ValueError):
            defect_repair_category("tombstoned-chip")

    def test_blank_defect_rejected(self):
        with self.assertRaises(ValueError):
            defect_repair_category("   ")

    def test_every_defect_maps_to_a_category_that_exists(self):
        for defect in ("broken-conductor", "lifted-land", "barrel-crack", "coating-void"):
            self.assertIn(defect_repair_category(defect), REPAIR_CRITERIA)


class CriteriaTests(unittest.TestCase):
    def test_a_category_carries_named_criteria(self):
        self.assertIn("land-bond-pull-strength-n", criterion_names("land-repair"))

    def test_unknown_category_rejected(self):
        with self.assertRaises(ValueError):
            repair_criteria("varnish-repair")

    def test_every_category_carries_at_least_two_criteria(self):
        for category in REPAIR_CRITERIA:
            self.assertGreaterEqual(len(repair_criteria(category)), 2)

    def test_every_criterion_states_a_direction_and_a_positive_limit(self):
        for category in REPAIR_CRITERIA:
            for criterion in repair_criteria(category):
                self.assertIn(criterion["bound"], ("max", "min"))
                self.assertGreater(criterion["limit"], 0.0)


class ScalingTests(unittest.TestCase):
    def test_level_two_leaves_a_ceiling_as_stated(self):
        self.assertAlmostEqual(scaled_limit(MAX_CRITERION, 2), 0.20, places=9)

    def test_level_one_brings_a_ceiling_down(self):
        expected = 0.20 * ASSURANCE_LEVEL_FACTORS[1]
        self.assertAlmostEqual(scaled_limit(MAX_CRITERION, 1), expected, places=9)

    def test_level_one_raises_a_floor(self):
        expected = 3.0 / ASSURANCE_LEVEL_FACTORS[1]
        self.assertAlmostEqual(scaled_limit(MIN_CRITERION, 1), expected, places=9)

    def test_level_three_relaxes_both_directions(self):
        self.assertGreater(scaled_limit(MAX_CRITERION, 3), scaled_limit(MAX_CRITERION, 2))
        self.assertLess(scaled_limit(MIN_CRITERION, 3), scaled_limit(MIN_CRITERION, 2))

    def test_unknown_assurance_level_rejected(self):
        with self.assertRaises(ValueError):
            scaled_limit(MAX_CRITERION, 4)

    def test_non_integer_assurance_level_rejected(self):
        with self.assertRaises(ValueError):
            scaled_limit(MAX_CRITERION, 2.0)

    def test_criterion_without_a_direction_rejected(self):
        with self.assertRaises(ValueError):
            scaled_limit({"name": "x", "bound": "about", "limit": 1.0})


class UtilisationTests(unittest.TestCase):
    def test_a_ceiling_value_on_its_limit_uses_exactly_one(self):
        self.assertAlmostEqual(criterion_utilisation(MAX_CRITERION, 0.20, 2), 1.0, places=9)

    def test_a_floor_value_on_its_limit_uses_exactly_one(self):
        self.assertAlmostEqual(criterion_utilisation(MIN_CRITERION, 3.0, 2), 1.0, places=9)

    def test_half_the_ceiling_uses_half(self):
        self.assertAlmostEqual(criterion_utilisation(MAX_CRITERION, 0.10, 2), 0.5, places=9)

    def test_half_the_floor_uses_double(self):
        self.assertAlmostEqual(criterion_utilisation(MIN_CRITERION, 1.5, 2), 2.0, places=9)

    def test_a_ceiling_and_a_floor_are_comparable_on_one_scale(self):
        ceiling = criterion_utilisation(MAX_CRITERION, 0.10, 2)
        floor = criterion_utilisation(MIN_CRITERION, 6.0, 2)
        self.assertAlmostEqual(ceiling, floor, places=9)

    def test_zero_against_a_floor_rejected(self):
        with self.assertRaises(ValueError):
            criterion_utilisation(MIN_CRITERION, 0.0, 2)

    def test_negative_against_a_ceiling_rejected(self):
        with self.assertRaises(ValueError):
            criterion_utilisation(MAX_CRITERION, -0.01, 2)

    def test_non_numeric_measurement_rejected(self):
        with self.assertRaises(ValueError):
            criterion_utilisation(MAX_CRITERION, "0.1", 2)


class OpenItemTests(unittest.TestCase):
    def test_a_full_measurement_set_leaves_nothing_open(self):
        self.assertEqual(open_items("conductor-repair", conductor_repair()["measurements"]), [])

    def test_a_missing_measurement_is_an_open_item(self):
        measurements = dict(conductor_repair()["measurements"])
        del measurements["jumper-overlap-length-mm"]
        items = open_items("conductor-repair", measurements)
        self.assertTrue(any("jumper-overlap-length-mm" in i for i in items))

    def test_an_empty_measurement_set_opens_every_criterion(self):
        self.assertEqual(
            len(open_items("conductor-repair", {})), len(criterion_names("conductor-repair"))
        )

    def test_a_measurement_from_another_category_rejected(self):
        with self.assertRaises(ValueError):
            open_items("conductor-repair", {"coating-overlap-mm": 4.0})

    def test_non_mapping_measurements_rejected(self):
        with self.assertRaises(ValueError):
            open_items("conductor-repair", [("a", 1)])


class GradingTests(unittest.TestCase):
    def test_grading_returns_one_row_per_supplied_measurement(self):
        graded = grade_measurements("conductor-repair", conductor_repair()["measurements"])
        self.assertEqual(len(graded), 3)

    def test_a_comfortable_measurement_is_met(self):
        graded = grade_measurements("conductor-repair", {"conductor-width-reduction": 0.05})
        self.assertTrue(graded[0]["met"])

    def test_a_measurement_on_its_ceiling_is_met(self):
        graded = grade_measurements("conductor-repair", {"conductor-width-reduction": 0.20})
        self.assertTrue(graded[0]["met"])
        self.assertAlmostEqual(graded[0]["utilisation"], 1.0, places=9)

    def test_a_measurement_past_its_ceiling_is_not_met(self):
        graded = grade_measurements("conductor-repair", {"conductor-width-reduction": 0.40})
        self.assertFalse(graded[0]["met"])

    def test_grading_reports_the_scaled_limit_not_the_stated_one(self):
        graded = grade_measurements(
            "conductor-repair", {"conductor-width-reduction": 0.05}, level=1
        )
        self.assertAlmostEqual(graded[0]["limit"], 0.20 * ASSURANCE_LEVEL_FACTORS[1], places=9)


class AcceptanceTests(unittest.TestCase):
    def test_a_comfortable_conductor_repair_is_accepted(self):
        result = assess_repair_acceptance(conductor_repair())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])

    def test_the_governing_criterion_is_the_one_closest_to_its_bound(self):
        result = assess_repair_acceptance(conductor_repair())
        # width uses 0.05/0.20 = 0.25, resistance 0.02/0.10 = 0.20, and the
        # jumper overlap 3.0/6.0 = 0.50 -- the floor is the tightest of the three.
        self.assertEqual(result["governing_criterion"], "jumper-overlap-length-mm")
        self.assertAlmostEqual(result["governing_utilisation"], 0.5, places=9)

    def test_one_breached_criterion_refuses_the_whole_repair(self):
        repair = conductor_repair()
        repair["measurements"]["conductor-width-reduction"] = 0.45
        result = assess_repair_acceptance(repair)
        self.assertFalse(result["accepted"])
        self.assertIn("conductor-width-reduction", result["breaches"])

    def test_a_shortfall_against_a_floor_is_a_breach(self):
        repair = conductor_repair()
        repair["measurements"]["jumper-overlap-length-mm"] = 1.0
        result = assess_repair_acceptance(repair)
        self.assertFalse(result["accepted"])
        self.assertIn("jumper-overlap-length-mm", result["breaches"])

    def test_a_missing_measurement_blocks_acceptance(self):
        repair = conductor_repair()
        del repair["measurements"]["conductor-resistance-increase"]
        result = assess_repair_acceptance(repair)
        self.assertFalse(result["accepted"])
        self.assertTrue(result["open_items"])

    def test_the_tighter_assurance_level_can_refuse_the_same_repair(self):
        repair = conductor_repair(assurance_level=1)
        repair["measurements"]["conductor-width-reduction"] = 0.18
        self.assertFalse(assess_repair_acceptance(repair)["accepted"])
        relaxed = conductor_repair(assurance_level=2)
        relaxed["measurements"]["conductor-width-reduction"] = 0.18
        self.assertTrue(assess_repair_acceptance(relaxed)["accepted"])

    def test_a_category_that_does_not_treat_the_defect_is_a_finding(self):
        repair = {
            "defect": "lifted-land",
            "repair_category": "coating-repair",
            "measurements": {
                "coating-thickness-mm": 0.05,
                "coating-overlap-mm": 3.0,
                "coating-repair-area-fraction": 0.02,
            },
        }
        result = assess_repair_acceptance(repair)
        self.assertFalse(result["accepted"])
        self.assertTrue(any("is treated by a" in f for f in result["findings"]))

    def test_the_category_is_resolved_from_the_defect_when_absent(self):
        result = assess_repair_acceptance(conductor_repair())
        self.assertEqual(result["repair_category"], result["expected_category"])

    def test_a_land_repair_grades_its_own_criteria(self):
        repair = {
            "defect": "lifted-land",
            "measurements": {
                "land-area-loss": 0.10,
                "land-bond-pull-strength-n": 8.0,
                "land-to-conductor-overlap-mm": 2.0,
            },
        }
        self.assertTrue(assess_repair_acceptance(repair)["accepted"])

    def test_missing_required_repair_key_rejected(self):
        repair = conductor_repair()
        del repair["measurements"]
        with self.assertRaises(ValueError):
            assess_repair_acceptance(repair)

    def test_non_mapping_repair_rejected(self):
        with self.assertRaises(ValueError):
            assess_repair_acceptance("broken-conductor")


if __name__ == "__main__":
    unittest.main()
