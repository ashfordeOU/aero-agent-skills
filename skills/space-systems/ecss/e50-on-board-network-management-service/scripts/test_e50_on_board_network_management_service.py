"""Contract tests for the clause 5.7.2.4 network management service logic."""

import unittest

from e50_on_board_network_management_service_logic import (
    DEFAULT_OPERATIONS,
    MANAGED,
    PARTIAL,
    UNREACHABLE,
    assess_management_service,
    assess_resource,
    missing_operations,
    normalise_resource,
    path_faults,
    validate_name,
    validate_operations,
)

ROUTER = {
    "name": "router-a",
    "operations": ["configure", "monitor", "control"],
    "management_path": [],
}
NODE = {
    "name": "node-1",
    "operations": ["configure", "monitor", "control"],
    "management_path": ["router-a"],
}
READ_ONLY = {"name": "node-2", "operations": ["monitor"], "management_path": ["router-a"]}
SELF_MANAGED = {
    "name": "router-b",
    "operations": ["configure", "monitor", "control"],
    "management_path": ["router-b"],
}


class ValidationTests(unittest.TestCase):
    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_name("  ")

    def test_non_string_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_name(7)

    def test_name_is_trimmed(self):
        self.assertEqual(validate_name(" router-a "), "router-a")

    def test_a_bare_string_is_not_an_operation_list(self):
        with self.assertRaises(ValueError):
            validate_operations("monitor")

    def test_repeated_operation_rejected(self):
        with self.assertRaises(ValueError):
            validate_operations(["monitor", "monitor"])

    def test_operation_order_is_preserved(self):
        self.assertEqual(validate_operations(["monitor", "configure"]), ("monitor", "configure"))

    def test_non_mapping_resource_rejected(self):
        with self.assertRaises(ValueError):
            normalise_resource(["router-a"])

    def test_resource_without_operations_defaults_to_none_supported(self):
        self.assertEqual(normalise_resource({"name": "x"})["operations"], ())

    def test_duplicate_resource_name_rejected(self):
        with self.assertRaises(ValueError):
            assess_management_service([ROUTER, dict(ROUTER)])

    def test_empty_inventory_rejected(self):
        with self.assertRaises(ValueError):
            assess_management_service([])

    def test_non_list_inventory_rejected(self):
        with self.assertRaises(ValueError):
            assess_management_service(ROUTER)

    def test_non_collection_known_names_rejected(self):
        with self.assertRaises(ValueError):
            path_faults(ROUTER, "router-a")


class OperationCoverageTests(unittest.TestCase):
    def test_a_full_resource_misses_nothing(self):
        self.assertEqual(missing_operations(ROUTER), ())

    def test_a_read_only_resource_misses_two_operations(self):
        self.assertEqual(set(missing_operations(READ_ONLY)), {"configure", "control"})

    def test_the_default_operation_set_has_three_members(self):
        self.assertEqual(len(DEFAULT_OPERATIONS), 3)

    def test_an_extended_required_set_finds_more_gaps(self):
        gaps = missing_operations(ROUTER, ["configure", "monitor", "control", "reset"])
        self.assertEqual(gaps, ("reset",))

    def test_an_extra_operation_is_not_a_gap(self):
        rich = dict(ROUTER, operations=["configure", "monitor", "control", "reset"])
        self.assertEqual(missing_operations(rich), ())

    def test_coverage_is_the_fraction_supported(self):
        result = assess_resource(READ_ONLY, {"router-a", "node-2"})
        self.assertAlmostEqual(result["coverage"], 1.0 / 3.0, places=9)


class PathTests(unittest.TestCase):
    def test_an_independent_path_has_no_faults(self):
        self.assertEqual(path_faults(NODE, {"router-a", "node-1"}), ())

    def test_an_empty_path_has_no_faults(self):
        self.assertEqual(path_faults(ROUTER, {"router-a"}), ())

    def test_a_self_dependent_path_is_a_fault(self):
        faults = path_faults(SELF_MANAGED, {"router-b"})
        self.assertTrue(any("itself" in f for f in faults))

    def test_a_hop_outside_the_inventory_is_a_fault(self):
        stray = dict(NODE, management_path=["switch-x"])
        faults = path_faults(stray, {"router-a", "node-1"})
        self.assertTrue(any("not a managed resource" in f for f in faults))

    def test_a_known_hop_is_not_a_fault(self):
        self.assertEqual(path_faults(NODE, ["router-a", "node-1"]), ())


