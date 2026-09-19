#!/usr/bin/env python3
"""Gate 3 contract test for e2021-generic-actuator-electronics-ratings.

Stdlib unittest only, offline, deterministic. A declared rating landing exactly
on a requirement is asserted with assertAlmostEqual against the requirement and
on the decision the logic then takes, never with a strict inequality whose
truth would depend on the last bit of a product.
"""

import unittest

from e2021_generic_actuator_electronics_ratings_logic import (
    DEFAULT_RATING_SPEC,
    OUTPUT_CURRENT,
    OUTPUT_POWER,
    RATING_EPS,
    apply_margin,
    evaluate_ratings,
    family_envelope,
    grade_rating,
    group_demands,
    load_demand,
    rating_status,
    resolve_spec,
)


def nominal_loads():
    return [
        {"name": "separation-nut-one", "group": "separation-salvo",
         "resistance_min_ohm": 4.0, "drive_voltage_max_v": 32.0},
        {"name": "separation-nut-two", "group": "separation-salvo",
         "resistance_min_ohm": 8.0, "drive_voltage_max_v": 32.0},
        {"name": "valve-latch", "group": "valve-single",
         "resistance_min_ohm": 16.0, "drive_voltage_max_v": 32.0},
    ]


def nominal_config():
    return {
        "loads": nominal_loads(),
        "declared_output_current_a": 16.0,
        "declared_output_power_w": 500.0,
    }


class TestSpecResolution(unittest.TestCase):
    def test_defaults_are_returned_untouched(self):
        spec = resolve_spec()
        self.assertAlmostEqual(spec["design_margin_fraction"], 0.25, places=9)
        self.assertEqual(set(spec), set(DEFAULT_RATING_SPEC))

    def test_override_is_applied(self):
        spec = resolve_spec({"design_margin_fraction": 0.5})
        self.assertAlmostEqual(spec["design_margin_fraction"], 0.5, places=9)

    def test_override_does_not_mutate_the_default(self):
        resolve_spec({"design_margin_fraction": 0.5})
        self.assertAlmostEqual(
            DEFAULT_RATING_SPEC["design_margin_fraction"], 0.25, places=9
        )

    def test_a_zero_margin_is_admissible(self):
        self.assertAlmostEqual(
            resolve_spec({"design_margin_fraction": 0.0})["design_margin_fraction"],
            0.0,
            places=9,
        )

    def test_a_negative_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"design_margin_fraction": -0.1})

    def test_a_non_positive_recommended_capability_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"recommended_output_current_a": 0.0})

    def test_an_unrecognized_key_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec({"recommended_output_energy_j": 5.0})

    def test_a_non_mapping_override_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_spec([("design_margin_fraction", 0.25)])


class TestLoadDemand(unittest.TestCase):
    def test_the_demand_is_taken_at_the_worst_corner(self):
        demand = load_demand(nominal_loads()[0])
        self.assertAlmostEqual(demand["current_a"], 8.0, places=9)
        self.assertAlmostEqual(demand["power_w"], 256.0, places=9)

    def test_a_higher_resistance_asks_for_less(self):
        demand = load_demand(nominal_loads()[2])
        self.assertAlmostEqual(demand["current_a"], 2.0, places=9)

    def test_a_load_defaults_to_its_own_group(self):
        load = nominal_loads()[0]
        del load["group"]
        self.assertEqual(load_demand(load)["group"], "separation-nut-one")

    def test_a_zero_resistance_is_rejected(self):
        load = nominal_loads()[0]
        load["resistance_min_ohm"] = 0.0
        with self.assertRaises(ValueError):
            load_demand(load)

    def test_a_non_positive_drive_voltage_is_rejected(self):
        load = nominal_loads()[0]
        load["drive_voltage_max_v"] = 0.0
        with self.assertRaises(ValueError):
            load_demand(load)

    def test_a_load_without_a_name_is_rejected(self):
        load = nominal_loads()[0]
        load["name"] = " "
        with self.assertRaises(ValueError):
            load_demand(load)

    def test_a_non_mapping_load_is_rejected(self):
        with self.assertRaises(ValueError):
            load_demand(["separation-nut-one"])


