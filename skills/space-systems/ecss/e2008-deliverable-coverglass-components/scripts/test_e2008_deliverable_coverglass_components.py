#!/usr/bin/env python3
"""Contract test for delivered coverglass components (offline).

Walks the clause workflow step by step: the standing of the cited
process document, the ordered route the batch was actually taken
through, the sampling floor a batch of that size owes, the difference
between a per-coverglass screen and a sampled inspection and the
different way each of them fails, the bracket on how many pieces passed
every screen, the batch disposition, and the piece-weighted delivery
roll-up. This is the gate 3 review evidence for the leaf.
"""

import copy
import unittest

from e2008_deliverable_coverglass_components_logic import (
    BATCH_CONCESSION,
    BATCH_RELEASED,
    BATCH_WITHHELD,
    STANDING_CURRENT,
    STANDING_NOT_GOVERNING,
    STANDING_OFF_ISSUE,
    assess_coverglass_batch,
    assess_coverglass_delivery,
    deliverable_count_bracket,
    grade_inspection_record,
    resolve_document_standing,
    route_conformance,
    sampling_floor,
)

SOUND_ROUTE = [
    "cutting-and-sizing",
    "cleaning",
    "ar-coating-deposition",
    "uv-filter-deposition",
    "marking-and-packaging",
]


def _inspections(count, sample):
    return [
        {
            "inspection": "visual-defect-screen",
            "mode": "per-coverglass-screen",
            "pieces_inspected": count,
            "pieces_failed": 0,
        },
        {
            "inspection": "dimensional-check",
            "mode": "sampled-inspection",
            "pieces_inspected": sample,
            "pieces_failed": 0,
        },
        {
            "inspection": "coating-transmission-check",
            "mode": "sampled-inspection",
            "pieces_inspected": sample,
            "pieces_failed": 0,
        },
    ]


def _batch(batch_id, count=100, sample=11, **overrides):
    record = {
        "batch_id": batch_id,
        "piece_count": count,
        "process_document": {
            "status": "approved",
            "approved_issue": "C",
            "built_issue": "C",
        },
        "declared_route": copy.deepcopy(SOUND_ROUTE),
        "executed_route": copy.deepcopy(SOUND_ROUTE),
        "inspections": _inspections(count, sample),
    }
    record.update(copy.deepcopy(overrides))
    return record


class DocumentStandingTests(unittest.TestCase):
    def test_approved_document_at_the_built_issue_governs_outright(self):
        result = resolve_document_standing("approved", "C", "C")
        self.assertEqual(result["standing"], STANDING_CURRENT)
        self.assertTrue(result["governs"])
        self.assertEqual(result["findings"], [])

    def test_draft_document_governs_nothing(self):
        result = resolve_document_standing("draft", "C", "C")
        self.assertEqual(result["standing"], STANDING_NOT_GOVERNING)
        self.assertFalse(result["governs"])
        self.assertTrue(result["findings"])

    def test_withdrawn_document_governs_nothing(self):
        result = resolve_document_standing("withdrawn", "B", "B")
        self.assertFalse(result["governs"])

    def test_superseded_document_still_governs_off_issue(self):
        result = resolve_document_standing("superseded", "C", "C")
        self.assertEqual(result["standing"], STANDING_OFF_ISSUE)
        self.assertTrue(result["governs"])

    def test_approved_document_at_another_issue_is_off_issue(self):
        result = resolve_document_standing("approved", "D", "B")
        self.assertEqual(result["standing"], STANDING_OFF_ISSUE)
        self.assertTrue(result["findings"])

    def test_unknown_document_status_rejected(self):
        with self.assertRaises(ValueError):
            resolve_document_standing("pending", "C", "C")

    def test_blank_issue_rejected(self):
        with self.assertRaises(ValueError):
            resolve_document_standing("approved", "  ", "C")


