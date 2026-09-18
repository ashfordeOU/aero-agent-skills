#!/usr/bin/env python3
"""Contract test for the status readout independence judgement (offline)."""

import copy
import unittest

from e2020_status_reading_failure_independence_logic import (
    COMMAND_DERIVED,
    COMMAND_POWER_ELEMENT,
    INDEPENDENT_SENSING,
    SHARED_SENSING,
    STATUS_COMMAND_DERIVED_ONLY,
    STATUS_INDEPENDENT,
    STATUS_SHARED_SINGLE_POINT,
    assess_status_independence,
    blinding_elements,
    categorize_path,
    categorize_paths,
    independent_path_ids,
    senses_device_state,
    validate_architecture,
)

COMMAND_CHAIN = [
    "command-decoder",
    "command-driver",
    "harness-segment-a",
    "device-connector",
]

GOOD_ARCH = {
    "command_chain": COMMAND_CHAIN,
    "command_power_domain": "command-bus",
    "paths": [
        {
            "id": "p1",
            "source": "device-contact",
            "shared_elements": [],
            "powered_from": "telemetry-bus",
        },
        {
            "id": "p2",
            "source": "command-echo",
            "shared_elements": ["command-decoder"],
            "powered_from": "command-bus",
        },
    ],
}

SHARED_ARCH = {
    "command_chain": COMMAND_CHAIN,
    "command_power_domain": "command-bus",
    "paths": [
        {
            "id": "s1",
            "source": "device-contact",
            "shared_elements": ["device-connector"],
            "powered_from": "telemetry-bus",
        },
        {
            "id": "s2",
            "source": "load-current-sense",
            "shared_elements": ["device-connector", "harness-segment-a"],
            "powered_from": "telemetry-bus",
        },
    ],
}

ECHO_ARCH = {
    "command_chain": COMMAND_CHAIN,
    "command_power_domain": "command-bus",
    "paths": [
        {
            "id": "e1",
            "source": "command-echo",
            "shared_elements": ["command-decoder"],
            "powered_from": "command-bus",
        },
        {
            "id": "e2",
            "source": "commanded-state-memory",
            "shared_elements": [],
            "powered_from": "command-bus",
        },
    ],
}


def _arch(base, **overrides):
    architecture = copy.deepcopy(base)
    architecture.update(overrides)
    return architecture


class ValidationTests(unittest.TestCase):
    def test_good_architecture_validates(self):
        self.assertIs(validate_architecture(GOOD_ARCH), GOOD_ARCH)

    def test_non_mapping_architecture_rejected(self):
        with self.assertRaises(ValueError):
            validate_architecture("two relays and a telemetry line")

    def test_empty_command_chain_rejected(self):
        with self.assertRaises(ValueError):
            validate_architecture(_arch(GOOD_ARCH, command_chain=[]))

    def test_missing_paths_rejected(self):
        architecture = _arch(GOOD_ARCH)
        del architecture["paths"]
        with self.assertRaises(ValueError):
            validate_architecture(architecture)

    def test_duplicate_path_id_rejected(self):
        architecture = copy.deepcopy(GOOD_ARCH)
        architecture["paths"][1]["id"] = "p1"
        with self.assertRaises(ValueError):
            validate_architecture(architecture)

    def test_unknown_source_rejected(self):
        architecture = copy.deepcopy(GOOD_ARCH)
        architecture["paths"][0]["source"] = "operator-confidence"
        with self.assertRaises(ValueError):
            validate_architecture(architecture)

    def test_non_sequence_shared_elements_rejected(self):
        architecture = copy.deepcopy(GOOD_ARCH)
        architecture["paths"][0]["shared_elements"] = "device-connector"
        with self.assertRaises(ValueError):
            validate_architecture(architecture)

    def test_empty_element_name_rejected(self):
        architecture = copy.deepcopy(GOOD_ARCH)
        architecture["paths"][0]["shared_elements"] = ["  "]
        with self.assertRaises(ValueError):
            validate_architecture(architecture)

    def test_path_without_an_id_rejected(self):
        architecture = copy.deepcopy(GOOD_ARCH)
        del architecture["paths"][0]["id"]
        with self.assertRaises(ValueError):
            validate_architecture(architecture)


class SourceTests(unittest.TestCase):
    def test_a_device_contact_senses_the_device(self):
        self.assertTrue(senses_device_state("device-contact"))

    def test_a_command_echo_does_not_sense_the_device(self):
        self.assertFalse(senses_device_state("command-echo"))

    def test_a_register_readback_does_not_sense_the_device(self):
        self.assertFalse(senses_device_state("driver-register-readback"))

    def test_an_unknown_source_rejected(self):
        with self.assertRaises(ValueError):
            senses_device_state("telepathy")