class TestGroupsAndEnvelope(unittest.TestCase):
    def test_loads_fired_together_are_one_demand(self):
        groups = {entry["group"]: entry for entry in group_demands(nominal_loads())}
        self.assertAlmostEqual(groups["separation-salvo"]["current_a"], 12.0, places=9)
        self.assertAlmostEqual(groups["separation-salvo"]["power_w"], 384.0, places=9)

    def test_a_single_load_group_stands_alone(self):
        groups = {entry["group"]: entry for entry in group_demands(nominal_loads())}
        self.assertAlmostEqual(groups["valve-single"]["current_a"], 2.0, places=9)

    def test_group_members_are_listed(self):
        groups = {entry["group"]: entry for entry in group_demands(nominal_loads())}
        self.assertEqual(
            groups["separation-salvo"]["members"],
            ["separation-nut-one", "separation-nut-two"],
        )

    def test_duplicate_load_names_are_rejected(self):
        loads = nominal_loads()
        loads[1]["name"] = loads[0]["name"]
        with self.assertRaises(ValueError):
            group_demands(loads)

    def test_an_empty_load_family_is_rejected(self):
        with self.assertRaises(ValueError):
            group_demands([])

    def test_the_salvo_outranks_either_of_its_members(self):
        envelope = family_envelope(nominal_loads())
        self.assertAlmostEqual(envelope["envelope_current_a"], 12.0, places=9)
        self.assertEqual(envelope["current_sizing_group"], "separation-salvo")

    def test_the_power_envelope_names_its_own_driver(self):
        envelope = family_envelope(nominal_loads())
        self.assertAlmostEqual(envelope["envelope_power_w"], 384.0, places=9)
        self.assertEqual(envelope["power_sizing_group"], "separation-salvo")

    def test_the_envelope_is_not_the_family_mean(self):
        envelope = family_envelope(nominal_loads())
        mean_current = (8.0 + 4.0 + 2.0) / 3.0
        self.assertNotAlmostEqual(
            envelope["envelope_current_a"], mean_current, places=9
        )


class TestMargin(unittest.TestCase):
    def test_the_margin_lifts_the_envelope_once(self):
        self.assertAlmostEqual(apply_margin(12.0, 0.25), 15.0, places=9)

    def test_a_zero_margin_leaves_the_envelope_alone(self):
        self.assertAlmostEqual(apply_margin(12.0, 0.0), 12.0, places=9)

    def test_applying_it_twice_compounds_it(self):
        self.assertAlmostEqual(
            apply_margin(apply_margin(12.0, 0.25), 0.25), 18.75, places=9
        )

    def test_a_negative_margin_is_rejected(self):
        with self.assertRaises(ValueError):
            apply_margin(12.0, -0.25)

    def test_a_negative_envelope_is_rejected(self):
        with self.assertRaises(ValueError):
            apply_margin(-1.0, 0.25)


class TestRatingGrade(unittest.TestCase):
    def test_a_rating_above_both_conditions_is_adequate(self):
        grade = grade_rating(16.0, 15.0, 10.0)
        self.assertTrue(grade["adequate"])
        self.assertAlmostEqual(grade["family_shortfall"], 0.0, places=9)

    def test_a_rating_exactly_on_the_requirement_covers_the_family(self):
        grade = grade_rating(15.0, 15.0, 10.0)
        self.assertAlmostEqual(grade["declared"], 15.0, places=9)
        self.assertAlmostEqual(grade["required"], 15.0, places=9)
        self.assertTrue(grade["covers_family"])
        self.assertAlmostEqual(grade["family_shortfall"], 0.0, places=9)

    def test_a_rating_under_the_requirement_reports_its_shortfall(self):
        grade = grade_rating(14.0, 15.0, 10.0)
        self.assertFalse(grade["covers_family"])
        self.assertAlmostEqual(grade["family_shortfall"], 1.0, places=9)

    def test_covering_the_family_is_not_enough_for_a_generic_design(self):
        grade = grade_rating(8.0, 7.0, 10.0)
        self.assertTrue(grade["covers_family"])
        self.assertFalse(grade["meets_generic_baseline"])
        self.assertFalse(grade["adequate"])

    def test_a_non_positive_declared_rating_is_rejected(self):
        with self.assertRaises(ValueError):
            grade_rating(0.0, 15.0, 10.0)


