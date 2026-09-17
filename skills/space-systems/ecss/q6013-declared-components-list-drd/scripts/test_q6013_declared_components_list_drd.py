#!/usr/bin/env python3
"""Contract tests for the Annex B declared components list data item.

Every workflow step the SKILL.md sets out is exercised here, together
with the stop conditions the gate 3 contract reviews: a refused data-item
policy, a list that was never submitted, a list with no reference or
issue, an empty list, a line missing a required field, a part identifier
declared twice under a different part, a part in a radiation environment
with no evidence, a broker purchase with no justification and entries
left pending or rejected.
"""

import unittest

from q6013_declared_components_list_drd_logic import (
    APPROVAL_STATE_OUTSTANDING,
    APPROVED,
    APPLICATION_REFERENCE,
    AUTOMOTIVE_GRADE,
    BROKER_ROUTE_UNJUSTIFIED,
    COMMERCIAL_GRADE,
    CONDITIONALLY_APPROVED,
    DEFAULT_LIST_DRD_POLICY,
    DUPLICATE_PART_CONFLICT,
    ENTRY_COMPLETENESS_SHORT,
    FRANCHISED_DISTRIBUTOR,
    INDEPENDENT_BROKER,
    LIST_NOT_ESTABLISHED,
    LIST_SUBMITTABLE,
    MANUFACTURER,
    MANUFACTURER_DIRECT,
    PENDING,
    PART_IDENTIFIER,
    QUALITY_LEVEL,
    RADIATION_EVIDENCE_MISSING,
    RADIATION_EVIDENCE_REFERENCE,
    REJECTED,
    REQUIRED_ENTRY_FIELDS,
    assess_declared_components_list_drd,
    conflicting_part_identifiers,
    entries_grouped_by_approval_state,
    entries_without_radiation_evidence,
    entry_completeness,
    entry_is_complete,
    incomplete_entries,
    missing_fields,
    pending_share,
    unjustified_broker_entries,
    validate_entries,
    validate_entry,
    validate_list_drd_policy,
    validate_list_identity,
)


def _policy(**overrides):
    policy = dict(DEFAULT_LIST_DRD_POLICY)
    policy.update(overrides)
    return policy


def _entry(identifier="CAP-1005", **overrides):
    entry = {
        PART_IDENTIFIER: identifier,
        MANUFACTURER: "north-line-semiconductors",
        QUALITY_LEVEL: AUTOMOTIVE_GRADE,
        "procurement_route": FRANCHISED_DISTRIBUTOR,
        RADIATION_EVIDENCE_REFERENCE: "RAD-RPT-0071",
        APPLICATION_REFERENCE: "SCH-PWR-12",
        "approval_state": APPROVED,
        "radiation_environment": True,
        "broker_justification": "",
    }
    entry.update(overrides)
    return entry


def _entries():
    return [
        _entry("CAP-1005"),
        _entry("REG-2210", quality_level=COMMERCIAL_GRADE),
        _entry("MCU-3380", procurement_route=MANUFACTURER_DIRECT),
    ]


def _list(**overrides):
    declared = {
        "list_reference": "DCL-COTS-0912",
        "issue": "issue 3",
        "entries": _entries(),
    }
    declared.update(overrides)
    return declared


def _case(**overrides):
    case = {"policy": _policy(), "declared_list": _list()}
    case.update(overrides)
    return case


class PolicyValidationTests(unittest.TestCase):
    def test_default_policy_is_usable(self):
        self.assertIs(
            validate_list_drd_policy(DEFAULT_LIST_DRD_POLICY), DEFAULT_LIST_DRD_POLICY
        )

    def test_non_mapping_policy_refused(self):
        with self.assertRaises(ValueError):
            validate_list_drd_policy("min_entry_completeness")

    def test_completeness_floor_above_one_refused(self):
        with self.assertRaises(ValueError):
            validate_list_drd_policy(_policy(min_entry_completeness=1.2))

    def test_negative_pending_share_refused(self):
        with self.assertRaises(ValueError):
            validate_list_drd_policy(_policy(max_pending_share=-0.1))

    def test_non_boolean_radiation_flag_refused(self):
        with self.assertRaises(ValueError):
            validate_list_drd_policy(_policy(require_radiation_evidence="yes"))


