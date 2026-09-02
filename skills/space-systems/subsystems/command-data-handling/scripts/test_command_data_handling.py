#!/usr/bin/env python3
"""Gate 3 contract test: spacecraft command and data handling logic.

Exercises scripts/command_data_handling_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - CRC-16-CCITT
error detection, CCSDS-style telemetry packet assembly and parsing,
command packet validation, downlink budgeting, onboard storage sizing,
frame counting, and redundancy availability.

Known values: CRC-16-CCITT of b"123456789" is the published check value
0x29B1, and the CRC of the empty input is the init value 0xFFFF. The
telemetry packet with apid 7, sequence count 0, unsegmented flags, and
data b"\\xAA\\xBB" is exactly
00 07 C0 00 00 01 AA BB 45 7F (header, data, CRC-16). The command with
opcode 0x12, apid 7, payload b"\\x01\\x02\\x03" is exactly
12 00 07 00 03 01 02 03 B1 80. Downlink: 1,000,000 bits at
1,000,000 bps takes 1.0 s; 12,500,000 bits at 2,500,000 bps takes
5.0 s; clearing 100,000,000 bits in a 50 s window needs 2,000,000 bps.
Storage: 1000 bytes/orbit for 3 orbits is 3000 bytes, and a 10% margin
makes it exactly 3300 bytes. Framing: 100 data bits in 32-bit frames
needs 4 frames; 33 bits needs 2. Redundancy: 2 healthy strings with
requirement 1 is available; 0 healthy strings is not.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import command_data_handling_logic as cdh  # noqa: E402


class Crc16Test(unittest.TestCase):
    def test_standard_check_value(self):
        # Published CRC-16-CCITT check value for b"123456789".
        self.assertEqual(cdh.crc16_ccitt(b"123456789"), 0x29B1)

    def test_empty_input_is_init_value(self):
        self.assertEqual(cdh.crc16_ccitt(b""), 0xFFFF)

    def test_single_bit_flip_changes_crc(self):
        a = cdh.crc16_ccitt(b"\x00\x01\x02\x03")
        b = cdh.crc16_ccitt(b"\x00\x01\x02\x83")  # flip MSB of last byte
        self.assertNotEqual(a, b)


class TelemetryPacketTest(unittest.TestCase):
    def test_byte_exact_layout(self):
        # apid 7, seq 0, flags 3 (unsegmented), data 0xAA 0xBB:
        # header = 00 07 C0 00 00 01, data = AA BB, CRC = 45 7F.
        pkt = cdh.telemetry_packet(7, 0, b"\xAA\xBB")
        self.assertEqual(
            pkt, bytes([0x00, 0x07, 0xC0, 0x00, 0x00, 0x01, 0xAA, 0xBB, 0x45, 0x7F])
        )
        self.assertEqual(len(pkt), 10)

    def test_parse_roundtrip(self):
        data = bytes(range(32))
        pkt = cdh.telemetry_packet(0x2A, 1234, data)
        parsed = cdh.parse_telemetry_packet(pkt)
        self.assertEqual(parsed["apid"], 0x2A)
        self.assertEqual(parsed["seq_count"], 1234)
        self.assertEqual(parsed["seq_flags"], 3)
        self.assertEqual(parsed["data"], data)

    def test_corrupted_payload_raises_crc_mismatch(self):
        pkt = bytearray(cdh.telemetry_packet(7, 5, b"\x10\x20\x30"))
        pkt[6] ^= 0x01  # corrupt one payload bit, trailer untouched
        with self.assertRaises(ValueError):
            cdh.parse_telemetry_packet(pkt)

    def test_apid_and_sequence_bounds(self):
        cdh.telemetry_packet(0x7FF, 0x3FFF, b"\x01")  # max apid and seq ok
        with self.assertRaises(ValueError):
            cdh.telemetry_packet(0x800, 0, b"\x01")
        with self.assertRaises(ValueError):
            cdh.telemetry_packet(0, 0x4000, b"\x01")
        with self.assertRaises(ValueError):
            cdh.telemetry_packet(0, 0, b"")  # empty data rejected

    def test_too_short_packet_raises(self):
        with self.assertRaises(ValueError):
            cdh.parse_telemetry_packet(b"\x00\x07\xC0\x00\x00\x01\xAA\xBB")


class CommandValidationTest(unittest.TestCase):
    def test_byte_exact_layout_and_valid(self):
        cmd = cdh.command_packet(0x12, 0x07, b"\x01\x02\x03")
        self.assertEqual(
            cmd, bytes([0x12, 0x00, 0x07, 0x00, 0x03, 0x01, 0x02, 0x03, 0xB1, 0x80])
        )
        self.assertEqual(cdh.validate_command_packet(cmd), (True, "ok"))

    def test_expected_opcode_and_apid_checks(self):
        cmd = cdh.command_packet(0x12, 0x07, b"\x01")
        self.assertEqual(cdh.validate_command_packet(cmd, expected_opcode=0x12),
                         (True, "ok"))
        self.assertEqual(cdh.validate_command_packet(cmd, expected_opcode=0x11),
                         (False, "unexpected opcode"))
        self.assertEqual(cdh.validate_command_packet(cmd, expected_apid=0x08),
                         (False, "unexpected apid"))

    def test_corrupted_command_fails_crc(self):
        cmd = bytearray(cdh.command_packet(0x12, 0x07, b"\x01\x02\x03"))
        cmd[5] ^= 0x01  # corrupt payload, trailer untouched
        self.assertEqual(cdh.validate_command_packet(cmd), (False, "crc mismatch"))

    def test_length_field_mismatch_rejected(self):
        cmd = cdh.command_packet(0x12, 0x07, b"\x01\x02\x03")
        truncated = cmd[:6] + cmd[8:]  # drop one payload byte
        self.assertEqual(cdh.validate_command_packet(truncated),
                         (False, "length field mismatch"))

    def test_too_short_command_rejected(self):
        self.assertEqual(cdh.validate_command_packet(b"\x12\x00"), (False, "packet too short"))


class DownlinkBudgetTest(unittest.TestCase):
    def test_exact_times(self):
        self.assertEqual(cdh.downlink_time_s(1_000_000, 1_000_000), 1.0)
        self.assertEqual(cdh.downlink_time_s(12_500_000, 2_500_000), 5.0)

    def test_zero_volume_takes_zero_time(self):
        self.assertEqual(cdh.downlink_time_s(0, 1_000_000), 0.0)

    def test_rate_required_for_window(self):
        self.assertEqual(cdh.data_rate_for_window(100_000_000, 50), 2_000_000.0)

    def test_fits_window_verdict(self):
        self.assertTrue(cdh.downlink_fits_window(1_000_000, 1_000_000, 1.5))
        self.assertFalse(cdh.downlink_fits_window(1_000_000, 1_000_000, 0.5))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cdh.downlink_time_s(1, 0)
        with self.assertRaises(ValueError):
            cdh.downlink_time_s(-1, 1_000)
        with self.assertRaises(ValueError):
            cdh.data_rate_for_window(1, 0)


class StorageSizingTest(unittest.TestCase):
    def test_plain_three_orbits(self):
        self.assertEqual(cdh.storage_size_bytes(1000, 3), 3000)

    def test_margin_is_exact(self):
        # 10% margin on 3000 bytes is exactly 3300 (integer math, no float drift).
        self.assertEqual(cdh.storage_size_bytes(1000, 3, margin_fraction=0.1), 3300)
        self.assertEqual(cdh.storage_size_bytes(1000, 3, margin_fraction=0.0), 3000)

    def test_zero_orbits_and_partial_byte_round_up(self):
        self.assertEqual(cdh.storage_size_bytes(1000, 0), 0)
        self.assertEqual(cdh.storage_size_bytes(1, 1, margin_fraction=0.5), 2)

    def test_negative_inputs_raise(self):
        with self.assertRaises(ValueError):
            cdh.storage_size_bytes(-1, 3)
        with self.assertRaises(ValueError):
            cdh.storage_size_bytes(1000, -1)


class FramingTest(unittest.TestCase):
    def test_ceil_division(self):
        self.assertEqual(cdh.frame_count(100, 32), 4)
        self.assertEqual(cdh.frame_count(32, 32), 1)
        self.assertEqual(cdh.frame_count(33, 32), 2)

    def test_zero_volume_needs_no_frames(self):
        self.assertEqual(cdh.frame_count(0, 32), 0)

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cdh.frame_count(100, 0)


class RedundancyTest(unittest.TestCase):
    def test_dual_string_availability(self):
        self.assertTrue(cdh.redundancy_ok(2, required=1))
        self.assertTrue(cdh.redundancy_ok(1, required=1))
        self.assertFalse(cdh.redundancy_ok(0, required=1))
        self.assertFalse(cdh.redundancy_ok(1, required=2))

    def test_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            cdh.redundancy_ok(1, required=0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
