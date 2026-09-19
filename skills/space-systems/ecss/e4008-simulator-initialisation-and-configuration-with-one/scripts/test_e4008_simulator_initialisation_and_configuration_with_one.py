"""Contract tests for the clause 5.5.2 single-Schedule initialisation logic."""

import unittest

from e4008_simulator_initialisation_and_configuration_with_one_logic import (
    CONFIGURABLE_STATES,
    NORMATIVE_ITEMS,
    NORMATIVE_ITEM_COUNT,
    REQUIRED_STATE_SEQUENCE,
    assess_initialisation,
    count_schedules,
    order_initialisation_entry_points,
    validate_configuration_writes,
    validate_single_schedule,
    validate_state_sequence,
)


def clean_spec():
    """A run that satisfies all four normative items."""
    return {
        "states": ["building", "connecting", "initialising", "standby"],
        "services": [
            {"kind": "logger", "name": "Logger"},
            {"kind": "schedule", "name": "Schedule"},
            {"kind": "time_keeper", "name": "TimeKeeper"},
        ],
        "configuration_writes": [
            {"field": "orbit.semi_major_axis", "state": "building"},
            {"field": "power.bus_voltage", "state": "building"},
        ],
        "entry_points": [
            {"name": "LoadCatalogue", "priority": 0},
            {"name": "BindLinks", "priority": 10, "depends_on": ["LoadCatalogue"]},
            {"name": "SeedState", "priority": 20, "depends_on": ["BindLinks"]},
        ],
        "posted_order": ["LoadCatalogue", "BindLinks", "SeedState"],
    }


class StateSequenceTests(unittest.TestCase):
    def test_required_sequence_has_four_states(self):
        self.assertEqual(len(REQUIRED_STATE_SEQUENCE), 4)
        self.assertEqual(REQUIRED_STATE_SEQUENCE[0], "building")
        self.assertEqual(REQUIRED_STATE_SEQUENCE[-1], "standby")

    def test_clean_walk_is_compliant(self):
        result = validate_state_sequence(list(REQUIRED_STATE_SEQUENCE))
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_case_is_folded(self):
        result = validate_state_sequence(["Building", "CONNECTING", "initialising", "Standby"])
        self.assertTrue(result["compliant"])

    def test_missing_state_is_a_finding(self):
        result = validate_state_sequence(["building", "initialising", "standby"])
        self.assertFalse(result["compliant"])
        self.assertTrue(any("connecting" in f for f in result["findings"]))

    def test_repeated_state_is_a_finding(self):
        result = validate_state_sequence(
            ["building", "connecting", "connecting", "initialising", "standby"])
        self.assertFalse(result["compliant"])

    def test_out_of_order_walk_is_a_finding(self):
        result = validate_state_sequence(
            ["building", "initialising", "connecting", "standby"])
        self.assertFalse(result["compliant"])
        self.assertTrue(any("before" in f for f in result["findings"]))

    def test_foreign_state_is_a_finding(self):
        result = validate_state_sequence(
            ["building", "connecting", "initialising", "executing", "standby"])
        self.assertFalse(result["compliant"])

    def test_empty_walk_rejected(self):
        with self.assertRaises(ValueError):
            validate_state_sequence([])

    def test_non_sequence_walk_rejected(self):
        with self.assertRaises(ValueError):
            validate_state_sequence("building")

    def test_blank_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_state_sequence(["building", "  "])


class ScheduleTests(unittest.TestCase):
    def test_bare_strings_are_accepted(self):
        tally = count_schedules(["logger", "schedule"])
        self.assertEqual(tally["count"], 1)

    def test_single_schedule_is_compliant(self):
        result = validate_single_schedule([{"kind": "schedule", "name": "Schedule"}])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["schedule_count"], 1)

    def test_no_schedule_is_a_finding(self):
        result = validate_single_schedule([{"kind": "logger", "name": "Logger"}])
        self.assertFalse(result["compliant"])
        self.assertEqual(result["schedule_count"], 0)

    def test_two_schedules_is_a_finding(self):
        result = validate_single_schedule([
            {"kind": "schedule", "name": "Primary"},
            {"kind": "Schedule", "name": "Backup"},
        ])
        self.assertFalse(result["compliant"])
        self.assertEqual(result["schedule_names"], ["Primary", "Backup"])

    def test_service_without_kind_rejected(self):
        with self.assertRaises(ValueError):
            count_schedules([{"name": "Schedule"}])

    def test_non_sequence_services_rejected(self):
        with self.assertRaises(ValueError):
            count_schedules("schedule")

    def test_service_of_wrong_shape_rejected(self):
        with self.assertRaises(ValueError):
            count_schedules([42])


