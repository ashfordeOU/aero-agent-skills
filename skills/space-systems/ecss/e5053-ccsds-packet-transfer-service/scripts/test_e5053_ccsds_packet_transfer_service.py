#!/usr/bin/env python3
"""Gate 3 contract test for e5053-ccsds-packet-transfer-service.

stdlib unittest, offline, deterministic. Run:
    python3 test_e5053_ccsds_packet_transfer_service.py
"""

import unittest

from e5053_ccsds_packet_transfer_service_logic import (
    ALTERED,
    DISCARDED,
    END_OF_PACKET,
    ERROR_END_OF_PACKET,
    EXTENDED,
    INDICATED,
    MIN_PACKET_OCTETS,
    NO_TERMINATOR,
    TRUNCATED,
    UNMODIFIED,
    assess_ccsds_packet_transfer_service,
    boundaries_preserved,
    build_request,
    categorize_packet_delivery,
    service_indication,
    validate_packet,
    validate_terminator,
)

PACKET = tuple(range(20))


def request(packet=PACKET, user_value=9, logical=40, prefix=(2, 5)):
    return build_request(packet, prefix, logical, user_value)


class TestPacketValidation(unittest.TestCase):
    def test_a_long_enough_packet_is_accepted(self):
        self.assertEqual(len(validate_packet(PACKET)), 20)

    def test_bytes_are_accepted(self):
        self.assertEqual(validate_packet(bytes(PACKET)), PACKET)

    def test_a_packet_shorter_than_a_header_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_packet(tuple(range(MIN_PACKET_OCTETS - 1)))

    def test_an_out_of_range_octet_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_packet(list(range(19)) + [300])

    def test_a_non_sequence_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_packet(20)


class TestTerminator(unittest.TestCase):
    def test_the_normal_marker_is_valid(self):
        self.assertEqual(validate_terminator(END_OF_PACKET), END_OF_PACKET)

    def test_the_error_marker_is_valid(self):
        self.assertEqual(validate_terminator(ERROR_END_OF_PACKET), ERROR_END_OF_PACKET)

    def test_an_unknown_marker_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_terminator("finished")


class TestRequest(unittest.TestCase):
    def test_a_request_keeps_every_parameter(self):
        built = request()
        self.assertEqual(built["packet_octets"], 20)
        self.assertEqual(built["target_spacewire_address"], (2, 5))
        self.assertEqual(built["target_logical_address"], 40)
        self.assertEqual(built["user_application_value"], 9)

    def test_an_empty_prefix_is_legal(self):
        self.assertEqual(request(prefix=())["target_spacewire_address"], ())

    def test_a_bad_prefix_octet_is_rejected(self):
        with self.assertRaises(ValueError):
            request(prefix=(2, 999))

    def test_a_non_sequence_prefix_is_rejected(self):
        with self.assertRaises(ValueError):
            request(prefix=2)

    def test_an_out_of_range_user_value_is_rejected(self):
        with self.assertRaises(ValueError):
            request(user_value=256)

    def test_an_out_of_range_logical_address_is_rejected(self):
        with self.assertRaises(ValueError):
            request(logical=-1)


class TestDeliveryCategories(unittest.TestCase):
    def test_an_identical_packet_is_unmodified(self):
        self.assertEqual(categorize_packet_delivery(PACKET, PACKET), UNMODIFIED)

    def test_a_short_prefix_of_the_packet_is_truncated(self):
        self.assertEqual(categorize_packet_delivery(PACKET, PACKET[:12]), TRUNCATED)

    def test_the_packet_with_trailing_data_is_extended(self):
        self.assertEqual(
            categorize_packet_delivery(PACKET, PACKET + (7, 7)), EXTENDED
        )

    def test_a_changed_octet_is_altered_not_truncated(self):
        changed = list(PACKET)
        changed[3] = 200
        self.assertEqual(categorize_packet_delivery(PACKET, changed), ALTERED)

    def test_a_shorter_but_different_packet_is_altered(self):
        changed = list(PACKET[:12])
        changed[0] = 99
        self.assertEqual(categorize_packet_delivery(PACKET, changed), ALTERED)


