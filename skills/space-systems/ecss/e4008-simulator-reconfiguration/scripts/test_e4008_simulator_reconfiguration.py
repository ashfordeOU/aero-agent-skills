"""Contract tests for the clause 5.5.3 simulator reconfiguration logic."""

import unittest

from e4008_simulator_reconfiguration_logic import (
    NORMATIVE_ITEMS,
    NORMATIVE_ITEM_COUNT,
    RECONFIGURABLE_FROM,
    RECONFIGURATION_SEQUENCE,
    assess_reconfiguration,
    check_identity_preservation,
    diff_configuration,
    validate_entry_state,
    validate_reconfiguration_walk,
)


def clean_spec():
    """A reconfiguration that satisfies both normative items."""
    return {
        "entry_state": "standby",
        "walk": ["building", "connecting", "initialising", "standby"],
        "previous_configuration": {
            "orbit.semi_major_axis": 7000.0,
            "power.bus_voltage": 28.0,
        },
        "reapplied_configuration": {
            "orbit.semi_major_axis": 7200.0,
            "power.bus_voltage": 28.0,
        },
        "previous_identities": {"Schedule": "svc-schedule", "Sat/Power": "mdl-power"},
        "new_identities": {"Schedule": "svc-schedule", "Sat/Power": "mdl-power"},
    }


class EntryStateTests(unittest.TestCase):
    def test_standby_is_the_permitted_entry(self):
        self.assertEqual(RECONFIGURABLE_FROM, ("standby",))
        self.assertTrue(validate_entry_state("standby")["permitted"])

    def test_case_is_folded(self):
        self.assertTrue(validate_entry_state("Standby")["permitted"])

    def test_executing_is_refused(self):
        result = validate_entry_state("executing")
        self.assertFalse(result["permitted"])
        self.assertTrue(result["findings"])

    def test_storing_is_refused(self):
        self.assertFalse(validate_entry_state("storing")["permitted"])

    def test_aborting_is_refused(self):
        self.assertFalse(validate_entry_state("aborting")["permitted"])

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry_state("paused")

    def test_non_string_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry_state(3)

    def test_blank_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry_state("   ")


class WalkTests(unittest.TestCase):
    def test_required_walk_is_compliant(self):
        result = validate_reconfiguration_walk(list(RECONFIGURATION_SEQUENCE))
        self.assertTrue(result["compliant"])

    def test_missing_state_is_a_finding(self):
        result = validate_reconfiguration_walk(["building", "initialising", "standby"])
        self.assertFalse(result["compliant"])
        self.assertTrue(any("connecting" in f for f in result["findings"]))

    def test_out_of_order_walk_is_a_finding(self):
        result = validate_reconfiguration_walk(
            ["building", "initialising", "connecting", "standby"])
        self.assertFalse(result["compliant"])

    def test_walk_not_ending_in_standby_is_a_finding(self):
        result = validate_reconfiguration_walk(
            ["building", "connecting", "initialising", "standby", "executing"])
        self.assertFalse(result["compliant"])
        self.assertTrue(any("rather than standby" in f for f in result["findings"]))

    def test_foreign_state_is_reported(self):
        result = validate_reconfiguration_walk(
            ["building", "connecting", "restoring", "initialising", "standby"])
        self.assertTrue(any("outside the reconfiguration walk" in f for f in result["findings"]))

    def test_empty_walk_rejected(self):
        with self.assertRaises(ValueError):
            validate_reconfiguration_walk([])

    def test_non_sequence_walk_rejected(self):
        with self.assertRaises(ValueError):
            validate_reconfiguration_walk("standby")


class ConfigurationDiffTests(unittest.TestCase):
    def test_identical_sets_retain_everything(self):
        diff = diff_configuration({"a": 1, "b": 2}, {"a": 1, "b": 2})
        self.assertEqual(diff["retained"], ["a", "b"])
        self.assertEqual(diff["dropped"], [])
        self.assertEqual(diff["introduced"], [])
        self.assertEqual(diff["changed"], [])

    def test_changed_value_is_reported(self):
        diff = diff_configuration({"a": 1}, {"a": 5})
        self.assertEqual(diff["changed"], ["a"])

    def test_dropped_field_is_reported(self):
        diff = diff_configuration({"a": 1, "b": 2}, {"a": 1})
        self.assertEqual(diff["dropped"], ["b"])

    def test_introduced_field_is_reported(self):
        diff = diff_configuration({"a": 1}, {"a": 1, "c": 3})
        self.assertEqual(diff["introduced"], ["c"])

    def test_results_are_sorted(self):
        diff = diff_configuration({"z": 1, "a": 1}, {})
        self.assertEqual(diff["dropped"], ["a", "z"])

    def test_empty_previous_rejected(self):
        with self.assertRaises(ValueError):
            diff_configuration({}, {"a": 1})

    def test_non_mapping_rejected(self):
        with self.assertRaises(ValueError):
            diff_configuration([("a", 1)], {"a": 1})

    def test_blank_field_path_rejected(self):
        with self.assertRaises(ValueError):
            diff_configuration({"  ": 1}, {"a": 1})


