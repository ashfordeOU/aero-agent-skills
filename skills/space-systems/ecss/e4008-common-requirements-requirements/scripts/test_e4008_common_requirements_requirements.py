"""Contract tests for the clause 5.1.2 common-requirements grading logic."""

import unittest

from e4008_common_requirements_requirements_logic import (
    IDENTIFIER_MAX_LENGTH,
    NORMATIVE_ITEMS,
    NORMATIVE_ITEM_COUNT,
    assess_configuration,
    assess_element,
    build_catalogue_index,
    compliance_ratio,
    resolve_reference,
    scope_key,
    validate_identifier,
    validate_uuid,
)

CATALOGUE = [
    {"path": "Sensors/Gyro", "kind": "Model"},
    {"path": "Sensors/Gyro/Rate", "kind": "Field"},
    {"path": "Sensors/Gyro/Reset", "kind": "Operation"},
    {"path": "Bus/Clock", "kind": "Model"},
]

UUID_A = "11111111-2222-3333-4444-555555555555"
UUID_B = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
UUID_C = "0123456f-89ab-cdef-0123-456789abcdef"


def element(**overrides):
    base = {
        "name": "gyro_a",
        "uuid": UUID_A,
        "reference": "Sensors/Gyro",
        "kind": "Model",
        "parent": "Assembly",
    }
    base.update(overrides)
    return base


class IdentifierTests(unittest.TestCase):
    def test_plain_identifier_accepted(self):
        self.assertEqual(validate_identifier("gyro_a"), "gyro_a")

    def test_surrounding_whitespace_is_trimmed(self):
        self.assertEqual(validate_identifier("  clock1  "), "clock1")

    def test_leading_digit_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("1gyro")

    def test_hyphen_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("gyro-a")

    def test_reserved_word_rejected_despite_valid_pattern(self):
        with self.assertRaises(ValueError):
            validate_identifier("Instance")

    def test_over_length_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("g" * (IDENTIFIER_MAX_LENGTH + 1))

    def test_bound_length_identifier_accepted(self):
        name = "g" * IDENTIFIER_MAX_LENGTH
        self.assertEqual(validate_identifier(name), name)

    def test_blank_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("   ")

    def test_non_string_name_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier(7)


class UuidTests(unittest.TestCase):
    def test_uppercase_uuid_is_normalised(self):
        self.assertEqual(validate_uuid(UUID_B.upper()), UUID_B)

    def test_hex_letters_beyond_f_rejected(self):
        with self.assertRaises(ValueError):
            validate_uuid("gggggggg-bbbb-cccc-dddd-eeeeeeeeeeee")

    def test_wrong_group_lengths_rejected(self):
        with self.assertRaises(ValueError):
            validate_uuid("1111111-2222-3333-4444-555555555555")

    def test_non_string_uuid_rejected(self):
        with self.assertRaises(ValueError):
            validate_uuid(None)


class CatalogueIndexTests(unittest.TestCase):
    def test_index_maps_path_to_kind(self):
        index = build_catalogue_index(CATALOGUE)
        self.assertEqual(index["Sensors/Gyro/Rate"], "Field")

    def test_duplicate_path_rejected(self):
        with self.assertRaises(ValueError):
            build_catalogue_index(CATALOGUE + [{"path": "Bus/Clock", "kind": "Model"}])

    def test_empty_catalogue_rejected(self):
        with self.assertRaises(ValueError):
            build_catalogue_index([])

    def test_entry_missing_kind_rejected(self):
        with self.assertRaises(ValueError):
            build_catalogue_index([{"path": "Bus/Clock"}])

    def test_unresolved_reference_returns_none(self):
        index = build_catalogue_index(CATALOGUE)
        self.assertIsNone(resolve_reference(index, "Sensors/Star"))

    def test_reference_path_must_be_text(self):
        index = build_catalogue_index(CATALOGUE)
        with self.assertRaises(ValueError):
            resolve_reference(index, 12)


class ScopeKeyTests(unittest.TestCase):
    def test_none_parent_is_the_root_scope(self):
        self.assertEqual(scope_key(None), "")

    def test_slashes_are_trimmed(self):
        self.assertEqual(scope_key("/Assembly/Bus/"), "Assembly/Bus")

    def test_non_string_parent_rejected(self):
        with self.assertRaises(ValueError):
            scope_key(3.5)


