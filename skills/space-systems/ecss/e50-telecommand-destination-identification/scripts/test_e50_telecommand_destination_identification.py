"""Contract tests for the clause 5.4.10 destination-identification logic."""

import unittest

from e50_telecommand_destination_identification_logic import (
    BROADCAST_ID,
    address_space_size,
    assess_destination_identification,
    correctable_bit_errors,
    detectable_bit_errors,
    evaluate_command_destination,
    hamming_distance,
    minimum_separation,
    validate_identifier_set,
)

FIELD_BITS = 10
ASSIGNED = [0b0000000000, 0b0000001111, 0b1111110000]
APPLICATIONS = [1, 4, 17]


def base_spec(**overrides):
    spec = {
        "field_bits": FIELD_BITS,
        "assigned_ids": ASSIGNED,
        "applications": APPLICATIONS,
        "commands": [
            {"name": "TC_MODE_SET", "spacecraft_id": 0b0000001111, "application_id": 4},
            {"name": "TC_TIME_SYNC", "spacecraft_id": BROADCAST_ID, "application_id": 1,
             "broadcast_safe": True},
        ],
        "required_separation": 3,
    }
    spec.update(overrides)
    return spec


class AddressSpaceTests(unittest.TestCase):
    def test_ten_bits_carry_a_thousand_and_twenty_four_addresses(self):
        self.assertEqual(address_space_size(10), 1024)

    def test_one_bit_carries_two_addresses(self):
        self.assertEqual(address_space_size(1), 2)

    def test_zero_width_field_rejected(self):
        with self.assertRaises(ValueError):
            address_space_size(0)

    def test_absurd_width_rejected(self):
        with self.assertRaises(ValueError):
            address_space_size(200)

    def test_non_integer_width_rejected(self):
        with self.assertRaises(ValueError):
            address_space_size(10.0)


class HammingTests(unittest.TestCase):
    def test_identical_identifiers_are_zero_apart(self):
        self.assertEqual(hamming_distance(0b1010, 0b1010), 0)

    def test_single_bit_flip_is_distance_one(self):
        self.assertEqual(hamming_distance(0b1010, 0b1011), 1)

    def test_distance_counts_every_differing_bit(self):
        self.assertEqual(hamming_distance(0b0000001111, 0b1111110000), 10)

    def test_negative_identifier_rejected(self):
        with self.assertRaises(ValueError):
            hamming_distance(-1, 4)

    def test_boolean_identifier_rejected(self):
        with self.assertRaises(ValueError):
            hamming_distance(True, 4)


class SeparationTests(unittest.TestCase):
    def test_minimum_separation_is_the_closest_pair(self):
        self.assertEqual(minimum_separation(ASSIGNED), 4)

    def test_adjacent_numbering_separates_by_one_bit(self):
        self.assertEqual(minimum_separation([4, 5, 6]), 1)

    def test_repeated_identifier_rejected(self):
        with self.assertRaises(ValueError):
            minimum_separation([4, 9, 4])

    def test_single_identifier_cannot_be_separated(self):
        with self.assertRaises(ValueError):
            minimum_separation([4])

    def test_separation_of_four_detects_three_and_corrects_one(self):
        self.assertEqual(detectable_bit_errors(4), 3)
        self.assertEqual(correctable_bit_errors(4), 1)

    def test_separation_of_one_detects_and_corrects_nothing(self):
        self.assertEqual(detectable_bit_errors(1), 0)
        self.assertEqual(correctable_bit_errors(1), 0)

    def test_zero_separation_rejected(self):
        with self.assertRaises(ValueError):
            detectable_bit_errors(0)


class IdentifierSetTests(unittest.TestCase):
    def test_assignment_reports_capacity_and_occupancy(self):
        assignment = validate_identifier_set(FIELD_BITS, ASSIGNED)
        self.assertEqual(assignment["capacity"], 1024)
        self.assertEqual(assignment["assigned"], 3)
        self.assertAlmostEqual(assignment["occupancy"], 3.0 / 1024.0)

    def test_assignment_carries_the_separation_and_its_consequences(self):
        assignment = validate_identifier_set(FIELD_BITS, ASSIGNED)
        self.assertEqual(assignment["separation"], 4)
        self.assertEqual(assignment["detectable_bit_errors"], 3)

    def test_identifier_wider_than_the_field_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier_set(4, [1, 2, 64])

    def test_single_identifier_set_takes_the_field_width_as_separation(self):
        assignment = validate_identifier_set(8, [7])
        self.assertEqual(assignment["separation"], 8)

    def test_empty_assignment_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier_set(8, [])


