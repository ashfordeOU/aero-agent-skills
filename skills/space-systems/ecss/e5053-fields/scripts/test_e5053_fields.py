#!/usr/bin/env python3
"""Contract test for the unit field set and its order (offline)."""

import copy
import unittest

from e5053_fields_logic import (
    FIELD_ORDER,
    MINIMUM_PACKET_OCTETS,
    ORDER_BAD,
    ORDER_OK,
    PACKET,
    PROTOCOL_IDENTIFIER,
    RESERVED,
    SINGLE_OCTET_FIELDS,
    TARGET_LOGICAL_ADDRESS,
    UNIT_OK,
    UNIT_SHORT,
    USER_APPLICATION,
    assess_fields,
    audit_field_sequence,
    decode_unit,
    encode_unit,
    field_offsets,
    minimum_unit_octets,
)

SMALLEST_PACKET = [2, 171, 192, 17, 0, 0, 9]
PACKET_OCTETS = [2, 171, 192, 17, 0, 3, 1, 2, 3, 4]

PARTS = {
    "path_addresses": [3, 7],
    "target_logical_address": 40,
    "protocol_identifier": 2,
    "reserved": 0,
    "user_application": 5,
    "packet": PACKET_OCTETS,
}

UNIT = list(encode_unit(PARTS))


def _parts(**overrides):
    parts = copy.deepcopy(PARTS)
    parts.update(overrides)
    return parts


class OrderTests(unittest.TestCase):
    def test_the_unit_has_five_named_fields(self):
        self.assertEqual(len(FIELD_ORDER), 5)

    def test_the_packet_is_the_last_field(self):
        self.assertEqual(FIELD_ORDER[-1], PACKET)

    def test_every_field_before_the_packet_is_one_octet(self):
        self.assertEqual(len(SINGLE_OCTET_FIELDS), 4)
        self.assertNotIn(PACKET, SINGLE_OCTET_FIELDS)

    def test_the_address_comes_before_the_identifier(self):
        self.assertLess(
            FIELD_ORDER.index(TARGET_LOGICAL_ADDRESS),
            FIELD_ORDER.index(PROTOCOL_IDENTIFIER),
        )

    def test_the_reserved_octet_sits_before_the_user_application(self):
        self.assertLess(
            FIELD_ORDER.index(RESERVED), FIELD_ORDER.index(USER_APPLICATION)
        )


class OffsetTests(unittest.TestCase):
    def test_pathless_unit_starts_at_octet_zero(self):
        offsets = field_offsets(0)
        self.assertEqual(offsets[TARGET_LOGICAL_ADDRESS], 0)
        self.assertEqual(offsets[PACKET], 4)

    def test_path_bytes_shift_every_field(self):
        offsets = field_offsets(3)
        self.assertEqual(offsets[TARGET_LOGICAL_ADDRESS], 3)
        self.assertEqual(offsets[USER_APPLICATION], 6)
        self.assertEqual(offsets[PACKET], 7)

    def test_offsets_are_consecutive(self):
        offsets = field_offsets(2)
        values = [offsets[name] for name in FIELD_ORDER]
        self.assertEqual(values, list(range(2, 7)))

    def test_minimum_unit_covers_every_field_and_a_smallest_packet(self):
        self.assertEqual(minimum_unit_octets(0), 4 + MINIMUM_PACKET_OCTETS)
        self.assertEqual(minimum_unit_octets(2), 6 + MINIMUM_PACKET_OCTETS)

    def test_negative_path_length_rejected(self):
        with self.assertRaises(ValueError):
            field_offsets(-1)

    def test_non_integer_path_length_rejected(self):
        with self.assertRaises(ValueError):
            minimum_unit_octets(True)


class AuditTests(unittest.TestCase):
    def test_required_order_is_conformant(self):
        audit = audit_field_sequence(FIELD_ORDER)
        self.assertEqual(audit["verdict"], ORDER_OK)
        self.assertTrue(audit["conformant"])
        self.assertEqual(audit["findings"], [])

    def test_swapped_fields_are_reported_as_misordered(self):
        audit = audit_field_sequence(
            [PROTOCOL_IDENTIFIER, TARGET_LOGICAL_ADDRESS, RESERVED,
             USER_APPLICATION, PACKET]
        )
        self.assertTrue(audit["misordered"])
        self.assertEqual(audit["verdict"], ORDER_BAD)

    def test_a_dropped_field_is_reported_as_missing(self):
        audit = audit_field_sequence(
            [TARGET_LOGICAL_ADDRESS, PROTOCOL_IDENTIFIER, USER_APPLICATION, PACKET]
        )
        self.assertEqual(audit["missing"], (RESERVED,))
        self.assertTrue(any("shift" in f for f in audit["findings"]))

    def test_an_invented_field_is_reported_as_unexpected(self):
        audit = audit_field_sequence(list(FIELD_ORDER) + ["checksum"])
        self.assertEqual(audit["unexpected"], ("checksum",))
        self.assertTrue(any("not a field" in f for f in audit["findings"]))

    def test_a_repeated_field_rejected(self):
        with self.assertRaises(ValueError):
            audit_field_sequence(list(FIELD_ORDER) + [RESERVED])

    def test_a_non_sequence_declaration_rejected(self):
        with self.assertRaises(ValueError):
            audit_field_sequence(7)

    def test_an_unnamed_field_rejected(self):
        with self.assertRaises(ValueError):
            audit_field_sequence([TARGET_LOGICAL_ADDRESS, ""])


