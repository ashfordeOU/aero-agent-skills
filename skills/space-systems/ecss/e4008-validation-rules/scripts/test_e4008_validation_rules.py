"""Contract tests for the clause 5.7.2.2 exchange file validation rules."""

import unittest

from e4008_validation_rules_logic import (
    ENTRY_KINDS,
    FIELD_TYPES,
    NORMATIVE_ITEMS,
    NORMATIVE_ITEM_COUNT,
    REFERENCE_TARGETS,
    assess_validation_rules,
    detect_reference_cycles,
    validate_entry_structure,
    validate_identifier,
    validate_reference_pass,
    validate_structure_pass,
)


def clean_entries():
    """A file body that satisfies both normative items."""
    return [
        {"id": "T_Base", "kind": "type", "name": "BaseType"},
        {"id": "T_Power", "kind": "type", "name": "PowerType", "base_ref": "T_Base"},
        {"id": "M_Sat", "kind": "model", "name": "Sat", "type_ref": "T_Base"},
        {"id": "M_Power", "kind": "model", "name": "Power", "type_ref": "T_Power",
         "parent_ref": "M_Sat"},
        {"id": "L_Bus", "kind": "link", "source_ref": "M_Sat", "target_ref": "M_Power"},
        {"id": "S_Step", "kind": "schedule_entry", "name": "Step", "model_ref": "M_Power",
         "period_ticks": 250},
    ]


class IdentifierTests(unittest.TestCase):
    def test_plain_identifier_accepted(self):
        self.assertEqual(validate_identifier("M_Sat"), "M_Sat")

    def test_path_style_identifier_accepted(self):
        self.assertEqual(validate_identifier("Sat/Power.bus"), "Sat/Power.bus")

    def test_leading_underscore_accepted(self):
        self.assertEqual(validate_identifier("_hidden"), "_hidden")

    def test_leading_digit_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("1Model")

    def test_padded_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier(" M_Sat")

    def test_empty_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("")

    def test_over_long_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("m" * 129)

    def test_illegal_character_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier("M Sat")

    def test_non_string_identifier_rejected(self):
        with self.assertRaises(ValueError):
            validate_identifier(12)


class SchemaTests(unittest.TestCase):
    def test_every_kind_requires_an_id_and_a_kind(self):
        for schema in ENTRY_KINDS.values():
            self.assertIn("id", schema["required"])
            self.assertIn("kind", schema["required"])

    def test_every_declared_field_has_a_type(self):
        for schema in ENTRY_KINDS.values():
            for field in tuple(schema["required"]) + tuple(schema["optional"]):
                self.assertIn(field, FIELD_TYPES)

    def test_every_reference_target_is_a_known_kind(self):
        for field, kind in REFERENCE_TARGETS.items():
            self.assertIn(field, FIELD_TYPES)
            self.assertIn(kind, ENTRY_KINDS)


class StructureTests(unittest.TestCase):
    def test_sound_entry_is_compliant(self):
        result = validate_entry_structure(
            {"id": "T_Base", "kind": "type", "name": "BaseType"})
        self.assertTrue(result["compliant"])
        self.assertEqual(result["kind"], "type")

    def test_unknown_kind_is_a_finding(self):
        result = validate_entry_structure({"id": "X", "kind": "widget"})
        self.assertFalse(result["compliant"])

    def test_missing_required_field_is_a_finding(self):
        result = validate_entry_structure({"id": "M", "kind": "model", "name": "M"})
        self.assertFalse(result["compliant"])
        self.assertTrue(any("type_ref" in f for f in result["findings"]))

    def test_undeclared_field_is_a_finding(self):
        result = validate_entry_structure(
            {"id": "T", "kind": "type", "name": "T", "colour": "red"})
        self.assertFalse(result["compliant"])
        self.assertTrue(any("undeclared field" in f for f in result["findings"]))

    def test_wrong_field_type_is_a_finding(self):
        result = validate_entry_structure(
            {"id": "S", "kind": "schedule_entry", "name": "S", "model_ref": "M",
             "period_ticks": -1})
        self.assertFalse(result["compliant"])

    def test_boolean_period_is_not_a_positive_integer(self):
        result = validate_entry_structure(
            {"id": "S", "kind": "schedule_entry", "name": "S", "model_ref": "M",
             "period_ticks": True})
        self.assertFalse(result["compliant"])

    def test_blank_name_is_a_finding(self):
        result = validate_entry_structure({"id": "T", "kind": "type", "name": "   "})
        self.assertFalse(result["compliant"])

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry_structure(["id"])

    def test_clean_body_passes_the_structure_pass(self):
        report = validate_structure_pass(clean_entries())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["unsound_positions"], [])

    def test_empty_body_rejected(self):
        with self.assertRaises(ValueError):
            validate_structure_pass([])

    def test_non_sequence_body_rejected(self):
        with self.assertRaises(ValueError):
            validate_structure_pass({"id": "T"})


