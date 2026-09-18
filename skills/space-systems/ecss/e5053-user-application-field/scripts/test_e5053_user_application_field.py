#!/usr/bin/env python3
"""Contract test for the user application field (offline)."""

import copy
import unittest

from e5053_user_application_field_logic import (
    DELIVER,
    DISCARD_UNREGISTERED,
    IDENTIFIER_SPACE,
    allocate_user_application_identifier,
    assess_user_application_field,
    audit_user_application_table,
    read_user_application_field,
    register_user_application,
    resolve_user_application,
    user_application_offset,
    validate_user_application_identifier,
)

TABLE = {0: "housekeeping-telemetry", 5: "telemetry-store", 9: "payload-command"}

BASE_CASE = {
    "octets": [3, 7, 40, 2, 0, 5, 8],
    "path_length": 2,
    "table": TABLE,
}


def _case(**overrides):
    case = copy.deepcopy(BASE_CASE)
    case.update(overrides)
    return case


class OffsetTests(unittest.TestCase):
    def test_pathless_unit_puts_the_field_fourth(self):
        self.assertEqual(user_application_offset(0), 3)

    def test_each_path_byte_pushes_the_field_along(self):
        self.assertEqual(user_application_offset(2), 5)
        self.assertEqual(user_application_offset(6), 9)

    def test_negative_path_length_rejected(self):
        with self.assertRaises(ValueError):
            user_application_offset(-1)

    def test_non_integer_path_length_rejected(self):
        with self.assertRaises(ValueError):
            user_application_offset(None)


class IdentifierTests(unittest.TestCase):
    def test_octet_identifiers_are_accepted(self):
        self.assertEqual(validate_user_application_identifier(0), 0)
        self.assertEqual(validate_user_application_identifier(255), 255)

    def test_identifier_wider_than_one_octet_rejected(self):
        with self.assertRaises(ValueError):
            validate_user_application_identifier(256)

    def test_negative_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_user_application_identifier(-1)

    def test_boolean_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_user_application_identifier(True)


class RegistrationTests(unittest.TestCase):
    def test_new_application_is_added_without_touching_the_original(self):
        updated = register_user_application(TABLE, 12, "attitude-log")
        self.assertEqual(updated[12], "attitude-log")
        self.assertNotIn(12, TABLE)

    def test_identifier_collision_rejected(self):
        with self.assertRaises(ValueError):
            register_user_application(TABLE, 5, "another-user")

    def test_application_registered_twice_rejected(self):
        with self.assertRaises(ValueError):
            register_user_application(TABLE, 12, "telemetry-store")

    def test_unnamed_application_rejected(self):
        with self.assertRaises(ValueError):
            register_user_application(TABLE, 12, "")

    def test_non_mapping_table_rejected(self):
        with self.assertRaises(ValueError):
            register_user_application([(5, "telemetry-store")], 12, "attitude-log")

    def test_table_with_an_out_of_range_key_rejected(self):
        with self.assertRaises(ValueError):
            register_user_application({300: "somewhere"}, 12, "attitude-log")


class AllocationTests(unittest.TestCase):
    def test_lowest_free_identifier_is_taken(self):
        self.assertEqual(allocate_user_application_identifier(TABLE), 1)

    def test_free_preference_is_honoured(self):
        self.assertEqual(allocate_user_application_identifier(TABLE, 40), 40)

    def test_held_preference_rejected(self):
        with self.assertRaises(ValueError):
            allocate_user_application_identifier(TABLE, 9)

    def test_empty_table_allocates_the_first_identifier(self):
        self.assertEqual(allocate_user_application_identifier({}), 0)

    def test_exhausted_space_rejected(self):
        full = dict((i, "user-%d" % i) for i in range(IDENTIFIER_SPACE))
        with self.assertRaises(ValueError):
            allocate_user_application_identifier(full)

    def test_out_of_range_preference_rejected(self):
        with self.assertRaises(ValueError):
            allocate_user_application_identifier(TABLE, 256)


