#!/usr/bin/env python3
"""Gate 3 contract test for e5053-target-logical-address.

stdlib unittest, offline, deterministic. Run:
    python3 test_e5053_target_logical_address.py
"""

import unittest

from e5053_target_logical_address_logic import (
    ASSIGNED,
    DEFAULT,
    DEFAULT_LOGICAL_ADDRESS,
    DELIVER,
    MISROUTED,
    PATH_RESERVED,
    REJECT,
    RESERVED,
    RESERVED_LOGICAL_ADDRESS,
    assess_target_logical_address,
    categorize_target_logical_address,
    cross_check_with_route_prefix,
    is_assignable,
    is_default_logical_address,
    receiver_action,
    resolve_target_logical_address,
    validate_logical_address,
    validate_node_addresses,
)

NODE = 40
OTHER = 41


class TestFieldValidation(unittest.TestCase):
    def test_an_assignable_value_is_accepted(self):
        self.assertEqual(validate_logical_address(NODE), NODE)

    def test_a_value_over_one_octet_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_logical_address(256)

    def test_a_negative_value_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_logical_address(-1)

    def test_a_boolean_is_not_an_octet(self):
        with self.assertRaises(ValueError):
            validate_logical_address(True)

    def test_a_float_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_logical_address(40.0)


class TestCategories(unittest.TestCase):
    def test_a_low_encoding_belongs_to_the_routing_prefix(self):
        self.assertEqual(categorize_target_logical_address(7), PATH_RESERVED)

    def test_an_ordinary_encoding_is_assignable(self):
        self.assertEqual(categorize_target_logical_address(NODE), ASSIGNED)
        self.assertTrue(is_assignable(NODE))

    def test_the_default_encoding_is_its_own_group(self):
        self.assertEqual(
            categorize_target_logical_address(DEFAULT_LOGICAL_ADDRESS), DEFAULT
        )
        self.assertTrue(is_default_logical_address(DEFAULT_LOGICAL_ADDRESS))
        self.assertFalse(is_assignable(DEFAULT_LOGICAL_ADDRESS))

    def test_the_highest_encoding_is_reserved(self):
        self.assertEqual(
            categorize_target_logical_address(RESERVED_LOGICAL_ADDRESS), RESERVED
        )

    def test_the_boundary_below_the_default_is_still_assignable(self):
        self.assertTrue(is_assignable(DEFAULT_LOGICAL_ADDRESS - 1))


class TestNodeAddressSet(unittest.TestCase):
    def test_a_set_of_assignable_addresses_is_accepted(self):
        self.assertEqual(validate_node_addresses([NODE, OTHER]), frozenset([NODE, OTHER]))

    def test_the_default_encoding_may_not_be_assigned_to_a_node(self):
        with self.assertRaises(ValueError):
            validate_node_addresses([DEFAULT_LOGICAL_ADDRESS])

    def test_a_prefix_selector_may_not_be_assigned_to_a_node(self):
        with self.assertRaises(ValueError):
            validate_node_addresses([7])

    def test_a_non_collection_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_node_addresses(NODE)


class TestResolution(unittest.TestCase):
    def test_logical_addressing_writes_the_target_address(self):
        self.assertEqual(resolve_target_logical_address(NODE, True), NODE)

    def test_no_logical_addressing_writes_the_default(self):
        self.assertEqual(
            resolve_target_logical_address(NODE, False), DEFAULT_LOGICAL_ADDRESS
        )

    def test_no_logical_addressing_ignores_an_unusable_node_value(self):
        self.assertEqual(
            resolve_target_logical_address(0, False), DEFAULT_LOGICAL_ADDRESS
        )

    def test_an_unassignable_target_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_target_logical_address(7, True)

    def test_the_policy_flag_must_be_a_boolean(self):
        with self.assertRaises(ValueError):
            resolve_target_logical_address(NODE, "yes")


class TestReceiverAction(unittest.TestCase):
    def test_an_address_the_node_answers_to_is_delivered(self):
        self.assertEqual(receiver_action(NODE, [NODE]), DELIVER)

    def test_an_address_the_node_does_not_answer_to_is_misrouted(self):
        self.assertEqual(receiver_action(OTHER, [NODE]), MISROUTED)

    def test_the_default_encoding_is_delivered_when_accepted(self):
        self.assertEqual(receiver_action(DEFAULT_LOGICAL_ADDRESS, [NODE]), DELIVER)

    def test_the_default_encoding_is_rejected_when_not_accepted(self):
        self.assertEqual(
            receiver_action(DEFAULT_LOGICAL_ADDRESS, [NODE], accept_default=False),
            REJECT,
        )

    def test_a_prefix_selector_value_is_rejected(self):
        self.assertEqual(receiver_action(7, [NODE]), REJECT)

    def test_the_reserved_encoding_is_rejected(self):
        self.assertEqual(receiver_action(RESERVED_LOGICAL_ADDRESS, [NODE]), REJECT)


class TestPrefixCrossCheck(unittest.TestCase):
    def test_no_prefix_octet_means_no_comparison(self):
        self.assertIsNone(cross_check_with_route_prefix(NODE, None))

    def test_matching_prefix_octet_agrees(self):
        self.assertTrue(cross_check_with_route_prefix(NODE, NODE))

    def test_differing_prefix_octet_disagrees(self):
        self.assertFalse(cross_check_with_route_prefix(NODE, OTHER))


class TestAssessment(unittest.TestCase):
    def test_a_matching_field_is_delivered(self):
        report = assess_target_logical_address(NODE, [NODE])
        self.assertEqual(report["verdict"], "deliver")
        self.assertEqual(report["findings"], [])

    def test_a_misrouted_field_is_held(self):
        report = assess_target_logical_address(OTHER, [NODE])
        self.assertEqual(report["receiver_action"], MISROUTED)
        self.assertTrue(any("does not answer to" in f for f in report["findings"]))

    def test_the_default_under_logical_addressing_is_a_finding(self):
        report = assess_target_logical_address(
            DEFAULT_LOGICAL_ADDRESS, [NODE], logical_addressing_in_use=True
        )
        self.assertEqual(report["verdict"], "hold")

    def test_the_default_without_logical_addressing_is_a_limitation(self):
        report = assess_target_logical_address(
            DEFAULT_LOGICAL_ADDRESS, [NODE], logical_addressing_in_use=False
        )
        self.assertEqual(report["verdict"], "deliver")
        self.assertTrue(any("names no particular node" in n for n in report["limitations"]))

    def test_a_prefix_selector_value_is_a_finding(self):
        report = assess_target_logical_address(7, [NODE])
        self.assertEqual(report["category"], PATH_RESERVED)
        self.assertEqual(report["verdict"], "hold")

    def test_a_prefix_disagreement_is_a_finding(self):
        report = assess_target_logical_address(
            NODE, [NODE], prefix_logical_octet=OTHER
        )
        self.assertFalse(report["prefix_agreement"])
        self.assertTrue(any("routing prefix ended on" in f for f in report["findings"]))

    def test_a_prefix_agreement_leaves_the_transfer_deliverable(self):
        report = assess_target_logical_address(
            NODE, [NODE], prefix_logical_octet=NODE
        )
        self.assertTrue(report["prefix_agreement"])
        self.assertEqual(report["verdict"], "deliver")

    def test_assessment_propagates_a_field_error(self):
        with self.assertRaises(ValueError):
            assess_target_logical_address(999, [NODE])


if __name__ == "__main__":
    unittest.main()