class RouteConformanceTests(unittest.TestCase):
    def test_the_declared_route_run_as_declared_conforms(self):
        result = route_conformance(SOUND_ROUTE, SOUND_ROUTE)
        self.assertTrue(result["conforms"])
        self.assertEqual(result["findings"], [])

    def test_a_step_the_document_never_declares_is_named(self):
        executed = SOUND_ROUTE + ["conductive-coating-deposition"]
        result = route_conformance(SOUND_ROUTE, executed)
        self.assertEqual(
            result["undeclared_steps"], ["conductive-coating-deposition"]
        )
        self.assertFalse(result["conforms"])

    def test_coating_run_before_the_clean_breaks_the_sequence(self):
        executed = [
            "cutting-and-sizing",
            "ar-coating-deposition",
            "cleaning",
            "uv-filter-deposition",
            "marking-and-packaging",
        ]
        result = route_conformance(SOUND_ROUTE, executed)
        self.assertEqual(result["out_of_order_steps"], ["cleaning"])
        self.assertFalse(result["conforms"])

    def test_a_declared_step_this_batch_did_not_need_is_only_a_note(self):
        executed = [s for s in SOUND_ROUTE if s != "uv-filter-deposition"]
        result = route_conformance(SOUND_ROUTE, executed)
        self.assertEqual(result["declared_not_run"], ["uv-filter-deposition"])
        self.assertTrue(result["conforms"])
        self.assertTrue(result["findings"])

    def test_a_step_listed_twice_is_rejected(self):
        with self.assertRaises(ValueError):
            route_conformance(SOUND_ROUTE, SOUND_ROUTE + ["cleaning"])

    def test_an_empty_route_is_rejected(self):
        with self.assertRaises(ValueError):
            route_conformance([], SOUND_ROUTE)

    def test_an_unknown_route_step_is_rejected(self):
        with self.assertRaises(ValueError):
            route_conformance(SOUND_ROUTE, ["annealing"])


class SamplingFloorTests(unittest.TestCase):
    def test_floor_on_a_perfect_square_batch_is_exact(self):
        self.assertEqual(sampling_floor(100), 11)
        self.assertEqual(sampling_floor(2500), 51)

    def test_floor_grows_with_the_batch(self):
        self.assertEqual(sampling_floor(2000), 45)

    def test_floor_never_exceeds_the_batch(self):
        self.assertEqual(sampling_floor(2), 2)

    def test_policy_minimum_raises_a_small_batch_floor(self):
        self.assertEqual(sampling_floor(9, {"min_sample_size": 8}), 8)

    def test_empty_batch_rejected(self):
        with self.assertRaises(ValueError):
            sampling_floor(0)

    def test_fractional_batch_count_rejected(self):
        with self.assertRaises(ValueError):
            sampling_floor(10.0)


class InspectionGradingTests(unittest.TestCase):
    def test_full_screen_with_yield_loss_is_acceptable(self):
        result = grade_inspection_record(
            {
                "inspection": "visual-defect-screen",
                "mode": "per-coverglass-screen",
                "pieces_inspected": 100,
                "pieces_failed": 4,
            },
            100,
        )
        self.assertEqual(result["failure_kind"], "screen-yield-loss")
        self.assertTrue(result["acceptable"])

    def test_a_screen_run_on_part_of_the_batch_is_flagged(self):
        result = grade_inspection_record(
            {
                "inspection": "visual-defect-screen",
                "mode": "per-coverglass-screen",
                "pieces_inspected": 60,
                "pieces_failed": 0,
            },
            100,
        )
        self.assertFalse(result["coverage_ok"])

    def test_a_sample_below_the_floor_is_flagged(self):
        result = grade_inspection_record(
            {
                "inspection": "dimensional-check",
                "mode": "sampled-inspection",
                "pieces_inspected": 4,
                "pieces_failed": 0,
            },
            100,
        )
        self.assertFalse(result["coverage_ok"])
        self.assertEqual(result["sampling_floor"], 11)

    def test_a_sample_failure_is_evidence_and_not_yield(self):
        result = grade_inspection_record(
            {
                "inspection": "dimensional-check",
                "mode": "sampled-inspection",
                "pieces_inspected": 12,
                "pieces_failed": 1,
            },
            100,
        )
        self.assertEqual(result["failure_kind"], "sample-evidence")
        self.assertFalse(result["acceptable"])

    def test_a_sample_cannot_discharge_an_owed_screen(self):
        result = grade_inspection_record(
            {
                "inspection": "visual-defect-screen",
                "mode": "sampled-inspection",
                "pieces_inspected": 20,
                "pieces_failed": 0,
            },
            100,
        )
        self.assertFalse(result["mode_ok"])

    def test_an_inspection_outside_the_policy_set_discharges_nothing(self):
        result = grade_inspection_record(
            {
                "inspection": "packing-audit",
                "mode": "sampled-inspection",
                "pieces_inspected": 20,
                "pieces_failed": 0,
            },
            100,
        )
        self.assertIsNone(result["owed_mode"])
        self.assertTrue(result["findings"])

    def test_more_failures_than_pieces_inspected_rejected(self):
        with self.assertRaises(ValueError):
            grade_inspection_record(
                {
                    "inspection": "dimensional-check",
                    "mode": "sampled-inspection",
                    "pieces_inspected": 5,
                    "pieces_failed": 6,
                },
                100,
            )

    def test_inspecting_more_pieces_than_the_batch_holds_rejected(self):
        with self.assertRaises(ValueError):
            grade_inspection_record(
                {
                    "inspection": "dimensional-check",
                    "mode": "sampled-inspection",
                    "pieces_inspected": 120,
                    "pieces_failed": 0,
                },
                100,
            )