class ResolveTests(unittest.TestCase):
    def test_registered_identifier_reaches_its_application(self):
        routed = resolve_user_application(TABLE, 9)
        self.assertEqual(routed["disposition"], DELIVER)
        self.assertEqual(routed["application"], "payload-command")
        self.assertEqual(routed["findings"], [])

    def test_identifier_zero_is_a_real_identifier(self):
        routed = resolve_user_application(TABLE, 0)
        self.assertEqual(routed["application"], "housekeeping-telemetry")

    def test_unregistered_identifier_is_dropped(self):
        routed = resolve_user_application(TABLE, 200)
        self.assertEqual(routed["disposition"], DISCARD_UNREGISTERED)
        self.assertIsNone(routed["application"])
        self.assertTrue(any("dropped" in f for f in routed["findings"]))

    def test_out_of_range_identifier_rejected(self):
        with self.assertRaises(ValueError):
            resolve_user_application(TABLE, 999)


class ReadTests(unittest.TestCase):
    def test_field_is_read_after_the_reserved_octet(self):
        self.assertEqual(read_user_application_field(BASE_CASE["octets"], 2), 5)

    def test_pathless_unit_reads_the_fourth_octet(self):
        self.assertEqual(read_user_application_field([82, 2, 0, 9, 8], 0), 9)

    def test_short_unit_rejected(self):
        with self.assertRaises(ValueError):
            read_user_application_field([82, 2, 0], 0)

    def test_non_sequence_unit_rejected(self):
        with self.assertRaises(ValueError):
            read_user_application_field(5, 0)


class AuditTests(unittest.TestCase):
    def test_audit_counts_the_registered_entries(self):
        report = audit_user_application_table(TABLE)
        self.assertEqual(report["registered"], 3)
        self.assertEqual(report["free"], IDENTIFIER_SPACE - 3)
        self.assertFalse(report["exhausted"])
        self.assertEqual(report["next_free"], 1)

    def test_empty_table_is_entirely_free(self):
        report = audit_user_application_table({})
        self.assertEqual(report["free"], IDENTIFIER_SPACE)
        self.assertAlmostEqual(report["utilisation"], 0.0, places=9)

    def test_full_table_is_exhausted(self):
        full = dict((i, "user-%d" % i) for i in range(IDENTIFIER_SPACE))
        report = audit_user_application_table(full)
        self.assertTrue(report["exhausted"])
        self.assertIsNone(report["next_free"])
        self.assertAlmostEqual(report["utilisation"], 1.0, places=9)

    def test_quarter_full_table_reports_its_share(self):
        quarter = dict((i, "user-%d" % i) for i in range(IDENTIFIER_SPACE // 4))
        report = audit_user_application_table(quarter)
        self.assertAlmostEqual(report["utilisation"], 0.25, places=9)


class AssessTests(unittest.TestCase):
    def test_registered_unit_resolves(self):
        result = assess_user_application_field(_case())
        self.assertEqual(result["verdict"], "user-application-resolved")
        self.assertEqual(result["application"], "telemetry-store")
        self.assertEqual(result["identifier_offset"], 5)

    def test_unregistered_unit_does_not_resolve(self):
        result = assess_user_application_field(
            _case(octets=[3, 7, 40, 2, 0, 200, 8])
        )
        self.assertEqual(result["verdict"], "user-application-unresolved")
        self.assertEqual(result["disposition"], DISCARD_UNREGISTERED)
        self.assertTrue(result["findings"])

    def test_wrong_declared_path_length_reads_another_field(self):
        result = assess_user_application_field(_case(path_length=0))
        self.assertEqual(result["identifier_offset"], 3)
        self.assertEqual(result["identifier"], 2)

    def test_case_without_a_table_rejected(self):
        case = _case()
        del case["table"]
        with self.assertRaises(ValueError):
            assess_user_application_field(case)

    def test_case_without_octets_rejected(self):
        case = _case()
        del case["octets"]
        with self.assertRaises(ValueError):
            assess_user_application_field(case)

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_user_application_field("telemetry-store")


if __name__ == "__main__":
    unittest.main()
