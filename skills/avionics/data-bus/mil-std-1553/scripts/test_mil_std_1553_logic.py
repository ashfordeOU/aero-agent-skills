#!/usr/bin/env python3
"""Gate 3 contract test: MIL-STD-1553B word encoding and classification
(paraphrase).

Exercises scripts/mil_std_1553_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - the worked anchor command
word encodes to the expected 20-bit integer with odd parity, decode
round-trips every field, data and status words encode and decode, the
odd parity check catches a flipped bit, message format classification
covers BC-to-RT, RT-to-BC, RT-to-RT, broadcast, and mode code, and
out-of-range fields raise ValueError.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mil_std_1553_logic as m1553  # noqa: E402

# Worked anchor: RT address 5 (00101), T/R 1 (transmit), subaddress 12
# (01100), word count 16 (10000). Data field 11664 has 6 set bits plus
# the 1-0-0 sync has 1 set bit, so the odd parity bit is 0 and the full
# 20-bit word 93316 keeps odd parity.
ANCHOR_CMD = 93316


class CommandWordEncodeTest(unittest.TestCase):
    def test_anchor_command_word_encodes_to_expected_integer(self):
        self.assertEqual(m1553.encode_command_word(5, 12, 16, 1), ANCHOR_CMD)

    def test_anchor_word_has_odd_parity(self):
        self.assertEqual(bin(ANCHOR_CMD).count("1") % 2, 1)
        self.assertTrue(m1553.parity_ok(ANCHOR_CMD))

    def test_computed_parity_makes_popcount_odd(self):
        word = m1553.encode_command_word(3, 5, 7, 0)
        self.assertEqual(bin(word).count("1") % 2, 1)

    def test_command_sync_pattern(self):
        self.assertEqual(ANCHOR_CMD & 0b111, m1553.SYNC_COMMAND)

    def test_max_field_values_encode(self):
        word = m1553.encode_command_word(31, 31, 31, 1)
        self.assertLessEqual(word, m1553.WORD_MASK)
        self.assertTrue(m1553.parity_ok(word))


class CommandWordDecodeTest(unittest.TestCase):
    def test_anchor_decode_round_trips_all_fields(self):
        fields = m1553.decode_command_word(ANCHOR_CMD)
        self.assertEqual(fields["rt_address"], 5)
        self.assertEqual(fields["transmit_receive"], 1)
        self.assertEqual(fields["subaddress"], 12)
        self.assertEqual(fields["word_count"], 16)
        self.assertEqual(fields["parity"], 0)
        self.assertTrue(fields["parity_ok"])

    def test_random_word_round_trip(self):
        for rt, sub, wc, tr in ((1, 1, 1, 0), (31, 31, 31, 1),
                                (7, 20, 30, 0), (30, 3, 2, 1)):
            word = m1553.encode_command_word(rt, sub, wc, tr)
            fields = m1553.decode_command_word(word)
            self.assertEqual(fields["rt_address"], rt)
            self.assertEqual(fields["transmit_receive"], tr)
            self.assertEqual(fields["subaddress"], sub)
            self.assertEqual(fields["word_count"], wc)
            self.assertEqual(fields["parity"], word >> 19)
            self.assertTrue(fields["parity_ok"])

    def test_data_sync_word_rejected_as_command(self):
        data_word = m1553.encode_data_word(100)
        with self.assertRaises(ValueError):
            m1553.decode_command_word(data_word)


class DataWordTest(unittest.TestCase):
    def test_anchor_data_word_encodes(self):
        self.assertEqual(m1553.encode_data_word(0x7FFF), 262139)

    def test_data_word_odd_parity(self):
        self.assertEqual(bin(262139).count("1") % 2, 1)

    def test_data_word_round_trip(self):
        for data in (0, 1, 0x8000, 0xFFFF, 12345):
            word = m1553.encode_data_word(data)
            fields = m1553.decode_data_word(word)
            self.assertEqual(fields["data"], data)
            self.assertTrue(fields["parity_ok"])

    def test_command_sync_word_rejected_as_data(self):
        with self.assertRaises(ValueError):
            m1553.decode_data_word(ANCHOR_CMD)

    def test_data_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            m1553.encode_data_word(0x10000)
        with self.assertRaises(ValueError):
            m1553.encode_data_word(-1)


class StatusWordTest(unittest.TestCase):
    def test_anchor_status_word_encodes(self):
        self.assertEqual(m1553.encode_status_word(5, busy=1), 606276)

    def test_status_word_odd_parity(self):
        self.assertEqual(bin(606276).count("1") % 2, 1)

    def test_status_word_round_trip_flags(self):
        word = m1553.encode_status_word(
            5, message_error=1, service_request=1, broadcast_received=1,
            subsystem_flag=1, dynamic_bus_control_acceptance=1)
        fields = m1553.decode_status_word(word)
        self.assertEqual(fields["rt_address"], 5)
        self.assertEqual(fields["message_error"], 1)
        self.assertEqual(fields["service_request"], 1)
        self.assertEqual(fields["broadcast_received"], 1)
        self.assertEqual(fields["subsystem_flag"], 1)
        self.assertEqual(fields["dynamic_bus_control_acceptance"], 1)
        self.assertEqual(fields["instrumentation"], 0)
        self.assertEqual(fields["busy"], 0)
        self.assertEqual(fields["terminal_flag"], 0)
        self.assertTrue(fields["parity_ok"])

    def test_default_status_word_is_quiet(self):
        word = m1553.encode_status_word(9)
        fields = m1553.decode_status_word(word)
        self.assertEqual(fields["rt_address"], 9)
        for flag in ("message_error", "instrumentation", "service_request",
                     "broadcast_received", "busy", "subsystem_flag",
                     "dynamic_bus_control_acceptance", "terminal_flag"):
            self.assertEqual(fields[flag], 0)


class MessageFormatTest(unittest.TestCase):
    def test_bc_to_rt(self):
        self.assertEqual(m1553.classify_message(5, 12, 16, 0), "bc-to-rt")

    def test_rt_to_bc(self):
        self.assertEqual(m1553.classify_message(5, 12, 16, 1), "rt-to-bc")

    def test_broadcast(self):
        self.assertEqual(m1553.classify_message(31, 8, 8, 0), "broadcast")

    def test_mode_code_low_subaddress(self):
        self.assertEqual(m1553.classify_message(3, 0, 17, 0), "mode-code")

    def test_mode_code_high_subaddress(self):
        self.assertEqual(m1553.classify_message(3, 31, 17, 0), "mode-code")

    def test_mode_command_encodes_mode_code_in_word_count_field(self):
        word = m1553.encode_command_word(3, 0, 17, 0)
        fields = m1553.decode_command_word(word)
        self.assertEqual(fields["subaddress"], 0)
        self.assertEqual(fields["word_count"], 17)


class RtToRtTest(unittest.TestCase):
    def test_valid_pair(self):
        rx = m1553.encode_command_word(5, 12, 16, 0)
        tx = m1553.encode_command_word(6, 12, 16, 1)
        self.assertTrue(m1553.is_rt_to_rt_pair(rx, tx))

    def test_two_receive_commands_is_not_rt_to_rt(self):
        rx = m1553.encode_command_word(5, 12, 16, 0)
        self.assertFalse(m1553.is_rt_to_rt_pair(rx, rx))

    def test_mode_command_pair_is_not_rt_to_rt(self):
        rx = m1553.encode_command_word(5, 12, 16, 0)
        mode = m1553.encode_command_word(6, 0, 17, 1)
        self.assertFalse(m1553.is_rt_to_rt_pair(rx, mode))

    def test_broadcast_pair_is_not_rt_to_rt(self):
        rx = m1553.encode_command_word(5, 12, 16, 0)
        bcast = m1553.encode_command_word(31, 12, 16, 1)
        self.assertFalse(m1553.is_rt_to_rt_pair(rx, bcast))


class BoundsTest(unittest.TestCase):
    def test_rt_address_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            m1553.encode_command_word(32, 0, 0, 0)
        with self.assertRaises(ValueError):
            m1553.encode_command_word(-1, 0, 0, 0)

    def test_subaddress_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            m1553.encode_command_word(0, 32, 0, 0)

    def test_word_count_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            m1553.encode_command_word(0, 0, 32, 0)

    def test_transmit_receive_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            m1553.encode_command_word(0, 0, 0, 2)

    def test_classify_invalid_inputs_raise(self):
        with self.assertRaises(ValueError):
            m1553.classify_message(32, 0, 0, 0)
        with self.assertRaises(ValueError):
            m1553.classify_message(0, 32, 0, 0)
        with self.assertRaises(ValueError):
            m1553.classify_message(0, 0, 32, 0)
        with self.assertRaises(ValueError):
            m1553.classify_message(0, 0, 0, 2)

    def test_word_bounds_raise(self):
        with self.assertRaises(ValueError):
            m1553.decode_command_word(1 << 20)
        with self.assertRaises(ValueError):
            m1553.decode_command_word(-1)
        with self.assertRaises(ValueError):
            m1553.parity_ok(1 << 20)

    def test_non_integer_input_raises(self):
        with self.assertRaises(ValueError):
            m1553.encode_command_word("5", 12, 16, 1)
        with self.assertRaises(ValueError):
            m1553.encode_command_word(5, 12, 16, True)
        with self.assertRaises(ValueError):
            m1553.encode_data_word(3.5)


class ParityConsistencyTest(unittest.TestCase):
    def test_built_words_always_odd_parity(self):
        words = [
            m1553.encode_command_word(0, 0, 0, 0),
            m1553.encode_command_word(31, 31, 31, 1),
            m1553.encode_data_word(0),
            m1553.encode_data_word(0xFFFF),
            m1553.encode_status_word(31, message_error=1, terminal_flag=1),
        ]
        for word in words:
            self.assertEqual(bin(word).count("1") % 2, 1)
            self.assertTrue(m1553.parity_ok(word))

    def test_flipped_parity_bit_is_detected(self):
        fields = m1553.decode_command_word(ANCHOR_CMD ^ (1 << 19))
        self.assertFalse(fields["parity_ok"])

    def test_flipped_data_bit_is_detected(self):
        self.assertFalse(m1553.parity_ok(ANCHOR_CMD ^ (1 << 3)))

    def test_all_zero_word_is_not_odd_parity(self):
        self.assertFalse(m1553.parity_ok(0))


if __name__ == "__main__":
    unittest.main(verbosity=2)
