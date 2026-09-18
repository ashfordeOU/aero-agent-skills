"""Contract tests for the clause 5.5.2 send request logic."""

import unittest

from e5053_send_request_logic import (
    DEFAULT_MAX_TRANSFER_OCTETS,
    LOGICAL_ADDRESS_MAX,
    LOGICAL_ADDRESS_MIN,
    PATH_PORT_MAX,
    PRIMARY_HEADER_OCTETS,
    PROTOCOL_IDENTIFIER,
    RESERVED_OCTET,
    assess_send_request,
    categorize_destination,
    encode_destination,
    encode_send_request,
    validate_ccsds_packet,
)


def build_packet(data_octets=4, apid=0x2A):
    length_field = data_octets - 1
    return [
        (apid >> 8) & 0x07,
        apid & 0xFF,
        0xC0,
        0x01,
        (length_field >> 8) & 0xFF,
        length_field & 0xFF,
    ] + [0x5A] * data_octets


GOOD_PACKET = build_packet()


class DestinationTests(unittest.TestCase):
    def test_bare_logical_address_is_categorized(self):
        self.assertEqual(categorize_destination(40), ("logical", [40]))

    def test_lowest_logical_address_accepted(self):
        self.assertEqual(categorize_destination(LOGICAL_ADDRESS_MIN)[0], "logical")

    def test_highest_logical_address_accepted(self):
        self.assertEqual(categorize_destination(LOGICAL_ADDRESS_MAX)[0], "logical")

    def test_reserved_low_address_rejected(self):
        with self.assertRaises(ValueError):
            categorize_destination(LOGICAL_ADDRESS_MIN - 1)

    def test_reserved_top_address_rejected(self):
        with self.assertRaises(ValueError):
            categorize_destination(LOGICAL_ADDRESS_MAX + 1)

    def test_path_of_ports_is_categorized(self):
        self.assertEqual(categorize_destination([2, 5, 1]), ("path", [2, 5, 1]))

    def test_path_may_end_in_a_logical_address(self):
        kind, octets = categorize_destination([3, 7, 96])
        self.assertEqual(kind, "path")
        self.assertEqual(octets[-1], 96)

    def test_single_port_is_a_path(self):
        self.assertEqual(categorize_destination([4]), ("path", [4]))

    def test_zero_port_in_a_path_rejected(self):
        with self.assertRaises(ValueError):
            categorize_destination([2, 0, 5])

    def test_out_of_range_port_in_a_path_rejected(self):
        with self.assertRaises(ValueError):
            categorize_destination([2, PATH_PORT_MAX + 1, 5])

    def test_reserved_tail_value_rejected(self):
        with self.assertRaises(ValueError):
            categorize_destination([2, 5, 255])

    def test_empty_destination_rejected(self):
        with self.assertRaises(ValueError):
            categorize_destination([])

    def test_boolean_destination_rejected(self):
        with self.assertRaises(ValueError):
            categorize_destination(True)

    def test_text_destination_rejected(self):
        with self.assertRaises(ValueError):
            categorize_destination("40")

    def test_encode_destination_returns_the_octets(self):
        self.assertEqual(encode_destination([2, 5, 96]), [2, 5, 96])


class PacketValidationTests(unittest.TestCase):
    def test_well_formed_packet_returns_its_declared_length(self):
        octets, declared = validate_ccsds_packet(GOOD_PACKET)
        self.assertEqual(declared, len(octets))
        self.assertEqual(declared, PRIMARY_HEADER_OCTETS + 4)

    def test_bytes_input_accepted(self):
        _octets, declared = validate_ccsds_packet(bytes(GOOD_PACKET))
        self.assertEqual(declared, len(GOOD_PACKET))

    def test_truncated_packet_rejected(self):
        with self.assertRaises(ValueError):
            validate_ccsds_packet(GOOD_PACKET[:-1])

    def test_packet_with_a_surplus_tail_rejected(self):
        with self.assertRaises(ValueError):
            validate_ccsds_packet(GOOD_PACKET + [0x00])

    def test_header_only_stub_rejected(self):
        with self.assertRaises(ValueError):
            validate_ccsds_packet([0x08, 0x2A, 0xC0])

    def test_out_of_range_octet_rejected(self):
        bad = list(GOOD_PACKET)
        bad[-1] = 300
        with self.assertRaises(ValueError):
            validate_ccsds_packet(bad)


