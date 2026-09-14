#!/usr/bin/env python3
"""Contract test for the external diode process identification document.

Walks the clause workflow step by step: whether what the supplier wrote
is a written document in force at all, whether the part in front of the
reviewer belongs inside the document's scope, the processes the part is
genuinely made by against the set declared, the production document and
the qualification lot each declaration has to name, the date arithmetic
that catches a document written after the lot it covers, the share of
qualification-critical processes that reach qualification, and the one
document verdict. This is the gate 3 review evidence for the leaf.
"""

import copy
import unittest

from e2008_protection_diode_production_control_logic import (
    PID_ACCEPTED,
    PID_INCOMPLETE,
    PID_NOT_IN_FORCE,
    QUALIFICATION_CRITICAL,
    assess_process_identification_document,
    control_and_evidence_links,
    document_form_standing,
    document_precedes_lot,
    entry_coverage_share,
    process_coverage,
    qualification_entry_scope,
)

ALL_PROCESSES = [
    "die-attach",
    "package-seal",
    "lead-forming",
    "lead-finish",
    "screening-burn-in",
    "electrical-test",
    "marking",
    "packing",
]


def _entries(processes=None):
    names = ALL_PROCESSES if processes is None else processes
    return [
        {
            "process": name,
            "controlling_document": "PD-%s" % name,
            "qualification_lot": "QL-2026-04",
        }
        for name in names
    ]


SOUND_CASE = {
    "document_id": "PID-EXT-DIODE-02",
    "document_form": "written-and-issued",
    "diode_role": "external-protection-diode",
    "enters_qualification": True,
    "document_issue_date": "2026-01-10",
    "lot_build_date": "2026-03-02",
    "processes_used": list(ALL_PROCESSES),
    "declared_entries": _entries(),
}


def _case(**overrides):
    record = copy.deepcopy(SOUND_CASE)
    record.update(overrides)
    return record


class DocumentFormTests(unittest.TestCase):
    def test_an_issued_written_document_is_in_force(self):
        result = document_form_standing("written-and-issued")
        self.assertTrue(result["in_force"])
        self.assertEqual(result["findings"], [])

    def test_a_draft_is_written_but_not_in_force(self):
        result = document_form_standing("written-draft")
        self.assertTrue(result["written"])
        self.assertFalse(result["in_force"])

    def test_slides_are_not_a_written_document(self):
        result = document_form_standing("presentation-pack")
        self.assertFalse(result["written"])
        self.assertTrue(result["findings"])

    def test_a_verbal_baseline_is_not_a_written_document(self):
        self.assertFalse(document_form_standing("verbal-baseline")["written"])

    def test_an_absent_document_is_reported(self):
        self.assertTrue(document_form_standing("absent")["findings"])

    def test_unknown_document_form_rejected(self):
        with self.assertRaises(ValueError):
            document_form_standing("a-shared-folder")


class ScopeTests(unittest.TestCase):
    def test_an_external_diode_entering_qualification_is_in_scope(self):
        result = qualification_entry_scope("external-protection-diode", True)
        self.assertTrue(result["in_scope"])
        self.assertEqual(result["findings"], [])

    def test_an_integral_diode_is_controlled_elsewhere(self):
        result = qualification_entry_scope("integral-protection-diode", True)
        self.assertFalse(result["in_scope"])
        self.assertTrue(result["findings"])

    def test_a_part_not_entering_qualification_is_out_of_scope(self):
        result = qualification_entry_scope("external-protection-diode", False)
        self.assertFalse(result["in_scope"])

    def test_non_boolean_entry_flag_rejected(self):
        with self.assertRaises(ValueError):
            qualification_entry_scope("external-protection-diode", "yes")


class CoverageTests(unittest.TestCase):
    def test_a_document_covering_every_process_used_is_complete(self):
        result = process_coverage(ALL_PROCESSES, ALL_PROCESSES)
        self.assertEqual(result["undeclared"], [])
        self.assertEqual(result["missing_critical"], [])
        self.assertAlmostEqual(result["coverage_share"], 1.0, places=9)

    def test_a_process_used_and_never_declared_is_named(self):
        declared = [p for p in ALL_PROCESSES if p != "lead-finish"]
        result = process_coverage(declared, ALL_PROCESSES)
        self.assertEqual(result["undeclared"], ["lead-finish"])
        self.assertEqual(result["missing_critical"], ["lead-finish"])

    def test_a_declared_process_the_part_is_not_made_by_is_named(self):
        used = [p for p in ALL_PROCESSES if p != "marking"]
        result = process_coverage(ALL_PROCESSES, used)
        self.assertEqual(result["declared_not_used"], ["marking"])

    def test_coverage_share_counts_the_processes_used(self):
        declared = ["die-attach", "package-seal"]
        used = ["die-attach", "package-seal", "marking", "packing"]
        result = process_coverage(declared, used)
        self.assertAlmostEqual(result["coverage_share"], 0.5, places=9)

    def test_a_repeated_declaration_rejected(self):
        with self.assertRaises(ValueError):
            process_coverage(["die-attach", "die-attach"], ALL_PROCESSES)

    def test_an_unknown_process_rejected(self):
        with self.assertRaises(ValueError):
            process_coverage(["die-attach"], ["die-attach", "gold-plating"])

    def test_an_empty_build_route_rejected(self):
        with self.assertRaises(ValueError):
            process_coverage(ALL_PROCESSES, [])