class CommandDestinationTests(unittest.TestCase):
    def setUp(self):
        self.assignment = validate_identifier_set(FIELD_BITS, ASSIGNED)
        self.applications = set(APPLICATIONS)

    def test_fully_addressed_command_is_unambiguous(self):
        record = evaluate_command_destination(
            {"name": "TC_A", "spacecraft_id": 0b0000001111, "application_id": 4},
            self.assignment,
            self.applications,
        )
        self.assertTrue(record["unambiguous"])

    def test_unset_spacecraft_is_a_problem(self):
        record = evaluate_command_destination(
            {"name": "TC_A", "spacecraft_id": None, "application_id": 4},
            self.assignment,
            self.applications,
        )
        self.assertFalse(record["unambiguous"])
        self.assertIn("unset", record["problems"][0])

    def test_unset_application_is_a_problem(self):
        record = evaluate_command_destination(
            {"name": "TC_A", "spacecraft_id": 0, "application_id": None},
            self.assignment,
            self.applications,
        )
        self.assertFalse(record["unambiguous"])

    def test_broadcast_without_the_flag_is_a_problem(self):
        record = evaluate_command_destination(
            {"name": "TC_A", "spacecraft_id": BROADCAST_ID, "application_id": 1},
            self.assignment,
            self.applications,
        )
        self.assertFalse(record["unambiguous"])

    def test_broadcast_with_the_flag_is_accepted(self):
        record = evaluate_command_destination(
            {"name": "TC_A", "spacecraft_id": BROADCAST_ID, "application_id": 1,
             "broadcast_safe": True},
            self.assignment,
            self.applications,
        )
        self.assertTrue(record["unambiguous"])

    def test_unassigned_spacecraft_identifier_is_a_problem(self):
        record = evaluate_command_destination(
            {"name": "TC_A", "spacecraft_id": 5, "application_id": 4},
            self.assignment,
            self.applications,
        )
        self.assertFalse(record["unambiguous"])

    def test_undeclared_application_is_a_problem(self):
        record = evaluate_command_destination(
            {"name": "TC_A", "spacecraft_id": 0, "application_id": 99},
            self.assignment,
            self.applications,
        )
        self.assertFalse(record["unambiguous"])

    def test_non_boolean_broadcast_flag_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_command_destination(
                {"name": "TC_A", "spacecraft_id": 0, "application_id": 4, "broadcast_safe": 1},
                self.assignment,
                self.applications,
            )

    def test_command_missing_a_field_rejected(self):
        with self.assertRaises(ValueError):
            evaluate_command_destination(
                {"name": "TC_A", "spacecraft_id": 0}, self.assignment, self.applications
            )


class AssessmentTests(unittest.TestCase):
    def test_well_addressed_dictionary_is_compliant(self):
        result = assess_destination_identification(base_spec())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])

    def test_adjacent_numbering_fails_the_separation_requirement(self):
        result = assess_destination_identification(
            base_spec(
                assigned_ids=[4, 5, 6],
                commands=[{"name": "TC_A", "spacecraft_id": 4, "application_id": 4}],
            )
        )
        self.assertFalse(result["separation_met"])
        self.assertFalse(result["compliant"])

    def test_ambiguous_commands_are_named(self):
        result = assess_destination_identification(
            base_spec(
                commands=[{"name": "TC_LOOSE", "spacecraft_id": None, "application_id": 4}]
            )
        )
        self.assertEqual(result["ambiguous_commands"], ["TC_LOOSE"])

    def test_findings_name_the_command(self):
        result = assess_destination_identification(
            base_spec(
                commands=[{"name": "TC_LOOSE", "spacecraft_id": None, "application_id": 4}]
            )
        )
        self.assertIn("TC_LOOSE", result["findings"][0])

    def test_duplicate_command_name_rejected(self):
        command = {"name": "TC_A", "spacecraft_id": 0, "application_id": 4}
        with self.assertRaises(ValueError):
            assess_destination_identification(base_spec(commands=[command, dict(command)]))

    def test_duplicate_application_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_destination_identification(base_spec(applications=[1, 1, 4]))

    def test_empty_command_set_rejected(self):
        with self.assertRaises(ValueError):
            assess_destination_identification(base_spec(commands=[]))

    def test_zero_required_separation_rejected(self):
        with self.assertRaises(ValueError):
            assess_destination_identification(base_spec(required_separation=0))

    def test_missing_spec_key_rejected(self):
        spec = base_spec()
        del spec["applications"]
        with self.assertRaises(ValueError):
            assess_destination_identification(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_destination_identification(["field_bits"])


if __name__ == "__main__":
    unittest.main()