class CycleTests(unittest.TestCase):
    def test_acyclic_graph_has_no_cycle(self):
        self.assertEqual(detect_reference_cycles({"a": ["b"], "b": []}), [])

    def test_two_node_cycle_is_found(self):
        self.assertEqual(detect_reference_cycles({"a": ["b"], "b": ["a"]}), ["a", "b"])

    def test_self_reference_is_a_cycle(self):
        self.assertEqual(detect_reference_cycles({"a": ["a"]}), ["a"])

    def test_dangling_target_is_ignored_by_the_cycle_walk(self):
        self.assertEqual(detect_reference_cycles({"a": ["ghost"]}), [])

    def test_non_mapping_edges_rejected(self):
        with self.assertRaises(ValueError):
            detect_reference_cycles([("a", "b")])


class ReferenceTests(unittest.TestCase):
    def test_clean_body_passes_the_reference_pass(self):
        entries = clean_entries()
        result = validate_reference_pass(entries)
        self.assertTrue(result["compliant"])
        self.assertIn("M_Power", result["identifiers"])

    def test_duplicate_identifier_is_a_finding(self):
        entries = clean_entries()
        entries.append({"id": "M_Sat", "kind": "model", "name": "Twin", "type_ref": "T_Base"})
        result = validate_reference_pass(entries)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["duplicates"], ["M_Sat"])

    def test_unresolved_reference_is_a_finding(self):
        entries = clean_entries()
        entries[2]["type_ref"] = "T_Missing"
        result = validate_reference_pass(entries)
        self.assertFalse(result["compliant"])
        self.assertTrue(result["unresolved"])

    def test_reference_to_the_wrong_kind_is_a_finding(self):
        entries = clean_entries()
        entries[4]["source_ref"] = "T_Base"
        result = validate_reference_pass(entries)
        self.assertFalse(result["compliant"])
        self.assertTrue(result["kind_mismatch"])

    def test_parent_cycle_is_a_finding(self):
        entries = clean_entries()
        entries[2]["parent_ref"] = "M_Power"
        result = validate_reference_pass(entries)
        self.assertFalse(result["compliant"])
        self.assertEqual(result["cycles"], ["M_Power", "M_Sat"])

    def test_structurally_broken_entry_is_excluded_and_reported(self):
        entries = clean_entries()
        entries.append({"id": "Broken", "kind": "model", "name": "Broken"})
        result = validate_reference_pass(entries)
        self.assertEqual(result["excluded_positions"], [6])
        self.assertTrue(any("excluded from the reference pass" in f for f in result["findings"]))

    def test_bad_structure_report_rejected(self):
        with self.assertRaises(ValueError):
            validate_reference_pass(clean_entries(), structure={"no": "results"})


class AssessmentTests(unittest.TestCase):
    def test_item_catalogue_has_two_entries(self):
        self.assertEqual(len(NORMATIVE_ITEMS), NORMATIVE_ITEM_COUNT)

    def test_clean_body_is_compliant(self):
        result = assess_validation_rules(clean_entries())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["violations"], [])
        self.assertEqual(result["item_count"], NORMATIVE_ITEM_COUNT)

    def test_structural_defect_violates_item_one(self):
        entries = clean_entries()
        entries[0]["colour"] = "red"
        result = assess_validation_rules(entries)
        self.assertIn("VR-01", result["violations"])

    def test_referential_defect_violates_item_two_only(self):
        entries = clean_entries()
        entries[3]["type_ref"] = "T_Absent"
        result = assess_validation_rules(entries)
        self.assertEqual(result["violations"], ["VR-02"])

    def test_both_items_can_fail_together(self):
        entries = clean_entries()
        entries[0]["colour"] = "red"
        entries[3]["type_ref"] = "T_Absent"
        result = assess_validation_rules(entries)
        self.assertEqual(sorted(result["violations"]), ["VR-01", "VR-02"])

    def test_empty_body_rejected(self):
        with self.assertRaises(ValueError):
            assess_validation_rules([])

    def test_every_item_carries_a_title_and_status(self):
        result = assess_validation_rules(clean_entries())
        for item in result["items"]:
            self.assertTrue(item["title"])
            self.assertIn(item["status"], ("satisfied", "violated"))


if __name__ == "__main__":
    unittest.main()
