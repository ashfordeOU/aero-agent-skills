#!/usr/bin/env python3
"""Gate 3 contract test: ECSS-E-ST-10C clause 5.2.3.7 requirements-
specification agreement loop.

Exercises scripts/e10_req_agreement_logic.py (stdlib unittest,
offline). Contract: docs/harness-contract.md gate 3 - a party role
categorizes as exactly customer or supplier and an unrecognized role
raises; the required signatories are every recorded party provided at
least one holds the customer role, otherwise it raises; a party's
review state is agreed only when its status is agreed at the
specification's current revision, stale when agreed at a different
revision, an open comment when a dissent is recorded, and pending
otherwise (including no record at all); elapsed days since a review
opened is current day minus opened day and a future opened day
raises; a signatory's violation list reflects its state plus an
overdue-review flag once elapsed days exceeds the review period; and
the aggregated review is agreed only when every required signatory's
violation list is empty.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import e10_req_agreement_logic as ra  # noqa: E402


class ClassifyPartyRoleTest(unittest.TestCase):
    def test_customer_role(self):
        self.assertEqual(ra.classify_party_role("customer"), "customer")

    def test_supplier_role(self):
        self.assertEqual(ra.classify_party_role("supplier"), "supplier")

    def test_unknown_role_raises(self):
        with self.assertRaises(ValueError):
            ra.classify_party_role("observer")


class RequiredSignatoriesTest(unittest.TestCase):
    def test_customer_and_suppliers(self):
        parties = [
            {"party_id": "cust-1", "role": "customer"},
            {"party_id": "supp-1", "role": "supplier"},
            {"party_id": "supp-2", "role": "supplier"},
        ]
        self.assertEqual(
            ra.required_signatories(parties), ["cust-1", "supp-1", "supp-2"]
        )

    def test_deduplicates_repeated_party(self):
        parties = [
            {"party_id": "cust-1", "role": "customer"},
            {"party_id": "cust-1", "role": "customer"},
        ]
        self.assertEqual(ra.required_signatories(parties), ["cust-1"])

    def test_no_customer_raises(self):
        parties = [{"party_id": "supp-1", "role": "supplier"}]
        with self.assertRaises(ValueError):
            ra.required_signatories(parties)

    def test_unknown_role_raises(self):
        parties = [
            {"party_id": "cust-1", "role": "customer"},
            {"party_id": "x", "role": "observer"},
        ]
        with self.assertRaises(ValueError):
            ra.required_signatories(parties)


class ReviewStateTest(unittest.TestCase):
    def test_agreed_at_current_revision(self):
        review = {"status": "agreed", "reviewed_revision": 3}
        self.assertEqual(ra.review_state(review, 3), ra.STATE_AGREED)

    def test_agreed_at_stale_revision(self):
        review = {"status": "agreed", "reviewed_revision": 2}
        self.assertEqual(ra.review_state(review, 3), ra.STATE_STALE_AGREEMENT)

    def test_comment_is_open(self):
        review = {"status": "comment", "reviewed_revision": 3}
        self.assertEqual(ra.review_state(review, 3), ra.STATE_OPEN_COMMENT)

    def test_pending_status(self):
        review = {"status": "pending"}
        self.assertEqual(ra.review_state(review, 3), ra.STATE_PENDING)

    def test_missing_status_is_pending(self):
        self.assertEqual(ra.review_state({}, 3), ra.STATE_PENDING)

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            ra.review_state({"status": "rejected"}, 3)


class DaysPendingTest(unittest.TestCase):
    def test_elapsed_days(self):
        self.assertEqual(ra.days_pending({"opened_day": 10}, 25), 15)

    def test_missing_opened_day_is_zero(self):
        self.assertEqual(ra.days_pending({}, 25), 0)

    def test_future_opened_day_raises(self):
        with self.assertRaises(ValueError):
            ra.days_pending({"opened_day": 30}, 25)


class SignatoryViolationsTest(unittest.TestCase):
    def test_agreed_has_no_violation(self):
        self.assertEqual(
            ra.signatory_violations("cust-1", ra.STATE_AGREED, 0, 30), []
        )

    def test_stale_agreement_flagged(self):
        violations = ra.signatory_violations("cust-1", ra.STATE_STALE_AGREEMENT, 0, 30)
        self.assertEqual(violations, [{"issue": "stale_agreement", "party": "cust-1"}])

    def test_open_comment_within_period(self):
        violations = ra.signatory_violations("supp-1", ra.STATE_OPEN_COMMENT, 5, 30)
        self.assertEqual(violations, [{"issue": "open_comment", "party": "supp-1"}])

    def test_open_comment_overdue(self):
        violations = ra.signatory_violations("supp-1", ra.STATE_OPEN_COMMENT, 45, 30)
        self.assertEqual(
            violations,
            [
                {"issue": "open_comment", "party": "supp-1"},
                {"issue": "overdue_review", "party": "supp-1", "elapsed_days": 45},
            ],
        )

    def test_pending_overdue(self):
        violations = ra.signatory_violations("supp-2", ra.STATE_PENDING, 31, 30)
        self.assertEqual(
            violations,
            [
                {"issue": "pending_agreement", "party": "supp-2"},
                {"issue": "overdue_review", "party": "supp-2", "elapsed_days": 31},
            ],
        )

    def test_negative_review_period_raises(self):
        with self.assertRaises(ValueError):
            ra.signatory_violations("cust-1", ra.STATE_PENDING, 0, -1)


class AgreementReviewTest(unittest.TestCase):
    def test_fully_agreed_spec(self):
        spec = {
            "spec_id": "SRS-001",
            "revision": 2,
            "parties": [
                {"party_id": "cust-1", "role": "customer"},
                {"party_id": "supp-1", "role": "supplier"},
            ],
            "reviews": {
                "cust-1": {"status": "agreed", "reviewed_revision": 2, "opened_day": 1},
                "supp-1": {"status": "agreed", "reviewed_revision": 2, "opened_day": 1},
            },
        }
        review = ra.agreement_review(spec, current_day=5)
        self.assertEqual(review["violations"], [])
        self.assertTrue(ra.is_spec_agreed(review))

    def test_missing_review_treated_as_pending(self):
        spec = {
            "spec_id": "SRS-002",
            "revision": 1,
            "parties": [
                {"party_id": "cust-1", "role": "customer"},
                {"party_id": "supp-1", "role": "supplier"},
            ],
            "reviews": {
                "cust-1": {"status": "agreed", "reviewed_revision": 1, "opened_day": 1},
            },
        }
        review = ra.agreement_review(spec, current_day=5)
        self.assertEqual(review["party_states"]["supp-1"], ra.STATE_PENDING)
        self.assertFalse(ra.is_spec_agreed(review))

    def test_mixed_violations_and_overdue(self):
        spec = {
            "spec_id": "SRS-003",
            "revision": 4,
            "parties": [
                {"party_id": "cust-1", "role": "customer"},
                {"party_id": "supp-1", "role": "supplier"},
                {"party_id": "supp-2", "role": "supplier"},
            ],
            "reviews": {
                "cust-1": {"status": "agreed", "reviewed_revision": 3, "opened_day": 1},
                "supp-1": {"status": "comment", "reviewed_revision": 4, "opened_day": 0},
                "supp-2": {"status": "agreed", "reviewed_revision": 4, "opened_day": 1},
            },
        }
        review = ra.agreement_review(spec, current_day=40, review_period_days=30)
        issues = {(v["party"], v["issue"]) for v in review["violations"]}
        self.assertIn(("cust-1", "stale_agreement"), issues)
        self.assertIn(("supp-1", "open_comment"), issues)
        self.assertIn(("supp-1", "overdue_review"), issues)
        self.assertNotIn(("supp-2", "stale_agreement"), issues)
        self.assertFalse(ra.is_spec_agreed(review))

    def test_review_raises_on_no_customer(self):
        spec = {
            "spec_id": "SRS-004",
            "revision": 1,
            "parties": [{"party_id": "supp-1", "role": "supplier"}],
            "reviews": {},
        }
        with self.assertRaises(ValueError):
            ra.agreement_review(spec, current_day=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