class EncodeTests(unittest.TestCase):
    def test_protocol_and_reserved_octets_follow_the_address(self):
        encoded = encode_send_request(40, GOOD_PACKET)
        self.assertEqual(encoded[0], 40)
        self.assertEqual(encoded[1], PROTOCOL_IDENTIFIER)
        self.assertEqual(encoded[2], RESERVED_OCTET)

    def test_packet_follows_the_reserved_octet_unchanged(self):
        encoded = encode_send_request(40, GOOD_PACKET)
        self.assertEqual(encoded[3:], GOOD_PACKET)

    def test_path_address_lengthens_the_transfer(self):
        short = encode_send_request(40, GOOD_PACKET)
        longer = encode_send_request([2, 5, 96], GOOD_PACKET)
        self.assertEqual(len(longer) - len(short), 2)


class AssessSendRequestTests(unittest.TestCase):
    def _request(self, **overrides):
        request = {"destination": 40, "ccsds_packet": list(GOOD_PACKET)}
        request.update(overrides)
        return request

    def test_good_request_is_accepted(self):
        result = assess_send_request(self._request())
        self.assertTrue(result["accepted"])
        self.assertEqual(result["findings"], [])

    def test_accepted_request_reports_its_encoded_length(self):
        result = assess_send_request(self._request())
        self.assertEqual(result["encoded_octets"], len(GOOD_PACKET) + 3)
        self.assertEqual(result["destination_kind"], "logical")

    def test_default_limit_is_applied_when_none_is_given(self):
        result = assess_send_request(self._request())
        self.assertEqual(result["max_transfer_octets"], DEFAULT_MAX_TRANSFER_OCTETS)

    def test_bad_destination_is_a_finding_not_an_exception(self):
        result = assess_send_request(self._request(destination=7))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("destination" in f for f in result["findings"]))

    def test_bad_packet_is_a_finding_not_an_exception(self):
        result = assess_send_request(self._request(ccsds_packet=GOOD_PACKET[:-1]))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("CCSDS packet" in f for f in result["findings"]))

    def test_both_defects_are_reported_together(self):
        result = assess_send_request(
            self._request(destination=7, ccsds_packet=GOOD_PACKET[:-1])
        )
        self.assertEqual(len(result["findings"]), 2)

    def test_over_long_transfer_is_refused(self):
        result = assess_send_request(self._request(max_transfer_octets=8))
        self.assertFalse(result["accepted"])
        self.assertTrue(any("transmit limit" in f for f in result["findings"]))

    def test_transfer_exactly_at_the_limit_is_accepted(self):
        exact = len(GOOD_PACKET) + 3
        result = assess_send_request(self._request(max_transfer_octets=exact))
        self.assertTrue(result["accepted"])

    def test_zero_limit_rejected(self):
        with self.assertRaises(ValueError):
            assess_send_request(self._request(max_transfer_octets=0))

    def test_non_integer_limit_rejected(self):
        with self.assertRaises(ValueError):
            assess_send_request(self._request(max_transfer_octets=12.5))

    def test_missing_key_rejected(self):
        request = self._request()
        del request["destination"]
        with self.assertRaises(ValueError):
            assess_send_request(request)

    def test_non_mapping_request_rejected(self):
        with self.assertRaises(ValueError):
            assess_send_request([40, GOOD_PACKET])


if __name__ == "__main__":
    unittest.main()
