#!/usr/bin/env python3
"""Contract test for deliverable bare solar cell components (offline)."""

import copy
import unittest

from e2008_bare_cell_deliverable_components_logic import (
    CONCESSION,
    DELIVERABLE,
    DISPOSITION_RANK,
    INSPECTION_MODES,
    LOT_RELEASABLE,
    LOT_RELEASABLE_WITH_CONCESSIONS,
    LOT_WITHHELD,
    PID_STATES,
    REQUIRED_INSPECTIONS,
    SAMPLED_FRACTION_FLOOR,
    STANDING_CURRENT,
    STANDING_NONE,
    STANDING_OFF_ISSUE,
    WITHHELD,
    assess_bare_cell_delivery,
    deliverable_cell_bounds,
    disposition_sub_lot,
    inspection_yield,
    pid_standing,
    process_step_coverage,
)

CELLS = 200

STEPS_DECLARED = [
    "wafer-preparation",
    "junction-formation",
    "antireflection-coating",
    "contact-metallization",
    "dicing",
]

CLEAN_INSPECTIONS = [
    {"kind": "visual-inspection", "mode": "per-cell", "inspected": CELLS, "passed": CELLS},
    {"kind": "electrical-performance", "mode": "per-cell", "inspected": CELLS, "passed": CELLS},
    {"kind": "dimensional-measurement", "mode": "sampled", "inspected": 20, "passed": 20},
    {"kind": "contact-integrity", "mode": "sampled", "inspected": 20, "passed": 20},
]

SUB_LOT_A = {
    "identifier": "BC-LOT-A",
    "cells": CELLS,
    "document_state": "approved",
    "approved_issue": "C",
    "build_issue": "C",
    "steps_used": list(STEPS_DECLARED),
    "steps_declared": list(STEPS_DECLARED),
    "inspections": copy.deepcopy(CLEAN_INSPECTIONS),
}

SUB_LOT_B = dict(SUB_LOT_A, identifier="BC-LOT-B")


def _sub_lot(base=None, **overrides):
    item = copy.deepcopy(base if base is not None else SUB_LOT_A)
    for key, value in overrides.items():
        if value is None and key in item:
            del item[key]
        else:
            item[key] = value
    return item


def _inspections(**per_kind):
    out = copy.deepcopy(CLEAN_INSPECTIONS)
    for record in out:
        if record["kind"] in per_kind:
            record.update(per_kind[record["kind"]])
    return out


class DocumentStandingTests(unittest.TestCase):
    def test_an_approved_document_at_the_build_issue_governs(self):
        result = pid_standing("approved", "C", "C")
        self.assertEqual(result["standing"], STANDING_CURRENT)
        self.assertEqual(result["findings"], [])

    def test_a_draft_process_document_governs_nothing(self):
        result = pid_standing("draft", "C", "C")
        self.assertEqual(result["standing"], STANDING_NONE)
        self.assertTrue(any("draft" in f for f in result["findings"]))

    def test_a_withdrawn_process_document_governs_nothing(self):
        self.assertEqual(pid_standing("withdrawn", "C", "C")["standing"], STANDING_NONE)

    def test_a_superseded_document_leaves_a_delta_to_disposition(self):
        result = pid_standing("superseded", "D", "C")
        self.assertEqual(result["standing"], STANDING_OFF_ISSUE)
        self.assertTrue(any("superseded" in f for f in result["findings"]))

    def test_a_build_to_an_unapproved_issue_is_off_issue(self):
        result = pid_standing("approved", "C", "B")
        self.assertEqual(result["standing"], STANDING_OFF_ISSUE)

    def test_every_declared_document_state_resolves(self):
        for state in PID_STATES:
            self.assertIn(
                pid_standing(state, "C", "C")["standing"],
                (STANDING_CURRENT, STANDING_OFF_ISSUE, STANDING_NONE),
            )

    def test_a_blank_build_issue_is_rejected(self):
        with self.assertRaises(ValueError):
            pid_standing("approved", "C", "  ")

    def test_an_unknown_document_state_is_rejected(self):
        with self.assertRaises(ValueError):
            pid_standing("pending-signature-probably", "C", "C")


