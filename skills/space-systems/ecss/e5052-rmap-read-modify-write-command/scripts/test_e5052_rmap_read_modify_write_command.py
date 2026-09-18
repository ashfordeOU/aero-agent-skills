"""Contract test for the RMAP read-modify-write leaf (stdlib unittest)."""

import unittest

from e5052_rmap_read_modify_write_command_logic import (
    COMMAND_HEADER_BYTES,
    MAX_BASE_ADDRESS,
    PACKET_TYPE_COMMAND,
    REPLY_HEADER_BYTES,
    RMW_OPTION_BITS,
    assess_rmw_command,
    bits_changed,
    bits_selected,
    command_size,
    decode_instruction_byte,
    instruction_byte,
    mask_selectivity,
    masked_merge,
    operand_width,
    permitted_data_lengths,
    reply_address_length_code,
    reply_data_length,
    reply_size,
    split_operand_and_mask,
    validate_rmw_command,
)


def spec(**kw):
    record = {
        "target_logical_address": 0x20,
        "initiator_logical_address": 0xFE,
        "destination_key": 0x02,
        "transaction_id": 3,
        "extended_address": 0,
        "address": 0x40,
        "data": [0x0F, 0x00, 0x0F, 0x0F],
    }
    record.update(kw)
    return record


class TestValidateRmwCommand(unittest.TestCase):
    def test_data_length_is_derived_from_the_field(self):
        self.assertEqual(validate_rmw_command(spec())["data_length"], 4)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_rmw_command([0x0F, 0x0F])

    def test_empty_data_raises(self):
        with self.assertRaises(ValueError):
            validate_rmw_command(spec(data=[]))

    def test_odd_data_length_raises(self):
        with self.assertRaises(ValueError):
            validate_rmw_command(spec(data=[1, 2, 3]))

    def test_oversized_data_raises(self):
        with self.assertRaises(ValueError):
            validate_rmw_command(spec(data=list(range(10))))

    def test_data_byte_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            validate_rmw_command(spec(data=[0x0F, 300]))

    def test_declared_length_disagreeing_raises(self):
        with self.assertRaises(ValueError):
            validate_rmw_command(spec(declared_data_length=8))

    def test_declared_length_agreeing_is_accepted(self):
        self.assertEqual(validate_rmw_command(spec(declared_data_length=4))["data_length"], 4)

    def test_address_beyond_the_field_raises(self):
        with self.assertRaises(ValueError):
            validate_rmw_command(spec(address=MAX_BASE_ADDRESS + 1))

    def test_original_of_the_wrong_width_raises(self):
        with self.assertRaises(ValueError):
            validate_rmw_command(spec(original=[0x00]))

    def test_original_of_the_operand_width_is_accepted(self):
        norm = validate_rmw_command(spec(original=[0xF0, 0xF0]))
        self.assertEqual(norm["original"], [0xF0, 0xF0])

    def test_permitted_lengths_are_even(self):
        self.assertEqual(permitted_data_lengths(), (2, 4, 6, 8))


class TestSplitAndWidth(unittest.TestCase):
    def test_operand_width_is_half_the_data_field(self):
        self.assertEqual(operand_width(spec()), 2)

    def test_split_returns_operand_then_mask(self):
        operand, mask = split_operand_and_mask(spec())
        self.assertEqual(operand, [0x0F, 0x00])
        self.assertEqual(mask, [0x0F, 0x0F])

    def test_reply_returns_the_operand_width(self):
        self.assertEqual(reply_data_length(spec()), 2)

    def test_two_byte_field_is_a_single_byte_operand(self):
        self.assertEqual(operand_width(spec(data=[0x01, 0x01])), 1)


class TestInstructionByte(unittest.TestCase):
    def test_packet_type_marks_a_command(self):
        self.assertEqual((instruction_byte(spec()) >> 6) & 0b11, PACKET_TYPE_COMMAND)

    def test_option_bits_are_the_read_modify_write_combination(self):
        value = instruction_byte(spec())
        bits = ((value >> 5) & 1, (value >> 4) & 1, (value >> 3) & 1, (value >> 2) & 1)
        self.assertEqual(bits, RMW_OPTION_BITS)

    def test_reply_path_code_round_trips(self):
        packed = instruction_byte(spec(reply_address=[2, 3, 4, 5, 6]))
        self.assertEqual(decode_instruction_byte(packed)["reply_address_code"], 2)

    def test_plain_write_byte_is_rejected(self):
        with self.assertRaises(ValueError):
            decode_instruction_byte(0b01_1_0_1_1_00)

    def test_reply_packet_type_is_rejected(self):
        with self.assertRaises(ValueError):
            decode_instruction_byte(0b00_0_1_1_1_00)

    def test_oversized_reply_path_raises(self):
        with self.assertRaises(ValueError):
            reply_address_length_code(list(range(13)))


