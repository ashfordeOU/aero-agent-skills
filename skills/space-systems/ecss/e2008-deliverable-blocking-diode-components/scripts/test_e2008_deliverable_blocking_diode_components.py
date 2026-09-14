#!/usr/bin/env python3
"""Contract test for deliverable planar blocking diode components (offline).

Walks the clause workflow step by step: the process identification
document and its issue history, the issue actually in force on the day a
lot was processed, the unreleased and superseded issues, the declared
processing and inspection steps graded separately, the step nobody
authorised, the four record states kept apart, the coverage figures
against their declared minima, the failure policy, and the roll-up into
one delivery verdict. This is the gate 3 review evidence for the leaf.
"""

import copy
import unittest

from e2008_deliverable_blocking_diode_components_logic import (
    DELIVERY_ACCEPTED,
    DELIVERY_NOT_ACCEPTED,
    ISSUE_IN_FORCE,
    ISSUE_NOT_YET_EFFECTIVE,
    ISSUE_SUPERSEDED,
    ISSUE_UNKNOWN,
    ISSUE_UNRELEASED,
    LOT_CLEAR,
    LOT_NO_DOCUMENT,
    LOT_STEP_FAILED,
    LOT_STEP_NOT_PERFORMED,
    LOT_STEP_NO_RECORD,
    LOT_UNAUTHORISED_STEP,
    OUTCOME_FAILED,
    OUTCOME_NOT_PERFORMED,
    OUTCOME_PERFORMED,
    assess_deliverable_blocking_diodes,
    assess_lot_processing,
    categorize_issue,
    issue_in_force,
    resolve_policy,
    validate_process_document,
)

STEPS_A = {
    "planar-blocking-diode-die-attach": "process",
    "planar-blocking-diode-lead-bonding": "process",
    "planar-blocking-diode-encapsulation": "process",
    "planar-blocking-diode-visual-inspection": "inspection",
    "planar-blocking-diode-contact-area-inspection": "inspection",
}

STEPS_B = dict(STEPS_A)
STEPS_B["planar-blocking-diode-surface-passivation"] = "process"


def _document(**overrides):
    doc = {
        "document_id": "PID-BD-PLANAR-0012",
        "issues": [
            {
                "issue": "A",
                "released": True,
                "effective": "2025-03-01",
                "steps": copy.deepcopy(STEPS_A),
            },
            {
                "issue": "B",
                "released": True,
                "effective": "2026-01-15",
                "steps": copy.deepcopy(STEPS_B),
            },
            {
                "issue": "C",
                "released": False,
                "effective": "2026-06-01",
                "steps": copy.deepcopy(STEPS_B),
            },
        ],
    }
    doc.update(copy.deepcopy(overrides))
    return doc


def _records(steps, **overrides):
    book = {name: OUTCOME_PERFORMED for name in steps}
    book.update(overrides)
    return book


def _lot(lot_id="LOT-01", issue="B", processed_on="2026-02-10", **overrides):
    entry = {
        "lot_id": lot_id,
        "document_id": "PID-BD-PLANAR-0012",
        "issue": issue,
        "processed_on": processed_on,
        "step_records": _records(STEPS_B),
    }
    entry.update(copy.deepcopy(overrides))
    return entry


def _case(**overrides):
    case = {
        "part_id": "BD-PLANAR-12",
        "process_document": _document(),
        "lots": [_lot("LOT-01"), _lot("LOT-02")],
    }
    case.update(copy.deepcopy(overrides))
    return case


class DocumentValidationTests(unittest.TestCase):
    def test_a_sound_document_validates_and_orders_its_issues(self):
        doc = validate_process_document(_document())
        self.assertEqual([i["issue"] for i in doc["issues"]], ["A", "B", "C"])

    def test_a_document_with_no_issues_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_process_document(_document(issues=[]))

    def test_a_repeated_issue_label_is_rejected(self):
        doc = _document()
        doc["issues"][1]["issue"] = "A"
        with self.assertRaises(ValueError):
            validate_process_document(doc)

    def test_an_issue_declaring_no_steps_is_rejected(self):
        doc = _document()
        doc["issues"][0]["steps"] = {}
        with self.assertRaises(ValueError):
            validate_process_document(doc)

    def test_an_unknown_step_kind_is_rejected(self):
        doc = _document()
        doc["issues"][0]["steps"]["planar-blocking-diode-die-attach"] = "paperwork"
        with self.assertRaises(ValueError):
            validate_process_document(doc)

    def test_a_malformed_effective_date_is_rejected(self):
        doc = _document()
        doc["issues"][0]["effective"] = "last spring"
        with self.assertRaises(ValueError):
            validate_process_document(doc)


