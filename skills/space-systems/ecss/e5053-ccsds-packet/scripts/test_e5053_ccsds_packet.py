"""Contract test for the CCSDS packet leaf (stdlib unittest)."""

import unittest

from e5053_ccsds_packet_logic import (
    APID_IDLE,
    GROUPING_CONTINUATION,
    GROUPING_FIRST,
    GROUPING_LAST,
    GROUPING_UNSEGMENTED,
    MAX_APID,
    MAX_DATA_FIELD_BYTES,
    MAX_SEQUENCE_COUNT,
    PACKET_VERSION,
    PRIMARY_HEADER_BYTES,
    PROTOCOL_IDENTIFIER_BYTES,
    TYPE_TELECOMMAND,
    TYPE_TELEMETRY,
    assess_ccsds_packet,
    data_field_bytes_from_length_field,
    decode_primary_header,
    encode_primary_header,
    group_user_datum,
    next_sequence_count,
    packet_length_field,
    total_packet_bytes,
    transfer_frame_bytes,
    validate_packet_fields,
)


def fields(**kw):
    record = {
        "version": PACKET_VERSION,
        "type": TYPE_TELEMETRY,
        "secondary_header": False,
        "apid": 0x21,
        "grouping": GROUPING_UNSEGMENTED,
        "sequence_count": 100,
        "data_field_bytes": 64,
    }
    record.update(kw)
    return record