class IdentityValidationTests(unittest.TestCase):
    def test_identity_is_read_back(self):
        identity = validate_list_identity(_list())
        self.assertEqual(identity["list_reference"], "DCL-COTS-0912")
        self.assertEqual(identity["issue"], "issue 3")

    def test_non_mapping_list_refused(self):
        with self.assertRaises(ValueError):
            validate_list_identity(["DCL"])

    def test_non_string_reference_refused(self):
        with self.assertRaises(ValueError):
            validate_list_identity(_list(list_reference=912))


class EntryValidationTests(unittest.TestCase):
    def test_unrecognised_quality_level_refused(self):
        with self.assertRaises(ValueError):
            validate_entry(_entry(quality_level="aerospace-ish"))

    def test_unrecognised_procurement_route_refused(self):
        with self.assertRaises(ValueError):
            validate_entry(_entry(procurement_route="a-friend"))

    def test_unrecognised_approval_state_refused(self):
        with self.assertRaises(ValueError):
            validate_entry(_entry(approval_state="probably-fine"))

    def test_non_boolean_radiation_environment_refused(self):
        with self.assertRaises(ValueError):
            validate_entry(_entry(radiation_environment="maybe"))

    def test_non_mapping_entry_refused(self):
        with self.assertRaises(ValueError):
            validate_entry(["CAP-1005"])

    def test_entries_sequence_is_required(self):
        with self.assertRaises(ValueError):
            validate_entries("CAP-1005")


class CompletenessTests(unittest.TestCase):
    def test_a_full_line_is_complete(self):
        self.assertTrue(entry_is_complete(_entry()))
        self.assertEqual(missing_fields(_entry()), ())

    def test_a_blank_field_is_named(self):
        self.assertEqual(
            missing_fields(_entry(application_reference="  ")),
            (APPLICATION_REFERENCE,),
        )

    def test_completeness_is_the_complete_share(self):
        entries = _entries()
        entries[1][APPLICATION_REFERENCE] = ""
        self.assertAlmostEqual(entry_completeness(entries), 2.0 / 3.0, places=9)

    def test_incomplete_line_is_named_by_its_identifier(self):
        entries = _entries()
        entries[2][MANUFACTURER] = ""
        self.assertEqual(incomplete_entries(entries), ("MCU-3380",))

    def test_a_line_with_no_identifier_is_named_by_position(self):
        entries = [_entry(identifier="")]
        self.assertEqual(incomplete_entries(entries), ("line 1",))

    def test_every_required_field_is_graded(self):
        for field in REQUIRED_ENTRY_FIELDS:
            entry = _entry(**{field: ""})
            self.assertIn(field, missing_fields(entry))


class DuplicateTests(unittest.TestCase):
    def test_identical_repeat_is_not_a_conflict(self):
        entries = _entries() + [_entry("CAP-1005")]
        self.assertEqual(conflicting_part_identifiers(entries), ())

    def test_same_number_different_manufacturer_conflicts(self):
        entries = _entries() + [_entry("CAP-1005", manufacturer="south-line-parts")]
        self.assertEqual(conflicting_part_identifiers(entries), ("CAP-1005",))

    def test_same_number_different_grade_conflicts(self):
        entries = _entries() + [_entry("CAP-1005", quality_level=COMMERCIAL_GRADE)]
        self.assertEqual(conflicting_part_identifiers(entries), ("CAP-1005",))


class GroupingTests(unittest.TestCase):
    def test_lines_are_grouped_by_approval_state(self):
        entries = _entries()
        entries[0]["approval_state"] = PENDING
        grouped = entries_grouped_by_approval_state(entries)
        self.assertEqual(grouped[PENDING], ("CAP-1005",))
        self.assertEqual(len(grouped[APPROVED]), 2)

    def test_pending_share_is_the_pending_fraction(self):
        entries = _entries()
        entries[0]["approval_state"] = PENDING
        self.assertAlmostEqual(pending_share(entries), 1.0 / 3.0, places=9)

    def test_an_empty_list_has_no_pending_share(self):
        self.assertAlmostEqual(pending_share([]), 0.0, places=9)


