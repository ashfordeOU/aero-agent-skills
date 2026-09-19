#!/usr/bin/env python3
"""Gate 3 contract test for e2040-device-architecture-definition-task.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_device_architecture_definition_task.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_device_architecture_definition_task_logic import (  # noqa: E402
    ASSURANCE_LEVELS,
    RESOURCES,
    assurance_rank,
    define_device_architecture,
    normalize_assurance,
    normalize_direction,
    partition_membership,
    resource_rollup,
    utilisation,
    validate_allocations,
    validate_blocks,
    validate_interfaces,
    validate_partitions,
    validate_resources,
    within_budget,
)


def base_architecture():
    return {
        "partitions": [
            {"name": "control", "rationale": "command path kept separate"},
            {"name": "payload-io"},
        ],
        "blocks": [
            {
                "id": "BLK-CTRL",
                "function": "device command decode",
                "partition": "control",
                "assurance": "B",
                "resources": {"power_w": 1.5, "mass_g": 40.0, "area_mm2": 600.0},
            },
            {
                "id": "BLK-IO",
                "function": "payload data interface",
                "partition": "payload-io",
                "assurance": "C",
                "resources": {"power_w": 2.5, "mass_g": 60.0, "area_mm2": 900.0},
            },
        ],
        "interfaces": [
            {
                "id": "IF-1",
                "endpoints": ["BLK-CTRL", "BLK-IO"],
                "protocol": "internal register bus",
                "direction": "bidirectional",
            }
        ],
        "allocations": [
            {"requirement": "R-1", "block": "BLK-CTRL"},
            {"requirement": "R-2", "block": "BLK-IO"},
        ],
        "budgets": {"power_w": 4.0, "mass_g": 120.0, "area_mm2": 2000.0},
    }


def codes(result):
    return sorted({f["code"] for f in result["findings"]})


class TestFolding(unittest.TestCase):
    def test_dal_form_folds_to_a_level(self):
        self.assertEqual(normalize_assurance("DAL B"), "B")

    def test_lowercase_level_folds(self):
        self.assertEqual(normalize_assurance("d"), "D")

    def test_unknown_level_rejected(self):
        with self.assertRaises(ValueError):
            normalize_assurance("E")

    def test_level_a_is_the_most_demanding(self):
        self.assertLess(assurance_rank("A"), assurance_rank("D"))

    def test_duplex_folds_to_bidirectional(self):
        self.assertEqual(normalize_direction("duplex"), "bidirectional")

    def test_unknown_direction_rejected(self):
        with self.assertRaises(ValueError):
            normalize_direction("radial")

    def test_four_assurance_levels_are_the_whole_scale(self):
        self.assertEqual(len(ASSURANCE_LEVELS), 4)

    def test_three_resources_roll_up(self):
        self.assertEqual(len(RESOURCES), 3)


class TestResourceHandling(unittest.TestCase):
    def test_absent_resources_fill_with_zero(self):
        self.assertEqual(validate_resources(None)["power_w"], 0.0)

    def test_unknown_resource_rejected(self):
        with self.assertRaises(ValueError):
            validate_resources({"volume_cm3": 3})

    def test_negative_resource_rejected(self):
        with self.assertRaises(ValueError):
            validate_resources({"power_w": -1})

    def test_rollup_sums_every_block(self):
        blocks = validate_blocks(base_architecture()["blocks"])
        self.assertAlmostEqual(resource_rollup(blocks)["power_w"], 4.0, places=9)
        self.assertAlmostEqual(resource_rollup(blocks)["mass_g"], 100.0, places=9)

    def test_rollup_can_be_taken_over_one_partition(self):
        blocks = validate_blocks(base_architecture()["blocks"])
        totals = resource_rollup(blocks, ["BLK-CTRL"])
        self.assertAlmostEqual(totals["area_mm2"], 600.0, places=9)

    def test_rollup_of_an_unknown_block_rejected(self):
        blocks = validate_blocks(base_architecture()["blocks"])
        with self.assertRaises(ValueError):
            resource_rollup(blocks, ["BLK-NOPE"])

    def test_a_rollup_landing_exactly_on_budget_is_within_it(self):
        self.assertTrue(within_budget(1.5 + 2.5, 4.0))

    def test_a_rollup_landing_on_a_tenths_sum_is_within_budget(self):
        self.assertTrue(within_budget(0.1 + 0.2, 0.3))

    def test_a_rollup_over_budget_is_reported(self):
        self.assertFalse(within_budget(4.1, 4.0))

    def test_utilisation_is_the_fraction_consumed(self):
        self.assertAlmostEqual(utilisation(2.0, 4.0), 0.5, places=9)

    def test_utilisation_against_a_zero_budget_rejected(self):
        with self.assertRaises(ValueError):
            utilisation(1.0, 0.0)


class TestValidation(unittest.TestCase):
    def test_blocks_resolve_by_identifier(self):
        blocks = validate_blocks(base_architecture()["blocks"])
        self.assertEqual(sorted(blocks), ["BLK-CTRL", "BLK-IO"])

    def test_duplicate_block_id_rejected(self):
        entries = base_architecture()["blocks"]
        entries.append(dict(entries[0]))
        with self.assertRaises(ValueError):
            validate_blocks(entries)

    def test_unknown_block_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocks([{"id": "B", "function": "f", "vendor": "x"}])

    def test_block_without_a_function_rejected(self):
        with self.assertRaises(ValueError):
            validate_blocks([{"id": "B"}])

    def test_an_interface_with_one_endpoint_rejected(self):
        with self.assertRaises(ValueError):
            validate_interfaces([{"id": "IF", "endpoints": ["BLK-CTRL"]}])

    def test_an_interface_looping_to_itself_rejected(self):
        with self.assertRaises(ValueError):
            validate_interfaces([{"id": "IF", "endpoints": ["BLK-A", "BLK-A"]}])

    def test_duplicate_interface_id_rejected(self):
        entries = base_architecture()["interfaces"]
        entries.append(dict(entries[0]))
        with self.assertRaises(ValueError):
            validate_interfaces(entries)

    def test_duplicate_allocation_rejected(self):
        entries = base_architecture()["allocations"]
        entries.append(dict(entries[0]))
        with self.assertRaises(ValueError):
            validate_allocations(entries)

    def test_allocation_without_a_block_rejected(self):
        with self.assertRaises(ValueError):
            validate_allocations([{"requirement": "R-1"}])

    def test_duplicate_partition_rejected(self):
        with self.assertRaises(ValueError):
            validate_partitions([{"name": "control"}, {"name": "control"}])

    def test_non_boolean_mixed_criticality_rejected(self):
        with self.assertRaises(ValueError):
            validate_partitions([{"name": "control", "mixed_criticality": "yes"}])

    def test_membership_groups_blocks_by_partition(self):
        blocks = validate_blocks(base_architecture()["blocks"])
        self.assertEqual(
            partition_membership(blocks), {"control": ["BLK-CTRL"], "payload-io": ["BLK-IO"]}
        )


class TestDefineArchitecture(unittest.TestCase):
    def test_a_coherent_architecture_is_documented(self):
        result = define_device_architecture(base_architecture())
        self.assertTrue(result["documented"])
        self.assertEqual(result["findings"], [])

    def test_the_rollup_reaches_the_result(self):
        result = define_device_architecture(base_architecture())
        self.assertAlmostEqual(result["resource_rollup"]["power_w"], 4.0, places=9)
        self.assertEqual(result["over_budget_resources"], [])

    def test_a_rollup_landing_exactly_on_budget_does_not_fail(self):
        result = define_device_architecture(base_architecture())
        self.assertNotIn("resource-rollup-over-budget", codes(result))

    def test_a_rollup_over_budget_is_reported(self):
        architecture = base_architecture()
        architecture["budgets"]["power_w"] = 3.0
        result = define_device_architecture(architecture)
        self.assertIn("resource-rollup-over-budget", codes(result))
        self.assertEqual(result["over_budget_resources"], ["power_w"])

    def test_a_block_outside_the_partitioning_is_reported(self):
        architecture = base_architecture()
        architecture["blocks"][1]["partition"] = ""
        result = define_device_architecture(architecture)
        self.assertIn("block-outside-partitioning", codes(result))

    def test_a_block_in_an_undeclared_partition_is_reported(self):
        architecture = base_architecture()
        architecture["blocks"][1]["partition"] = "telemetry"
        result = define_device_architecture(architecture)
        self.assertIn("block-in-undeclared-partition", codes(result))

    def test_a_partition_mixing_levels_without_a_declaration_is_reported(self):
        architecture = base_architecture()
        architecture["blocks"][1]["partition"] = "control"
        result = define_device_architecture(architecture)
        self.assertIn("partition-mixes-assurance-levels", codes(result))

    def test_a_declared_mixed_partition_is_accepted(self):
        architecture = base_architecture()
        architecture["blocks"][1]["partition"] = "control"
        architecture["partitions"][0]["mixed_criticality"] = True
        result = define_device_architecture(architecture)
        self.assertNotIn("partition-mixes-assurance-levels", codes(result))

    def test_a_dangling_interface_endpoint_is_reported(self):
        architecture = base_architecture()
        architecture["interfaces"][0]["endpoints"] = ["BLK-CTRL", "BLK-GHOST"]
        result = define_device_architecture(architecture)
        self.assertIn("interface-endpoint-not-a-block", codes(result))

    def test_an_interface_without_a_protocol_is_reported(self):
        architecture = base_architecture()
        architecture["interfaces"][0]["protocol"] = ""
        result = define_device_architecture(architecture)
        self.assertIn("interface-without-protocol", codes(result))

    def test_an_unconnected_block_is_reported(self):
        architecture = base_architecture()
        architecture["interfaces"] = []
        result = define_device_architecture(architecture)
        self.assertIn("block-without-interface", codes(result))

    def test_an_allocation_to_an_unknown_block_is_reported(self):
        architecture = base_architecture()
        architecture["allocations"][1]["block"] = "BLK-GHOST"
        result = define_device_architecture(architecture)
        self.assertIn("allocation-to-unknown-block", codes(result))

    def test_a_block_with_no_allocated_requirement_is_reported(self):
        architecture = base_architecture()
        architecture["allocations"] = [{"requirement": "R-1", "block": "BLK-CTRL"}]
        result = define_device_architecture(architecture)
        self.assertIn("block-without-allocated-requirement", codes(result))

    def test_unknown_architecture_key_rejected(self):
        architecture = base_architecture()
        architecture["owner"] = "someone"
        with self.assertRaises(ValueError):
            define_device_architecture(architecture)

    def test_missing_allocations_rejected(self):
        architecture = base_architecture()
        del architecture["allocations"]
        with self.assertRaises(ValueError):
            define_device_architecture(architecture)

    def test_an_architecture_with_no_block_rejected(self):
        architecture = base_architecture()
        architecture["blocks"] = []
        with self.assertRaises(ValueError):
            define_device_architecture(architecture)

    def test_non_mapping_architecture_rejected(self):
        with self.assertRaises(ValueError):
            define_device_architecture([("blocks", [])])


if __name__ == "__main__":
    unittest.main()
