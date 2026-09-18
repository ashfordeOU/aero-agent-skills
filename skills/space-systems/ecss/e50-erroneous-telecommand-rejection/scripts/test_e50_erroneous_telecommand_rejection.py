#!/usr/bin/env python3
"""Gate 3 contract test for e50-erroneous-telecommand-rejection.

stdlib unittest, offline, deterministic. Run:
    python3 test_e50_erroneous_telecommand_rejection.py
"""

import unittest

from e50_erroneous_telecommand_rejection_logic import (
    ACCEPTED,
    CHECK_ORDER,
    DESTINATION,
    INTEGRITY,
    LENGTH,
    PARAMETER,
    REJECTED,
    SERVICE,
    append_check_symbol,
    assess_telecommand,
    check_destination,
    check_integrity,
    check_length,
    check_parameters,
    check_service,
    crc16_ccitt,
    first_failing_check,
    split_check_symbol,
    validate_octets,
)

BODY = (0x18, 0x03, 0xC0, 0x00, 0x00, 0x07, 0x11, 0x04, 0x01, 0x00)
KNOWN_APIDS = (3, 10, 96)
SUPPORTED = {17: (1,), 11: (4,), 8: (1, 2)}
RANGES = {"offset_s": (0, 3600), "identifier": (1, 64)}
GOOD_PARAMS = {"offset_s": 120, "identifier": 7}


def packet(body=BODY):
    return append_check_symbol(body)


def call(**overrides):
    kwargs = {
        "packet": packet(),
        "declared_body_octets": len(BODY),
        "application_id": 3,
        "known_application_ids": KNOWN_APIDS,
        "service": 11,
        "subservice": 4,
        "supported_services": SUPPORTED,
        "parameters": dict(GOOD_PARAMS),
        "ranges": RANGES,
    }
    kwargs.update(overrides)
    return kwargs


class TestOctets(unittest.TestCase):
    def test_bytes_are_accepted_as_octets(self):
        self.assertEqual(validate_octets(b"\x01\x02"), (1, 2))

    def test_an_out_of_range_octet_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_octets([1, 300])

    def test_a_boolean_octet_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_octets([True, 2])

    def test_text_is_not_octets(self):
        with self.assertRaises(ValueError):
            validate_octets("0102")


class TestCheckSymbol(unittest.TestCase):
    def test_the_check_symbol_is_stable_for_a_given_body(self):
        self.assertEqual(crc16_ccitt(BODY), crc16_ccitt(list(BODY)))

    def test_a_single_flipped_bit_changes_the_symbol(self):
        flipped = list(BODY)
        flipped[4] ^= 0x01
        self.assertNotEqual(crc16_ccitt(BODY), crc16_ccitt(flipped))

    def test_the_symbol_is_sixteen_bits_wide(self):
        self.assertLessEqual(crc16_ccitt(BODY), 0xFFFF)

    def test_appending_then_splitting_returns_the_body(self):
        body, symbol = split_check_symbol(packet())
        self.assertEqual(body, BODY)
        self.assertEqual(symbol, crc16_ccitt(BODY))

    def test_a_packet_with_no_body_is_rejected(self):
        with self.assertRaises(ValueError):
            split_check_symbol((0x12, 0x34))


