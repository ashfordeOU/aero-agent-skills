"""Contract tests for the clause 5.3.1 target SpaceWire address field."""

import unittest

from e5053_target_spacewire_address_field_logic import (
    LOGICAL_ADDRESS_MAX,
    LOGICAL_ADDRESS_MIN,
    NULL_BYTE,
    PAD_ALIGNMENT,
    PATH_ADDRESS_MAX,
    PATH_ADDRESS_MIN,
    RESERVED_BYTE,
    alignment_remainder,
    assess_target_address_field,
    build_address_field,
    categorize_byte,
    consume_hop,
    field_length,
    is_aligned,
    is_direct,
    parse_address_field,
    route_packet,
    strip_leading_padding,
    validate_field,
    validate_logical_address,
    validate_path,
)

ROUTE = [3, 7, 2]
LOGICAL = 40


class CategorizeTests(unittest.TestCase):
    def test_zero_is_padding(self):
        self.assertEqual(categorize_byte(NULL_BYTE), "null")

    def test_low_value_is_a_path_address(self):
        self.assertEqual(categorize_byte(PATH_ADDRESS_MIN), "path")
        self.assertEqual(categorize_byte(PATH_ADDRESS_MAX), "path")

    def test_mid_value_is_a_logical_address(self):
        self.assertEqual(categorize_byte(LOGICAL_ADDRESS_MIN), "logical")
        self.assertEqual(categorize_byte(LOGICAL_ADDRESS_MAX), "logical")

    def test_top_value_is_reserved(self):
        self.assertEqual(categorize_byte(RESERVED_BYTE), "reserved")

    def test_value_above_the_byte_range_rejected(self):
        with self.assertRaises(ValueError):
            categorize_byte(256)

    def test_negative_value_rejected(self):
        with self.assertRaises(ValueError):
            categorize_byte(-1)

    def test_boolean_rejected(self):
        with self.assertRaises(ValueError):
            categorize_byte(True)

    def test_non_integer_rejected(self):
        with self.assertRaises(ValueError):
            categorize_byte(3.0)


class FieldValidationTests(unittest.TestCase):
    def test_list_of_bytes_passes_through(self):
        self.assertEqual(validate_field([1, 2, 3]), [1, 2, 3])

    def test_bytes_object_is_accepted(self):
        self.assertEqual(validate_field(bytes([1, 2])), [1, 2])

    def test_text_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_field("0102")

    def test_out_of_range_byte_rejected(self):
        with self.assertRaises(ValueError):
            validate_field([1, 300])

    def test_length_counts_the_padding(self):
        self.assertEqual(field_length([0, 0, 3, 40]), 4)


class RouteValidationTests(unittest.TestCase):
    def test_valid_ports_pass(self):
        self.assertEqual(validate_path(ROUTE), ROUTE)

    def test_none_route_is_empty(self):
        self.assertEqual(validate_path(None), [])

    def test_port_above_the_path_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_path([PATH_ADDRESS_MAX + 1])

    def test_zero_port_rejected(self):
        with self.assertRaises(ValueError):
            validate_path([0])

    def test_logical_address_in_range_accepted(self):
        self.assertEqual(validate_logical_address(LOGICAL), LOGICAL)

    def test_logical_address_below_the_range_rejected(self):
        with self.assertRaises(ValueError):
            validate_logical_address(LOGICAL_ADDRESS_MIN - 1)

    def test_reserved_logical_address_rejected(self):
        with self.assertRaises(ValueError):
            validate_logical_address(RESERVED_BYTE)

    def test_absent_logical_address_is_none(self):
        self.assertIsNone(validate_logical_address(None))