class EncodeTests(unittest.TestCase):
    def test_encoded_unit_puts_the_path_first(self):
        self.assertEqual(UNIT[:2], [3, 7])

    def test_encoded_unit_follows_the_field_order(self):
        self.assertEqual(UNIT[2:6], [40, 2, 0, 5])

    def test_encoded_unit_ends_with_the_packet(self):
        self.assertEqual(UNIT[6:], PACKET_OCTETS)

    def test_pathless_unit_is_four_octets_shorter_than_its_packet_start(self):
        unit = encode_unit(_parts(path_addresses=[]))
        self.assertEqual(len(unit), 4 + len(PACKET_OCTETS))

    def test_missing_single_octet_field_rejected(self):
        parts = _parts()
        del parts["reserved"]
        with self.assertRaises(ValueError):
            encode_unit(parts)

    def test_missing_packet_rejected(self):
        parts = _parts()
        del parts["packet"]
        with self.assertRaises(ValueError):
            encode_unit(parts)

    def test_packet_shorter_than_a_primary_header_rejected(self):
        with self.assertRaises(ValueError):
            encode_unit(_parts(packet=[2, 171, 192]))

    def test_path_byte_holding_a_logical_address_rejected(self):
        with self.assertRaises(ValueError):
            encode_unit(_parts(path_addresses=[3, 90]))

    def test_field_octet_out_of_range_rejected(self):
        with self.assertRaises(ValueError):
            encode_unit(_parts(user_application=300))

    def test_non_mapping_parts_rejected(self):
        with self.assertRaises(ValueError):
            encode_unit([40, 2, 0, 5])


class DecodeTests(unittest.TestCase):
    def test_decode_recovers_every_field(self):
        decoded = decode_unit(UNIT, 2)
        self.assertEqual(decoded["path_addresses"], (3, 7))
        self.assertEqual(decoded["target_logical_address"], 40)
        self.assertEqual(decoded["protocol_identifier"], 2)
        self.assertEqual(decoded["reserved"], 0)
        self.assertEqual(decoded["user_application"], 5)
        self.assertEqual(list(decoded["packet"]), PACKET_OCTETS)

    def test_decode_round_trips_an_encode(self):
        parts = _parts(path_addresses=[], packet=SMALLEST_PACKET)
        decoded = decode_unit(encode_unit(parts), 0)
        self.assertEqual(list(decoded["packet"]), SMALLEST_PACKET)
        self.assertEqual(decoded["path_addresses"], ())

    def test_unit_too_short_for_every_field_rejected(self):
        with self.assertRaises(ValueError):
            decode_unit(UNIT[:8], 2)

    def test_declared_path_holding_a_logical_address_rejected(self):
        bad = list(UNIT)
        bad[1] = 90
        with self.assertRaises(ValueError):
            decode_unit(bad, 2)

    def test_octet_out_of_range_rejected(self):
        bad = list(UNIT)
        bad[-1] = 999
        with self.assertRaises(ValueError):
            decode_unit(bad, 2)

    def test_non_sequence_unit_rejected(self):
        with self.assertRaises(ValueError):
            decode_unit(40, 0)


class AssessTests(unittest.TestCase):
    def test_conformant_unit_is_well_formed(self):
        result = assess_fields({"octets": UNIT, "path_length": 2})
        self.assertEqual(result["verdict"], UNIT_OK)
        self.assertTrue(result["well_formed"])
        self.assertEqual(result["order_verdict"], ORDER_OK)
        self.assertEqual(result["fields"]["target_logical_address"], 40)

    def test_short_unit_is_reported_and_not_decoded(self):
        result = assess_fields({"octets": UNIT[:7], "path_length": 2})
        self.assertEqual(result["verdict"], UNIT_SHORT)
        self.assertFalse(result["well_formed"])
        self.assertIsNone(result["fields"])
        self.assertTrue(result["findings"])

    def test_declared_order_defect_is_carried_through(self):
        result = assess_fields(
            {
                "octets": UNIT,
                "path_length": 2,
                "declared_fields": [
                    PROTOCOL_IDENTIFIER, TARGET_LOGICAL_ADDRESS, RESERVED,
                    USER_APPLICATION, PACKET,
                ],
            }
        )
        self.assertEqual(result["verdict"], ORDER_BAD)
        self.assertFalse(result["well_formed"])
        self.assertIsNotNone(result["fields"])

    def test_assess_reports_the_minimum_unit_size(self):
        result = assess_fields({"octets": UNIT, "path_length": 2})
        self.assertEqual(result["minimum_octets"], minimum_unit_octets(2))

    def test_case_without_octets_rejected(self):
        with self.assertRaises(ValueError):
            assess_fields({"path_length": 2})

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_fields(UNIT)


if __name__ == "__main__":
    unittest.main()
