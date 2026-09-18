#!/usr/bin/env python3
"""Gate 3 contract test for e5053-target-spacewire-address.

stdlib unittest, offline, deterministic. Run:
    python3 test_e5053_target_spacewire_address.py
"""

import unittest

from e5053_target_spacewire_address_logic import (
    CONFIGURATION_PORT,
    FORM_EMPTY,
    FORM_LOGICAL,
    FORM_PATH,
    FORM_PATH_THEN_LOGICAL,
    LOGICAL,
    PATH,
    RESERVED,
    RESERVED_OCTET,
    address_form,
    assess_target_spacewire_address,
    categorize_address_octet,
    deliver_hop,
    is_empty_address,
    leading_path_octets,
    route_trace,
    validate_target_spacewire_address,
)


class TestOctetCategories(unittest.TestCase):
    def test_lowest_encoding_is_the_configuration_port(self):
        self.assertEqual(categorize_address_octet(0), CONFIGURATION_PORT)

    def test_low_encodings_select_a_port(self):
        self.assertEqual(categorize_address_octet(1), PATH)
        self.assertEqual(categorize_address_octet(31), PATH)

    def test_middle_encodings_are_logical(self):
        self.assertEqual(categorize_address_octet(32), LOGICAL)
        self.assertEqual(categorize_address_octet(254), LOGICAL)

    def test_highest_encoding_is_reserved(self):
        self.assertEqual(categorize_address_octet(RESERVED_OCTET), RESERVED)

    def test_out_of_range_octet_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_address_octet(256)

    def test_boolean_octet_is_not_an_integer(self):
        with self.assertRaises(ValueError):
            categorize_address_octet(False)


class TestAddressValidation(unittest.TestCase):
    def test_empty_address_is_legal(self):
        self.assertEqual(validate_target_spacewire_address([]), ())
        self.assertTrue(is_empty_address([]))

    def test_bytes_are_accepted(self):
        self.assertEqual(validate_target_spacewire_address(bytes([2, 3, 40])), (2, 3, 40))

    def test_non_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_target_spacewire_address(7)

    def test_out_of_range_member_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_target_spacewire_address([2, 300])

    def test_float_member_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_target_spacewire_address([2.0])


class TestAddressForm(unittest.TestCase):
    def test_empty_address_has_the_empty_form(self):
        self.assertEqual(address_form([]), FORM_EMPTY)

    def test_only_port_selectors_is_a_path_address(self):
        self.assertEqual(address_form([2, 5, 1]), FORM_PATH)

    def test_a_single_logical_octet_is_a_logical_address(self):
        self.assertEqual(address_form([40]), FORM_LOGICAL)

    def test_selectors_then_a_logical_octet_is_the_mixed_form(self):
        self.assertEqual(address_form([2, 5, 40]), FORM_PATH_THEN_LOGICAL)

    def test_octets_after_the_logical_octet_are_malformed(self):
        with self.assertRaises(ValueError):
            address_form([2, 40, 41])

    def test_a_reserved_octet_in_the_tail_is_malformed(self):
        with self.assertRaises(ValueError):
            address_form([2, RESERVED_OCTET])

    def test_leading_selector_count_stops_at_the_logical_octet(self):
        self.assertEqual(leading_path_octets([2, 5, 40]), 2)
        self.assertEqual(leading_path_octets([40, 2]), 0)


class TestRouting(unittest.TestCase):
    def test_a_router_consumes_the_leading_selector(self):
        self.assertEqual(deliver_hop([2, 5, 40]), (5, 40))

    def test_a_router_leaves_a_logical_octet_in_place(self):
        with self.assertRaises(ValueError):
            deliver_hop([40, 2])

    def test_an_empty_address_has_nothing_to_consume(self):
        with self.assertRaises(ValueError):
            deliver_hop([])

    def test_trace_shows_the_address_shrinking(self):
        trace = route_trace([2, 5, 40], 2)
        self.assertEqual(trace[0], (2, 5, 40))
        self.assertEqual(trace[-1], (40,))

    def test_zero_routers_leaves_the_address_untouched(self):
        self.assertEqual(route_trace([2, 5, 40], 0), [(2, 5, 40)])

    def test_negative_router_count_is_rejected(self):
        with self.assertRaises(ValueError):
            route_trace([2, 5, 40], -1)

    def test_more_routers_than_selectors_is_rejected(self):
        with self.assertRaises(ValueError):
            route_trace([2, 40], 2)


class TestAssessment(unittest.TestCase):
    def test_direct_attachment_with_no_prefix_is_usable(self):
        report = assess_target_spacewire_address([], directly_attached=True)
        self.assertEqual(report["verdict"], "address-usable")
        self.assertTrue(report["empty"])

    def test_direct_attachment_with_a_prefix_is_a_finding(self):
        report = assess_target_spacewire_address([2], directly_attached=True)
        self.assertEqual(report["verdict"], "address-rejected")
        self.assertTrue(any("directly attached" in f for f in report["findings"]))

    def test_routed_target_with_no_prefix_is_a_finding(self):
        report = assess_target_spacewire_address([], directly_attached=False)
        self.assertEqual(report["verdict"], "address-rejected")

    def test_router_count_mismatch_is_a_finding(self):
        report = assess_target_spacewire_address([2, 5, 40], router_count=3)
        self.assertTrue(any("port selector" in f for f in report["findings"]))

    def test_router_count_match_is_clean(self):
        report = assess_target_spacewire_address([2, 5, 40], router_count=2)
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["form"], FORM_PATH_THEN_LOGICAL)

    def test_reserved_octet_is_reported_once(self):
        report = assess_target_spacewire_address([2, RESERVED_OCTET])
        self.assertEqual(
            len([f for f in report["findings"] if "reserved encoding" in f]), 1
        )

    def test_configuration_port_selector_is_a_limitation(self):
        report = assess_target_spacewire_address([0, 40], router_count=1)
        self.assertTrue(
            any("configuration port" in n for n in report["limitations"])
        )

    def test_categories_are_reported_per_octet(self):
        report = assess_target_spacewire_address([2, 40], router_count=1)
        self.assertEqual(report["octet_categories"], (PATH, LOGICAL))

    def test_malformed_tail_is_a_finding_not_an_exception(self):
        report = assess_target_spacewire_address([2, 40, 41], router_count=1)
        self.assertIsNone(report["form"])
        self.assertEqual(report["verdict"], "address-rejected")


if __name__ == "__main__":
    unittest.main()