class BuildTests(unittest.TestCase):
    def test_path_only_field(self):
        self.assertEqual(build_address_field(ROUTE), ROUTE)

    def test_logical_address_terminates_the_field(self):
        self.assertEqual(build_address_field(ROUTE, LOGICAL), ROUTE + [LOGICAL])

    def test_padding_leads_the_field(self):
        field = build_address_field([3, 7], LOGICAL, align_to=PAD_ALIGNMENT)
        self.assertEqual(field[0], NULL_BYTE)
        self.assertEqual(len(field), PAD_ALIGNMENT)

    def test_already_aligned_field_is_not_padded(self):
        field = build_address_field(ROUTE, LOGICAL, align_to=PAD_ALIGNMENT)
        self.assertEqual(field, ROUTE + [LOGICAL])

    def test_directly_attached_target_has_an_empty_field(self):
        self.assertEqual(build_address_field([], None), [])

    def test_alignment_below_one_rejected(self):
        with self.assertRaises(ValueError):
            build_address_field(ROUTE, LOGICAL, align_to=0)

    def test_bad_port_rejected_at_build_time(self):
        with self.assertRaises(ValueError):
            build_address_field([RESERVED_BYTE], LOGICAL)


class ParseTests(unittest.TestCase):
    def test_padding_path_and_logical_address_are_separated(self):
        parsed = parse_address_field([0, 0, 3, 7, 2, LOGICAL])
        self.assertEqual(parsed["padding"], 2)
        self.assertEqual(parsed["path"], ROUTE)
        self.assertEqual(parsed["logical_address"], LOGICAL)

    def test_empty_field_parses_to_nothing(self):
        parsed = parse_address_field([])
        self.assertEqual(parsed["path"], [])
        self.assertIsNone(parsed["logical_address"])

    def test_interior_null_rejected(self):
        with self.assertRaises(ValueError):
            parse_address_field([3, 0, 7])

    def test_reserved_byte_rejected(self):
        with self.assertRaises(ValueError):
            parse_address_field([3, RESERVED_BYTE])

    def test_path_byte_after_the_logical_address_rejected(self):
        with self.assertRaises(ValueError):
            parse_address_field([3, LOGICAL, 7])

    def test_second_logical_address_rejected(self):
        with self.assertRaises(ValueError):
            parse_address_field([LOGICAL, LOGICAL])

    def test_strip_leading_padding_removes_only_the_leading_run(self):
        self.assertEqual(strip_leading_padding([0, 0, 3, 7]), [3, 7])

    def test_strip_leading_padding_on_an_unpadded_field_is_identity(self):
        self.assertEqual(strip_leading_padding(ROUTE), ROUTE)


class AlignmentTests(unittest.TestCase):
    def test_four_byte_field_is_aligned(self):
        self.assertTrue(is_aligned([0, 3, 7, LOGICAL]))

    def test_three_byte_field_is_not_aligned(self):
        self.assertFalse(is_aligned([3, 7, LOGICAL]))

    def test_remainder_is_reported(self):
        self.assertEqual(alignment_remainder([3, 7, LOGICAL]), 3)

    def test_empty_field_is_aligned(self):
        self.assertTrue(is_aligned([]))

    def test_alignment_below_one_rejected(self):
        with self.assertRaises(ValueError):
            alignment_remainder([3], 0)


class DirectnessTests(unittest.TestCase):
    def test_empty_field_is_direct(self):
        self.assertTrue(is_direct([]))

    def test_logical_address_alone_is_direct(self):
        self.assertTrue(is_direct([LOGICAL]))

    def test_path_bytes_make_the_field_indirect(self):
        self.assertFalse(is_direct(ROUTE))