class LinkTests(unittest.TestCase):
    def test_fully_linked_declarations_report_nothing(self):
        result = control_and_evidence_links(_entries())
        self.assertEqual(result["uncontrolled"], [])
        self.assertEqual(result["never_entered_qualification"], [])

    def test_a_declaration_with_no_controlling_document_is_named(self):
        rows = _entries()
        rows[0]["controlling_document"] = ""
        result = control_and_evidence_links(rows)
        self.assertEqual(result["uncontrolled"], ["die-attach"])

    def test_a_declaration_with_no_qualification_lot_is_named(self):
        rows = _entries()
        rows[4]["qualification_lot"] = None
        result = control_and_evidence_links(rows)
        self.assertEqual(result["never_entered_qualification"],
                         ["screening-burn-in"])

    def test_empty_entry_list_rejected(self):
        with self.assertRaises(ValueError):
            control_and_evidence_links([])

    def test_non_mapping_entry_rejected(self):
        with self.assertRaises(ValueError):
            control_and_evidence_links(["die-attach"])


class ChronologyTests(unittest.TestCase):
    def test_a_document_issued_before_the_lot_is_ordered(self):
        result = document_precedes_lot("2026-01-10", "2026-03-02")
        self.assertTrue(result["ordered"])
        self.assertEqual(result["days_ahead"], 51)

    def test_a_document_issued_the_day_the_lot_was_built_is_ordered(self):
        result = document_precedes_lot("2026-03-02", "2026-03-02")
        self.assertTrue(result["ordered"])
        self.assertEqual(result["days_ahead"], 0)

    def test_a_document_issued_after_the_lot_is_a_record_not_a_commitment(self):
        result = document_precedes_lot("2026-04-01", "2026-03-02")
        self.assertFalse(result["ordered"])
        self.assertEqual(result["days_ahead"], -30)
        self.assertTrue(result["findings"])

    def test_a_malformed_date_rejected(self):
        with self.assertRaises(ValueError):
            document_precedes_lot("early spring", "2026-03-02")


class EntryShareTests(unittest.TestCase):
    def test_every_critical_process_reaching_qualification_scores_one(self):
        result = entry_coverage_share(ALL_PROCESSES, ALL_PROCESSES)
        self.assertAlmostEqual(result["entry_share"], 1.0, places=9)
        self.assertEqual(result["short"], [])

    def test_a_declared_but_unqualified_process_does_not_count(self):
        entered = [p for p in ALL_PROCESSES if p != "package-seal"]
        result = entry_coverage_share(ALL_PROCESSES, entered)
        self.assertEqual(result["short"], ["package-seal"])
        self.assertAlmostEqual(
            result["entry_share"], 4.0 / len(QUALIFICATION_CRITICAL), places=9
        )

    def test_a_policy_with_no_critical_processes_rejected(self):
        with self.assertRaises(ValueError):
            entry_coverage_share(ALL_PROCESSES, ALL_PROCESSES, ())


class DocumentVerdictTests(unittest.TestCase):
    def test_a_sound_document_identifies_the_processes(self):
        result = assess_process_identification_document(_case())
        self.assertEqual(result["verdict"], PID_ACCEPTED)
        self.assertEqual(result["findings"], [])
        self.assertTrue(result["entry_floor_met"])

    def test_a_draft_document_is_not_in_force(self):
        result = assess_process_identification_document(
            _case(document_form="written-draft")
        )
        self.assertEqual(result["verdict"], PID_NOT_IN_FORCE)

    def test_an_integral_diode_falls_outside_this_document(self):
        result = assess_process_identification_document(
            _case(diode_role="integral-protection-diode")
        )
        self.assertEqual(result["verdict"], PID_NOT_IN_FORCE)

    def test_a_part_not_entering_qualification_falls_outside(self):
        result = assess_process_identification_document(
            _case(enters_qualification=False)
        )
        self.assertEqual(result["verdict"], PID_NOT_IN_FORCE)

    def test_an_undeclared_critical_process_leaves_the_document_incomplete(self):
        rows = _entries([p for p in ALL_PROCESSES if p != "die-attach"])
        result = assess_process_identification_document(
            _case(declared_entries=rows)
        )
        self.assertEqual(result["verdict"], PID_INCOMPLETE)
        self.assertEqual(result["coverage"]["missing_critical"], ["die-attach"])

    def test_a_declaration_with_no_qualification_lot_is_incomplete(self):
        rows = _entries()
        rows[3]["qualification_lot"] = ""
        result = assess_process_identification_document(
            _case(declared_entries=rows)
        )
        self.assertEqual(result["verdict"], PID_INCOMPLETE)
        self.assertFalse(result["entry_floor_met"])

    def test_a_declaration_with_no_production_document_is_incomplete(self):
        rows = _entries()
        rows[7]["controlling_document"] = None
        result = assess_process_identification_document(
            _case(declared_entries=rows)
        )
        self.assertEqual(result["verdict"], PID_INCOMPLETE)
        self.assertEqual(result["links"]["uncontrolled"], ["packing"])

    def test_a_document_written_after_the_lot_is_incomplete(self):
        result = assess_process_identification_document(
            _case(document_issue_date="2026-04-01")
        )
        self.assertEqual(result["verdict"], PID_INCOMPLETE)
        self.assertFalse(result["chronology"]["ordered"])

    def test_policy_can_shorten_the_critical_process_set(self):
        rows = _entries([p for p in ALL_PROCESSES if p != "lead-finish"])
        used = [p for p in ALL_PROCESSES if p != "lead-finish"]
        relaxed = assess_process_identification_document(
            _case(
                declared_entries=rows,
                processes_used=used,
                policy={"critical_processes": ("die-attach", "package-seal")},
            )
        )
        self.assertEqual(relaxed["verdict"], PID_ACCEPTED)

    def test_an_empty_declaration_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_process_identification_document(_case(declared_entries=[]))

    def test_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_process_identification_document("the processes were written up")


if __name__ == "__main__":
    unittest.main()
