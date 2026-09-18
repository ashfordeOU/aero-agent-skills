"""Contract test for the RMAP read-command leaf (stdlib unittest)."""

import unittest

from e5052_rmap_read_command_logic import (
    COMMAND_HEADER_BYTES,
    MAX_BASE_ADDRESS,
    MAX_DATA_LENGTH,
    PACKET_TYPE_COMMAND,
    REGION_MEMORY,
    REGION_PORT,
    REPLY_ADDRESS_LENGTHS,
    REPLY_HEADER_BYTES,
    address_span,
    assess_read_command,
    check_reply,
    decode_instruction_byte,
    instruction_byte,
    padded_reply_address,
    read_command_size,
    read_reply_size,
    reply_address_length_code,
    returned_data_share,
    validate_read_command,
)


def spec(**kw):
    record = {
        "target_logical_address": 0x20,
        "initiator_logical_address": 0xFE,
        "destination_key": 0x02,
        "transaction_id": 11,
        "extended_address": 0,
        "address": 0x2000,
        "data_length": 64,
        "verify": False,
        "acknowledge": True,
        "increment": True,
    }
    record.update(kw)
    return record


class TestValidateReadCommand(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_read_command({"data_length": 8})
        self.assertTrue(norm["acknowledge"])
        self.assertTrue(norm["increment"])
        self.assertIsNone(norm["region"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_read_command("read 64 bytes")

    def test_payload_on_a_read_raises(self):
        with self.assertRaises(ValueError):
            validate_read_command(spec(data=[1, 2, 3]))

    def test_missing_length_raises(self):
        bare = spec()
        del bare["data_length"]
        with self.assertRaises(ValueError):
            validate_read_command(bare)

    def test_zero_length_read_raises(self):
        with self.assertRaises(ValueError):
            validate_read_command(spec(data_length=0))

    def test_length_beyond_the_field_raises(self):
        with self.assertRaises(ValueError):
            validate_read_command(spec(data_length=MAX_DATA_LENGTH + 1))

    def test_address_beyond_the_field_raises(self):
        with self.assertRaises(ValueError):
            validate_read_command(spec(address=MAX_BASE_ADDRESS + 1))

    def test_unknown_region_raises(self):
        with self.assertRaises(ValueError):
            validate_read_command(spec(region="cache"))

    def test_boolean_transaction_id_raises(self):
        with self.assertRaises(ValueError):
            validate_read_command(spec(transaction_id=True))

    def test_non_boolean_increment_raises(self):
        with self.assertRaises(ValueError):
            validate_read_command(spec(increment=1))


class TestReplyAddress(unittest.TestCase):
    def test_absent_path_is_code_zero(self):
        self.assertEqual(reply_address_length_code(None), 0)

    def test_four_byte_path_is_one_group(self):
        self.assertEqual(reply_address_length_code([1, 2, 3, 4]), 1)

    def test_nine_byte_path_is_three_groups(self):
        self.assertEqual(reply_address_length_code(list(range(9))), 3)

    def test_oversized_path_raises(self):
        with self.assertRaises(ValueError):
            reply_address_length_code(list(range(13)))

    def test_short_path_is_left_padded(self):
        self.assertEqual(padded_reply_address([7, 8]), [0, 0, 7, 8])

    def test_field_widths_are_whole_groups_of_four(self):
        self.assertEqual(REPLY_ADDRESS_LENGTHS, (0, 4, 8, 12))


class TestInstructionByte(unittest.TestCase):
    def test_write_bit_is_clear(self):
        self.assertFalse((instruction_byte(spec()) >> 5) & 1)

    def test_packet_type_marks_a_command(self):
        self.assertEqual((instruction_byte(spec()) >> 6) & 0b11, PACKET_TYPE_COMMAND)

    def test_options_round_trip(self):
        packed = instruction_byte(spec(acknowledge=True, increment=False,
                                       reply_address=[5]))
        options = decode_instruction_byte(packed)
        self.assertTrue(options["acknowledge"])
        self.assertFalse(options["increment"])
        self.assertEqual(options["reply_address_code"], 1)

    def test_write_instruction_is_rejected(self):
        with self.assertRaises(ValueError):
            decode_instruction_byte(0b01_1_0_1_1_00)

    def test_reply_packet_type_is_rejected(self):
        with self.assertRaises(ValueError):
            decode_instruction_byte(0b00_0_0_1_1_00)

    def test_instruction_byte_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            decode_instruction_byte(300)


class TestSizing(unittest.TestCase):
    def test_command_carries_no_payload(self):
        self.assertEqual(read_command_size(spec(data_length=1024)), COMMAND_HEADER_BYTES)

    def test_reply_path_lengthens_the_command_only(self):
        self.assertEqual(read_command_size(spec(reply_address=[3])),
                         COMMAND_HEADER_BYTES + 4)

    def test_reply_is_header_plus_data_plus_the_data_check_byte(self):
        self.assertEqual(read_reply_size(spec(data_length=64)),
                         REPLY_HEADER_BYTES + 64 + 1)

    def test_unacknowledged_read_has_no_reply_on_the_link(self):
        self.assertEqual(read_reply_size(spec(acknowledge=False)), 0)

    def test_incrementing_span_covers_every_byte(self):
        self.assertEqual(address_span(spec(address=0x40, data_length=8)), (0x40, 0x47))

    def test_non_incrementing_span_is_one_address(self):
        self.assertEqual(address_span(spec(address=0x40, data_length=8, increment=False)),
                         (0x40, 0x40))

    def test_returned_data_share_matches_the_hand_calculation(self):
        share = returned_data_share(spec(data_length=64))
        self.assertAlmostEqual(share, 64.0 / (16 + 12 + 64 + 1), places=12)

    def test_longer_reads_return_a_larger_share(self):
        self.assertGreater(returned_data_share(spec(data_length=1024)),
                           returned_data_share(spec(data_length=4)))


class TestCheckReply(unittest.TestCase):
    def test_matching_reply_has_no_findings(self):
        self.assertEqual(check_reply(spec(), {"status": 0, "data_length": 64,
                                             "transaction_id": 11}), [])

    def test_short_return_is_flagged(self):
        findings = check_reply(spec(), {"status": 0, "data_length": 32,
                                        "transaction_id": 11})
        self.assertTrue(any("against the" in f for f in findings))

    def test_failed_reply_carrying_data_is_flagged(self):
        findings = check_reply(spec(), {"status": 4, "data_length": 64,
                                        "transaction_id": 11})
        self.assertTrue(any("still carries" in f for f in findings))

    def test_failed_reply_with_no_data_is_clean(self):
        self.assertEqual(check_reply(spec(), {"status": 4, "data_length": 0,
                                             "transaction_id": 11}), [])

    def test_mismatched_identifier_is_flagged(self):
        findings = check_reply(spec(), {"status": 0, "data_length": 64,
                                        "transaction_id": 12})
        self.assertTrue(any("does not match" in f for f in findings))

    def test_reply_to_an_unacknowledged_read_is_flagged(self):
        findings = check_reply(spec(acknowledge=False),
                               {"status": 0, "data_length": 64, "transaction_id": 11})
        self.assertTrue(any("asked for none" in f for f in findings))

    def test_non_mapping_reply_raises(self):
        with self.assertRaises(ValueError):
            check_reply(spec(), [0, 64])

    def test_out_of_range_status_raises(self):
        with self.assertRaises(ValueError):
            check_reply(spec(), {"status": 300, "data_length": 0})


class TestAssessReadCommand(unittest.TestCase):
    def test_plain_read_is_acceptable(self):
        result = assess_read_command(spec())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_unacknowledged_read_is_flagged(self):
        result = assess_read_command(spec(acknowledge=False))
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("nowhere to be returned" in f for f in result["findings"]))

    def test_verify_bit_on_a_read_is_flagged(self):
        result = assess_read_command(spec(verify=True))
        self.assertTrue(any("nothing to verify" in f for f in result["findings"]))

    def test_span_past_the_address_field_is_flagged(self):
        result = assess_read_command(spec(address=MAX_BASE_ADDRESS - 1, data_length=8))
        self.assertTrue(any("address field" in f for f in result["findings"]))

    def test_incrementing_read_of_a_port_is_flagged(self):
        result = assess_read_command(spec(region=REGION_PORT, increment=True))
        self.assertTrue(any("port-style" in f for f in result["findings"]))

    def test_non_incrementing_read_of_a_port_is_acceptable(self):
        result = assess_read_command(spec(region=REGION_PORT, increment=False))
        self.assertTrue(result["acceptable"])

    def test_non_incrementing_read_of_memory_is_flagged(self):
        result = assess_read_command(spec(region=REGION_MEMORY, increment=False))
        self.assertTrue(any("one location" in f for f in result["findings"]))

    def test_single_byte_non_incrementing_memory_read_is_acceptable(self):
        result = assess_read_command(spec(region=REGION_MEMORY, increment=False,
                                          data_length=1))
        self.assertTrue(result["acceptable"])

    def test_reply_findings_are_folded_into_the_verdict(self):
        result = assess_read_command(spec(), {"status": 0, "data_length": 8,
                                             "transaction_id": 11})
        self.assertFalse(result["acceptable"])
        self.assertTrue(result["reply_findings"])

    def test_clean_reply_keeps_the_verdict_acceptable(self):
        result = assess_read_command(spec(), {"status": 0, "data_length": 64,
                                             "transaction_id": 11})
        self.assertTrue(result["acceptable"])


if __name__ == "__main__":
    unittest.main()
