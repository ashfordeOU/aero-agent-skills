"""Contract test for the RMAP write-command leaf (stdlib unittest)."""

import unittest

from e5052_rmap_write_command_logic import (
    CHECK_POLYNOMIAL_REFLECTED,
    FIXED_HEADER_BYTES,
    MAX_BASE_ADDRESS,
    MAX_DATA_LENGTH,
    PACKET_TYPE_COMMAND,
    REPLY_ADDRESS_LENGTHS,
    address_span,
    assess_write_command,
    check_value,
    decode_instruction_byte,
    header_bytes,
    instruction_byte,
    padded_reply_address,
    reply_address_length_code,
    validate_write_command,
    write_packet_size,
)


def spec(**kw):
    record = {
        "target_logical_address": 0x20,
        "initiator_logical_address": 0xFE,
        "destination_key": 0x02,
        "transaction_id": 7,
        "extended_address": 0,
        "address": 0x1000,
        "data_length": 64,
        "verify": False,
        "acknowledge": True,
        "increment": True,
    }
    record.update(kw)
    return record


class TestValidateWriteCommand(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_write_command({"data_length": 4})
        self.assertTrue(norm["acknowledge"])
        self.assertTrue(norm["increment"])
        self.assertFalse(norm["verify"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_write_command([1, 2, 3])

    def test_zero_data_length_raises(self):
        with self.assertRaises(ValueError):
            validate_write_command(spec(data_length=0))

    def test_missing_data_length_raises(self):
        bare = spec()
        del bare["data_length"]
        with self.assertRaises(ValueError):
            validate_write_command(bare)

    def test_data_length_beyond_the_field_raises(self):
        with self.assertRaises(ValueError):
            validate_write_command(spec(data_length=MAX_DATA_LENGTH + 1))

    def test_address_beyond_the_field_raises(self):
        with self.assertRaises(ValueError):
            validate_write_command(spec(address=MAX_BASE_ADDRESS + 1))

    def test_non_boolean_verify_raises(self):
        with self.assertRaises(ValueError):
            validate_write_command(spec(verify="yes"))

    def test_data_byte_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            validate_write_command(spec(data=[0, 256], data_length=None))

    def test_declared_length_disagreeing_with_data_raises(self):
        with self.assertRaises(ValueError):
            validate_write_command(spec(data=[1, 2, 3], data_length=4))

    def test_supplied_data_sets_the_length(self):
        norm = validate_write_command(spec(data=[1, 2, 3], data_length=None))
        self.assertEqual(norm["data_length"], 3)

    def test_transaction_id_beyond_two_bytes_raises(self):
        with self.assertRaises(ValueError):
            validate_write_command(spec(transaction_id=65536))


class TestReplyAddress(unittest.TestCase):
    def test_absent_reply_address_is_code_zero(self):
        self.assertEqual(reply_address_length_code(None), 0)

    def test_empty_reply_address_is_code_zero(self):
        self.assertEqual(reply_address_length_code([]), 0)

    def test_one_byte_path_takes_one_group(self):
        self.assertEqual(reply_address_length_code([3]), 1)

    def test_five_byte_path_takes_two_groups(self):
        self.assertEqual(reply_address_length_code([1, 2, 3, 4, 5]), 2)

    def test_oversized_path_raises(self):
        with self.assertRaises(ValueError):
            reply_address_length_code(list(range(13)))

    def test_path_is_left_padded_with_zero_bytes(self):
        self.assertEqual(padded_reply_address([3]), [0, 0, 0, 3])

    def test_no_padding_for_an_absent_path(self):
        self.assertEqual(padded_reply_address(None), [])

    def test_field_widths_are_whole_groups_of_four(self):
        self.assertEqual(REPLY_ADDRESS_LENGTHS, (0, 4, 8, 12))

    def test_bad_reply_address_type_raises(self):
        with self.assertRaises(ValueError):
            reply_address_length_code("0304")


class TestCheckValue(unittest.TestCase):
    def test_empty_sequence_is_zero(self):
        self.assertEqual(check_value([]), 0)

    def test_value_is_a_single_byte(self):
        self.assertTrue(0 <= check_value([1, 2, 3, 4, 5, 6, 7, 8]) <= 255)

    def test_appending_the_check_value_makes_the_run_close_to_zero(self):
        payload = [0x10, 0x20, 0x30, 0x40]
        crc = check_value(payload)
        self.assertEqual(check_value(payload + [crc]), 0)

    def test_a_flipped_bit_changes_the_value(self):
        self.assertNotEqual(check_value([0x10, 0x20]), check_value([0x11, 0x20]))

    def test_byte_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            check_value([0, 300])

    def test_polynomial_is_the_reflected_form(self):
        self.assertEqual(CHECK_POLYNOMIAL_REFLECTED, 0xE0)


class TestInstructionByte(unittest.TestCase):
    def test_write_bit_is_set(self):
        self.assertTrue((instruction_byte(spec()) >> 5) & 1)

    def test_packet_type_marks_a_command(self):
        self.assertEqual((instruction_byte(spec()) >> 6) & 0b11, PACKET_TYPE_COMMAND)

    def test_option_bits_round_trip(self):
        packed = instruction_byte(spec(verify=True, acknowledge=False, increment=False))
        options = decode_instruction_byte(packed)
        self.assertTrue(options["verify"])
        self.assertFalse(options["acknowledge"])
        self.assertFalse(options["increment"])

    def test_reply_address_code_round_trips(self):
        packed = instruction_byte(spec(reply_address=[1, 2, 3, 4, 5]))
        self.assertEqual(decode_instruction_byte(packed)["reply_address_code"], 2)

    def test_reply_packet_type_is_rejected(self):
        with self.assertRaises(ValueError):
            decode_instruction_byte(0b00_1_0_1_1_00)

    def test_read_instruction_is_rejected(self):
        with self.assertRaises(ValueError):
            decode_instruction_byte(0b01_0_0_1_1_00)


class TestSizing(unittest.TestCase):
    def test_header_without_a_reply_path_is_the_fixed_size(self):
        self.assertEqual(header_bytes(spec()), FIXED_HEADER_BYTES)

    def test_reply_path_adds_a_whole_group(self):
        self.assertEqual(header_bytes(spec(reply_address=[3])), FIXED_HEADER_BYTES + 4)

    def test_packet_is_header_plus_data_plus_the_data_check_byte(self):
        self.assertEqual(write_packet_size(spec(data_length=64)),
                         FIXED_HEADER_BYTES + 64 + 1)

    def test_incrementing_span_covers_every_byte(self):
        self.assertEqual(address_span(spec(address=0x100, data_length=16)),
                         (0x100, 0x10F))

    def test_non_incrementing_span_is_one_address(self):
        self.assertEqual(address_span(spec(address=0x100, data_length=16, increment=False)),
                         (0x100, 0x100))


class TestAssessWriteCommand(unittest.TestCase):
    def test_plain_write_is_acceptable(self):
        result = assess_write_command(spec())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_verified_write_within_the_buffer_is_acceptable(self):
        result = assess_write_command(spec(verify=True, data_length=32,
                                           verify_buffer_bytes=64))
        self.assertTrue(result["acceptable"])

    def test_verified_write_exactly_filling_the_buffer_is_acceptable(self):
        result = assess_write_command(spec(verify=True, data_length=64,
                                           verify_buffer_bytes=64))
        self.assertTrue(result["acceptable"])

    def test_verified_write_overrunning_the_buffer_is_flagged(self):
        result = assess_write_command(spec(verify=True, data_length=128,
                                           verify_buffer_bytes=64))
        self.assertFalse(result["acceptable"])
        self.assertTrue(any("verify buffer" in f for f in result["findings"]))

    def test_verified_write_without_a_reply_is_flagged(self):
        result = assess_write_command(spec(verify=True, acknowledge=False,
                                           verify_buffer_bytes=256))
        self.assertTrue(any("no reply" in f for f in result["findings"]))

    def test_verified_write_to_one_address_is_flagged(self):
        result = assess_write_command(spec(verify=True, increment=False,
                                           verify_buffer_bytes=256))
        self.assertTrue(any("non-incrementing" in f for f in result["findings"]))

    def test_span_running_past_the_address_field_is_flagged(self):
        result = assess_write_command(spec(address=MAX_BASE_ADDRESS - 2, data_length=16))
        self.assertTrue(any("address field" in f for f in result["findings"]))

    def test_data_check_value_is_reported_when_data_is_supplied(self):
        result = assess_write_command(spec(data=[1, 2, 3, 4], data_length=None))
        self.assertEqual(result["data_check_value"], check_value([1, 2, 3, 4]))

    def test_data_check_value_is_absent_when_only_a_length_is_declared(self):
        self.assertNotIn("data_check_value", assess_write_command(spec()))


if __name__ == "__main__":
    unittest.main()