class EvidenceTests(unittest.TestCase):
    def test_exposed_line_with_no_evidence_is_named(self):
        entries = _entries()
        entries[1][RADIATION_EVIDENCE_REFERENCE] = ""
        self.assertEqual(entries_without_radiation_evidence(entries), ("REG-2210",))

    def test_a_line_outside_the_radiation_environment_is_not_named(self):
        entries = _entries()
        entries[1][RADIATION_EVIDENCE_REFERENCE] = ""
        entries[1]["radiation_environment"] = False
        self.assertEqual(entries_without_radiation_evidence(entries), ())

    def test_broker_line_without_justification_is_named(self):
        entries = _entries()
        entries[2]["procurement_route"] = INDEPENDENT_BROKER
        self.assertEqual(unjustified_broker_entries(entries), ("MCU-3380",))

    def test_broker_line_with_justification_is_accepted(self):
        entries = _entries()
        entries[2]["procurement_route"] = INDEPENDENT_BROKER
        entries[2]["broker_justification"] = "last-time-buy, sole source"
        self.assertEqual(unjustified_broker_entries(entries), ())


class AssessmentTests(unittest.TestCase):
    def test_complete_list_satisfies_the_data_item(self):
        result = assess_declared_components_list_drd(_case())
        self.assertEqual(result["verdict"], LIST_SUBMITTABLE)
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["entry_count"], 3)

    def test_absent_list_stops_the_assessment(self):
        result = assess_declared_components_list_drd(_case(declared_list=None))
        self.assertEqual(result["verdict"], LIST_NOT_ESTABLISHED)

    def test_blank_issue_stops_the_assessment(self):
        result = assess_declared_components_list_drd(
            _case(declared_list=_list(issue="   "))
        )
        self.assertEqual(result["verdict"], LIST_NOT_ESTABLISHED)

    def test_empty_entry_sequence_stops_the_assessment(self):
        result = assess_declared_components_list_drd(
            _case(declared_list=_list(entries=[]))
        )
        self.assertEqual(result["verdict"], LIST_NOT_ESTABLISHED)

    def test_missing_entries_key_refused(self):
        declared = _list()
        del declared["entries"]
        with self.assertRaises(ValueError):
            assess_declared_components_list_drd(_case(declared_list=declared))

    def test_incomplete_entry_outranks_the_later_checks(self):
        entries = _entries()
        entries[0][APPLICATION_REFERENCE] = ""
        result = assess_declared_components_list_drd(
            _case(declared_list=_list(entries=entries))
        )
        self.assertEqual(result["verdict"], ENTRY_COMPLETENESS_SHORT)

    def test_duplicate_conflict_is_its_own_verdict(self):
        entries = _entries() + [_entry("CAP-1005", manufacturer="south-line-parts")]
        result = assess_declared_components_list_drd(
            _case(declared_list=_list(entries=entries))
        )
        self.assertEqual(result["verdict"], DUPLICATE_PART_CONFLICT)

    def test_missing_radiation_evidence_is_its_own_verdict(self):
        entries = _entries()
        entries[1][RADIATION_EVIDENCE_REFERENCE] = ""
        result = assess_declared_components_list_drd(
            _case(
                policy=_policy(min_entry_completeness=0.5),
                declared_list=_list(entries=entries),
            )
        )
        self.assertEqual(result["verdict"], RADIATION_EVIDENCE_MISSING)

    def test_unjustified_broker_route_is_its_own_verdict(self):
        entries = _entries()
        entries[2]["procurement_route"] = INDEPENDENT_BROKER
        result = assess_declared_components_list_drd(
            _case(declared_list=_list(entries=entries))
        )
        self.assertEqual(result["verdict"], BROKER_ROUTE_UNJUSTIFIED)

    def test_rejected_entry_is_outstanding(self):
        entries = _entries()
        entries[0]["approval_state"] = REJECTED
        result = assess_declared_components_list_drd(
            _case(declared_list=_list(entries=entries))
        )
        self.assertEqual(result["verdict"], APPROVAL_STATE_OUTSTANDING)

    def test_pending_entry_is_outstanding(self):
        entries = _entries()
        entries[0]["approval_state"] = PENDING
        result = assess_declared_components_list_drd(
            _case(declared_list=_list(entries=entries))
        )
        self.assertEqual(result["verdict"], APPROVAL_STATE_OUTSTANDING)

    def test_conditional_entry_passes_with_an_advisory(self):
        entries = _entries()
        entries[0]["approval_state"] = CONDITIONALLY_APPROVED
        result = assess_declared_components_list_drd(
            _case(declared_list=_list(entries=entries))
        )
        self.assertEqual(result["verdict"], LIST_SUBMITTABLE)
        self.assertEqual(len(result["advisories"]), 1)

    def test_non_mapping_case_refused(self):
        with self.assertRaises(ValueError):
            assess_declared_components_list_drd(["list"])


if __name__ == "__main__":
    unittest.main()