class IssueInForceTests(unittest.TestCase):
    def test_the_issue_in_force_is_the_latest_released_one_already_effective(self):
        self.assertEqual(issue_in_force(_document(), "2026-02-10")["issue"], "B")

    def test_an_earlier_processing_day_is_governed_by_the_earlier_issue(self):
        self.assertEqual(issue_in_force(_document(), "2025-06-01")["issue"], "A")

    def test_a_day_before_any_issue_was_effective_has_no_issue_in_force(self):
        self.assertIsNone(issue_in_force(_document(), "2024-01-01"))

    def test_an_unreleased_issue_never_governs_however_late_its_date(self):
        self.assertEqual(issue_in_force(_document(), "2026-09-01")["issue"], "B")

    def test_the_current_issue_is_graded_in_force(self):
        state = categorize_issue(_document(), "B", "2026-02-10")
        self.assertEqual(state["state"], ISSUE_IN_FORCE)

    def test_an_older_issue_used_after_a_newer_one_took_effect_is_superseded(self):
        state = categorize_issue(_document(), "A", "2026-02-10")
        self.assertEqual(state["state"], ISSUE_SUPERSEDED)
        self.assertEqual(state["governing_issue"], "B")

    def test_an_unreleased_issue_is_named_as_unreleased(self):
        state = categorize_issue(_document(), "C", "2026-09-01")
        self.assertEqual(state["state"], ISSUE_UNRELEASED)

    def test_an_issue_used_before_its_effective_date_is_not_yet_effective(self):
        state = categorize_issue(_document(), "B", "2025-06-01")
        self.assertEqual(state["state"], ISSUE_NOT_YET_EFFECTIVE)

    def test_an_issue_the_document_never_carried_is_unknown(self):
        state = categorize_issue(_document(), "Z", "2026-02-10")
        self.assertEqual(state["state"], ISSUE_UNKNOWN)

    def test_a_lot_naming_no_issue_at_all_is_unknown(self):
        state = categorize_issue(_document(), "   ", "2026-02-10")
        self.assertEqual(state["state"], ISSUE_UNKNOWN)


class LotProcessingTests(unittest.TestCase):
    def test_a_fully_processed_and_inspected_lot_is_clear(self):
        result = assess_lot_processing(_lot(), _document())
        self.assertEqual(result["verdict"], LOT_CLEAR)
        self.assertEqual(result["findings"], [])
        self.assertAlmostEqual(result["process_coverage"], 1.0, places=9)
        self.assertAlmostEqual(result["inspection_coverage"], 1.0, places=9)

    def test_a_missing_step_record_ranks_worst_of_the_step_states(self):
        book = _records(STEPS_B)
        del book["planar-blocking-diode-lead-bonding"]
        result = assess_lot_processing(_lot(step_records=book), _document())
        self.assertEqual(result["verdict"], LOT_STEP_NO_RECORD)
        self.assertEqual(result["missing"], ["planar-blocking-diode-lead-bonding"])

    def test_a_step_the_issue_never_declared_is_reported_as_unauthorised(self):
        book = _records(STEPS_B)
        book["planar-blocking-diode-solvent-wash"] = OUTCOME_PERFORMED
        result = assess_lot_processing(_lot(step_records=book), _document())
        self.assertEqual(result["verdict"], LOT_UNAUTHORISED_STEP)
        self.assertEqual(result["unauthorised"], ["planar-blocking-diode-solvent-wash"])
        self.assertTrue(any("nobody authorised" in f for f in result["findings"]))

    def test_a_step_recorded_as_not_performed_is_kept_apart_from_absence(self):
        book = _records(
            STEPS_B,
            **{"planar-blocking-diode-encapsulation": OUTCOME_NOT_PERFORMED}
        )
        result = assess_lot_processing(_lot(step_records=book), _document())
        self.assertEqual(result["verdict"], LOT_STEP_NOT_PERFORMED)
        self.assertEqual(result["missing"], [])

    def test_a_failed_step_is_kept_apart_from_absence(self):
        book = _records(
            STEPS_B,
            **{"planar-blocking-diode-visual-inspection": OUTCOME_FAILED}
        )
        result = assess_lot_processing(_lot(step_records=book), _document())
        self.assertEqual(result["verdict"], LOT_STEP_FAILED)
        self.assertTrue(any("disposition" in f for f in result["findings"]))

    def test_processing_and_inspection_coverage_are_graded_separately(self):
        book = _records(STEPS_B)
        book["planar-blocking-diode-visual-inspection"] = OUTCOME_NOT_PERFORMED
        book["planar-blocking-diode-contact-area-inspection"] = OUTCOME_NOT_PERFORMED
        result = assess_lot_processing(_lot(step_records=book), _document())
        self.assertAlmostEqual(result["process_coverage"], 1.0, places=9)
        self.assertAlmostEqual(result["inspection_coverage"], 0.0, places=9)
        self.assertTrue(any("built and not verified" in f for f in result["findings"]))

    def test_an_inspection_coverage_landing_exactly_on_the_minimum_is_accepted(self):
        book = _records(STEPS_B)
        book["planar-blocking-diode-visual-inspection"] = OUTCOME_NOT_PERFORMED
        result = assess_lot_processing(
            _lot(step_records=book), _document(), {"min_inspection_coverage": 0.5}
        )
        self.assertAlmostEqual(result["inspection_coverage"], 0.5, places=9)
        self.assertTrue(result["meets_coverage"])

    def test_a_superseded_issue_blocks_the_lot_unless_policy_allows_it(self):
        lot = _lot(issue="A", step_records=_records(STEPS_A))
        blocked = assess_lot_processing(lot, _document())
        allowed = assess_lot_processing(
            lot, _document(), {"allow_superseded_issue": True}
        )
        self.assertEqual(blocked["verdict"], LOT_NO_DOCUMENT)
        self.assertEqual(allowed["verdict"], LOT_CLEAR)

    def test_an_unreleased_issue_leaves_the_lot_without_a_build_standard(self):
        lot = _lot(issue="C", processed_on="2026-09-01")
        result = assess_lot_processing(lot, _document())
        self.assertEqual(result["verdict"], LOT_NO_DOCUMENT)

    def test_an_unknown_issue_leaves_every_recorded_step_unauthorised(self):
        result = assess_lot_processing(_lot(issue="Z"), _document())
        self.assertEqual(result["verdict"], LOT_NO_DOCUMENT)
        self.assertEqual(len(result["unauthorised"]), len(STEPS_B))

    def test_a_lot_naming_another_document_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_lot_processing(_lot(document_id="PID-OTHER-1"), _document())

    def test_an_unknown_step_outcome_is_rejected(self):
        book = _records(STEPS_B)
        book["planar-blocking-diode-die-attach"] = "probably-fine"
        with self.assertRaises(ValueError):
            assess_lot_processing(_lot(step_records=book), _document())