class HopTests(unittest.TestCase):
    def test_hop_takes_the_leading_port(self):
        port, remaining = consume_hop([3, 7, LOGICAL])
        self.assertEqual(port, 3)
        self.assertEqual(remaining, [7, LOGICAL])

    def test_hop_discards_the_leading_padding_first(self):
        port, remaining = consume_hop([0, 0, 3, 7])
        self.assertEqual(port, 3)
        self.assertEqual(remaining, [7])

    def test_hop_on_an_exhausted_field_rejected(self):
        with self.assertRaises(ValueError):
            consume_hop([])

    def test_hop_on_a_logical_address_rejected(self):
        with self.assertRaises(ValueError):
            consume_hop([LOGICAL])

    def test_hop_on_a_reserved_byte_rejected(self):
        with self.assertRaises(ValueError):
            consume_hop([RESERVED_BYTE])

    def test_route_consumes_every_path_byte(self):
        walk = route_packet([0, 3, 7, 2, LOGICAL])
        self.assertEqual(walk["ports"], ROUTE)
        self.assertEqual(walk["remaining"], [LOGICAL])
        self.assertEqual(walk["hops"], 3)

    def test_partial_route_leaves_the_residue(self):
        walk = route_packet([3, 7, 2, LOGICAL], 1)
        self.assertEqual(walk["ports"], [3])
        self.assertEqual(walk["residue"]["path"], [7, 2])

    def test_route_beyond_the_field_rejected(self):
        with self.assertRaises(ValueError):
            route_packet(ROUTE, 4)

    def test_negative_hop_count_rejected(self):
        with self.assertRaises(ValueError):
            route_packet(ROUTE, -1)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "field": build_address_field(ROUTE, LOGICAL, align_to=PAD_ALIGNMENT),
            "require_alignment": True,
            "expected_hops": 3,
            "target_directly_attached": False,
            "require_logical_address": True,
        }
        spec.update(overrides)
        return spec

    def test_well_formed_field_is_compliant(self):
        result = assess_target_address_field(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_misaligned_field_is_flagged_when_alignment_is_required(self):
        result = assess_target_address_field(
            self._spec(field=[3, 7, LOGICAL], expected_hops=2)
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("alignment" in f for f in result["findings"]))

    def test_misaligned_field_passes_when_alignment_is_not_required(self):
        result = assess_target_address_field(
            self._spec(field=[3, 7, LOGICAL], expected_hops=2, require_alignment=False)
        )
        self.assertTrue(result["compliant"])

    def test_empty_field_for_a_remote_target_is_flagged(self):
        result = assess_target_address_field(
            self._spec(field=[], expected_hops=0, require_logical_address=False)
        )
        self.assertTrue(any("not directly attached" in f for f in result["findings"]))

    def test_path_bytes_for_an_attached_target_are_flagged(self):
        result = assess_target_address_field(self._spec(target_directly_attached=True))
        self.assertTrue(any("directly attached target" in f for f in result["findings"]))

    def test_hop_count_mismatch_is_flagged(self):
        result = assess_target_address_field(self._spec(expected_hops=2))
        self.assertTrue(any("routes 3 hop" in f for f in result["findings"]))

    def test_missing_logical_address_is_flagged(self):
        result = assess_target_address_field(
            self._spec(field=[0, 3, 7, 2], expected_hops=3)
        )
        self.assertTrue(any("logical target address" in f for f in result["findings"]))

    def test_route_walk_is_reported(self):
        result = assess_target_address_field(self._spec())
        self.assertEqual(result["route"]["ports"], ROUTE)
        self.assertEqual(result["route"]["remaining"], [LOGICAL])

    def test_alignment_remainder_is_reported(self):
        result = assess_target_address_field(
            self._spec(field=[3, 7, LOGICAL], expected_hops=2, require_alignment=False)
        )
        self.assertEqual(result["alignment_remainder"], 3)

    def test_missing_field_key_rejected(self):
        with self.assertRaises(ValueError):
            assess_target_address_field({"expected_hops": 1})

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_target_address_field([3, 7])

    def test_non_boolean_attachment_flag_rejected(self):
        with self.assertRaises(ValueError):
            assess_target_address_field(self._spec(target_directly_attached="no"))

    def test_negative_expected_hops_rejected(self):
        with self.assertRaises(ValueError):
            assess_target_address_field(self._spec(expected_hops=-2))

    def test_reserved_byte_in_the_field_rejected(self):
        with self.assertRaises(ValueError):
            assess_target_address_field(self._spec(field=[3, RESERVED_BYTE]))


if __name__ == "__main__":
    unittest.main()
