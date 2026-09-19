#!/usr/bin/env python3
"""Contract test for the two-phase declared lists (offline)."""

import copy
import unittest

from e3102_declared_materials_parts_processes_lists_logic import (
    APPROVAL_STATUSES,
    COMMON_FIELDS,
    EXTRA_FIELDS_BY_LIST,
    LIST_TYPES,
    LISTS_CONTROLLED,
    LISTS_OPEN,
    assess_fluid_compatibility,
    audit_entry,
    compile_declared_lists,
    entries_awaiting_approval,
    group_entries,
    list_summary,
    missing_fields,
    required_fields,
    validate_entry,
)

MATERIAL = {
    "list_type": "declared-materials-list",
    "item_id": "MAT-001",
    "designation": "aluminium alloy 6061-T6 extrusion",
    "specification_reference": "MAT-SPEC-014",
    "supplier": "extrusion house",
    "approval_status": "approved",
    "material_form": "extruded profile",
    "lot_traceability": "LOT-2214",
    "fluid_wetted": True,
    "working_fluid": "ammonia",
    "compatibility_evidence": "long-duration life test report LT-0031",
}

PART = {
    "list_type": "declared-parts-list",
    "item_id": "PRT-001",
    "designation": "end cap",
    "specification_reference": "DRW-1102",
    "supplier": "machine shop",
    "approval_status": "approved",
    "part_number": "PN-1102-03",
    "lot_traceability": "LOT-9981",
    "fluid_wetted": False,
}

PROCESS = {
    "list_type": "declared-processes-list",
    "item_id": "PRC-001",
    "designation": "orbital welding of the end cap",
    "specification_reference": "PRC-SPEC-007",
    "supplier": "machine shop",
    "approval_status": "approved",
    "process_specification": "WPS-007 rev C",
    "operator_qualification": "welder card W-118",
    "fluid_wetted": False,
}

BASE_CASE = {
    "equipment": "constant conductance heat pipe assembly",
    "entries": (MATERIAL, PART, PROCESS),
}


def _entry(base, **overrides):
    entry = copy.deepcopy(base)
    entry.update(overrides)
    return entry


def _case(base, **overrides):
    case = copy.deepcopy(base)
    case.update(overrides)
    return case


class FieldRegistryTests(unittest.TestCase):
    def test_every_list_declares_extra_fields(self):
        for list_type in LIST_TYPES:
            self.assertTrue(EXTRA_FIELDS_BY_LIST[list_type])

    def test_required_fields_start_with_the_common_set(self):
        for list_type in LIST_TYPES:
            fields = required_fields(list_type)
            for field in COMMON_FIELDS:
                self.assertIn(field, fields)

    def test_a_process_list_asks_for_operator_qualification(self):
        self.assertIn(
            "operator_qualification", required_fields("declared-processes-list")
        )

    def test_a_parts_list_does_not_ask_for_a_material_form(self):
        self.assertNotIn("material_form", required_fields("declared-parts-list"))

    def test_an_unknown_list_type_rejected(self):
        with self.assertRaises(ValueError):
            required_fields("declared-software-list")


class EntryValidationTests(unittest.TestCase):
    def test_a_complete_entry_validates(self):
        self.assertIs(validate_entry(MATERIAL), MATERIAL)

    def test_an_entry_without_an_item_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry(_entry(MATERIAL, item_id="  "))

    def test_an_entry_with_an_unknown_approval_status_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry(_entry(MATERIAL, approval_status="probably-fine"))

    def test_a_non_boolean_wetted_flag_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry(_entry(MATERIAL, fluid_wetted="yes"))

    def test_a_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            validate_entry("MAT-001")

    def test_every_named_approval_status_is_accepted(self):
        for status in APPROVAL_STATUSES:
            self.assertIs(
                validate_entry(_entry(MATERIAL, approval_status=status)).get(
                    "approval_status"
                ),
                status,
            )


class CompletenessTests(unittest.TestCase):
    def test_a_complete_entry_is_missing_nothing(self):
        self.assertEqual(missing_fields(MATERIAL), [])

    def test_a_dropped_field_is_reported(self):
        broken = _entry(MATERIAL)
        del broken["lot_traceability"]
        self.assertIn("lot_traceability", missing_fields(broken))

    def test_a_blank_field_counts_as_missing(self):
        self.assertIn("supplier", missing_fields(_entry(MATERIAL, supplier="   ")))

    def test_a_process_missing_its_specification_is_reported(self):
        broken = _entry(PROCESS)
        del broken["process_specification"]
        self.assertIn("process_specification", missing_fields(broken))


class CompatibilityTests(unittest.TestCase):
    def test_a_dry_item_needs_no_compatibility_basis(self):
        verdict = assess_fluid_compatibility(PART)
        self.assertFalse(verdict["wetted"])
        self.assertTrue(verdict["evidenced"])

    def test_a_wetted_item_with_evidence_passes(self):
        verdict = assess_fluid_compatibility(MATERIAL)
        self.assertTrue(verdict["wetted"])
        self.assertTrue(verdict["evidenced"])

    def test_a_wetted_item_without_evidence_fails(self):
        broken = _entry(MATERIAL)
        del broken["compatibility_evidence"]
        verdict = assess_fluid_compatibility(broken)
        self.assertFalse(verdict["evidenced"])
        self.assertTrue(any("compatibility basis" in r for r in verdict["reasons"]))

    def test_a_wetted_item_that_names_no_fluid_fails(self):
        broken = _entry(MATERIAL)
        del broken["working_fluid"]
        verdict = assess_fluid_compatibility(broken)
        self.assertTrue(any("name the fluid" in r for r in verdict["reasons"]))

    def test_a_blank_evidence_string_is_no_evidence(self):
        verdict = assess_fluid_compatibility(
            _entry(MATERIAL, compatibility_evidence="  ")
        )
        self.assertFalse(verdict["evidenced"])


