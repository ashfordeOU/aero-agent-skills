"""Contract tests for the clause 5.5.4.2 level 2 simulator interface logic."""

import unittest

from e4008_level_2_simulator_isimulatorl2_requirements_logic import (
    LEVEL1_OPERATIONS,
    LEVEL2_OPERATIONS,
    MAX_STEP_TICKS,
    NORMATIVE_ITEMS,
    NORMATIVE_ITEM_COUNT,
    PERMITTED_STATES,
    SIMULATOR_STATES,
    assess_level2_interface,
    check_state_guard,
    missing_operations,
    unexpected_operations,
    validate_operation_name,
    validate_state_set,
    validate_step_request,
    validate_time_scale,
)


def clean_spec():
    """An interface that satisfies all seven normative items."""
    return {
        "operations": list(LEVEL1_OPERATIONS) + list(LEVEL2_OPERATIONS),
        "state_guards": {
            "hold": ["executing"],
            "store": ["standby"],
            "step": ["standby"],
            "set_time_scale": ["standby", "executing"],
        },
        "hold_idempotent": True,
        "resume_idempotent": True,
        "step_ticks": 1000,
        "time_scale": 1.0,
    }


class OperationSetTests(unittest.TestCase):
    def test_the_two_sets_are_disjoint(self):
        self.assertEqual(set(LEVEL1_OPERATIONS) & set(LEVEL2_OPERATIONS), set())

    def test_every_operation_has_a_permitted_state_set(self):
        for name in list(LEVEL1_OPERATIONS) + list(LEVEL2_OPERATIONS):
            self.assertIn(name, PERMITTED_STATES)
            self.assertTrue(PERMITTED_STATES[name])

    def test_every_permitted_state_is_a_known_state(self):
        for states in PERMITTED_STATES.values():
            for state in states:
                self.assertIn(state, SIMULATOR_STATES)

    def test_operation_name_is_canonicalised(self):
        self.assertEqual(validate_operation_name("Set-Time Scale"), "set_time_scale")

    def test_unknown_operation_rejected(self):
        with self.assertRaises(ValueError):
            validate_operation_name("rewind")

    def test_blank_operation_rejected(self):
        with self.assertRaises(ValueError):
            validate_operation_name("  ")

    def test_non_string_operation_rejected(self):
        with self.assertRaises(ValueError):
            validate_operation_name(9)

    def test_missing_operations_reported_in_required_order(self):
        offered = ["run", "exit"]
        self.assertEqual(missing_operations(offered, ["hold", "run", "store"]),
                         ["hold", "store"])

    def test_nothing_missing_from_a_complete_interface(self):
        offered = list(LEVEL1_OPERATIONS) + list(LEVEL2_OPERATIONS)
        self.assertEqual(missing_operations(offered, LEVEL2_OPERATIONS), [])

    def test_unexpected_operation_reported(self):
        self.assertEqual(unexpected_operations(["run", "rewind"]), ["rewind"])

    def test_duplicate_offer_is_collapsed(self):
        self.assertEqual(unexpected_operations(["rewind", "rewind"]), ["rewind"])

    def test_non_sequence_operation_set_rejected(self):
        with self.assertRaises(ValueError):
            unexpected_operations("run")


class StateGuardTests(unittest.TestCase):
    def test_exact_declaration_is_compliant(self):
        result = check_state_guard("hold", ["executing"])
        self.assertTrue(result["compliant"])
        self.assertEqual(result["widened"], [])

    def test_narrower_declaration_is_compliant(self):
        result = check_state_guard("abort", ["standby"])
        self.assertTrue(result["compliant"])
        self.assertTrue(result["narrowed"])

    def test_wider_declaration_is_a_finding(self):
        result = check_state_guard("hold", ["executing", "building"])
        self.assertFalse(result["compliant"])
        self.assertEqual(result["widened"], ["building"])

    def test_state_set_is_canonicalised(self):
        self.assertEqual(validate_state_set(["Standby", "standby"]), ["standby"])

    def test_unknown_state_rejected(self):
        with self.assertRaises(ValueError):
            validate_state_set(["hyperspace"])

    def test_empty_state_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_state_set([])

    def test_non_sequence_state_set_rejected(self):
        with self.assertRaises(ValueError):
            validate_state_set("standby")