class TestSizing(unittest.TestCase):
    def test_command_carries_operand_mask_and_a_check_byte(self):
        self.assertEqual(command_size(spec()), COMMAND_HEADER_BYTES + 4 + 1)

    def test_reply_path_lengthens_the_command(self):
        self.assertEqual(command_size(spec(reply_address=[9])),
                         COMMAND_HEADER_BYTES + 4 + 4 + 1)

    def test_reply_carries_half_the_command_data(self):
        self.assertEqual(reply_size(spec()), REPLY_HEADER_BYTES + 2 + 1)

    def test_reply_is_shorter_than_the_command(self):
        self.assertLess(reply_size(spec()), command_size(spec()))


class TestMaskedMerge(unittest.TestCase):
    def test_masked_bits_come_from_the_operand(self):
        self.assertEqual(masked_merge([0xF0], [0x0F], [0x0F]), [0xFF])

    def test_unmasked_bits_are_left_alone(self):
        self.assertEqual(masked_merge([0xF0], [0xFF], [0x0F]), [0xFF])

    def test_empty_mask_leaves_the_content(self):
        self.assertEqual(masked_merge([0xA5], [0x5A], [0x00]), [0xA5])

    def test_full_mask_replaces_the_content(self):
        self.assertEqual(masked_merge([0xA5], [0x5A], [0xFF]), [0x5A])

    def test_width_mismatch_raises(self):
        with self.assertRaises(ValueError):
            masked_merge([0x01, 0x02], [0x01], [0x01])

    def test_empty_original_raises(self):
        with self.assertRaises(ValueError):
            masked_merge([], [], [])

    def test_bits_selected_counts_the_mask(self):
        self.assertEqual(bits_selected([0x0F, 0xF0]), 8)

    def test_selectivity_is_the_selected_fraction(self):
        self.assertAlmostEqual(mask_selectivity([0x0F, 0xF0]), 0.5, places=12)

    def test_full_mask_selectivity_is_one(self):
        self.assertAlmostEqual(mask_selectivity([0xFF]), 1.0, places=12)

    def test_empty_mask_selectivity_is_zero(self):
        self.assertAlmostEqual(mask_selectivity([0x00, 0x00]), 0.0, places=12)

    def test_bits_changed_counts_only_real_flips(self):
        self.assertEqual(bits_changed([0xF0], [0xFF], [0x0F]), 4)

    def test_bits_changed_is_zero_when_the_operand_already_matches(self):
        self.assertEqual(bits_changed([0xFF], [0xFF], [0x0F]), 0)


class TestAssessRmwCommand(unittest.TestCase):
    def test_partial_mask_on_an_aligned_address_is_acceptable(self):
        result = assess_rmw_command(spec())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_all_zero_mask_is_flagged(self):
        result = assess_rmw_command(spec(data=[0x00, 0x00, 0x00, 0x00]))
        self.assertTrue(any("no bits" in f for f in result["findings"]))

    def test_all_ones_mask_is_flagged(self):
        result = assess_rmw_command(spec(data=[0x12, 0x34, 0xFF, 0xFF]))
        self.assertTrue(any("plain write" in f for f in result["findings"]))

    def test_operand_bits_outside_the_mask_are_flagged(self):
        result = assess_rmw_command(spec(data=[0xF0, 0x00, 0x0F, 0x0F]))
        self.assertTrue(any("outside the mask" in f for f in result["findings"]))

    def test_unaligned_address_is_flagged(self):
        result = assess_rmw_command(spec(address=0x41))
        self.assertTrue(any("not aligned" in f for f in result["findings"]))

    def test_single_byte_operand_is_always_aligned(self):
        result = assess_rmw_command(spec(address=0x41, data=[0x01, 0x01]))
        self.assertTrue(result["acceptable"])

    def test_merged_content_is_reported_when_the_original_is_supplied(self):
        result = assess_rmw_command(spec(original=[0xF0, 0xF0]))
        self.assertEqual(result["merged"], [0xFF, 0xF0])

    def test_bits_changed_is_reported_with_the_original(self):
        result = assess_rmw_command(spec(original=[0xF0, 0xF0]))
        self.assertEqual(result["bits_changed"], 4)

    def test_merged_content_is_absent_without_the_original(self):
        self.assertNotIn("merged", assess_rmw_command(spec()))

    def test_reply_data_length_is_reported(self):
        self.assertEqual(assess_rmw_command(spec())["reply_data_length"], 2)


if __name__ == "__main__":
    unittest.main()
