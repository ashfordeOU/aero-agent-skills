"""Contract tests for the clause 5.5.3 received-transfer delivery logic."""

import unittest

from e5053_transfer_packet_logic import (
    DELIVER,
    DISCARD,
    EXTENDED_PROTOCOL_MARKER,
    NOT_OURS,
    PRIMARY_HEADER_OCTETS,
    PROTOCOL_IDENTIFIER,
    packet_field_is_whole,
    read_protocol_fields,
    receive_transfer,
    strip_leading_logical_address,
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


PACKET = build_packet()


def build_transfer(protocol=PROTOCOL_IDENTIFIER, reserved=0x00, packet=None,
                   logical_address=40):
    body = [protocol, reserved] + list(PACKET if packet is None else packet)
    if logical_address is None:
        return body
    return [logical_address] + body


class StripAddressTests(unittest.TestCase):
    def test_logical_address_octet_is_removed(self):
        self.assertEqual(strip_leading_logical_address([40, 2, 0], True), [2, 0])

    def test_path_addressed_transfer_is_untouched(self):
        self.assertEqual(strip_leading_logical_address([2, 0, 9], False), [2, 0, 9])

    def test_empty_logical_transfer_rejected(self):
        with self.assertRaises(ValueError):
            strip_leading_logical_address([], True)

    def test_non_boolean_addressing_flag_rejected(self):
        with self.assertRaises(ValueError):
            strip_leading_logical_address([40, 2, 0], "yes")

    def test_bad_octet_rejected(self):
        with self.assertRaises(ValueError):
            strip_leading_logical_address([40, 300], True)


class ProtocolFieldTests(unittest.TestCase):
    def test_fields_are_split_from_the_packet(self):
        protocol, reserved, field = read_protocol_fields([2, 0, 9, 9])
        self.assertEqual(protocol, 2)
        self.assertEqual(reserved, 0)
        self.assertEqual(field, [9, 9])

    def test_body_with_only_the_two_fields_gives_an_empty_packet_field(self):
        self.assertEqual(read_protocol_fields([2, 0])[2], [])

    def test_one_octet_body_rejected(self):
        with self.assertRaises(ValueError):
            read_protocol_fields([2])

    def test_bytes_body_accepted(self):
        self.assertEqual(read_protocol_fields(bytes([2, 0, 7]))[0], 2)


class PacketFieldWholenessTests(unittest.TestCase):
    def test_whole_packet_is_accepted(self):
        self.assertTrue(packet_field_is_whole(PACKET))

    def test_truncated_packet_is_rejected(self):
        self.assertFalse(packet_field_is_whole(PACKET[:-1]))

    def test_surplus_tail_is_rejected(self):
        self.assertFalse(packet_field_is_whole(PACKET + [0x00]))

    def test_header_stub_is_rejected(self):
        self.assertFalse(packet_field_is_whole(PACKET[:PRIMARY_HEADER_OCTETS - 1]))

    def test_empty_field_is_rejected(self):
        self.assertFalse(packet_field_is_whole([]))


class ReceiveTransferTests(unittest.TestCase):
    def test_good_transfer_is_delivered(self):
        result = receive_transfer(build_transfer())
        self.assertEqual(result["disposition"], DELIVER)
        self.assertTrue(result["delivered"])
        self.assertEqual(result["ccsds_packet"], PACKET)

    def test_delivered_packet_is_byte_identical(self):
        payload = build_packet(data_octets=9, apid=0x1FF)
        result = receive_transfer(build_transfer(packet=payload))
        self.assertEqual(result["ccsds_packet"], payload)

    def test_path_addressed_transfer_has_no_address_octet(self):
        result = receive_transfer(
            build_transfer(logical_address=None), addressed_logically=False
        )
        self.assertTrue(result["delivered"])

    def test_error_terminator_discards_before_parsing(self):
        result = receive_transfer(build_transfer(), terminator="EEP")
        self.assertEqual(result["disposition"], DISCARD)
        self.assertIsNone(result["protocol_identifier"])

    def test_absent_terminator_discards(self):
        result = receive_transfer(build_transfer(), terminator=None)
        self.assertFalse(result["delivered"])

    def test_other_protocol_identifier_is_not_ours(self):
        result = receive_transfer(build_transfer(protocol=0x01))
        self.assertEqual(result["disposition"], NOT_OURS)
        self.assertEqual(result["findings"], [])

    def test_extended_protocol_marker_is_recognised(self):
        result = receive_transfer(build_transfer(protocol=EXTENDED_PROTOCOL_MARKER))
        self.assertEqual(result["disposition"], NOT_OURS)
        self.assertIn("extended", result["reason"])

    def test_truncated_packet_field_is_discarded(self):
        result = receive_transfer(build_transfer(packet=PACKET[:-2]))
        self.assertEqual(result["disposition"], DISCARD)
        self.assertTrue(any("whole space packet" in f for f in result["findings"]))

    def test_short_transfer_is_discarded(self):
        result = receive_transfer([40, 2])
        self.assertEqual(result["disposition"], DISCARD)
        self.assertIn("too short", result["reason"])

    def test_non_zero_reserved_octet_is_noted_but_delivered(self):
        result = receive_transfer(build_transfer(reserved=0x5A))
        self.assertTrue(result["delivered"])
        self.assertEqual(result["reserved_octet"], 0x5A)
        self.assertTrue(any("reserved octet" in f for f in result["findings"]))

    def test_protocol_identifier_is_reported_on_delivery(self):
        result = receive_transfer(build_transfer())
        self.assertEqual(result["protocol_identifier"], PROTOCOL_IDENTIFIER)

    def test_unknown_terminator_rejected(self):
        with self.assertRaises(ValueError):
            receive_transfer(build_transfer(), terminator="ESC")

    def test_blank_terminator_rejected(self):
        with self.assertRaises(ValueError):
            receive_transfer(build_transfer(), terminator="  ")

    def test_bad_octet_in_the_transfer_rejected(self):
        with self.assertRaises(ValueError):
            receive_transfer([40, 2, 0, 400])


if __name__ == "__main__":
    unittest.main()