class DeliverableBracketTests(unittest.TestCase):
    def test_one_clean_screen_brackets_at_the_batch_count(self):
        result = deliverable_count_bracket(
            100, [{"pieces_inspected": 100, "pieces_failed": 0}]
        )
        self.assertEqual(result["at_most"], 100)
        self.assertEqual(result["at_least"], 100)

    def test_two_screens_give_a_bracket_and_not_one_number(self):
        result = deliverable_count_bracket(
            100,
            [
                {"pieces_inspected": 100, "pieces_failed": 2},
                {"pieces_inspected": 100, "pieces_failed": 5},
            ],
        )
        self.assertEqual(result["at_most"], 95)
        self.assertEqual(result["at_least"], 93)
        self.assertTrue(result["findings"])

    def test_a_screen_coverage_gap_lowers_the_floor(self):
        result = deliverable_count_bracket(
            100, [{"pieces_inspected": 90, "pieces_failed": 0}]
        )
        self.assertEqual(result["at_most"], 90)
        self.assertEqual(result["at_least"], 90)
        self.assertEqual(result["uncovered_slots"], 10)

    def test_no_screen_at_all_releases_nothing(self):
        result = deliverable_count_bracket(100, [])
        self.assertEqual(result["at_least"], 0)
        self.assertTrue(result["findings"])

    def test_non_sequence_screen_records_rejected(self):
        with self.assertRaises(ValueError):
            deliverable_count_bracket(100, "all pieces screened")


class BatchDispositionTests(unittest.TestCase):
    def test_a_sound_batch_releases_in_full(self):
        result = assess_coverglass_batch(_batch("CG-A"))
        self.assertEqual(result["disposition"], BATCH_RELEASED)
        self.assertEqual(result["released_pieces"], 100)

    def test_an_off_issue_document_releases_under_concession(self):
        result = assess_coverglass_batch(
            _batch(
                "CG-B",
                process_document={
                    "status": "approved",
                    "approved_issue": "D",
                    "built_issue": "C",
                },
            )
        )
        self.assertEqual(result["disposition"], BATCH_CONCESSION)

    def test_a_draft_document_withholds_the_batch(self):
        result = assess_coverglass_batch(
            _batch(
                "CG-C",
                process_document={
                    "status": "draft",
                    "approved_issue": "C",
                    "built_issue": "C",
                },
            )
        )
        self.assertEqual(result["disposition"], BATCH_WITHHELD)
        self.assertEqual(result["released_pieces"], 0)

    def test_an_undeclared_route_step_withholds_the_batch(self):
        result = assess_coverglass_batch(
            _batch(
                "CG-D",
                executed_route=SOUND_ROUTE + ["conductive-coating-deposition"],
            )
        )
        self.assertEqual(result["disposition"], BATCH_WITHHELD)

    def test_a_missing_owed_inspection_withholds_the_batch(self):
        record = _batch("CG-E")
        record["inspections"] = record["inspections"][:2]
        result = assess_coverglass_batch(record)
        self.assertEqual(result["missing_inspections"], ["coating-transmission-check"])
        self.assertEqual(result["disposition"], BATCH_WITHHELD)

    def test_a_failed_sample_withholds_the_whole_batch(self):
        record = _batch("CG-F")
        record["inspections"][1]["pieces_failed"] = 1
        result = assess_coverglass_batch(record)
        self.assertEqual(result["disposition"], BATCH_WITHHELD)

    def test_a_partial_screen_releases_under_concession_on_the_lower_bound(self):
        record = _batch("CG-G")
        record["inspections"][0]["pieces_inspected"] = 80
        result = assess_coverglass_batch(record)
        self.assertEqual(result["disposition"], BATCH_CONCESSION)
        self.assertEqual(result["released_pieces"], 80)

    def test_a_batch_with_no_piece_count_rejected(self):
        record = _batch("CG-H")
        del record["piece_count"]
        with self.assertRaises(ValueError):
            assess_coverglass_batch(record)


