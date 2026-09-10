#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10-02C clause 5.2.4.3 acceptance stage.

Exercises scripts/e1002_acceptance_logic.py (stdlib unittest, offline).
Contract: docs/harness-contract.md gate 3 - a prototype-philosophy
article needs a dedicated acceptance test while a protoflight article
is credited from its protoflight campaign; flight-standard eligibility
gates ahead of the test result; a prototype acceptance test that
exceeds the qualification amplitude is flagged as overtest rather than
silently accepted; workmanship/performance failures route to
nonconformance instead of acceptance; and stage closure requires every
article in the set to be dispositioned and accepted.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e1002_acceptance_logic as acc  # noqa: E402


class RequiredTestRoleTest(unittest.TestCase):
    def test_prototype_needs_acceptance_test(self):
        self.assertEqual(acc.required_test_role("prototype"), "acceptance_test")

    def test_protoflight_is_credited(self):
        self.assertEqual(acc.required_test_role("protoflight"), "protoflight_credit")

    def test_unknown_philosophy_raises(self):
        with self.assertRaises(ValueError):
            acc.required_test_role("qualification_only")


class CheckFlightStandardTest(unittest.TestCase):
    def test_matching_baseline_is_eligible(self):
        self.assertTrue(acc.check_flight_standard("baseline-B3", "baseline-B3"))

    def test_mismatched_baseline_is_not_eligible(self):
        self.assertFalse(acc.check_flight_standard("baseline-EM-parts", "baseline-B3"))


class CheckAcceptanceOvertestTest(unittest.TestCase):
    def test_prototype_within_qualification_amplitude_ok(self):
        self.assertFalse(acc.check_acceptance_overtest("prototype", 8.0, 10.0))

    def test_prototype_exceeding_qualification_amplitude_flagged(self):
        self.assertTrue(acc.check_acceptance_overtest("prototype", 12.0, 10.0))

    def test_protoflight_exempt_even_at_full_amplitude(self):
        self.assertFalse(acc.check_acceptance_overtest("protoflight", 10.0, 10.0))

    def test_unknown_philosophy_raises(self):
        with self.assertRaises(ValueError):
            acc.check_acceptance_overtest("qualification_only", 5.0, 5.0)


class EvaluateTestOutcomeTest(unittest.TestCase):
    def test_clean_run_passes(self):
        self.assertEqual(
            acc.evaluate_test_outcome(anomaly_detected=False, performance_within_spec=True),
            "passed",
        )

    def test_anomaly_fails(self):
        self.assertEqual(
            acc.evaluate_test_outcome(anomaly_detected=True, performance_within_spec=True),
            "failed",
        )

    def test_out_of_spec_performance_fails(self):
        self.assertEqual(
            acc.evaluate_test_outcome(anomaly_detected=False, performance_within_spec=False),
            "failed",
        )


class DispositionArticleTest(unittest.TestCase):
    BASE = {
        "id": "ART-001",
        "philosophy": "prototype",
        "article_baseline": "baseline-B3",
        "qualified_baseline": "baseline-B3",
        "applied_amplitude": 8.0,
        "qualification_amplitude": 10.0,
        "anomaly_detected": False,
        "performance_within_spec": True,
    }

    def test_clean_prototype_article_is_accepted(self):
        self.assertEqual(
            acc.disposition_article(self.BASE),
            {"id": "ART-001", "role": "acceptance_test", "status": "accepted"},
        )

    def test_baseline_mismatch_blocks_before_test_result_matters(self):
        article = dict(self.BASE, article_baseline="baseline-EM-parts", anomaly_detected=True)
        self.assertEqual(
            acc.disposition_article(article)["status"], "blocked_not_flight_standard"
        )

    def test_overtest_blocks_even_with_clean_result(self):
        article = dict(self.BASE, applied_amplitude=12.0)
        self.assertEqual(acc.disposition_article(article)["status"], "blocked_overtest")

    def test_anomaly_fails_workmanship_or_performance(self):
        article = dict(self.BASE, anomaly_detected=True)
        self.assertEqual(
            acc.disposition_article(article)["status"],
            "failed_workmanship_or_performance",
        )

    def test_protoflight_article_credited_at_full_amplitude(self):
        article = dict(
            self.BASE,
            philosophy="protoflight",
            applied_amplitude=10.0,
        )
        self.assertEqual(
            acc.disposition_article(article),
            {"id": "ART-001", "role": "protoflight_credit", "status": "accepted"},
        )

    def test_missing_id_raises(self):
        article = dict(self.BASE)
        del article["id"]
        with self.assertRaises(ValueError):
            acc.disposition_article(article)


class BuildAcceptanceDispositionTest(unittest.TestCase):
    ARTICLES = [
        {
            "id": "ART-001",
            "philosophy": "prototype",
            "article_baseline": "baseline-B3",
            "qualified_baseline": "baseline-B3",
            "applied_amplitude": 8.0,
            "qualification_amplitude": 10.0,
            "anomaly_detected": False,
            "performance_within_spec": True,
        },
        {
            "id": "ART-002",
            "philosophy": "protoflight",
            "article_baseline": "baseline-B4",
            "qualified_baseline": "baseline-B4",
            "applied_amplitude": 9.0,
            "qualification_amplitude": 9.0,
            "anomaly_detected": True,
            "performance_within_spec": True,
        },
    ]

    def test_disposition_order_and_content(self):
        result = acc.build_acceptance_disposition(self.ARTICLES)
        self.assertEqual(
            result,
            [
                {"id": "ART-001", "role": "acceptance_test", "status": "accepted"},
                {
                    "id": "ART-002",
                    "role": "protoflight_credit",
                    "status": "failed_workmanship_or_performance",
                },
            ],
        )

    def test_duplicate_id_raises(self):
        with self.assertRaises(ValueError):
            acc.build_acceptance_disposition(self.ARTICLES + [self.ARTICLES[0]])

    def test_does_not_mutate_input(self):
        before = [dict(a) for a in self.ARTICLES]
        acc.build_acceptance_disposition(self.ARTICLES)
        self.assertEqual(self.ARTICLES, before)


class MissingDispositionsTest(unittest.TestCase):
    def test_detects_gap(self):
        dispositions = [{"id": "ART-001", "role": "acceptance_test", "status": "accepted"}]
        self.assertEqual(
            acc.missing_dispositions(["ART-001", "ART-002", "ART-003"], dispositions),
            ["ART-002", "ART-003"],
        )

    def test_no_gap(self):
        dispositions = [{"id": "ART-001", "role": "acceptance_test", "status": "accepted"}]
        self.assertEqual(acc.missing_dispositions(["ART-001"], dispositions), [])


class CloseOutAcceptanceStageTest(unittest.TestCase):
    def test_all_accepted_closes_clean(self):
        dispositions = [
            {"id": "ART-001", "role": "acceptance_test", "status": "accepted"},
            {"id": "ART-002", "role": "protoflight_credit", "status": "accepted"},
        ]
        self.assertEqual(acc.close_out_acceptance_stage(dispositions), (True, []))

    def test_open_items_block_closure(self):
        dispositions = [
            {"id": "ART-001", "role": "acceptance_test", "status": "accepted"},
            {"id": "ART-002", "role": "acceptance_test", "status": "blocked_overtest"},
        ]
        self.assertEqual(
            acc.close_out_acceptance_stage(dispositions),
            (False, [{"id": "ART-002", "status": "blocked_overtest"}]),
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
