"""Contract test for the e3311 non-explosive safe-and-arm leaf (stdlib unittest)."""

import unittest

from e3311_safe_arm_device_non_explosive_logic import (
    DEFAULT_SAFE_ARM_POLICY,
    SA_FUNCTIONS,
    SA_INTERFACES,
    VERDICT_MET,
    VERDICT_NOT_MET,
    assess_functions,
    assess_inhibits,
    assess_interfaces,
    assess_position_indication,
    assess_safe_arm_device,
    assess_timing_and_life,
    independent_inhibit_groups,
    validate_safe_arm_policy,
)


def inhibits(*entries):
    if entries:
        return list(entries)
    return [
        {"id": "relay-k1", "active_in_safe": True, "common_cause_group": None},
        {"id": "relay-k2", "active_in_safe": True, "common_cause_group": None},
    ]


def functions(**kw):
    declared = {name: True for name in SA_FUNCTIONS}
    declared.update(kw)
    return declared


def interfaces(**kw):
    declared = {
        "command": "J1",
        "monitor": "J2",
        "primary-power": "J3",
        "firing-output": "J4",
        "manual-safing": "J5",
    }
    declared.update(kw)
    return declared


def timing(**kw):
    case = {
        "arm_time_s": 0.4,
        "safing_time_s": 0.9,
        "qualified_cycles": 200,
        "planned_cycles": 30,
    }
    case.update(kw)
    return case


def full_case(**kw):
    case = {
        "inhibits": inhibits(),
        "functions": functions(),
        "indication_source": "interrupter-position",
        "interfaces": interfaces(),
        "timing_and_life": timing(),
    }
    case.update(kw)
    return case


class TestPolicyValidation(unittest.TestCase):
    def test_default_policy_is_valid(self):
        self.assertIs(
            validate_safe_arm_policy(DEFAULT_SAFE_ARM_POLICY), DEFAULT_SAFE_ARM_POLICY
        )

    def test_non_mapping_policy_raises(self):
        with self.assertRaises(ValueError):
            validate_safe_arm_policy(["required_independent_inhibits", 2])

    def test_zero_required_inhibits_raises(self):
        policy = dict(DEFAULT_SAFE_ARM_POLICY, required_independent_inhibits=0)
        with self.assertRaises(ValueError):
            validate_safe_arm_policy(policy)

    def test_non_positive_arm_time_limit_raises(self):
        policy = dict(DEFAULT_SAFE_ARM_POLICY, max_arm_time_s=0.0)
        with self.assertRaises(ValueError):
            validate_safe_arm_policy(policy)

    def test_unknown_required_interface_raises(self):
        policy = dict(DEFAULT_SAFE_ARM_POLICY, required_interfaces=("coolant",))
        with self.assertRaises(ValueError):
            validate_safe_arm_policy(policy)

    def test_empty_required_function_list_raises(self):
        policy = dict(DEFAULT_SAFE_ARM_POLICY, required_functions=())
        with self.assertRaises(ValueError):
            validate_safe_arm_policy(policy)


