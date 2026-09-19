#!/usr/bin/env python3
"""Gate 3 contract test for e2040-device-phase-review-conduct.

Offline, deterministic, stdlib unittest. Run:
    python3 test_e2040_device_phase_review_conduct.py
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from e2040_device_phase_review_conduct_logic import (  # noqa: E402
    BOARD_SIDES,
    DISPOSITIONS,
    PHASE_REVIEWS,
    SEVERITIES,
    conduct_phase_review,
    meets_readiness_threshold,
    normalize_disposition,
    normalize_phase,
    normalize_review,
    normalize_severity,
    observation_closure,
    open_observations,
    output_readiness,
    outstanding_outputs,
    review_closing_phase,
    validate_board,
    validate_observations,
    validate_outputs,
)


def base_review():
    return {
        "review": "pdr",
        "phase": "definition",
        "board": {
            "chair": "customer review manager",
            "chair_side": "customer",
            "participants": ["supplier lead", "product assurance"],
        },
        "outputs": [
            {
                "id": "DI-01",
                "title": "device requirements specification",
                "mandatory": True,
                "delivered": True,
                "mature": True,
            },
            {
                "id": "DI-02",
                "title": "development plan",
                "mandatory": True,
                "delivered": True,
                "mature": True,
            },
            {
                "id": "DI-03",
                "title": "preliminary verification plan",
                "mandatory": True,
                "delivered": True,
                "mature": True,
            },
            {
                "id": "DI-04",
                "title": "trade study note",
                "mandatory": False,
                "delivered": False,
                "mature": False,
            },
        ],
        "observations": [
            {
                "id": "RID-1",
                "severity": "minor",
                "disposition": "closed",
                "rationale": "text corrected in issue 2",
            },
            {
                "id": "RID-2",
                "severity": "comment",
                "disposition": "rejected",
                "rationale": "out of scope for this device",
            },
        ],
        "readiness_threshold": 1.0,
    }


def codes(result):
    return sorted({finding["code"] for finding in result["findings"]})


class TestFolding(unittest.TestCase):
    def test_review_long_name_folds(self):
        self.assertEqual(normalize_review("Critical Design Review"), "cdr")

    def test_review_short_name_folds(self):
        self.assertEqual(normalize_review("  ORR "), "orr")

    def test_unknown_review_rejected(self):
        with self.assertRaises(ValueError):
            normalize_review("kickoff meeting")

    def test_phase_alias_folds(self):
        self.assertEqual(normalize_phase("Detailed Design"), "detailed-design")

    def test_unknown_phase_rejected(self):
        with self.assertRaises(ValueError):
            normalize_phase("disposal")

    def test_severity_alias_folds(self):
        self.assertEqual(normalize_severity("Critical"), "major")

    def test_disposition_alias_folds(self):
        self.assertEqual(
            normalize_disposition("accepted with action"), "action-raised"
        )

    def test_unknown_disposition_rejected(self):
        with self.assertRaises(ValueError):
            normalize_disposition("deferred forever")

    def test_blank_severity_rejected(self):
        with self.assertRaises(ValueError):
            normalize_severity("   ")

    def test_vocabularies_are_closed(self):
        self.assertEqual(len(PHASE_REVIEWS), 6)
        self.assertEqual(len(SEVERITIES), 3)
        self.assertEqual(len(DISPOSITIONS), 4)
        self.assertIn("customer", BOARD_SIDES)


class TestReviewPhasePairing(unittest.TestCase):
    def test_definition_phase_is_closed_by_pdr(self):
        self.assertEqual(review_closing_phase("definition"), "pdr")

    def test_qualification_phase_is_closed_by_qr(self):
        self.assertEqual(review_closing_phase("qualification"), "qr")

    def test_mismatched_review_is_a_finding(self):
        review = base_review()
        review["review"] = "cdr"
        result = conduct_phase_review(review)
        self.assertIn("review-does-not-close-phase", codes(result))
        self.assertEqual(result["verdict"], "review-repeated")


class TestBoard(unittest.TestCase):
    def test_customer_chair_accepted(self):
        board = validate_board(base_review()["board"])
        self.assertEqual(board["chair_side"], "customer")

    def test_supplier_chair_is_a_finding_not_an_error(self):
        review = base_review()
        review["board"]["chair_side"] = "supplier"
        result = conduct_phase_review(review)
        self.assertIn("review-not-customer-chaired", codes(result))

    def test_missing_chair_rejected(self):
        with self.assertRaises(ValueError):
            validate_board({"chair": "", "chair_side": "customer"})

    def test_unknown_chair_side_rejected(self):
        with self.assertRaises(ValueError):
            validate_board({"chair": "a", "chair_side": "regulator"})

    def test_unknown_board_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_board(
                {"chair": "a", "chair_side": "customer", "secretary": "b"}
            )


class TestOutputs(unittest.TestCase):
    def test_duplicate_output_id_rejected(self):
        entries = base_review()["outputs"]
        entries.append(dict(entries[0]))
        with self.assertRaises(ValueError):
            validate_outputs(entries)

    def test_unknown_output_key_rejected(self):
        with self.assertRaises(ValueError):
            validate_outputs([{"id": "DI-01", "owner": "supplier"}])

    def test_non_boolean_maturity_rejected(self):
        with self.assertRaises(ValueError):
            validate_outputs([{"id": "DI-01", "mature": "yes"}])

    def test_optional_output_excluded_from_readiness(self):
        outputs = validate_outputs(base_review()["outputs"])
        self.assertAlmostEqual(output_readiness(outputs), 1.0, places=9)

    def test_delivered_but_immature_is_not_ready(self):
        review = base_review()
        review["outputs"][1]["mature"] = False
        result = conduct_phase_review(review)
        self.assertIn("mandatory-output-immature", codes(result))
        self.assertIn("DI-02", result["outstanding_outputs"])

    def test_undelivered_mandatory_output_reported(self):
        review = base_review()
        review["outputs"][2]["delivered"] = False
        review["outputs"][2]["mature"] = False
        result = conduct_phase_review(review)
        self.assertIn("mandatory-output-undelivered", codes(result))

    def test_readiness_is_two_in_three_when_one_output_slips(self):
        review = base_review()
        review["outputs"][0]["delivered"] = False
        review["outputs"][0]["mature"] = False
        result = conduct_phase_review(review)
        self.assertAlmostEqual(result["readiness"], 2.0 / 3.0, places=9)

    def test_no_mandatory_output_rejected(self):
        review = base_review()
        for item in review["outputs"]:
            item["mandatory"] = False
        with self.assertRaises(ValueError):
            conduct_phase_review(review)


class TestObservations(unittest.TestCase):
    def test_duplicate_observation_id_rejected(self):
        entries = base_review()["observations"]
        entries.append(dict(entries[0]))
        with self.assertRaises(ValueError):
            validate_observations(entries)

    def test_rejected_without_rationale_is_a_finding(self):
        review = base_review()
        review["observations"][1]["rationale"] = ""
        result = conduct_phase_review(review)
        self.assertIn("disposition-without-rationale", codes(result))

    def test_open_major_observation_repeats_the_review(self):
        review = base_review()
        review["observations"].append(
            {"id": "RID-3", "severity": "major", "disposition": "open"}
        )
        result = conduct_phase_review(review)
        self.assertIn("major-observation-open", codes(result))
        self.assertEqual(result["verdict"], "review-repeated")
        self.assertEqual(result["open_major_observations"], ["RID-3"])

    def test_major_moved_to_an_action_still_blocks(self):
        review = base_review()
        review["observations"].append(
            {"id": "RID-4", "severity": "major", "disposition": "action-raised"}
        )
        result = conduct_phase_review(review)
        self.assertIn("major-observation-open", codes(result))

    def test_open_minor_observation_closes_with_actions(self):
        review = base_review()
        review["observations"].append(
            {"id": "RID-5", "severity": "minor", "disposition": "action-raised"}
        )
        result = conduct_phase_review(review)
        self.assertEqual(result["verdict"], "closed-with-actions")
        self.assertFalse(result["acceptable"])

    def test_observation_closure_counts_settled_items(self):
        observations = validate_observations(base_review()["observations"])
        self.assertAlmostEqual(observation_closure(observations), 1.0, places=9)

    def test_open_observations_filtered_by_severity(self):
        review = base_review()
        review["observations"].append(
            {"id": "RID-6", "severity": "comment", "disposition": "open"}
        )
        observations = validate_observations(review["observations"])
        self.assertEqual(open_observations(observations, "comment"), ["RID-6"])
        self.assertEqual(open_observations(observations, "major"), [])

    def test_observation_closure_needs_an_observation(self):
        with self.assertRaises(ValueError):
            observation_closure([])


class TestThresholdPortability(unittest.TestCase):
    def test_exact_landing_meets_the_threshold(self):
        self.assertTrue(meets_readiness_threshold(3.0 / 4.0, 0.75))

    def test_two_in_three_meets_a_two_in_three_threshold(self):
        self.assertTrue(meets_readiness_threshold(2.0 / 3.0, 2.0 / 3.0))

    def test_below_threshold_reported(self):
        self.assertFalse(meets_readiness_threshold(0.5, 0.75))

    def test_threshold_outside_unit_interval_rejected(self):
        with self.assertRaises(ValueError):
            meets_readiness_threshold(0.5, 1.5)

    def test_boolean_is_not_a_fraction(self):
        with self.assertRaises(ValueError):
            meets_readiness_threshold(True, 0.5)

    def test_readiness_exactly_on_a_relaxed_threshold_passes(self):
        review = base_review()
        review["outputs"][0]["mature"] = False
        review["readiness_threshold"] = 2.0 / 3.0
        result = conduct_phase_review(review)
        self.assertNotIn("readiness-below-threshold", codes(result))


class TestVerdict(unittest.TestCase):
    def test_clean_review_closes(self):
        result = conduct_phase_review(base_review())
        self.assertEqual(result["verdict"], "closed")
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_mandatory_count_excludes_optional_items(self):
        result = conduct_phase_review(base_review())
        self.assertEqual(result["mandatory_count"], 3)

    def test_unknown_review_key_rejected(self):
        review = base_review()
        review["venue"] = "site"
        with self.assertRaises(ValueError):
            conduct_phase_review(review)

    def test_missing_outputs_rejected(self):
        review = base_review()
        del review["outputs"]
        with self.assertRaises(ValueError):
            conduct_phase_review(review)

    def test_non_mapping_review_rejected(self):
        with self.assertRaises(ValueError):
            conduct_phase_review([("review", "pdr")])

    def test_empty_output_list_rejected(self):
        review = base_review()
        review["outputs"] = []
        with self.assertRaises(ValueError):
            conduct_phase_review(review)


if __name__ == "__main__":
    unittest.main()
