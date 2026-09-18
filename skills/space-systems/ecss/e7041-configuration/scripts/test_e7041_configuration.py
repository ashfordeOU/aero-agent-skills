"""Contract tests for the clause 6.13.3.1 downlink configuration logic."""

import unittest

from e7041_configuration_logic import (
    MIN_PARTS_FOR_TRANSFER,
    assess_downlink_configuration,
    largest_supported_message_octets,
    last_part_fill_ratio,
    last_part_octets,
    max_numbered_parts,
    part_count,
    usable_part_octets,
    validate_transaction_identifiers,
)


class UsablePayloadTests(unittest.TestCase):
    def test_overhead_is_subtracted_from_the_packet_limit(self):
        self.assertEqual(usable_part_octets(1024, 24), 1000)

    def test_zero_overhead_leaves_the_whole_packet(self):
        self.assertEqual(usable_part_octets(1024, 0), 1024)

    def test_overhead_equal_to_the_limit_is_refused(self):
        with self.assertRaises(ValueError):
            usable_part_octets(64, 64)

    def test_overhead_above_the_limit_is_refused(self):
        with self.assertRaises(ValueError):
            usable_part_octets(64, 96)

    def test_non_integer_packet_limit_is_refused(self):
        with self.assertRaises(ValueError):
            usable_part_octets(1024.0, 24)

    def test_boolean_overhead_is_refused(self):
        with self.assertRaises(ValueError):
            usable_part_octets(1024, True)

    def test_negative_overhead_is_refused(self):
        with self.assertRaises(ValueError):
            usable_part_octets(1024, -8)


class SequenceFieldTests(unittest.TestCase):
    def test_eight_bit_field_numbers_two_hundred_fifty_five_parts(self):
        self.assertEqual(max_numbered_parts(8), 255)

    def test_sixteen_bit_field_numbers_sixty_five_thousand_parts(self):
        self.assertEqual(max_numbered_parts(16), 65535)

    def test_zero_width_field_is_refused(self):
        with self.assertRaises(ValueError):
            max_numbered_parts(0)

    def test_field_wider_than_the_model_limit_is_refused(self):
        with self.assertRaises(ValueError):
            max_numbered_parts(64)


class PartCountTests(unittest.TestCase):
    def test_exact_multiple_uses_whole_parts(self):
        self.assertEqual(part_count(4000, 1000), 4)

    def test_one_octet_past_a_boundary_costs_a_whole_part(self):
        self.assertEqual(part_count(4001, 1000), 5)

    def test_message_smaller_than_a_part_needs_one_part(self):
        self.assertEqual(part_count(300, 1000), 1)

    def test_zero_length_message_is_refused(self):
        with self.assertRaises(ValueError):
            part_count(0, 1000)

    def test_last_part_of_an_exact_multiple_is_full(self):
        self.assertEqual(last_part_octets(4000, 1000), 1000)

    def test_last_part_carries_only_the_remainder(self):
        self.assertEqual(last_part_octets(4001, 1000), 1)

    def test_last_part_fill_ratio_reports_occupancy(self):
        self.assertAlmostEqual(last_part_fill_ratio(4500, 1000), 0.5, places=9)

    def test_full_last_part_reports_unit_occupancy(self):
        self.assertAlmostEqual(last_part_fill_ratio(4000, 1000), 1.0, places=9)

    def test_supported_message_is_parts_times_part_size(self):
        self.assertEqual(largest_supported_message_octets(1000, 255), 255000)


class IdentifierPoolTests(unittest.TestCase):
    def test_pool_is_returned_sorted(self):
        self.assertEqual(validate_transaction_identifiers([7, 1, 4], 8), (1, 4, 7))

    def test_duplicate_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            validate_transaction_identifiers([1, 4, 1], 8)

    def test_identifier_outside_the_field_is_refused(self):
        with self.assertRaises(ValueError):
            validate_transaction_identifiers([1, 300], 8)

    def test_negative_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            validate_transaction_identifiers([-1, 4], 8)

    def test_empty_pool_is_refused(self):
        with self.assertRaises(ValueError):
            validate_transaction_identifiers([], 8)

    def test_non_integer_identifier_is_refused(self):
        with self.assertRaises(ValueError):
            validate_transaction_identifiers(["4"], 8)


class AssessmentTests(unittest.TestCase):
    def _spec(self, **overrides):
        spec = {
            "max_packet_octets": 1024,
            "part_report_overhead_octets": 24,
            "configured_part_octets": 1000,
            "largest_message_octets": 120000,
            "part_number_bits": 8,
            "identifier_bits": 8,
            "transaction_identifiers": [1, 2, 3, 4],
            "concurrent_transactions": 3,
        }
        spec.update(overrides)
        return spec

    def test_nominal_configuration_is_compliant(self):
        result = assess_downlink_configuration(self._spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_nominal_configuration_reports_the_part_count(self):
        result = assess_downlink_configuration(self._spec())
        self.assertEqual(result["parts_needed"], 120)
        self.assertEqual(result["effective_part_octets"], 1000)

    def test_part_size_above_the_usable_payload_is_clamped_and_flagged(self):
        result = assess_downlink_configuration(self._spec(configured_part_octets=1024))
        self.assertEqual(result["effective_part_octets"], 1000)
        self.assertFalse(result["compliant"])
        self.assertIn("exceeds", result["findings"][0])

    def test_message_needing_more_parts_than_the_field_is_flagged(self):
        result = assess_downlink_configuration(self._spec(largest_message_octets=400000))
        self.assertFalse(result["compliant"])
        self.assertTrue(any("numbers at most" in f for f in result["findings"]))

    def test_single_part_message_is_flagged_as_not_needing_the_service(self):
        result = assess_downlink_configuration(self._spec(largest_message_octets=800))
        self.assertEqual(result["parts_needed"], 1)
        self.assertLess(result["parts_needed"], MIN_PARTS_FOR_TRANSFER)
        self.assertTrue(any("does not need" in f for f in result["findings"]))

    def test_identifier_pool_smaller_than_the_concurrency_is_flagged(self):
        result = assess_downlink_configuration(
            self._spec(transaction_identifiers=[1, 2], concurrent_transactions=4)
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(any("concurrent transactions" in f for f in result["findings"]))

    def test_supported_ceiling_follows_the_effective_part_size(self):
        result = assess_downlink_configuration(self._spec(configured_part_octets=1024))
        self.assertEqual(result["largest_supported_message_octets"], 255000)

    def test_last_part_occupancy_is_reported(self):
        result = assess_downlink_configuration(self._spec(largest_message_octets=119500))
        self.assertEqual(result["last_part_octets"], 500)
        self.assertAlmostEqual(result["last_part_fill_ratio"], 0.5, places=9)

    def test_missing_key_is_refused(self):
        spec = self._spec()
        del spec["part_number_bits"]
        with self.assertRaises(ValueError):
            assess_downlink_configuration(spec)

    def test_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_downlink_configuration(["max_packet_octets"])

    def test_zero_concurrency_is_refused(self):
        with self.assertRaises(ValueError):
            assess_downlink_configuration(self._spec(concurrent_transactions=0))


if __name__ == "__main__":
    unittest.main()