class DeliveryRollupTests(unittest.TestCase):
    @staticmethod
    def _case(batches, policy=None):
        case = {"delivery_id": "DEL-1", "batches": batches}
        if policy is not None:
            case["policy"] = policy
        return case

    def test_a_clean_delivery_meets_the_release_threshold(self):
        result = assess_coverglass_delivery(
            self._case([_batch("CG-1"), _batch("CG-2")])
        )
        self.assertEqual(result["verdict"], BATCH_RELEASED)
        self.assertTrue(result["meets_release_threshold"])
        self.assertAlmostEqual(result["release_share"], 1.0, places=12)

    def test_the_rollup_weights_pieces_and_not_batches(self):
        small_bad = _batch(
            "CG-SMALL",
            count=20,
            sample=5,
            process_document={
                "status": "draft",
                "approved_issue": "C",
                "built_issue": "C",
            },
        )
        large_clean = _batch("CG-LARGE", count=2000, sample=50)
        result = assess_coverglass_delivery(
            self._case([small_bad, large_clean])
        )
        self.assertEqual(result["total_pieces"], 2020)
        self.assertEqual(result["released_pieces"], 2000)
        self.assertAlmostEqual(result["release_share"], 2000 / 2020, places=12)
        self.assertEqual(result["withheld_batches"], ["CG-SMALL"])

    def test_the_weakest_batch_is_the_largest_of_the_worst(self):
        result = assess_coverglass_delivery(
            self._case(
                [
                    _batch("CG-1"),
                    _batch(
                        "CG-2",
                        count=300,
                        sample=20,
                        executed_route=SOUND_ROUTE
                        + ["conductive-coating-deposition"],
                    ),
                ]
            )
        )
        self.assertEqual(result["verdict"], BATCH_WITHHELD)
        self.assertEqual(result["weakest_batch"], "CG-2")

    def test_a_relaxed_threshold_accepts_a_partly_withheld_delivery(self):
        batches = [
            _batch(
                "CG-1",
                count=20,
                sample=5,
                process_document={
                    "status": "withdrawn",
                    "approved_issue": "C",
                    "built_issue": "C",
                },
            ),
            _batch("CG-2", count=2000, sample=50),
        ]
        strict = assess_coverglass_delivery(self._case(batches))
        relaxed = assess_coverglass_delivery(
            self._case(batches, {"min_release_share": 0.9})
        )
        self.assertFalse(strict["meets_release_threshold"])
        self.assertTrue(relaxed["meets_release_threshold"])

    def test_a_repeated_batch_identifier_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_delivery(
                self._case([_batch("CG-1"), _batch("CG-1")])
            )

    def test_an_empty_delivery_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_delivery(self._case([]))

    def test_a_non_mapping_case_rejected(self):
        with self.assertRaises(ValueError):
            assess_coverglass_delivery("every batch followed the route")


if __name__ == "__main__":
    unittest.main()