class StepAndScaleTests(unittest.TestCase):
    def test_positive_step_accepted(self):
        self.assertEqual(validate_step_request(500), 500)

    def test_step_at_the_bound_is_accepted(self):
        self.assertEqual(validate_step_request(MAX_STEP_TICKS), MAX_STEP_TICKS)

    def test_step_past_the_bound_rejected(self):
        with self.assertRaises(ValueError):
            validate_step_request(MAX_STEP_TICKS + 1)

    def test_zero_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_step_request(0)

    def test_negative_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_step_request(-5)

    def test_float_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_step_request(5.0)

    def test_boolean_step_rejected(self):
        with self.assertRaises(ValueError):
            validate_step_request(True)

    def test_unit_time_scale_accepted(self):
        self.assertAlmostEqual(validate_time_scale(1), 1.0, places=9)

    def test_fractional_time_scale_accepted(self):
        self.assertAlmostEqual(validate_time_scale(0.25), 0.25, places=9)

    def test_zero_time_scale_rejected(self):
        with self.assertRaises(ValueError):
            validate_time_scale(0)

    def test_negative_time_scale_rejected(self):
        with self.assertRaises(ValueError):
            validate_time_scale(-2.0)

    def test_infinite_time_scale_rejected(self):
        with self.assertRaises(ValueError):
            validate_time_scale(float("inf"))

    def test_non_numeric_time_scale_rejected(self):
        with self.assertRaises(ValueError):
            validate_time_scale("1.0")


class AssessmentTests(unittest.TestCase):
    def test_item_catalogue_has_seven_entries(self):
        self.assertEqual(len(NORMATIVE_ITEMS), NORMATIVE_ITEM_COUNT)
        self.assertEqual(len(set(i for i, _ in NORMATIVE_ITEMS)), NORMATIVE_ITEM_COUNT)

    def test_clean_interface_is_compliant(self):
        result = assess_level2_interface(clean_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["item_count"], NORMATIVE_ITEM_COUNT)

    def test_dropped_level1_operation_violates_item_one(self):
        spec = clean_spec()
        spec["operations"].remove("configure")
        result = assess_level2_interface(spec)
        self.assertIn("L2-01", result["violations"])
        self.assertEqual(result["missing_level1"], ["configure"])

    def test_dropped_level2_operation_violates_item_two(self):
        spec = clean_spec()
        spec["operations"].remove("restore")
        result = assess_level2_interface(spec)
        self.assertIn("L2-02", result["violations"])

    def test_foreign_operation_violates_item_three(self):
        spec = clean_spec()
        spec["operations"].append("rewind")
        result = assess_level2_interface(spec)
        self.assertIn("L2-03", result["violations"])
        self.assertEqual(result["unexpected"], ["rewind"])

    def test_widened_guard_violates_item_four(self):
        spec = clean_spec()
        spec["state_guards"]["store"] = ["standby", "executing"]
        result = assess_level2_interface(spec)
        self.assertIn("L2-04", result["violations"])

    def test_non_idempotent_hold_violates_item_five(self):
        spec = clean_spec()
        spec["hold_idempotent"] = False
        result = assess_level2_interface(spec)
        self.assertIn("L2-05", result["violations"])

    def test_non_positive_step_violates_item_six(self):
        spec = clean_spec()
        spec["step_ticks"] = 0
        result = assess_level2_interface(spec)
        self.assertIn("L2-06", result["violations"])

    def test_non_positive_time_scale_violates_item_seven(self):
        spec = clean_spec()
        spec["time_scale"] = -1.0
        result = assess_level2_interface(spec)
        self.assertIn("L2-07", result["violations"])

    def test_absent_optional_evidence_leaves_items_satisfied(self):
        spec = {"operations": list(LEVEL1_OPERATIONS) + list(LEVEL2_OPERATIONS)}
        result = assess_level2_interface(spec)
        self.assertTrue(result["compliant"])

    def test_missing_operations_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_level2_interface({"time_scale": 1.0})

    def test_empty_operations_rejected(self):
        with self.assertRaises(ValueError):
            assess_level2_interface({"operations": []})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_level2_interface(["run"])

    def test_non_mapping_state_guards_rejected(self):
        spec = clean_spec()
        spec["state_guards"] = ["hold"]
        with self.assertRaises(ValueError):
            assess_level2_interface(spec)

    def test_non_boolean_idempotence_rejected(self):
        spec = clean_spec()
        spec["resume_idempotent"] = "yes"
        with self.assertRaises(ValueError):
            assess_level2_interface(spec)

    def test_guard_results_are_keyed_by_canonical_name(self):
        spec = clean_spec()
        spec["state_guards"]["Set-Time Scale"] = ["standby"]
        del spec["state_guards"]["set_time_scale"]
        result = assess_level2_interface(spec)
        self.assertIn("set_time_scale", result["state_guards"])

    def test_every_item_carries_a_title_and_status(self):
        result = assess_level2_interface(clean_spec())
        for item in result["items"]:
            self.assertTrue(item["title"])
            self.assertIn(item["status"], ("satisfied", "violated"))


if __name__ == "__main__":
    unittest.main()