class GroupingTests(unittest.TestCase):
    def test_entries_land_in_their_own_list(self):
        grouped = group_entries((MATERIAL, PART, PROCESS))
        for list_type in LIST_TYPES:
            self.assertEqual(len(grouped[list_type]), 1)

    def test_a_duplicate_item_in_one_list_rejected(self):
        with self.assertRaises(ValueError):
            group_entries((MATERIAL, _entry(MATERIAL)))

    def test_the_same_identifier_in_two_lists_is_allowed(self):
        twin = _entry(PART, item_id=MATERIAL["item_id"])
        grouped = group_entries((MATERIAL, twin))
        self.assertEqual(len(grouped["declared-parts-list"]), 1)

    def test_a_non_sequence_entry_set_rejected(self):
        with self.assertRaises(ValueError):
            group_entries("MAT-001")

    def test_pending_entries_are_collected_by_list(self):
        awaiting = entries_awaiting_approval(
            (
                _entry(MATERIAL, approval_status="pending-customer-approval"),
                PART,
                PROCESS,
            )
        )
        self.assertEqual(awaiting["declared-materials-list"], ["MAT-001"])

    def test_nothing_awaits_approval_on_a_fully_approved_set(self):
        self.assertEqual(entries_awaiting_approval((MATERIAL, PART, PROCESS)), {})


class AuditTests(unittest.TestCase):
    def test_a_complete_approved_entry_is_controlled(self):
        audit = audit_entry(MATERIAL)
        self.assertTrue(audit["controlled"])
        self.assertEqual(audit["reasons"], [])

    def test_a_refused_entry_is_not_controlled(self):
        audit = audit_entry(_entry(PART, approval_status="not-approved"))
        self.assertFalse(audit["controlled"])
        self.assertTrue(any("refused approval" in r for r in audit["reasons"]))

    def test_an_approved_entry_missing_a_field_is_not_controlled(self):
        broken = _entry(PROCESS)
        del broken["operator_qualification"]
        audit = audit_entry(broken)
        self.assertFalse(audit["controlled"])
        self.assertIn("operator_qualification", audit["missing_fields"])

    def test_a_wetted_entry_without_evidence_is_not_controlled(self):
        broken = _entry(MATERIAL)
        del broken["compatibility_evidence"]
        self.assertFalse(audit_entry(broken)["controlled"])

    def test_the_summary_counts_controlled_entries(self):
        summary = list_summary((MATERIAL, PART, PROCESS), "declared-materials-list")
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["controlled"], 1)
        self.assertEqual(summary["uncontrolled"], [])

    def test_the_summary_names_the_wetted_items(self):
        summary = list_summary((MATERIAL, PART, PROCESS), "declared-materials-list")
        self.assertEqual(summary["wetted"], ["MAT-001"])


class CompileTests(unittest.TestCase):
    def test_a_complete_declaration_is_controlled(self):
        result = compile_declared_lists(BASE_CASE)
        self.assertEqual(result["verdict"], LISTS_CONTROLLED)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["uncontrolled"], [])

    def test_an_empty_list_opens_the_declaration(self):
        result = compile_declared_lists(_case(BASE_CASE, entries=(MATERIAL, PART)))
        self.assertEqual(result["verdict"], LISTS_OPEN)
        self.assertTrue(
            any("declared-processes-list has no entries" in f for f in result["findings"])
        )

    def test_a_wetted_material_without_evidence_opens_the_declaration(self):
        broken = _entry(MATERIAL)
        del broken["compatibility_evidence"]
        result = compile_declared_lists(
            _case(BASE_CASE, entries=(broken, PART, PROCESS))
        )
        self.assertEqual(result["verdict"], LISTS_OPEN)
        self.assertIn("MAT-001", result["uncontrolled"])

    def test_a_pending_entry_is_reported_without_being_uncontrolled(self):
        pending = _entry(PART, approval_status="pending-customer-approval")
        result = compile_declared_lists(
            _case(BASE_CASE, entries=(MATERIAL, pending, PROCESS))
        )
        self.assertNotIn("PRT-001", result["uncontrolled"])
        self.assertIn("declared-parts-list", result["awaiting_approval"])
        self.assertEqual(result["verdict"], LISTS_OPEN)

    def test_a_refused_entry_lands_in_the_uncontrolled_set(self):
        refused = _entry(PROCESS, approval_status="not-approved")
        result = compile_declared_lists(
            _case(BASE_CASE, entries=(MATERIAL, PART, refused))
        )
        self.assertIn("PRC-001", result["uncontrolled"])

    def test_the_summaries_cover_every_list(self):
        result = compile_declared_lists(BASE_CASE)
        self.assertEqual(set(result["summaries"]), set(LIST_TYPES))

    def test_an_empty_declaration_rejected(self):
        with self.assertRaises(ValueError):
            compile_declared_lists(_case(BASE_CASE, entries=()))

    def test_a_declaration_without_an_equipment_name_rejected(self):
        case = _case(BASE_CASE)
        del case["equipment"]
        with self.assertRaises(ValueError):
            compile_declared_lists(case)

    def test_a_duplicate_item_rejected_at_compile_time(self):
        with self.assertRaises(ValueError):
            compile_declared_lists(
                _case(BASE_CASE, entries=(MATERIAL, _entry(MATERIAL), PART, PROCESS))
            )

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            compile_declared_lists("heat pipe assembly")


if __name__ == "__main__":
    unittest.main()