class TestEndToEnd(unittest.TestCase):
    def test_an_adequate_declaration_reports_no_findings(self):
        report = evaluate_ratings(nominal_config())
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["status"], "generic-ratings-adequate")
        self.assertTrue(report["adequate"])

    def test_the_required_ratings_carry_the_margin(self):
        report = evaluate_ratings(nominal_config())
        self.assertAlmostEqual(report[OUTPUT_CURRENT]["required"], 15.0, places=9)
        self.assertAlmostEqual(report[OUTPUT_POWER]["required"], 480.0, places=9)

    def test_an_undersized_current_rating_names_the_sizing_group(self):
        config = nominal_config()
        config["declared_output_current_a"] = 14.0
        report = evaluate_ratings(config)
        self.assertFalse(report["adequate"])
        self.assertEqual(report["status"], "hold-generic-ratings")
        self.assertTrue(
            any("separation-salvo" in f for f in report["findings"])
        )

    def test_an_undersized_power_rating_is_its_own_finding(self):
        config = nominal_config()
        config["declared_output_power_w"] = 400.0
        report = evaluate_ratings(config)
        self.assertFalse(report[OUTPUT_POWER]["covers_family"])
        self.assertTrue(report[OUTPUT_CURRENT]["covers_family"])

    def test_a_rating_below_the_generic_baseline_is_flagged_separately(self):
        config = nominal_config()
        config["loads"] = [nominal_loads()[2]]
        config["declared_output_current_a"] = 3.0
        config["declared_output_power_w"] = 300.0
        report = evaluate_ratings(config)
        self.assertTrue(report[OUTPUT_CURRENT]["covers_family"])
        self.assertFalse(report[OUTPUT_CURRENT]["meets_generic_baseline"])
        self.assertTrue(
            any("recommended generic capability" in f for f in report["findings"])
        )

    def test_an_absent_declaration_adopts_the_requirement(self):
        config = {"loads": nominal_loads()}
        report = evaluate_ratings(config)
        self.assertAlmostEqual(report[OUTPUT_CURRENT]["declared"], 15.0, places=9)
        self.assertTrue(report[OUTPUT_CURRENT]["covers_family"])

    def test_a_larger_margin_can_hold_a_passing_declaration(self):
        config = nominal_config()
        self.assertTrue(evaluate_ratings(config)["adequate"])
        config["spec"] = {"design_margin_fraction": 0.5}
        self.assertFalse(evaluate_ratings(config)["adequate"])

    def test_splitting_a_salvo_into_singles_lowers_the_requirement(self):
        config = nominal_config()
        config["declared_output_current_a"] = 10.5
        self.assertFalse(evaluate_ratings(config)["adequate"])
        for load in config["loads"]:
            load["group"] = load["name"]
        self.assertTrue(evaluate_ratings(config)["adequate"])

    def test_a_missing_load_key_is_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_ratings({"declared_output_current_a": 16.0})

    def test_the_config_must_be_a_mapping(self):
        with self.assertRaises(ValueError):
            evaluate_ratings([("loads", [])])

    def test_the_status_token_rejects_a_non_sequence(self):
        with self.assertRaises(ValueError):
            rating_status("hold")

    def test_the_named_tolerance_is_far_below_any_declared_rating(self):
        self.assertLess(RATING_EPS, 1e-6)


if __name__ == "__main__":
    unittest.main()