class TestValidatePacketFields(unittest.TestCase):
    def test_defaults_are_filled_in(self):
        norm = validate_packet_fields({"apid": 1, "data_field_bytes": 4})
        self.assertEqual(norm["grouping"], GROUPING_UNSEGMENTED)
        self.assertEqual(norm["type"], TYPE_TELEMETRY)
        self.assertFalse(norm["secondary_header"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_fields([0, 1, 2])

    def test_missing_apid_raises(self):
        bare = fields()
        del bare["apid"]
        with self.assertRaises(ValueError):
            validate_packet_fields(bare)

    def test_apid_beyond_the_field_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_fields(fields(apid=MAX_APID + 1))

    def test_other_version_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_fields(fields(version=1))

    def test_missing_data_field_length_raises(self):
        bare = fields()
        del bare["data_field_bytes"]
        with self.assertRaises(ValueError):
            validate_packet_fields(bare)

    def test_empty_data_field_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_fields(fields(data_field_bytes=0))

    def test_oversized_data_field_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_fields(fields(data_field_bytes=MAX_DATA_FIELD_BYTES + 1))

    def test_sequence_count_beyond_the_field_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_fields(fields(sequence_count=MAX_SEQUENCE_COUNT + 1))

    def test_non_boolean_secondary_header_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_fields(fields(secondary_header=1))

    def test_grouping_outside_the_two_bit_field_raises(self):
        with self.assertRaises(ValueError):
            validate_packet_fields(fields(grouping=4))


class TestLengthField(unittest.TestCase):
    def test_length_field_is_one_less_than_the_data_field(self):
        self.assertEqual(packet_length_field(64), 63)

    def test_single_byte_data_field_is_length_zero(self):
        self.assertEqual(packet_length_field(1), 0)

    def test_round_trip_through_the_length_field(self):
        self.assertEqual(data_field_bytes_from_length_field(packet_length_field(4096)), 4096)

    def test_largest_data_field_fits_the_two_byte_field(self):
        self.assertEqual(packet_length_field(MAX_DATA_FIELD_BYTES), 0xFFFF)

    def test_negative_length_field_raises(self):
        with self.assertRaises(ValueError):
            data_field_bytes_from_length_field(-1)


class TestPrimaryHeader(unittest.TestCase):
    def test_header_is_six_bytes(self):
        self.assertEqual(len(encode_primary_header(fields())), PRIMARY_HEADER_BYTES)

    def test_header_round_trips(self):
        original = validate_packet_fields(fields(type=TYPE_TELECOMMAND,
                                                 secondary_header=True,
                                                 apid=0x123,
                                                 grouping=GROUPING_FIRST,
                                                 sequence_count=9001,
                                                 data_field_bytes=512))
        self.assertEqual(decode_primary_header(encode_primary_header(original)), original)

    def test_apid_lands_in_the_first_word(self):
        header = encode_primary_header(fields(apid=0x2AB))
        self.assertEqual(((header[0] << 8) | header[1]) & MAX_APID, 0x2AB)

    def test_type_bit_separates_the_two_directions(self):
        telemetry = encode_primary_header(fields(type=TYPE_TELEMETRY))
        telecommand = encode_primary_header(fields(type=TYPE_TELECOMMAND))
        self.assertNotEqual(telemetry[0], telecommand[0])

    def test_short_header_raises(self):
        with self.assertRaises(ValueError):
            decode_primary_header([0, 0, 0, 0, 0])

    def test_header_byte_out_of_range_raises(self):
        with self.assertRaises(ValueError):
            decode_primary_header([0, 0, 0, 0, 0, 300])

    def test_non_sequence_header_raises(self):
        with self.assertRaises(ValueError):
            decode_primary_header("000000")

    def test_captured_header_of_another_version_raises(self):
        header = encode_primary_header(fields())
        header[0] |= 0b0010_0000
        with self.assertRaises(ValueError):
            decode_primary_header(header)


class TestSizing(unittest.TestCase):
    def test_packet_is_header_plus_data_field(self):
        self.assertEqual(total_packet_bytes(fields(data_field_bytes=64)),
                         PRIMARY_HEADER_BYTES + 64)

    def test_frame_adds_routing_and_the_protocol_byte(self):
        self.assertEqual(transfer_frame_bytes(fields(data_field_bytes=64), 1),
                         1 + PROTOCOL_IDENTIFIER_BYTES + PRIMARY_HEADER_BYTES + 64)

    def test_a_path_address_lengthens_the_frame(self):
        self.assertEqual(transfer_frame_bytes(fields(), 4)
                         - transfer_frame_bytes(fields(), 1), 3)

    def test_zero_routing_bytes_raises(self):
        with self.assertRaises(ValueError):
            transfer_frame_bytes(fields(), 0)


class TestGrouping(unittest.TestCase):
    def test_small_datum_stays_unsegmented(self):
        self.assertEqual(group_user_datum(100, 256), [(GROUPING_UNSEGMENTED, 100)])

    def test_datum_exactly_filling_one_packet_stays_unsegmented(self):
        self.assertEqual(group_user_datum(256, 256), [(GROUPING_UNSEGMENTED, 256)])

    def test_two_part_datum_is_first_then_last(self):
        parts = group_user_datum(300, 256)
        self.assertEqual([flag for flag, _ in parts], [GROUPING_FIRST, GROUPING_LAST])

    def test_three_part_datum_has_a_continuation(self):
        parts = group_user_datum(600, 256)
        self.assertEqual([flag for flag, _ in parts],
                         [GROUPING_FIRST, GROUPING_CONTINUATION, GROUPING_LAST])

    def test_parts_sum_back_to_the_datum(self):
        parts = group_user_datum(1000, 256)
        self.assertEqual(sum(count for _, count in parts), 1000)

    def test_no_part_exceeds_the_data_field_limit(self):
        for _, count in group_user_datum(1000, 256):
            self.assertLessEqual(count, 256)

    def test_zero_length_datum_raises(self):
        with self.assertRaises(ValueError):
            group_user_datum(0, 256)

    def test_zero_data_field_limit_raises(self):
        with self.assertRaises(ValueError):
            group_user_datum(100, 0)


class TestSequenceCount(unittest.TestCase):
    def test_counter_advances_by_one(self):
        self.assertEqual(next_sequence_count(10), 11)

    def test_counter_wraps_at_the_field_width(self):
        self.assertEqual(next_sequence_count(MAX_SEQUENCE_COUNT), 0)

    def test_counter_beyond_the_field_raises(self):
        with self.assertRaises(ValueError):
            next_sequence_count(MAX_SEQUENCE_COUNT + 1)


class TestAssessCcsdsPacket(unittest.TestCase):
    def test_plain_packet_is_acceptable(self):
        result = assess_ccsds_packet(fields())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_reported_sizes_agree_with_the_helpers(self):
        result = assess_ccsds_packet(fields(data_field_bytes=64), 4)
        self.assertEqual(result["packet_bytes"], PRIMARY_HEADER_BYTES + 64)
        self.assertEqual(result["frame_bytes"], 4 + 1 + PRIMARY_HEADER_BYTES + 64)

    def test_grouped_idle_traffic_is_flagged(self):
        result = assess_ccsds_packet(fields(apid=APID_IDLE, grouping=GROUPING_FIRST))
        self.assertTrue(any("grouped" in f for f in result["findings"]))

    def test_idle_traffic_with_a_secondary_header_is_flagged(self):
        result = assess_ccsds_packet(fields(apid=APID_IDLE, secondary_header=True))
        self.assertTrue(any("secondary header" in f for f in result["findings"]))

    def test_unsegmented_idle_traffic_is_acceptable(self):
        self.assertTrue(assess_ccsds_packet(fields(apid=APID_IDLE))["acceptable"])

    def test_frame_over_the_profile_maximum_is_flagged(self):
        result = assess_ccsds_packet(fields(data_field_bytes=4096), 1,
                                     max_frame_bytes=1024)
        self.assertTrue(any("maximum" in f for f in result["findings"]))

    def test_frame_exactly_at_the_maximum_is_acceptable(self):
        frame = transfer_frame_bytes(fields(data_field_bytes=64), 1)
        result = assess_ccsds_packet(fields(data_field_bytes=64), 1, max_frame_bytes=frame)
        self.assertTrue(result["acceptable"])

    def test_counter_that_skips_is_flagged(self):
        result = assess_ccsds_packet(fields(sequence_count=105),
                                     previous_sequence_count=100)
        self.assertTrue(any("was due" in f for f in result["findings"]))

    def test_counter_that_advances_by_one_is_acceptable(self):
        result = assess_ccsds_packet(fields(sequence_count=101),
                                     previous_sequence_count=100)
        self.assertTrue(result["acceptable"])

    def test_counter_wrap_is_accepted(self):
        result = assess_ccsds_packet(fields(sequence_count=0),
                                     previous_sequence_count=MAX_SEQUENCE_COUNT)
        self.assertTrue(result["acceptable"])

    def test_primary_header_is_reported(self):
        result = assess_ccsds_packet(fields())
        self.assertEqual(result["primary_header"], encode_primary_header(fields()))


if __name__ == "__main__":
    unittest.main()