class TestInhibitGrouping(unittest.TestCase):
    def test_two_standalone_inhibits_count_twice(self):
        grouping = independent_inhibit_groups(inhibits())
        self.assertEqual(grouping["independent_count"], 2)
        self.assertEqual(grouping["standalone"], ["relay-k1", "relay-k2"])

    def test_a_shared_common_cause_collapses_to_one(self):
        entries = inhibits(
            {"id": "k1", "active_in_safe": True, "common_cause_group": "coil-a"},
            {"id": "k2", "active_in_safe": True, "common_cause_group": "coil-a"},
        )
        grouping = independent_inhibit_groups(entries)
        self.assertEqual(grouping["independent_count"], 1)
        self.assertEqual(grouping["grouped"]["coil-a"], ["k1", "k2"])

    def test_an_inhibit_inactive_in_safe_does_not_count(self):
        entries = inhibits(
            {"id": "k1", "active_in_safe": True, "common_cause_group": None},
            {"id": "k2", "active_in_safe": False, "common_cause_group": None},
        )
        self.assertEqual(independent_inhibit_groups(entries)["independent_count"], 1)

    def test_a_mixed_set_counts_groups_plus_standalone(self):
        entries = inhibits(
            {"id": "k1", "active_in_safe": True, "common_cause_group": "coil-a"},
            {"id": "k2", "active_in_safe": True, "common_cause_group": "coil-a"},
            {"id": "s1", "active_in_safe": True, "common_cause_group": None},
        )
        self.assertEqual(independent_inhibit_groups(entries)["independent_count"], 2)

    def test_a_duplicate_inhibit_id_raises(self):
        entries = inhibits(
            {"id": "k1", "active_in_safe": True, "common_cause_group": None},
            {"id": "k1", "active_in_safe": True, "common_cause_group": None},
        )
        with self.assertRaises(ValueError):
            independent_inhibit_groups(entries)

    def test_an_empty_inhibit_list_raises(self):
        with self.assertRaises(ValueError):
            independent_inhibit_groups([])

    def test_a_missing_active_flag_raises(self):
        with self.assertRaises(ValueError):
            independent_inhibit_groups([{"id": "k1"}])

    def test_a_non_boolean_active_flag_raises(self):
        with self.assertRaises(ValueError):
            independent_inhibit_groups([{"id": "k1", "active_in_safe": 1}])


class TestInhibitAssessment(unittest.TestCase):
    def test_two_independent_inhibits_pass(self):
        result = assess_inhibits(inhibits())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_a_single_inhibit_fails(self):
        entries = [{"id": "k1", "active_in_safe": True, "common_cause_group": None}]
        result = assess_inhibits(entries)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["independent_count"], 1)

    def test_two_inhibits_on_one_coil_fail_and_say_why(self):
        entries = inhibits(
            {"id": "k1", "active_in_safe": True, "common_cause_group": "coil-a"},
            {"id": "k2", "active_in_safe": True, "common_cause_group": "coil-a"},
        )
        result = assess_inhibits(entries)
        self.assertFalse(result["compliant"])
        self.assertTrue(any("common cause" in f for f in result["findings"]))

    def test_a_three_inhibit_policy_rejects_a_two_inhibit_device(self):
        policy = dict(DEFAULT_SAFE_ARM_POLICY, required_independent_inhibits=3)
        result = assess_inhibits(inhibits(), policy)
        self.assertFalse(result["compliant"])


class TestFunctions(unittest.TestCase):
    def test_a_complete_function_set_passes(self):
        result = assess_functions(functions())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["functions_absent"], [])

    def test_a_missing_function_is_named(self):
        result = assess_functions(
            functions(**{"manual-safing-without-primary-power": False})
        )
        self.assertFalse(result["compliant"])
        self.assertIn(
            "manual-safing-without-primary-power", result["functions_absent"]
        )

    def test_an_undeclared_function_raises(self):
        declared = functions()
        del declared["remote-arm-and-disarm-command"]
        with self.assertRaises(ValueError):
            assess_functions(declared)

    def test_an_unknown_function_key_raises(self):
        with self.assertRaises(ValueError):
            assess_functions(functions(**{"self-destruct": True}))


class TestPositionIndication(unittest.TestCase):
    def test_an_interrupter_driven_indication_passes(self):
        result = assess_position_indication("interrupter-position")
        self.assertTrue(result["compliant"])

    def test_a_commanded_state_indication_is_a_finding(self):
        result = assess_position_indication("commanded-state")
        self.assertFalse(result["compliant"])
        self.assertEqual(len(result["findings"]), 1)

    def test_a_coil_current_indication_is_a_finding(self):
        result = assess_position_indication("drive-coil-current")
        self.assertFalse(result["compliant"])

    def test_an_unknown_indication_source_raises(self):
        with self.assertRaises(ValueError):
            assess_position_indication("operator-memory")