class PathCategoryTests(unittest.TestCase):
    def test_a_sensing_path_sharing_nothing_is_independent(self):
        result = categorize_path(GOOD_ARCH["paths"][0], COMMAND_CHAIN, "command-bus")
        self.assertEqual(result["category"], INDEPENDENT_SENSING)
        self.assertEqual(result["shared_elements"], [])

    def test_a_sensing_path_through_the_chain_is_shared(self):
        result = categorize_path(SHARED_ARCH["paths"][0], COMMAND_CHAIN, "command-bus")
        self.assertEqual(result["category"], SHARED_SENSING)
        self.assertEqual(result["shared_elements"], ["device-connector"])

    def test_an_echo_path_is_command_derived_whatever_it_shares(self):
        path = {"id": "x", "source": "command-echo", "shared_elements": []}
        result = categorize_path(path, COMMAND_CHAIN)
        self.assertEqual(result["category"], COMMAND_DERIVED)
        self.assertTrue(any("ordered state" in f for f in result["findings"]))

    def test_command_power_makes_a_sensing_path_shared(self):
        path = {
            "id": "p9",
            "source": "independent-sensor",
            "shared_elements": [],
            "powered_from": "command-bus",
        }
        result = categorize_path(path, COMMAND_CHAIN, "command-bus")
        self.assertEqual(result["category"], SHARED_SENSING)
        self.assertIn(COMMAND_POWER_ELEMENT, result["shared_elements"])

    def test_another_power_domain_leaves_the_path_independent(self):
        path = {
            "id": "p9",
            "source": "independent-sensor",
            "shared_elements": [],
            "powered_from": "telemetry-bus",
        }
        self.assertEqual(
            categorize_path(path, COMMAND_CHAIN, "command-bus")["category"],
            INDEPENDENT_SENSING,
        )

    def test_a_shared_element_outside_the_chain_is_only_a_finding(self):
        path = {
            "id": "p9",
            "source": "device-contact",
            "shared_elements": ["thermal-strap"],
        }
        result = categorize_path(path, COMMAND_CHAIN)
        self.assertEqual(result["category"], INDEPENDENT_SENSING)
        self.assertTrue(any("not in the command chain" in f for f in result["findings"]))

    def test_categorizing_every_path_keeps_the_declared_order(self):
        self.assertEqual(
            [entry["id"] for entry in categorize_paths(GOOD_ARCH)], ["p1", "p2"]
        )


class BlindingElementTests(unittest.TestCase):
    def test_an_independent_path_leaves_nothing_blinding(self):
        self.assertEqual(blinding_elements(GOOD_ARCH), [])

    def test_the_common_element_of_every_sensing_path_blinds_the_readout(self):
        self.assertEqual(blinding_elements(SHARED_ARCH), ["device-connector"])

    def test_an_element_on_only_one_sensing_path_does_not_blind(self):
        self.assertNotIn("harness-segment-a", blinding_elements(SHARED_ARCH))

    def test_with_no_sensing_path_the_whole_chain_blinds(self):
        self.assertEqual(blinding_elements(ECHO_ARCH), sorted(COMMAND_CHAIN))

    def test_independent_path_ids_lists_only_independent_paths(self):
        self.assertEqual(independent_path_ids(GOOD_ARCH), ["p1"])


class AssessmentTests(unittest.TestCase):
    def test_an_independent_sensing_path_meets_the_requirement(self):
        result = assess_status_independence(GOOD_ARCH)
        self.assertEqual(result["verdict"], STATUS_INDEPENDENT)
        self.assertEqual(result["independent_path_ids"], ["p1"])
        self.assertEqual(result["command_derived_path_ids"], ["p2"])
        self.assertFalse(result["redundant"])

    def test_only_shared_sensing_is_a_single_point(self):
        result = assess_status_independence(SHARED_ARCH)
        self.assertEqual(result["verdict"], STATUS_SHARED_SINGLE_POINT)
        self.assertEqual(result["independent_path_ids"], [])
        self.assertEqual(result["sensing_path_count"], 2)
        self.assertTrue(any("fails with the interface" in f for f in result["findings"]))
        self.assertTrue(any("device-connector" in d for d in result["duties"]))

    def test_only_echo_paths_cannot_witness_the_device(self):
        result = assess_status_independence(ECHO_ARCH)
        self.assertEqual(result["verdict"], STATUS_COMMAND_DERIVED_ONLY)
        self.assertEqual(result["sensing_path_count"], 0)
        self.assertTrue(any("repeats the order" in f for f in result["findings"]))
        self.assertTrue(any("achieved device state" in d for d in result["duties"]))

    def test_two_independent_paths_are_reported_as_redundant(self):
        architecture = copy.deepcopy(GOOD_ARCH)
        architecture["paths"].append(
            {
                "id": "p3",
                "source": "position-switch",
                "shared_elements": [],
                "powered_from": "telemetry-bus",
            }
        )
        result = assess_status_independence(architecture)
        self.assertTrue(result["redundant"])
        self.assertEqual(result["independent_path_count"], 2)

    def test_a_shared_path_beside_an_independent_one_is_still_recorded(self):
        architecture = copy.deepcopy(GOOD_ARCH)
        architecture["paths"].append(
            {
                "id": "p4",
                "source": "load-current-sense",
                "shared_elements": ["harness-segment-a"],
                "powered_from": "telemetry-bus",
            }
        )
        result = assess_status_independence(architecture)
        self.assertEqual(result["verdict"], STATUS_INDEPENDENT)
        self.assertEqual(result["shared_path_ids"], ["p4"])
        self.assertTrue(any("command-dependent" in d for d in result["duties"]))

    def test_losing_command_power_demotes_the_only_sensing_path(self):
        architecture = copy.deepcopy(GOOD_ARCH)
        architecture["paths"][0]["powered_from"] = "command-bus"
        result = assess_status_independence(architecture)
        self.assertEqual(result["verdict"], STATUS_SHARED_SINGLE_POINT)
        self.assertEqual(result["blinding_elements"], [COMMAND_POWER_ELEMENT])

    def test_assessment_rejects_a_broken_architecture(self):
        architecture = copy.deepcopy(GOOD_ARCH)
        architecture["paths"][0]["source"] = "wishful-thinking"
        with self.assertRaises(ValueError):
            assess_status_independence(architecture)


if __name__ == "__main__":
    unittest.main()