class PolicyTests(unittest.TestCase):
    def test_defaults_resolve(self):
        settings = resolve_policy()
        self.assertAlmostEqual(settings["min_inspection_coverage"], 1.0, places=9)
        self.assertFalse(settings["allow_superseded_issue"])

    def test_a_coverage_minimum_of_zero_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"min_process_coverage": 0.0})

    def test_a_non_boolean_issue_policy_is_rejected(self):
        with self.assertRaises(ValueError):
            resolve_policy({"allow_superseded_issue": "sometimes"})


class DeliveryRollUpTests(unittest.TestCase):
    def test_a_sound_delivery_is_accepted(self):
        result = assess_deliverable_blocking_diodes(_case())
        self.assertEqual(result["verdict"], DELIVERY_ACCEPTED)
        self.assertEqual(result["deliverable_lots"], ["LOT-01", "LOT-02"])
        self.assertEqual(result["findings"], [])

    def test_one_thin_lot_holds_the_delivery(self):
        book = _records(STEPS_B)
        del book["planar-blocking-diode-contact-area-inspection"]
        case = _case(lots=[_lot("LOT-01"), _lot("LOT-02", step_records=book)])
        result = assess_deliverable_blocking_diodes(case)
        self.assertEqual(result["verdict"], DELIVERY_NOT_ACCEPTED)
        self.assertEqual(result["weakest_lot"], "LOT-02")
        self.assertEqual(result["deliverable_lots"], ["LOT-01"])

    def test_a_dispositioned_failure_can_be_carried_by_policy(self):
        book = _records(
            STEPS_B,
            **{"planar-blocking-diode-visual-inspection": OUTCOME_FAILED}
        )
        case = _case(
            lots=[_lot("LOT-01", step_records=book)],
            policy={
                "carry_dispositioned_failure": True,
                "min_inspection_coverage": 0.5,
            },
        )
        result = assess_deliverable_blocking_diodes(case)
        self.assertEqual(result["verdict"], DELIVERY_ACCEPTED)

    def test_a_duplicate_lot_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_deliverable_blocking_diodes(
                _case(lots=[_lot("LOT-01"), _lot("LOT-01")])
            )

    def test_a_delivery_with_no_lots_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_deliverable_blocking_diodes(_case(lots=[]))

    def test_an_empty_part_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_deliverable_blocking_diodes(_case(part_id=" "))


if __name__ == "__main__":
    unittest.main(verbosity=1)