class ElementGradingTests(unittest.TestCase):
    def setUp(self):
        self.index = build_catalogue_index(CATALOGUE)

    def test_clean_element_satisfies_all_five_items(self):
        record = assess_element(element(), self.index)
        self.assertEqual(record["satisfied"], NORMATIVE_ITEM_COUNT)
        self.assertTrue(record["compliant"])
        self.assertEqual(record["findings"], [])

    def test_every_normative_item_is_graded(self):
        record = assess_element(element(), self.index)
        self.assertEqual(sorted(record["items"]), sorted(NORMATIVE_ITEMS))

    def test_sibling_name_collision_is_caught(self):
        names, uuids = {}, set()
        assess_element(element(), self.index, names, uuids)
        second = assess_element(element(uuid=UUID_B), self.index, names, uuids)
        self.assertFalse(second["items"]["name-unique-in-parent-scope"])

    def test_same_name_in_a_different_parent_scope_is_allowed(self):
        names, uuids = {}, set()
        assess_element(element(), self.index, names, uuids)
        second = assess_element(
            element(uuid=UUID_B, parent="OtherAssembly"), self.index, names, uuids
        )
        self.assertTrue(second["items"]["name-unique-in-parent-scope"])

    def test_unresolved_reference_also_blocks_the_kind_item(self):
        record = assess_element(element(reference="Sensors/Star"), self.index)
        self.assertFalse(record["items"]["reference-resolves-in-catalogue"])
        self.assertFalse(record["items"]["declared-kind-agrees-with-target"])

    def test_resolvable_reference_to_the_wrong_kind_is_caught(self):
        record = assess_element(
            element(reference="Sensors/Gyro/Rate", kind="Model"), self.index
        )
        self.assertTrue(record["items"]["reference-resolves-in-catalogue"])
        self.assertFalse(record["items"]["declared-kind-agrees-with-target"])

    def test_repeated_uuid_is_caught(self):
        names, uuids = {}, set()
        assess_element(element(), self.index, names, uuids)
        second = assess_element(
            element(name="gyro_b", reference="Bus/Clock"), self.index, names, uuids
        )
        self.assertFalse(second["items"]["uuid-well-formed-and-unique"])

    def test_malformed_name_does_not_claim_scope_uniqueness(self):
        record = assess_element(element(name="1gyro"), self.index)
        self.assertFalse(record["items"]["identifier-well-formed"])
        self.assertFalse(record["items"]["name-unique-in-parent-scope"])

    def test_missing_key_rejected(self):
        broken = element()
        del broken["uuid"]
        with self.assertRaises(ValueError):
            assess_element(broken, self.index)

    def test_non_mapping_element_rejected(self):
        with self.assertRaises(ValueError):
            assess_element(["gyro_a"], self.index)


class ComplianceRatioTests(unittest.TestCase):
    def test_full_compliance_is_one(self):
        self.assertAlmostEqual(compliance_ratio(10, 10), 1.0, places=9)

    def test_partial_compliance(self):
        self.assertAlmostEqual(compliance_ratio(3, 4), 0.75, places=9)

    def test_zero_total_rejected(self):
        with self.assertRaises(ValueError):
            compliance_ratio(0, 0)

    def test_satisfied_above_total_rejected(self):
        with self.assertRaises(ValueError):
            compliance_ratio(6, 5)

    def test_boolean_argument_rejected(self):
        with self.assertRaises(ValueError):
            compliance_ratio(True, 5)


class ConfigurationTests(unittest.TestCase):
    def _config(self, elements):
        return {"catalogue": CATALOGUE, "elements": elements}

    def test_clean_configuration_is_compliant(self):
        result = assess_configuration(
            self._config([
                element(),
                element(name="clock_a", uuid=UUID_B, reference="Bus/Clock"),
            ])
        )
        self.assertTrue(result["compliant"])
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["ratio"], 1.0, places=9)

    def test_graded_count_is_five_per_element(self):
        result = assess_configuration(self._config([element()]))
        self.assertEqual(result["graded"], NORMATIVE_ITEM_COUNT)

    def test_findings_are_prefixed_with_the_element_name(self):
        result = assess_configuration(
            self._config([element(name="gyro_a", reference="Sensors/Star")])
        )
        self.assertFalse(result["compliant"])
        self.assertTrue(result["findings"][0].startswith("gyro_a: "))

    def test_ratio_reflects_partial_satisfaction(self):
        result = assess_configuration(
            self._config([
                element(),
                element(name="clock_a", uuid=UUID_C, reference="Nowhere", kind="Model"),
            ])
        )
        self.assertAlmostEqual(result["ratio"], 8.0 / 10.0, places=9)

    def test_empty_element_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_configuration(self._config([]))

    def test_missing_catalogue_rejected(self):
        with self.assertRaises(ValueError):
            assess_configuration({"elements": [element()]})

    def test_non_mapping_config_rejected(self):
        with self.assertRaises(ValueError):
            assess_configuration("configuration")


if __name__ == "__main__":
    unittest.main()