class ProcessStepTests(unittest.TestCase):
    def test_a_build_using_only_declared_steps_is_on_document(self):
        result = process_step_coverage(STEPS_DECLARED, STEPS_DECLARED)
        self.assertTrue(result["on_document"])
        self.assertEqual(result["undeclared"], [])

    def test_a_step_used_but_not_declared_takes_the_build_off_document(self):
        used = STEPS_DECLARED + ["laser-edge-isolation"]
        result = process_step_coverage(used, STEPS_DECLARED)
        self.assertEqual(result["undeclared"], ["laser-edge-isolation"])
        self.assertFalse(result["on_document"])

    def test_a_declared_step_left_unused_is_a_note_not_a_defect(self):
        used = STEPS_DECLARED[:-1]
        result = process_step_coverage(used, STEPS_DECLARED)
        self.assertEqual(result["unused_declared"], ["dicing"])
        self.assertTrue(result["on_document"])

    def test_a_process_document_declaring_no_step_is_rejected(self):
        with self.assertRaises(ValueError):
            process_step_coverage(STEPS_DECLARED, [])

    def test_a_build_recording_no_step_is_rejected(self):
        with self.assertRaises(ValueError):
            process_step_coverage([], STEPS_DECLARED)


class InspectionYieldTests(unittest.TestCase):
    def test_a_full_per_cell_screen_covers_the_sub_lot(self):
        result = inspection_yield(CLEAN_INSPECTIONS[0], CELLS)
        self.assertTrue(result["coverage_ok"])
        self.assertAlmostEqual(result["inspected_fraction"], 1.0, places=9)
        self.assertAlmostEqual(result["pass_fraction"], 1.0, places=9)

    def test_a_partial_per_cell_screen_leaves_cells_without_a_record(self):
        record = {"kind": "visual-inspection", "mode": "per-cell",
                  "inspected": 150, "passed": 150}
        result = inspection_yield(record, CELLS)
        self.assertFalse(result["coverage_ok"])
        self.assertTrue(any("carry no record" in f for f in result["findings"]))

    def test_a_sample_exactly_on_the_sampling_floor_is_adequate(self):
        inspected = int(round(CELLS * SAMPLED_FRACTION_FLOOR))
        record = {"kind": "dimensional-measurement", "mode": "sampled",
                  "inspected": inspected, "passed": inspected}
        result = inspection_yield(record, CELLS)
        self.assertAlmostEqual(
            result["inspected_fraction"], SAMPLED_FRACTION_FLOOR, places=9
        )
        self.assertTrue(result["coverage_ok"])

    def test_a_sample_under_the_floor_does_not_speak_for_the_sub_lot(self):
        record = {"kind": "dimensional-measurement", "mode": "sampled",
                  "inspected": 5, "passed": 5}
        self.assertFalse(inspection_yield(record, CELLS)["coverage_ok"])

    def test_a_failure_inside_a_sample_makes_the_population_suspect(self):
        record = {"kind": "contact-integrity", "mode": "sampled",
                  "inspected": 20, "passed": 19}
        result = inspection_yield(record, CELLS)
        self.assertFalse(result["sample_clean"])
        self.assertEqual(result["failed"], 1)

    def test_a_failure_inside_a_per_cell_screen_is_yield_not_suspicion(self):
        record = {"kind": "visual-inspection", "mode": "per-cell",
                  "inspected": CELLS, "passed": CELLS - 4}
        result = inspection_yield(record, CELLS)
        self.assertTrue(result["sample_clean"])
        self.assertAlmostEqual(result["pass_fraction"], 196.0 / 200.0, places=9)

    def test_more_cells_inspected_than_the_sub_lot_holds_is_rejected(self):
        record = {"kind": "visual-inspection", "mode": "per-cell",
                  "inspected": CELLS + 1, "passed": CELLS}
        with self.assertRaises(ValueError):
            inspection_yield(record, CELLS)

    def test_more_passes_than_inspections_is_rejected(self):
        record = {"kind": "visual-inspection", "mode": "per-cell",
                  "inspected": 10, "passed": 11}
        with self.assertRaises(ValueError):
            inspection_yield(record, CELLS)

    def test_an_unknown_inspection_mode_is_rejected(self):
        record = {"kind": "visual-inspection", "mode": "eyeballed",
                  "inspected": 10, "passed": 10}
        with self.assertRaises(ValueError):
            inspection_yield(record, CELLS)

    def test_every_declared_mode_is_handled(self):
        for mode in INSPECTION_MODES:
            record = {"kind": "visual-inspection", "mode": mode,
                      "inspected": CELLS, "passed": CELLS}
            self.assertIn("coverage_ok", inspection_yield(record, CELLS))