class TestInterfaces(unittest.TestCase):
    def test_five_separate_connectors_pass(self):
        result = assess_interfaces(interfaces())
        self.assertTrue(result["compliant"])
        self.assertEqual(sorted(result["connectors"]), sorted(SA_INTERFACES))

    def test_command_sharing_the_firing_shell_is_a_finding(self):
        result = assess_interfaces(interfaces(command="J4"))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("firing" in f for f in result["findings"]))

    def test_monitor_sharing_the_firing_shell_is_a_finding(self):
        result = assess_interfaces(interfaces(monitor="J4"))
        self.assertFalse(result["compliant"])

    def test_separation_can_be_waived_by_policy(self):
        policy = dict(
            DEFAULT_SAFE_ARM_POLICY, separate_command_and_firing_connectors=False
        )
        result = assess_interfaces(interfaces(command="J4"), policy)
        self.assertTrue(result["compliant"])

    def test_an_undeclared_interface_raises(self):
        declared = interfaces()
        del declared["manual-safing"]
        with self.assertRaises(ValueError):
            assess_interfaces(declared)

    def test_a_blank_connector_name_raises(self):
        with self.assertRaises(ValueError):
            assess_interfaces(interfaces(monitor="   "))


class TestTimingAndLife(unittest.TestCase):
    def test_a_prompt_device_passes(self):
        result = assess_timing_and_life(timing())
        self.assertTrue(result["compliant"])

    def test_an_arm_time_exactly_on_the_limit_passes(self):
        result = assess_timing_and_life(timing(arm_time_s=1.0))
        self.assertAlmostEqual(result["arm_time_s"], 1.0, places=9)
        self.assertTrue(result["compliant"])

    def test_a_slow_arm_fails(self):
        result = assess_timing_and_life(timing(arm_time_s=3.0))
        self.assertFalse(result["compliant"])

    def test_a_slow_safing_fails(self):
        result = assess_timing_and_life(timing(safing_time_s=5.0))
        self.assertFalse(result["compliant"])

    def test_an_underqualified_cycle_life_fails(self):
        result = assess_timing_and_life(timing(qualified_cycles=10))
        self.assertFalse(result["compliant"])

    def test_a_plan_beyond_the_qualified_life_fails(self):
        result = assess_timing_and_life(timing(qualified_cycles=60, planned_cycles=90))
        self.assertFalse(result["compliant"])

    def test_a_non_integer_cycle_count_raises(self):
        with self.assertRaises(ValueError):
            assess_timing_and_life(timing(qualified_cycles=200.5))


class TestFullAssessment(unittest.TestCase):
    def test_a_sound_device_is_met(self):
        report = assess_safe_arm_device(full_case())
        self.assertEqual(report["verdict"], VERDICT_MET)
        self.assertEqual(report["failed_parts"], [])
        self.assertEqual(report["findings"], [])

    def test_one_broken_part_names_only_itself(self):
        report = assess_safe_arm_device(full_case(indication_source="commanded-state"))
        self.assertEqual(report["verdict"], VERDICT_NOT_MET)
        self.assertEqual(report["failed_parts"], ["position-indication"])

    def test_several_broken_parts_are_all_named(self):
        case = full_case(
            inhibits=[
                {"id": "k1", "active_in_safe": True, "common_cause_group": "coil-a"},
                {"id": "k2", "active_in_safe": True, "common_cause_group": "coil-a"},
            ],
            interfaces=interfaces(command="J4"),
        )
        report = assess_safe_arm_device(case)
        self.assertEqual(report["failed_parts"], ["inhibits", "interfaces"])
        self.assertGreaterEqual(len(report["findings"]), 3)

    def test_every_part_appears_in_the_report(self):
        report = assess_safe_arm_device(full_case())
        for name in (
            "inhibits",
            "functions",
            "position-indication",
            "interfaces",
            "timing-and-life",
        ):
            self.assertIn(name, report["parts"])

    def test_a_non_mapping_case_raises(self):
        with self.assertRaises(ValueError):
            assess_safe_arm_device("two inhibits")

    def test_a_case_without_inhibits_raises(self):
        case = full_case()
        del case["inhibits"]
        with self.assertRaises(ValueError):
            assess_safe_arm_device(case)


if __name__ == "__main__":
    unittest.main()