class ConfigurationWriteTests(unittest.TestCase):
    def test_only_building_is_configurable(self):
        self.assertEqual(CONFIGURABLE_STATES, ("building",))

    def test_writes_in_building_are_applied(self):
        result = validate_configuration_writes(
            [{"field": "mass", "state": "building"}])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["applied"], ["mass"])

    def test_write_after_publication_is_a_finding(self):
        result = validate_configuration_writes(
            [{"field": "mass", "state": "initialising"}])
        self.assertFalse(result["compliant"])
        self.assertEqual(result["late"], ["mass"])

    def test_empty_write_list_is_compliant(self):
        result = validate_configuration_writes([])
        self.assertTrue(result["compliant"])

    def test_write_outside_the_sequence_rejected(self):
        with self.assertRaises(ValueError):
            validate_configuration_writes([{"field": "mass", "state": "executing"}])

    def test_write_without_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_configuration_writes([{"state": "building"}])

    def test_non_mapping_write_rejected(self):
        with self.assertRaises(ValueError):
            validate_configuration_writes(["mass"])


class EntryPointOrderTests(unittest.TestCase):
    def test_priority_decides_the_order(self):
        order = order_initialisation_entry_points([
            {"name": "B", "priority": 5},
            {"name": "A", "priority": 1},
        ])
        self.assertEqual([r["name"] for r in order], ["A", "B"])

    def test_declaration_order_breaks_a_priority_tie(self):
        order = order_initialisation_entry_points([
            {"name": "first", "priority": 3},
            {"name": "second", "priority": 3},
        ])
        self.assertEqual([r["name"] for r in order], ["first", "second"])

    def test_dependency_outranks_priority(self):
        order = order_initialisation_entry_points([
            {"name": "late", "priority": 1, "depends_on": ["early"]},
            {"name": "early", "priority": 9},
        ])
        self.assertEqual([r["name"] for r in order], ["early", "late"])

    def test_cycle_rejected(self):
        with self.assertRaises(ValueError):
            order_initialisation_entry_points([
                {"name": "a", "depends_on": ["b"]},
                {"name": "b", "depends_on": ["a"]},
            ])

    def test_unknown_dependency_rejected(self):
        with self.assertRaises(ValueError):
            order_initialisation_entry_points([{"name": "a", "depends_on": ["ghost"]}])

    def test_duplicate_entry_point_rejected(self):
        with self.assertRaises(ValueError):
            order_initialisation_entry_points([{"name": "a"}, {"name": "a"}])

    def test_string_dependency_rejected(self):
        with self.assertRaises(ValueError):
            order_initialisation_entry_points([{"name": "a", "depends_on": "b"}])

    def test_non_integer_priority_rejected(self):
        with self.assertRaises(ValueError):
            order_initialisation_entry_points([{"name": "a", "priority": 1.5}])

    def test_empty_entry_point_list_rejected(self):
        with self.assertRaises(ValueError):
            order_initialisation_entry_points([])


class AssessmentTests(unittest.TestCase):
    def test_item_catalogue_has_four_entries(self):
        self.assertEqual(len(NORMATIVE_ITEMS), NORMATIVE_ITEM_COUNT)

    def test_clean_run_is_compliant(self):
        result = assess_initialisation(clean_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["item_count"], NORMATIVE_ITEM_COUNT)

    def test_clean_run_reports_the_dependency_order(self):
        result = assess_initialisation(clean_spec())
        self.assertEqual(result["entry_point_order"],
                         ["LoadCatalogue", "BindLinks", "SeedState"])

    def test_second_schedule_violates_item_two(self):
        spec = clean_spec()
        spec["services"].append({"kind": "schedule", "name": "Backup"})
        result = assess_initialisation(spec)
        self.assertIn("IN-02", result["violations"])

    def test_late_write_violates_item_three(self):
        spec = clean_spec()
        spec["configuration_writes"].append(
            {"field": "power.bus_voltage", "state": "standby"})
        result = assess_initialisation(spec)
        self.assertIn("IN-03", result["violations"])

    def test_skipped_state_violates_item_one(self):
        spec = clean_spec()
        spec["states"] = ["building", "initialising", "standby"]
        result = assess_initialisation(spec)
        self.assertIn("IN-01", result["violations"])

    def test_wrong_posted_order_violates_item_four(self):
        spec = clean_spec()
        spec["posted_order"] = ["BindLinks", "LoadCatalogue", "SeedState"]
        result = assess_initialisation(spec)
        self.assertIn("IN-04", result["violations"])

    def test_absent_posted_order_leaves_item_four_satisfied(self):
        spec = clean_spec()
        del spec["posted_order"]
        result = assess_initialisation(spec)
        self.assertNotIn("IN-04", result["violations"])

    def test_missing_key_rejected(self):
        spec = clean_spec()
        del spec["services"]
        with self.assertRaises(ValueError):
            assess_initialisation(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_initialisation(["states"])

    def test_non_sequence_posted_order_rejected(self):
        spec = clean_spec()
        spec["posted_order"] = "LoadCatalogue"
        with self.assertRaises(ValueError):
            assess_initialisation(spec)

    def test_every_item_carries_a_status(self):
        result = assess_initialisation(clean_spec())
        for item in result["items"]:
            self.assertIn(item["status"], ("satisfied", "violated"))
            self.assertTrue(item["title"])


if __name__ == "__main__":
    unittest.main()