class DeliverableBoundsTests(unittest.TestCase):
    def test_a_clean_sub_lot_brackets_every_cell_exactly(self):
        yields = [inspection_yield(r, CELLS) for r in CLEAN_INSPECTIONS]
        bounds = deliverable_cell_bounds(CELLS, yields)
        self.assertEqual(bounds["lower"], CELLS)
        self.assertEqual(bounds["upper"], CELLS)
        self.assertTrue(bounds["determinate"])

    def test_independent_failures_widen_the_bracket(self):
        records = _inspections(
            **{
                "visual-inspection": {"passed": CELLS - 2},
                "electrical-performance": {"passed": CELLS - 5},
            }
        )
        yields = [inspection_yield(r, CELLS) for r in records]
        bounds = deliverable_cell_bounds(CELLS, yields)
        self.assertEqual(bounds["upper"], CELLS - 5)
        self.assertEqual(bounds["lower"], CELLS - 7)
        self.assertFalse(bounds["determinate"])

    def test_cells_with_no_screen_record_lower_the_floor_of_the_bracket(self):
        records = _inspections(
            **{"visual-inspection": {"inspected": 150, "passed": 150}}
        )
        yields = [inspection_yield(r, CELLS) for r in records]
        bounds = deliverable_cell_bounds(CELLS, yields)
        self.assertEqual(bounds["upper"], 150)
        self.assertEqual(bounds["unrecorded"], 50)

    def test_a_sub_lot_with_no_per_cell_screen_releases_nothing(self):
        sampled_only = [r for r in CLEAN_INSPECTIONS if r["mode"] == "sampled"]
        yields = [inspection_yield(r, CELLS) for r in sampled_only]
        bounds = deliverable_cell_bounds(CELLS, yields)
        self.assertEqual(bounds["upper"], 0)
        self.assertFalse(bounds["determinate"])

    def test_a_zero_cell_sub_lot_is_rejected(self):
        with self.assertRaises(ValueError):
            deliverable_cell_bounds(0, [])


class SubLotDispositionTests(unittest.TestCase):
    def test_a_clean_sub_lot_is_deliverable_in_full(self):
        result = disposition_sub_lot(_sub_lot())
        self.assertEqual(result["disposition"], DELIVERABLE)
        self.assertEqual(result["releasable_cells"], CELLS)
        self.assertEqual(result["findings"], [])

    def test_a_draft_process_document_withholds_the_whole_sub_lot(self):
        result = disposition_sub_lot(_sub_lot(document_state="draft"))
        self.assertEqual(result["disposition"], WITHHELD)
        self.assertEqual(result["releasable_cells"], 0)

    def test_an_off_issue_build_releases_only_under_concession(self):
        result = disposition_sub_lot(_sub_lot(build_issue="B"))
        self.assertEqual(result["disposition"], CONCESSION)
        self.assertEqual(result["releasable_cells"], CELLS)

    def test_an_undeclared_process_step_withholds_the_sub_lot(self):
        used = STEPS_DECLARED + ["unlogged-anneal"]
        result = disposition_sub_lot(_sub_lot(steps_used=used))
        self.assertEqual(result["disposition"], WITHHELD)

    def test_a_missing_required_inspection_withholds_the_sub_lot(self):
        records = [r for r in copy.deepcopy(CLEAN_INSPECTIONS)
                   if r["kind"] != "contact-integrity"]
        result = disposition_sub_lot(_sub_lot(inspections=records))
        self.assertEqual(result["missing_inspections"], ["contact-integrity"])
        self.assertEqual(result["disposition"], WITHHELD)

    def test_a_screen_run_as_a_sample_does_not_discharge_the_screen(self):
        records = _inspections(**{"visual-inspection": {"mode": "sampled"}})
        result = disposition_sub_lot(_sub_lot(inspections=records))
        self.assertEqual(result["wrong_mode_inspections"], ["visual-inspection"])
        self.assertEqual(result["disposition"], WITHHELD)

    def test_a_failure_in_a_sampled_inspection_withholds_the_sub_lot(self):
        records = _inspections(**{"contact-integrity": {"passed": 19}})
        result = disposition_sub_lot(_sub_lot(inspections=records))
        self.assertEqual(result["disposition"], WITHHELD)

    def test_a_partial_screen_releases_only_under_concession(self):
        records = _inspections(
            **{"visual-inspection": {"inspected": 150, "passed": 150}}
        )
        result = disposition_sub_lot(_sub_lot(inspections=records))
        self.assertEqual(result["disposition"], CONCESSION)
        self.assertEqual(result["releasable_cells"], 150)

    def test_screen_yield_loss_lowers_the_released_count_not_the_disposition(self):
        records = _inspections(**{"electrical-performance": {"passed": CELLS - 6}})
        result = disposition_sub_lot(_sub_lot(inspections=records))
        self.assertEqual(result["disposition"], DELIVERABLE)
        self.assertEqual(result["releasable_cells"], CELLS - 6)

    def test_a_duplicated_inspection_record_is_rejected(self):
        records = copy.deepcopy(CLEAN_INSPECTIONS)
        records.append(copy.deepcopy(CLEAN_INSPECTIONS[0]))
        with self.assertRaises(ValueError):
            disposition_sub_lot(_sub_lot(inspections=records))

    def test_a_missing_sub_lot_key_is_rejected(self):
        with self.assertRaises(ValueError):
            disposition_sub_lot(_sub_lot(steps_declared=None))

    def test_every_required_inspection_is_looked_for(self):
        result = disposition_sub_lot(_sub_lot(inspections=[]))
        self.assertEqual(
            sorted(result["missing_inspections"]),
            sorted(kind for kind, _ in REQUIRED_INSPECTIONS),
        )