class ResourceVerdictTests(unittest.TestCase):
    def test_a_covered_independent_resource_is_managed(self):
        result = assess_resource(NODE, {"router-a", "node-1"})
        self.assertEqual(result["verdict"], MANAGED)
        self.assertEqual(result["reasons"], [])

    def test_a_read_only_resource_is_partial(self):
        result = assess_resource(READ_ONLY, {"router-a", "node-2"})
        self.assertEqual(result["verdict"], PARTIAL)

    def test_a_self_managed_resource_is_unreachable(self):
        result = assess_resource(SELF_MANAGED, {"router-b"})
        self.assertEqual(result["verdict"], UNREACHABLE)

    def test_a_path_fault_outranks_an_operation_gap(self):
        broken = dict(READ_ONLY, management_path=["node-2"])
        result = assess_resource(broken, {"node-2"})
        self.assertEqual(result["verdict"], UNREACHABLE)
        self.assertTrue(result["missing"])

    def test_the_missing_operations_are_named_in_the_reasons(self):
        result = assess_resource(READ_ONLY, {"router-a", "node-2"})
        self.assertTrue(any("control" in r for r in result["reasons"]))


class ServiceTests(unittest.TestCase):
    def test_a_sound_inventory_provides_the_service(self):
        result = assess_management_service([ROUTER, NODE])
        self.assertTrue(result["service_provided"])
        self.assertEqual(result["findings"], [])

    def test_full_coverage_reads_as_one(self):
        result = assess_management_service([ROUTER, NODE])
        self.assertAlmostEqual(result["coverage"], 1.0, places=9)

    def test_a_read_only_resource_breaks_coverage(self):
        result = assess_management_service([ROUTER, READ_ONLY])
        self.assertFalse(result["coverage_met"])
        self.assertIn("node-2", result["partial"])

    def test_coverage_ratio_counts_every_operation(self):
        result = assess_management_service([ROUTER, READ_ONLY])
        self.assertAlmostEqual(result["coverage"], 4.0 / 6.0, places=9)

    def test_a_self_managed_resource_breaks_path_independence(self):
        result = assess_management_service([ROUTER, SELF_MANAGED])
        self.assertFalse(result["paths_independent"])
        self.assertIn("router-b", result["unreachable"])

    def test_a_path_fault_does_not_hide_an_operation_gap(self):
        broken = dict(READ_ONLY, management_path=["node-2"])
        result = assess_management_service([ROUTER, broken])
        self.assertIn("node-2", result["with_gaps"])
        self.assertIn("node-2", result["unreachable"])

    def test_both_failures_are_reported_separately(self):
        broken = dict(READ_ONLY, management_path=["node-2"])
        result = assess_management_service([ROUTER, broken])
        self.assertEqual(len(result["findings"]), 2)

    def test_an_extended_required_set_can_fail_a_sound_inventory(self):
        result = assess_management_service(
            [ROUTER, NODE], ["configure", "monitor", "control", "reset"]
        )
        self.assertFalse(result["service_provided"])

    def test_the_required_set_is_carried_in_the_result(self):
        result = assess_management_service([ROUTER, NODE])
        self.assertEqual(result["required"], list(DEFAULT_OPERATIONS))

    def test_every_resource_appears_once_in_the_report(self):
        result = assess_management_service([ROUTER, NODE, READ_ONLY])
        self.assertEqual([r["resource"] for r in result["per_resource"]], result["resources"])

    def test_a_repeated_required_operation_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_management_service([ROUTER], ["monitor", "monitor"])


if __name__ == "__main__":
    unittest.main()