class IdentityTests(unittest.TestCase):
    def test_preserved_identities_are_compliant(self):
        result = check_identity_preservation({"Schedule": "s1"}, {"Schedule": "s1"})
        self.assertTrue(result["compliant"])

    def test_changed_identity_is_a_finding(self):
        result = check_identity_preservation({"Schedule": "s1"}, {"Schedule": "s2"})
        self.assertFalse(result["compliant"])
        self.assertTrue(any("changed from" in f for f in result["findings"]))

    def test_absent_identity_is_a_finding(self):
        result = check_identity_preservation({"Schedule": "s1", "Clock": "c1"}, {"Schedule": "s1"})
        self.assertTrue(any("is absent" in f for f in result["findings"]))

    def test_new_identity_is_a_finding(self):
        result = check_identity_preservation({"Schedule": "s1"}, {"Schedule": "s1", "Extra": "e1"})
        self.assertTrue(any("appeared without" in f for f in result["findings"]))

    def test_empty_previous_identities_rejected(self):
        with self.assertRaises(ValueError):
            check_identity_preservation({}, {"Schedule": "s1"})

    def test_non_mapping_identities_rejected(self):
        with self.assertRaises(ValueError):
            check_identity_preservation(["Schedule"], {"Schedule": "s1"})


class AssessmentTests(unittest.TestCase):
    def test_item_catalogue_has_two_entries(self):
        self.assertEqual(len(NORMATIVE_ITEMS), NORMATIVE_ITEM_COUNT)

    def test_clean_reconfiguration_is_compliant(self):
        result = assess_reconfiguration(clean_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["item_count"], NORMATIVE_ITEM_COUNT)

    def test_value_change_is_allowed_by_default(self):
        result = assess_reconfiguration(clean_spec())
        self.assertEqual(result["configuration_diff"]["changed"], ["orbit.semi_major_axis"])
        self.assertNotIn("RC-02", result["violations"])

    def test_value_change_violates_a_value_preserving_reconfiguration(self):
        spec = clean_spec()
        spec["allow_value_changes"] = False
        result = assess_reconfiguration(spec)
        self.assertIn("RC-02", result["violations"])

    def test_entry_from_executing_violates_item_one(self):
        spec = clean_spec()
        spec["entry_state"] = "executing"
        result = assess_reconfiguration(spec)
        self.assertIn("RC-01", result["violations"])

    def test_short_walk_violates_item_one(self):
        spec = clean_spec()
        spec["walk"] = ["building", "standby"]
        result = assess_reconfiguration(spec)
        self.assertIn("RC-01", result["violations"])

    def test_dropped_field_violates_item_two(self):
        spec = clean_spec()
        del spec["reapplied_configuration"]["power.bus_voltage"]
        result = assess_reconfiguration(spec)
        self.assertIn("RC-02", result["violations"])

    def test_changed_schedule_identity_violates_item_two(self):
        spec = clean_spec()
        spec["new_identities"]["Schedule"] = "svc-schedule-2"
        result = assess_reconfiguration(spec)
        self.assertIn("RC-02", result["violations"])

    def test_both_items_can_fail_together(self):
        spec = clean_spec()
        spec["entry_state"] = "restoring"
        spec["new_identities"] = {"Schedule": "other", "Sat/Power": "mdl-power"}
        result = assess_reconfiguration(spec)
        self.assertEqual(sorted(result["violations"]), ["RC-01", "RC-02"])

    def test_missing_key_rejected(self):
        spec = clean_spec()
        del spec["walk"]
        with self.assertRaises(ValueError):
            assess_reconfiguration(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_reconfiguration(["standby"])

    def test_non_boolean_value_flag_rejected(self):
        spec = clean_spec()
        spec["allow_value_changes"] = "no"
        with self.assertRaises(ValueError):
            assess_reconfiguration(spec)

    def test_every_item_carries_a_title_and_status(self):
        result = assess_reconfiguration(clean_spec())
        for item in result["items"]:
            self.assertTrue(item["title"])
            self.assertIn(item["status"], ("satisfied", "violated"))


if __name__ == "__main__":
    unittest.main()