class DeliveryTests(unittest.TestCase):
    def test_a_clean_delivery_of_two_sub_lots_is_releasable(self):
        result = assess_bare_cell_delivery(
            {"sub_lots": [_sub_lot(), _sub_lot(SUB_LOT_B)]}
        )
        self.assertEqual(result["verdict"], LOT_RELEASABLE)
        self.assertAlmostEqual(result["release_share"], 1.0, places=9)
        self.assertEqual(result["total_cells"], 2 * CELLS)

    def test_one_withheld_sub_lot_withholds_the_delivery(self):
        result = assess_bare_cell_delivery(
            {
                "sub_lots": [_sub_lot(), _sub_lot(SUB_LOT_B, document_state="draft")],
                "required_release_share": 0.0,
            }
        )
        self.assertEqual(result["verdict"], LOT_WITHHELD)
        self.assertEqual(result["withheld"], ["BC-LOT-B"])

    def test_a_concession_sub_lot_downgrades_but_does_not_withhold(self):
        result = assess_bare_cell_delivery(
            {"sub_lots": [_sub_lot(), _sub_lot(SUB_LOT_B, build_issue="B")]}
        )
        self.assertEqual(result["verdict"], LOT_RELEASABLE_WITH_CONCESSIONS)
        self.assertEqual(result["under_concession"], ["BC-LOT-B"])

    def test_the_release_share_is_weighted_by_cells_not_by_sub_lots(self):
        small = _sub_lot(SUB_LOT_B, cells=20, inspections=_inspections(
            **{
                "visual-inspection": {"inspected": 20, "passed": 20},
                "electrical-performance": {"inspected": 20, "passed": 20},
                "dimensional-measurement": {"inspected": 2, "passed": 2},
                "contact-integrity": {"inspected": 2, "passed": 2},
            }
        ))
        result = assess_bare_cell_delivery({"sub_lots": [_sub_lot(), small]})
        self.assertEqual(result["total_cells"], CELLS + 20)
        self.assertAlmostEqual(result["release_share"], 1.0, places=9)

    def test_a_release_share_exactly_on_its_threshold_is_met(self):
        records = _inspections(**{"electrical-performance": {"passed": CELLS - 20}})
        result = assess_bare_cell_delivery(
            {
                "sub_lots": [_sub_lot(inspections=records)],
                "required_release_share": 0.9,
            }
        )
        self.assertAlmostEqual(result["release_share"], 0.9, places=9)
        self.assertEqual(result["verdict"], LOT_RELEASABLE)

    def test_a_release_share_under_its_threshold_withholds_the_delivery(self):
        records = _inspections(**{"electrical-performance": {"passed": CELLS - 40}})
        result = assess_bare_cell_delivery(
            {
                "sub_lots": [_sub_lot(inspections=records)],
                "required_release_share": 0.9,
            }
        )
        self.assertEqual(result["verdict"], LOT_WITHHELD)

    def test_the_worst_sub_lot_sets_the_delivery_verdict(self):
        ranks = [DISPOSITION_RANK[d] for d in (WITHHELD, CONCESSION, DELIVERABLE)]
        self.assertEqual(ranks, sorted(ranks))

    def test_a_repeated_sub_lot_identifier_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_delivery({"sub_lots": [_sub_lot(), _sub_lot()]})

    def test_an_empty_delivery_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_delivery({"sub_lots": []})

    def test_a_release_threshold_outside_the_unit_interval_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_delivery(
                {"sub_lots": [_sub_lot()], "required_release_share": 1.4}
            )

    def test_a_non_mapping_spec_is_rejected(self):
        with self.assertRaises(ValueError):
            assess_bare_cell_delivery([_sub_lot()])


if __name__ == "__main__":
    unittest.main(verbosity=1)