class TestIndication(unittest.TestCase):
    def test_a_normal_end_raises_an_indication(self):
        indication = service_indication(request(), PACKET, END_OF_PACKET)
        self.assertEqual(indication["packet_octets"], 20)
        self.assertEqual(indication["user_application_value"], 9)

    def test_an_error_end_raises_no_indication(self):
        self.assertIsNone(service_indication(request(), PACKET, ERROR_END_OF_PACKET))

    def test_no_end_marker_raises_no_indication(self):
        self.assertIsNone(service_indication(request(), PACKET, NO_TERMINATOR))

    def test_a_delivered_user_value_overrides_the_requested_one(self):
        indication = service_indication(request(), PACKET, END_OF_PACKET, 11)
        self.assertEqual(indication["user_application_value"], 11)

    def test_an_out_of_range_delivered_user_value_is_rejected(self):
        with self.assertRaises(ValueError):
            service_indication(request(), PACKET, END_OF_PACKET, 400)

    def test_a_non_mapping_request_is_rejected(self):
        with self.assertRaises(ValueError):
            service_indication(PACKET, PACKET, END_OF_PACKET)


class TestBoundaries(unittest.TestCase):
    def test_matching_boundaries_are_preserved(self):
        self.assertTrue(boundaries_preserved([20, 30], [20, 30]))

    def test_a_merged_pair_loses_the_boundary(self):
        self.assertFalse(boundaries_preserved([20, 30], [50]))

    def test_a_split_packet_loses_the_boundary(self):
        self.assertFalse(boundaries_preserved([50], [20, 30]))

    def test_an_empty_request_run_is_rejected(self):
        with self.assertRaises(ValueError):
            boundaries_preserved([], [])

    def test_an_impossibly_short_delivery_is_rejected(self):
        with self.assertRaises(ValueError):
            boundaries_preserved([20], [3])


class TestAssessment(unittest.TestCase):
    def test_a_clean_transfer_meets_the_service(self):
        report = assess_ccsds_packet_transfer_service(request(), PACKET, END_OF_PACKET)
        self.assertEqual(report["outcome"], INDICATED)
        self.assertEqual(report["verdict"], "service-met")
        self.assertEqual(report["packet_category"], UNMODIFIED)

    def test_an_error_marker_discards_without_a_finding(self):
        report = assess_ccsds_packet_transfer_service(
            request(), PACKET, ERROR_END_OF_PACKET
        )
        self.assertEqual(report["outcome"], DISCARDED)
        self.assertEqual(report["findings"], [])
        self.assertTrue(any("error marker" in n for n in report["limitations"]))

    def test_a_missing_end_marker_is_a_finding(self):
        report = assess_ccsds_packet_transfer_service(
            request(), PACKET, NO_TERMINATOR
        )
        self.assertEqual(report["verdict"], "service-not-met")
        self.assertTrue(any("no end marker" in f for f in report["findings"]))

    def test_a_normal_end_with_nothing_delivered_is_a_finding(self):
        report = assess_ccsds_packet_transfer_service(request(), None, END_OF_PACKET)
        self.assertEqual(report["outcome"], DISCARDED)
        self.assertTrue(any("no packet was delivered" in f for f in report["findings"]))

    def test_a_truncated_delivery_does_not_meet_the_service(self):
        report = assess_ccsds_packet_transfer_service(
            request(), PACKET[:12], END_OF_PACKET
        )
        self.assertEqual(report["packet_category"], TRUNCATED)
        self.assertEqual(report["verdict"], "service-not-met")

    def test_an_extended_delivery_names_the_extra_octets(self):
        report = assess_ccsds_packet_transfer_service(
            request(), PACKET + (1, 2, 3), END_OF_PACKET
        )
        self.assertTrue(any("beyond the 20 given" in f for f in report["findings"]))

    def test_a_changed_user_value_is_a_separate_finding(self):
        report = assess_ccsds_packet_transfer_service(
            request(), PACKET, END_OF_PACKET, delivered_user_value=11
        )
        self.assertEqual(report["packet_category"], UNMODIFIED)
        self.assertEqual(len(report["findings"]), 1)

    def test_a_changed_logical_address_is_a_separate_finding(self):
        report = assess_ccsds_packet_transfer_service(
            request(), PACKET, END_OF_PACKET, delivered_logical_address=41
        )
        self.assertTrue(any("arrived" in f for f in report["findings"]))

    def test_an_unknown_terminator_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_ccsds_packet_transfer_service(request(), PACKET, "done")


if __name__ == "__main__":
    unittest.main()
