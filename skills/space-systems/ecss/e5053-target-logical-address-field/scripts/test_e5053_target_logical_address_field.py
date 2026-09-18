#!/usr/bin/env python3
"""Contract test for the target logical address field (offline)."""

import copy
import unittest

from e5053_target_logical_address_field_logic import (
    ASSIGNED_LOGICAL_ADDRESS,
    DEFAULT_LOGICAL,
    DEFAULT_LOGICAL_ADDRESS,
    DEFAULT_SOURCE,
    PATH_ADDRESS,
    PATH_ADDRESS_MAX,
    REGISTRY_SOURCE,
    RESERVED_LOGICAL,
    assess_target_logical_address_field,
    categorize_address,
    decode_address_prefix,
    encode_address_prefix,
    is_logical_address,
    resolve_target_logical_address,
    validate_target_logical_address,
)

REGISTRY = {"obc": 40, "transponder": 82, "spare-unit": None}

BASE_CASE = {
    "destination_node": "obc",
    "registry": REGISTRY,
    "path_addresses": (3, 7),
}


def _case(**overrides):
    case = copy.deepcopy(BASE_CASE)
    case.update(overrides)
    return case


class AddressCategoryTests(unittest.TestCase):
    def test_low_octet_is_a_path_address(self):
        self.assertEqual(categorize_address(0), PATH_ADDRESS)
        self.assertEqual(categorize_address(PATH_ADDRESS_MAX), PATH_ADDRESS)

    def test_first_octet_above_the_path_range_is_assignable(self):
        self.assertEqual(categorize_address(32), ASSIGNED_LOGICAL_ADDRESS)

    def test_default_address_has_its_own_category(self):
        self.assertEqual(
            categorize_address(DEFAULT_LOGICAL_ADDRESS), DEFAULT_LOGICAL
        )

    def test_top_of_the_space_is_reserved(self):
        self.assertEqual(categorize_address(255), RESERVED_LOGICAL)

    def test_only_assignable_and_default_octets_are_logical_addresses(self):
        self.assertTrue(is_logical_address(40))
        self.assertTrue(is_logical_address(DEFAULT_LOGICAL_ADDRESS))
        self.assertFalse(is_logical_address(10))
        self.assertFalse(is_logical_address(255))

    def test_octet_above_one_byte_rejected(self):
        with self.assertRaises(ValueError):
            categorize_address(256)

    def test_negative_octet_rejected(self):
        with self.assertRaises(ValueError):
            categorize_address(-1)

    def test_boolean_octet_rejected(self):
        with self.assertRaises(ValueError):
            categorize_address(True)

    def test_non_integer_octet_rejected(self):
        with self.assertRaises(ValueError):
            categorize_address("0x28")


class ValidateFieldTests(unittest.TestCase):
    def test_assignable_address_is_usable_without_a_finding(self):
        graded = validate_target_logical_address(40)
        self.assertTrue(graded["usable"])
        self.assertEqual(graded["findings"], [])

    def test_path_range_octet_is_not_usable(self):
        graded = validate_target_logical_address(5)
        self.assertFalse(graded["usable"])
        self.assertTrue(any("router" in f for f in graded["findings"]))

    def test_reserved_octet_is_not_usable(self):
        graded = validate_target_logical_address(255)
        self.assertFalse(graded["usable"])
        self.assertTrue(any("reserved" in f for f in graded["findings"]))

    def test_default_address_is_usable_but_flagged(self):
        graded = validate_target_logical_address(DEFAULT_LOGICAL_ADDRESS)
        self.assertTrue(graded["usable"])
        self.assertTrue(any("default" in f for f in graded["findings"]))