class TestIndividualChecks(unittest.TestCase):
    def test_an_intact_packet_passes_integrity(self):
        self.assertTrue(check_integrity(packet()))

    def test_a_corrupted_packet_fails_integrity(self):
        broken = list(packet())
        broken[2] ^= 0xFF
        self.assertFalse(check_integrity(broken))

    def test_a_matching_declared_length_passes(self):
        self.assertTrue(check_length(packet(), len(BODY)))

    def test_a_short_declared_length_fails(self):
        self.assertFalse(check_length(packet(), len(BODY) - 1))

    def test_a_negative_declared_length_is_rejected(self):
        with self.assertRaises(ValueError):
            check_length(packet(), -1)

    def test_a_known_application_identifier_passes(self):
        self.assertTrue(check_destination(3, KNOWN_APIDS))

    def test_an_unknown_application_identifier_fails(self):
        self.assertFalse(check_destination(77, KNOWN_APIDS))

    def test_an_application_identifier_out_of_range_is_rejected(self):
        with self.assertRaises(ValueError):
            check_destination(5000, KNOWN_APIDS)

    def test_a_supported_service_pair_passes(self):
        self.assertTrue(check_service(11, 4, SUPPORTED))

    def test_a_supported_service_with_an_unsupported_subservice_fails(self):
        self.assertFalse(check_service(11, 9, SUPPORTED))

    def test_an_unsupported_service_fails(self):
        self.assertFalse(check_service(200, 1, SUPPORTED))

    def test_parameters_inside_their_ranges_have_no_offender(self):
        self.assertEqual(check_parameters(GOOD_PARAMS, RANGES), ())

    def test_a_parameter_past_its_upper_bound_is_an_offender(self):
        self.assertEqual(
            check_parameters({"offset_s": 4000}, RANGES), ("offset_s",)
        )

    def test_a_parameter_exactly_on_its_bound_is_allowed(self):
        self.assertEqual(check_parameters({"offset_s": 3600}, RANGES), ())

    def test_a_parameter_with_no_declared_range_is_an_offender(self):
        self.assertEqual(check_parameters({"unknown": 1}, RANGES), ("unknown",))

    def test_an_inverted_range_is_rejected(self):
        with self.assertRaises(ValueError):
            check_parameters({"offset_s": 1}, {"offset_s": (10, 0)})


class TestChain(unittest.TestCase):
    def test_a_clean_command_fails_no_check(self):
        self.assertIsNone(first_failing_check(**call()))

    def test_integrity_is_reported_before_any_later_defect(self):
        broken = list(packet())
        broken[1] ^= 0xFF
        reason = first_failing_check(
            **call(packet=broken, application_id=999 % 2048, service=200)
        )
        self.assertEqual(reason, INTEGRITY)

    def test_length_is_reported_before_destination(self):
        reason = first_failing_check(
            **call(declared_body_octets=2, application_id=77)
        )
        self.assertEqual(reason, LENGTH)

    def test_destination_is_reported_before_service(self):
        reason = first_failing_check(**call(application_id=77, service=200))
        self.assertEqual(reason, DESTINATION)

    def test_service_is_reported_before_parameters(self):
        reason = first_failing_check(
            **call(subservice=9, parameters={"offset_s": 99999})
        )
        self.assertEqual(reason, SERVICE)

    def test_a_bad_parameter_is_the_last_reason(self):
        reason = first_failing_check(**call(parameters={"offset_s": 99999}))
        self.assertEqual(reason, PARAMETER)


class TestAssessment(unittest.TestCase):
    def test_a_valid_command_is_accepted_with_its_plan(self):
        report = assess_telecommand(**call(), execution_steps=("arm", "fire"))
        self.assertEqual(report["verdict"], ACCEPTED)
        self.assertEqual(report["execution_plan"], ("arm", "fire"))
        self.assertFalse(report["rejection_report_owed"])

    def test_a_rejected_command_executes_nothing_at_all(self):
        report = assess_telecommand(
            **call(parameters={"offset_s": 99999}), execution_steps=("arm", "fire")
        )
        self.assertEqual(report["verdict"], REJECTED)
        self.assertEqual(report["execution_plan"], ())
        self.assertFalse(report["partially_executed"])

    def test_a_rejection_owes_the_ground_a_report(self):
        report = assess_telecommand(**call(application_id=77))
        self.assertTrue(report["rejection_report_owed"])
        self.assertEqual(report["rejection_reason"], DESTINATION)

    def test_the_checks_passed_before_rejection_are_listed(self):
        report = assess_telecommand(**call(subservice=9))
        self.assertEqual(report["checks_before_rejection"], (INTEGRITY, LENGTH, DESTINATION))

    def test_an_accepted_command_lists_the_whole_chain(self):
        report = assess_telecommand(**call())
        self.assertEqual(report["checks_before_rejection"], CHECK_ORDER)

    def test_the_offending_parameters_are_named(self):
        report = assess_telecommand(
            **call(parameters={"offset_s": 99999, "identifier": 7})
        )
        self.assertEqual(report["out_of_range_parameters"], ("offset_s",))

    def test_a_non_sequence_execution_plan_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_telecommand(**call(), execution_steps="arm")


if __name__ == "__main__":
    unittest.main()