class ResolveTests(unittest.TestCase):
    def test_registered_node_takes_its_registered_address(self):
        resolved = resolve_target_logical_address("transponder", REGISTRY)
        self.assertEqual(resolved["target_logical_address"], 82)
        self.assertEqual(resolved["source"], REGISTRY_SOURCE)
        self.assertEqual(resolved["findings"], [])

    def test_unaddressed_node_falls_back_to_the_default_address(self):
        resolved = resolve_target_logical_address("spare-unit", REGISTRY)
        self.assertEqual(
            resolved["target_logical_address"], DEFAULT_LOGICAL_ADDRESS
        )
        self.assertEqual(resolved["source"], DEFAULT_SOURCE)
        self.assertTrue(any("default" in f for f in resolved["findings"]))

    def test_fallback_can_be_refused(self):
        with self.assertRaises(ValueError):
            resolve_target_logical_address(
                "spare-unit", REGISTRY, allow_default=False
            )

    def test_unknown_node_rejected(self):
        with self.assertRaises(ValueError):
            resolve_target_logical_address("ghost", REGISTRY)

    def test_non_mapping_registry_rejected(self):
        with self.assertRaises(ValueError):
            resolve_target_logical_address("obc", [("obc", 40)])

    def test_empty_node_name_rejected(self):
        with self.assertRaises(ValueError):
            resolve_target_logical_address("", REGISTRY)

    def test_node_registered_in_the_path_range_rejected(self):
        with self.assertRaises(ValueError):
            resolve_target_logical_address("bad", {"bad": 9})


class PrefixTests(unittest.TestCase):
    def test_prefix_puts_the_path_bytes_first(self):
        self.assertEqual(encode_address_prefix(40, (3, 7)), (3, 7, 40))

    def test_prefix_without_a_path_is_one_octet(self):
        self.assertEqual(encode_address_prefix(82), (82,))

    def test_path_byte_carrying_a_logical_address_rejected(self):
        with self.assertRaises(ValueError):
            encode_address_prefix(40, (3, 90))

    def test_prefix_with_a_reserved_target_rejected(self):
        with self.assertRaises(ValueError):
            encode_address_prefix(255)

    def test_prefix_with_a_path_range_target_rejected(self):
        with self.assertRaises(ValueError):
            encode_address_prefix(9)

    def test_non_sequence_path_rejected(self):
        with self.assertRaises(ValueError):
            encode_address_prefix(40, 3)

    def test_decode_recovers_what_encode_wrote(self):
        decoded = decode_address_prefix(encode_address_prefix(40, (3, 7)) + (2, 0))
        self.assertEqual(decoded["path_addresses"], (3, 7))
        self.assertEqual(decoded["target_logical_address"], 40)
        self.assertEqual(decoded["remainder_offset"], 3)

    def test_decode_of_a_pathless_unit(self):
        decoded = decode_address_prefix((82, 2, 0, 1))
        self.assertEqual(decoded["path_addresses"], ())
        self.assertEqual(decoded["remainder_offset"], 1)

    def test_decode_of_an_all_path_unit_rejected(self):
        with self.assertRaises(ValueError):
            decode_address_prefix((3, 7, 1))

    def test_decode_of_an_empty_unit_rejected(self):
        with self.assertRaises(ValueError):
            decode_address_prefix(())


class AssessTests(unittest.TestCase):
    def test_registered_case_sets_the_field(self):
        result = assess_target_logical_address_field(_case())
        self.assertEqual(result["verdict"], "address-field-set")
        self.assertEqual(result["target_logical_address"], 40)
        self.assertEqual(result["address_prefix"], (3, 7, 40))
        self.assertEqual(result["path_length"], 2)
        self.assertEqual(result["source"], REGISTRY_SOURCE)

    def test_unaddressed_node_case_reports_the_fallback(self):
        result = assess_target_logical_address_field(
            _case(destination_node="spare-unit")
        )
        self.assertEqual(result["category"], DEFAULT_LOGICAL)
        self.assertEqual(result["source"], DEFAULT_SOURCE)
        self.assertTrue(result["usable"])
        self.assertTrue(any("default" in f for f in result["findings"]))

    def test_case_without_a_path_reports_zero_path_length(self):
        result = assess_target_logical_address_field(_case(path_addresses=()))
        self.assertEqual(result["path_length"], 0)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_target_logical_address_field("obc")

    def test_case_with_an_unknown_node_rejected(self):
        with self.assertRaises(ValueError):
            assess_target_logical_address_field(_case(destination_node="ghost"))


if __name__ == "__main__":
    unittest.main()
